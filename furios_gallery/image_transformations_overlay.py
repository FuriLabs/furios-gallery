# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gtk, Gdk, GLib

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

    def make_slider_menu_button(self, icon_name: str, tooltip: str, title: str, value: float, lower: float, upper: float, step: float, digits: int, on_change) -> Gtk.MenuButton:
        btn = Gtk.MenuButton()
        btn.set_tooltip_text(tooltip)
        btn.set_valign(Gtk.Align.CENTER)
        btn.set_has_frame(True)

        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(18)
        btn.set_child(icon)

        pop = Gtk.Popover()
        pop.set_has_arrow(True)
        pop.set_size_request(260, -1)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_hexpand(True)

        label = Gtk.Label(label=title)
        label.set_valign(Gtk.Align.CENTER)
        label.add_css_class("dim-label")

        adj = Gtk.Adjustment(
            value=float(value),
            lower=float(lower),
            upper=float(upper),
            step_increment=float(step),
            page_increment=float(step) * 10.0,
        )

        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        scale.set_draw_value(True)
        scale.set_digits(int(digits))
        scale.set_valign(Gtk.Align.CENTER)
        scale.set_hexpand(True)

        adj.connect("value-changed", lambda a: on_change(float(a.get_value())))

        box.append(label)
        box.append(scale)
        pop.set_child(box)
        btn.set_popover(pop)

        return btn

    def build_imtr_bar(self) -> Gtk.Widget:
        bar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        bar.set_hexpand(True)
        bar.set_halign(Gtk.Align.FILL)
        bar.set_valign(Gtk.Align.END)
        bar.set_margin_start(6)
        bar.set_margin_end(6)
        bar.set_margin_bottom(12)
        bar.add_css_class("osd")
        bar.add_css_class("toolbar")

        outer = Gtk.ScrolledWindow()
        outer.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        outer.set_overlay_scrolling(True)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_halign(Gtk.Align.CENTER)
        row.set_margin_top(1)
        row.set_margin_bottom(1)
        outer.set_child(row)

        # Brigthness, Contrast, Saturation, Temperature, Blur
        row.append(self.make_slider_menu_button(
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

        row.append(self.make_slider_menu_button(
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

        row.append(self.make_slider_menu_button(
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

        row.append(self.make_slider_menu_button(
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

        row.append(self.make_slider_menu_button(
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

        cancel = Gtk.Button(label="Cancel")
        cancel.set_hexpand(True)
        cancel.connect("clicked", self.on_cancel_clicked)

        apply = Gtk.Button(label="Apply")
        apply.set_hexpand(True)
        apply.add_css_class("suggested-action")
        apply.connect("clicked", self.on_apply_clicked)

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

    def on_cancel_clicked(self, _btn=None):
        self.brightness, self.contrast, self.saturation, self.temperature, self.blur = self.defaults
        self.update_preview()

    def on_apply_clicked(self, _btn=None):
        # TODO
        pass

