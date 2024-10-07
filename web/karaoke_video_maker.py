#!/usr/bin/env python3

import moviepy.editor as mp
from pydub import AudioSegment
import pysrt
import subprocess
import os
import re
import sys
from app_db import update_progress
import requests
from celery_app import app as celery_app
import time

def rename_file_without_special_chars(file_path):
    # Replace problematic characters (e.g., single quotes)
    new_file_path = file_path.replace("'", "")
    return new_file_path

# Step 1: Remove audio from .webm file
def remove_audio(video_path):
    video = mp.VideoFileClip(video_path)
    video_without_audio = video.without_audio()
    return video_without_audio

def remove_vocals(audio_path, accompaniment_file):
    spleeter_api_url = "http://spleeter:5001/split"
    response = requests.post(spleeter_api_url, json={"file_path": audio_path, "accompaniment_file": accompaniment_file})

    if response.status_code == 200:
        print("Spleeter separation successful! Waiting for the output file...")
        
        # Wait for the accompaniment file to be created (polling)
        for _ in range(60):  # Wait for up to 60 seconds
            if os.path.exists(accompaniment_file):
                return accompaniment_file
            time.sleep(1)  # Wait for 1 second before checking again
        
        raise Exception(f"Accompaniment file not found: {accompaniment_file}")
    else:
        raise Exception(f"Spleeter error: {response.json().get('error')}")

def remove_vocals_2(input_file, output_folder):
    command = [
        "docker", "run", "--rm",
        "-v", f"{input_file}:/app/input",
        "-v", f"{output_folder}:/app/output",
        "deezer/spleeter", "separate", "-i", "/app/input", "-o", "/app/output"
    ]
    subprocess.run(command, check=True)

# Step 2: Add .ogg audio to the video
def add_audio(video_file, audio_with_vocals, audio_without_vocals, output_file):
    command = [
        'ffmpeg',
        '-i', video_file,                     # Input video
        '-i', audio_with_vocals,              # First audio track (with vocals)
        '-i', audio_without_vocals,           # Second audio track (without vocals)
        '-map', '0:v',                        # Map video stream
        '-map', '1:a',                        # Map first audio stream
        '-map', '2:a',                        # Map second audio stream
        '-c:v', 'copy',                       # Copy video stream without re-encoding
        '-c:a', 'aac',                        # Encode audio to AAC
        '-strict', 'experimental',            # Enable experimental features for aac
        '-shortest',                          # Make sure the video and audio streams match length
        output_file                           # Output file
    ]
    
    subprocess.run(command, check=True)

# Step 3: Convert .lrc file to .srt for subtitle embedding
def time_to_milliseconds(lrc_time):
    minutes, seconds = lrc_time.split(':')
    seconds, milliseconds = seconds.split('.')
    total_ms = int(minutes) * 60 * 1000 + int(seconds) * 1000 + int(milliseconds) * 10
    return total_ms

def lrc_to_srt(lrc_path, output_path):
    with open(lrc_path, 'r') as f:
        lines = f.readlines()

    srt_subtitles = pysrt.SubRipFile()
    time_lyrics_pattern = re.compile(r'\[(\d+:\d+\.\d+)\](.*)')

    parsed_lines = []
    for line in lines:
        match = time_lyrics_pattern.match(line)
        if match:
            lrc_time = match.group(1)
            lyrics = match.group(2).strip()
            start_time_ms = time_to_milliseconds(lrc_time)
            parsed_lines.append((start_time_ms, lyrics))

    for i, (start_time, lyrics) in enumerate(parsed_lines):
        if i < len(parsed_lines) - 1:
            end_time = parsed_lines[i + 1][0]
        else:
            end_time = start_time + 3000

        srt_start_time = pysrt.SubRipTime(milliseconds=start_time)
        srt_end_time = pysrt.SubRipTime(milliseconds=end_time)

        srt_subtitles.append(pysrt.SubRipItem(i + 1, srt_start_time, srt_end_time, lyrics))

    srt_subtitles.save(output_path)

# Step 3.5: Split the subtitles into main and after
def split_srt_to_two(srt_path, main_srt_path, after_srt_path):
    subs = pysrt.open(srt_path)

    main_subs = pysrt.SubRipFile()
    after_subs = pysrt.SubRipFile()

    for i, sub in enumerate(subs):
        main_subs.append(sub)
        if i < len(subs) - 1:
            next_sub = pysrt.SubRipItem(i + 1, sub.start, sub.end, subs[i + 1].text)
            after_subs.append(next_sub)

    main_subs.save(main_srt_path)
    after_subs.save(after_srt_path)

# Step 4: Embed subtitles into the video with the desired styling
def embed_subtitles(video_path, main_srt, after_srt, output_path, song_name, artist_name, album_name):
    temp_output_1 = f"{output_path}_temp_main.mp4"
    
    main_srt = main_srt.replace("'", "'\\''")
    after_srt = after_srt.replace("'", "'\\''")

    update_progress(song_name, artist_name, album_name, 8, "Embedding Subtitles - Main")
    font = "Arial Unicode MS"
    command_main = [
        'ffmpeg', '-i', video_path, '-vf', 
        f"subtitles={main_srt}:force_style='Fontname={font},Fontsize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Alignment=2,MarginV=30'",
        temp_output_1
    ]
    subprocess.run(command_main)

    update_progress(song_name, artist_name, album_name, 9, "Embedding Subtitles - After")
    command_after = [
        'ffmpeg', '-i', temp_output_1, '-vf', 
        f"subtitles={after_srt}:force_style='Fontname={font},Fontsize=18,PrimaryColour=&H00808080,OutlineColour=&H00000000,BorderStyle=3,Alignment=2,MarginV=10'",
        output_path
    ]
    subprocess.run(command_after)

    subprocess.run(['rm', temp_output_1])

# Main function to execute the process
@celery_app.task
def create_karaoke(artist_name, album_name, song_name):
    # base_path = os.path.join("input", artist, album, f"{artist}")
    # # Extract artist, album, and song names from the path
    # try:
    #     artist_name, album_name, song_name = base_path.split('/')[1:4]
    # except ValueError:
    #     raise ValueError("Invalid path format. Expected 'input/<artist_name>/<album_name>/<song_name>'.")

    # Define input and output paths
    input_folder = os.path.join("shared", "input", artist_name, album_name)
    output_folder = os.path.join("shared", "output", artist_name, album_name)
    os.makedirs(output_folder, exist_ok=True)

    video_file = os.path.join(input_folder, f"{artist_name} - {song_name}.webm")
    audio_file = os.path.join(input_folder, f"{artist_name} - {song_name}.ogg")
    lrc_file = os.path.join(input_folder, f"{artist_name} - {song_name}.lrc")
    output_file = os.path.join(output_folder, f"{artist_name} - {song_name}.mp4")

    # Check if all necessary files exist
    if not all([os.path.exists(video_file), os.path.exists(audio_file), os.path.exists(lrc_file)]):
        raise FileNotFoundError("One or more input files are missing (webm, ogg, lrc).")

    # Generate unique temporary filenames based on artist, album, and song name
    temp_video_no_audio = f"{artist_name}_{album_name}_{song_name}_temp_no_audio.webm"
    temp_video_subtitles = f"{artist_name}_{album_name}_{song_name}_temp_subtitles.mp4"
    temp_srt_file = f"{artist_name}_{album_name}_{song_name}_subtitles.srt"
    temp_main_srt_file = rename_file_without_special_chars(f"{artist_name}_{album_name}_{song_name}_main.srt")
    temp_after_srt_file = rename_file_without_special_chars(f"{artist_name}_{album_name}_{song_name}_after.srt")
    temp_accompaniment_file = os.path.join(output_folder, f"{artist_name}_{album_name}_{song_name}_accompaniment.wav")

    # Step 1: Remove audio from video
    update_progress(song_name, artist_name, album_name, 4, "Removing Audio")
    video_no_audio = remove_audio(video_file)
    video_no_audio.write_videofile(temp_video_no_audio)

    # Step 2: Add .ogg audio to video
    update_progress(song_name, artist_name, album_name, 5, "Adding Audio")
    remove_vocals(audio_file, temp_accompaniment_file)
    add_audio(temp_video_no_audio, audio_file, temp_accompaniment_file, temp_video_subtitles)

    # Step 3: Convert .lrc to .srt
    update_progress(song_name, artist_name, album_name, 6, "Converting Lyrics to SRT")
    lrc_to_srt(lrc_file, temp_srt_file)

    # Step 3.5: Split the SRT into main and after
    update_progress(song_name, artist_name, album_name, 7, "Splitting Subtitles")
    split_srt_to_two(temp_srt_file, temp_main_srt_file, temp_after_srt_file)

    # Step 4: Embed the converted subtitles (main and after) into the video
    embed_subtitles(temp_video_subtitles, temp_main_srt_file, temp_after_srt_file, output_file, song_name, artist_name, album_name)

    # # Clean up temporary files
    for temp_file in [temp_video_no_audio, temp_video_subtitles, temp_srt_file, temp_main_srt_file, temp_after_srt_file]:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# Main entry point
def main():
    if len(sys.argv) != 2:
        print("Usage: python karaoke_video_maker.py input/<artist_name>/<album_name>/<artist_name> - <song_name>")
        sys.exit(1)

    base_path = sys.argv[1]
    create_karaoke(base_path)

if __name__ == "__main__":
    main()
