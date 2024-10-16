from flask import Flask, request, render_template, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from extensions import db
from flask_migrate import Migrate
import os
from fuzzywuzzy import process
from track_downloader import search_spotify, run_download_process
from karaoke_video_maker import create_karaoke
from app_db import update_progress, init_db
import sqlite3
from celery_app import celery_app
from models import SongQueue

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URL')  # From environment variables
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database and migration objects
db.init_app(app)
migrate = Migrate(app, db)

# Import your models
from models import SongQueue

# Set up the path where the output files are stored
OUTPUT_DIR = "output"

# Step 1: Define the route for the homepage with the search bar
@app.route('/', methods=['GET', 'POST'])
def index():
    search_results = []
    spotify_results = []

    # Local search (POST request)
    if request.method == 'POST' and 'search' in request.form:
        search_query = request.form.get('search')
        search_results = search_songs(search_query)
    
    # Spotify search (POST request from "Search the Internet" button)
    if request.method == 'POST' and 'search_internet' in request.form:
        search_query = request.form.get('search_internet')
        spotify_results = search_spotify(search_query)

    return render_template('index.html', search_results=search_results, spotify_results=spotify_results)

# Add a song to the download queue from the Spotify results
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
    # Fetch all songs from the SongQueue table
    # You can filter based on status if needed
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

@app.route('/progress/<int:song_id>')
def progress(song_id):
    song = SongQueue.query.get(song_id)
    if song:
        # Assuming you have a way to calculate progress based on song status
        # You might store progress as a separate field in the SongQueue model
        # For this example, we'll use a simple mapping
        status_progress_map = {
            'queued': 0,
            'processing': 50,
            'completed': 100,
            'failed': 0
        }
        progress = status_progress_map.get(song.status, 0)
        return jsonify({'progress': progress, 'status': song.status})
    else:
        return jsonify({'progress': 0, 'status': 'unknown'})

# Step 2: Fuzzy search function to find matching songs
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

def process_queue_if_not_running():
    # Check if any song is currently being processed
    processing_song = SongQueue.query.filter_by(status='processing').first()
    queued_song = SongQueue.query.filter_by(status='queued').first()
    if not processing_song and queued_song:
        process_queue.delay()

# Task to pop the song from the queue after the tasks complete
@celery_app.task
def update_song_status(song_id):
    song = SongQueue.query.get(song_id)
    if song:
        song.status = 'completed'
        db.session.commit()

    # Check for next song and process
    process_queue.delay()

@celery_app.task
def mark_song_as_failed(request, exc, traceback, song_id):
    song = SongQueue.query.get(song_id)
    if song:
        song.status = 'failed'
        db.session.commit()

    # Proceed to next song
    process_queue_if_not_running()

# Function to process the queue automatically
@celery_app.task(name='process_queue')
def process_queue():
    song = SongQueue.query.filter_by(status='queued').order_by(SongQueue.timestamp).first()
    if song:
        # Update status to 'processing'
        song.status = 'processing'
        db.session.commit()

        # Extract song details
        artist_name = song.artist
        album_name = song.album
        song_name = song.name
        url = song.spotify_url

        # Create the task chain
        chain = (
            run_download_process.s(artist_name, album_name, song_name, url) |
            create_karaoke.si(artist_name, album_name, song_name) |
            update_song_status.si(song.id)
        )

        # Link error handling
        chain.link_error(mark_song_as_failed.s(song.id))

        # Start the task chain
        chain.apply_async()
    else:
        # Queue is empty, do nothing
        pass

if __name__ == '__main__':
    app.run(debug=True)
