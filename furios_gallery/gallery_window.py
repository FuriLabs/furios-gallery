# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

from gi.repository import Gtk, Adw, Gdk
from os.path import expanduser
from pathlib import Path
import os
from .media_view import MediaView
from .grid_view import GridView
from .albums_view import Albums
from .thumbnail_generator import ThumbnailGenerator
from .media_manager import get_album_database_paths, get_album_media_paths, create_tables, create_connection, insert_file, populate_database, delete_from_albums

class GalleryWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connect("close-request", lambda _: exit(0))

        self.set_default_size(400, 600)
        self.set_hexpand(True)
        self.set_vexpand(True)

        app_dir = Path(expanduser("~/.local/share/io.FuriOS.Gallery"))
        app_dir.mkdir(parents=True, exist_ok=True)

        self.conn = create_connection(str(app_dir / "gallery-albums.db"))
        if self.conn is not None:
            create_tables(self.conn)

        self.thumbnails = ThumbnailGenerator()
        self.current_album = ""
        self.media_paths = get_album_database_paths(self.conn, "Recents")
        self.current_index = len(self.media_paths) - 1
        self.current_view = None

        # Create main layout structure
        self.toast_overlay = Adw.ToastOverlay()
        self.toolbar_view = Adw.ToolbarView()

        # Setup header with buttons
        self.header = Adw.HeaderBar()
        self.header.set_title_widget(Adw.WindowTitle(title="Gallery"))

        # Add return to albums button on the left
        self.return_to_albums_btn = Gtk.Button(icon_name="application-exit-rtl-symbolic")
        self.return_to_albums_btn.connect("clicked", self.on_return_to_albums_view)
        self.header.pack_start(self.return_to_albums_btn)

        # Add create album button on the left
        self.create_album_btn = Gtk.Button(icon_name="folder-new-symbolic")
        self.create_album_btn.connect("clicked", self.create_album)
        self.header.pack_start(self.create_album_btn)

        # Add delete button on the right
        self.delete_media_btn = Gtk.Button(icon_name="user-trash-symbolic")
        self.delete_media_btn.connect("clicked", self.open_delete_popup)
        self.delete_media_btn.add_css_class("delete-btn")
        self.header.pack_end(self.delete_media_btn)

        self.toolbar_view.add_top_bar(self.header)

        # Setup navigation and content
        self.navigation_view = Adw.NavigationView()
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.current_view = self.create_albums_box()
        self.main_box.append(self.current_view)

        # Setup navigation page
        self.main_page = Adw.NavigationPage(
            title="Gallery",
            child=self.main_box
        )
        self.navigation_view.add(self.main_page)

        # Setup bottom sheet
        self.bottom_sheet = Adw.BottomSheet()
        self.bottom_sheet.set_content(self.navigation_view)

        # Setup content
        self.toolbar_view.set_content(self.bottom_sheet)
        self.toast_overlay.set_child(self.toolbar_view)
        self.set_content(self.toast_overlay)

        self.present()

    def show_toast(self, message, duration=3):
        """Display a toast message."""
        toast = Adw.Toast(title=message)
        self.toast_overlay.add_toast(toast)
        print(message)
        def dismiss_toast():
            toast.dismiss()
            return False
        GLib.timeout_add_seconds(duration, dismiss_toast)

    def create_media_view_box(self):
        media_view_box = MediaView(self)
        media_view_box.widget.set_halign(Gtk.Align.FILL)
        media_view_box.widget.set_valign(Gtk.Align.FILL)
        media_view_box.widget.set_hexpand(True)
        media_view_box.widget.set_vexpand(True)
        media_view_box.widget.set_name("mediaView-square")
        return media_view_box

    def create_grid_view_box(self):
        media_grid_view_box = GridView(self, self.thumbnails)
        media_grid_view_box.set_halign(Gtk.Align.FILL)
        media_grid_view_box.set_valign(Gtk.Align.FILL)
        media_grid_view_box.set_hexpand(True)
        media_grid_view_box.set_vexpand(True)

        if media_grid_view_box.flowbox is not None:
            self.thumbnails.load_images_in_background(self.media_paths, media_grid_view_box.flowbox)

        media_grid_view_box.set_name("mediaGridView-square")
        return media_grid_view_box

    def create_albums_box(self):
        albums_box = Albums(self)
        albums_box.set_halign(Gtk.Align.FILL)
        albums_box.set_valign(Gtk.Align.FILL)
        albums_box.set_hexpand(True)
        albums_box.set_vexpand(True)
        albums_box.set_name("albums-square")
        return albums_box

    def switch_to_view(self, new_view_creator):
        if self.current_view:
            self.main_box.remove(self.current_view)
        self.current_view = new_view_creator()
        self.main_box.append(self.current_view)

    def open_media_at_index(self, media_index):
        self.current_index = media_index
        self.switch_to_view(self.create_media_view_box)

    def open_album(self, album_name):
        self.media_paths = get_album_database_paths(self.conn, album_name)
        self.current_index = len(self.media_paths) - 1
        self.switch_to_view(self.create_grid_view_box)

    def on_return_to_albums_view(self, btn):
        self.switch_to_view(self.create_albums_box)

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

                        # Refresh the albums view
                        self.switch_to_view(self.create_albums_box)
                    else:
                        print(f"Album '{album_name}' already exists in the database.")
                except Exception as e:
                    print(f"Failed to create album '{album_name}': {e}")
            else:
                print("Album name cannot be empty")
        dialog.destroy()

    def open_delete_popup(self, btn):
        if hasattr(self.current_view, 'flowbox'):
            self.current_view.flowbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)

            # Create selection bar
            selection_bar = Adw.HeaderBar()

            # Selection count label
            self.selected_files_label = Gtk.Label(
                label=f"Selected Files: {len(self.current_view.flowbox.get_selected_children())}"
            )
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

            # Replace the header bar temporarily
            self.toolbar_view.remove(self.header)
            self.toolbar_view.add_top_bar(selection_bar)
            self.selection_bar = selection_bar

    def on_cancel_selection(self, btn):
        if hasattr(self.current_view, 'flowbox'):
            self.current_view.flowbox.unselect_all()
            self.current_view.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)

        # Restore original header
        self.toolbar_view.remove(self.selection_bar)
        self.toolbar_view.add_top_bar(self.header)

    def on_delete_confirmation(self, btn):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Delete Files?",
            body=f"This will permanently delete the {len(self.current_view.flowbox.get_selected_children())} selected files from your system"
        )

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self.on_delete_media)
        dialog.present()

    def on_delete_media(self, dialog, response):
        if response == "delete":
            selected_children = self.current_view.flowbox.get_selected_children()
            for child in selected_children:
                media_index = child.media_index
                media_path = self.media_paths[media_index]
                delete_from_albums(self.conn, media_path)

                try:
                    if os.path.exists(media_path):
                        os.remove(media_path)
                except Exception as e:
                    print(f"Error deleting file: {e}")

                self.current_view.flowbox.remove(child)

        # Restore original header
        self.toolbar_view.remove(self.selection_bar)
        self.toolbar_view.add_top_bar(self.header)

        if hasattr(self.current_view, 'flowbox'):
            self.current_view.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)

        dialog.destroy()
