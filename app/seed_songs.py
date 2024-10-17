import boto3
from botocore.exceptions import NoCredentialsError
import re
from app import create_app
from app.models import AvailableSong
from extensions import db

def seed_songs_from_s3(bucket_name):
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')
    app = create_app()

    with app.app_context():
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    # Parse the key
                    match = re.match(r'(.+?)/(.+?)/(.+?) - (.+?)\.mp4', key)
                    if match:
                        artist_name = match.group(1)
                        album_name = match.group(2)
                        song_artist = match.group(3)
                        song_name = match.group(4)

                        # Avoid duplicates
                        existing_song = AvailableSong.query.filter_by(
                            artist=artist_name,
                            album=album_name,
                            song_name=song_name
                        ).first()

                        if not existing_song:
                            song = AvailableSong(
                                artist=artist_name,
                                album=album_name,
                                song_name=song_name,
                                s3_key=key
                            )
                            db.session.add(song)
                            print(f"Added song: {artist_name} - {song_name}")
                    else:
                        print(f"Could not parse key: {key}")
        db.session.commit()
        print("Database seeding completed.")

if __name__ == '__main__':
    bucket_name = 'bb-karaoke'  # Replace with your bucket name
    seed_songs_from_s3(bucket_name)