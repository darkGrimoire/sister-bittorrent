from block import Block

class Piece():
    def __init__(self, piece_index, piece_hash):
        self.piece_index = piece_index
        self.piece_hash = piece_hash
        self.block_lists = [Block]