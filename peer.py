import time
import random
import struct
import asyncio
from bitstring import BitArray
from typing import List, Dict
import messages
from piece import PieceManager
from block import BLOCK_SIZE
from dumper import dump

MAX_RETRY = 3
MAX_PEER = 30
INFINITE = float('inf')

class PeerManager():
    def __init__(self, info_hash, peer_id: str, piece_manager: PieceManager):
        self.peer_list = []
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.piece_manager = piece_manager
        self.downloadable_peers = asyncio.Queue()
        self.requesting_peers = asyncio.Queue()
        self.cancelled_requests = []
        self.choked_peer = []
        self.seeding = True
        self.seeded = 0

    @property
    def downloading(self):
        return not self.piece_manager.isComplete()

    async def addPeers(self, raw_peers):
        if raw_peers[0].get('peer id'):
            peers = [Peer(self, raw_peer['ip'], raw_peer['port'], raw_peer['peer id']) for raw_peer in raw_peers]
        else:
            peers = [Peer(self, raw_peer['ip'], raw_peer['port']) for raw_peer in raw_peers]
        connectPeersTasks = [peer.connect() for peer in peers]
        for res in asyncio.as_completed(connectPeersTasks):
            peer = await res
            if len(self.peer_list) < MAX_PEER and peer.isHealthy() and peer not in self.peer_list:
                peer.task = asyncio.create_task(peer.readMessage())
                self.peer_list.append(peer)

    def removePeer(self, peer):
        if peer in self.peer_list:
            peer.task.cancel()
            self.peer_list.remove(peer)
                
    async def download(self):
        while self.downloading:
            peer = await self.downloadable_peers.get()
            if not peer.isHealthy():
                continue
            if  len(peer.have_pieces) > 10:
                have_pieces = random.sample(peer.have_pieces, 10)
            else:
                have_pieces = peer.have_pieces
            for piece_idx in have_pieces:
                if self.piece_manager.bitfield[piece_idx]:
                    peer.have_pieces.remove(piece_idx)
                    continue
                request_data = self.piece_manager.getEmptyBlockFromPiece(piece_idx)
                if request_data:
                    req_idx, req_begin, req_length = request_data
                    request = messages.Request(req_idx, req_begin, req_length)
                    await peer.sendMessage(request.writeMessage())
                    print(f'PEER_MAN: downloading piece {piece_idx} from {peer.ip}')
                    await asyncio.sleep(0.01)
            await asyncio.sleep(0.2)
            await self.downloadable_peers.put(peer)

    async def handleRequests(self):
        while self.seeding:
            peer, request = await self.requesting_peers.get()
            if (peer, request) in self.cancelled_requests:
                self.cancelled_requests.remove((peer, request))
                continue
            block = self.piece_manager.getBlock(request.idx, request.begin, request.length)
            if block:
                piece = messages.Piece(request.idx, request.begin, block, request.length)
                await peer.sendMessage(piece.writeMessage())
                self.seeded += request.length
                print(f'PEER_MAN: Request {peer.ip} for piece {request.idx} has been fulfilled!')

    async def addReadyPeer(self, peer):
        await self.downloadable_peers.put(peer)

    async def addRequestPeer(self, peer, request: messages.Request):
        await self.requesting_peers.put((peer, request))

    def addPiece(self, piece: messages.Piece):
        self.piece_manager.receiveBlock(piece.idx, piece.begin, piece.block, piece.block_length)

    def removeRequest(self, peer, cancel: messages.Cancel):
        request = messages.Request(cancel.idx, cancel.begin, cancel.length)
        self.cancelled_requests.append((peer, request))

class Peer():
    def __init__(self, peer_manager: PeerManager, ip: str, port: int, peer_id='???'):
        self.ip = ip
        self.port = port
        if isinstance(peer_id, bytes):
            peer_id = peer_id.decode('utf-8', 'replace')
        self.peer_id = peer_id
        self.peer_manager = peer_manager
        self.state = {
            'am_choking': True,
            'am_interested': False,
            'peer_choking': True,
            'peer_interested': False
        }
        self.handshaked = False
        self.timeout = 0
        self.retry = 0
        self.have_pieces = []
        self.writer: asyncio.StreamWriter = None
        self.reader: asyncio.StreamReader = None
        self.task = None

    def __eq__(self, peer):
        return isinstance(peer, Peer) and self.ip == peer.ip and self.port == peer.port

    def __repr__(self):
        return f'{self.peer_id} {self.ip}:{self.port}'

    @property
    def time_span(self):
        return time.time()

    def notTimeout(self):
        return self.time_span >= self.timeout

    def isResponsive(self):
        return 0 <= self.time_span - self.timeout <= 20

    def isHealthy(self) -> bool:
        return self.notTimeout() and self.isResponsive()
    
    def handleHandshake(self, handshake: messages.Handshake):
        print(f'PEER: {self.ip}:{self.port} get handshake!')
        self.timeout = self.time_span
        self.handshaked = True
        self.peer_manager.getBitfield()

    def handleKeepAlive(self):
        self.timeout = self.time_span

    async def handleInterested(self, _):
        print(f'PEER: {self.ip}:{self.port} handling Interested...')
        self.timeout = self.time_span
        self.state['peer_interested'] = True
        if self.state['am_choking']:
            self.state['am_choking'] = False
            unchoke = messages.UnChoke()
            await self.sendMessage(unchoke.writeMessage())

    async def handleNotInterested(self, _):
        print(f'PEER: {self.ip}:{self.port} handling Not Interested...')
        self.timeout = self.time_span
        self.state['peer_interested'] = False
    
    async def handleChoke(self, _):
        print(f'PEER: {self.ip}:{self.port} handling Choke...')
        self.state['peer_choking'] = True
        self.timeout = self.time_span + 10

    async def handleUnchoke(self, _):
        print(f'PEER: {self.ip}:{self.port} handling Unchoke...')
        self.timeout = self.time_span
        self.state['peer_choking'] = False
        await self.peer_manager.addReadyPeer(self)
    
    async def handleBitfield(self, bitfield: messages.BitField):
        print(f'PEER: {self.ip}:{self.port} handling Bitfield...')
        self.timeout = self.time_span
        for idx, have in enumerate(bitfield.bitfield):
            if have:
                self.have_pieces.append(idx)
        if self.peer_manager.downloading and self.state['peer_choking'] and not self.state['am_interested']:
            interested = messages.Interested()
            await self.sendMessage(interested.writeMessage())
            self.state['am_interested'] = True
            print(f'PEER: {self.ip}:{self.port} sent interested!')

    async def handleHave(self, have: messages.Have):
        print(f'PEER: {self.ip}:{self.port} handling Have...')
        self.timeout = self.time_span
        self.have_pieces.append(have.piece_idx)
        if self.peer_manager.downloading and self.state['peer_choking'] and not self.state['am_interested']:
            interested = messages.Interested()
            await self.sendMessage(interested.writeMessage())
            self.state['am_interested'] = True
            print(f'PEER: {self.ip}:{self.port} sent interested!')

    async def handleRequest(self, request: messages.Request):
        print(f'PEER: {self.ip}:{self.port} handling Request...')
        self.timeout = self.time_span
        if self.state['peer_interested'] and self.state['am_choking']:
            await self.peer_manager.addRequestPeer(self, request)
    
    async def handlePiece(self, piece: messages.Piece):
        print(f'PEER: {self.ip}:{self.port} handling Piece...')
        self.timeout = self.time_span
        self.peer_manager.addPiece(piece)

    async def handleCancel(self, cancel: messages.Cancel):
        print(f'PEER: {self.ip}:{self.port} handling Cancel...')
        self.timeout = self.time_span
        self.peer_manager.removeRequest(self, cancel)

    async def handlePort(self, port: messages.Port):
        print(f'PEER: {self.ip}:{self.port} handling Port...')
        self.timeout = self.time_span
        pass

    async def connect(self):
        try:
            print(f'PEER: Trying to connect to {self.ip}:{self.port}...')
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip, self.port),
                timeout=5
            )
            handshake = messages.Handshake(self.peer_manager.peer_id.encode(), self.peer_manager.info_hash)
            self.writer.write(handshake.writeMessage())
            await self.writer.drain()
            self.timeout = self.time_span
            print(f'PEER: Connected and handshake sent to {self.ip}:{self.port}!')
        except Exception as e:
            print(f'PEER: {self.ip}:{self.port} Cannot create connection')
            print(e)
            print(type(e))
            self.timeout = INFINITE
        finally:
            return self
    
    async def readHandshake(self):
        resp = await self.reader.read(68)
        try:
            handshake_msg = messages.Handshake.readMessage(resp)
            self.handshaked = True
            self.timeout = self.time_span
            print(f'PEER: handshake readed from {self.ip}:{self.port}!')
        except:
            print(f'PEER: {self.ip} does not receive handshake msg first!')
            self.timeout = INFINITE
            self.task.cancel()

    async def sendMessage(self, message: bytes):
        if self.isHealthy():
            self.writer.write(message)
            await self.writer.drain()
    
    async def readMessage(self):
        while True:
            if not self.handshaked:
                await self.readHandshake()
            else:
                print(f'PEER: {self.ip}:{self.port} starts reading messages')
                msg_handler = {
                    messages.Choke: self.handleChoke,
                    messages.UnChoke: self.handleUnchoke,
                    messages.Interested: self.handleInterested,
                    messages.NotInterested: self.handleNotInterested,
                    messages.Have: self.handleHave,
                    messages.BitField: self.handleBitfield,
                    messages.Request: self.handleRequest,
                    messages.Piece: self.handlePiece,
                    messages.Cancel: self.handleCancel,
                    messages.Port: self.handlePort
                }
                buffer = b''
                while True:
                    resp = await self.reader.read(BLOCK_SIZE)
                    buffer += resp
                    print(f'PEER: {self.ip}:{self.port} has read {len(resp)} buffer! now buffer {len(buffer)}')
                    if not buffer and not resp:
                        break
                    self.timeout = self.time_span
                    while True:
                        if len(buffer) < 4:
                            break
                        msg_len = struct.unpack('>I', buffer[:4])[0]
                        total_length = msg_len + 4
                        if len(buffer) < total_length:
                            print(f'PEER: {self.ip}:{self.port} length mismatch, reread. {len(buffer)} < {total_length}')
                            break
                        payload = buffer[:total_length]
                        buffer = buffer[total_length:]
                        if msg_len == 0:
                            self.handleKeepAlive()
                            continue
                        try:
                            print(f'PEER: {self.ip}:{self.port} Determining Message...')
                            msg = messages.Message.determineMessage(payload)
                            print(f'PEER: {self.ip}:{self.port} successfully readed message {type(msg)}')
                            if msg:
                                await msg_handler[type(msg)](msg)
                        except messages.WrongMessageException:
                            print(f'PEER: {self.ip} error determining message')
                            continue


                    
                


