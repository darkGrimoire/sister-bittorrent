import time
BLOCK_SIZE = 2**14

class State(Enum):
    FREE = 0
    PENDING = 1
    COMPLETE = 2

class Block():
    def __init__(self, size=BLOCK_SIZE):
        self.state = State.FREE
        self.last_seen = 0
        self.size = size
        self.data = b''

    def flush(self):
        self.data = b''
        self.state = State.FREE
