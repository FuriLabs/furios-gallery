from gi.repository import Gtk, Adw, Gdk
from .media_manager import setup_media_manager, get_media_paths, get_last_media_url

class FuriosGalleryApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='io.FuriOS.Gallery')
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

        self.current_view = Gtk.Box()

        self.main_box.append(self.current_view)

        self.win.present()

    def create_menu_buttons(self):
        self.stack.add_titled(Gtk.Label(), "albums_view", "albums_view")
        self.stack.add_titled(Gtk.Label(), "media_view", "media_view")
        self.stack.add_titled(Gtk.Label(), "media_grid_view", "grid_view")

        self.stack.set_visible_child_name("media_view")

        self.stack.connect("notify::visible-child", self.switch_view)

    def switch_view(self, stack, param):
        for child in list(self.current_view):
            self.current_view.remove(child)

        visible_child_name = self.stack.get_visible_child_name()
        if visible_child_name == "albums_view":
            print("here goes albums")
        elif visible_child_name == "media_view":
            print("here goes media view")
        elif visible_child_name == "media_grid_view":
            print("here goes gridView")
        else:
            print("Not a possible state")