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
        self.albums_box = None
        self.mediaView_box = None
        self.mediaGridView_box = None
        self.media_paths = get_media_paths()
        self.current_index = len(get_media_paths()) - 1

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
        self.win.set_title('Experiment Panels')

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_content(self.main_box)
        menu_label = Gtk.Label(label="FuriOS Gallery")
        self.main_box.append(menu_label)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(500)

        self.create_menu_buttons()

        self.stack_switcher = Gtk.StackSwitcher()
        self.stack_switcher.set_stack(self.stack)
        self.main_box.append(self.stack_switcher)

        self.current_view = self.create_media_view_box()

        self.main_box.append(self.current_view)

        self.win.present()

    def create_menu_buttons(self):
        self.stack.add_titled(Gtk.Label(), "albums_view", "albums_view")
        self.stack.add_titled(Gtk.Label(), "media_view", "media_view")
        self.stack.add_titled(Gtk.Label(), "media_grid_view", "grid_view")

        self.stack.set_visible_child_name("media_view")

        self.stack.connect("notify::visible-child", self.switch_view)

    def create_media_view_box(self):
        mediaView_box = MediaView(self)

        mediaView_box.widget.set_size_request(420, 700)
        mediaView_box.widget.set_halign(Gtk.Align.CENTER)
        mediaView_box.widget.set_valign(Gtk.Align.CENTER)
        mediaView_box.widget.set_hexpand(True)
        mediaView_box.widget.set_vexpand(True)

        mediaView_box.widget.set_name("mediaView-square")

        return mediaView_box

    def create_grid_view_box(self):
        mediaGridView_square = GridView(self, self.thumbnails)
        mediaGridView_square.set_size_request(420, 800)
        mediaGridView_square.set_halign(Gtk.Align.CENTER)
        mediaGridView_square.set_valign(Gtk.Align.CENTER)
        mediaGridView_square.set_hexpand(True)
        mediaGridView_square.set_vexpand(True)

        if mediaGridView_square.flowbox is not None:
            self.thumbnails.load_images_in_background(self.media_paths, mediaGridView_square.flowbox)

        mediaGridView_square.set_name("mediaGridView-square")
        return mediaGridView_square

    def create_albums_box(self):
        albums_square = Albums(self)
        albums_square.set_size_request(420, 800)
        albums_square.set_halign(Gtk.Align.CENTER)
        albums_square.set_valign(Gtk.Align.CENTER)
        albums_square.set_hexpand(True)
        albums_square.set_vexpand(True)

        albums_square.set_name("albums-square")

        return albums_square

    def switch_view(self, stack, param):
        for child in list(self.current_view):
            self.current_view.remove(child)

        visible_child_name = self.stack.get_visible_child_name()
        if visible_child_name == "albums_view":
            self.albums_box = self.create_albums_box()
            self.current_view.append(self.albums_box)
        elif visible_child_name == "media_view":
            self.mediaView_box = self.create_media_view_box()
            self.current_view.append(self.mediaView_box)
        elif visible_child_name == "media_grid_view":
            self.mediaGridView_box = self.create_grid_view_box()
            self.current_view.append(self.mediaGridView_box)
        else:
            print("Not a possible state")

    def open_media_at_index(self, media_index):
        self.stack.set_visible_child_name("media_view")

        for child in list(self.current_view):
            self.current_view.remove(child)

        if not self.mediaView_box:
            self.mediaView_box = self.create_media_view_box()
        self.current_view.append(self.mediaView_box)

    def open_album(self, album_name):
        self.albums_box.flowbox.unselect_all()
        self.media_paths = get_album_media_paths(album_name)
        self.current_index = len(self.media_paths) - 1

        self.stack.set_visible_child_name("media_grid_view")

    def open_videos_album(self):
        self.albums_box.flowbox.unselect_all()
        self.media_paths = get_videos_paths()
        self.current_index = len(self.media_paths) - 1

        self.stack.set_visible_child_name("media_grid_view")

    def open_pictures_album(self):
        self.albums_box.flowbox.unselect_all()
        self.media_paths = get_pictures_paths()
        self.current_index = len(self.media_paths) - 1

        self.stack.set_visible_child_name("media_grid_view")