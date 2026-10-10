# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>
# Bardia Moshiri <bardia@furilabs.com>
# Jesús Higueras <jesus@furilabs.com>
# Luis Garcia <git@luigi311.com>

import gi
import weakref

from .preview_loader import get_preview_loader

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, Graphene, GLib

class ImageViewerWidget(Gtk.Widget):
    def __init__(self, path, win, scrolled_win, *args,
                 max_dimension=None, async_loading=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.pixbuf = None
        self.texture = None
        self.min_scale = 0
        self.scale = 1.0
        self.scale_at_start = 1.0
        self.zoom_enabled = True
        self.scrolled_win = scrolled_win
        self.win = win
        self.zoom_gesture = None
        self._zoom_handler_ids = []
        self._released = False
        self._preview_path = None

        if async_loading:
            viewer_ref = weakref.ref(self)

            def ready(decoded):
                viewer = viewer_ref()
                if viewer is not None and not viewer._released:
                    viewer.set_preview(*decoded)
                return GLib.SOURCE_REMOVE

            self._preview_path = path
            self._preview_size = max_dimension or 1600
            get_preview_loader().request(path, self._preview_size, ready, priority=0)
        else:
            self.set_pixbuf(self.load_pixbuf(path, max_dimension))

    def load_pixbuf(self, path, max_dimension):
        if max_dimension is None:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
        else:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                path, max_dimension, max_dimension, True
            )
        return GdkPixbuf.Pixbuf.apply_embedded_orientation(pixbuf)

    def prioritize(self):
        if not self._released and self.texture is None and self._preview_path is not None:
            get_preview_loader().request(self._preview_path, self._preview_size, priority=0)

    def set_preview(self, width, height, pixels):
        if self._released:
            return
        data = GLib.Bytes.new(pixels)
        self.texture = Gdk.MemoryTexture.new(
            width, height, Gdk.MemoryFormat.R8G8B8A8, data, width * 4
        )
        self.calculate_initial_scale()
        self.scale_at_start = self.scale
        self.queue_resize()
        self.queue_draw()

    def set_pixbuf(self, pixbuf):
        if self._released:
            return
        self.pixbuf = pixbuf
        self.texture = Gdk.Texture.new_for_pixbuf(pixbuf)
        self.calculate_initial_scale()
        self.scale_at_start = self.scale
        self.queue_resize()
        self.queue_draw()

    def reset_view_fit(self, center=True):
        if self._released or self.texture is None or self.scrolled_win is None:
            return
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
        if not enabled and self.zoom_gesture:
            # drop any in-progress gesture cleanly
            self.zoom_gesture.reset()

    def calculate_initial_scale(self):
        if self.texture is None or self.win is None:
            return
        win_width = max(1, self.win.get_width())
        win_height = max(1, self.win.get_height())
        img_width = self.texture.get_width()
        img_height = self.texture.get_height()

        # Calculate the scale to fit the image within the window
        scale_width = win_width / img_width
        scale_height = win_height / img_height
        self.min_scale = self.scale = min(scale_width, scale_height)

    def do_snapshot(self, snapshot):
        if self.texture is None:
            return
        width = self.texture.get_intrinsic_width() * self.scale
        height = self.texture.get_intrinsic_height() * self.scale
        self.texture.snapshot(snapshot, width, height)

    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.CONSTANT_SIZE

    def do_measure(self, orientation, for_size):
        if self.texture is None:
            return (0, 0, -1, -1)
        if orientation == Gtk.Orientation.HORIZONTAL:
            width = self.texture.get_intrinsic_width() * self.scale
            return (width, width, -1, -1)
        else:
            height = self.texture.get_intrinsic_height() * self.scale
            return (height, height, -1, -1)

    def init_gestures(self):
        self.zoom_gesture = Gtk.GestureZoom.new()
        self._zoom_handler_ids = [
            self.zoom_gesture.connect("begin", self.on_zoom_begin),
            self.zoom_gesture.connect("scale-changed", self.on_zoom),
        ]
        self.scrolled_win.add_controller(self.zoom_gesture)

    def release(self):
        if self.zoom_gesture is not None:
            for handler_id in self._zoom_handler_ids:
                self.zoom_gesture.disconnect(handler_id)
            self._zoom_handler_ids.clear()
            self.zoom_gesture.reset()
            if self.scrolled_win is not None:
                self.scrolled_win.remove_controller(self.zoom_gesture)
            self.zoom_gesture = None

        self._released = True
        self.texture = None
        self.pixbuf = None
        self.scrolled_win = None
        self.win = None

    def on_zoom_begin(self, gesture, sequence):
        if not self.zoom_enabled or self.texture is None or self.scrolled_win is None:
            return
        self.scale_at_start = self.scale

    def on_zoom(self, gesture, scale_delta):
        if not self.zoom_enabled or self.texture is None or self.scrolled_win is None:
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
