import random
import string
import ipaddress
import struct
from typing import Type, Dict, Optional
import asyncio
from aiohttp import ClientSession
from urllib.parse import urlencode
from bcoding import bdecode
from dumper import dump
from torrent import Torrent

PEER_ID = 'SISTER-FAWWIS-' + ''.join(
    random.choice(string.ascii_lowercase + string.digits)
    for i in range(6)
)

MAX_RETRY = 2

class TrackerManager():
    def __init__(self, torrent: Type[Torrent]):
        self.torrent = torrent
        self.trackers_url = torrent.getAnnounceList()
        self.trackers = [Tracker(url[0], self.torrent.getInfoHash(), self.torrent.getSize()) for url in self.trackers_url]
        self.trackers_tasks = [tracker.getPeers() for tracker in self.trackers]
        self.peers = []
        
    async def getPeers(self):
        for res in asyncio.as_completed(self.trackers_tasks):
            tracker_response = await res
            if tracker_response:
                self.peers.append(tracker_response)
            print(f'self.peers now: {self.peers}')

class Tracker():
    def __init__(self, tracker_url: str, info_hash, size: int):
        self.url = tracker_url
        if 'announce' not in self.url:
            if self.url[-1] == '/':
                self.url += 'announce'
            else:
                self.url += '/announce'
        self.info_hash = info_hash
        self.size = size
        self.tries = 0
        self.compact = 0
        self.event = 'started'

    async def getPeers(self) -> Dict:
        tracker_response = await self.requestPeers()
        print(f'---TRACKER RESPONSE--- {self.url}:{self.info_hash}:{self.size}')
        print(tracker_response)
        if tracker_response:
            if isinstance(tracker_response['peers'], bytes):
                tracker_response = self.unpackPeers(tracker_response)
        return tracker_response
    
    async def requestPeers(self) -> Optional[Dict]:
        async with ClientSession() as session:
            try:
                response = await session.get(self.url + '?' + self.getTrackerParams())
                response_data = await response.read()
                peers = bdecode(response_data)
                return peers
            except (TypeError, ValueError):
                print(f'cannot decode response from {self.url}')
                print(f'response: {response_data}')
            except Exception as e:
                print(e)
                print(type(e))
                
                self.tries += 1
                if self.tries == MAX_RETRY:
                    print(f'cannot connect to tracker {self.url}!')
                    return
                else:
                    print(f'reconnecting... from tracker {self.url} using compact mode')
                    self.compact = 1
                    await asyncio.sleep(2)
                    await self.requestPeers()
    
    def getTrackerParams(self) -> str:
        msg = {
            'info_hash': self.info_hash,
            'peer_id': PEER_ID,
            'port': 6889,
            'uploaded': 0,
            'downloaded': 0,
            'left': self.size,
            'compact': self.compact,
            'event': self.event
        }
        return urlencode(msg)
    
    def unpackPeers(self, raw_response: Dict) -> Dict:
        new_response = raw_response
        peers = raw_response['peers']
        temp = [peers[i:i+6] for i in range(0, len(peers), 6)]
        new_peers = [{'ip': str(ipaddress.IPv4Address(peer[:4])), 'port': struct.unpack('>H', peer[4:])[0]} for peer in temp]
        new_response['peers'] = new_peers
        return new_response

if __name__ == "__main__":
    torrent = Torrent('sintel.torrent')
    trackman = TrackerManager(torrent)
    dump(trackman)
    loop = asyncio.get_event_loop()
    print(torrent.getAnnounceList())
    loop.run_until_complete(trackman.getPeers())
    loop.close()