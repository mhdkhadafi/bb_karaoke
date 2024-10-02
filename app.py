from flask import Flask, request, render_template, redirect, url_for
import os
from fuzzywuzzy import process
from track_downloader import search_spotify, run_download_process
from karaoke_video_maker import create_karaoke
from app_db import update_progress, init_db
import sqlite3

app = Flask(__name__)
init_db()

# In-memory queue to store songs
download_queue = []

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
    song = {
        'name': request.form['song_name'],
        'artist': request.form['artist_name'],
        'album': request.form['album_name'],
        'spotify_url': request.form['spotify_url']
    }
    download_queue.append(song)
    
    # Start processing the queue automatically if there's at least one song
    if download_queue:
        process_queue()

    return redirect(url_for('queue'))

# Display the download queue
@app.route('/queue')
def queue():
    return render_template('queue.html', download_queue=download_queue)

# Remove a song from the download queue
@app.route('/remove_from_queue/<int:index>', methods=['POST'])
def remove_from_queue(index):
    if 0 <= index < len(download_queue):
        download_queue.pop(index)
    return redirect(url_for('queue'))

@app.route('/progress/<song_name>/<artist_name>/<album_name>', methods=['GET'])
def get_progress(song_name, artist_name, album_name):
    conn = sqlite3.connect('karaoke_progress.db')
    c = conn.cursor()
    c.execute('''SELECT progress, status FROM progress WHERE song_name = ? AND artist_name = ? AND album_name = ?''',
              (song_name, artist_name, album_name))
    result = c.fetchone()
    conn.close()

    if result:
        return {'progress': result[0], 'status': result[1]}
    else:
        return {'progress': 0, 'status': 'Not Started'}

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

# Function to process the queue automatically
def process_queue():
    while download_queue:
        # Get the first song from the queue
        song = download_queue[0]
        artist_name = song['artist']
        album_name = song['album']
        song_name = song['name']
        url = song['spotify_url']

        try:
            # Step 1: Download the song
            run_download_process(artist_name, album_name, song_name, url)

            # Step 2: Create the karaoke video
            create_karaoke(artist_name, album_name, song_name)

            update_progress(song_name, artist_name, album_name, 10, "Completed")

            # Remove the song from the queue after processing
            download_queue.pop(0)

        except Exception as e:
            print(f"Error processing the song: {e}")
            break  # Stop processing on error

if __name__ == '__main__':
    app.run(debug=True)
