import fnmatch
from pathlib import Path
import os
from PIL import Image, ExifTags
import datetime
from datetime import datetime
import pyinotify
import pyinotify
import threading

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

def list_albums():
    pictures_path = Path.home() / 'Pictures'
    videos_path = Path.home() / 'Videos'

    albums_pictures = {
        entry.name for entry in os.scandir(pictures_path) if entry.is_dir()
    }

    albums_videos = {
        entry.name for entry in os.scandir(videos_path) if entry.is_dir()
    }

    unique_albums = albums_pictures.union(albums_videos)

    sorted_albums = sorted(unique_albums)
    sorted_albums.insert(0, "Pictures")
    sorted_albums.insert(0, "Videos")

    return sorted_albums

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

    return media_paths

def get_videos_paths():
    videos_path = Path.home() / 'Videos'
    videos_paths = []

    if videos_path.is_dir():
        videos_paths = sorted(
            str(file) for file in videos_path.rglob('*.mkv')
        )

    video_file_count = len(videos_paths)

    return videos_paths

def get_pictures_paths():
    pictures_path = Path.home() / 'Pictures'
    pictures_paths = []

    if pictures_path.is_dir():
        pictures_paths = sorted(
            str(file) for file in pictures_path.rglob('*.jpg')
        )

    picture_file_count = len(pictures_paths)

    return pictures_paths

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

def ordinal(n):
    if 10 <= n % 100 <= 20:
        return 'th'
    return {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')

def get_picture_date(image_path):
    with Image.open(image_path) as img:
        exif = img._getexif()

        if exif is not None:
            for tag_id, value in exif.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)

                if tag == 'DateTime':
                    date_obj = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')

                    return date_obj.strftime(f'%b {date_obj.day}{ordinal(date_obj.day)}, %Y')

    return "No date found"

def get_video_date(file_path):
    try:
        creation_time = os.path.getctime(file_path)
        return datetime.datetime.fromtimestamp(creation_time).strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"Error retrieving file metadata: {e}")
    return "No Date Found"

def get_media_date(file_path):
    if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        return get_picture_date(file_path)
    elif file_path.lower().endswith(('.mp4', '.mkv', '.avi')):
        return get_video_date(file_path)
    else:
        return "No Date Found"

class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CREATE(self, event):
        print(f"File created: {event.pathname}")

    def process_IN_DELETE(self, event):
        print(f"File deleted: {event.pathname}")

    def process_IN_MODIFY(self, event):
        print(f"File modified: {event.pathname}")

class DirectoryWatcher(threading.Thread):
    def __init__(self, directory_path):
        super().__init__()
        self.directory_path = directory_path
        self.stop_event = threading.Event()

    def run(self):
        wm = pyinotify.WatchManager()

        mask = pyinotify.IN_CREATE | pyinotify.IN_DELETE | pyinotify.IN_MODIFY

        handler = EventHandler()

        notifier = pyinotify.Notifier(wm, handler)

        wm.add_watch(self.directory_path, mask)

        print(f"Monitoring directory: {self.directory_path}")

        while not self.stop_event.is_set():
            notifier.process_events()
            if notifier.check_events():
                notifier.read_events()

    def stop(self):
        self.stop_event.set()
        print("Stopping directory monitoring...")