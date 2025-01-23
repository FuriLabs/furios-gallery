# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import asyncio, gi, os
from gi.repository import Gtk, GLib, Adw, Gdk

class GridView(Adw.NavigationPage):
    def __init__(self, app, thumbnails, album_name="Media", items_per_load=200):
        super().__init__(title=album_name)

        self.app = app
        self.thumbnails = thumbnails
        self.items_per_load = items_per_load

        # Main box to hold the grid view
        self.main_grid_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_grid_box.set_hexpand(True)
        self.main_grid_box.set_vexpand(True)
        self.main_grid_box.set_halign(Gtk.Align.FILL)
        self.main_grid_box.set_valign(Gtk.Align.FILL)

        # Placeholder while loading
        self.placeholder = Gtk.Label(label="Loading...")
        self.main_grid_box.append(self.placeholder)

        # Set the main grid box as the child of the NavigationPage
        self.set_child(self.main_grid_box)

        # Setup CSS
        self.setup_css()

        # Flowbox will be None initially
        self.flowbox = None

        # Async setup of widget
        asyncio.create_task(self.setup_widget())

    def setup_css(self):
        css_provider = Gtk.CssProvider()

        css_provider.load_from_data(b"""
        .delete-btn {
            padding: 5px;
        }
        """
        )

        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    async def setup_widget(self):
        await self.create_widget()
        GLib.idle_add(self._replace_placeholder_with_widget)

    def _replace_placeholder_with_widget(self):
        self.main_grid_box.remove(self.placeholder)

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

        # Load initial items
        asyncio.create_task(self.load_more_items())

        # Connect signals
        self.flowbox.connect("selected-children-changed", self.on_child_selected)
        self.flowbox.connect("selected-children-changed", self.update_selected_count)

        # Connect scroll event
        adjustment = scrolled_window.get_vadjustment()
        adjustment.connect("value-changed", self.on_scroll)

        self.main_grid_box.append(scrolled_window)

    def update_selected_count(self, flowbox):
        if hasattr(self.app, 'selected_files_label') and self.flowbox.get_selection_mode() == Gtk.SelectionMode.MULTIPLE:
            self.app.selected_files_label.set_text(f"Selected Files: {len(self.flowbox.get_selected_children())}")

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
            selected = flowbox.get_selected_children()
            if selected:  # Check if there are selected items
                item = selected[0]
                self.app.current_index = item.media_index
                self.app.open_media_at_index(item.media_index)
            self.flowbox.unselect_all()
