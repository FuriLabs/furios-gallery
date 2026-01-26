# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>
# Bardia Moshiri <bardia@furilabs.com>
# Jesús Higueras <jesus@furilabs.com>
# Luis Garcia <git@luigi311.com>

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, Graphene

class ImageViewerWidget(Gtk.Widget):
    def __init__(self, path, win, scrolled_win, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
        self.texture = Gdk.Texture.new_for_pixbuf(self.pixbuf)
        self.min_scale = 0
        self.scale = 1.0
        self.scale_at_start = 1.0
        self.zoom_enabled = True
        self.scrolled_win = scrolled_win
        self.win = win

        # Calculate the initial scale to fit the image within the window
        self.calculate_initial_scale()

    def reset_view_fit(self, center=True):
        self.calculate_initial_scale()
        self.scale_at_start = self.scale

        hadj = self.scrolled_win.get_hadjustment()
        vadj = self.scrolled_win.get_vadjustment()
        if not hadj or not vadj:
            return

        if not center:
            hadj.set_value(0.0)
            vadj.set_value(0.0)
            return

        hx = max(0.0, (hadj.get_upper() - hadj.get_page_size()) / 2.0)
        vy = max(0.0, (vadj.get_upper() - vadj.get_page_size()) / 2.0)
        hadj.set_value(hx)
        vadj.set_value(vy)

        self.queue_resize()
        self.queue_draw()

    def set_zoom_enabled(self, enabled: bool):
        self.zoom_enabled = enabled
        if not enabled and getattr(self, "zoom_gesture", None):
            # drop any in-progress gesture cleanly
            self.zoom_gesture.reset()

    def calculate_initial_scale(self):
        win_width = self.win.get_width()
        win_height = self.win.get_height()
        img_width = self.pixbuf.get_width()
        img_height = self.pixbuf.get_height()

        # Calculate the scale to fit the image within the window
        scale_width = win_width / img_width
        scale_height = win_height / img_height
        self.min_scale = self.scale = min(scale_width, scale_height)

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
        self.zoom_gesture.connect("begin", self.on_zoom_begin)
        self.zoom_gesture.connect("scale-changed", self.on_zoom)
        self.scrolled_win.add_controller(self.zoom_gesture)

    def on_zoom_begin(self, gesture, sequence):
        if not self.zoom_enabled:
            return
        self.scale_at_start = self.scale

    def on_zoom(self, gesture, scale_delta):
        if not self.zoom_enabled:
            return
        zoom_factor = (scale_delta * self.scale_at_start) / self.scale
        self.queue_resize()

        new_scale = self.scale * zoom_factor

        # Clamp to full screen
        if new_scale < self.min_scale:
            new_scale = self.min_scale

        # In order to zoom in/out at the gesture's center, we need to figure out
        # the new adjustment values that will keep the gesture's center at the same
        # position on the screen after the zoom. Since the gesture's position is
        # relative to our scrollable, we need to convert it to the native window
        # coordinates first.

        _, x, y = gesture.get_bounding_box_center()

        h_adjust = self.scrolled_win.get_hadjustment()
        v_adjust = self.scrolled_win.get_vadjustment()

        origin = Graphene.Point(0, 0)
        _, our_origin_on_screen = self.scrolled_win.compute_point(self.get_native(), origin)

        x = x + our_origin_on_screen.x
        y = y + our_origin_on_screen.y

        new_h_value = h_adjust.get_value() * zoom_factor + x * (zoom_factor - 1)
        new_v_value = v_adjust.get_value() * zoom_factor + y * (zoom_factor - 1)

        h_adjust.set_value(new_h_value)
        v_adjust.set_value(new_v_value)

        # Update scale which triggers resize
        self.scale = new_scale
        self.queue_draw()
