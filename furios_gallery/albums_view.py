# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, Gdk, GLib, GdkPixbuf
from .media_manager import get_album_database_paths, list_database_albums, get_album_media_paths
from .thumbnail_generator import ThumbnailGenerator

class Albums(Gtk.Box):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.thumbnail_generator = ThumbnailGenerator()
        self.setup_css()
        self.widget = self.create_widget()
        self.append(self.widget)

    def setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
        .rounded-image {
            border-radius: 20px;
        }
        .missing-image {
            border-radius: 20px;
            background-color: #333;
        }
        """)
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def create_widget(self):
        albums_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        albums_box.set_hexpand(True)
        albums_box.set_vexpand(True)
        albums_box.set_halign(Gtk.Align.FILL)
        albums_box.set_valign(Gtk.Align.FILL)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.set_halign(Gtk.Align.FILL)
        scrolled_window.set_valign(Gtk.Align.FILL)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_column_spacing(0)
        self.flowbox.set_row_spacing(0)
        self.flowbox.set_max_children_per_line(3)
        self.flowbox.set_min_children_per_line(3)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flowbox.set_homogeneous(True)
        self.flowbox.set_hexpand(False)
        self.flowbox.set_vexpand(True)

        scrolled_window.set_child(self.flowbox)
        albums_box.append(scrolled_window)

        self.load_albums()
        self.flowbox.connect("selected-children-changed", self.on_child_selected)

        return albums_box

    def load_albums(self):
        albums = list_database_albums(self.app.conn)

        for album in albums:
            flowbox_child = Gtk.FlowBoxChild()
            flowbox_child.album_name = album

            album_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            album_box.set_spacing(8)
            album_box.set_halign(Gtk.Align.CENTER)
            album_box.set_valign(Gtk.Align.CENTER)

            album_paths = get_album_media_paths(self.app.conn, album)
            if album_paths:
                last_media_url = album_paths[-1]
                print(last_media_url)
                if last_media_url.endswith(('.mp4', '.mkv', '.avi')):
                    thumbnail_path = self.thumbnail_generator.generate_thumbnail(last_media_url)
                    if thumbnail_path:
                        image = GdkPixbuf.Pixbuf.new_from_file_at_scale(thumbnail_path, width=400, height=400, preserve_aspect_ratio=False)
                        picture = Gtk.Picture.new_for_pixbuf(image)
                        picture.set_css_classes(["rounded-image"])
                else:
                    image = GdkPixbuf.Pixbuf.new_from_file_at_scale(last_media_url, width=400, height=400, preserve_aspect_ratio=False)
                    picture = Gtk.Picture.new_for_pixbuf(image)
                    picture.set_css_classes(["rounded-image"])
            else:
                picture = Gtk.Box()
                picture.set_css_classes(["missing-image"])

                picture_content = Gtk.Image.new_from_icon_name("folder-symbolic")
                picture_content.set_pixel_size(70)

                icon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                icon_box.set_hexpand(True)
                icon_box.set_vexpand(True)
                icon_box.set_halign(Gtk.Align.FILL)
                icon_box.set_valign(Gtk.Align.FILL)
                icon_box.append(picture_content)

                picture.append(icon_box)

            label = Gtk.Label(label=album)
            label.set_wrap(False)
            label.set_max_width_chars(20)

            album_box.append(picture)
            album_box.append(label)

            flowbox_child.set_child(album_box)
            self.flowbox.append(flowbox_child)

        self.show()

    def on_child_selected(self, flowbox):
        if self.flowbox.get_selection_mode() == Gtk.SelectionMode.SINGLE:
            selected_children = flowbox.get_selected_children()
            if selected_children:
                selected_child = selected_children[0]
                album_name = selected_child.album_name
                self.app.current_album = album_name

                if album_name == "Videos":
                    self.app.open_album("Videos")
                elif album_name == "Pictures":
                    self.app.open_album("Pictures")
                else:
                    self.app.open_album(album_name)
