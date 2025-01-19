from gi.repository import Gtk, Adw, Gdk
from .media_view import MediaView
from .grid_view import GridView
from .albums_view import Albums
from .thumbnail_generator import ThumbnailGenerator
from .media_manager import setup_media_manager, get_media_paths, get_last_media_url, get_pictures_paths, get_videos_paths, get_album_media_paths

class FuriosGalleryApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='io.FuriOS.Gallery')
        self.thumbnails = ThumbnailGenerator()
        setup_media_manager()
        self.media_paths = get_media_paths()
        self.current_index = len(get_media_paths()) - 1
        self.current_view = None

    def do_activate(self):
        self.setup_window()

    def get_screen_size(self):
        display = Gdk.Display.get_default()

        monitors = display.get_monitors()

        if monitors.get_n_items() == 0:
            raise RuntimeError("No monitors found")

        monitor = monitors.get_item(0)

        geometry = monitor.get_geometry()

        screen_width = geometry.width
        screen_height = geometry.height

        return screen_width, screen_height

    def setup_window(self):
        screen_width, screen_height = self.get_screen_size()
        print(f"Screen width: {screen_width}, Screen height: {screen_height}")

        self.win = Adw.ApplicationWindow(application=self)
        self.win.set_default_size(screen_width, screen_height)
        self.win.set_hexpand(True)
        self.win.set_vexpand(True)
        self.win.set_title('Gallery')

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_content(self.main_box)
        menu_label = Gtk.Label(label="Gallery")
        self.main_box.append(menu_label)

        self.current_view = self.create_albums_box()
        self.main_box.append(self.current_view)

        self.win.present()

    def create_media_view_box(self):
        media_view_box = MediaView(self)
        media_view_box.widget.set_size_request(420, 700)
        media_view_box.widget.set_halign(Gtk.Align.CENTER)
        media_view_box.widget.set_valign(Gtk.Align.CENTER)
        media_view_box.widget.set_hexpand(True)
        media_view_box.widget.set_vexpand(True)
        media_view_box.widget.set_name("mediaView-square")
        return media_view_box

    def create_grid_view_box(self):
        media_grid_view_box = GridView(self, self.thumbnails)
        media_grid_view_box.set_size_request(420, 800)
        media_grid_view_box.set_halign(Gtk.Align.CENTER)
        media_grid_view_box.set_valign(Gtk.Align.CENTER)
        media_grid_view_box.set_hexpand(True)
        media_grid_view_box.set_vexpand(True)

        if media_grid_view_box.flowbox is not None:
            self.thumbnails.load_images_in_background(self.media_paths, media_grid_view_box.flowbox)

        media_grid_view_box.set_name("mediaGridView-square")
        return media_grid_view_box

    def create_albums_box(self):
        albums_box = Albums(self)
        albums_box.set_size_request(420, 800)
        albums_box.set_halign(Gtk.Align.CENTER)
        albums_box.set_valign(Gtk.Align.CENTER)
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
        self.media_paths = get_album_media_paths(album_name)
        self.current_index = len(self.media_paths) - 1
        self.switch_to_view(self.create_grid_view_box)

    def open_videos_album(self):
        self.media_paths = get_videos_paths()
        self.current_index = len(self.media_paths) - 1
        self.switch_to_view(self.create_grid_view_box)

    def open_pictures_album(self):
        self.media_paths = get_pictures_paths()
        self.current_index = len(self.media_paths) - 1
        self.switch_to_view(self.create_grid_view_box)
