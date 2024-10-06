#!/usr/bin/env python3

import web.track_downloader as track_downloader
import web.karaoke_video_maker as karaoke_video_maker
import os
import sys

def main():
    # Step 1: Get the search term from the user and run the download process
    search_term = input("Enter the song/artist/album to search for: ")
    
    # Run the download process from track_downloader.py
    artist_name, album_name, song_name = track_downloader.run_download_process(search_term)

    # Step 2: Run the karaoke creation process from karaoke_video_maker.py
    base_path = os.path.join("input", artist_name, album_name, song_name)
    
    # Pass the base path to create_karaoke function in karaoke_video_maker.py
    karaoke_video_maker.create_karaoke(base_path)

if __name__ == "__main__":
    main()
