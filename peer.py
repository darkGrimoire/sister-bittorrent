import time
import struct
import asyncio
from bitstring import BitArray
from typing import List, Dict
import messages
from block import BLOCK_SIZE

MAX_RETRY = 3
INFINITE = float('inf')

class PeerManager():
    def __init__(self, peer_list: List, info_hash, peer_id: str):
        self.peer_list = peer_list
        self.info_hash = info_hash
        self.peer_id = peer_id

    async def requestPiece(self):
        pass

    def addReadyPeer(self, peer: Peer):
        pass
    def addRequestPeer(self, request: messages.Request):
        pass
    def addPiece(self, piece: messages.Piece):
        pass
    def removeRequest(self, request: messages.Cancel):
        pass
    
class Peer():
    def __init__(self, peer_manager: PeerManager, info_hash: bytes, ip: str, port: int, peer_id: str):
        self.info_hash = info_hash
        self.ip = ip
        self.port = port
        self.peer_manager = peer_manager
        self.state = {
            'am_choking': 1,
            'am_interested': 0,
            'peer_choking': 1,
            'peer_interested': 0
        }
        self.peer_id = peer_id
        self.handshaked = False
        self.last_seen = 0
        self.timeout = 0
        self.retry = 0
        self.bitfield = BitArray(peer_manager.getNumPieces())
        self.writer: asyncio.StreamWriter = None
        self.reader: asyncio.StreamReader = None

    def isHealthy(self) -> bool:
        return self.last_seen >= self.timeout

    def handleHandshake(self, handshake: messages.Handshake):
        self.handshaked = True
        self.last_seen = time.time()
        self.peer_manager.getBitfield()

    def handleKeepAlive(self, _):
        self.last_seen = time.time()

    def handleInterested(self, _):
        print(f'PEER: {self.peer_id} handling Interested...')
        self.state['peer_interested'] = 1

    def handleNotInterested(self, _):
        print(f'PEER: {self.peer_id} handling Not Interested...')
        self.state['peer_interested'] = 0
    
    def handleChoke(self, _):
        print(f'PEER: {self.peer_id} handling Choke...')
        self.state['peer_choking'] = 1
        self.timeout = self.last_seen + 20

    def handleUnchoke(self):
        print(f'PEER: {self.peer_id} handling Unchoke...')
        self.state['peer_choking'] = 0
        self.peer_manager.addReadyPeer(self)
    
    def handleBitfield(self, bitfield: messages.BitField):
        print(f'PEER: {self.peer_id} handling Bitfield...')
        self.bitfield = bitfield.bitfield

    def handleHave(self, have: messages.Have):
        print(f'PEER: {self.peer_id} handling Have...')
        self.bitfield[have.piece_idx] = True

    def handleRequest(self, request: messages.Request):
        print(f'PEER: {self.peer_id} handling Request...')
        self.peer_manager.addRequestPeer(self, request)
    
    def handlePiece(self, piece: messages.Piece):
        print(f'PEER: {self.peer_id} handling Piece...')
        self.peer_manager.addPiece(self, piece)

    def handleCancel(self, cancel: messages.Cancel):
        print(f'PEER: {self.peer_id} handling Cancel...')
        self.peer_manager.removeRequest(self, cancel)

    def handlePort(self, port: messages.Port):
        pass

    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip, self.port),
                timeout=10
            )
        except:
            print(f'PEER: {self.peer_id} Cannot create connection')
            self.timeout = INFINITE
    
    async def readHandshake(self):
        resp = await self.reader.read(68)
        try:
            handshake_msg = messages.Handshake.readMessage(resp)
            self.handshaked = True
        except:
            print(f'PEER: {self.ip} does not receive handshake msg first!')
            self.timeout = INFINITE

    async def sendMessage(self, message: bytes):
        if self.isHealthy():
            self.writer.write(message)
            await self.writer.drain()
            self.last_seen = time.time()
    
    async def readMessage(self):
        if not self.handshaked:
            self.readHandshake()
        else:
            msg_handler = {
                messages.Choke: handleChoke,
                messages.UnChoke: handleUnchoke,
                messages.Interested: handleInterested,
                messages.NotInterested: handleNotInterested,
                messages.Have: handleHave,
                messages.BitField: handleBitfield,
                messages.Request: handleRequest,
                messages.Piece: handlePiece,
                messages.Cancel: handleCancel,
                messages.Port: handlePort
            }
            buffer = b''
            while True:
                resp = await self.reader.read(BLOCK_SIZE)
                buffer += resp
                if not buffer and not resp:
                    return
                while True:
                    if len(buffer) < 4:
                        break
                    msg_len = struct.unpack('>I', buffer[:4][0])
                    total_length = msg_len + 4
                    if len(buffer) < total_length:
                        break
                    payload = buffer[:total_length]
                    buffer = buffer[total_length:]
                    if msg_len == 0:
                        self.handleKeepAlive()
                        continue
                    try:
                        msg = messages.Message.determineMessage(payload)
                        if msg:
                            msg_handler[type(msg)](msg)
                    except messages.WrongMessageException:
                        print(f'PEER: {self.ip} error determining message')
                        continue


                    
                


