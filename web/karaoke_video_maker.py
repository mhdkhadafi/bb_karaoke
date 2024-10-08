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
import shutil

def rename_file_without_special_chars(file_path):
    # Replace problematic characters (e.g., single quotes)
    new_file_path = file_path.replace("'", "")
    return new_file_path

# Step 1: Remove audio from .webm file
def remove_audio(video_path):
    video = mp.VideoFileClip(video_path)
    video_without_audio = video.without_audio()
    return video_without_audio

#def remove_vocals(audio_path, accompaniment_file):
#    spleeter_api_url = "http://spleeter:5001/split"
#    response = requests.post(spleeter_api_url, json={"file_path": audio_path, "accompaniment_file": accompaniment_file})
#
#    if response.status_code == 200:
#        print("Spleeter separation successful! Waiting for the output file...")
#        
#        # Wait for the accompaniment file to be created (polling)
#        for _ in range(60):  # Wait for up to 60 seconds
#            if os.path.exists(accompaniment_file):
#                return accompaniment_file
#            time.sleep(1)  # Wait for 1 second before checking again
#        
#        raise Exception(f"Accompaniment file not found: {accompaniment_file}")
#    else:
#        raise Exception(f"Spleeter error: {response.json().get('error')}")

def remove_vocals(input_file, output_folder):
    volume_path = "/home/ec2-user/bb_karaoke/shared"
    command = [
        "docker", "run", 
        "-v", f"{volume_path}:/shared",
        "deezer/spleeter:3.8", 
        "separate", 
        "-o", output_folder, 
        input_file
    ]

    subprocess.run(command, check=True)


# Step 2: Add .ogg audio to the video
def add_audio(video_file, audio_without_vocals, output_file):
    #command = [
    #    'ffmpeg',
    #    '-i', video_file,                     # Input video (VP8 in WebM)
    #    '-i', audio_with_vocals,              # First audio track (with vocals)
    #    '-i', audio_without_vocals,           # Second audio track (without vocals)
    #    '-map', '0:v',                        # Map video stream
    #    '-map', '1:a',                        # Map first audio stream
    #    '-map', '2:a',                        # Map second audio stream
    #    '-c:v', 'libx264',                    # Re-encode video to H.264 for MP4 compatibility
    #    '-c:a', 'aac',                        # Encode audio to AAC
    #    '-strict', 'experimental',            # Enable experimental features for AAC
    #    '-shortest',                          # Ensure video and audio match length
    #    '-preset', 'ultrafast',               # Optionally speed up encoding (can change to 'fast', etc.)
    #    output_file                           # Output file
    #]
    command = [
        'ffmpeg', '-i', video_file, '-i', audio_without_vocals, 
        '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', '-strict', 'experimental', '-map', '0:v', '-map', '1:a', output_file
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

def create_video(video_file, audio_with_vocals, audio_without_vocals, main_srt, after_srt, output_file):
    font = "Arial Unicode MS"

    command = [
        'ffmpeg',
        '-i', video_file,                     # Input video (VP8 in WebM)
        '-i', audio_with_vocals,              # First audio track (with vocals)
        '-i', audio_without_vocals,           # Second audio track (without vocals)
        '-map', '0:v',                        # Map video stream
        '-map', '1:a',                        # Map first audio stream (with vocals)
        '-map', '2:a',                        # Map second audio stream (without vocals)
        '-vf', f"[0:v]subtitles={main_srt}:force_style='Fontname={font},Fontsize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Alignment=2,MarginV=30'," \
            f"subtitles={after_srt}:force_style='Fontname={font},Fontsize=18,PrimaryColour=&H00808080,OutlineColour=&H00000000,BorderStyle=3,Alignment=2,MarginV=10'[out]",
        '-c:v', 'libx264',                    # Re-encode video to H.264 for MP4 compatibility
        '-c:a', 'aac',                        # Encode audio to AAC
        '-strict', 'experimental',            # Enable experimental features for AAC
        '-shortest',                          # Ensure video and audio match length
        '-preset', 'ultrafast',               # Speed up encoding
        output_file                           # Output file
    ]

    subprocess.run(command, check=True)

# Step 4: Embed subtitles into the video with the desired styling
def embed_subtitles(video_path, main_srt, after_srt, output_path, song_name, artist_name, album_name):
    temp_output_1 = f"{output_path}_temp_main.mp4"
    
    main_srt = main_srt.replace("'", "'\\''")
    after_srt = after_srt.replace("'", "'\\''")

    update_progress(song_name, artist_name, album_name, 8, "Embedding Subtitles - Main")
    font = "Arial Unicode MS"
    command_main = [
        'ffmpeg', '-i', video_path, '-vf', 
        f"subtitles='{main_srt}':force_style='Fontname={font},Fontsize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Alignment=2,MarginV=30'",
        temp_output_1
    ]
    subprocess.run(command_main)

    update_progress(song_name, artist_name, album_name, 9, "Embedding Subtitles - After")
    command_after = [
        'ffmpeg', '-i', temp_output_1, '-vf', 
        f"subtitles='{after_srt}':force_style='Fontname={font},Fontsize=18,PrimaryColour=&H00808080,OutlineColour=&H00000000,BorderStyle=3,Alignment=2,MarginV=10'",
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
    temp_srt_file = os.path.join(input_folder, f"{artist_name}_{album_name}_{song_name}_subtitles.srt")
    temp_main_srt_file = os.path.join(input_folder, kvm.rename_file_without_special_chars(f"{artist_name}_{album_name}_{song_name}_main.srt"))
    temp_after_srt_file = os.path.join(input_folder, kvm.rename_file_without_special_chars(f"{artist_name}_{album_name}_{song_name}_after.srt"))
    temp_accompaniment_file = os.path.join(input_folder, f"{artist_name}_{album_name}_{song_name}_accompaniment.wav")
    original_accompaniment_file = os.path.join(input_folder, f"{artist_name} - {song_name}", 'accompaniment.wav')

    # Step 1: Add .ogg audio to video
    update_progress(song_name, artist_name, album_name, 4, "Adding Audio")
    remove_vocals(audio_file, input_folder)
    shutil.move(original_accompaniment_file, temp_accompaniment_file)

    # Step 2: Convert .lrc to .srt
    update_progress(song_name, artist_name, album_name, 5, "Converting Lyrics to SRT")
    lrc_to_srt(lrc_file, temp_srt_file)

    # Step 3: Split the SRT into main and after
    update_progress(song_name, artist_name, album_name, 6, "Splitting Subtitles")
    split_srt_to_two(temp_srt_file, temp_main_srt_file, temp_after_srt_file)
    
    # Step 4: Create Video
    update_progress(song_name, artist_name, album_name, 7, "Creating Karaoke Video")
    create_video(video_file, audio_file, temp_accompaniment_file, temp_main_srt_file, temp_after_srt_file, output_file)

    # # Clean up temporary files
    for temp_file in [temp_srt_file, temp_main_srt_file, temp_after_srt_file, temp_accompaniment_file]:
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
