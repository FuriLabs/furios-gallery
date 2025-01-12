import fnmatch
from pathlib import Path
import os
from PIL import Image
from datetime import datetime

videos_paths = []
pictures_paths = []
media_paths = []
almbus = []

def extract_file_date(filepath):
    try:
        if filepath.lower().endswith(('.jpg', '.jpeg')):
            with Image.open(filepath) as img:
                exif_data = img._getexif()
                if exif_data:
                    date_str = exif_data.get(36867)
                    if date_str:
                        return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
    except Exception as e:
        print(f"Error reading EXIF data from {filepath}: {e}")

    stat = os.stat(filepath)
    return datetime.fromtimestamp(stat.st_mtime)


def setup_media_manager():
    global videos_paths, pictures_paths, media_paths

    pictures_path = Path.home() / 'Pictures' / 'furios-camera'
    videos_path = Path.home() / 'Videos' / 'furios-camera'

    pictures_paths = sorted(
        [str(pictures_path / filename) for filename in os.listdir(pictures_path) if fnmatch.fnmatch(filename, '*.jpg')]
    )
    videos_paths = sorted(
        [str(videos_path / filename) for filename in os.listdir(videos_path) if fnmatch.fnmatch(filename, '*.mkv')]
    )

    all_media_paths = pictures_paths + videos_paths

    media_paths = sorted(all_media_paths, key=extract_file_date)

    picture_file_count = len(pictures_paths)
    video_file_count = len(videos_paths)

def get_album_media_paths(album_name):
    pictures_path = Path.home() / 'Pictures' / album_name
    videos_path = Path.home() / 'Videos' / album_name

    pictures_paths = []
    videos_paths = []

    if pictures_path.is_dir():
        pictures_paths = sorted(
            [str(pictures_path / filename) for filename in os.listdir(pictures_path) if fnmatch.fnmatch(filename, '*.jpg')]
        )

    if videos_path.is_dir():
        videos_paths = sorted(
            [str(videos_path / filename) for filename in os.listdir(videos_path) if fnmatch.fnmatch(filename, '*.mkv')]
        )

    media_paths = pictures_paths + videos_paths

    media_paths = sorted(media_paths, key=extract_file_date)

    picture_file_count = len(pictures_paths)
    video_file_count = len(videos_paths)

    print(f"Picture files: {picture_file_count}, Video files: {video_file_count}")

    return media_paths

def get_media_paths():
    global media_paths
    return media_paths

def get_last_media_url():
    global media_paths
    return media_paths[-1]

def get_last_video_url():
    global videos_paths
    return videos_paths[-1]

def get_media_from_index(index):
    global media_paths
    return media_paths[index]
