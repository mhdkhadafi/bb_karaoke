from extensions import db
from datetime import datetime

class SongQueue(db.Model):
    __tablename__ = 'song_queue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255), nullable=False)
    album = db.Column(db.String(255), nullable=False)
    spotify_url = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='queued')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
