# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>
# Bardia Moshiri <bardia@furilabs.com>
# Jesús Higueras <jesus@furilabs.com>
# Luis Garcia <git@luigi311.com>

import os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gdk, Adw, GLib
from os.path import expanduser
from pathlib import Path

from .edit_view.furios_media_tools import FuriOSMediaTools
from .media_view import MediaView
from .edit_view.edit_view import EditView
from .grid_view import GridView
from .albums_view import Albums
from .thumbnail_generator import ThumbnailGenerator
from .media_properties_view import MediaPropertiesView
from .database_manager import (
    get_album_database_paths,
    create_tables, create_connection,
    delete_from_albums,
    populate_database_async,
)
from .ui import (
    create_gallery_header, create_album_button, create_info_button, create_media_options_button,
    create_delete_media_button, create_return_button, create_main_window_layout,
    create_album_create_dialog, create_selection_header_bar, create_delete_confirmation_dialog,
    create_map_page, clear_flowbox, create_change_file_name_button, create_rename_dialog
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
        self.toast_overlay, self.toolbar_view, self.bottom_sheet, self.navigation_view = create_main_window_layout()

        # Header bar setup
        self.header = create_gallery_header()

        # Create album button
        self.create_album_btn = create_album_button(self.create_album)
        self.header.pack_start(self.create_album_btn)

        # Info button (initially hidden)
        self.info_btn = create_info_button(self.on_info_clicked)
        self.header.pack_end(self.info_btn)

        # Media view buttons (initially hidden)
        self.media_options_btn = create_media_options_button(self.on_media_options_clicked)
        self.header.pack_end(self.media_options_btn)

        # Delete media button
        self.delete_media_btn = create_delete_media_button(self.open_delete_popup)
        self.header.pack_end(self.delete_media_btn)

        # Return button
        self.return_btn = create_return_button(self.on_return_clicked)
        self.header.pack_start(self.return_btn)

        # Create change Name button (initially hidden)
        self.create_change_name_btn = create_change_file_name_button(self.change_file_name)
        self.header.pack_start(self.create_change_name_btn)

        # Create initial albums page
        self.initial_albums_page = self.create_albums_page()
        self.navigation_view.add(self.initial_albums_page)

        # Add header to toolbar view
        self.toolbar_view.add_top_bar(self.header)

        # Set toast overlay as main content
        self.set_content(self.toast_overlay)

        # Navigation view state changes
        self.navigation_view.connect('popped', self.on_navigation_changed)
        self.navigation_view.connect('pushed', self.on_navigation_changed)

        self.present()

        # Start background database population AFTER window is shown
        self.start_background_loading(str(app_dir / "gallery-albums.db"))

    def start_background_loading(self, db_file):
        def on_completion():
            print("Background database population complete!")

            # Refresh the albums view if it's currently visible
            current_page = self.navigation_view.get_visible_page()
            if hasattr(current_page, 'load_albums_async'):
                GLib.idle_add(current_page.load_albums_async)
            elif hasattr(current_page, 'load_albums'):
                GLib.idle_add(current_page.load_albums)

        # Start the background loading
        populate_database_async(db_file, completion_callback=on_completion)

    def on_page_popped(self, navigation_view, page):
        # If it has a FlowBox, remove each child
        if hasattr(page, "flowbox"):
            clear_flowbox(page.flowbox)

        # Finally unparent the page itself from the nav‐view
        navigation_view.remove(page)

    def on_navigation_changed(self, navigation_view, page=None):
        visible_page = navigation_view.get_visible_page()
        if visible_page:
            if isinstance(visible_page, MediaView):
                # Media view header
                self.header.set_title_widget(Adw.WindowTitle(title="Media"))
                self.create_change_name_btn.set_visible(True)
                self.create_album_btn.set_visible(False)
                self.delete_media_btn.set_visible(True)
                self.media_options_btn.set_visible(True)
                self.info_btn.set_visible(True)
                self.return_btn.set_visible(True)
            elif visible_page.get_title() == "Albums":
                # Album view header
                self.header.set_title_widget(Adw.WindowTitle(title="Gallery"))
                self.create_change_name_btn.set_visible(False)
                self.create_album_btn.set_visible(True)
                self.delete_media_btn.set_visible(True)
                self.media_options_btn.set_visible(False)
                self.info_btn.set_visible(False)
                self.return_btn.set_visible(False)
            elif visible_page.get_title() == "Location":
                # Map view header
                self.header.set_title_widget(Adw.WindowTitle(title=self.current_album))
                self.create_change_name_btn.set_visible(False)
                self.create_album_btn.set_visible(False)
                self.delete_media_btn.set_visible(False)
                self.media_options_btn.set_visible(False)
                self.info_btn.set_visible(False)
                self.return_btn.set_visible(True)
            elif visible_page.get_title() == "Edit":
                # Edit view header
                curr_file = f"Editing {os.path.basename(self.media_paths[self.current_index])}"
                self.header.set_title_widget(Adw.WindowTitle(title=curr_file))
                self.create_change_name_btn.set_visible(True)
                self.create_album_btn.set_visible(False)
                self.delete_media_btn.set_visible(False)
                self.media_options_btn.set_visible(False)
                self.info_btn.set_visible(False)
                self.return_btn.set_visible(True)
            else:
                # Grid view header
                self.header.set_title_widget(Adw.WindowTitle(title=self.current_album))
                self.create_album_btn.set_visible(False)
                self.delete_media_btn.set_visible(True)
                self.media_options_btn.set_visible(False)
                self.info_btn.set_visible(False)
                self.return_btn.set_visible(True)

    def on_info_clicked(self, btn):
        current_page = self.navigation_view.get_visible_page()
        if isinstance(current_page, MediaView):
            current_media = self.media_paths[self.current_index]
            properties_view = MediaPropertiesView(current_media, self)

            self.bottom_sheet.set_sheet(properties_view)
            self.bottom_sheet.set_open(True)

    def hide_properties(self, button=None):
        self.bottom_sheet.set_open(False)

    def update_properties_view(self):
        if self.bottom_sheet.get_open():
            current_page = self.navigation_view.get_visible_page()
            if isinstance(current_page, MediaView):
                current_media = self.media_paths[self.current_index]
                properties_view = MediaPropertiesView(current_media, self)
                properties_view.set_vexpand(True)
                self.bottom_sheet.set_content(properties_view)

    def on_media_options_clicked(self, btn):
        current_page = self.navigation_view.get_visible_page()
        if isinstance(current_page, MediaView):
            current_page.open_menu_popup(None)

    def on_return_clicked(self, btn=None):
        # If bottom sheet is open, close it first
        if self.bottom_sheet.get_open():
            self.hide_properties()

        if self.navigation_view.get_visible_page():
            self.navigation_view.pop()

    def on_map_clicked(self, lat, lon):
        self.hide_properties()
        current_page = self.navigation_view.get_visible_page()
        if isinstance(current_page, MediaView):
            # Create a navigation page for the map
            map_page = create_map_page(lat, lon)

            # Push the map page to the navigation stack
            self.navigation_view.push(map_page)

    def create_albums_page(self):
        albums_page = Albums(self)
        albums_page.set_name("albums-square")
        albums_page.set_tag("albumsView")
        return albums_page

    def create_media_view_page(self):
        media_view = MediaView(self)
        media_view.set_halign(Gtk.Align.FILL)
        media_view.set_valign(Gtk.Align.FILL)
        media_view.set_hexpand(True)
        media_view.set_vexpand(True)
        media_view.set_name("mediaView-square")
        media_view.set_tag("mediaView")
        return media_view

    def create_edit_media_view_page(self, curr_pix_buff):
        edit_view = EditView(self, curr_pix_buff)
        edit_view.set_halign(Gtk.Align.FILL)
        edit_view.set_valign(Gtk.Align.FILL)
        edit_view.set_hexpand(True)
        edit_view.set_vexpand(True)
        edit_view.set_name("editView-square")
        edit_view.set_tag("editView")
        return edit_view

    def create_grid_view_page(self, album_name=None):
        media_grid_view = GridView(self, self.thumbnails)
        media_grid_view.set_halign(Gtk.Align.FILL)
        media_grid_view.set_valign(Gtk.Align.FILL)
        media_grid_view.set_hexpand(True)
        media_grid_view.set_vexpand(True)

        media_grid_view.set_name("mediaGridView-square")
        media_grid_view.set_tag(f"gridView-{album_name}")

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

    def open_media_edit(self, media_index: int, media_path: str):
        self.current_index = media_index
        edit_page = self.create_edit_media_view_page(media_path)
        self.navigation_view.push(edit_page)

    def create_album(self, button):
        dialog, entry = create_album_create_dialog(self)

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
            self.selection_bar, self.selected_files_label = create_selection_header_bar(
                label_text, self.on_cancel_selection, self.on_delete_confirmation
            )

            # Restore original header
            self.toolbar_view.remove(self.header)
            self.toolbar_view.add_top_bar(self.selection_bar)

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

        dialog = create_delete_confirmation_dialog(self, heading, body)
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

    def change_file_name(self, _button):
        curr_file_path = self.media_paths[self.current_index]
        initial = FuriOSMediaTools._basename_without_ext(curr_file_path)

        dlg, entry, error_label, rename_btn, cancel_btn = create_rename_dialog(
            self.get_root(),
            initial
        )

        entry.connect("changed", lambda *_: error_label.set_visible(False))

        def do_rename():
            success, text = FuriOSMediaTools.change_file_name(
                curr_file_path,
                entry.get_text().strip()
            )
            if not success:
                error_label.set_text(text)
                error_label.set_visible(True)
                entry.grab_focus()
                entry.select_region(0, -1)
                return

            self.media_paths[self.current_index] = text
            dlg.close()

        rename_btn.connect("clicked", lambda _b: do_rename())
        cancel_btn.connect("clicked", lambda _b: dlg.close())

        dlg.present(self.get_root())
        entry.grab_focus()
        entry.select_region(0, -1)
