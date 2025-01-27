# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs

import os, av
from PIL import Image

from furios_gallery.media_manager import PICTURE_EXTENSIONS, VIDEO_EXTENSIONS, extract_extension, check_file_integrity

THUMBNAIL_SIZE = (250, 250)
DISPLAY_SIZE = (25, 25)
CACHE_DIR = os.path.expanduser("~/.cache/thumbnail_cache")

def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def generate_image_thumbnail(image_path):
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    thumbnail_path = os.path.join(CACHE_DIR, f"{base_name}_thumbnail.jpg")
    if not os.path.exists(thumbnail_path):
        if not check_file_integrity(image_path):
            return None

        try:
            with Image.open(image_path) as img:
                img.thumbnail(THUMBNAIL_SIZE)
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                img.save(thumbnail_path, format="JPEG")
        except IOError as e:
            print(f"Failed to open or process image {image_path}: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while processing {image_path}: {e}")
            return None
    return thumbnail_path

def generate_video_thumbnail(video_path):
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    thumbnail_path = os.path.join(CACHE_DIR, f"{base_name}_thumbnail.jpg")
    if not os.path.exists(thumbnail_path):
        if not check_file_integrity(video_path):
            return None

        try:
            container = av.open(video_path)
            frame = next(container.decode(video=0))
            img = frame.to_image()
            img.thumbnail(THUMBNAIL_SIZE)
            img.save(thumbnail_path, format="JPEG")
        except (av.AVError, IOError) as e:
            print(f"Error processing video: {e}")
            return None

    return thumbnail_path

def has_thumbnail(media_path):
    base_name = os.path.splitext(os.path.basename(media_path))[0]
    thumbnail_path = os.path.join(CACHE_DIR, f"{base_name}_thumbnail.jpg")

    return os.path.exists(thumbnail_path)

def generate_thumbnail(media_path):
    media_path = os.path.abspath(media_path)
    if extract_extension(media_path) in PICTURE_EXTENSIONS:
        return generate_image_thumbnail(media_path)
    elif extract_extension(media_path) in VIDEO_EXTENSIONS:
        return generate_video_thumbnail(media_path)
    else:
        return None
