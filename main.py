from dumper import dump
from torrent import Torrent
from tracker import Tracker

if __name__ == "__main__":
    torrent_file = 'sintel.torrent'
    torrent = Torrent(torrent_file)
    Tracker = Tracker(torrent.getAnnounceList())