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
from gi.repository import Gtk, Adw, Gdk, GdkPixbuf, Pango

from .database_manager import get_album_database_paths, list_database_albums, get_album_media_paths, get_latest_media_path
from .thumbnail_generator import ThumbnailGenerator

class Albums(Adw.NavigationPage):
    def __init__(self, app_window):
        super().__init__(title="Albums")

        self.app_window = app_window
        self.thumbnail_generator = ThumbnailGenerator()

        # Main content box
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content_box.set_hexpand(True)
        self.content_box.set_vexpand(True)

        # Scrolled window for albums
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)

        # Flowbox for albums
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_column_spacing(10)
        self.flowbox.set_row_spacing(10)
        self.flowbox.set_max_children_per_line(3)
        self.flowbox.set_min_children_per_line(3)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flowbox.set_homogeneous(True)

        # Connect selection changed signal
        self.flowbox.connect("selected-children-changed", self.on_album_selected)

        # Setup CSS for album items
        self.setup_css()

        # Add flowbox to scrolled window
        scrolled_window.set_child(self.flowbox)
        self.content_box.append(scrolled_window)

        # Set content of NavigationPage
        self.set_child(self.content_box)

        # Load albums
        self.load_albums()

        # Give focus to the album_view page
        self.app_window.present()

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
        """
        )

        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def load_albums(self):
        # Clear existing items
        self.flowbox.remove_all()

        # Get albums from database
        albums = list_database_albums(self.app_window.conn)

        for album in albums:
            flowbox_child = Gtk.FlowBoxChild()
            flowbox_child.album_name = album

            album_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            album_box.set_spacing(8)
            album_box.set_halign(Gtk.Align.CENTER)
            album_box.set_valign(Gtk.Align.CENTER)

            last_media_url = get_latest_media_path(self.app_window.conn, album)

            if last_media_url:
                thumbnail_path = self.thumbnail_generator.generate_thumbnail(last_media_url)
                if thumbnail_path:
                    image = GdkPixbuf.Pixbuf.new_from_file_at_scale(thumbnail_path, width=400, height=400, preserve_aspect_ratio=False)
                    picture = Gtk.Picture.new_for_pixbuf(image)
                    picture.set_css_classes(["rounded-image"])
            else:
                # Default missing album image
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

            # Album name label
            label = Gtk.Label(label=album)
            label.set_wrap(False)
            label.set_ellipsize(Pango.EllipsizeMode.END)

            album_box.append(picture)
            album_box.append(label)

            flowbox_child.set_child(album_box)
            self.flowbox.append(flowbox_child)

    def on_album_selected(self, flowbox):
        if flowbox.get_selection_mode() == Gtk.SelectionMode.SINGLE:
            selected_children = flowbox.get_selected_children()
            if selected_children:
                selected_child = selected_children[0]
                album_name = selected_child.album_name

                # Update current album
                self.app_window.current_album = album_name

                # Retrieve media paths for the selected album
                self.app_window.media_paths = get_album_database_paths(self.app_window.conn, album_name)
                self.app_window.current_index = len(self.app_window.media_paths) - 1

                # Update header title
                self.app_window.header.set_title_widget(Adw.WindowTitle(title=album_name))

                # Create grid view page for the album
                grid_view_page = self.app_window.create_grid_view_page(album_name)

                # Push grid view to navigation view
                self.app_window.navigation_view.push(grid_view_page)

            self.flowbox.unselect_all()

    def update_album_thumbnail(self, album):
        last_media_url = get_latest_media_path(self.app_window.conn, album)

        if last_media_url:
            thumbnail_path = self.thumbnail_generator.generate_thumbnail(last_media_url)
            if thumbnail_path:
                image = GdkPixbuf.Pixbuf.new_from_file_at_scale(thumbnail_path, width=400, height=400, preserve_aspect_ratio=False)
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
            label.set_ellipsize(Pango.EllipsizeMode.END)

        for child in self.flowbox:
            if hasattr(child, "album_name") and child.album_name == album:
                album_box = child.get_child()
                children = list(album_box)
                if children:
                    album_box.remove(children[0])
                    album_box.prepend(picture)

    def update_all_album_thumbnails(self):
        for child in self.flowbox:  # Iterate over all children in the FlowBox
            if hasattr(child, "album_name"):
                album_name = child.album_name
                self.update_album_thumbnail(album_name)
