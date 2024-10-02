import sqlite3

# Function to initialize the progress table
def init_db():
    conn = sqlite3.connect('karaoke_progress.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS progress
                 (id INTEGER PRIMARY KEY, song_name TEXT, artist_name TEXT, album_name TEXT, progress INTEGER, status TEXT)''')
    conn.commit()
    conn.close()

# Function to update the progress of a song in the database
def update_progress(song_name, artist_name, album_name, progress, status):
    conn = sqlite3.connect('karaoke_progress.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO progress (song_name, artist_name, album_name, progress, status)
                 VALUES (?, ?, ?, ?, ?)''', (song_name, artist_name, album_name, progress, status))
    conn.commit()
    conn.close()
