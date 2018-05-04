# Feedgrabber.py

Creates a local sqlite database to store Youtube RSS feeds and downloads new videos when requested.

Tested on Windows 7, 10 & Ubuntu 16.04

FEATURES/TODO :
- [x] Add RSS feeds
  - [ ] Validate RSS feed prior to saving
  - [x] Assist in creating RSS url from Channel ID
- [x] List all feeds
- [x] Delete feed
  - [ ] Delete multiple feeds at once
- [x] Download all new videos
  - [x] Download all new videos through Hooktube
  - [ ] Set download path
  - [ ] Set download scructure
  - [ ] Set preferred resolution/quality
  - [ ] Delete after X days
  - [ ] Delete if larger than X size
  - [x] Download videos on timer
    - [ ] Set timer duration
- [x] Import Youtube subscription feed
  - [ ] Allow user to enter file destination

- [ ] Clean up code
  - [ ] Give better names to variables
- [ ] Clean up comments
- [ ] Add proper install instructions