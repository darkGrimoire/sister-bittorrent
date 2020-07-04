import asyncio
from dumper import dump
from torrent import Torrent
from tracker import Tracker, TrackerManager, PEER_ID
from peer import PeerManager
from piece import PieceManager

class TorrentClient():
    def __init__(self, torrent: str):
        self.torrent = Torrent(torrent)
        self.tracker_manager = TrackerManager(self.torrent)
        self.piece_manager = PieceManager(self.torrent)
        self.peer_manager = PeerManager(self.torrent.getInfoHash(), PEER_ID, self.piece_manager)
        self.leech_task = None
        self.seed_task = None

    async def main(self):
        await self.tracker_manager.requestPeers()
        peers = self.tracker_manager.getPeersOnly()
        await self.peer_manager.addPeers(peers)
        self.leech_task = asyncio.create_task(self.peer_manager.download())
        self.seed_task = asyncio.create_task(self.peer_manager.handleRequests())
        while self.peer_manager.downloading or self.peer_manager.seeding:
            await asyncio.sleep(2)
            dump(self.peer_manager)
            self.displayProgress()

    def displayProgress(self):
        active_peers = []
        for peer in self.peer_manager.peer_list:
            print(f'HEALTH STATUS: {peer.time_span} {peer.timeout} | {peer.notTimeout()} {peer.isResponsive()}')
            if peer.isHealthy():
                active_peers.append(peer)
        n_peers = len(active_peers)
        size_tor = float(self.torrent.getSize() / (1024 * 1024))
        size_completed = float(self.piece_manager.completed_size / (1024 * 1024))
        percentage = round(size_completed / size_tor * 100)
        percentage_bar = '#' * round(size_completed / size_tor * 20)
        seed_ratio = 0
        print(f'Active Peers: {n_peers}')
        for idx, peer in enumerate(active_peers):
            if (idx+1) % 2 != 0:
                print(f'{peer}          ', end='')
            else:
                print(f'{peer}')
        print(f'\nCompleted: {percentage:>2}% | {percentage_bar:20} of 100% | {size_completed:.2f}MB of {size_tor:.2f}MB | seed ratio: {seed_ratio}')

if __name__ == "__main__":
    client = TorrentClient('sintel.torrent')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.main())