# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, Gsk

class DrawOverlay(Gtk.Widget):
    def __init__(
        self,
        picture_widget: Gtk.Widget,
        texture: Gdk.Texture,
        *,
        clamp_to_image: bool = True,
        line_width: float = 4.0,
        color_rgba: str = "rgba(0, 140, 255, 0.95)",
        min_point_dist: float = 1.5,
    ):
        super().__init__()
        self.picture_widget = picture_widget
        self.texture = texture

        self.clamp_to_image = clamp_to_image
        self.line_width = float(line_width)
        self.min_point_dist2 = float(min_point_dist) ** 2

        self.color = Gdk.RGBA()
        self.color.parse(color_rgba)

        # Each stroke is: {"pts": [(x,y), ...], "width": float, "color": Gdk.RGBA}
        self.strokes: list[dict] = []
        self.current_pts: list[tuple[float, float]] | None = None

        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_halign(Gtk.Align.FILL)
        self.set_valign(Gtk.Align.FILL)
        self.set_can_target(True)

        drag = Gtk.GestureDrag.new()
        drag.connect("drag-begin", self.on_drag_begin)
        drag.connect("drag-update", self.on_drag_update)
        drag.connect("drag-end", self.on_drag_end)
        self.add_controller(drag)

    '''
    * Public Helpers *
    '''
    def set_color(self, rgba: Gdk.RGBA):
        self.color = rgba.copy() if hasattr(rgba, "copy") else rgba
        self.queue_draw()

    def set_line_width(self, width: float):
        self.line_width = float(max(1.0, width))
        self.queue_draw()

    def clear(self):
        self.strokes.clear()
        self.current_pts = None
        self.queue_draw()

    def undo_last_stroke(self):
        if self.strokes:
            self.strokes.pop()
            self.queue_draw()

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

    '''
    * Snapshot Rendering *
    '''
    def do_snapshot(self, snapshot: Gtk.Snapshot):
        for s in self.strokes:
            self.snapshot_stroke(snapshot, s["pts"], s["width"], s["color"])

        if self.current_pts and len(self.current_pts) >= 2:
            self.snapshot_stroke(snapshot, self.current_pts, self.line_width, self.color)

    def snapshot_stroke(self, snapshot: Gtk.Snapshot,
                         pts: list[tuple[float, float]],
                         width: float,
                         color: Gdk.RGBA):
        if len(pts) < 2:
            return

        path = Gsk.PathBuilder.new()
        x0, y0 = pts[0]
        path.move_to(x0, y0)
        for (x, y) in pts[1:]:
            path.line_to(x, y)

        gsk_path = path.to_path()

        stroke = Gsk.Stroke.new(float(width))
        stroke.set_line_cap(Gsk.LineCap.ROUND)
        stroke.set_line_join(Gsk.LineJoin.ROUND)

        snapshot.append_stroke(gsk_path, stroke, color)

    '''
    * Events *
    '''
    def inside_image(self, x: float, y: float) -> bool:
        if not self.clamp_to_image:
            return True
        ix, iy, iw, ih = self.image_rect_in_widget()
        return (ix <= x <= ix + iw) and (iy <= y <= iy + ih)

    def on_drag_begin(self, gesture: Gtk.GestureDrag, start_x: float, start_y: float):
        x = float(start_x)
        y = float(start_y)

        if not self.inside_image(x, y):
            self.current_pts = None
            return

        self.current_pts = [(x, y)]
        self.queue_draw()

    def on_drag_update(self, gesture: Gtk.GestureDrag, offset_x: float, offset_y: float):
        if not self.current_pts:
            return

        x0, y0 = self.current_pts[0]
        x = x0 + float(offset_x)
        y = y0 + float(offset_y)

        if not self.inside_image(x, y):
            return

        lx, ly = self.current_pts[-1]
        dx = x - lx
        dy = y - ly
        if (dx * dx + dy * dy) < self.min_point_dist2:
            return

        self.current_pts.append((x, y))
        self.queue_draw()

    def on_drag_end(self, gesture: Gtk.GestureDrag, offset_x: float, offset_y: float):
        if not self.current_pts:
            return

        if len(self.current_pts) >= 2:
            # capture style NOW so future changes don't affect this stroke
            self.strokes.append({
                "pts": self.current_pts,
                "width": float(self.line_width),
                "color": self.color.copy() if hasattr(self.color, "copy") else self.color,
            })

        self.current_pts = None
        self.queue_draw()
