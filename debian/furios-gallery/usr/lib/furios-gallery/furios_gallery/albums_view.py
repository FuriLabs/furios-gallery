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

        albums_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        albums_box.set_hexpand(True)
        albums_box.set_vexpand(True)
        albums_box.set_halign(Gtk.Align.FILL)
        albums_box.set_valign(Gtk.Align.FILL)

        albums_action = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        albums_action.set_halign(Gtk.Align.FILL)
        albums_action.set_halign(Gtk.Align.END)
        albums_action.set_hexpand(True)
        albums_action.set_margin_start(10)
        albums_action.set_margin_end(10)
        albums_action.set_margin_bottom(10)

        create_album_button = Gtk.Button()
        create_album_button_icon = Gtk.Image.new_from_icon_name("folder-new-symbolic")
        create_album_button_icon.set_pixel_size(25)
        create_album_button.set_child(create_album_button_icon)
        create_album_button.connect("clicked", self.create_album)

        albums_action.append(create_album_button)

        albums_box.append(albums_action)

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

        albums_box.append(scrolled_window)

        self.load_albums()

        self.flowbox.connect("selected-children-changed", self.on_child_selected)

        return albums_box

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

    def create_album(self, button):
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
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
                print(f"Album created: {album_name}")
                #TBD: Make the SQL database
            else:
                print("Album name cannot be empty")
        dialog.destroy()