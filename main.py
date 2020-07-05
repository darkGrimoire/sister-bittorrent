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
        if not self.piece_manager.isComplete():
            await self.tracker_manager.requestPeers()
            peers = self.tracker_manager.getPeersOnly()
            await self.peer_manager.addPeers(peers)
            self.leech_task = asyncio.create_task(self.peer_manager.download())
            self.seed_task = asyncio.create_task(self.peer_manager.handleRequests())
            self.filesaver_task = asyncio.create_task(self.piece_manager.writePiece())
            while self.peer_manager.downloading:
                await asyncio.sleep(2)
                # dump(self.peer_manager)
                self.displayDownloadProgress()
            await self.tracker_manager.sendCompleted()
        print(f'DOWNLOAD FOR {self.torrent.torrent_file} HAS COMPLETED!')
        print('------SEEDING START------')
        await self.openServer()
        self.refresh_tracker_task = asyncio.create_task(self.refreshTrackers())
        while self.peer_manager.seeding:
            await asyncio.sleep(2)
            self.displayUploadProgress()
    
    async def refreshTrackers(self):
        while True:
            await asyncio.sleep(30)
            await self.tracker_manager.requestPeers()
            peers = self.tracker_manager.getPeersOnly()
            # await self.peer_manager.addPeers(peers)

    async def openServer(self):
        self.server = await asyncio.start_server(self.peer_manager.serveClientConnect, '127.0.0.1', 52786)
        self.server_task = asyncio.create_task(self.server.serve_forever())
        print(f'SERVER STARTED! {self.server.is_serving()}')

    def displayDownloadProgress(self):
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
        seed_ratio = float(self.peer_manager.seeded / self.torrent.getSize())
        print(f'Active Peers: {n_peers}')
        for idx, peer in enumerate(active_peers):
            if (idx+1) % 2 != 0:
                print(f'{peer}          ', end='')
            else:
                print(f'{peer}')
        print(f'\nCompleted: {percentage:>2}% | {percentage_bar:20} of 100% | {size_completed:.2f}MB of {size_tor:.2f}MB | seed ratio: {seed_ratio:.3f}')

    def displayUploadProgress(self):
        active_peers = []
        for peer in self.peer_manager.peer_list:
            print(f'HEALTH STATUS: {peer.time_span} {peer.timeout} | {peer.notTimeout()} {peer.isResponsive()}')
            if peer.isHealthy():
                active_peers.append(peer)
        n_peers = len(active_peers)
        size_tor = float(self.torrent.getSize() / (1024 * 1024))
        seed_ratio = float(self.peer_manager.seeded / self.torrent.getSize())
        print(f'Active Peers: {n_peers}')
        for idx, peer in enumerate(active_peers):
            if (idx+1) % 2 != 0:
                print(f'{peer}          ', end='')
            else:
                print(f'{peer}')
        print(f'\nCompleted: 100% | {size_tor:.2f}MB | seed ratio: {seed_ratio:.3f}')

if __name__ == "__main__":
    client = TorrentClient('sintel.torrent')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.main())