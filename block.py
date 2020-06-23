class Block():
    def __init__(self, piece, index, size):
        self.piece = piece
        self.index = index
        self.size = size
        self.data = b''

    def flush(self):
        self.data = b''
