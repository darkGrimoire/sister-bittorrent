import random
import string
import ipaddress
import struct
from typing import Dict, Optional
import asyncio
from aiohttp import ClientSession
from urllib.parse import urlencode
from pprint import pformat
from bcoding import bdecode
from torrent import Torrent
import util

PEER_ID = 'SISTER-' + ''.join(
    random.choice(string.ascii_lowercase + string.digits)
    for i in range(13)
)

MAX_RETRY = 2

class TrackerManager():
    def __init__(self, torrent: Torrent):
        self.torrent = torrent
        self.trackers_url = torrent.getAnnounceList()
        self.trackers = [Tracker(url[0], self.torrent.getInfoHash(), self.torrent.getSize()) for url in self.trackers_url]
        self.trackers_tasks = [tracker.getPeers() for tracker in self.trackers]
        self.tracker_responses = []
        
    async def requestPeers(self):
        self.tracker_responses = []
        for res in asyncio.as_completed(self.trackers_tasks):
            tracker_resp = await res
            if tracker_resp:
                self.tracker_responses.append(tracker_resp)
            print(f'TRACKER: tracker_response now: {self.tracker_responses}')
    
    def getPeersOnly(self):
        peers = []
        for response in self.tracker_responses:
            for peer in response['peers']:
                peer_item = {'ip': peer['ip'], 'port': peer['port']}
                if peer_item not in peers:
                    peers.append(peer_item)
        return peers

    def getPeers(self):
        peers = []
        for response in self.tracker_responses:
            for peer in response['peers']:
                if not peer.get('peer id'):
                    peer['peer id'] = '???'
                peer_item = {'peer id': peer['peer id'], 'ip': peer['ip'], 'port': peer['port']}
                res_idx, res = util.searchDictIdx(peers, 'ip', peer_item['ip'])
                if res_idx == -1:
                    peers.append(peer_item)
                elif peer['peer id'] != '???' and res['peer id'] == '???':
                    peers.pop(res_idx)
                    peers.append(peer_item)
        return peers

    async def sendCompleted(self):
        for tracker in self.trackers:
            tracker.event = 'completed'
        self.tracker_responses = []
        tracker_tasks = [tracker.getPeers() for tracker in self.trackers]
        for res in asyncio.as_completed(tracker_tasks):
            tracker_resp = await res
            if tracker_resp:
                self.tracker_responses.append(tracker_resp)
            # print(f'TRACKER: tracker_response now: {self.tracker_responses}')
        else:
            print(f'TRACKER_MAN: send complete done!')
    
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
        # print(f'---TRACKER RESPONSE--- {self.url}:{self.info_hash}:{self.size}')
        # print(tracker_response)
        if tracker_response:
            if isinstance(tracker_response['peers'], bytes):
                tracker_response = self.unpackPeers(tracker_response)
        self.event = ''
        return tracker_response
    
    async def requestPeers(self) -> Optional[Dict]:
        async with ClientSession() as session:
            try:
                response = await session.get(self.url + '?' + self.getTrackerParams())
                response_data = await response.read()
                peers = bdecode(response_data)
                return peers
            except (TypeError, ValueError):
                # print(f'TRACKER: cannot decode response from {self.url}')
                # print(f'TRACKER: response: {response_data}')
                self.tries += 1
                if self.tries >= MAX_RETRY:
                    # print(f'TRACKER: cannot connect to tracker {self.url}!')
                    return
                else:
                    # print(f'TRACKER: reconnecting... from tracker {self.url} using compact mode')
                    self.compact = 1
                    await asyncio.sleep(2)
                    await self.requestPeers()
            except Exception as e:
                # print(e)
                # print(type(e))
                
                self.tries += 1
                if self.tries == MAX_RETRY:
                    # print(f'TRACKER: cannot connect to tracker {self.url}!')
                    return
                else:
                    # print(f'TRACKER: reconnecting... from tracker {self.url} using compact mode')
                    self.compact = 1
                    await asyncio.sleep(2)
                    await self.requestPeers()
    
    def getTrackerParams(self) -> str:
        msg = {
            'info_hash': self.info_hash,
            'peer_id': PEER_ID,
            'port': 52786,
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

async def main(torrent):
    trackman = TrackerManager(torrent)
    dump(trackman)
    await trackman.requestPeers()
    print('TRACKER: TASKS COMPLETED!')
    print('TRACKER: peers')
    print(pformat(trackman.getPeers()))
    print('TRACKER: peers compact')
    print(pformat(trackman.getPeersOnly()))

if __name__ == "__main__":
    from dumper import dump
    import messages
    import piece
    torrent = Torrent('sintel.torrent')
    loop = asyncio.get_event_loop()
    print(torrent.getAnnounceList())
    loop.run_until_complete(main(torrent))
    loop.close()