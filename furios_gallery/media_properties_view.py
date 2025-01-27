# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Bardia Moshiri <bardia@furilabs.com>

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
from PIL import Image
from PIL.ExifTags import TAGS
import os
import mimetypes
from datetime import datetime

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
        self.camera_rows = {
            "Maker, Model": Adw.ActionRow(title="Maker, Model"),
            "Image Dimensions": Adw.ActionRow(title="Image Dimensions"),
            "Aperture": Adw.ActionRow(title="Aperture"),
            "Exposure": Adw.ActionRow(title="Exposure"),
            "ISO": Adw.ActionRow(title="ISO"),
            "FocalLength": Adw.ActionRow(title="Focal Length"),
            "Location": Adw.ActionRow(title="Location"),
        }

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
        pass

    def load_video_properties(self):
        pass

    def on_folder_clicked(self, button):
        folder_path = os.path.dirname(self.media_path)
        GLib.spawn_command_line_async(f"xdg-open {folder_path}")
