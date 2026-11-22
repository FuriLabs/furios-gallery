# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import gi
gi.require_version("Gtk", "4.0")

from PIL import Image
from gi.repository import Gtk, GLib
from .furios_media_tools import preview_sigma, BLUR_FRACTION_PER_UNIT, blur_sigma
from .ui import (create_main_bar_body, create_cancel_btn, create_apply_btn, make_slider_menu_button)

# name, title, icon, default, lower, upper, step
ADJUSTMENTS = (
    ("brightness", "Brightness", "weather-clear-symbolic", 1.0, 0.5, 1.5, 0.01),
    ("contrast", "Contrast", "semi-starred-symbolic", 1.0, 0.5, 1.5, 0.01),
    ("saturation", "Saturation", "color-select-symbolic", 1.0, 0.0, 2.0, 0.01),
    ("temperature", "Temperature", "temperature-symbolic", 0.0, 0.0, 1.0, 0.01),
    ("blur", "Blur", "edit-select-all-symbolic", 0.0, 0.0, 3.0, 0.05),
)

DEFAULTS = {name: default for name, _t, _i, default, *_ in ADJUSTMENTS}

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

class ImageTransformationsOverlay(Gtk.Widget):
    def __init__(self, picture_widget: Gtk.Widget, media_path: str):
        super().__init__()
        self.picture_widget = picture_widget
        self.media_path = media_path
        self.on_cancel = None
        self.on_apply = None
        self.values = dict(DEFAULTS)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_halign(Gtk.Align.FILL)
        self.set_valign(Gtk.Align.FILL)

        with Image.open(self.media_path) as im:
            self.image_width, self.image_height = im.size

        self.preview_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(self.get_display(), self.preview_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)
        self.preview_update_id = 0

        self.bar = self.build_bar()

    def clear_preview(self):
        if self.preview_update_id:
            GLib.source_remove(self.preview_update_id)
            self.preview_update_id = 0
        self.picture_widget.remove_css_class("image_transformations-preview")

    def build_bar(self) -> Gtk.Widget:
        bar = create_main_bar_body(8, 6, 6, 12, 6, "vertical")

        outer = Gtk.ScrolledWindow()
        outer.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        outer.set_overlay_scrolling(True)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_halign(Gtk.Align.CENTER)
        row.set_margin_top(1)
        row.set_margin_bottom(1)
        outer.set_child(row)

        for name, title, icon, default, lower, upper, step in ADJUSTMENTS:
            row.append(make_slider_menu_button(
                icon_name=icon,
                tooltip=title,
                title=title,
                value=self.values[name],
                lower=lower,
                upper=upper,
                step=step,
                digits=2,
                on_change=lambda v, name=name: self.on_value_changed(name, v),
            ))

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_hexpand(True)

        cancel = create_cancel_btn(self.on_cancel_clicked)

        apply = create_apply_btn(self.on_apply_clicked)

        actions.append(cancel)
        actions.append(apply)

        bar.append(outer)
        bar.append(actions)
        return bar

    def on_cancel_clicked(self, _btn):
        self.clear_preview()
        self.values = dict(DEFAULTS)
        if callable(self.on_cancel):
            self.on_cancel()

    def on_apply_clicked(self, _btn):
        self.clear_preview()
        if callable(self.on_apply):
            self.on_apply()

    def get_bar_widget(self) -> Gtk.Widget:
        return self.bar

    def get_export_params(self) -> dict:
        v = self.values
        return {
            "brightness": v["brightness"],
            "contrast": v["contrast"],
            "saturation": v["saturation"],
            "sepia": max(0.0, clamp(v["temperature"], 0.0, 1.0)) * 0.6,
            "blur": blur_sigma(v["blur"] * BLUR_FRACTION_PER_UNIT, self.image_width, self.image_height),
        }

    def on_value_changed(self, name: str, value: float):
        self.values[name] = float(value)
        if not self.preview_update_id:
            self.preview_update_id = GLib.timeout_add(16, self.update_preview)

    def update_preview(self) -> bool:
        self.preview_update_id = 0
        p = self.get_export_params()

        parts = [
            f"brightness({p['brightness']:.3f})",
            f"contrast({p['contrast']:.3f})",
            f"saturate({p['saturation']:.3f})",
            f"sepia({p['sepia']:.3f})",
        ]

        sigma = preview_sigma(p["blur"], self.image_width, self.image_height, self.picture_widget.get_allocated_width(), self.picture_widget.get_allocated_height())
        if sigma > 1e-3:
            parts.append(f"blur({sigma:.3f}px)")

        css = f".{"image_transformations-preview"} {{ filter: {' '.join(parts)}; }}"
        self.preview_provider.load_from_data(css.encode())
        self.picture_widget.add_css_class("image_transformations-preview")
        return GLib.SOURCE_REMOVE