# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gtk, Gdk, GLib
from .ui import (create_main_bar_body, create_cancel_btn, create_apply_btn)

FILTERS = [
    ("Original", "filter-original"),
    ("B&W", "filter-bw"),
    ("Vivid", "filter-vivid"),
    ("Invert", "filter-invert"),
    ("Soft", "filter-soft"),
]

ALL_FILTER_CLASSES = tuple(css for _label, css in FILTERS)

CSS = b"""
    .filter-thumb picture {
      border-radius: 3px;
      box-shadow: 0 5px 18px rgba(0,0,0,0.25);
    }
    .filter-original { filter: none; }
    .filter-bw { filter: grayscale(1); }
    .filter-vivid { filter: saturate(1.7) contrast(1.15); }
    .filter-invert { filter: invert(1); }
    .filter-soft { filter: blur(0.7px) brightness(1.02); }
    """

class FiltersOverlay(Gtk.Widget):
    def __init__( self, picture_widget: Gtk.Widget, media_path: str, thumbnails):
        super().__init__()
        self.picture_widget = picture_widget
        self.media_path = media_path
        self.thumbnails = thumbnails

        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_halign(Gtk.Align.FILL)
        self.set_valign(Gtk.Align.FILL)

        self.ensure_css_loaded()

        self.bar = self.build_bar()

    def ensure_css_loaded(self):
        display = self.get_display()
        if getattr(display, "_filters_css_loaded", False):
            return
        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            display, prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        display._filters_css_loaded = True

    def set_picture_from_file(self, picture: Gtk.Picture, path: str):
        try:
            tex = Gdk.Texture.new_from_filename(path)
            picture.set_paintable(tex)
        except Exception as e:
            print("Failed to load filter thumbnail:", e)
        return False

    def make_filter_button(self, label: str, css_class: str, thumb_path: str) -> Gtk.Button:
        btn = Gtk.Button()
        btn.add_css_class("flat")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        vbox.add_css_class("filter-thumb")

        thumb = Gtk.Picture()
        thumb.set_content_fit(Gtk.ContentFit.COVER)
        thumb.set_size_request(56, 74)
        thumb.add_css_class(css_class)
        GLib.idle_add(self.set_picture_from_file, thumb, thumb_path)

        lab = Gtk.Label(label=label)
        lab.set_halign(Gtk.Align.CENTER)

        vbox.append(thumb)
        vbox.append(lab)
        btn.set_child(vbox)

        btn.connect("clicked", self.on_filter_clicked, css_class)
        return btn

    def build_bar(self) -> Gtk.Widget:
        filters_bar = create_main_bar_body(8, 6, 6, 12, 6, "vertical")

        outer = Gtk.ScrolledWindow()
        outer.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        outer.set_overlay_scrolling(True)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        row.set_margin_top(1)
        row.set_margin_bottom(1)
        outer.set_child(row)

        thumb_path = self.thumbnails.generate_thumbnail(self.media_path)
        if thumb_path:
            for label, css_class in FILTERS:
                row.append(self.make_filter_button(label, css_class, thumb_path))

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_hexpand(True)

        cancel = create_cancel_btn(self.on_cancel_clicked)

        apply = create_apply_btn(self.on_apply_clicked)

        actions.append(cancel)
        actions.append(apply)

        filters_bar.append(outer)
        filters_bar.append(actions)
        return filters_bar

    def on_cancel_clicked(self, _btn):
        if callable(getattr(self, "on_cancel", None)):
            self.on_cancel()

    def on_apply_clicked(self, _btn):
        if callable(getattr(self, "on_apply", None)):
            self.on_apply(getattr(self, "selected_filter", "filter-original"))

    def get_bar_widget(self) -> Gtk.Widget:
        return self.bar

    def on_filter_clicked(self, button: Gtk.Button, css_class: str):
        self.selected_filter = css_class
        for c in ALL_FILTER_CLASSES:
            self.picture_widget.remove_css_class(c)
        self.picture_widget.add_css_class(css_class)
