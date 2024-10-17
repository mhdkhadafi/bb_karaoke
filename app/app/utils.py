# app/utils.py

from extensions import db
from .models import AvailableSong, SongQueue
from fuzzywuzzy import process

def update_song_progress(song_id, progress, status):
    song = SongQueue.query.get(song_id)
    if song:
        song.progress = progress
        song.status = status
        db.session.commit()

def search_songs(query, limit=5):
    if not query:
        return []

    # Fetch all available songs
    songs = AvailableSong.query.all()

    # Prepare data for fuzzy matching
    song_data = []
    for song in songs:
        combined = f"{song.artist} {song.album} {song.song_name}"
        song_data.append((combined, song))

    # Perform fuzzy search
    results = process.extract(query, [data[0] for data in song_data], limit=limit)

    # Collect the best matches
    best_matches = []
    for match in results:
        combined_string, score = match
        for data in song_data:
            if data[0] == combined_string:
                song = data[1]
                best_matches.append({
                    'song_name': song.song_name,
                    'artist_name': song.artist,
                    'album_name': song.album,
                    's3_key': song.s3_key,
                    'score': score
                })
                break

    return best_matches