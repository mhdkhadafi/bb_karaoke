# app/utils.py

from extensions import db
from .models import AvailableSong, SongQueue
from fuzzywuzzy import process, fuzz

def update_song_progress(song_id, progress, status):
    song = SongQueue.query.get(song_id)
    if song:
        song.progress = progress
        song.status = status
        db.session.commit()

def search_songs(query, limit=10):
    if not query:
        return []

    query = query.lower()

    results = []

    for song in AvailableSong.query.all():
        artist = song.artist.lower()
        album = song.album.lower()
        song_name = song.song_name.lower()

        # Calculate individual fuzzy scores
        artist_score = fuzz.token_sort_ratio(query, artist)
        album_score = fuzz.token_sort_ratio(query, album)
        song_name_score = fuzz.token_sort_ratio(query, song_name)
        combined_score = fuzz.token_sort_ratio(query, f"{artist} {album} {song_name}")

        # Max score among the fields
        score = max(artist_score, album_score, song_name_score, combined_score)

        # Append to results
        results.append({
            'id': song.id,
            'song_name': song.song_name,
            'artist_name': song.artist,
            'album_name': song.album,
            's3_key': song.s3_key,
            'score': score
        })

    # Filter out low scores
    min_score = 50  # Adjust based on testing
    filtered_results = [r for r in results if r['score'] >= min_score]

    # Sort and limit
    best_matches = sorted(filtered_results, key=lambda x: x['score'], reverse=True)[:limit]

    return best_matches
