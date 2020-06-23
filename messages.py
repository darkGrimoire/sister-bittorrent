import struct
import bitstring

class WrongMessageException(Exception):
    pass

class Message():
    def writeMessage(self):
        raise NotImplementedError()

    @classmethod
    def readMessage(cls, payload):
        raise NotImplementedError()

    @staticmethod
    def determineMessage(payload):
        try:
            message_id = struct.unpack('>I', payload[4:5])[0]
        except:
            print('Unpack message error')
            return None
        
        translate_id = {
            0: Choke,
            1: UnChoke,
            2: Interested,
            3: NotInterested,
            4: Have,
            5: BitField,
            6: Request,
            7: Piece,
            8: Cancel,
            9: Port
        }

        if message_id not in translate_id:
            raise WrongMessageException("Message Type not supported!")
        return translate_id[message_id].readMessage(payload)

class KeepAlive(Message):
    msg_len = 0

    total_bytes = 4

    def writeMessage(self) -> bytes:
        return struct.pack('>I', msg_len)
    
    @classmethod
    def readMessage(cls, payload):
        payload_len = struct.unpack('>I', payload[:cls.total_bytes])[0]
        if payload_len != cls.msg_len:
            raise WrongMessageException("Not a keep-alive messsage!")
        return cls()
    
class Choke(Message):
    msg_len = 1
    msg_id = 0

    total_bytes = 5

    def writeMessage(self) -> bytes:
        return struct.pack('>IB', msg_len, msg_id)
    
    @classmethod
    def readMessage(cls, payload):
        payload_len, payload_id = struct.unpack('>IB', payload[:cls.msg_len])
        if (payload_len != cls.msg_len or payload_id != cls.msg_id):
            raise WrongMessageException("Not a Choke message!")
        return cls()

class UnChoke(Message):
    msg_len = 1
    msg_id = 1

    total_bytes = 5

    def writeMessage(self) -> bytes:
        return struct.pack('>IB', msg_len, msg_id)
    
    @classmethod
    def readMessage(cls, payload):
        payload_len, payload_id = struct.unpack('>IB', payload[:cls.msg_len])
        if (payload_len != cls.msg_len or payload_id != cls.msg_id):
            raise WrongMessageException("Not an UnChoke message!")
        return cls()

class Interested(Message):
    msg_len = 1
    msg_id = 2
    
    total_bytes = 5

    def writeMessage(self) -> bytes:
        return struct.pack('>IB', msg_len, msg_id)
    
    @classmethod
    def readMessage(cls, payload):
        payload_len, payload_id = struct.unpack('>IB', payload[:cls.msg_len])
        if (payload_len != cls.msg_len or payload_id != cls.msg_id):
            raise WrongMessageException("Not an Interested message!")
        return cls()

class NotInterested(Message):
    msg_len = 1
    msg_id = 3
    
    total_bytes = 4

    def writeMessage(self) -> bytes:
        return struct.pack('>IB', msg_len, msg_id)
    
    @classmethod
    def readMessage(cls, payload):
        payload_len, payload_id = struct.unpack('>IB', payload[:cls.msg_len])
        if (payload_len != cls.msg_len or payload_id != cls.msg_id):
            raise WrongMessageException("Not an NotInterested message!")
        return cls()

class Have(Message):
    msg_len = 5
    msg_id = 4
    
    total_bytes = 9

    def __init__(self, piece_idx):
        self.piece_idx = piece_idx

    def writeMessage(self) -> bytes:
        return struct.pack('>IBI', msg_len, msg_id, self.piece_idx)
    
    @classmethod
    def readMessage(cls, payload):
        payload_len, payload_id, payload_idx = struct.unpack('>IBI', payload[:cls.msg_len])
        if (payload_len != cls.msg_len or payload_id != cls.msg_id):
            raise WrongMessageException("Not a Have message!")
        return cls(payload_idx)

class BitField(Message):
    msg_id = 5

    def __init__(self, bitfield):
        self.bitfield = bitfield.tobytes()
        self.msg_len = 1 + len(self.bitfield)
        self.total_bytes = 4 + self.msg_len

    def writeMessage(self) -> bytes:
        return struct.pack(f'>IB{len(self.bitfield)}s', self.msg_len, msg_id, self.bitfield)
    
    @classmethod
    def readMessage(cls, payload):
        payload_len, payload_id = struct.unpack('>IB', payload[:5])
        payload_bitfield_raw = struct.unpack(f'>{payload_len-1}s', payload[5:5+payload_len-1])[0]
        if payload_id != cls.msg_id:
            raise WrongMessageException("Not a BitField message!")
        payload_bitfield = bitstring.BitArray(bytes=bytes(payload_bitfield_raw))
        return cls(payload_bitfield)

class Request(Message):
    msg_len = 13
    msg_id = 6
    
    total_bytes = 17

    def __init__(self, idx, begin, length):
        self.idx = idx
        self.begin = begin
        self.length = length

    def writeMessage(self) -> bytes:
        return struct.pack('>IBIII', msg_len, msg_id, self.idx, self.begin, self.length)
    
    @classmethod
    def readMessage(cls, payload):
        payload_len, payload_id, payload_idx, payload_begin, payload_length = struct.unpack('>IBIII', payload[:cls.msg_len])
        if (payload_len != cls.msg_len or payload_id != cls.msg_id):
            raise WrongMessageException("Not a Request message!")
        return cls(payload_idx, payload_begin, payload_length)

class Piece(Message):
    msg_id = 7

    def __init__(self, idx, begin, block, block_length):
        self.idx = idx
        self.begin = begin
        self.block = block
        self.block_length = block_length
        self.msg_len = 9 + block_length
        self.total_bytes = 4 + msg_len

    def writeMessage(self) -> bytes:
        return struct.pack(f'>IBII{self.block_length}s', self.msg_len, msg_id, self.idx, self.begin, self.block)
    
    @classmethod
    def readMessage(cls, payload):
        payload_block_length = len(payload) - 13
        payload_len, payload_id, payload_idx, payload_begin, payload_block = struct.unpack(f'>IBII{payload_block_length}s', payload[:13 + block_length])
        if (payload_len != cls.msg_len or payload_id != cls.msg_id):
            raise WrongMessageException("Not a Piece message!")
        return cls(payload_idx, payload_begin, payload_block, payload_block_length)

class Cancel(Message):
    msg_len = 13
    msg_id = 8
    total_bytes = 17

    def __init__(self, idx, begin, length):
        self.idx = idx
        self.begin = begin
        self.length = length

    def writeMessage(self) -> bytes:
        return struct.pack('>IBIII', msg_len, msg_id, self.idx, self.begin, self.length)
    
    @classmethod
    def readMessage(cls, payload):
        payload_len, payload_id, payload_idx, payload_begin, payload_length = struct.unpack('>IBIII', payload[:cls.msg_len])
        if (payload_len != cls.msg_len or payload_id != cls.msg_id):
            raise WrongMessageException("Not a Cancel message!")
        return cls(payload_idx, payload_begin, payload_length)
    
class Port(Message):
    msg_len = 3
    msg_id = 9
    
    total_bytes = 9

    def __init__(self, port):
        self.port = port

    def writeMessage(self) -> bytes:
        return struct.pack('>IBI', msg_len, msg_id, self.port)
    
    @classmethod
    def readMessage(cls, payload):
        payload_len, payload_id, payload_port = struct.unpack('>IBI', payload[:cls.msg_len])
        if (payload_len != cls.msg_len or payload_id != cls.msg_id):
            raise WrongMessageException("Not a Port message!")
        return cls(payload_port)