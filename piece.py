import os
import math
from collections import defaultdict
import time
import hashlib
import bitstring
import asyncio
from torrent import Torrent
from block import Block, BLOCK_SIZE, State

class PieceManager():
    def __init__(self, torrent : Torrent):
        self.torrent = torrent
        self.bitfield = bitstring.BitArray(torrent.getNumPieces())
        self.initialize_pieces()
        self.initialize_files()
        self.completed_pieces = 0
        self.completed_size = 0
        self.writable_piece = asyncio.Queue()
        if self.isAlreadyDone():
            self.extractDone()
    
    def initialize_pieces(self):
        num_of_pieces = self.torrent.getNumPieces()
        self.pieces = [Piece(idx, self.torrent.getHashPiece(idx), self.torrent.getPieceSize()) for idx in range(num_of_pieces-1)]
        total_size = self.torrent.getSize()
        last_piece_size = total_size % self.torrent.getPieceSize() if total_size % self.torrent.getPieceSize() != 0 else self.torrent.getPieceSize()
        self.pieces.append(Piece(num_of_pieces-1, self.torrent.getHashPiece(num_of_pieces-1), last_piece_size))

    def initialize_files(self):
        self.files = defaultdict(list)
        piece_offset = 0
        piece_size_used = 0
        for current_file in self.torrent.raw_files:
            current_file_size = current_file['length']
            file_offset = 0
            while current_file_size > 0:
                piece_idx = int(piece_offset / self.torrent.getPieceSize())
                piece_size = self.pieces[piece_idx].piece_size - piece_size_used
                if current_file_size - piece_size < 0:
                    file_info = {
                        'path': current_file['path'],
                        'length': current_file_size,
                        'piece_offset': piece_size_used,
                        'file_offset': file_offset
                    }
                    piece_offset += current_file_size
                    file_offset += current_file_size
                    piece_size_used += current_file_size
                    current_file_size = 0
                else:
                    current_file_size -= piece_size
                    file_info = {
                        'path': current_file['path'],
                        'length': piece_size,
                        'piece_offset': piece_size_used,
                        'file_offset': file_offset
                    }
                    piece_offset += piece_size
                    file_offset += piece_size
                    piece_size_used = 0
                self.files[piece_idx].append(file_info)

    def isAlreadyDone(self):
        for file_info in self.torrent.raw_files:
            if not os.path.exists(file_info['path']):
                return False
            if os.path.getsize(file_info['path']) != file_info['length']:
                return False
        return True

    def extractDone(self):
        for piece_idx, infos in self.files.items():
            buffer = b''
            for file_info in infos:
                try:
                    f = open(file_info['path'], 'rb')
                except Exception:
                    print(f'PIECE_MAN: error extracting from done works')
                    break
                f.seek(file_info['file_offset'])
                buffer += f.read(file_info['length'])
                f.close()
            self.pieces[piece_idx].setPiece(buffer)
            self.completed_pieces += 1
            self.bitfield[piece_idx] = True
            self.completed_size += len(buffer)
            buffer = b''
        print('PIECE_MAN: Extracting done! ')

    def getPiece(self, piece_idx):
        return self.pieces[piece_idx]

    def getEmptyBlockFromPiece(self, piece_idx):
        self.pieces[piece_idx].updateBlockStatus()
        return self.getPiece(piece_idx).getEmptyBlock()
    
    def getBlock(self, idx, begin, block_length):
        if not self.getPiece(idx).complete:
            return None
        return self.getPiece(idx).getBlock(begin, block_length)

    async def receiveBlock(self, idx, begin, block, block_length):
        if self.pieces[idx].complete:
            return
        res = self.pieces[idx].setBlock(begin, block, block_length)
        if res:
            self.completed_size += block_length
            # print(f'PIECE_MAN: received piece_idx {idx}! completed size now {self.completed_size}')
        if self.pieces[idx].isComplete():
            self.completed_pieces += 1
            self.bitfield[idx] = True
            await self.writable_piece.put(self.pieces[idx])
            print(f'PIECE_MAN: piece {idx} completed!')
            if self.isComplete():
                await self.writable_piece.put(None)
    
    def isComplete(self):
        return self.completed_pieces == self.torrent.getNumPieces()

    async def writePiece(self):
        while True:
            piece = await self.writable_piece.get()
            if not piece:
                break
            for file_info in self.files[piece.piece_index]:
                try:
                    f = open(file_info['path'], 'r+b')
                except IOError:
                    f = open(file_info['path'], 'wb')
                except Exception:
                    print(f'PIECE_MAN: error writing file for piece_idx {piece.piece_index}')
                    break
                f.seek(file_info['file_offset'])
                f.write(piece.data[file_info['piece_offset'] : file_info['piece_offset']+file_info['length']])
                f.close()
                print(f'PIECE_MAN: successfully write piece {piece.piece_index} to file {file_info["path"]}')
            await asyncio.sleep(0.01)

class Piece():
    def __init__(self, piece_index: int, piece_hash: bytes, piece_size: int):
        self.piece_index = piece_index
        self.piece_hash = piece_hash
        self.piece_size = piece_size
        self.num_blocks = int(math.ceil(float(piece_size) / BLOCK_SIZE))
        self.initialize_blocks()
        self.complete = False
        self.data = b''

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
            return True
        return False
    
    def setPiece(self, data: bytes):
        if hashlib.sha1(data).digest() != self.piece_hash:
            print(f'PIECE: error set data hash mismatch')
            return False
        for block in self.blocks:
            if block.state != State.COMPLETE:
                block.state = State.COMPLETE
        self.complete = True
        self.data = data
        print(f'PIECE: Set Data for piece {self.piece_index} done!')
        return True

    def updateBlockStatus(self):
        for block in self.blocks:
            if block.state == State.PENDING and time.time() - block.last_seen > 5:
                block.flush()

    def isComplete(self):
        if not self.complete:
            for block in self.blocks:
                if block.state != State.COMPLETE:
                    # print(f'PIECE: piece {self.piece_index} still has uncompleted block')
                    return False
            data = b''.join([block.data for block in self.blocks])
            if hashlib.sha1(data).digest() != self.piece_hash:
                # print(f'PIECE: piece {self.piece_index} has different piece_hash')
                self.flush()
                return False
            self.complete = True
            self.data = data
            return True
        else:
            return True