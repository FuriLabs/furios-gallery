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

from .crop_overlay import CropOverlay
from .furios_media_tools import FuriOSMediaTools
from .image_viewer_widget import ImageViewerWidget
from gi.repository import Adw, Gtk, Gdk, GdkPixbuf, Graphene
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
            return

        def on_fine_tunes_clicked(btn):
            return

        def on_drawing_clicked(btn):
            return

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

        def _on_response(dlg, response_id: str):
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

        dialog.connect("response", _on_response)
        dialog.present()
