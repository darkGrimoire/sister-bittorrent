import math
import time
import hashlib
import bitstring
from torrent import Torrent
from block import Block, BLOCK_SIZE, State

class PieceManager():
    def __init__(self, torrent : Torrent):
        self.torrent = torrent
        self.bitfield = bitstring.BitArray(torrent.getNumPieces())
        self.initialize_pieces()
        self.files = torrent.getFiles()
        self.completed_pieces = 0
    
    def initialize_pieces(self):
        num_of_pieces = self.torrent.getNumPieces()
        self.pieces = [Piece(idx, self.torrent.getHashPiece(idx), self.torrent.getPieceSize()) for idx in range(num_of_pieces-1)]
        total_size = self.torrent.getSize()
        last_piece_size = total_size % self.torrent.getPieceSize() if total_size % self.torrent.getPieceSize() != 0 else self.torrent.getPieceSize()
        self.pieces.append(Piece(num_of_pieces-1, self.torrent.getHashPiece(num_of_pieces-1), last_piece_size))

class Piece():
    def __init__(self, piece_index, piece_hash, piece_size):
        self.piece_index = piece_index
        self.piece_hash = piece_hash
        self.piece_size = piece_size
        self.num_blocks = int(math.ceil(float(piece_size) / BLOCK_SIZE))
        self.initialize_blocks()
        self.complete = False
        self.data = b''
        self.files = []

    def initialize_blocks(self):
        self.blocks = [Block() for x in range(self.num_blocks-1)]
        last_block_size = self.piece_size % BLOCK_SIZE if self.piece_size % BLOCK_SIZE != 0 else BLOCK_SIZE
        self.blocks.append(Block(last_block_size))

    def flush(self):
        self.data = b''
        for block in self.blocks:
            block.flush()

    def getBlock(self, begin, block_length):
        return self.data[begin:block_length]
        
    def getEmptyBlock(self):
        if self.complete:
            return None

        for idx, block in enumerate(self.blocks):
            if block.state == State.FREE:
                block.state = State.PENDING
                block.last_seen = time.time()
                return self.piece_index, idx * BLOCK_SIZE, block.size
        return None

    def setBlock(self, begin, block_data, block_length):
        block_index = math.ceil(begin / BLOCK_SIZE)
        if self.blocks[block_index].state != State.COMPLETE and self.blocks[block_index].size == block_length:
            self.blocks[block_index].data += block_data
            self.blocks[block_index].state = State.COMPLETE

    def updateBlockStatus(self):
        for block in self.blocks:
            if block.state == State.PENDING and time.time() - block.last_seen > 5:
                block.flush()

    def isComplete(self):
        if not self.complete:
            for block in self.blocks:
                if block.state != State.COMPLETE:
                    return False
            data = b''.join([block.data for block in self.blocks])
            if hashlib.sha1(data).digest() != self.piece_hash:
                self.flush()
                return False
            self.complete = True
            self.data = data
            self.writePieceData()

        else:
            return True

    def writePieceData(self):
        print(f'---\ndata has been written from piece_idx {self.piece_index}!\n---')