# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, Gdk, GLib, GdkPixbuf
from os.path import expanduser
from pathlib import Path
import os

from .media_view import MediaView
from .grid_view import GridView
from .albums_view import Albums
from .thumbnail_generator import ThumbnailGenerator
from .media_manager import (
    get_album_database_paths, get_album_media_paths,
    create_tables, create_connection,
    insert_file, delete_from_albums,
)

class GalleryWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connect("close-request", lambda _: exit(0))

        self.set_default_size(400, 600)
        self.set_hexpand(True)
        self.set_vexpand(True)

        # Set up application directory
        app_dir = Path(expanduser("~/.local/share/io.FuriOS.Gallery"))
        app_dir.mkdir(parents=True, exist_ok=True)

        # Database connection
        self.conn = create_connection(str(app_dir / "gallery-albums.db"))
        if self.conn is not None:
            create_tables(self.conn)

        # Thumbnail generator
        self.thumbnails = ThumbnailGenerator()

        # Media management variables
        self.current_album = ""
        self.media_paths = get_album_database_paths(self.conn, "Recents")
        self.current_index = len(self.media_paths) - 1

        # Create toast overlay for notifications
        self.toast_overlay = Adw.ToastOverlay()

        # Header bar setup
        self.header = Adw.HeaderBar()
        self.header.set_title_widget(Adw.WindowTitle(title="Gallery"))

        # Create navigation view for swipe gestures
        self.navigation_view = Adw.NavigationView()

        # Create initial albums page
        initial_albums_page = self.create_albums_page()
        self.navigation_view.add(initial_albums_page)

        # Toolbar view setup
        self.toolbar_view = Adw.ToolbarView()

        # Create album button
        self.create_album_btn = Gtk.Button(icon_name="folder-new-symbolic")
        self.create_album_btn.connect("clicked", self.create_album)
        self.header.pack_start(self.create_album_btn)

        # Media view buttons (initially hidden)
        self.media_options_btn = Gtk.Button(icon_name="view-more-symbolic")
        self.media_options_btn.connect("clicked", self.on_media_options_clicked)
        self.media_options_btn.set_visible(False)
        self.header.pack_end(self.media_options_btn)

        # Delete media button
        self.delete_media_btn = Gtk.Button(icon_name="user-trash-symbolic")
        self.delete_media_btn.connect("clicked", self.open_delete_popup)
        self.delete_media_btn.add_css_class("delete-btn")
        self.header.pack_end(self.delete_media_btn)

        # Return button
        self.return_btn = Gtk.Button(icon_name="application-exit-rtl-symbolic")
        self.return_btn.connect("clicked", self.on_return_clicked)
        self.return_btn.set_visible(False)
        self.header.pack_start(self.return_btn)

        # Add header to toolbar view
        self.toolbar_view.add_top_bar(self.header)

        # Set navigation view as toolbar content
        self.toolbar_view.set_content(self.navigation_view)

        # Set toast overlay as main content
        self.toast_overlay.set_child(self.toolbar_view)
        self.set_content(self.toast_overlay)

        # Navigation view state changes
        self.navigation_view.connect('popped', self.on_navigation_changed)
        self.navigation_view.connect('pushed', self.on_navigation_changed)

        self.present()

    def on_navigation_changed(self, navigation_view, page=None):
        visible_page = navigation_view.get_visible_page()
        if visible_page:
            if isinstance(visible_page, MediaView):
                # Media view header
                self.header.set_title_widget(Adw.WindowTitle(title="Media"))
                self.create_album_btn.set_visible(False)
                self.delete_media_btn.set_visible(True)
                self.media_options_btn.set_visible(True)
                self.return_btn.set_visible(True)
            elif visible_page.get_title() == "Albums":
                # Album view header
                self.header.set_title_widget(Adw.WindowTitle(title="Gallery"))
                self.create_album_btn.set_visible(True)
                self.delete_media_btn.set_visible(True)
                self.media_options_btn.set_visible(False)
                self.return_btn.set_visible(False)
            else:
                # Grid view header
                self.header.set_title_widget(Adw.WindowTitle(title=self.current_album))
                self.create_album_btn.set_visible(False)
                self.delete_media_btn.set_visible(True)
                self.media_options_btn.set_visible(False)
                self.return_btn.set_visible(True)

    def on_media_options_clicked(self, btn):
        current_page = self.navigation_view.get_visible_page()
        if isinstance(current_page, MediaView):
            current_page.open_menu_popup(None)

    def on_return_clicked(self, btn=None):
        if self.navigation_view.get_visible_page():
            self.navigation_view.pop()

    def create_albums_page(self):
        albums_page = Albums(self)
        albums_page.set_name("albums-square")
        return albums_page

    def create_media_view_page(self):
        media_view = MediaView(self)
        media_view.set_halign(Gtk.Align.FILL)
        media_view.set_valign(Gtk.Align.FILL)
        media_view.set_hexpand(True)
        media_view.set_vexpand(True)
        media_view.set_name("mediaView-square")
        return media_view

    def create_grid_view_page(self, album_name=None):
        media_grid_view = GridView(self, self.thumbnails)
        media_grid_view.set_halign(Gtk.Align.FILL)
        media_grid_view.set_valign(Gtk.Align.FILL)
        media_grid_view.set_hexpand(True)
        media_grid_view.set_vexpand(True)

        media_grid_view.set_name("mediaGridView-square")

        return media_grid_view

    def show_toast(self, message, duration=3):
        toast = Adw.Toast(title=message)
        self.toast_overlay.add_toast(toast)
        print(message)
        def dismiss_toast():
            toast.dismiss()
            return False
        GLib.timeout_add_seconds(duration, dismiss_toast)

    def open_media_at_index(self, media_index):
        self.current_index = media_index
        media_page = self.create_media_view_page()
        self.navigation_view.push(media_page)

    def create_album(self, button):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Create New Album",
            body="Enter the name of your new album:",
        )

        entry = Gtk.Entry()
        entry.set_placeholder_text("Album Name")
        entry.set_margin_top(10)
        entry.set_margin_bottom(10)
        dialog.set_extra_child(entry)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("create", "Create")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)

        dialog.connect("response", lambda dialog, response: self.on_album_create_response(dialog, response, entry))

        dialog.present()

    def on_album_create_response(self, dialog, response, entry):
        if response == "create":
            album_name = entry.get_text().strip()
            if album_name:
                try:
                    check_sql = "SELECT album_name FROM albums WHERE album_name = ?"
                    cur = self.conn.cursor()
                    cur.execute(check_sql, (album_name,))
                    if cur.fetchone() is None:
                        insert_sql = "INSERT INTO albums (album_name) VALUES (?)"
                        cur.execute(insert_sql, (album_name,))
                        self.conn.commit()
                        print(f"Successfully added album '{album_name}' to the database.")

                        # Refresh the current albums view
                        current_page = self.navigation_view.get_visible_page()
                        if hasattr(current_page, 'load_albums'):
                            current_page.load_albums()
                    else:
                        print(f"Album '{album_name}' already exists in the database.")
                except Exception as e:
                    print(f"Failed to create album '{album_name}': {e}")
            else:
                print("Album name cannot be empty")
        dialog.destroy()

    def open_delete_popup(self, btn):
        visible_page = self.navigation_view.get_visible_page()
        if visible_page:
            if isinstance(visible_page, GridView):
                flowbox = visible_page.flowbox
                label_text = f"Selected Files: {len(flowbox.get_selected_children())}"
            elif isinstance(visible_page, MediaView):
                visible_page.open_delete_popup(btn)
                return
            elif visible_page.get_title() == "Albums":
                flowbox = visible_page.flowbox
                label_text = f"Selected Albums: {len(flowbox.get_selected_children())}"
            else:
                print("Unsupported view type for delete popup")
                return

            flowbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)

            # Create selection bar
            selection_bar = Adw.HeaderBar()

            # Selection count label
            self.selected_files_label = Gtk.Label(label=label_text)
            selection_bar.set_title_widget(self.selected_files_label)

            # Cancel button
            self.cancel_btn = Gtk.Button(label="Cancel")
            self.cancel_btn.connect("clicked", self.on_cancel_selection)
            selection_bar.pack_start(self.cancel_btn)

            # Delete confirmation button
            self.delete_confirm_btn = Gtk.Button(label="Delete")
            self.delete_confirm_btn.add_css_class("destructive-action")
            self.delete_confirm_btn.connect("clicked", self.on_delete_confirmation)
            selection_bar.pack_end(self.delete_confirm_btn)

            # Restore original header
            self.toolbar_view.remove(self.header)
            self.toolbar_view.add_top_bar(selection_bar)
            self.selection_bar = selection_bar

    def on_cancel_selection(self, btn):
        current_page = self.navigation_view.get_visible_page()

        if isinstance(current_page, GridView):
            flowbox = current_page.flowbox
        elif isinstance(current_page, MediaView):
            return
        elif current_page.get_title() == "Albums":
            flowbox = current_page.flowbox
        else:
            print("Unsupported view type")
            return

        flowbox.unselect_all()
        flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)

        # Restore original header
        self.toolbar_view.remove(self.selection_bar)
        self.toolbar_view.add_top_bar(self.header)

    def on_delete_confirmation(self, btn):
        current_page = self.navigation_view.get_visible_page()

        if isinstance(current_page, GridView):
            flowbox = current_page.flowbox
            heading = "Delete Files?"
            body = f"This will permanently delete the {len(flowbox.get_selected_children())} selected files from your system"
            response_handler = self.on_delete_media
        elif isinstance(current_page, MediaView):
            current_page.open_delete_popup(btn)
            return
        elif current_page.get_title() == "Albums":
            flowbox = current_page.flowbox
            heading = "Delete Albums?"
            body = f"This will permanently delete the {len(flowbox.get_selected_children())} selected albums"
            response_handler = self.on_delete_albums
        else:
            print("Unsupported view type for delete confirmation")
            return

        selected_children = flowbox.get_selected_children()

        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=heading,
            body=body
        )

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", response_handler)
        dialog.present()

    def on_delete_media(self, dialog, response):
        if response == "delete":
            current_page = self.navigation_view.get_visible_page()

            if isinstance(current_page, GridView):
                flowbox = current_page.flowbox
            elif isinstance(current_page, MediaView):
                return
            elif current_page.get_title() == "Albums":
                flowbox = current_page.flowbox
            else:
                print("Unsupported view type for delete")
                return

            selected_children = flowbox.get_selected_children()

            for child in selected_children:
                media_index = child.media_index
                media_path = self.media_paths[media_index]
                delete_from_albums(self.conn, media_path)

                try:
                    if os.path.exists(media_path):
                        os.remove(media_path)
                except Exception as e:
                    print(f"Error deleting file: {e}")

                flowbox.remove(child)

        self.toolbar_view.remove(self.selection_bar)
        self.toolbar_view.add_top_bar(self.header)

        current_page = self.navigation_view.get_visible_page()

        if isinstance(current_page, GridView):
            flowbox = current_page.flowbox
        elif isinstance(current_page, MediaView):
            return
        elif current_page.get_title() == "Albums":
            flowbox = current_page.flowbox
        else:
            print("Unsupported view type for selection mode reset")
            return

        flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        dialog.destroy()

    def on_delete_albums(self, dialog, response):
        if response == "delete":
            current_page = self.navigation_view.get_visible_page()

            if current_page.get_title() == "Albums":
                flowbox = current_page.flowbox
                selected_children = flowbox.get_selected_children()

                for child in selected_children:
                    album_name = child.album_name

                    # Skip default albums
                    if album_name.lower() in ['recents', 'pictures', 'videos']:
                        continue

                    try:
                        # Delete album from database
                        cur = self.conn.cursor()
                        cur.execute("DELETE FROM file_albums WHERE album_id IN (SELECT album_id FROM albums WHERE album_name = ?)", (album_name,))
                        cur.execute("DELETE FROM albums WHERE album_name = ?", (album_name,))
                        self.conn.commit()

                        # Remove from UI
                        flowbox.remove(child)
                    except Exception as e:
                        print(f"Error deleting album {album_name}: {e}")

                # Refresh albums view
                current_page.load_albums()

        # Restore original header
        self.toolbar_view.remove(self.selection_bar)
        self.toolbar_view.add_top_bar(self.header)

        current_page.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        dialog.destroy()
