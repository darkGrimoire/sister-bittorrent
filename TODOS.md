# TODO LIST
### Goal: Asynchronous single-threaded bittorrent client

- [x] Read torrent file
  - [x] Decode torrent file
  - [x] Decode pieces, check hash
  - [x] Getter and Setter of Torrent class
  - [x] Include some necessary torrent related methods
- [x] Make tracker request
  - [x] Create request messages
  - [x] Decode response messages
- [x] Connect to peers
  - [x] Make Block and Piece
  - [x] Make peer states and messages
  - [x] Make a connection
- [x] Make Pieces Manager
- [x] Make Peer Manager
  - [x] Make download and upload loops
  - [x] Make message listeners
  - [x] Can receive pieces in memory
- [ ] Write data to disk
  - [x] Design FileSaver Scheme
  - [ ] Write completed piece
- [ ] Seed data
- [ ] Bonus: Making some GUI
- [ ] Bonus: implements rarest-piece-first selection strategy