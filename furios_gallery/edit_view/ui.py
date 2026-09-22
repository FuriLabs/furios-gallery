# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import gi
from typing import Callable
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Shumate', '1.0')
from gi.repository import Gtk, Adw, Gdk, GdkPixbuf, Pango, Shumate

def create_main_bar_body(spacing, mstart, mend, mbottom, mtop, direction):
    if direction == "vertical":
        bar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
    elif direction == "horizontal":
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=spacing)

    bar.set_halign(Gtk.Align.FILL)
    bar.set_valign(Gtk.Align.END)
    bar.set_hexpand(True)
    bar.set_margin_start(mstart)
    bar.set_margin_end(mend)
    bar.set_margin_bottom(mbottom)
    bar.set_margin_top(mtop)

    bar.add_css_class("osd")
    bar.add_css_class("toolbar")

    return bar

def create_cancel_btn(callback):
    cancel = Gtk.Button(label="Cancel")
    cancel.set_hexpand(True)
    cancel.set_halign(Gtk.Align.FILL)
    cancel.connect("clicked", callback)

    return cancel

def create_confirmation_dialog(root_ctx, title, body):
    dialog = Adw.MessageDialog.new(root_ctx, title, body)

    dialog.add_response("cancel", "Cancel")
    dialog.add_response("copy", "Save Copy")
    dialog.add_response("overwrite", "Overwrite")
    dialog.set_response_appearance("overwrite", Adw.ResponseAppearance.DESTRUCTIVE)
    dialog.set_response_appearance("copy", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response("copy")
    dialog.set_close_response("cancel")

    return dialog

def create_icon_btn(icon_name: str,tooltip: str, handler):
    btn = Gtk.Button()
    btn.set_has_frame(False)
    btn.set_tooltip_text(tooltip)

    img = Gtk.Image.new_from_icon_name(icon_name)
    img.set_pixel_size(22)
    btn.set_child(img)

    btn.connect("clicked", handler)
    return btn

'''
* Crop Feature *
'''
def create_crop_btn(callback):
    crop = Gtk.Button(label="Crop")
    crop.set_hexpand(True)
    crop.set_halign(Gtk.Align.FILL)
    crop.add_css_class("suggested-action")
    crop.connect("clicked", callback)
    
    return crop

'''
* Filters Feature *
'''
def create_apply_btn(callback):
    crop = Gtk.Button(label="Apply")
    crop.set_hexpand(True)
    crop.set_halign(Gtk.Align.FILL)
    crop.add_css_class("suggested-action")
    crop.connect("clicked", callback)
    
    return crop


'''
* Image Transformations Feature *
'''
def make_slider_menu_button(icon_name: str, tooltip: str, title: str, value: float, lower: float, upper: float, step: float, digits: int, on_change) -> Gtk.MenuButton:
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

'''
* Drawing Feature *
'''
def apply_color(_btn, chooser, current_color, on_color_changed, dialog):
    rgba = chooser.get_rgba()
    current_color.red = rgba.red
    current_color.green = rgba.green
    current_color.blue = rgba.blue
    current_color.alpha = rgba.alpha
    on_color_changed(rgba)
    dialog.close()

def color_activated(_chooser, rgba, current_color, on_color_changed, dialog):
    current_color.red = rgba.red
    current_color.green = rgba.green
    current_color.blue = rgba.blue
    current_color.alpha = rgba.alpha
    on_color_changed(rgba)
    dialog.close()

def open_color_sheet(_btn, bar, current_color, on_color_changed):
    dialog = Adw.Dialog()
    dialog.set_title("Stroke color")
    dialog.set_presentation_mode(Adw.DialogPresentationMode.BOTTOM_SHEET)
    dialog.set_follows_content_size(False)

    root = bar.get_root()

    # Size sheet relative to current window
    if root is not None:
        root_height = root.get_allocated_height()
        root_width = root.get_allocated_width()

        if root_height > 0:
            dialog.set_content_height(int(root_height / 3))
        else:
            dialog.set_content_height(300)

        if root_width > 0:
            dialog.set_content_width(root_width)
        else:
            dialog.set_content_width(360)

    else:
        dialog.set_content_height(300)
        dialog.set_content_width(360)

    # Main content
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

    content.set_margin_top(12)
    content.set_margin_bottom(12)
    content.set_margin_start(12)
    content.set_margin_end(12)
    content.set_hexpand(True)
    content.set_vexpand(True)

    # Header
    header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

    title = Gtk.Label(label="Stroke color")
    title.set_halign(Gtk.Align.START)
    title.set_hexpand(True)

    done_color = Gtk.Button(label="Done")
    done_color.add_css_class("suggested-action")

    header.append(title)
    header.append(done_color)

    # Color chooser
    chooser = Gtk.ColorChooserWidget()
    chooser.set_rgba(current_color)
    chooser.set_vexpand(True)

    chooser_scroll = Gtk.ScrolledWindow()
    chooser_scroll.set_hexpand(True)
    chooser_scroll.set_vexpand(True)
    chooser_scroll.set_propagate_natural_width(False)
    chooser_scroll.set_propagate_natural_height(False)
    chooser_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
    chooser_scroll.set_child(chooser)

    done_color.connect("clicked", apply_color, chooser, current_color, on_color_changed, dialog)

    chooser.connect("color-activated", color_activated, current_color, on_color_changed, dialog)

    # Build sheet
    content.append(header)
    content.append(chooser_scroll)

    dialog.set_child(content)
    dialog.present(bar)

def on_size_value_changed(scale, on_size_changed):
    on_size_changed(scale.get_value())

def on_undo_pressed(_gesture, _n_press, _x, _y, on_undo):
    on_undo()

def create_drawing_bar(
    on_cancel,
    on_done,
    on_undo,
    on_color_changed,
    initial_rgba,
    on_size_changed,
    initial_size: float,
    size_range=(1.0, 100.0),
    spacing=0,
    mstart=5, mend=5, mbottom=12, mtop=6,
) -> Gtk.Widget:
    bar = create_main_bar_body(spacing, mstart, mend, mbottom, mtop, "horizontal")
    bar.set_can_target(True)

    # Cancel
    cancel = create_cancel_btn(on_cancel)

    # Color
    color_btn = Gtk.Button()
    color_btn.set_tooltip_text("Stroke color")
    color_btn.set_valign(Gtk.Align.CENTER)
    color_btn.set_has_frame(True)

    color_icon = Gtk.Image.new_from_icon_name("color-select")
    color_icon.set_pixel_size(18)
    color_btn.set_child(color_icon)

    current_color = initial_rgba.copy()

    color_btn.connect("clicked", open_color_sheet, bar, current_color, on_color_changed)

    # Size popover
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

    low, high = size_range

    adj = Gtk.Adjustment(value=float(initial_size), lower=float(low), upper=float(high), step_increment=1.0, page_increment=2.0)

    scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
    scale.set_draw_value(True)
    scale.set_digits(0)
    scale.set_valign(Gtk.Align.CENTER)
    scale.set_hexpand(True)
    scale.set_size_request(150, -1)

    scale.connect("value-changed", on_size_value_changed, on_size_changed)

    size_box.append(size_label)
    size_box.append(scale)
    size_pop.set_child(size_box)
    size_btn.set_popover(size_pop)

    # Undo
    undo_btn = Gtk.MenuButton()
    undo_btn.set_has_frame(True)
    undo_btn.set_valign(Gtk.Align.CENTER)
    undo_btn.set_tooltip_text("Undo last stroke")

    undo_icon = Gtk.Image.new_from_icon_name("edit-undo-symbolic")
    undo_icon.set_pixel_size(18)
    undo_btn.set_child(undo_icon)

    gesture = Gtk.GestureClick.new()
    gesture.connect("pressed", on_undo_pressed, on_undo)
    undo_btn.add_controller(gesture)

    # Done
    done = Gtk.Button(label="Done")
    done.set_hexpand(True)
    done.set_halign(Gtk.Align.FILL)
    done.add_css_class("suggested-action")
    done.connect("clicked", on_done)

    # Layout
    bar.append(cancel)
    bar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
    bar.append(color_btn)
    bar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
    bar.append(size_btn)
    bar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
    bar.append(undo_btn)
    bar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
    bar.append(done)

    return bar
