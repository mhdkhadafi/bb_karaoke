#!/usr/bin/env python3

import moviepy.editor as mp
import pysrt
import subprocess
import os
import re
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

def remove_vocals(input_file, output_folder, output_file):
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

    # Move the accompaniment file to the desired output file
    original_accompaniment_file = os.path.join(
        os.path.dirname(output_folder), 
        os.path.splitext(os.path.basename(input_file))[0], 
        'accompaniment.wav'
    )
    shutil.move(original_accompaniment_file, output_file)

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
    font = "Noto Sans"
    fallback_fonts = "Noto Sans CJK SC, Noto Sans CJK TC, Noto Sans CJK HK, Noto Sans CJK KR, Noto Sans CJK JP"

    command = [
        'ffmpeg',
        '-i', video_file,                     # Input video (VP8 in WebM)
        '-i', audio_without_vocals,              # First audio track (with vocals)
        '-i', audio_with_vocals,           # Second audio track (without vocals)
        '-map', '0:v',                        # Map video stream
        '-map', '1:a',                        # Map first audio stream (with vocals)
        '-map', '2:a',                        # Map second audio stream (without vocals)
        '-vf', f"[0:v]subtitles={after_srt}:force_style='Fontname={font},FallbackFonts={fallback_fonts},Fontsize=16,PrimaryColour=&H00808080,OutlineColour=&H00000000,BorderStyle=3,Alignment=2,MarginV=10'," \
            f"subtitles={main_srt}:force_style='Fontname={font},FallbackFonts={fallback_fonts},Fontsize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Alignment=2,MarginV=30'[out]",
        '-c:v', 'libx264',                    # Re-encode video to H.264 for MP4 compatibility
        '-c:a', 'aac',                        # Encode audio to AAC
        '-strict', 'experimental',            # Enable experimental features for AAC
        '-shortest',                          # Ensure video and audio match length
        '-preset', 'ultrafast',               # Speed up encoding
        output_file                           # Output file
    ]

    subprocess.run(command, check=True)
