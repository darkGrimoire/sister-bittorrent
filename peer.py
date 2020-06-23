import struct
from typing import List, Dict

HANDSHAKE_RESERVED = b'\x00' * 8
HANDSHAKE_PSTR = b'BitTorrent protocol'
HANDSHAKE_PSTRLEN = len(HANDSHAKE_PSTR)
        

class PeerManager():
    def __init__(self, peer_list: List, info_hash, peer_id: str):
        self.peer_list = peer_list
        self.info_hash = info_hash
        self.peer_id = peer_id

    async def requestPiece(self):
        pass
    
class Peer():
    def __init__(self, info_hash, ip: str, port: int, peer_id: str):
        self.info_hash = info_hash
        self.ip = ip
        self.port = port
        self.state = {
            'am_choking': 1,
            'am_interested': 0,
            'peer_choking': 1,
            'peer_interested': 0
        }
        self.peer_id = peer_id

    def handshakeMsg(self):
        return struct.pack(f'>B{HANDSHAKE_PSTRLEN}s8s20s20s',
            HANDSHAKE_PSTRLEN,
            HANDSHAKE_PSTR,
            HANDSHAKE_RESERVED,
            self.info_hash,
            self.peer_id
        )