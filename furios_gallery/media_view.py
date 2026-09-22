# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>
# Bardia Moshiri <bardia@furilabs.com>
# Jesús Higueras <jesus@furilabs.com>
# Luis Garcia <git@luigi311.com>

import gi, os
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
from .video_player_widget import VideoPlayerWidget
from .image_viewer_widget import ImageViewerWidget
from .media_manager import get_file_creation_date
from .database_manager import delete_from_albums, delete_file_from_album, list_database_albums, add_file_to_album
from .ui import (
    create_media_view_main_box, create_media_view_overlay, create_media_view_carousel,
    create_media_navigation_buttons, create_media_options_dialog, create_media_options_content,
    create_option_button, create_album_selection_dialog, create_album_selection_content,
    create_delete_confirmation_dialog
)

class MediaView(Adw.NavigationPage):
    def __init__(self, app):
        super().__init__(title="Media")
        self.app = app
        self.carousel = None
        self._updating_carousel = False
        self._active_page = None
        self.setup_content()

    def setup_content(self):
        # Main content box
        self.main_box = create_media_view_main_box()

        # Overlay for additional UI elements
        self.overlay = create_media_view_overlay()

        # Create the carousel
        self.carousel = create_media_view_carousel(self.on_page_changed)

        # Populate the carousel
        if self.app.media_paths:
            self.populate_carousel(self.carousel, self.app.current_index)

        self.main_box.append(self.carousel)

        # Add touch event listener
        self.add_touch_event_listener(self.overlay)

        # Setup navigation and overlay buttons
        self.setup_buttons()

        # Set overlay child
        self.overlay.set_child(self.main_box)

        # Set content for NavigationPage
        self.set_child(self.overlay)

        # Disable gesture navigation
        self.set_can_pop(False)

        if len(self.app.media_paths) > 0:
            new_date = get_file_creation_date(self.app.media_paths[self.app.current_index])
            # this is a bit of a hack since setting this immediately here for some reason doesn't update the header
            GLib.timeout_add(5, self.update_header_title, new_date)

    def update_header_title(self, date):
        self.app.header.set_title_widget(Adw.WindowTitle(title=date))
        self.app.update_properties_view()

    def open_menu_popup(self, btn):
        dialog = create_media_options_dialog(self.get_root())

        media_options = create_media_options_content()

        add_to_album_btn = create_option_button("Add to Album", lambda btn: self.add_to_album(btn, None, dialog))
        media_options.append(add_to_album_btn)

        remove_from_album_btn = create_option_button("Remove from Album", self.delete_from_album, dialog)
        media_options.append(remove_from_album_btn)

        media_path = self.app.media_paths[self.app.current_index]
        if media_path.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            edit_medit_btn = create_option_button(
                "Edit Media",
                lambda _btn: (
                    dialog.close(),
                    self.app.open_media_edit(self.app.current_index, self.app.media_paths[self.app.current_index])
                )
            )

            media_options.append(edit_medit_btn)

        close_media_options_btn = create_option_button("Cancel", self.on_close_media_options, dialog)
        media_options.append(close_media_options_btn)

        dialog.set_extra_child(media_options)

        dialog.present()

    def add_to_album(self, btn, add_album_box, first_dialog):
        dialog = create_album_selection_dialog(
            self.get_root(),
            "Add to Album",
            "Select an album to add the file to:"
        )

        scrolled_window, flowbox = create_album_selection_content()

        albums = list_database_albums(self.app.conn)
        for album in albums:
            button = Gtk.Button(label=album)
            button.connect("clicked", self.on_album_button_clicked, album, first_dialog, dialog)
            flowbox.append(button)

        dialog.set_extra_child(scrolled_window)

        dialog.add_response("cancel", "Cancel")
        dialog.set_response_appearance("cancel", Adw.ResponseAppearance.DESTRUCTIVE)

        dialog.connect("response", lambda dialog, response: dialog.destroy())
        dialog.present()

    def on_album_button_clicked(self, btn, album_name, first_dialog, second_dialog):
        try:
            file_path = self.app.media_paths[self.app.current_index]
            add_file_to_album(self.app.conn, file_path, album_name)

            albums_view_page = self.app.navigation_view.find_page("albumsView")
            if albums_view_page:
                albums_view_page.update_all_album_thumbnails()

            second_dialog.destroy()
            first_dialog.destroy()
            print(f"Successfully added {file_path} to album '{album_name}'")
        except Exception as e:
            print(f"Error adding file to album '{album_name}': {e}")

    def delete_from_album(self, btn, dialog):
        media_to_delete_index = self.app.current_index
        media_to_delete_path = self.app.media_paths[media_to_delete_index]
        delete_file_from_album(self.app.conn, media_to_delete_path, self.app.current_album)
        self.update_carousel()

        albums_view_page = self.app.navigation_view.find_page("albumsView")
        if albums_view_page:
            albums_view_page.update_all_album_thumbnails()

        grid_view_page = self.app.navigation_view.find_page(f"gridView-{self.app.current_album}")
        if grid_view_page:
            grid_view_page.delete_media_from_flowbox(media_to_delete_path)

        dialog.destroy()

    def on_close_media_options(self, btn, dialog):
        dialog.destroy()

    def open_delete_popup(self, btn):
        dialog = create_delete_confirmation_dialog(
            self.get_root(),
            "Delete File?",
            "This will permanently delete the file from your system"
        )

        dialog.connect("response", self.on_delete_media)

        dialog.present()

    def on_delete_media(self, dialog, response):
        if response == "delete":
            try:
                media_to_delete_path = self.app.media_paths[self.app.current_index]
                delete_from_albums(self.app.conn, media_to_delete_path)

                if os.path.exists(media_to_delete_path):
                    os.remove(media_to_delete_path)
                    print(f"File deleted: {media_to_delete_path}")
                else:
                    print(f"File not found: {media_to_delete_path}")

                self.update_carousel()

                albums_view_page = self.app.navigation_view.find_page("albumsView")
                if albums_view_page:
                    albums_view_page.update_all_album_thumbnails()

                grid_view_page = self.app.navigation_view.find_page(f"gridView-{self.app.current_album}")
                if grid_view_page:
                    grid_view_page.delete_media_from_flowbox(media_to_delete_path)
            except Exception as e:
                print(f"Error deleting file: {e}")

        dialog.destroy()

    def update_carousel(self):
        if not 0 <= self.app.current_index < len(self.app.media_paths):
            print("Error: Current index is out of range.")
            return

        deleted_index = self.app.current_index
        del self.app.media_paths[deleted_index]

        if not self.app.media_paths:
            self.app.current_index = 0
            self._updating_carousel = True
            try:
                self.clear_carousel()
            finally:
                self._updating_carousel = False
            self._active_page = None
            self.app.header.set_title_widget(Adw.WindowTitle(title="Media"))
            self.update_navigation_buttons()
            return

        # Keep the same numeric index so the item that shifted into the deleted
        # item's position is shown. If the last item was deleted, show the new last item.
        self.app.current_index = min(deleted_index, len(self.app.media_paths) - 1)
        self.rebuild_carousel()
        self.update_date_label()
        self.update_navigation_buttons()
        self.app.update_properties_view()

    def update_date_label(self):
        if len(self.app.media_paths) > 0:
            new_date = get_file_creation_date(self.app.media_paths[self.app.current_index])
            self.app.header.set_title_widget(Adw.WindowTitle(title=new_date))

    def create_media_page(self, index):
        if index < 0 or index >= len(self.app.media_paths):
            return None

        media_path = self.app.media_paths[index]

        if media_path.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            page = Gtk.ScrolledWindow()
            page.set_hexpand(True)
            page.set_vexpand(True)
            page.set_halign(Gtk.Align.FILL)
            page.set_valign(Gtk.Align.FILL)
            zoomable_image = ImageViewerWidget(media_path, self.app, page)
            zoomable_image.set_vexpand(True)
            zoomable_image.set_hexpand(True)
            zoomable_image.set_valign(Gtk.Align.CENTER)
            zoomable_image.set_halign(Gtk.Align.CENTER)
            page.set_child(zoomable_image)
            zoomable_image.init_gestures()
        elif media_path.endswith(('.mp4', '.mkv', '.avi')):
            page = VideoPlayerWidget(media_path)
            page.set_halign(Gtk.Align.CENTER)
            page.set_valign(Gtk.Align.CENTER)
        else:
            return None

        page.media_index = index
        return page

    def populate_carousel(self, carousel, curr_index):
        if not self.app.media_paths:
            return

        curr_index = min(max(curr_index, 0), len(self.app.media_paths) - 1)
        first_index = min(curr_index + 2, len(self.app.media_paths) - 1)
        last_index = max(curr_index - 2, 0)
        current_page = None

        old_updating_state = self._updating_carousel
        self._updating_carousel = True
        try:
            for media_index in range(first_index, last_index - 1, -1):
                page = self.create_media_page(media_index)
                if page is None:
                    continue

                carousel.append(page)
                if media_index == curr_index:
                    current_page = page

            if current_page is not None:
                carousel.scroll_to(current_page, False)
                self._active_page = current_page
        finally:
            self._updating_carousel = old_updating_state

    def rebuild_carousel(self):
        old_updating_state = self._updating_carousel
        self._updating_carousel = True
        try:
            self.clear_carousel()
            self.populate_carousel(self.carousel, self.app.current_index)
        finally:
            self._updating_carousel = old_updating_state

    def clear_carousel(self):
        child = self.carousel.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            if isinstance(child, VideoPlayerWidget):
                child.stop_video()
            self.carousel.remove(child)
            child = next_child

    def find_page_for_media_index(self, media_index):
        for page_index in range(self.carousel.get_n_pages()):
            page = self.carousel.get_nth_page(page_index)
            if page is not None and page.media_index == media_index:
                return page
        return None

    def on_page_changed(self, carousel, index):
        if self._updating_carousel:
            return

        page_index = int(index)
        page_count = carousel.get_n_pages()
        if page_index < 0 or page_index >= page_count:
            return

        current_page = carousel.get_nth_page(page_index)
        if current_page is None:
            return

        if self._active_page is not None and self._active_page is not current_page:
            if isinstance(self._active_page, VideoPlayerWidget):
                self._active_page.stop_video()

        media_index = current_page.media_index
        if media_index < 0 or media_index >= len(self.app.media_paths):
            return

        self._active_page = current_page
        self.app.current_index = media_index

        # Extend the carousel by one item when reaching either loaded edge.
        if page_index == 0:
            self.add_media_to_carousel(media_index + 1, True)
        elif page_index == page_count - 1:
            self.add_media_to_carousel(media_index - 1, False)

        self.update_date_label()
        self.update_navigation_buttons()
        self.app.update_properties_view()

    def setup_buttons(self):
        buttons_box = create_media_navigation_buttons(self.update_media_left, self.update_media_right)
        self.left_button = buttons_box.get_first_child()
        self.right_button = buttons_box.get_last_child()
        self.overlay.add_overlay(buttons_box)
        self.update_navigation_buttons()

    def update_navigation_buttons(self):
        if not self.app.media_paths:
            self.left_button.set_sensitive(False)
            self.right_button.set_sensitive(False)
            return

        # The carousel is ordered from higher media indexes on the left to lower
        # media indexes on the right to preserve the existing navigation direction.
        self.left_button.set_sensitive(self.app.current_index < len(self.app.media_paths) - 1)
        self.right_button.set_sensitive(self.app.current_index > 0)

    def update_media_left(self, btn):
        target_index = self.app.current_index + 1
        if target_index >= len(self.app.media_paths):
            return

        target_page = self.find_page_for_media_index(target_index)
        if target_page is None:
            target_page = self.add_media_to_carousel(target_index, True)

        if target_page is not None:
            self.carousel.scroll_to(target_page, True)

    def update_media_right(self, btn):
        target_index = self.app.current_index - 1
        if target_index < 0:
            return

        target_page = self.find_page_for_media_index(target_index)
        if target_page is None:
            target_page = self.add_media_to_carousel(target_index, False)

        if target_page is not None:
            self.carousel.scroll_to(target_page, True)

    def add_touch_event_listener(self, widget):
        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", self.on_screen_touched)
        widget.add_controller(gesture)

    def on_screen_touched(self, gesture, n_press, x, y):
        current_page = self.find_page_for_media_index(self.app.current_index)
        if isinstance(current_page, VideoPlayerWidget):
            current_page.on_video_clicked(None)

    def add_media_to_carousel(self, index, prepend=False):
        if index > len(self.app.media_paths) - 1 or index < 0:
            return None

        existing_page = self.find_page_for_media_index(index)
        if existing_page is not None:
            return existing_page

        page = self.create_media_page(index)
        if page is None:
            return None

        old_updating_state = self._updating_carousel
        self._updating_carousel = True
        try:
            if prepend:
                self.carousel.prepend(page)
            else:
                self.carousel.append(page)
        finally:
            self._updating_carousel = old_updating_state

        return page
