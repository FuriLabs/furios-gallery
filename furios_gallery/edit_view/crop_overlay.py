# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, Graphene, Gsk

class CropOverlay(Gtk.Widget):
    HANDLE = 12
    HIT = 18
    MIN_SIZE = 32

    def __init__(self, picture_widget: Gtk.Widget, texture: Gdk.Texture):
        super().__init__()
        self.picture_widget = picture_widget
        self.texture = texture

        self.initial_h = self.texture.get_height()
        self.initial_w = self.texture.get_width()

        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_halign(Gtk.Align.FILL)
        self.set_valign(Gtk.Align.FILL)
        self.set_can_target(True)

        self.rect = [0.0, 0.0, 0.0, 0.0]

        self.mode = None
        self.drag_start = (0.0, 0.0)
        self.rect_start = None

        drag = Gtk.GestureDrag.new()
        drag.connect("drag-begin", self.on_drag_begin)
        drag.connect("drag-update", self.on_drag_update)
        drag.connect("drag-end", self.on_drag_end)
        self.add_controller(drag)

        self.bar = self.build_crop_bar()
        self.bar.set_can_target(True)

    def get_bar_widget(self) -> Gtk.Widget:
        return self.bar

    def build_crop_bar(self):
        if getattr(self, "crop_bar", None):
            return

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bar.set_halign(Gtk.Align.FILL)
        bar.set_valign(Gtk.Align.END)
        bar.set_hexpand(True)
        bar.set_margin_start(12)
        bar.set_margin_end(12)
        bar.set_margin_bottom(12)
        bar.set_margin_top(6)

        bar.add_css_class("osd")
        bar.add_css_class("toolbar")

        cancel = Gtk.Button(label="Cancel")
        cancel.set_hexpand(True)
        cancel.set_halign(Gtk.Align.FILL)
        cancel.connect("clicked", self.on_cancel_clicked)

        crop = Gtk.Button(label="Crop")
        crop.set_hexpand(True)
        crop.set_halign(Gtk.Align.FILL)
        crop.add_css_class("suggested-action")
        crop.connect("clicked", self.on_apply_clicked)

        bar.append(cancel)
        bar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        bar.append(crop)

        return bar

    def on_cancel_clicked(self, btn=None):
        if callable(getattr(self, "on_cancel", None)):
            self.on_cancel()

    def on_apply_clicked(self, btn=None):
        if callable(getattr(self, "on_apply", None)):
            self.on_apply(getattr(self, "selected_filter", "filter-original"))

    def image_rect_in_widget(self) -> tuple[float, float, float, float]:
        w = float(self.get_allocated_width())
        h = float(self.get_allocated_height())

        tw = float(self.texture.get_width())
        th = float(self.texture.get_height())

        if w <= 0 or h <= 0 or tw <= 0 or th <= 0:
            return (0.0, 0.0, w, h)

        scale = min(w / tw, h / th)
        iw = tw * scale
        ih = th * scale
        ix = (w - iw) * 0.5
        iy = (h - ih) * 0.5
        return (ix, iy, iw, ih)

    def clamp_rect_to_image(self, rect):
        ix, iy, iw, ih = self.image_rect_in_widget()
        x, y, w, h = rect

        w = max(w, self.MIN_SIZE)
        h = max(h, self.MIN_SIZE)

        w = min(w, iw)
        h = min(h, ih)

        x = max(ix, min(x, ix + iw - w))
        y = max(iy, min(y, iy + ih - h))

        return [x, y, w, h]

    def init_default_rect(self):
        ix, iy, iw, ih = self.image_rect_in_widget()
        w = iw * 0.6
        h = ih * 0.6
        x = ix + (iw - w) * 0.5
        y = iy + (ih - h) * 0.5
        self.rect = self.clamp_rect_to_image([x, y, w, h])
        self.queue_draw()

    def handle_points(self):
        x, y, w, h = self.rect
        return {
            "nw": (x, y),
            "ne": (x + w, y),
            "sw": (x, y + h),
            "se": (x + w, y + h),
        }

    def hit_test(self, px: float, py: float) -> str | None:
        for name, (hx, hy) in self.handle_points().items():
            if (px - hx) ** 2 + (py - hy) ** 2 <= (self.HIT ** 2):
                return name

        x, y, w, h = self.rect
        if x <= px <= x + w and y <= py <= y + h:
            return "move"
        return None

    def snapshot_circle(self, snapshot: Gtk.Snapshot, cx: float, cy: float, r: float, color: Gdk.RGBA):
        rect = Graphene.Rect().init(cx - r, cy - r, 2*r, 2*r)

        rr = Gsk.RoundedRect()
        rad = Graphene.Size()
        rad.init(r, r)

        rr.init(rect, rad, rad, rad, rad)

        snapshot.push_rounded_clip(rr)
        snapshot.append_color(color, rect)
        snapshot.pop()

    def do_snapshot(self, snapshot: Gtk.Snapshot):
        w = float(self.get_allocated_width())
        h = float(self.get_allocated_height())

        if self.rect[2] <= 0 or self.rect[3] <= 0:
            self.init_default_rect()

        x, y, rw, rh = self.rect

        dim = Gdk.RGBA(); dim.parse("rgba(0,0,0,0.45)")
        white = Gdk.RGBA(); white.parse("rgba(255,255,255,0.90)")

        # dim around crop rect
        snapshot.append_color(dim, Graphene.Rect().init(0, 0, w, y))
        snapshot.append_color(dim, Graphene.Rect().init(0, y + rh, w, max(0.0, h - (y + rh))))
        snapshot.append_color(dim, Graphene.Rect().init(0, y, x, rh))
        snapshot.append_color(dim, Graphene.Rect().init(x + rw, y, max(0.0, w - (x + rw)), rh))

        # border
        t = 2.0
        snapshot.append_color(white, Graphene.Rect().init(x, y, rw, t))
        snapshot.append_color(white, Graphene.Rect().init(x, y + rh - t, rw, t))
        snapshot.append_color(white, Graphene.Rect().init(x, y, t, rh))
        snapshot.append_color(white, Graphene.Rect().init(x + rw - t, y, t, rh))

        # circular handles
        fill = Gdk.RGBA(); fill.parse("rgba(255,255,255,0.25)")
        stroke = Gdk.RGBA(); stroke.parse("rgba(255,255,255,0.95)")

        r_outer = float(self.HANDLE) * 0.5
        r_inner = max(1.0, r_outer - 2.0)

        for _, (hx, hy) in self.handle_points().items():
            self.snapshot_circle(snapshot, hx, hy, r_outer, stroke)
            self.snapshot_circle(snapshot, hx, hy, r_inner, fill)

    def on_drag_begin(self, gesture, start_x, start_y):
        if self.rect[2] <= 0 or self.rect[3] <= 0:
            self.init_default_rect()

        mode = self.hit_test(float(start_x), float(start_y))
        if mode is None:
            ix, iy, iw, ih = self.image_rect_in_widget()
            if not (ix <= start_x <= ix + iw and iy <= start_y <= iy + ih):
                self.mode = None
                return
            self.rect = self.clamp_rect_to_image([start_x - 80, start_y - 80, 160, 160])
            self.queue_draw()
            mode = "move"

        self.mode = mode
        self.drag_start = (float(start_x), float(start_y))
        self.rect_start = self.rect.copy()

    def on_drag_update(self, gesture, offset_x, offset_y):
        if not self.mode or self.rect_start is None:
            return

        dx = float(offset_x)
        dy = float(offset_y)

        x0, y0, w0, h0 = self.rect_start

        if self.mode == "move":
            new_rect = [x0 + dx, y0 + dy, w0, h0]
        else:
            x, y, w, h = x0, y0, w0, h0

            if self.mode == "nw":
                x = x0 + dx
                y = y0 + dy
                w = (x0 + w0) - x
                h = (y0 + h0) - y
            elif self.mode == "ne":
                y = y0 + dy
                w = w0 + dx
                h = (y0 + h0) - y
            elif self.mode == "sw":
                x = x0 + dx
                w = (x0 + w0) - x
                h = h0 + dy
            elif self.mode == "se":
                w = w0 + dx
                h = h0 + dy

            new_rect = [x, y, w, h]

        self.rect = self.clamp_rect_to_image(new_rect)
        self.queue_draw()

    def on_drag_end(self, *_args):
        self.mode = None
        self.rect_start = None

    def get_crop_in_image_pixels(self) -> tuple[int, int, int, int]:
        ix, iy, iw, ih = self.image_rect_in_widget()
        x, y, w, h = self.rect

        nx = (x - ix) / iw
        ny = (y - iy) / ih
        nw = w / iw
        nh = h / ih

        tw = self.texture.get_width()
        th = self.texture.get_height()

        x_px = int(nx * tw)
        y_px = int(ny * th)
        w_px = int(nw * tw)
        h_px = int(nh * th)

        x_px = max(0, min(x_px, tw - 1))
        y_px = max(0, min(y_px, th - 1))
        w_px = max(1, min(w_px, tw - x_px))
        h_px = max(1, min(h_px, th - y_px))

        return (x_px, y_px, w_px, h_px)
