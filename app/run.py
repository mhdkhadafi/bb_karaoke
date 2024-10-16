import track_downloader as td
import karaoke_video_maker as kvm
import aws_helpers as aws
import os
import shutil

def generate_karaoke_video(search_term):
    tracks = td.search_spotify(search_term)
    song = tracks[0]
    artist_name = song['artists'][0]['name']
    album_name = song['album']['name']
    song_name = song['name']
    url = song['external_urls']['spotify']
    td.download_audio(url)
    td.download_video(artist_name, album_name, song_name)
    td.download_lyrics(artist_name, album_name, song_name)

    input_folder = os.path.join("shared", "input", artist_name, album_name)
    output_folder = os.path.join("shared", "output", artist_name, album_name)
    os.makedirs(output_folder, exist_ok=True)
    video_file = os.path.join(input_folder, f"{artist_name} - {song_name}.webm")
    audio_file = os.path.join(input_folder, f"{artist_name} - {song_name}.ogg")
    lrc_file = os.path.join(input_folder, f"{artist_name} - {song_name}.lrc")
    output_file = os.path.join(output_folder, f"{artist_name} - {song_name}.mp4")
    if not all([os.path.exists(video_file), os.path.exists(audio_file), os.path.exists(lrc_file)]):
        raise FileNotFoundError("One or more input files are missing (webm, ogg, lrc).")

    temp_video_no_audio = os.path.join(input_folder, f"{artist_name}_{album_name}_{song_name}_temp_no_audio.webm")
    temp_video_subtitles = os.path.join(input_folder, f"{artist_name}_{album_name}_{song_name}_temp_subtitles.mp4")
    temp_srt_file = os.path.join(input_folder, f"{artist_name}_{album_name}_{song_name}_subtitles.srt")
    temp_main_srt_file = os.path.join(input_folder, kvm.rename_file_without_special_chars(f"{artist_name}_{album_name}_{song_name}_main.srt"))
    temp_after_srt_file = os.path.join(input_folder, kvm.rename_file_without_special_chars(f"{artist_name}_{album_name}_{song_name}_after.srt"))
    temp_accompaniment_file = os.path.join(input_folder, f"{artist_name}_{album_name}_{song_name}_accompaniment.wav")
    original_accompaniment_file = os.path.join(input_folder, f"{artist_name} - {song_name}", 'accompaniment.wav')


    kvm.remove_vocals(audio_file, input_folder)
    shutil.move(original_accompaniment_file, temp_accompaniment_file)
    kvm.lrc_to_srt(lrc_file, temp_srt_file)
    kvm.split_srt_to_two(temp_srt_file, temp_main_srt_file, temp_after_srt_file)
    kvm.create_video(video_file, audio_file, temp_accompaniment_file, temp_main_srt_file, temp_after_srt_file, output_file)
    
    bucket_name = 'bb-karaoke'
    s3_file_name = f"{artist_name}/{album_name}/{artist_name} - {song_name}.mp4"
    aws.upload_to_s3(output_file, bucket_name, s3_file_name)


def main():
    pass

if __name__ == "__main__":
    main()

