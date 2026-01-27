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

        # convert IMAGE pts -> WIDGET pts for drawing
        wpts = [self.image_to_widget(xi, yi) for (xi, yi) in pts]

        path = Gsk.PathBuilder.new()
        x0, y0 = wpts[0]
        path.move_to(x0, y0)
        for (x, y) in wpts[1:]:
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
        xw = float(start_x)
        yw = float(start_y)

        img_pt = self.widget_to_image(xw, yw)

        if self.clamp_to_image and img_pt is None:
            self.current_pts = None
            return

        if img_pt is None:
            self.current_pts = None
            return

        self.drag_begin_widget = (xw, yw) # widget coords for offsets
        self.current_pts = [img_pt] # image coords for storage
        self.queue_draw()

    def on_drag_update(self, gesture: Gtk.GestureDrag, offset_x: float, offset_y: float):
        if not self.current_pts:
            return

        # GestureDrag gives offsets from drag-begin point in WIDGET space
        # We need current widget point first, then convert to image.
        # We can reconstruct current widget point from the begin point:
        # BUT we stored image begin point, so we must keep the begin widget point too.
        if not hasattr(self, "drag_begin_widget"):
            return

        xw0, yw0 = self.drag_begin_widget
        xw = xw0 + float(offset_x)
        yw = yw0 + float(offset_y)

        img_pt = self.widget_to_image(xw, yw)
        if img_pt is None:
            return

        lx, ly = self.current_pts[-1]
        scale = self.image_scale_in_widget()
        min_img_dist2 = (self.min_point_dist2 / (scale * scale)) if scale > 0 else self.min_point_dist2

        dx = img_pt[0] - lx
        dy = img_pt[1] - ly
        if (dx*dx + dy*dy) < min_img_dist2:
            return

        self.current_pts.append(img_pt)
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
        if hasattr(self, "drag_begin_widget"):
            delattr(self, "drag_begin_widget")
        self.queue_draw()

    '''
    * Coordinate Transform Helpers *
    '''
    def image_scale_in_widget(self) -> float:
        # widget pixels per image pixel (same in x/y for "contain")
        _, _, iw, _ = self.image_rect_in_widget()
        tw = float(self.texture.get_width())
        return (iw / tw) if tw else 1.0

    # Since we are using Gsk Path builder and this one uses widget coordinates, we need to transform into image coordiiantes:
    def widget_to_image(self, xw: float, yw: float) -> tuple[float, float] | None:
        ix, iy, iw, ih = self.image_rect_in_widget()
        tw = float(self.texture.get_width())
        th = float(self.texture.get_height())

        if iw <= 0 or ih <= 0 or tw <= 0 or th <= 0:
            return None

        if not (ix <= xw <= ix + iw and iy <= yw <= iy + ih):
            return None

        # normalized within displayed image rect
        u = (xw - ix) / iw
        v = (yw - iy) / ih

        # convert to texture pixels
        xi = u * tw
        yi = v * th
        return (xi, yi)

    def image_to_widget(self, xi: float, yi: float) -> tuple[float, float]:
        ix, iy, iw, ih = self.image_rect_in_widget()
        tw = float(self.texture.get_width())
        th = float(self.texture.get_height())

        u = xi / tw if tw else 0.0
        v = yi / th if th else 0.0

        xw = ix + u * iw
        yw = iy + v * ih
        return (xw, yw)
