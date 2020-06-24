import math
import time
import hashlib
import bitstring
from block import Block, BLOCK_SIZE, State

class Piece():
    def __init__(self, piece_index, piece_hash, piece_size):
        self.piece_index = piece_index
        self.piece_hash = piece_hash
        self.piece_size = piece_size
        self.num_blocks = int(math.ceil(float(piece_size) / BLOCK_SIZE))
        self.downloaded_blocks = bitstring.BitArray(self.num_blocks)
        self.initialize_blocks()
        self.complete = False

    def initialize_blocks(self):
        self.blocks = [Block() for x in range(self.num_blocks-1)]
        last_block_size = self.piece_size % BLOCK_SIZE
        self.blocks.append(Block(last_block_size))

    def flush(self):
        for block in self.blocks:
            block.flush()
        
    def getEmptyBlock(self):
        if self.complete:
            return None

        for idx, block in enumerate(self.blocks):
            if block.state == State.FREE:
                block.state = State.PENDING
                block.last_seen = time.time()
                return self.piece_index, idx * BLOCK_SIZE, block.size
        return None

    def isComplete(self):
        if not self.complete:
            for block in self.blocks:
                if block.state == State.FREE or block.state == State.PENDING:
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
        pass