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
- [ ] ***Connect to peers**
  - [x] Make Block and Piece
  - [x] Make peer states and messages
  - [ ] Make a connection
- [ ] Make Peer Manager
- [ ] Make Pieces Manager
- [ ] Write data to disk
- [ ] Seed data
- [ ] Bonus: Making some GUI
- [ ] Bonus: implements rarest-piece-first selection strategy