# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import gi, os
gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")

from .crop_overlay import CropOverlay
from .image_viewer_widget import ImageViewerWidget
from gi.repository import Adw, Gtk, Gdk, GdkPixbuf, Graphene
from .ui import (create_edit_view_main_box, create_edit_view_overlay)

class EditView(Adw.NavigationPage):
    def __init__(self, app, media_path: str):
        super().__init__(title="Edit")
        self.app = app
        self.media_path = media_path
        self.texture: Gdk.Texture | None = None
        self.picture: Gtk.ScrolledWindow | None = None
        self.crop_overlay = None
        self.setup_content()

    def setup_content(self):
        self.main_box = create_edit_view_main_box()
        self.overlay = create_edit_view_overlay()

        viewer = self.setup_picture_to_edit(self.media_path)

        # self.image_overlay.set_child(viewer)
        self.main_box.append(viewer)

        # bottom tools bar on OUTER overlay (so it stays visible)
        self.setup_editing_tools_bar()

        # Set the image viewer as the child of the main box.
        self.overlay.set_child(self.main_box)

        # Set Content for Navigation Page.
        self.set_child(self.overlay)

        # Disable gesture navigation
        self.set_can_pop(False)

    def setup_picture_to_edit(self, media_path: str | None) -> Gtk.Widget:
        if not media_path or not os.path.exists(media_path):
            empty = Gtk.Label(label="No media found.")
            empty.set_hexpand(True)
            empty.set_vexpand(True)
            empty.set_halign(Gtk.Align.CENTER)
            empty.set_valign(Gtk.Align.CENTER)
            return empty

        try:
            self.texture = Gdk.Texture.new_from_filename(media_path)
        except GLib.Error:
            error = Gtk.Label(label="Failed to load image.")
            error.set_hexpand(True)
            error.set_vexpand(True)
            error.set_halign(Gtk.Align.CENTER)
            error.set_valign(Gtk.Align.CENTER)
            return error

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.set_halign(Gtk.Align.FILL)
        scrolled.set_valign(Gtk.Align.FILL)

        zoomable_image = ImageViewerWidget(media_path, self.app, scrolled)
        zoomable_image.set_hexpand(True)
        zoomable_image.set_vexpand(True)
        zoomable_image.set_halign(Gtk.Align.CENTER)
        zoomable_image.set_valign(Gtk.Align.CENTER)

        scrolled.set_child(zoomable_image)
        zoomable_image.init_gestures()

        self.picture = scrolled

        return scrolled

    def setup_picture_to_edit(self, media_path: str | None) -> Gtk.Widget:
        if not media_path or not os.path.exists(media_path):
            empty = Gtk.Label(label="No media found.")
            empty.set_hexpand(True)
            empty.set_vexpand(True)
            empty.set_halign(Gtk.Align.CENTER)
            empty.set_valign(Gtk.Align.CENTER)
            return empty

        try:
            self.texture = Gdk.Texture.new_from_filename(media_path)
        except GLib.Error:
            error = Gtk.Label(label="Failed to load image.")
            error.set_hexpand(True)
            error.set_vexpand(True)
            error.set_halign(Gtk.Align.CENTER)
            error.set_valign(Gtk.Align.CENTER)
            return error

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.set_halign(Gtk.Align.FILL)
        scrolled.set_valign(Gtk.Align.FILL)

        zoomable_image = ImageViewerWidget(media_path, self.app, scrolled)
        zoomable_image.set_hexpand(True)
        zoomable_image.set_vexpand(True)
        zoomable_image.set_halign(Gtk.Align.CENTER)
        zoomable_image.set_valign(Gtk.Align.CENTER)

        scrolled.set_child(zoomable_image)
        zoomable_image.init_gestures()

        self.picture = scrolled

        return scrolled
    
    def setup_editing_tools_bar(self):
        def on_crop_clicked(_btn):
            if not self.texture or not self.picture:
                return

            if self.crop_overlay is None:
                self.crop_overlay = CropOverlay(self.picture, self.texture)

                self.image_overlay.add_overlay(self.crop_overlay)
                self.crop_overlay.queue_draw()
            else:
                self.image_overlay.remove_overlay(self.crop_overlay)
                self.crop_overlay = None

        def on_filters_clicked(_btn):
            return

        def on_fine_tunes_clicked(_btn):
            return

        def on_drawing_clicked(_btn):
            return

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bar.set_hexpand(True)
        bar.set_halign(Gtk.Align.FILL)
        bar.set_valign(Gtk.Align.END)
        bar.set_margin_start(12)
        bar.set_margin_end(12)
        bar.set_margin_bottom(12)
        bar.set_margin_top(6)

        bar.add_css_class("toolbar")
        bar.add_css_class("osd")

        def _icon_button(icon_name: str, tooltip: str, handler):
            btn = Gtk.Button()
            btn.set_has_frame(False)
            btn.set_tooltip_text(tooltip)

            img = Gtk.Image.new_from_icon_name(icon_name)
            img.set_pixel_size(22)
            btn.set_child(img)

            btn.connect("clicked", handler)
            return btn

        crop_btn = _icon_button("zoom-fit-best", "Crop", on_crop_clicked)
        filters_btn = _icon_button("color-select", "Filters", on_filters_clicked)
        fine_tunes_btn = _icon_button("preferences-system", "Fine tunes", on_fine_tunes_clicked)
        drawing_btn = _icon_button("document-edit", "Drawing", on_drawing_clicked)

        for b in (crop_btn, filters_btn, fine_tunes_btn, drawing_btn):
            b.set_hexpand(True)
            b.set_halign(Gtk.Align.CENTER)
            bar.append(b)

        self.overlay.add_overlay(bar)
        bar.set_can_target(True)
