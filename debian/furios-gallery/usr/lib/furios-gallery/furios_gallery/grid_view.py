import asyncio
from gi.repository import Gtk, GLib

class GridView(Gtk.Box):
    def __init__(self, app, thumbnails, items_per_load=200):
        super().__init__()
        self.app = app
        self.thumbnails = thumbnails
        self.items_per_load = items_per_load
        self.flowbox = None

        self.placeholder = Gtk.Label(label="Loading...")
        self.append(self.placeholder)

        asyncio.create_task(self.setup_widget())

    async def setup_widget(self):
        self.widget = await self.create_widget()
        GLib.idle_add(self._replace_placeholder_with_widget)

    def _replace_placeholder_with_widget(self):
        self.remove(self.placeholder)
        self.append(self.widget)

    async def create_widget(self):
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_column_spacing(0)
        self.flowbox.set_row_spacing(0)
        self.flowbox.set_max_children_per_line(6)
        self.flowbox.set_min_children_per_line(6)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flowbox.set_homogeneous(True)

        scrolled_window.set_child(self.flowbox)

        asyncio.create_task(self.load_more_items())

        self.flowbox.connect("selected-children-changed", self.on_child_selected)

        adjustment = scrolled_window.get_vadjustment()
        adjustment.connect("value-changed", self.on_scroll)

        return scrolled_window

    def on_scroll(self, adjustment):
        if adjustment.get_value() + adjustment.get_page_size() >= adjustment.get_upper() - 50:
            if self.app.current_index < len(self.app.media_paths):
                asyncio.create_task(self.load_more_items())

    async def load_more_items(self):
        batch_size = 20

        start_index = self.app.current_index
        end_index = max(self.app.current_index - self.items_per_load, -1)

        for i in range(start_index, end_index, -1):
            if i < 0 or i >= len(self.app.media_paths):
                print(f"Skipped invalid index: {i}")
                continue

            media_path = self.app.media_paths[i]
            await asyncio.to_thread(self.add_media_to_flowbox, media_path, i)

        self.app.current_index = end_index

    def add_media_to_flowbox(self, media_path, media_index):
        flowbox_child = Gtk.FlowBoxChild()
        flowbox_child.media_index = media_index

        flowbox_child.set_size_request(50, 70)

        thumbnail_path = self.thumbnails.generate_thumbnail(media_path)
        if thumbnail_path:
            GLib.idle_add(
                self.thumbnails.update_ui_with_thumbnail,
                flowbox_child,
                thumbnail_path
            )

        GLib.idle_add(self.flowbox.append, flowbox_child)

    def on_child_selected(self, flowbox):
        item = flowbox.get_selected_children()[0]
        self.app.current_index = item.media_index
        self.app.open_media_at_index(item.media_index)
