import os
import shutil
import tempfile
from celery_app import celery_app
from .models import SongQueue
from extensions import db
from app.utils import update_song_progress
from app.track_downloader import download_audio, download_video, download_lyrics
from app.karaoke_video_maker import create_video, lrc_to_srt, remove_vocals, split_srt_to_two
from app.aws_helpers import upload_to_s3

@celery_app.task(name='process_queue')
def process_queue():
    song = SongQueue.query.filter_by(status='queued').order_by(SongQueue.timestamp).first()
    if song:
        song.status = 'processing'
        song.progress = 0
        db.session.commit()

        artist_name = song.artist
        album_name = song.album
        song_name = song.name
        url = song.spotify_url

        chain = (
            run_download_process.s(song.id, artist_name, album_name, song_name, url) |
            create_karaoke.s(song.id, artist_name, album_name, song_name) |
            update_song_status.s(song.id)
        )

        chain.link_error(mark_song_as_failed.s(song.id))
        chain.apply_async()
    else:
        pass

@celery_app.task
def run_download_process(song_id, artist_name, album_name, song_name, url):
    update_song_progress(song_id, progress=10, status='Downloading Audio')
    download_audio(url)

    update_song_progress(song_id, progress=30, status='Downloading Video')
    download_video(artist_name, album_name, song_name)

    update_song_progress(song_id, progress=50, status='Downloading Lyrics')
    download_lyrics(artist_name, album_name, song_name)

    return artist_name, album_name, song_name

@celery_app.task
def create_karaoke(song_id, artist_name, album_name, song_name):
    input_folder = os.path.join("shared", "input", artist_name, album_name)
    video_file = os.path.join(input_folder, f"{artist_name} - {song_name}.webm")
    audio_file = os.path.join(input_folder, f"{artist_name} - {song_name}.ogg")
    lrc_file = os.path.join(input_folder, f"{artist_name} - {song_name}.lrc")

    if not all([os.path.exists(video_file), os.path.exists(audio_file), os.path.exists(lrc_file)]):
        update_song_progress(song_id, progress=0, status="Failed")
        raise FileNotFoundError("One or more input files are missing (webm, ogg, lrc).")

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Remove vocals
            update_song_progress(song_id, progress=60, status="Removing Vocals")
            accompaniment_file = os.path.join(temp_dir, "accompaniment.wav")
            remove_vocals(audio_file, temp_dir, accompaniment_file)

            # Convert lrc to srt
            update_song_progress(song_id, progress=70, status="Converting Lyrics")
            srt_file = os.path.join(temp_dir, "subtitles.srt")
            lrc_to_srt(lrc_file, srt_file)

            # Split srt
            update_song_progress(song_id, progress=75, status="Splitting Subtitles")
            main_srt_file = os.path.join(temp_dir, "main.srt")
            after_srt_file = os.path.join(temp_dir, "after.srt")
            split_srt_to_two(srt_file, main_srt_file, after_srt_file)

            # Create video
            update_song_progress(song_id, progress=80, status="Creating Video")
            output_file = os.path.join(temp_dir, f"{artist_name} - {song_name}.mp4")
            create_video(
                video_file,
                audio_with_vocals=audio_file,
                audio_without_vocals=accompaniment_file,
                main_srt=main_srt_file,
                after_srt=after_srt_file,
                output_file=output_file
            )

            # Upload to S3
            update_song_progress(song_id, progress=90, status="Uploading to S3")
            s3_file_name = f"{artist_name}/{album_name}/{artist_name} - {song_name}.mp4"
            upload_to_s3(output_file, bucket_name='your-bucket-name', s3_file_name=s3_file_name)

            # Clean up input files
            update_song_progress(song_id, progress=95, status="Cleaning Up")
            shutil.rmtree(input_folder)

            # Update status to completed
            update_song_progress(song_id, progress=100, status="Completed")
        except Exception as e:
            update_song_progress(song_id, progress=0, status="Failed")
            raise e


@celery_app.task
def update_song_status(song_id):
    song = SongQueue.query.get(song_id)
    if song:
        song.status = 'completed'
        song.progress = 100
        db.session.commit()
    process_queue.delay()

@celery_app.task
def mark_song_as_failed(request, exc, traceback, song_id):
    song = SongQueue.query.get(song_id)
    if song:
        song.status = 'failed'
        db.session.commit()
    process_queue.delay()