import time
import asyncio
from bitstring import BitArray
from typing import List, Dict
import messages

MAX_RETRY = 3
INFINITE = float('inf')

class PeerManager():
    def __init__(self, peer_list: List, info_hash, peer_id: str):
        self.peer_list = peer_list
        self.info_hash = info_hash
        self.peer_id = peer_id

    async def requestPiece(self):
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

    def isHealthy(self) -> bool:
        return self.last_seen >= self.timeout

    def handleHandshake(self, handshake: messages.Handshake):
        self.handshaked = True
        self.last_seen = time.time()
        self.peer_manager.getBitfield()

    def handleKeepAlive(self):
        self.last_seen = time.time()

    def handleInterested(self):
        print(f'PEER: {self.peer_id} handling Interested...')
        self.state['peer_interested'] = 1

    def handleNotInterested(self):
        print(f'PEER: {self.peer_id} handling Not Interested...')
        self.state['peer_interested'] = 0
    
    def handleChoke(self):
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

    async def communicate(self):
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip, self.port),
                timeout=10
            )
        except:
            print(f'PEER: {self.peer_id} Cannot create connection')
            self.timeout = INFINITE
            return

        while not self.handshaked:
            writer.write(messages.Handshake(self.peer_id, self.info_hash).writeMessage())
            await writer.drain()
            handshake = await reader.read(49 + messages.HANDSHAKE_PSTRLEN)
            try:
                read_handshake = messages.Handshake.readMessage(handshake)
                self.handshaked = True
                self.last_seen = time.time()
            except:
                print(f'PEER: {self.peer_id} First message is not handshake!')
                self.retry += 1
                if self.retry >= MAX_RETRY:
                    self.timeout = INFINITE
                    return
                await asyncio.sleep(1)
                continue
        
        writer.write(messages.Interested().writeMessage())
        await writer.drain()
        self.state['am_interested'] = 1
        