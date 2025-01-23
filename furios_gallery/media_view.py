# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import gi, os
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, Gdk, GdkPixbuf
from .video_player_widget import VideoPlayerWidget
from .image_viewer_widget import ImageViewerWidget
from .media_manager import get_file_creation_date, delete_from_albums, delete_file_from_album, list_database_albums, add_file_to_album

class MediaView(Adw.NavigationPage):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.carousel = None
        self.previous_index = 0
        self.setup_css()
        self.setup_content()

    def setup_css(self):
        css_provider = Gtk.CssProvider()

        css_provider.load_from_data(b"""
        .media-menu-box {
            background-color: #333;
            padding: 15px; /* Increase padding inside the box */
        }
        .delete-btn {
            padding: 5px;
        }
        .test {
            background-color: #239;
        }
        """
        )

        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

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

        # Media menu box
        curr_index = self.app.current_index
        self.media_menu_box = self.create_media_menu_box(curr_index)
        self.main_box.append(self.media_menu_box)

        # Carousel
        self.carousel = self.create_carousel(curr_index)
        self.carousel.set_valign(Gtk.Align.FILL)
        self.carousel.set_halign(Gtk.Align.FILL)
        self.carousel.set_vexpand(True)
        self.carousel.set_hexpand(True)
        self.main_box.append(self.carousel)

        # Index label
        self.index_label = Gtk.Label(label=f"{curr_index + 1}/{len(self.app.media_paths)}")
        self.index_label.set_halign(Gtk.Align.CENTER)
        self.index_label.set_valign(Gtk.Align.END)
        self.index_label.set_margin_bottom(10)
        self.overlay.add_overlay(self.index_label)

        # Add touch event listener
        self.add_touch_event_listener(self.overlay)

        # Setup navigation and overlay buttons
        self.setup_buttons()

        # Set overlay child
        self.overlay.set_child(self.main_box)

        # Set content for NavigationPage
        self.set_child(self.overlay)

        # Set title
        self.set_title("Media View")

    def create_media_menu_box(self, curr_index):
        media_menu_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        media_menu_box.set_hexpand(True)
        media_menu_box.set_halign(Gtk.Align.FILL)
        media_menu_box.set_css_classes(["media-menu-box"])

        return_to_albums_btn = Gtk.Button(icon_name="application-exit-rtl-symbolic")
        return_to_albums_btn.set_size_request(50,40)
        return_to_albums_btn.set_halign(Gtk.Align.START)
        return_to_albums_btn.connect("clicked", self.on_return_to_albums_view)
        media_menu_box.append(return_to_albums_btn)

        self.date_label = Gtk.Label(label=get_file_creation_date(self.app.media_paths[curr_index]))
        self.date_label.set_hexpand(True)
        self.date_label.set_halign(Gtk.Align.FILL)
        media_menu_box.append(self.date_label)

        delete_media_btn = Gtk.Button(icon_name="user-trash-symbolic")
        delete_media_btn.set_margin_end(5)
        delete_media_btn.set_size_request(50,40)
        delete_media_btn.set_css_classes(["delete-btn"])
        delete_media_btn.set_halign(Gtk.Align.END)
        delete_media_btn.connect("clicked", self.open_delete_popup)
        media_menu_box.append(delete_media_btn)

        more_info_menu = Gtk.Button(icon_name="view-more-symbolic")
        more_info_menu.set_size_request(50,40)
        more_info_menu.set_halign(Gtk.Align.END)
        more_info_menu.connect("clicked", self.open_menu_popup)
        media_menu_box.append(more_info_menu)

        return media_menu_box

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

        add_to_album_btn = create_button("Add to Album", self.add_to_album, dialog)
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
            second_dialog.destroy()
            first_dialog.destroy()
            print(f"Successfully added {file_path} to album '{album_name}'")
        except Exception as e:
            print(f"Error adding file to album '{album_name}': {e}")

    def delete_from_album(self, btn, dialog):
        delete_file_from_album(self.app.conn, self.app.media_paths[self.app.current_index], self.app.current_album)
        dialog.destroy()

    def on_close_media_options(self, btn, dialog):
        dialog.destroy()

    def on_return_to_albums_view(self, btn):
        # Assuming the app has a navigation view method to go back
        if hasattr(self.app, 'navigation_view'):
            self.app.navigation_view.pop()
        else:
            # Fallback to app's method of switching views
            self.app.switch_to_view(self.app.create_albums_box)

    def open_delete_popup(self, btn):
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Delete File?",
            body="This will permanently delete the file from your system"
        )

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        dialog.connect("response", lambda dialog, response: self.on_delete_media(dialog, response))

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

                    self.update_carousel()
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

            self.update_label()
            self.update_date_label()
        else:
            print("Error: Current index is out of range.")

    def update_label(self):
        if hasattr(self, "index_label") and self.index_label.get_parent():
            self.overlay.remove_overlay(self.index_label)

        self.index_label = Gtk.Label(label=f"{self.app.current_index + 1}/{len(self.app.media_paths)}")
        self.index_label.set_halign(Gtk.Align.CENTER)
        self.index_label.set_valign(Gtk.Align.END)
        self.index_label.set_margin_bottom(10)

        self.overlay.add_overlay(self.index_label)

    def update_date_label(self):
        new_date = get_file_creation_date(self.app.media_paths[self.app.current_index])
        self.date_label.set_text(new_date)

    def create_carousel(self, curr_index):
        carousel = Adw.Carousel()
        carousel.set_spacing(20)
        carousel.set_halign(Gtk.Align.CENTER)
        carousel.set_valign(Gtk.Align.CENTER)
        carousel.connect("page-changed", self.on_page_changed)

        self.populate_carousel(carousel, curr_index)

        return carousel

    def populate_carousel(self, carousel, curr_index):
        start_index = curr_index
        end_index = max(curr_index - 5, -1)

        for i in range(start_index, end_index, -1):
            if 0 <= i < len(self.app.media_paths):
                media_path = self.app.media_paths[i]
                if media_path.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    scrolled_win = Gtk.ScrolledWindow()
                    scrolled_win.set_hexpand(True)
                    scrolled_win.set_vexpand(True)
                    scrolled_win.set_halign(Gtk.Align.FILL)
                    scrolled_win.set_valign(Gtk.Align.FILL)
                    zoomable_image = ImageViewerWidget(media_path, self.app)
                    zoomable_image.set_vexpand(True)
                    zoomable_image.set_hexpand(True)
                    zoomable_image.set_valign(Gtk.Align.CENTER)
                    scrolled_win.set_child(zoomable_image)
                    zoomable_image.init_gestures()
                    carousel.append(scrolled_win)
                elif media_path.endswith(('.mp4', '.mkv', '.avi')):
                    video_widget = VideoPlayerWidget(media_path)
                    video_widget.set_halign(Gtk.Align.CENTER)
                    video_widget.set_valign(Gtk.Align.CENTER)
                    carousel.append(video_widget)

    def clear_carousel(self):
        while child := self.carousel.get_first_child():
            self.carousel.remove(child)

    def on_page_changed(self, carousel, index):
        self.update_date_label()

        if index > self.previous_index:  # Swiping left
            self.app.current_index -= 1
        elif index < self.previous_index:  # Swiping right
            self.app.current_index += 1

        self.previous_index = index
        self.update_label()

        if index == 0:
            new_start = self.app.current_index + 1
            new_end = min(self.app.current_index + 4, len(self.app.media_paths) - 1)
            for i in range(new_start, new_end + 1):
                if 0 <= i < len(self.app.media_paths):
                    self.add_media_to_carousel(i, prepend=True)

        elif index == carousel.get_n_pages() - 1:
            new_start = self.app.current_index - 1
            new_end = max(self.app.current_index - 4, 0)
            for i in range(new_end, new_start + 1):
                if 0 <= i < len(self.app.media_paths):
                    self.add_media_to_carousel(i, prepend=False)

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
        if (self.app.current_index + 1 <= len(self.app.media_paths) - 1):
            self.carousel.scroll_to(self.carousel.get_nth_page(int(self.carousel.get_position()) - 1), True)
            self.on_page_changed(self.carousel, int(self.carousel.get_position()) - 1)
        else:
            print("no more prior things")

    def update_media_right(self, btn):
        if (self.app.current_index + 1 > 0):
            self.carousel.scroll_to(self.carousel.get_nth_page(int(self.carousel.get_position()) + 1), True)
            self.on_page_changed(self.carousel, int(self.carousel.get_position()) + 1)
        else:
            print("no more after things")

    def add_touch_event_listener(self, widget):
        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", self.on_screen_touched)
        widget.add_controller(gesture)

    def on_screen_touched(self, gesture, n_press, x, y):
        if isinstance(self.carousel.get_first_child(), VideoPlayerWidget):
            video_widget = self.carousel.get_first_child()
            video_widget.on_video_clicked(None)

    def add_media_to_carousel(self, index, prepend=False):
        media_path = self.app.media_paths[index]

        if media_path.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            scrolled_win = Gtk.ScrolledWindow()
            zoomable_image = ImageViewerWidget(media_path, self.app)
            zoomable_image.set_vexpand(True)
            zoomable_image.set_hexpand(True)
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

    def remove_excess_items(self, prepend):
        max_items = 7
        num_pages = self.carousel.get_n_pages()

        while num_pages > max_items:
            if prepend:
                self.carousel.remove(self.carousel.get_nth_page(num_pages - 1))
            else:
                self.carousel.remove(self.carousel.get_nth_page(0))

            num_pages = self.carousel.get_n_pages()
