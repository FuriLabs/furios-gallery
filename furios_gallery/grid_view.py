# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>
# Bardia Moshiri <bardia@furilabs.com>
# Jesús Higueras <jesus@furilabs.com>
# Luis Garcia <git@luigi311.com>

import asyncio
from gi.repository import Gtk, GLib, Adw
from .ui import (
    create_grid_view_main_box, create_grid_view_placeholder, create_grid_view_scrolled_window,
    create_grid_view_flowbox, setup_grid_view_css
)

class GridView(Adw.NavigationPage):
    def __init__(self, app, thumbnails, album_name="Media", items_per_load=200):
        super().__init__(title=album_name)

        self.app = app
        self.thumbnails = thumbnails
        self.items_per_load = items_per_load

        # Main box to hold the grid view
        self.main_grid_box = create_grid_view_main_box()

        # Placeholder while loading
        self.placeholder = create_grid_view_placeholder()
        self.main_grid_box.append(self.placeholder)

        # Set the main grid box as the child of the NavigationPage
        self.set_child(self.main_grid_box)

        # Setup CSS
        setup_grid_view_css()

        # Flowbox will be None initially
        self.flowbox = None

        self._loading = False

        # Async setup of widget
        asyncio.create_task(self.setup_widget())

    async def setup_widget(self):
        await self.create_widget()
        GLib.idle_add(self._replace_placeholder_with_widget)

    def _replace_placeholder_with_widget(self):
        self.main_grid_box.remove(self.placeholder)

    async def create_widget(self):
        scrolled_window = create_grid_view_scrolled_window()

        self.flowbox = create_grid_view_flowbox(self.on_child_selected, self.update_selected_count)

        scrolled_window.set_child(self.flowbox)

        # Load initial items
        asyncio.create_task(self.load_more_items())

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
        # If we're already loading, do nothing.
        # Prevents repeated calls if the user keeps scrolling.
        if self._loading == True:
            return
        self._loading = True

        batch_size = 20

        start_index = self.app.current_index
        end_index = max(self.app.current_index - self.items_per_load, 0)
        # We go from start_index down to end_index, in steps of batch_size
        while start_index > end_index:
            chunk_end = max(start_index - batch_size, end_index)
            tasks = []

            # Collect tasks for this chunk
            for i in range(start_index, chunk_end -1, -1):

                media_path = self.app.media_paths[i]
                # Schedule the thumbnail work in a thread to avoid blocking the main loop
                tasks.append(asyncio.to_thread(self.add_media_to_flowbox, media_path, i))

            # Run all tasks in parallel
            await asyncio.gather(*tasks)

            # Update the start_index to move on to the next chunk
            start_index = chunk_end

        # We've now loaded up to end_index
        self.app.current_index = end_index
        self._loading = False

    def add_media_to_flowbox(self, media_path, media_index):
        thumbnail_path = self.thumbnails.generate_thumbnail(media_path)

        if thumbnail_path:
            flowbox_child = Gtk.FlowBoxChild()
            flowbox_child.media_index = media_index
            flowbox_child.set_size_request(50, 90)

            GLib.idle_add(
                self.thumbnails.update_ui_with_thumbnail,
                flowbox_child,
                thumbnail_path
            )

            GLib.idle_add(self.flowbox.append, flowbox_child)

    def delete_media_from_flowbox(self, media_index):
        child = self.flowbox.get_first_child()

        while child:
            if hasattr(child, "media_index") and child.media_index == media_index:
                self.flowbox.remove(child)
                break
            child = child.get_next_sibling()

    def on_child_selected(self, flowbox):
        if self.flowbox.get_selection_mode() == Gtk.SelectionMode.SINGLE:
            selected = flowbox.get_selected_children()
            if selected:  # Check if there are selected items
                item = selected[0]
                self.app.current_index = item.media_index
                self.app.open_media_at_index(item.media_index)
            self.flowbox.unselect_all()
