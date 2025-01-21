# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GdkPixbuf

class ImageViewerWidget(Gtk.Widget):
    def __init__(self, path, win, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, win.get_width(), win.get_height(), True)
        self.texture = Gdk.Texture.new_for_pixbuf(self.pixbuf)
        self.scale = 1.0

        self.translate_x = 0
        self.translate_y = 0

        win_width, win_height = win.get_default_size()
        img_width = self.texture.get_intrinsic_width()
        img_height = self.texture.get_intrinsic_height()

        scale_width = win_width / img_width
        scale_height = win_height / img_height
        self.scale = min(scale_width, scale_height)

    def do_snapshot(self, snapshot):
        width = self.texture.get_intrinsic_width() * self.scale
        height = self.texture.get_intrinsic_height() * self.scale
        self.texture.snapshot(snapshot, width, height)

    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.CONSTANT_SIZE

    def do_measure(self, orientation, for_size):
        if orientation == Gtk.Orientation.HORIZONTAL:
            width = self.texture.get_intrinsic_width() * self.scale
            return (width, width, -1, -1)
        else:
            height = self.texture.get_intrinsic_height() * self.scale
            return (height, height, -1, -1)

    def init_gestures(self):
        self.zoom_gesture = Gtk.GestureZoom.new()
        self.zoom_gesture.connect("scale-changed", self.on_zoom)
        self.add_controller(self.zoom_gesture)

        self.drag_gesture = Gtk.GestureDrag.new()
        self.drag_gesture.connect("drag-begin", self.on_drag_begin)
        self.drag_gesture.connect("drag-update", self.on_drag_update)
        self.add_controller(self.drag_gesture)

    def on_zoom(self, gesture, scale_delta):
        zoom_factor = 1.005 if scale_delta > 1 else 0.99
        self.queue_resize()

        new_scale = self.scale * zoom_factor

        if  new_scale >= 0.18 and new_scale <= 0.7:
            self.scale = new_scale
            self.queue_resize()

    def on_drag_begin(self, gesture, start_x, start_y):
        self.drag_start_x = start_x
        self.drag_start_y = start_y

    def on_drag_update(self, gesture, offset_x, offset_y):
        self.translate_x += offset_x
        self.translate_y += offset_y
