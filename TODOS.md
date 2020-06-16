# TODO LIST
### Goal: Asynchronous single-threaded bittorrent client

- [x] Read torrent file
  - [x] Decode torrent file
  - [x] Decode pieces, check hash
  - [x] Getter and Setter of Torrent class
  - [x] Include some necessary torrent related methods
- [ ] ***Make tracker request**
  - [ ] Create request messages
  - [ ] Decode response messages
- [ ] Connect to peers
  - [ ] Make peer states and messages
  - [ ] Make a connection
- [ ] Make blocks and pieces manager
- [ ] Write data to disk
- [ ] Seed data
- [ ] Bonus: Making some GUI
- [ ] Bonus: implements rarest-piece-first selection strategy