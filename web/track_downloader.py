#!/usr/bin/env python3

import os
import subprocess
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pathlib
import requests
from app_db import update_progress
from celery_app import app as celery_app

# Authenticate with Spotify using Spotipy
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    scope="user-library-read",
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    cache_path="/app/.cache"
))

# Function to search for a song
def search_spotify(search_term):
    # Search for the song on Spotify
    results = sp.search(q=search_term, type='track', limit=5)

    # Collect the relevant track data
    tracks = []
    for track in results['tracks']['items']:
        track_info = {
            'name': track['name'],  # Song name
            'artists': track['artists'],  # List of artists (each artist has a 'name')
            'album': track['album'],  # Album info (with 'name')
            'external_urls': track['external_urls']  # Spotify URL for the track
        }
        tracks.append(track_info)

    return tracks

# Step 1: Search and download audio file using Zotify
def download_audio(spotify_url):
    # Run zotify search command as a subprocess
    result = subprocess.run(
        ['zotify', spotify_url, 
         '--download-lyrics', 'False',
         '--root-path', str(pathlib.Path().resolve()),
         '--output', 'shared/input/{artist}/{album}/{artist} - {song_name}.{ext}']
        )
    
def download_video(artist, album, song_name):
    base_path = pathlib.Path("shared/input") / artist / album
    video_file_path = base_path / f"{artist} - {song_name}.webm"

    # Skip download if the video file already exists
    if video_file_path.exists():
        print(f"Video file already exists: {video_file_path}. Skipping download.")
        return video_file_path
    
    po_token = os.getenv('PO_TOKEN')
    print(f"Downloading video for: {song_name}...")
    command = [
        "yt-dlp",
        "-f", "bestvideo[ext=webm]",
        "-o", str(video_file_path),
        "--extractor-args", f"youtube:player-client=web,default;po_token=web+{po_token}",
        "--cookies", "cookies.txt",
        f"ytsearch:{artist} {song_name}"
    ]
    subprocess.run(command)
    
    print(f"Video saved to: {video_file_path}")
    return video_file_path

# Step 3: Download lyrics using lrclib API
def download_lyrics(artist_name, album_name, song_name):
    base_path = pathlib.Path("shared/input") / artist_name / album_name
    lrc_file_path = base_path / f"{artist_name} - {song_name}.lrc"
    search_term = f"{artist_name} {song_name}"

    # Skip download if the LRC file already exists
    if lrc_file_path.exists():
        print(f"LRC file already exists: {lrc_file_path}. Skipping download.")
        return lrc_file_path

    print(f"Searching for lyrics for: {search_term}...")

    base_url = "https://lrclib.net/api"
    search_url = f"{base_url}/search"
    params = {
        "q": search_term
    }
    # Search for lyrics using lrclib API
    response = requests.get(search_url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        
        if data:
            # Get the first result's synced lyrics
            lyrics = data[0]['syncedLyrics']
            
            with open(lrc_file_path, 'w') as f:
                f.write(lyrics)
            print(f"Lyrics saved to: {lrc_file_path}")
            return lrc_file_path
        else:
            print(f"No lyrics found for: {search_term}")
            return None
    else:
        print(f"Error searching lyrics: {response.status_code} - {response.text}")
        return None

# Main function to run the full process
@celery_app.task
def run_download_process(artist_name, album_name, song_name, url):
    # artist_name, album_name, song_name, url = search_spotify(search_term)

    # # Step 1: Download audio using Zotify
    update_progress(song_name, artist_name, album_name, 1, "Downloading Audio")
    download_audio(url)

    # # Step 2: Download video using yt-dlp
    update_progress(song_name, artist_name, album_name, 2, "Downloading Video")
    download_video(artist_name, album_name, song_name)

    # Step 3: Download lyrics using lrclib
    update_progress(song_name, artist_name, album_name, 3, "Downloading Lyrics")
    download_lyrics(artist_name, album_name, song_name)

    return artist_name, album_name, song_name

# Entry point for running the script
if __name__ == "__main__":
    run_download_process()
