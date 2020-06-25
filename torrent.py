import math
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
from bcoding import bencode, bdecode
from dumper import dump

class Torrent():
    def __init__(self, torrent_file: str):
        self.torrent_file = torrent_file
        self.metainfo = self.decode_file()
        self.file_mode = self.isSingleFile()
        self.files = self.getFiles()
        bencoded_info = bencode(self.metainfo['info'])
        self.infoHash = hashlib.sha1(bencoded_info).digest()

    # GETTER
    def getAnnounce(self) -> str:
        return self.metainfo['announce']
    def getAnnounceList(self) -> List:
        return [self.getAnnounce()] if self.file_mode else self.metainfo.get('announce-list')
    def getCreationDate(self) -> Optional[str]:
        return datetime.fromtimestamp(self.metainfo.get('creation date')) if 'creation date' in self.metainfo else None
    def getCreator(self) -> Optional[str]:
        return self.metainfo.get('created by')
    def getComment(self) -> Optional[str]:
        return self.metainfo.get('comment')
    def getTorrentInfo(self) -> str:
        msg =(
            f'---TORRENT INFO---\n'
            f'Torrent File: {self.torrent_file}\n'
            f'Comment: {self.getComment()}\n'
            f'Created by: {self.getCreator()}\n'
            f'Pieces: {self.getNumPieces()}'
        )
        return msg
    def getRoot(self) -> str:
        return self.metainfo['info']['name']
    def getFiles(self) -> List:
        return self.files
    def getNumPieces(self) -> int:
        total_length = self.metainfo['info']['length'] if self.file_mode else sum(afile["length"] for afile in self.metainfo["info"]["files"])
        piece_size = self.metainfo['info']['piece length']
        return math.ceil(total_length/piece_size)
    def getInfoHash(self):
        return self.infoHash
    def getHashPiece(self, idx):
        return self.metainfo['info']['pieces'][idx*20:idx*20+20]
    def getSize(self) -> int:
        return self.metainfo['info']['length'] if self.file_mode else sum(afile["length"] for afile in self.metainfo["info"]["files"])
    def getPieceSize(self) -> int:
        return self.metainfo['info']['piece length']
    
    # Construction related methods
    def decode_file(self) -> Dict:
        with open(self.torrent_file, 'rb') as f:
            return bdecode(f)
    def isSingleFile(self) -> bool:
        return 'files' not in self.metainfo['info']
    def getFiles(self) -> List:
        files = []
        root = self.metainfo['info']['name']
        if self.file_mode:
            files.append([root])
        else:
            for file_info in self.metainfo['info']['files']:
                files.append(file_info['path'])
        return files

if __name__ == "__main__":
    tor = Torrent('sintel.torrent')
    dump(tor)
    urls = tor.getAnnounceList()
    for url in urls:
        print(url)