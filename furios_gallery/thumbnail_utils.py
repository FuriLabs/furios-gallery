# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs

import av
import hashlib
import math
import os
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from furios_gallery.media_manager import PICTURE_EXTENSIONS, VIDEO_EXTENSIONS, extract_extension, check_file_integrity

THUMBNAIL_SIZE = (256, 256)
DISPLAY_SIZE = (25, 25)
CACHE_DIR = os.path.expanduser("~/.cache/thumbnails/large")

def thumbnail_hash(media_path):
    uri = f"file://{os.path.abspath(media_path)}"
    return hashlib.md5(uri.encode()).hexdigest()

def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def has_thumbnail(media_path):
    thumbnail_path = os.path.join(CACHE_DIR, f"{thumbnail_hash(media_path)}.png")
    return os.path.exists(thumbnail_path)

def generate_thumbnail(media_path):
    media_path = os.path.abspath(media_path)
    thumbnail_path = os.path.join(CACHE_DIR, f"{thumbnail_hash(media_path)}.png")
    
    if not os.path.exists(thumbnail_path):
        if not os.path.exists(media_path) or os.path.getsize(media_path) == 0:
            print(f"File does not exist or is empty: {media_path}")
            return None
        
        if not check_file_integrity(media_path):
            print(f"File is invalid {media_path}")
            return None
        
        try:
            metadata = PngInfo()
            metadata.add_text("Thumb::URI", f"file://{media_path}")
            metadata.add_text("Thumb::MTime", str(math.trunc(os.path.getmtime(media_path))))
            metadata.add_text("Thumb::Size", str(os.path.getsize(media_path)))

            # Process Images thumbnails
            if extract_extension(media_path) in PICTURE_EXTENSIONS:
                with Image.open(media_path) as img:
                    img.thumbnail(THUMBNAIL_SIZE)
                    if img.mode == 'RGBA':
                        img = img.convert('RGB')

                    img.save(thumbnail_path, format="PNG", pnginfo=metadata)

            # Process Video thumbnails
            elif extract_extension(media_path) in VIDEO_EXTENSIONS:
                container = av.open(media_path)
                frame = next(container.decode(video=0))
                img = frame.to_image()
               
                img.thumbnail(THUMBNAIL_SIZE)
                img.save(thumbnail_path, format="PNG", pnginfo=metadata)
            else:
                return None
        except (av.AVError, IOError) as e:
                print(f"Error processing video: {e}")
                return None
        except IOError as e:
            print(f"Failed to open or process {media_path}: {e}")
            return None
    
    return thumbnail_path
