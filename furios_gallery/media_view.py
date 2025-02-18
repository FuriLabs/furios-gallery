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

class MediaView(Adw.NavigationPage):
    def __init__(self, app):
        super().__init__(title="Media")
        self.app = app
        self.carousel = None
        self.previous_index = 0
        self.setup_content()

    def setup_content(self):
        # Main content box
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_box.set_halign(Gtk.Align.FILL)
        self.main_box.set_valign(Gtk.Align.FILL)
        self.main_box.set_hexpand(True)
        self.main_box.set_vexpand(True)

        # Overlay for additional UI elements
        self.overlay = Gtk.Overlay()
        self.overlay.set_halign(Gtk.Align.FILL)
        self.overlay.set_valign(Gtk.Align.FILL)
        self.overlay.set_hexpand(True)
        self.overlay.set_vexpand(True)

        # Create the carousel
        self.carousel = Adw.Carousel()
        self.carousel.set_spacing(20)
        self.carousel.set_valign(Gtk.Align.FILL)
        self.carousel.set_halign(Gtk.Align.FILL)
        self.carousel.set_vexpand(True)
        self.carousel.set_hexpand(True)
        self.carousel.connect("page-changed", self.on_page_changed)

        # Populate the carousel
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
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            modal=True,
            heading="Media Options"
        )

        media_options = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        media_options.set_margin_top(10)
        media_options.set_margin_bottom(10)
        media_options.set_margin_start(10)
        media_options.set_margin_end(10)

        def create_button(label, on_click, *args):
            button = Gtk.Button(label=label)
            button.set_hexpand(True)
            button.set_halign(Gtk.Align.FILL)
            button.connect("clicked", on_click, *args)
            return button

        add_to_album_btn = create_button("Add to Album", lambda btn: self.add_to_album(btn, None, dialog))
        media_options.append(add_to_album_btn)

        remove_from_album_btn = create_button("Remove from Album", self.delete_from_album, dialog)
        media_options.append(remove_from_album_btn)

        close_media_options_btn = create_button("Cancel", self.on_close_media_options, dialog)
        media_options.append(close_media_options_btn)

        dialog.set_extra_child(media_options)

        dialog.present()

    def add_to_album(self, btn, add_album_box, first_dialog):
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Add to Album",
            body="Select an album to add the file to:",
        )

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_min_content_height(200)
        scrolled_window.set_min_content_width(300)

        flowbox = Gtk.FlowBox()
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_max_children_per_line(3)
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)

        albums = list_database_albums(self.app.conn)
        for album in albums:
            button = Gtk.Button(label=album)
            button.connect("clicked", self.on_album_button_clicked, album, first_dialog, dialog)
            flowbox.append(button)

        scrolled_window.set_child(flowbox)
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
        delete_file_from_album(self.app.conn, self.app.media_paths[media_to_delete_index], self.app.current_album)
        self.update_carousel()

        albums_view_page = self.app.navigation_view.find_page("albumsView")
        if albums_view_page:
            albums_view_page.update_all_album_thumbnails()

        grid_view_page = self.app.navigation_view.find_page("gridView")
        if grid_view_page:
            grid_view_page.delete_media_from_flowbox(media_to_delete_index)

        dialog.destroy()

    def on_close_media_options(self, btn, dialog):
        dialog.destroy()

    def open_delete_popup(self, btn):
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Delete File?",
            body="This will permanently delete the file from your system"
        )

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        dialog.connect("response", self.on_delete_media)

        dialog.present()

    def on_delete_media(self, dialog, response):
        if response == "delete":
            try:
                file_url = self.app.media_paths[self.app.current_index]
                delete_from_albums(self.app.conn, file_url)
                colon_index = file_url.find(':')
                if colon_index != -1:
                    file_path = file_url[colon_index + 1:]
                else:
                    file_path = file_url

                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"File deleted: {file_path}")

                    media_to_delete_index = self.app.current_index

                    self.update_carousel()

                    albums_view_page = self.app.navigation_view.find_page("albumsView")
                    if albums_view_page:
                        albums_view_page.update_all_album_thumbnails()

                    grid_view_page = self.app.navigation_view.find_page("gridView")
                    if grid_view_page:
                        grid_view_page.delete_media_from_flowbox(media_to_delete_index)

                    return True
                else:
                    print(f"File not found: {file_path}")
                    return False
            except Exception as e:
                print(f"Error deleting file: {e}")
                return False
        dialog.destroy()

    def update_carousel(self):
        if 0 <= self.app.current_index < len(self.app.media_paths):
            current_page = self.carousel.get_nth_page(self.carousel.get_position())
            if current_page:
                self.carousel.remove(current_page)

            del self.app.media_paths[self.app.current_index]

            if self.app.current_index >= len(self.app.media_paths):
                self.app.current_index = max(0, len(self.app.media_paths) - 1)

            self.clear_carousel()
            self.populate_carousel(self.carousel, self.app.current_index)

            self.update_date_label()
        else:
            print("Error: Current index is out of range.")

    def update_date_label(self):
        if len(self.app.media_paths) > 0:
            new_date = get_file_creation_date(self.app.media_paths[self.app.current_index])
            self.app.header.set_title_widget(Adw.WindowTitle(title=new_date))

    def populate_carousel(self, carousel, curr_index):
        # 1.- First append the first chil from the first child
        # 2.- Then determine one of the 3 scenarios:
        # --> Media index is the first of the album (index = 0)
        # --> Media index is the last of the album (index = len(self.app.media_paths))
        # --> Media index is not either of the either cases (being careful with the length of the list)

        media_path = self.app.media_paths[curr_index]
        if media_path.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            scrolled_win = Gtk.ScrolledWindow()
            scrolled_win.set_hexpand(True)
            scrolled_win.set_vexpand(True)
            scrolled_win.set_halign(Gtk.Align.FILL)
            scrolled_win.set_valign(Gtk.Align.FILL)
            zoomable_image = ImageViewerWidget(media_path, self.app, scrolled_win)
            zoomable_image.set_vexpand(True)
            zoomable_image.set_hexpand(True)
            zoomable_image.set_valign(Gtk.Align.CENTER)
            zoomable_image.set_halign(Gtk.Align.CENTER)
            scrolled_win.set_child(zoomable_image)
            zoomable_image.init_gestures()
            carousel.append(scrolled_win)
        elif media_path.endswith(('.mp4', '.mkv', '.avi')):
            video_widget = VideoPlayerWidget(media_path)
            video_widget.set_halign(Gtk.Align.CENTER)
            video_widget.set_valign(Gtk.Align.CENTER)
            carousel.append(video_widget)

        if curr_index == 0:
            # Load the last (if existant) 2 items and preappend to the carousel
            self.add_media_to_carousel(curr_index + 1, True)
            self.add_media_to_carousel(curr_index + 2, True)
        elif curr_index == len(self.app.media_paths) -1:
            # Load the next (if existant) 2 items and append to the carousel
            self.add_media_to_carousel(curr_index - 1, False)
            self.add_media_to_carousel(curr_index - 2, False)
        else:
            # Load the next 2 and previous 2 (if existant) items and pre and append them accordingly
            self.add_media_to_carousel(curr_index + 1, True)
            self.add_media_to_carousel(curr_index - 1, False)
            self.add_media_to_carousel(curr_index + 2, True)
            self.add_media_to_carousel(curr_index - 2, False)

    def clear_carousel(self):
        while child := self.carousel.get_first_child():
            self.carousel.remove(child)

    def on_page_changed(self, carousel, index):
        prev_page = self.carousel.get_nth_page(self.previous_index)
        if isinstance(prev_page, VideoPlayerWidget):
            prev_page.stop_video()

        self.update_date_label()

        if index > self.previous_index:  # Swiping left
            self.app.current_index -= 1
            if index == carousel.get_n_pages() - 1:
                self.add_media_to_carousel(self.app.current_index - 1, False)
        elif index < self.previous_index:  # Swiping right
            self.app.current_index += 1
            if index == carousel.get_n_pages() - 1:
                self.add_media_to_carousel(self.app.current_index + 1, True)
        else:
            return

        self.app.update_properties_view()

        self.previous_index = index

    def setup_buttons(self):
        buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        buttons_box.set_halign(Gtk.Align.FILL)
        buttons_box.set_valign(Gtk.Align.CENTER)
        buttons_box.set_hexpand(True)
        buttons_box.set_vexpand(True)

        left_button = Gtk.Button(icon_name="go-previous-symbolic")
        left_button.connect('clicked', self.update_media_left)
        left_button.set_hexpand(False)
        buttons_box.append(left_button)

        spacer = Gtk.Box()
        spacer.set_halign(Gtk.Align.FILL)
        spacer.set_hexpand(True)
        buttons_box.append(spacer)

        right_button = Gtk.Button(icon_name="go-next-symbolic")
        right_button.connect('clicked', self.update_media_right)
        right_button.set_hexpand(False)
        buttons_box.append(right_button)

        self.overlay.add_overlay(buttons_box)

    def update_media_left(self, btn):
        next_position = int(self.carousel.get_position()) - 1
        if next_position >= 0 and self.app.current_index + 1 <= len(self.app.media_paths) - 1:
            self.on_page_changed(self.carousel, next_position)
            self.carousel.scroll_to(self.carousel.get_nth_page(next_position), True)

    def update_media_right(self, btn):
        next_position = int(self.carousel.get_position()) + 1
        if next_position < len(self.app.media_paths) and next_position < self.carousel.get_n_pages():
            self.on_page_changed(self.carousel, next_position)
            self.carousel.scroll_to(self.carousel.get_nth_page(next_position), True)

    def add_touch_event_listener(self, widget):
        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", self.on_screen_touched)
        widget.add_controller(gesture)

    def on_screen_touched(self, gesture, n_press, x, y):
        if isinstance(self.carousel.get_first_child(), VideoPlayerWidget):
            video_widget = self.carousel.get_first_child()
            video_widget.on_video_clicked(None)

    def add_media_to_carousel(self, index, prepend=False):
        if index > len(self.app.media_paths) -1 or index < 0:
            return # Only append if its not out of boundaries

        media_path = self.app.media_paths[index]

        if media_path.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            scrolled_win = Gtk.ScrolledWindow()
            zoomable_image = ImageViewerWidget(media_path, self.app, scrolled_win)
            zoomable_image.set_vexpand(True)
            zoomable_image.set_hexpand(True)
            zoomable_image.set_valign(Gtk.Align.CENTER)
            zoomable_image.set_halign(Gtk.Align.CENTER)
            scrolled_win.set_child(zoomable_image)
            zoomable_image.init_gestures()

            if prepend:
                self.carousel.prepend(scrolled_win)
            else:
                self.carousel.append(scrolled_win)
        elif media_path.endswith(('.mp4', '.mkv', '.avi')):
            video_widget = VideoPlayerWidget(media_path)
            video_widget.set_halign(Gtk.Align.CENTER)
            video_widget.set_valign(Gtk.Align.CENTER)
            if prepend:
                self.carousel.prepend(video_widget)
            else:
                self.carousel.append(video_widget)
