import random
import string
from typing import Type
import asyncio
from aiohttp import ClientSession
from urllib.parse import urlencode
from bcoding import bdecode
from dumper import dump
from torrent import Torrent

PEER_ID = 'SISTER-' + ''.join(
    random.choice(string.ascii_lowercase + string.digits)
    for i in range(13)
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

    async def getPeers(self):
        raw_peers = await self.requestPeers()
        print(f'---RAW PEERS RESPONSE--- {self.url}:{self.info_hash}:{self.size}')
        print(raw_peers)
        # peers = self.unpackPeers()
        return raw_peers
    
    async def requestPeers(self):
        async with ClientSession() as session:
            try:
                response = await session.get(self.url + '?' + self.getTrackerParams())
                response_data = await response.read()
                peers = bdecode(response_data)
                return peers
            except TypeError:
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
                    print(f'reconnecting... from tracker {self.url}')
                    await asyncio.sleep(2)
                    await self.requestPeers()
    
    def getTrackerParams(self):
        msg = {
            'info_hash': self.info_hash,
            'peer_id': PEER_ID,
            'port': 6889,
            'uploaded': 0,
            'downloaded': 0,
            'left': self.size,
            'compact': 1,
            'event': 'started'
        }
        return urlencode(msg)
    
    def unpackPeers(self):
        pass

if __name__ == "__main__":
    torrent = Torrent('sintel.torrent')
    trackman = TrackerManager(torrent)
    dump(trackman)
    loop = asyncio.get_event_loop()
    print(torrent.getAnnounceList())
    loop.run_until_complete(trackman.getPeers())
    loop.close()