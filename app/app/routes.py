# app/routes.py

from track_downloader import search_spotify
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from .models import PlaylistSong, SongQueue, AvailableSong
from .utils import search_songs
from .tasks import process_queue
from sqlalchemy import func
from math import ceil
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
    songs_in_queue = SongQueue.query.filter(
        SongQueue.status.not_in(['completed', 'Completed'])
    ).order_by(SongQueue.timestamp).all()
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

@main_bp.route('/test_celery')
def test_celery():
    result = process_queue.apply_async()
    return f"Task dispatched: {result.id}"

@main_bp.route('/song_list', methods=['GET'])
def song_list():
    # Get query parameters
    view_type = request.args.get('view', 'song')  # 'song' or 'artist'
    letter = request.args.get('letter', 'A')      # Default to 'A'
    page = request.args.get('page', 1, type=int)  # Pagination

    # Define letters for navigation
    letters = [chr(i) for i in range(65, 91)]  # 'A' to 'Z'
    letters.append('#')  # Non-alphabetic

    per_page = 20  # Number of items per page

    if view_type == 'artist':
        # Fetch distinct artist names starting with the selected letter
        if letter == '#':
            # Artists starting with non-alphabetic characters
            artists_query = AvailableSong.query \
                .filter(func.substr(func.lower(AvailableSong.artist), 1, 1).notin_([chr(i).lower() for i in range(97, 123)])) \
                .with_entities(AvailableSong.artist) \
                .distinct()
        else:
            # Artists starting with the selected letter
            artists_query = AvailableSong.query \
                .filter(func.substr(func.lower(AvailableSong.artist), 1, 1) == letter.lower()) \
                .with_entities(AvailableSong.artist) \
                .distinct()

        total_artists = artists_query.count()
        total_pages = ceil(total_artists / per_page)
        artists = artists_query.order_by(AvailableSong.artist).offset((page - 1) * per_page).limit(per_page).all()

        # For each artist, get their songs
        songs = {}
        for artist_tuple in artists:
            artist_name = artist_tuple[0]
            artist_songs = AvailableSong.query.filter_by(artist=artist_name).order_by(AvailableSong.song_name).all()
            songs[artist_name] = artist_songs

        return render_template('song_list.html',
                               view_type=view_type,
                               letter=letter,
                               letters=letters,
                               page=page,
                               total_pages=total_pages,
                               songs=songs)
    else:
        # View by song
        if letter == '#':
            # Songs starting with non-alphabetic characters
            songs_query = AvailableSong.query \
                .filter(func.substr(func.lower(AvailableSong.song_name), 1, 1).notin_([chr(i).lower() for i in range(97, 123)]))
        else:
            # Songs starting with the selected letter
            songs_query = AvailableSong.query \
                .filter(func.substr(func.lower(AvailableSong.song_name), 1, 1) == letter.lower())

        total_songs = songs_query.count()
        total_pages = ceil(total_songs / per_page)
        songs = songs_query.order_by(AvailableSong.song_name).offset((page - 1) * per_page).limit(per_page).all()

        return render_template('song_list.html',
                               view_type=view_type,
                               letter=letter,
                               letters=letters,
                               page=page,
                               total_pages=total_pages,
                               songs=songs)

# Display the playlist
@main_bp.route('/playlist')
def playlist():
    # Fetch songs in the playlist ordered by their position
    playlist_songs = PlaylistSong.query.order_by(PlaylistSong.position).all()
    return render_template('playlist.html', playlist_songs=playlist_songs)

# Add a song to the playlist
@main_bp.route('/add_to_playlist', methods=['POST'])
def add_to_playlist():
    song_id = request.form.get('song_id')
    if song_id:
        # Fetch the song from AvailableSong
        song = AvailableSong.query.get(song_id)
        if song:
            # Determine the next position
            max_position = db.session.query(db.func.max(PlaylistSong.position)).scalar()
            next_position = (max_position or 0) + 1

            # Create a new PlaylistSong entry
            playlist_song = PlaylistSong(
                song_id=song.id,
                song_name=song.song_name,
                artist_name=song.artist,
                album_name=song.album,
                position=next_position
            )
            db.session.add(playlist_song)
            db.session.commit()
    return redirect(url_for('main.playlist'))

# Remove a song from the playlist
@main_bp.route('/remove_from_playlist/<int:playlist_song_id>', methods=['POST'])
def remove_from_playlist(playlist_song_id):
    playlist_song = PlaylistSong.query.get(playlist_song_id)
    if playlist_song:
        db.session.delete(playlist_song)
        db.session.commit()
    return redirect(url_for('main.playlist'))

# Update the playlist order
@main_bp.route('/update_playlist_order', methods=['POST'])
def update_playlist_order():
    order = request.json.get('order')
    if order:
        for idx, playlist_song_id in enumerate(order):
            playlist_song = PlaylistSong.query.get(playlist_song_id)
            if playlist_song:
                playlist_song.position = idx
        db.session.commit()
    return jsonify({'status': 'success'})