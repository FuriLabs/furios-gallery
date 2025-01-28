# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>
# Bardia Moshiri <bardia@furilabs.com>
# Jesús Higueras <jesus@furilabs.com>
# Luis Garcia <git@luigi311.com>

import os, time, av
from PIL import Image, ExifTags
from datetime import datetime

PICTURE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'bmp', 'webp', 'svg']
VIDEO_EXTENSIONS = ['mkv', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'm4v', 'mpg', 'mpeg']

def extract_extension(filepath: str) -> str:
    # Grab file extension without leading dot
    _, file_extension = os.path.splitext(filepath)
    file_extension = file_extension.lstrip(".").lower()

    return file_extension

def extract_file_date(filepath):
    try:
        if extract_extension(filepath) in ['jpg', 'jpeg']:
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

def get_file_creation_date(file_path):
    if not os.path.exists(file_path):
        return "File does not exist"

    creation_time = os.path.getctime(file_path)

    time_struct = time.localtime(creation_time)

    month = time.strftime('%b', time_struct)
    day = int(time.strftime('%d', time_struct))
    year = time.strftime('%Y', time_struct)

    if 11 <= day <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')

    readable_time = f"{month} {day}{suffix}, {year}"
    return readable_time

def check_file_integrity(file_path):
    if not os.path.exists(file_path):
        print(f"File does not exist: {file_path}")
        return False

    if os.path.getsize(file_path) == 0:
        print(f"File is empty: {file_path}")
        return False

    try:
        ext = extract_extension(file_path)
        if ext in PICTURE_EXTENSIONS:
            with Image.open(file_path) as img:
                img.verify()

                return True
        elif ext in VIDEO_EXTENSIONS:
            with av.open(file_path) as container:
                video_stream = container.streams.video[0]
                for frame in container.decode(video_stream):
                    if frame:
                        return True
                    break
            return False
        else:
            return None
    except (IOError, ValueError) as e:
        print(f"File could not be opened or is corrupted: {str(e)}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        return False

class MetadataReader():
    def __init__(self, file_path):
        self.metadata = {}
        self.file_path = file_path
        self.read_metadata_from_file_path()

    def read_metadata_from_file_path(self):
        ext = extract_extension(self.file_path)
        if ext in PICTURE_EXTENSIONS:
            image = Image.open(self.file_path)

            if 'exif' in image.info:
                exif_data = image._getexif()
                if exif_data:
                    self.metadata['EXIF Data'] = {ExifTags.TAGS.get(tag, f"Unknown Tag {tag}"): exif_data[tag] for tag in exif_data}
            else:
                print("No EXIF data found.")

        elif ext in VIDEO_EXTENSIONS:
            container = av.open(self.file_path)
            self.metadata['Video Metadata'] = {}
            self.metadata['Video Metadata']['Container'] = {
                "Format": container.format.name,
                "Duration": container.duration
            }

            self.metadata['Video Metadata']['Streams'] = {}
            for index, stream in enumerate(container.streams):
                stream_info = {
                    "Type": stream.type,
                    "Codec": stream.codec_context.codec_tag,
                    "Codec Tag": stream.codec_context.codec_tag
                }
                if stream.type == 'video':
                    stream_info.update({
                        "Width": stream.width,
                        "Height": stream.height
                    })
                elif stream.type == 'audio':
                    stream_info.update({
                        "Channels": stream.channels,
                        "Sample rate": stream.sample_rate
                    })
                self.metadata['Video Metadata']['Streams'][f"Stream {index}"] = stream_info

            container.close()

    def get_metadata_value(self, key):
        if key in self.metadata:
            return self.metadata[key]

        for category, data in self.metadata.items():
            if isinstance(data, dict):
                if key in data:
                    return data[key]
                for sub_key, sub_data in data.items():
                    if isinstance(sub_data, dict) and key in sub_data:
                        return sub_data[key]

    def contains_gps_data(self):
        exif_data = self.metadata.get('EXIF Data', {})
        gps_info = exif_data.get('GPSInfo', None)
        if gps_info and isinstance(gps_info, dict):
            return True
        return False