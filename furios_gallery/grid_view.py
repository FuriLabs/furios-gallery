import asyncio, gi, os
from gi.repository import Gtk, GLib, Adw, Gdk

class GridView(Gtk.Box):
    def __init__(self, app, thumbnails, items_per_load=200):
        super().__init__()
        self.app = app
        self.thumbnails = thumbnails
        self.items_per_load = items_per_load
        self.setup_css()
        self.flowbox = None

        self.placeholder = Gtk.Label(label="Loading...")
        self.append(self.placeholder)

        asyncio.create_task(self.setup_widget())

    def setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
        .grid-menu-box {
            background-color: #333;
            padding: 15px;
        }
        .delete-btn {
            padding: 5px;
        }
        """)
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    async def setup_widget(self):
        self.widget = await self.create_widget()
        GLib.idle_add(self._replace_placeholder_with_widget)

    def _replace_placeholder_with_widget(self):
        self.remove(self.placeholder)
        self.append(self.widget)

    async def create_widget(self):
        self.main_grid_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_grid_box.set_hexpand(True)
        self.main_grid_box.set_vexpand(True)
        self.main_grid_box.set_halign(Gtk.Align.FILL)
        self.main_grid_box.set_valign(Gtk.Align.FILL)

        self.grid_view_menu = self.create_grid_view_menu()
        self.grid_view_menu.set_valign(Gtk.Align.START)
        self.main_grid_box.append(self.grid_view_menu)

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

        self.main_grid_box.append(scrolled_window)

        return self.main_grid_box

    def create_grid_view_menu(self):
        grid_menu_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        grid_menu_box.set_hexpand(True)
        grid_menu_box.set_halign(Gtk.Align.FILL)
        grid_menu_box.set_valign(Gtk.Align.START)
        grid_menu_box.set_css_classes(["grid-menu-box"])

        return_to_albums_btn = Gtk.Button(icon_name="application-exit-rtl-symbolic")
        # return_to_albums_btn.set_size_request(50,40)
        return_to_albums_btn.set_halign(Gtk.Align.START)
        return_to_albums_btn.connect("clicked", self.on_return_to_albums_view)
        grid_menu_box.append(return_to_albums_btn)

        delete_media_btn = Gtk.Button(icon_name="user-trash-symbolic")
        # delete_media_btn.set_size_request(50,40)
        delete_media_btn.set_halign(Gtk.Align.END)
        delete_media_btn.connect("clicked", self.open_delete_popup)
        delete_media_btn.set_css_classes(["delete-btn"])
        delete_media_btn.set_margin_start(5)
        grid_menu_box.append(delete_media_btn)

        return grid_menu_box

    def on_return_to_albums_view(self, btn):
        self.app.switch_to_view(self.app.create_albums_box)

    def open_delete_popup(self, btn):
        self.flowbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)

        self.selected_files_label = Gtk.Label(label=f"Selected Files: {len(self.flowbox.get_selected_children())}")
        self.selected_files_label.set_hexpand(True)
        self.selected_files_label.set_halign(Gtk.Align.FILL)
        self.grid_view_menu.append(self.selected_files_label)

        self.cancel_btn = Gtk.Button(label="Cancel")
        self.cancel_btn.set_margin_end(15)
        self.cancel_btn.connect("clicked", self.on_cancel_btn)
        self.grid_view_menu.append(self.cancel_btn)

        self.delete_confirm_btn = Gtk.Button(label="Delete")
        self.delete_confirm_btn.connect("clicked", self.on_delete_confirmation)
        self.grid_view_menu.append(self.delete_confirm_btn)

    def on_cancel_btn(self, btn):
        self.flowbox.unselect_all()
        self.grid_view_menu.remove(self.selected_files_label)
        self.grid_view_menu.remove(self.cancel_btn)
        self.grid_view_menu.remove(self.delete_confirm_btn)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)

    def on_delete_confirmation(self, btn):
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Delete Files?",
            body=f"This will permanently delete the {len(self.flowbox.get_selected_children())} selected files from your system"
        )

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        dialog.connect("response", lambda dialog, response: self.on_delete_media(dialog, response))

        dialog.present()

    def on_delete_media(self, dialog, response):
        if response == "delete":
            selected_children = self.flowbox.get_selected_children()
            for child in selected_children:
                media_index = child.media_index
                media_path = self.app.media_paths[media_index]

                try:
                    if os.path.exists(media_path):
                        os.remove(media_path)
                        print(f"File deleted: {media_path}")
                    else:
                        print(f"File not found: {media_path}")
                except Exception as e:
                    print(f"Error deleting file: {e}")

                self.flowbox.remove(child)
        else:
            self.flowbox.unselect_all()
            self.grid_view_menu.remove(self.selected_files_label)
            self.grid_view_menu.remove(self.cancel_btn)
            self.grid_view_menu.remove(self.delete_confirm_btn)
            self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)

        dialog.destroy()

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
        if self.flowbox.get_selection_mode() == Gtk.SelectionMode.SINGLE:
            item = flowbox.get_selected_children()[0]
            self.app.current_index = item.media_index
            self.app.open_media_at_index(item.media_index)
        else:
            self.selected_files_label.set_text(f"Selected Files: {len(self.flowbox.get_selected_children())}")
