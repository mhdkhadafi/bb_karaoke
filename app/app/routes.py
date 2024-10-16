# app/routes.py

from flask import current_app as app
from flask import render_template, request, redirect, url_for, jsonify
from app.track_downloader import search_spotify
from .models import SongQueue
from .tasks import process_queue_if_not_running
from .extensions import db
import os
from fuzzywuzzy import process

# Homepage with search bar
@app.route('/', methods=['GET', 'POST'])
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

# Add a song to the download queue
@app.route('/add_to_queue', methods=['POST'])
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

    # Start processing the queue if not already running
    process_queue_if_not_running()

    return redirect(url_for('queue'))

# Display the download queue
@app.route('/queue')
def queue():
    songs_in_queue = SongQueue.query.order_by(SongQueue.timestamp).all()
    return render_template('queue.html', songs_in_queue=songs_in_queue)

# Remove a song from the download queue
@app.route('/remove_from_queue/<int:song_id>', methods=['POST'])
def remove_from_queue(song_id):
    song = SongQueue.query.get(song_id)
    if song:
        db.session.delete(song)
        db.session.commit()
    return redirect(url_for('queue'))

# Check the progress of a song
@app.route('/progress/<int:song_id>')
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
    songs = []
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for file in files:
            if file.endswith('.mp4'):  # Assuming karaoke files are .mp4
                song_name = os.path.splitext(file)[0]
                artist_name = root.split(os.sep)[-2]  # Assuming folder structure <artist>/<album>/<song.mp4>
                album_name = root.split(os.sep)[-1]
                songs.append({
                    'song_name': song_name,
                    'artist_name': artist_name,
                    'album_name': album_name,
                    'path': os.path.join(root, file)
                })
    
    # Perform fuzzy search
    if query:
        results = process.extract(query, [song['song_name'] for song in songs], limit=limit)
        # Filter the best matches and return relevant song information
        best_matches = [song for song_name, score in results if score > 80 for song in songs if song['song_name'] == song_name]
        return best_matches
    return []