import os
import subprocess
from PIL import Image
from gi.repository import Gtk

class ThumbnailGenerator:
    THUMBNAIL_SIZE = (250, 250)
    DISPLAY_SIZE = (25, 25)
    CACHE_DIR = os.path.expanduser("~/.cache/thumbnail_cache")

    def __init__(self):
        if not os.path.exists(self.CACHE_DIR):
            os.makedirs(self.CACHE_DIR)

    def generate_thumbnail(self, media_path):
        media_path = os.path.abspath(media_path)
        if media_path.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            return self._generate_image_thumbnail(media_path)
        elif media_path.endswith(('.mp4', '.mkv', '.avi', '.flv')):
            return self._generate_video_thumbnail(media_path)
        else:
            return None

    def _generate_image_thumbnail(self, image_path):
        thumbnail_path = os.path.join(self.CACHE_DIR, f"{os.path.basename(image_path)}_thumbnail.jpg")
        if not os.path.exists(thumbnail_path):
            with Image.open(image_path) as img:
                img.thumbnail(self.THUMBNAIL_SIZE)
                img.save(thumbnail_path, format="JPEG")
        return thumbnail_path

    def _generate_video_thumbnail(self, video_path):
        thumbnail_path = os.path.join(self.CACHE_DIR, f"{os.path.basename(video_path)}_thumbnail.jpg")

        if os.path.exists(thumbnail_path):
            return thumbnail_path

        try:
            command = [
                "ffmpeg",
                "-i", video_path,
                "-ss", "1",
                "-vframes", "1",
                "-q:v", "2",
                thumbnail_path
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            with Image.open(thumbnail_path) as img:
                img.thumbnail(self.THUMBNAIL_SIZE)
                img.save(thumbnail_path, format="JPEG")

        except subprocess.CalledProcessError as e:
            print(f"ffmpeg error: {e}")
            return None

        return thumbnail_path

    def update_ui_with_thumbnail(self, flowbox_child, thumbnail_path):
        thumbnail_picture = Gtk.Picture.new_for_filename(str(thumbnail_path))
        thumbnail_picture.set_content_fit(Gtk.ContentFit.COVER)

        flowbox_child.set_child(thumbnail_picture)