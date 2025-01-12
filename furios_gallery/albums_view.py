import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, Gdk, GLib, GdkPixbuf
from .media_manager import list_albums

class Albums(Gtk.Box):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.widget = self.create_widget()
        self.append(self.widget)

    def create_widget(self):
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.set_halign(Gtk.Align.FILL)
        scrolled_window.set_valign(Gtk.Align.FILL)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_column_spacing(0)
        self.flowbox.set_row_spacing(0)
        self.flowbox.set_max_children_per_line(3)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flowbox.set_hexpand(False)
        self.flowbox.set_vexpand(True)

        scrolled_window.set_child(self.flowbox)

        self.load_albums()

        self.flowbox.connect("selected-children-changed", self.on_child_selected)

        return scrolled_window

    def load_albums(self):
        albums = list_albums()

        for index, album in enumerate(albums):
            flowbox_child = Gtk.FlowBoxChild()

            flowbox_child.album_name = album

            album_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            album_box.set_spacing(8)
            album_box.set_halign(Gtk.Align.CENTER)
            album_box.set_valign(Gtk.Align.CENTER)

            icon = Gtk.Image.new_from_icon_name("folder-symbolic")
            icon.set_property("icon-size", Gtk.IconSize.LARGE)

            label = Gtk.Label(label=album)
            label.set_max_width_chars(20)
            label.set_halign(Gtk.Align.CENTER)

            album_box.append(icon)
            album_box.append(label)

            flowbox_child.set_child(album_box)

            self.flowbox.append(flowbox_child)

    def on_child_selected(self, flowbox):
        selected_children = flowbox.get_selected_children()
        if selected_children:
            selected_child = selected_children[0]
            album_name = selected_child.album_name
            print(f"Selected album: {album_name}")

            if album_name == "Videos":
                self.app.open_videos_album()
            elif album_name == "Pictures":
                self.app.open_pictures_album()
            else:
                self.app.open_album(album_name)