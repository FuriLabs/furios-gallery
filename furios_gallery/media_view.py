import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, Gdk, GLib, GdkPixbuf
from .media_manager import setup_media_manager, get_media_paths, get_last_media_url, get_media_from_index
from .video_player_widget import VideoPlayerWidget

class MediaView(Gtk.Box):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.carousel = None
        self.widget = self.create_widget()
        self.append(self.widget)

    def create_widget(self):
        self.overlay = Gtk.Overlay()
        self.overlay.set_size_request(390, 700)
        self.overlay.set_halign(Gtk.Align.CENTER)
        self.overlay.set_valign(Gtk.Align.CENTER)
        self.overlay.set_hexpand(True)
        self.overlay.set_vexpand(True)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_box.set_size_request(390, 700)
        self.main_box.set_halign(Gtk.Align.CENTER)
        self.main_box.set_valign(Gtk.Align.CENTER)
        self.main_box.set_hexpand(True)
        self.main_box.set_vexpand(True)

        self.carousel = self.create_carousel(self.app.current_index)
        self.main_box.append(self.carousel)

        self.index_label = Gtk.Label(label=f"{self.app.current_index + 1}/{len(self.app.media_paths)}")
        self.index_label.set_halign(Gtk.Align.CENTER)
        self.index_label.set_valign(Gtk.Align.END)
        self.index_label.set_margin_bottom(10)
        self.overlay.add_overlay(self.index_label)

        self.add_touch_event_listener(self.overlay)

        self.setup_buttons()

        self.overlay.set_child(self.main_box)
        return self.overlay

    def update_label(self):
        if hasattr(self, "index_label") and self.index_label.get_parent():
            self.overlay.remove_overlay(self.index_label)

        self.index_label = Gtk.Label(label=f"{self.app.current_index + 1}/{len(self.app.media_paths)}")
        self.index_label.set_halign(Gtk.Align.CENTER)
        self.index_label.set_valign(Gtk.Align.END)
        self.index_label.set_margin_bottom(10)

        self.overlay.add_overlay(self.index_label)

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
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(media_path, 420, 700, True)
                    image = Gtk.Picture.new_for_pixbuf(pixbuf)
                    carousel.append(image)
                elif media_path.endswith(('.mp4', '.mkv', '.avi')):
                    video_widget =VideoPlayerWidget(media_path)
                    video_widget.set_halign(Gtk.Align.CENTER)
                    video_widget.set_valign(Gtk.Align.CENTER)
                    carousel.append(video_widget)

    def clear_carousel(self):
        while child:= self.carousel.get_first_child():
            self.carousel.remove(child)

    def on_page_changed(self, carousel, index):
        if hasattr(self, "previous_index"):
            if index > self.previous_index:  # Swiping left
                self.app.current_index -= 1
            elif index < self.previous_index:  # Swiping right
                self.app.current_index += 1
        else:
            print("Initializing previous index.")
            self.previous_index = index

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
        buttons_box.set_halign(Gtk.Align.CENTER)
        buttons_box.set_valign(Gtk.Align.CENTER)
        buttons_box.set_hexpand(True)
        buttons_box.set_vexpand(True)
        buttons_box.set_size_request(40, 80)

        left_button = Gtk.Button(icon_name="go-previous-symbolic")
        left_button.connect('clicked', self.update_media_left)
        left_button.set_hexpand(False)
        buttons_box.append(left_button)

        spacer = Gtk.Box()
        spacer.set_size_request(300, 80)
        spacer.set_hexpand(True)
        buttons_box.append(spacer)

        right_button = Gtk.Button(icon_name="go-next-symbolic")
        right_button.connect('clicked', self.update_media_right)
        right_button.set_hexpand(False)
        buttons_box.append(right_button)

        self.overlay.add_overlay(buttons_box)

    def update_media_left(self, btn):
        self.carousel.scroll_to(self.carousel.get_nth_page(int(self.carousel.get_position()) - 1), True)

        self.on_page_changed(self.carousel, int(self.carousel.get_position()) - 1)

    def update_media_right(self, btn):
        self.carousel.scroll_to(self.carousel.get_nth_page(int(self.carousel.get_position()) + 1), True)

        self.on_page_changed(self.carousel, int(self.carousel.get_position()) + 1)

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
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(media_path, 420, 700, True)
            image = Gtk.Picture.new_for_pixbuf(pixbuf)
            if prepend:
                self.carousel.prepend(image)
            else:
                self.carousel.append(image)

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