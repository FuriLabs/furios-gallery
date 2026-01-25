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

from gi.repository import Adw, Gtk, Gdk, GdkPixbuf, Graphene
from .ui import (create_edit_view_main_box, create_edit_view_overlay)

class EditView(Adw.NavigationPage):
    def __init__(self, app, media_path: str):
        super().__init__(title="Edit")
        self.app = app
        self.media_path = media_path

        self.setup_content()

    def setup_content(self):
        self.main_box = create_edit_view_main_box()

        self.overlay = create_edit_view_overlay()

        viewer = self.setup_picture_to_edit(self.media_path)
        viewer.set_hexpand(True)
        viewer.set_vexpand(True)

        self.main_box.append(viewer)

        self.setup_editing_tools_bar()

        self.overlay.set_child(self.main_box)
        self.set_child(self.overlay)
        self.set_can_pop(False)

    def build_media_widget(self, media_path: str) -> Gtk.Widget:
        # Only images for now
        if not media_path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            # Returning a placeholder label (or raise) for now
            label = Gtk.Label(label="Unsupported media type (images only for now).")
            label.set_halign(Gtk.Align.CENTER)
            label.set_valign(Gtk.Align.CENTER)
            label.set_hexpand(True)
            label.set_vexpand(True)
            return label

        scrolled_win = Gtk.ScrolledWindow()
        scrolled_win.set_hexpand(True)
        scrolled_win.set_vexpand(True)
        scrolled_win.set_halign(Gtk.Align.FILL)
        scrolled_win.set_valign(Gtk.Align.FILL)

        zoomable_image = ImageViewerWidget(media_path, self.app, scrolled_win)
        zoomable_image.set_hexpand(True)
        zoomable_image.set_vexpand(True)
        zoomable_image.set_halign(Gtk.Align.CENTER)
        zoomable_image.set_valign(Gtk.Align.CENTER)

        scrolled_win.set_child(zoomable_image)
        zoomable_image.init_gestures()

        return scrolled_win

    def setup_picture_to_edit(self, media_path: str | None) -> Gtk.Widget:
        if not media_path or not os.path.exists(media_path):
            empty = Gtk.Label(label="No media found.")
            empty.set_hexpand(True)
            empty.set_vexpand(True)
            empty.set_halign(Gtk.Align.CENTER)
            empty.set_valign(Gtk.Align.CENTER)
            return empty

        try:
            texture = Gdk.Texture.new_from_filename(media_path)
        except GLib.Error:
            error = Gtk.Label(label="Failed to load image.")
            error.set_hexpand(True)
            error.set_vexpand(True)
            error.set_halign(Gtk.Align.CENTER)
            error.set_valign(Gtk.Align.CENTER)
            return error

        pic = Gtk.Picture.new_for_paintable(texture)
        pic.set_content_fit(Gtk.ContentFit.CONTAIN)
        pic.set_hexpand(True)
        pic.set_vexpand(True)
        pic.set_halign(Gtk.Align.CENTER)
        pic.set_valign(Gtk.Align.CENTER)

        return pic
    
    def setup_editing_tools_bar(self):
        def on_crop_clicked(_btn):
            return

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



