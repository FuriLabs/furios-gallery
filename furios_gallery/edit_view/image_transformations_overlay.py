# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gtk, Gdk, GLib
from .ui import (create_main_bar_body, create_cancel_btn, create_apply_btn, make_slider_menu_button)

class ImageTransformationsOverlay(Gtk.Widget):
    def __init__(self, picture_widget: Gtk.Widget, media_path: str):
        super().__init__()
        self.picture_widget = picture_widget
        self.media_path = media_path

        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_halign(Gtk.Align.FILL)
        self.set_valign(Gtk.Align.FILL)

        self.preview_css_class = "imtr-preview"
        self.css_provider = Gtk.CssProvider()
        self.css_update_id = 0

        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            self.css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.picture_widget.add_css_class(self.preview_css_class)
        self.brightness = 1.00
        self.contrast = 1.00
        self.saturation = 1.00
        self.temperature = 0.00
        self.blur = 0.0

        self.defaults = (self.brightness, self.contrast, self.saturation, self.temperature, self.blur)

        self.bar = self.build_imtr_bar()

    def get_bar_widget(self) -> Gtk.Widget:
        return self.bar

    def build_imtr_bar(self) -> Gtk.Widget:
        bar = create_main_bar_body(8, 6, 6, 12, 6, "vertical")

        outer = Gtk.ScrolledWindow()
        outer.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        outer.set_overlay_scrolling(True)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_halign(Gtk.Align.CENTER)
        row.set_margin_top(1)
        row.set_margin_bottom(1)
        outer.set_child(row)

        # Brigthness, Contrast, Saturation, Temperature, Blur
        row.append(make_slider_menu_button(
            icon_name="weather-clear-symbolic",
            tooltip="Brightness",
            title="Brightness",
            value=self.brightness,
            lower=0.0,
            upper=2.0,
            step=0.01,
            digits=2,
            on_change=self.on_brightness_changed,
        ))

        row.append(make_slider_menu_button(
            icon_name="semi-starred-symbolic",
            tooltip="Contrast",
            title="Contrast",
            value=self.contrast,
            lower=0.0,
            upper=2.0,
            step=0.01,
            digits=2,
            on_change=self.on_contrast_changed,
        ))

        row.append(make_slider_menu_button(
            icon_name="color-select-symbolic",
            tooltip="Saturation",
            title="Saturation",
            value=self.saturation,
            lower=0.0,
            upper=2.0,
            step=0.01,
            digits=2,
            on_change=self.on_saturation_changed,
        ))

        row.append(make_slider_menu_button(
            icon_name="temperature-symbolic",
            tooltip="Temperature",
            title="Temperature",
            value=self.temperature,
            lower=-1.0,
            upper=1.0,
            step=0.01,
            digits=2,
            on_change=self.on_temperature_changed,
        ))

        row.append(make_slider_menu_button(
            icon_name="edit-select-all-symbolic",
            tooltip="Blur",
            title="Blur",
            value=self.blur,
            lower=0.0,
            upper=5.0,
            step=0.05,
            digits=2,
            on_change=self.on_blur_changed,
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

    def on_brightness_changed(self, v: float):
        self.brightness = v
        self.update_preview()

    def on_contrast_changed(self, v: float):
        self.contrast = v
        self.update_preview()

    def on_saturation_changed(self, v: float):
        self.saturation = v
        self.update_preview()

    def on_temperature_changed(self, v: float):
        self.temperature = v
        self.update_preview()

    def on_blur_changed(self, v: float):
        self.blur = v
        self.update_preview()

    def build_filter_css(self) -> str:
        b = max(0.0, min(2.0, float(self.brightness)))
        c = max(0.0, min(2.0, float(self.contrast)))
        s = max(0.0, min(2.0, float(self.saturation)))
        bl = max(0.0, min(10.0, float(self.blur)))

        t = max(-1.0, min(1.0, float(self.temperature)))
        sep = max(0.0, t) * 0.6

        parts = [
            f"brightness({b:.3f})",
            f"contrast({c:.3f})",
            f"saturate({s:.3f})",
            f"sepia({sep:.3f})",
        ]

        if bl > 0.0001:
            parts.append(f"blur({bl:.3f}px)")

        return " ".join(parts)

    def update_preview(self):
        if getattr(self, "css_update_id", 0):
            GLib.source_remove(self.css_update_id)
        self.css_update_id = GLib.timeout_add(16, self.apply_preview_css)

    def apply_preview_css(self):
        self.css_update_id = 0
        filt = self.build_filter_css()

        css = f"""
        .{self.preview_css_class} {{
            filter: {filt};
        }}
        """.encode("utf-8")

        self.css_provider.load_from_data(css)
        return False

    def on_cancel_clicked(self, btn=None):
        self.brightness, self.contrast, self.saturation, self.temperature, self.blur = self.defaults
        self.update_preview()

        if callable(getattr(self, "on_cancel", None)):
            self.on_cancel()

    def on_apply_clicked(self, btn=None):
        if callable(getattr(self, "on_apply", None)):
            self.on_apply(getattr(self, "selected_filter", "filter-original"))