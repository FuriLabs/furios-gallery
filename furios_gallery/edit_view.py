# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import gi, os
gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")

from .draw_overlay import DrawOverlay
from .crop_overlay import CropOverlay
from .filters_overlay import FiltersOverlay
from .furios_media_tools import FuriOSMediaTools
from .image_viewer_widget import ImageViewerWidget
from gi.repository import Adw, Gtk, Gdk, GdkPixbuf, Graphene, GLib
from .ui import (create_edit_view_main_box, create_edit_view_overlay)

class EditView(Adw.NavigationPage):
    def __init__(self, app, media_path: str):
        super().__init__(title="Edit")
        self.app = app
        self.media_path = media_path
        self.zoomable_image = None
        self.texture: Gdk.Texture | None = None
        self.picture: Gtk.ScrolledWindow | None = None
        self.crop_overlay = None
        self.setup_content()

    def setup_content(self):
        self.main_box = create_edit_view_main_box()
        self.overlay = create_edit_view_overlay()

        viewer = self.setup_picture_to_edit(self.media_path)

        # self.overlay.set_child(viewer)
        self.main_box.append(viewer)

        # bottom tools bar on OUTER overlay (so it stays visible)
        self.setup_editing_tools_bar()

        # Set the image viewer as the child of the main box.
        self.overlay.set_child(self.main_box)

        # Set Content for Navigation Page.
        self.set_child(self.overlay)

        # Disable gesture navigation
        self.set_can_pop(False)

    def setup_picture_to_edit(self, media_path: str | None) -> Gtk.Widget:
        if not media_path or not os.path.exists(media_path):
            empty = Gtk.Label(label="No media found.")
            empty.set_hexpand(True)
            empty.set_vexpand(True)
            empty.set_halign(Gtk.Align.CENTER)
            empty.set_valign(Gtk.Align.CENTER)
            return empty

        try:
            self.texture = Gdk.Texture.new_from_filename(media_path)
        except GLib.Error:
            error = Gtk.Label(label="Failed to load image.")
            error.set_hexpand(True)
            error.set_vexpand(True)
            error.set_halign(Gtk.Align.CENTER)
            error.set_valign(Gtk.Align.CENTER)
            return error

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.set_halign(Gtk.Align.FILL)
        scrolled.set_valign(Gtk.Align.FILL)

        self.zoomable_image = ImageViewerWidget(media_path, self.app, scrolled)
        self.zoomable_image.set_hexpand(True)
        self.zoomable_image.set_vexpand(True)
        self.zoomable_image.set_halign(Gtk.Align.CENTER)
        self.zoomable_image.set_valign(Gtk.Align.CENTER)

        scrolled.set_child(self.zoomable_image)
        self.zoomable_image.init_gestures()

        self.picture = scrolled

        return scrolled

    '''
    * Editing Bar *
    '''
    
    def setup_editing_tools_bar(self):
        def on_crop_clicked(btn):
            if not self.texture or not self.picture:
                return

            # Return image to original size
            self.zoomable_image.reset_view_fit()

            # Disable zoom
            self.zoomable_image.set_zoom_enabled(not self.zoomable_image.zoom_enabled)

            # Hide the edit bar
            self.set_edit_bar_visible(False)

            if self.crop_overlay is None:
                self.crop_overlay = CropOverlay(self.picture, self.texture)
                self.overlay.add_overlay(self.crop_overlay)
                self.show_crop_bar()
            else:
                self.overlay.remove_overlay(self.crop_overlay)
                self.crop_overlay = None
                self.hide_crop_bar()
                self.set_edit_bar_visible(True)

        def on_filters_clicked(btn):
            if not self.texture or not self.zoomable_image:
                return

            self.zoomable_image.reset_view_fit()
            self.zoomable_image.set_zoom_enabled(False)
            self.set_edit_bar_visible(False)

            if getattr(self, "filters_overlay", None):
                self.overlay.remove_overlay(self.filters_overlay.get_bar_widget())
                self.filters_overlay = None

            target_widget = getattr(self.zoomable_image, "picture", self.zoomable_image)

            self.filters_overlay = FiltersOverlay(target_widget, media_path=self.media_path, thumbnails=self.app.thumbnails)

            self.filters_overlay.on_cancel = lambda: self.on_filters_cancel_clicked(btn)
            self.filters_overlay.on_apply  = lambda selected: self.on_filters_apply_clicked(btn)

            self.overlay.add_overlay(self.filters_overlay.get_bar_widget())

        def on_fine_tunes_clicked(btn):
            return

        def on_drawing_clicked(btn):
            if not self.texture or not self.picture:
                return

            self.zoomable_image.reset_view_fit()
            self.zoomable_image.set_zoom_enabled(False)
            self.set_edit_bar_visible(False)

            if getattr(self, "draw_overlay", None):
                self.overlay.remove_overlay(self.draw_overlay)
                self.draw_overlay = None

            self.draw_overlay = DrawOverlay(self.picture, self.texture, clamp_to_image=True)
            self.overlay.add_overlay(self.draw_overlay)
            self.draw_overlay.queue_draw()
            self.show_drawing_bar()

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bar.set_hexpand(True)
        bar.set_halign(Gtk.Align.FILL)
        bar.set_valign(Gtk.Align.END)
        bar.set_margin_start(12)
        bar.set_margin_end(12)
        bar.set_margin_bottom(12)
        bar.set_margin_top(6)

        bar.add_css_class("toolbar")
        bar.add_css_class("osd")

        def _icon_button(icon_name: str, tooltip: str, handler):
            btn = Gtk.Button()
            btn.set_has_frame(False)
            btn.set_tooltip_text(tooltip)

            img = Gtk.Image.new_from_icon_name(icon_name)
            img.set_pixel_size(22)
            btn.set_child(img)

            btn.connect("clicked", handler)
            return btn

        crop_btn = _icon_button("zoom-fit-best", "Crop", on_crop_clicked)
        filters_btn = _icon_button("color-select", "Filters", on_filters_clicked)
        fine_tunes_btn = _icon_button("preferences-system", "Fine tunes", on_fine_tunes_clicked)
        drawing_btn = _icon_button("document-edit", "Drawing", on_drawing_clicked)

        for b in (crop_btn, filters_btn, fine_tunes_btn, drawing_btn):
            b.set_hexpand(True)
            b.set_halign(Gtk.Align.CENTER)
            bar.append(b)

        self.overlay.add_overlay(bar)
        bar.set_can_target(True)
        self.edit_bar = bar

    def set_edit_bar_visible(self, visible: bool):
        if getattr(self, "edit_bar", None):
            self.edit_bar.set_visible(visible)
            self.edit_bar.set_can_target(visible)

    '''
    * Crop Feature *
    '''
    def show_crop_bar(self):
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
        cancel.connect("clicked", self.on_crop_cancel_clicked)

        crop = Gtk.Button(label="Crop")
        crop.set_hexpand(True)
        crop.set_halign(Gtk.Align.FILL)
        crop.add_css_class("suggested-action")
        crop.connect("clicked", self.on_crop_apply_clicked)

        bar.append(cancel)
        bar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        bar.append(crop)

        self.crop_bar = bar
        self.overlay.add_overlay(bar)
        bar.set_can_target(True)

    def hide_crop_bar(self):
        if getattr(self, "crop_bar", None):
            self.overlay.remove_overlay(self.crop_bar)
            self.crop_bar = None

    def on_crop_cancel_clicked(self, btn):
        if self.crop_overlay:
            self.overlay.remove_overlay(self.crop_overlay)
            self.crop_overlay = None
        self.hide_crop_bar()
        self.set_edit_bar_visible(True)
        self.zoomable_image.set_zoom_enabled(True)

    def on_crop_apply_clicked(self, btn):
        if not self.crop_overlay:
            return

        x, y, w, h = self.crop_overlay.get_crop_in_image_pixels()

        dialog = Adw.MessageDialog.new(
            self.get_root(),
            "Save cropped image?",
            "Do you want to overwrite the original file or save a new copy?"
        )

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("copy", "Save Copy")
        dialog.add_response("overwrite", "Overwrite")

        dialog.set_response_appearance("overwrite", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_response_appearance("copy", Adw.ResponseAppearance.SUGGESTED)

        dialog.set_default_response("copy")
        dialog.set_close_response("cancel")

        def on_response(dlg, response_id: str):
            if response_id == "cancel":
                dlg.close()
                return

            overwrite = (response_id == "overwrite")

            out_path = FuriOSMediaTools.compute_output_path(
                self.media_path,
                overwrite=overwrite,
                out_path=None,
                suffix="_cropped",
            )

            try:
                written_path = FuriOSMediaTools.crop_image_to_disk(
                    self.media_path,
                    x, y, w, h,
                    overwrite=overwrite,
                    out_path=out_path,
                    suffix="_cropped"
                )
                print("Cropped written to:", written_path)
                # Remove old viewer
                if self.picture:
                    self.main_box.remove(self.picture)

                # Create and add new viewer
                self.picture = self.setup_picture_to_edit(written_path)
                self.main_box.append(self.picture)

            except Exception as e:
                print("Crop failed:", e)

            self.on_crop_cancel_clicked(btn)
            self.set_edit_bar_visible(True)
            self.zoomable_image.set_zoom_enabled(True)

            dlg.close()

        dialog.connect("response", on_response)
        dialog.present()

    '''
    * Filters Feature *
    '''
    def on_filters_cancel_clicked(self, btn=None):
        if getattr(self, "filters_overlay", None):
            self.overlay.remove_overlay(self.filters_overlay.get_bar_widget())
            self.filters_overlay = None

        self.set_edit_bar_visible(True)
        self.zoomable_image.set_zoom_enabled(True)

    def on_filters_apply_clicked(self, btn=None):
        if not getattr(self, "filters_overlay", None):
            self.on_filters_cancel_clicked(btn)
            return

        css_class = getattr(self.filters_overlay, "selected_filter", "filter-original")

        dialog = Adw.MessageDialog.new(
            self.get_root(),
            "Save filtered image?",
            "Do you want to overwrite the original file or save a new copy?"
        )

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("copy", "Save Copy")
        dialog.add_response("overwrite", "Overwrite")

        dialog.set_response_appearance("overwrite", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_response_appearance("copy", Adw.ResponseAppearance.SUGGESTED)

        dialog.set_default_response("copy")
        dialog.set_close_response("cancel")

        def on_response(dlg, response_id: str):
            if response_id == "cancel":
                dlg.close()
                return

            overwrite = (response_id == "overwrite")

            out_path = FuriOSMediaTools.compute_output_path(
                self.media_path,
                overwrite=overwrite,
                out_path=None,
                suffix="_filtered",
            )

            try:
                # TODO: This must bake the filter into pixels.
                print("Clicked Apply")

            except Exception as e:
                print("Failed to apply filter:", e)

            # Exit filter mode + restore UI
            self.on_filters_cancel_clicked(btn)
            self.set_edit_bar_visible(True)
            self.zoomable_image.set_zoom_enabled(True)

            dlg.close()

        dialog.connect("response", on_response)
        dialog.present()

    '''
    * Drawing Feature *
    '''
    def show_drawing_bar(self):
        if getattr(self, "drawing_bar", None):
            return

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        bar.set_halign(Gtk.Align.FILL)
        bar.set_valign(Gtk.Align.END)
        bar.set_hexpand(True)
        bar.set_margin_start(5)
        bar.set_margin_end(5)
        bar.set_margin_bottom(12)
        bar.set_margin_top(6)

        bar.add_css_class("osd")
        bar.add_css_class("toolbar")
        bar.set_can_target(True)

        # Cancel button
        cancel = Gtk.Button(label="Cancel")
        cancel.set_hexpand(True)
        cancel.set_halign(Gtk.Align.FILL)
        cancel.connect("clicked", self.on_drawing_cancel_clicked)

        # Color popover button
        color_menu = Gtk.MenuButton()
        color_menu.set_tooltip_text("Stroke color")
        color_menu.set_valign(Gtk.Align.CENTER)
        color_menu.set_has_frame(True)

        color_icon = Gtk.Image.new_from_icon_name("color-select")
        color_icon.set_pixel_size(18)
        color_menu.set_child(color_icon)

        color_pop = Gtk.Popover()
        color_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        color_box.set_margin_top(10)
        color_box.set_margin_bottom(10)
        color_box.set_margin_start(10)
        color_box.set_margin_end(10)

        color_label = Gtk.Label(label="Stroke color")
        color_label.set_halign(Gtk.Align.START)

        color_dialog = Gtk.ColorDialog()
        color_btn = Gtk.ColorDialogButton.new(color_dialog)

        if getattr(self, "draw_overlay", None):
            color_btn.set_rgba(self.draw_overlay.color)

        def _on_color_changed(btn, _pspec=None):
            if not getattr(self, "draw_overlay", None):
                return
            self.draw_overlay.set_color(btn.get_rgba())

        color_btn.connect("notify::rgba", _on_color_changed)

        color_box.append(color_label)
        color_box.append(color_btn)
        color_pop.set_child(color_box)
        color_menu.set_popover(color_pop)

        # Size popover button
        size_btn = Gtk.MenuButton()
        size_btn.set_tooltip_text("Stroke size")
        size_btn.set_valign(Gtk.Align.CENTER)
        size_btn.set_has_frame(True)

        size_icon = Gtk.Image.new_from_icon_name("find-location")
        size_icon.set_pixel_size(18)
        size_btn.set_child(size_icon)

        size_pop = Gtk.Popover()
        size_pop.set_has_arrow(True)

        size_pop.set_size_request(220, -1)

        size_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        size_box.set_margin_top(10)
        size_box.set_margin_bottom(10)
        size_box.set_margin_start(12)
        size_box.set_margin_end(12)
        size_box.set_hexpand(True)

        size_label = Gtk.Label(label="Size")
        size_label.set_valign(Gtk.Align.CENTER)
        size_label.add_css_class("dim-label")

        adj = Gtk.Adjustment(value=4.0, lower=1.0, upper=100.0, step_increment=1.0, page_increment=2.0)

        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        scale.set_draw_value(True)
        scale.set_digits(0)
        scale.set_valign(Gtk.Align.CENTER)
        scale.set_hexpand(True)

        scale.set_size_request(150, -1)

        if getattr(self, "draw_overlay", None):
            adj.set_value(float(self.draw_overlay.line_width))

        def _on_size_changed(s):
            if getattr(self, "draw_overlay", None):
                self.draw_overlay.set_line_width(s.get_value())

        scale.connect("value-changed", _on_size_changed)

        size_box.append(size_label)
        size_box.append(scale)

        size_pop.set_child(size_box)
        size_btn.set_popover(size_pop)

        # Delete / Undo last stroke button
        undo_btn = Gtk.MenuButton()
        undo_btn.set_has_frame(True)
        undo_btn.set_valign(Gtk.Align.CENTER)
        undo_btn.set_tooltip_text("Undo last stroke")

        undo_icon = Gtk.Image.new_from_icon_name("edit-undo-symbolic")
        undo_icon.set_pixel_size(18)
        undo_btn.set_child(undo_icon)

        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", lambda *_: self.draw_overlay and self.draw_overlay.undo_last_stroke())
        undo_btn.add_controller(gesture)

        # Done Button
        done = Gtk.Button(label="Done")
        done.set_hexpand(True)
        done.set_halign(Gtk.Align.FILL)
        done.add_css_class("suggested-action")
        done.connect("clicked", self.on_drawing_done_clicked)

        # Layout
        bar.append(cancel)
        bar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        bar.append(color_menu)
        bar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        bar.append(size_btn)
        bar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        bar.append(undo_btn)
        bar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        bar.append(done)

        self.drawing_bar = bar
        self.overlay.add_overlay(bar)

    def on_drawing_cancel_clicked(self, _btn):
        if getattr(self, "draw_overlay", None):
            self.overlay.remove_overlay(self.draw_overlay)
            self.draw_overlay = None

        if getattr(self, "drawing_bar", None):
            self.overlay.remove_overlay(self.drawing_bar)
            self.drawing_bar = None

        self.set_edit_bar_visible(True)
        self.zoomable_image.set_zoom_enabled(True)

    def on_drawing_done_clicked(self, btn):
        if not getattr(self, "draw_overlay", None):
            self.on_drawing_cancel_clicked(btn)
            return

        strokes = getattr(self.draw_overlay, "strokes", None) or []
        if not strokes:
            self.on_drawing_cancel_clicked(btn)
            return

        dialog = Adw.MessageDialog.new(
            self.get_root(),
            "Save drawing?",
            "Do you want to overwrite the original file or save a new copy?"
        )

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("copy", "Save Copy")
        dialog.add_response("overwrite", "Overwrite")

        dialog.set_response_appearance("overwrite", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_response_appearance("copy", Adw.ResponseAppearance.SUGGESTED)

        dialog.set_default_response("copy")
        dialog.set_close_response("cancel")

        def on_response(dlg, response_id: str):
            if response_id == "cancel":
                dlg.close()
                return

            overwrite = (response_id == "overwrite")

            out_path = FuriOSMediaTools.compute_output_path(
                self.media_path,
                overwrite=overwrite,
                out_path=None,
                suffix="_drawn",
            )

            try:
                written_path = FuriOSMediaTools.rasterize_strokes_to_disk_cairo(
                    self.media_path,
                    strokes,
                    overwrite=overwrite,
                    out_path=out_path,
                    suffix="_drawn",
                )
                print("Drawing written to:", written_path)
                if self.picture:
                    self.main_box.remove(self.picture)

                self.media_path = written_path
                self.picture = self.setup_picture_to_edit(written_path)
                self.main_box.append(self.picture)

            except Exception as e:
                print("Failed to apply drawing:", e)

            self.on_drawing_cancel_clicked(btn)
            self.set_edit_bar_visible(True)
            self.zoomable_image.set_zoom_enabled(True)

            dlg.close()

        dialog.connect("response", on_response)
        dialog.present()

