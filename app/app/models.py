from extensions import db
from datetime import datetime
from extensions import db

class SongQueue(db.Model):
    __tablename__ = 'song_queue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255), nullable=False)
    album = db.Column(db.String(255), nullable=False)
    spotify_url = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='queued')
    progress = db.Column(db.Integer, default=0)  # Progress from 0 to 100
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AvailableSong(db.Model):
    __tablename__ = 'available_songs'

    id = db.Column(db.Integer, primary_key=True)
    artist = db.Column(db.String(255), nullable=False)
    album = db.Column(db.String(255), nullable=False)
    song_name = db.Column(db.String(255), nullable=False)
    s3_key = db.Column(db.String(255), nullable=False)  # S3 object key
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class PlaylistSong(db.Model):
    __tablename__ = 'playlist_songs'

    id = db.Column(db.Integer, primary_key=True)
    song_id = db.Column(db.Integer, db.ForeignKey('available_songs.id'), nullable=False)
    song_name = db.Column(db.String(255), nullable=False)
    artist_name = db.Column(db.String(255), nullable=False)
    album_name = db.Column(db.String(255), nullable=False)
    position = db.Column(db.Integer, nullable=False)

    song = db.relationship('AvailableSong', backref='playlist_entries')
