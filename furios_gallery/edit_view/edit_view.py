# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import gi, os
import traceback
gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")

from .draw_overlay import DrawOverlay
from .crop_overlay import CropOverlay
from .filters_overlay import FiltersOverlay
from .furios_media_tools import FuriOSMediaTools
from ..image_viewer_widget import ImageViewerWidget
from gi.repository import Adw, Gtk, Gdk, GdkPixbuf, Graphene, GLib
from ..ui import (create_edit_view_main_box, create_edit_view_overlay)
from .ui import (create_main_bar_body, create_confirmation_dialog, create_icon_btn)

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
    def on_apply_btn_clicked(self, btn, title: str, body: str, operation, reload_after: bool):
        dialog = create_confirmation_dialog(self.get_root(), title, body)

        def on_response(dlg, response_id: str):
            if response_id == "cancel":
                dlg.close()
                return

            overwrite = (response_id == "overwrite")

            out_path = FuriOSMediaTools.compute_output_path(
                self.media_path,
                overwrite=overwrite,
                out_path=None,
                suffix="_copy",
            )

            try:
                maybe_written = operation(self.media_path, out_path, overwrite)

                if reload_after:
                    new_path = maybe_written or out_path

                    if self.picture:
                        self.main_box.remove(self.picture)

                    self.media_path = new_path
                    self.picture = self.setup_picture_to_edit(new_path)
                    self.main_box.append(self.picture)

            except Exception as e:
                print("Failed to apply drawing:", e)

            self.set_edit_bar_visible(True)
            self.zoomable_image.set_zoom_enabled(True)

            dlg.close()

        dialog.connect("response", on_response)
        dialog.present()
    
    def setup_editing_tools_bar(self):
        bar = create_main_bar_body(12, 12, 12, 12, 6, "horizontal")

        crop_btn = create_icon_btn("zoom-fit-best", "Crop", self.on_crop_clicked)
        filters_btn = create_icon_btn("color-select", "Filters", self.on_filters_clicked)
        drawing_btn = create_icon_btn("document-edit", "Drawing", self.on_drawing_clicked)

        for b in (crop_btn, filters_btn, drawing_btn):
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
    def on_crop_clicked(self, btn):
            if not self.texture or not self.picture:
                return

            # Return image to original size
            self.zoomable_image.reset_view_fit()

            # Disable zoom
            self.zoomable_image.set_zoom_enabled(not self.zoomable_image.zoom_enabled)

            # Hide the edit bar
            self.set_edit_bar_visible(False)

            self.crop_overlay = CropOverlay(self.picture, self.texture)
            self.overlay.add_overlay(self.crop_overlay)

            self.crop_overlay.on_cancel = lambda: self.on_crop_cancel_clicked(btn)
            self.crop_overlay.on_apply  = lambda selected: self.on_crop_apply_clicked(btn)

            self.overlay.add_overlay(self.crop_overlay.get_bar_widget())

    def on_crop_cancel_clicked(self, btn=None):
        crop = getattr(self, "crop_overlay", None)
        if crop:
            self.overlay.remove_overlay(crop)
            bar = crop.get_bar_widget()
            if bar:
                self.overlay.remove_overlay(bar)

            self.crop_overlay = None

        self.set_edit_bar_visible(True)
        self.zoomable_image.set_zoom_enabled(True)

    def on_crop_apply_clicked(self, btn=None):
        if not getattr(self, "crop_overlay", None):
            return

        x, y, w, h = self.crop_overlay.get_crop_in_image_pixels()

        def op(in_path: str, out_path: str, overwrite: bool):
            return FuriOSMediaTools.crop_image_to_disk(
                in_path, x, y, w, h,
                overwrite=overwrite,
                out_path=out_path,
                suffix="_cropped",
            )

        self.on_apply_btn_clicked(
            btn=btn,
            title="Save cropped image?",
            body="Do you want to overwrite the original file or save a new copy?",
            operation=op,
            reload_after=True,
        )

        self.on_crop_cancel_clicked(btn)

    '''
    * Filters Feature *
    '''
    def on_filters_clicked(self, btn):
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

    def on_filters_cancel_clicked(self, btn=None):
        if getattr(self, "filters_overlay", None):
            self.overlay.remove_overlay(self.filters_overlay.get_bar_widget())
            self.filters_overlay = None

        self.set_edit_bar_visible(True)
        self.zoomable_image.set_zoom_enabled(True)

    def on_filters_apply_clicked(self, btn=None):
        overlay = getattr(self, "filters_overlay", None)
        if not overlay:
            self.on_filters_cancel_clicked(btn)
            return

        css_class = getattr(overlay, "selected_filter", "filter-original")

        def op(in_path: str, out_path: str, overwrite: bool):
            return FuriOSMediaTools.bake_filter_to_file(in_path, out_path, css_class)

        self.on_apply_btn_clicked(
            btn=btn,
            title="Save filtered image?",
            body="Do you want to overwrite the original file or save a new copy?",
            operation=op,
            reload_after=True,
        )

        self.on_filters_cancel_clicked(btn)

    '''
    * Drawing Feature *
    '''
    def on_drawing_clicked(self, btn):
        if not self.texture or not self.picture:
            return

        self.zoomable_image.reset_view_fit()
        self.zoomable_image.set_zoom_enabled(False)
        self.set_edit_bar_visible(False)

        if getattr(self, "draw_overlay", None):
            self.overlay.remove_overlay(self.draw_overlay.get_bar_widget())
            self.draw_overlay = None

        self.draw_overlay = DrawOverlay(self.picture, self.texture, clamp_to_image=True)

        self.draw_overlay.on_cancel = lambda: self.on_drawing_cancel_clicked(btn)
        self.draw_overlay.on_apply  = lambda payload=None: self.on_drawing_apply_clicked(btn)

        self.overlay.add_overlay(self.draw_overlay)
        self.overlay.add_overlay(self.draw_overlay.get_bar_widget())
        self.draw_overlay.queue_draw()

    def on_drawing_cancel_clicked(self, _btn=None):
        draw = getattr(self, "draw_overlay", None)
        if draw:
            bar = draw.get_bar_widget()
            if bar:
                self.overlay.remove_overlay(bar)

            self.overlay.remove_overlay(draw)
            self.draw_overlay = None

        self.set_edit_bar_visible(True)
        self.zoomable_image.set_zoom_enabled(True)

    def on_drawing_apply_clicked(self, btn=None):
        draw = getattr(self, "draw_overlay", None)
        if not draw:
            self.on_drawing_cancel_clicked(btn)
            return

        strokes = getattr(draw, "strokes", None) or []
        if not strokes:
            self.on_drawing_cancel_clicked(btn)
            return

        def op(in_path: str, out_path: str, overwrite: bool):
            return FuriOSMediaTools.rasterize_strokes_to_disk_cairo(
                in_path,
                strokes,
                overwrite=overwrite,
                out_path=out_path,
                suffix="_drawn",
            )

        self.on_apply_btn_clicked(
            btn=btn,
            title="Save drawing?",
            body="Do you want to overwrite the original file or save a new copy?",
            operation=op,
            reload_after=True,
        )

        self.on_drawing_cancel_clicked(btn)

