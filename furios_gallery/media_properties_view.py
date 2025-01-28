# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>
# Bardia Moshiri <bardia@furilabs.com>
# Jesús Higueras <jesus@furilabs.com>
# Luis Garcia <git@luigi311.com>

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
from PIL import Image
from PIL.ExifTags import TAGS
import os
import mimetypes
from datetime import datetime
from .media_manager import MetadataReader, extract_extension, PICTURE_EXTENSIONS, VIDEO_EXTENSIONS

class MediaPropertiesView(Gtk.Box):
    def __init__(self, media_path):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.media_path = media_path

        # Main content box with padding
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)

        # Init MetadataReader for selected file
        self.metadata_reader = MetadataReader(self.media_path)

        # Scrolled Window for content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_propagate_natural_height(True)
        scrolled.set_vexpand(True)

        # Groups box
        groups_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # File Information Group
        file_group = Adw.PreferencesGroup(title="File Information")

        # Folder row
        self.folder_row = Adw.ActionRow(title="Folder")
        folder_button = Gtk.Button(icon_name="folder-open-symbolic")
        folder_button.add_css_class("flat")
        folder_button.connect("clicked", self.on_folder_clicked)
        self.folder_row.add_suffix(folder_button)
        file_group.add(self.folder_row)

        # Path row
        self.path_row = Adw.ActionRow(title="Path")
        file_group.add(self.path_row)

        groups_box.append(file_group)

        # Media Information Group
        media_group = Adw.PreferencesGroup(title="Media Information")

        self.size_row = Adw.ActionRow(title="Media Size")
        self.format_row = Adw.ActionRow(title="Format")
        self.filesize_row = Adw.ActionRow(title="File Size")

        for row in [self.size_row, self.format_row, self.filesize_row]:
            media_group.add(row)

        groups_box.append(media_group)

        # Dates Group
        dates_group = Adw.PreferencesGroup(title="Dates")

        self.created_row = Adw.ActionRow(title="Created")
        self.modified_row = Adw.ActionRow(title="Modified")

        for row in [self.created_row, self.modified_row]:
            dates_group.add(row)

        groups_box.append(dates_group)

        # Camera Information Group
        self.camera_group = Adw.PreferencesGroup(title="Camera Information")

        # Create rows for camera info
        self.camera_rows = self.create_file_rows(extract_extension(self.media_path))

        for row in self.camera_rows.values():
            self.camera_group.add(row)

        groups_box.append(self.camera_group)

        # Add groups box to scrolled window
        scrolled.set_child(groups_box)

        # Add scrolled window to content
        content.append(scrolled)

        # Add content to main box
        self.append(content)

        # Load the properties
        self.load_properties()

    def create_file_rows(self, file_extension):
        camera_rows = {}
        if file_extension in PICTURE_EXTENSIONS:
            camera_rows = {
                "Maker, Model": Adw.ActionRow(title="Maker, Model"),
                "Image Dimensions": Adw.ActionRow(title="Image Dimensions"),
                "Aperture": Adw.ActionRow(title="Aperture"),
                "Exposure": Adw.ActionRow(title="Exposure"),
                "ISO": Adw.ActionRow(title="ISO"),
                "FocalLength": Adw.ActionRow(title="Focal Length"),
                "Location": Adw.ActionRow(title="Location"),
            }
        elif file_extension in VIDEO_EXTENSIONS:
            camera_rows = {
                "Format": Adw.ActionRow(title="Format"),
                "Duration": Adw.ActionRow(title="Duration"),
                "Video Streams": Adw.ActionRow(title="Video Streams"),
                "Audio Streams": Adw.ActionRow(title="Audio Streams"),
                "Codec": Adw.ActionRow(title="Codec"),
                "Resolution": Adw.ActionRow(title="Resolution"),
                "Channels": Adw.ActionRow(title="Channels"),
                "Sample Rate": Adw.ActionRow(title="Sample Rate")
            }
        return camera_rows

    def set_subtitle_or_hide(self, row_key, value):
        if value:
            self.camera_rows[row_key].set_subtitle(str(value))
            self.camera_rows[row_key].show()
        else:
            self.camera_rows[row_key].hide()

    def load_properties(self):
        # Set basic file information
        folder_path = os.path.dirname(self.media_path)
        self.folder_row.set_subtitle(folder_path)
        self.path_row.set_subtitle(self.media_path)

        # File stats
        stats = os.stat(self.media_path)
        size_mb = stats.st_size / (1024 * 1024)
        self.filesize_row.set_subtitle(f"{size_mb:.1f} MB")

        created = datetime.fromtimestamp(stats.st_ctime)
        modified = datetime.fromtimestamp(stats.st_mtime)
        self.created_row.set_subtitle(created.strftime("%Y-%m-%d %H:%M:%S"))
        self.modified_row.set_subtitle(modified.strftime("%Y-%m-%d %H:%M:%S"))

        # Media type and format
        mime_type, _ = mimetypes.guess_type(self.media_path)
        self.format_row.set_subtitle(mime_type or "Unknown")

        if mime_type and mime_type.startswith('image/'):
            self.load_image_properties()
        elif mime_type and mime_type.startswith('video/'):
            self.load_video_properties()

    def load_image_properties(self):
        for key in self.camera_rows:
            metadata_key_mapping = {
                "Maker, Model": ("Make", "Model"),
                "Image Dimensions": ("ImageWidth", "ImageLength"),
                "Aperture": "FNumber",
                "Exposure": "ExposureTime",
                "ISO": "ISOSpeedRatings",
                "FocalLength": "FocalLength",
                "Location": "GPSInfo"
            }

            metadata_key = metadata_key_mapping.get(key)
            if metadata_key:
                if key == "Maker, Model":
                    make = self.metadata_reader.get_metadata_value("Make")
                    model = self.metadata_reader.get_metadata_value("Model")

                    make_model = f"{make} {model}" if make and model else None
                    self.set_subtitle_or_hide(key, make_model)

                elif key == "Image Dimensions":
                    width = self.metadata_reader.get_metadata_value("ImageWidth")
                    height = self.metadata_reader.get_metadata_value("ImageLength")
                    dimensions_value = f"{width} x {height}" if width and height else None
                    self.set_subtitle_or_hide(key, dimensions_value)

                elif key == "Aperture":
                    aperture = self.metadata_reader.get_metadata_value("FNumber")
                    self.set_subtitle_or_hide(key, str(aperture) if aperture is not None else None)

                elif key == "Exposure":
                    exposure = self.metadata_reader.get_metadata_value("ExposureTime")
                    self.set_subtitle_or_hide(key, str(exposure) if exposure is not None else None)

                elif key == "ISO":
                    iso = self.metadata_reader.get_metadata_value("ISOSpeedRatings")
                    self.set_subtitle_or_hide(key, str(iso) if iso is not None else None)

                elif key == "FocalLength":
                    focal_length = self.metadata_reader.get_metadata_value("FocalLength")
                    self.set_subtitle_or_hide(key, str(focal_length) if focal_length is not None else None)

                elif key == "Location":
                    gps_info = self.metadata_reader.get_metadata_value("GPSInfo")
                    if gps_info and isinstance(gps_info, dict):
                        latitude_ref = gps_info.get(1)
                        latitude = gps_info.get(2)
                        longitude_ref = gps_info.get(3)
                        longitude = gps_info.get(4)

                        if latitude and longitude and latitude_ref and longitude_ref:
                            latitude_degrees = self.convert_gps_to_decimal(latitude, latitude_ref)
                            longitude_degrees = self.convert_gps_to_decimal(longitude, longitude_ref)
                            location_display = f"Lat: {latitude_degrees:.6f}, Lon: {longitude_degrees:.6f}"
                        else:
                            location_display = None
                    else:
                        location_display = None

                    self.set_subtitle_or_hide(key, location_display)

    def convert_gps_to_decimal(self, gps_data, ref):
        degrees, minutes, seconds = gps_data
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        if ref in ['S', 'W']:
            decimal *= -1
        return decimal

    def load_video_properties(self):
        metadata_key_mapping = {
            "Format": "Format",
            "Duration": "Duration",
            "Video Streams": "Video Streams",
            "Audio Streams": "Audio Streams",
            "Codec": "Codec",
            "Resolution": "Resolution",
            "Channels": "Channels",
            "Sample Rate": "Sample Rate"
        }

        video_metadata = self.metadata_reader.metadata.get('Video Metadata', {})
        container_info = video_metadata.get('Container', {})
        streams_info = video_metadata.get('Streams', {})

        # Handle Format and Duration
        format_value = extract_extension(self.media_path)
        duration_value = container_info.get("Duration")
        self.set_subtitle_or_hide("Format", format_value)
        self.set_subtitle_or_hide("Duration", duration_value)

        # Handle Video and Audio Streams count
        video_count = sum(1 for stream in streams_info.values() if stream['Type'] == 'video')
        audio_count = sum(1 for stream in streams_info.values() if stream['Type'] == 'audio')
        self.set_subtitle_or_hide("Video Streams", f"{video_count} Video Streams" if video_count else None)
        self.set_subtitle_or_hide("Audio Streams", f"{audio_count} Audio Streams" if audio_count else None)

        # Extract first video and audio stream if available
        first_video_stream = next((stream for stream in streams_info.values() if stream['Type'] == 'video'), None)
        first_audio_stream = next((stream for stream in streams_info.values() if stream['Type'] == 'audio'), None)

        # Handle Codec and Resolution for video streams
        if first_video_stream:
            codec_value = first_video_stream.get("Codec")
            resolution_value = f"{first_video_stream['Width']} x {first_video_stream['Height']}" if 'Width' in first_video_stream and 'Height' in first_video_stream else None
            self.set_subtitle_or_hide("Codec", codec_value)
            self.set_subtitle_or_hide("Resolution", resolution_value)
        else:
            self.camera_rows["Codec"].set_visible(False)
            self.camera_rows["Resolution"].set_visible(False)

        # Handle Channels and Sample Rate for audio streams
        if first_audio_stream:
            channels_value = first_audio_stream.get("Channels")
            sample_rate_value = first_audio_stream.get("Sample Rate")
            self.set_subtitle_or_hide("Channels", channels_value)
            self.set_subtitle_or_hide("Sample Rate", sample_rate_value)
        else:
            self.camera_rows["Channels"].set_visible(False)
            self.camera_rows["Sample Rate"].set_visible(False)

    def on_folder_clicked(self, button):
        folder_path = os.path.dirname(self.media_path)
        GLib.spawn_command_line_async(f"xdg-open {folder_path}")
