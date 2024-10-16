# app/utils.py

from extensions import db
from .models import SongQueue

def update_song_progress(song_id, progress, status):
    song = SongQueue.query.get(song_id)
    if song:
        song.progress = progress
        song.status = status
        db.session.commit()
