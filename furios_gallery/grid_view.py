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
        self._next_index = len(self.app.media_paths) - 1

        # Async setup of widget
        asyncio.create_task(self.setup_widget())

    async def setup_widget(self):
        await self.create_widget()
        GLib.idle_add(self._replace_placeholder_with_widget)

    def _replace_placeholder_with_widget(self):
        if self.placeholder.get_parent() is self.main_grid_box:
            self.main_grid_box.remove(self.placeholder)
        return False

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
        if self.app.selected_files_label is not None and self.flowbox.get_selection_mode() == Gtk.SelectionMode.MULTIPLE:
            self.app.selected_files_label.set_text(f"Selected Files: {len(self.flowbox.get_selected_children())}")

    def on_scroll(self, adjustment):
        if adjustment.get_value() + adjustment.get_page_size() >= adjustment.get_upper() - 50:
            if self._next_index >= 0:
                asyncio.create_task(self.load_more_items())

    async def load_more_items(self):
        # If we're already loading, do nothing.
        # Prevents repeated calls if the user keeps scrolling.
        if self._loading or self._next_index < 0:
            return
        self._loading = True

        try:
            batch_size = 20
            start_index = self._next_index
            end_index = max(start_index - self.items_per_load + 1, 0)

            # Load from newest to oldest without repeating chunk boundaries.
            chunk_start = start_index
            while chunk_start >= end_index:
                chunk_end = max(chunk_start - batch_size + 1, end_index)
                tasks = []

                for i in range(chunk_start, chunk_end - 1, -1):
                    media_path = self.app.media_paths[i]
                    tasks.append(asyncio.to_thread(self.generate_thumbnail_for_flowbox, media_path, i))

                await asyncio.gather(*tasks)
                chunk_start = chunk_end - 1

            self._next_index = end_index - 1
        finally:
            self._loading = False

    def generate_thumbnail_for_flowbox(self, media_path, media_index):
        thumbnail_path = self.thumbnails.generate_thumbnail(media_path)
        if thumbnail_path:
            GLib.idle_add(self.add_media_to_flowbox, media_path, media_index, thumbnail_path)

    def add_media_to_flowbox(self, media_path, media_index, thumbnail_path):
        if self.flowbox is None:
            return False

        flowbox_child = Gtk.FlowBoxChild()
        flowbox_child.media_path = media_path
        flowbox_child.media_index = media_index
        flowbox_child.set_size_request(50, 90)

        self.thumbnails.update_ui_with_thumbnail(flowbox_child, thumbnail_path)
        self.flowbox.append(flowbox_child)
        self.setup_single_child_click_handler(flowbox_child)
        return False

    def setup_single_child_click_handler(self, child):
        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", self.on_flowbox_child_clicked, child)
        child.add_controller(gesture)

    def delete_media_from_flowbox(self, media_path):
        child = self.flowbox.get_first_child()

        while child:
            if child.media_path == media_path:
                self.flowbox.remove(child)
                break
            child = child.get_next_sibling()

        self.refresh_media_indices()

    def refresh_media_indices(self):
        child = self.flowbox.get_first_child()

        while child:
            next_child = child.get_next_sibling()

            try:
                child.media_index = self.app.media_paths.index(child.media_path)
            except ValueError:
                self.flowbox.remove(child)

            child = next_child

        self.flowbox.invalidate_sort()

    def on_child_selected(self, flowbox):
        if self.flowbox.get_selection_mode() == Gtk.SelectionMode.MULTIPLE:
            # In multiple selection mode, just update the count
            return

        if self.flowbox.get_selection_mode() == Gtk.SelectionMode.SINGLE:
            selected = flowbox.get_selected_children()
            if selected:  # Check if there are selected items
                item = selected[0]
                try:
                    media_index = self.app.media_paths.index(item.media_path)
                except ValueError:
                    self.flowbox.remove(item)
                    self.flowbox.unselect_all()
                    return

                item.media_index = media_index
                self.app.current_index = media_index
                self.app.open_media_at_index(media_index)
            self.flowbox.unselect_all()

    def setup_flowbox_click_handlers(self):
        for child in self.flowbox:
            # Remove existing handlers to avoid duplicates
            gesture = Gtk.GestureClick.new()
            gesture.connect("pressed", self.on_flowbox_child_clicked, child)
            child.add_controller(gesture)

    def on_flowbox_child_clicked(self, gesture, n_press, x, y, child):
        if self.flowbox.get_selection_mode() == Gtk.SelectionMode.MULTIPLE:
            # Stop the gesture from propagating to prevent double-handling
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)

            if child.is_selected():
                self.flowbox.unselect_child(child)
            else:
                self.flowbox.select_child(child)
            return True
        return False
