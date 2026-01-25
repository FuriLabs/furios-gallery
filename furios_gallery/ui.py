# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>
# Bardia Moshiri <bardia@furilabs.com>
# Jesús Higueras <jesus@furilabs.com>
# Luis Garcia <git@luigi311.com>

import gi
from typing import Callable
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Shumate', '1.0')
from gi.repository import Gtk, Adw, Gdk, GdkPixbuf, Pango, Shumate

def create_gallery_header() -> Adw.HeaderBar:
    """Create the main gallery header bar."""
    header = Adw.HeaderBar()
    header.set_title_widget(Adw.WindowTitle(title="Gallery"))
    return header

def create_album_button(callback: Callable) -> Gtk.Button:
    """Create album button for header."""
    button = Gtk.Button(icon_name="folder-new-symbolic")
    button.connect("clicked", callback)
    return button

def create_change_file_name_button(callback: Callable) -> Gtk.Button:
    """Create change file name button for header."""
    button = Gtk.Button(icon_name="text-editor-symbolic")
    button.connect("clicked", callback)
    button.set_visible(False)
    return button

def create_info_button(callback: Callable) -> Gtk.Button:
    """Create info button for header."""
    button = Gtk.Button(icon_name="help-about-symbolic")
    button.connect("clicked", callback)
    button.set_visible(False)
    return button

def create_media_options_button(callback: Callable) -> Gtk.Button:
    """Create media options button for header."""
    button = Gtk.Button(icon_name="view-more-symbolic")
    button.connect("clicked", callback)
    button.set_visible(False)
    return button

def create_delete_media_button(callback: Callable) -> Gtk.Button:
    """Create delete media button for header."""
    button = Gtk.Button(icon_name="user-trash-symbolic")
    button.connect("clicked", callback)
    button.add_css_class("delete-btn")
    return button

def create_return_button(callback: Callable) -> Gtk.Button:
    """Create return button for header."""
    button = Gtk.Button(icon_name="go-previous-symbolic")
    button.connect("clicked", callback)
    button.set_visible(False)
    return button

def create_albums_content_box() -> Gtk.Box:
    """Create main content box for albums view."""
    content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    content_box.set_hexpand(True)
    content_box.set_vexpand(True)
    return content_box

def create_albums_scrolled_window() -> Gtk.ScrolledWindow:
    """Create scrolled window for albums."""
    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled_window.set_hexpand(True)
    scrolled_window.set_vexpand(True)
    return scrolled_window

def create_albums_flowbox(selection_callback: Callable, update_callback: Callable = None) -> Gtk.FlowBox:
    """Create flowbox for albums."""
    flowbox = Gtk.FlowBox()
    flowbox.set_valign(Gtk.Align.START)
    flowbox.set_column_spacing(10)
    flowbox.set_row_spacing(10)
    flowbox.set_max_children_per_line(3)
    flowbox.set_min_children_per_line(3)
    flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    flowbox.set_homogeneous(True)
    flowbox.connect("selected-children-changed", selection_callback)
    # Connect the update callback if provided
    if update_callback:
        flowbox.connect("selected-children-changed", update_callback)
    return flowbox

def create_rename_dialog(parent, initial_name: str):
    entry = Gtk.Entry()
    entry.set_hexpand(True)
    entry.set_text(initial_name)
    entry.set_activates_default(True)

    hint = Gtk.Label(label="Only the file name will change, not the extension.")
    hint.set_halign(Gtk.Align.START)
    hint.set_wrap(True)
    hint.add_css_class("dim-label")

    error_label = Gtk.Label()
    error_label.set_halign(Gtk.Align.START)
    error_label.set_wrap(True)
    error_label.set_visible(False)
    error_label.add_css_class("error")

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    content.set_margin_top(12)
    content.set_margin_bottom(12)
    content.set_margin_start(12)
    content.set_margin_end(12)
    content.append(entry)
    content.append(hint)
    content.append(error_label)

    cancel_btn = Gtk.Button(label="Cancel")
    rename_btn = Gtk.Button(label="Rename")
    rename_btn.add_css_class("suggested-action")

    entry.connect("activate", lambda _e: rename_btn.emit("clicked"))

    header = Adw.HeaderBar()
    header.pack_start(cancel_btn)
    header.pack_end(rename_btn)

    toolbar = Adw.ToolbarView()
    toolbar.add_top_bar(header)
    toolbar.set_content(content)

    dlg = Adw.Dialog()
    dlg.set_title("Rename file")
    dlg.set_child(toolbar)

    return dlg, entry, error_label, rename_btn, cancel_btn

def create_album_item(album_name: str, thumbnail_path: str = None) -> Gtk.FlowBoxChild:
    """Create an album item for the flowbox."""
    flowbox_child = Gtk.FlowBoxChild()
    flowbox_child.album_name = album_name

    album_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    album_box.set_spacing(8)
    album_box.set_halign(Gtk.Align.CENTER)
    album_box.set_valign(Gtk.Align.CENTER)

    if thumbnail_path:
        image = GdkPixbuf.Pixbuf.new_from_file_at_scale(thumbnail_path, width=400, height=400, preserve_aspect_ratio=False)
        picture = Gtk.Picture.new_for_pixbuf(image)
        picture.set_css_classes(["rounded-image"])
    else:
        # Default missing album image
        picture = Gtk.Box()
        picture.set_css_classes(["missing-image"])

        picture_content = Gtk.Image.new_from_icon_name("folder-symbolic")
        picture_content.set_pixel_size(70)

        icon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        icon_box.set_hexpand(True)
        icon_box.set_vexpand(True)
        icon_box.set_halign(Gtk.Align.FILL)
        icon_box.set_valign(Gtk.Align.FILL)
        icon_box.append(picture_content)

        picture.append(icon_box)

    # Album name label
    label = Gtk.Label(label=album_name)
    label.set_wrap(False)
    label.set_ellipsize(Pango.EllipsizeMode.END)

    album_box.append(picture)
    album_box.append(label)

    flowbox_child.set_child(album_box)
    return flowbox_child

def setup_albums_css():
    """Setup CSS for albums view."""
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(b"""
    .rounded-image {
        border-radius: 20px;
    }
    .missing-image {
        border-radius: 20px;
        background-color: #333;
    }
    """)
    display = Gdk.Display.get_default()
    Gtk.StyleContext.add_provider_for_display(display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

def create_grid_view_main_box() -> Gtk.Box:
    """Create main box for grid view."""
    main_grid_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    main_grid_box.set_hexpand(True)
    main_grid_box.set_vexpand(True)
    main_grid_box.set_halign(Gtk.Align.FILL)
    main_grid_box.set_valign(Gtk.Align.FILL)
    return main_grid_box

def create_grid_view_placeholder() -> Gtk.Label:
    """Create placeholder for grid view loading."""
    placeholder = Gtk.Label(label="Loading...")
    return placeholder

def create_grid_view_scrolled_window() -> Gtk.ScrolledWindow:
    """Create scrolled window for grid view."""
    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled_window.set_hexpand(True)
    scrolled_window.set_vexpand(True)
    return scrolled_window

def create_grid_view_flowbox(selection_callback: Callable, update_callback: Callable) -> Gtk.FlowBox:
    """Create flowbox for grid view."""
    flowbox = Gtk.FlowBox()
    flowbox.set_valign(Gtk.Align.START)
    flowbox.set_column_spacing(0)
    flowbox.set_row_spacing(0)
    flowbox.set_max_children_per_line(5)
    flowbox.set_min_children_per_line(5)
    flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    flowbox.set_sort_func(lambda child1, child2: child2.media_index - child1.media_index)
    flowbox.set_homogeneous(True)
    flowbox.connect("selected-children-changed", selection_callback)
    flowbox.connect("selected-children-changed", update_callback)
    return flowbox

def setup_grid_view_css():
    """Setup CSS for grid view."""
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(b"""
    .delete-btn {
        padding: 5px;
    }
    """)
    display = Gdk.Display.get_default()
    Gtk.StyleContext.add_provider_for_display(display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

def create_edit_view_main_box() -> Gtk.Box:
    """Create main content box for edit view."""
    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    main_box.set_halign(Gtk.Align.FILL)
    main_box.set_valign(Gtk.Align.FILL)
    main_box.set_hexpand(True)
    main_box.set_vexpand(True)
    return main_box

def create_edit_view_overlay() -> Gtk.Overlay:
    """Create overlay for edit view."""
    overlay = Gtk.Overlay()
    overlay.set_halign(Gtk.Align.FILL)
    overlay.set_valign(Gtk.Align.FILL)
    overlay.set_hexpand(True)
    overlay.set_vexpand(True)
    return overlay

def create_media_view_main_box() -> Gtk.Box:
    """Create main content box for media view."""
    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    main_box.set_halign(Gtk.Align.FILL)
    main_box.set_valign(Gtk.Align.FILL)
    main_box.set_hexpand(True)
    main_box.set_vexpand(True)
    return main_box

def create_media_view_overlay() -> Gtk.Overlay:
    """Create overlay for media view."""
    overlay = Gtk.Overlay()
    overlay.set_halign(Gtk.Align.FILL)
    overlay.set_valign(Gtk.Align.FILL)
    overlay.set_hexpand(True)
    overlay.set_vexpand(True)
    return overlay

def create_media_view_carousel(page_changed_callback: Callable) -> Adw.Carousel:
    """Create carousel for media view."""
    carousel = Adw.Carousel()
    carousel.set_spacing(20)
    carousel.set_valign(Gtk.Align.FILL)
    carousel.set_halign(Gtk.Align.FILL)
    carousel.set_vexpand(True)
    carousel.set_hexpand(True)
    carousel.connect("page-changed", page_changed_callback)
    return carousel

def create_media_navigation_buttons(left_callback: Callable, right_callback: Callable) -> Gtk.Box:
    """Create navigation buttons for media view."""
    buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    buttons_box.set_halign(Gtk.Align.FILL)
    buttons_box.set_valign(Gtk.Align.CENTER)
    buttons_box.set_hexpand(True)
    buttons_box.set_vexpand(True)

    left_button = Gtk.Button(icon_name="go-previous-symbolic")
    left_button.connect('clicked', left_callback)
    left_button.set_hexpand(False)
    buttons_box.append(left_button)

    spacer = Gtk.Box()
    spacer.set_halign(Gtk.Align.FILL)
    spacer.set_hexpand(True)
    buttons_box.append(spacer)

    right_button = Gtk.Button(icon_name="go-next-symbolic")
    right_button.connect('clicked', right_callback)
    right_button.set_hexpand(False)
    buttons_box.append(right_button)

    return buttons_box

def create_media_options_dialog(parent) -> Adw.MessageDialog:
    """Create media options dialog."""
    dialog = Adw.MessageDialog(
        transient_for=parent,
        modal=True,
        heading="Media Options"
    )
    return dialog

def create_media_options_content() -> Gtk.Box:
    """Create content for media options dialog."""
    media_options = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    media_options.set_margin_top(10)
    media_options.set_margin_bottom(10)
    media_options.set_margin_start(10)
    media_options.set_margin_end(10)
    return media_options

def create_option_button(label: str, callback: Callable, *args) -> Gtk.Button:
    """Create option button for dialogs."""
    button = Gtk.Button(label=label)
    button.set_hexpand(True)
    button.set_halign(Gtk.Align.FILL)
    button.connect("clicked", callback, *args)
    return button

def create_album_selection_dialog(parent, heading: str, body: str) -> Adw.MessageDialog:
    """Create album selection dialog."""
    dialog = Adw.MessageDialog(
        transient_for=parent,
        heading=heading,
        body=body,
    )
    return dialog

def create_album_selection_content() -> tuple[Gtk.ScrolledWindow, Gtk.FlowBox]:
    """Create content for album selection dialog."""
    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.set_min_content_height(200)
    scrolled_window.set_min_content_width(300)

    flowbox = Gtk.FlowBox()
    flowbox.set_valign(Gtk.Align.START)
    flowbox.set_max_children_per_line(3)
    flowbox.set_selection_mode(Gtk.SelectionMode.NONE)

    scrolled_window.set_child(flowbox)
    return scrolled_window, flowbox

def create_delete_confirmation_dialog(parent, heading: str, body: str) -> Adw.MessageDialog:
    """Create delete confirmation dialog."""
    dialog = Adw.MessageDialog(
        transient_for=parent,
        heading=heading,
        body=body
    )
    dialog.add_response("cancel", "Cancel")
    dialog.add_response("delete", "Delete")
    dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
    return dialog

def create_album_create_dialog(parent) -> tuple[Adw.MessageDialog, Gtk.Entry]:
    """Create album creation dialog."""
    dialog = Adw.MessageDialog(
        transient_for=parent,
        heading="Create New Album",
        body="Enter the name of your new album:",
    )

    entry = Gtk.Entry()
    entry.set_placeholder_text("Album Name")
    entry.set_margin_top(10)
    entry.set_margin_bottom(10)
    dialog.set_extra_child(entry)

    dialog.add_response("cancel", "Cancel")
    dialog.add_response("create", "Create")
    dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)

    return dialog, entry

def create_selection_header_bar(label_text: str, cancel_callback: Callable, delete_callback: Callable) -> tuple[Adw.HeaderBar, Gtk.Label]:
    """Create selection header bar."""
    selection_bar = Adw.HeaderBar()

    # Selection count label
    selected_files_label = Gtk.Label(label=label_text)
    selection_bar.set_title_widget(selected_files_label)

    # Cancel button
    cancel_btn = Gtk.Button(label="Cancel")
    cancel_btn.connect("clicked", cancel_callback)
    selection_bar.pack_start(cancel_btn)

    # Delete confirmation button
    delete_confirm_btn = Gtk.Button(label="Delete")
    delete_confirm_btn.add_css_class("destructive-action")
    delete_confirm_btn.connect("clicked", delete_callback)
    selection_bar.pack_end(delete_confirm_btn)

    return selection_bar, selected_files_label

def create_properties_content() -> Gtk.Box:
    """Create main content for properties view."""
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
    content.set_margin_top(24)
    content.set_margin_bottom(24)
    content.set_margin_start(24)
    content.set_margin_end(24)
    return content

def create_properties_scrolled_window() -> Gtk.ScrolledWindow:
    """Create scrolled window for properties."""
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_propagate_natural_height(True)
    scrolled.set_vexpand(True)
    return scrolled

def create_properties_groups_box() -> Gtk.Box:
    """Create groups box for properties."""
    groups_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    return groups_box

def create_file_info_group(folder_callback: Callable) -> tuple[Adw.PreferencesGroup, Adw.ActionRow, Adw.ActionRow]:
    """Create file information group."""
    file_group = Adw.PreferencesGroup(title="File Information")

    # Folder row
    folder_row = Adw.ActionRow(title="Folder")
    folder_button = Gtk.Button(icon_name="folder-open-symbolic")
    folder_button.add_css_class("flat")
    folder_button.connect("clicked", folder_callback)
    folder_row.add_suffix(folder_button)
    file_group.add(folder_row)

    # Path row
    path_row = Adw.ActionRow(title="Path")
    file_group.add(path_row)

    return file_group, folder_row, path_row

def create_media_info_group() -> tuple[Adw.PreferencesGroup, Adw.ActionRow, Adw.ActionRow]:
    """Create media information group."""
    media_group = Adw.PreferencesGroup(title="Media Information")

    format_row = Adw.ActionRow(title="Format")
    filesize_row = Adw.ActionRow(title="File Size")

    for row in [format_row, filesize_row]:
        media_group.add(row)

    return media_group, format_row, filesize_row

def create_dates_group() -> tuple[Adw.PreferencesGroup, Adw.ActionRow, Adw.ActionRow]:
    """Create dates group."""
    dates_group = Adw.PreferencesGroup(title="Dates")

    created_row = Adw.ActionRow(title="Created")
    modified_row = Adw.ActionRow(title="Modified")

    for row in [created_row, modified_row]:
        dates_group.add(row)

    return dates_group, created_row, modified_row

def create_camera_info_group() -> Adw.PreferencesGroup:
    """Create camera information group."""
    camera_group = Adw.PreferencesGroup(title="Camera Information")
    return camera_group

def create_map_group(lat: float, lon: float, map_callback: Callable) -> Adw.PreferencesGroup:
    """Create map group for GPS location."""
    map_group = Adw.PreferencesGroup(title="Location")

    # Create a vertical box to stack the map and the button
    map_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    map_container.set_vexpand(True)
    map_container.set_hexpand(True)

    # Create map widget
    map_widget = Shumate.SimpleMap()
    map_widget.set_vexpand(True)
    map_widget.set_hexpand(True)

    # Set up the map source
    registry = Shumate.MapSourceRegistry.new_with_defaults()
    map_source = registry.get_by_id(Shumate.MAP_SOURCE_OSM_MAPNIK)
    viewport = map_widget.get_viewport()
    map_widget.set_map_source(map_source)

    # Reference map source used by MarkerLayer
    viewport.set_reference_map_source(map_source)

    # Set up marker with visible icon
    marker_layer = Shumate.MarkerLayer(viewport=viewport)
    marker = Shumate.Marker()
    marker.set_location(lat, lon)

    # Create a visible marker icon
    marker_icon = Gtk.Image()
    marker_icon.set_from_icon_name("mark-location-symbolic")
    marker_icon.add_css_class("map-marker")
    marker_icon.set_pixel_size(48)
    marker.set_child(marker_icon)

    marker_layer.add_marker(marker)
    map_widget.get_map().add_layer(marker_layer)

    map_widget.get_map().go_to(lat, lon)
    viewport.set_zoom_level(19)

    # Add the map widget to the container
    map_container.append(map_widget)

    # Create the "Open Map" button
    open_map_button = Gtk.Button(label="Open Map")
    open_map_button.add_css_class("flat")
    open_map_button.connect("clicked", lambda btn: map_callback(lat, lon))

    # Add the button to the container (below the map)
    map_container.append(open_map_button)

    # Add the container to the map group
    map_group.add(map_container)

    return map_group

def create_video_player_css():
    """Setup CSS for video player."""
    css_provider = Gtk.CssProvider()
    css_provider.load_from_data(b"""
    .control-box {
        background-color: rgba(0, 0, 0, 0.7); /* Black with 70% opacity */
        border-radius: 10px;
        padding: 10px;
    }
    .control-box-button, .control-box-label {
        color: white; /* Text color */
        background-color: transparent; /* Transparent background */
        border: none; /* No border */
    }
    """)
    display = Gdk.Display.get_default()
    Gtk.StyleContext.add_provider_for_display(display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

def create_video_controls() -> tuple[Gtk.Box, Gtk.Button, Gtk.Image, Gtk.Label, Gtk.Button, Gtk.Image, Gtk.Scale]:
    """Create video player controls."""
    control_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    control_box.set_hexpand(True)
    control_box.set_halign(Gtk.Align.FILL)
    control_box.add_css_class("control-box")

    play_duration_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    play_duration_box.set_hexpand(True)
    play_duration_box.set_halign(Gtk.Align.FILL)
    control_box.append(play_duration_box)

    play_pause_button = Gtk.Button()
    play_pause_button.add_css_class("control-box-button")
    play_pause_image = Gtk.Image.new_from_icon_name("media-playback-start-symbolic")
    play_pause_image.set_pixel_size(25)
    play_pause_button.set_child(play_pause_image)
    play_duration_box.append(play_pause_button)

    duration_label = Gtk.Label(label="00:00/00:00")
    duration_label.add_css_class("control-box-label")
    play_duration_box.append(duration_label)

    spacer = Gtk.Box()
    spacer.set_size_request(40, 50)
    spacer.set_hexpand(True)
    play_duration_box.append(spacer)

    mute_button = Gtk.Button()
    mute_button.add_css_class("control-box-button")
    mute_image = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic")
    mute_image.set_pixel_size(25)
    mute_button.set_child(mute_image)
    mute_button.set_halign(Gtk.Align.END)
    play_duration_box.append(mute_button)

    seeker = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
    seeker.set_draw_value(False)
    seeker.set_hexpand(True)
    control_box.append(seeker)

    return control_box, play_pause_button, play_pause_image, duration_label, mute_button, mute_image, seeker

def create_video_overlay_and_button() -> tuple[Gtk.Overlay, Gtk.Button]:
    """Create video overlay and click button."""
    overlay = Gtk.Overlay()

    video_click_button = Gtk.Button()
    video_click_button.set_opacity(0)
    video_click_button.set_can_focus(False)

    return overlay, video_click_button

def create_main_window_layout() -> tuple[Adw.ToastOverlay, Adw.ToolbarView, Adw.BottomSheet, Adw.NavigationView]:
    """Create the main window layout structure."""
    toast_overlay = Adw.ToastOverlay()
    toolbar_view = Adw.ToolbarView()
    bottom_sheet = Adw.BottomSheet()
    bottom_sheet.set_modal(True)
    bottom_sheet.set_can_open(True)

    navigation_view = Adw.NavigationView()

    bottom_sheet.set_content(navigation_view)
    toolbar_view.set_content(bottom_sheet)
    toast_overlay.set_child(toolbar_view)

    return toast_overlay, toolbar_view, bottom_sheet, navigation_view

def create_map_page(lat: float, lon: float) -> Adw.NavigationPage:
    """Create a navigation page for the map."""
    map_page = Adw.NavigationPage()
    map_page.set_title("Location")

    # Create map widget
    map_widget = Shumate.SimpleMap()
    map_widget.set_vexpand(True)
    map_widget.set_hexpand(True)

    # Set up the map source
    registry = Shumate.MapSourceRegistry.new_with_defaults()
    map_source = registry.get_by_id(Shumate.MAP_SOURCE_OSM_MAPNIK)
    viewport = map_widget.get_viewport()
    map_widget.set_map_source(map_source)

    # Reference map source used by MarkerLayer
    viewport.set_reference_map_source(map_source)

    # Set up marker with visible icon
    marker_layer = Shumate.MarkerLayer(viewport=viewport)
    marker = Shumate.Marker()
    marker.set_location(lat, lon)

    # Create a visible marker icon
    marker_icon = Gtk.Image()
    marker_icon.set_from_icon_name("mark-location-symbolic")
    marker_icon.add_css_class("map-marker")
    marker_icon.set_pixel_size(48)
    marker.set_child(marker_icon)

    marker_layer.add_marker(marker)
    map_widget.get_map().add_layer(marker_layer)
    map_widget.get_map().go_to(lat, lon)
    viewport.set_zoom_level(19)

    # Set map as the page content
    map_page.set_child(map_widget)

    return map_page

def clear_flowbox(flowbox: Gtk.FlowBox):
    """Clear all children from a flowbox."""
    child = flowbox.get_first_child()
    while child is not None:
        next_child = child.get_next_sibling()
        flowbox.remove(child)
        child = next_child
