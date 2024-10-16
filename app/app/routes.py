# app/routes.py

from track_downloader import search_spotify
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from .models import SongQueue
from extensions import db
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=['GET', 'POST'])
def index():
    search_results = []
    spotify_results = []

    if request.method == 'POST' and 'search' in request.form:
        search_query = request.form.get('search')
        search_results = search_songs(search_query)

    if request.method == 'POST' and 'search_internet' in request.form:
        search_query = request.form.get('search_internet')
        spotify_results = search_spotify(search_query)

    return render_template('index.html', search_results=search_results, spotify_results=spotify_results)

@main_bp.route('/add_to_queue', methods=['POST'])
def add_to_queue():
    song = SongQueue(
        name=request.form['song_name'],
        artist=request.form['artist_name'],
        album=request.form['album_name'],
        spotify_url=request.form['spotify_url'],
        status='queued'
    )
    db.session.add(song)
    db.session.commit()

    # Import within the function to avoid circular import
    from .tasks import process_queue_if_not_running
    process_queue_if_not_running()

    return redirect(url_for('main.queue'))

@main_bp.route('/queue')
def queue():
    songs_in_queue = SongQueue.query.order_by(SongQueue.timestamp).all()
    return render_template('queue.html', songs_in_queue=songs_in_queue)

@main_bp.route('/remove_from_queue/<int:song_id>', methods=['POST'])
def remove_from_queue(song_id):
    song = SongQueue.query.get(song_id)
    if song:
        db.session.delete(song)
        db.session.commit()
    return redirect(url_for('main.queue'))

@main_bp.route('/progress/<int:song_id>')
def progress(song_id):
    song = SongQueue.query.get(song_id)
    if song:
        progress = song.progress or 0
        status = song.status or 'unknown'
        return jsonify({'progress': progress, 'status': status})
    else:
        return jsonify({'progress': 0, 'status': 'unknown'})

def search_songs(query, limit=5):
    # Collect all songs in the output directory
    pass