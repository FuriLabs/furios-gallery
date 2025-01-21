# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, Gdk, GLib, GdkPixbuf
from .media_manager import get_album_database_paths, list_database_albums, get_album_media_paths
from .thumbnail_generator import ThumbnailGenerator

class Albums(Gtk.Box):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.thumbnail_generator = ThumbnailGenerator()
        self.setup_css()
        self.widget = self.create_widget()
        self.append(self.widget)

    def setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
        .rounded-image {
            border-radius: 20px;
        }
        .album-menu-box {
            background-color: #333;
            padding: 15px;
        }
        .missing-image {
            border-radius: 20px;
            background-color: #333;
        }
        """)
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def create_widget(self):

        albums_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        albums_box.set_hexpand(True)
        albums_box.set_vexpand(True)
        albums_box.set_halign(Gtk.Align.FILL)
        albums_box.set_valign(Gtk.Align.FILL)

        self.album_menu_box = self.album_menu_box()

        albums_box.append(self.album_menu_box)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.set_margin_top(20)
        scrolled_window.set_halign(Gtk.Align.FILL)
        scrolled_window.set_valign(Gtk.Align.FILL)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_column_spacing(0)
        self.flowbox.set_row_spacing(0)
        self.flowbox.set_max_children_per_line(3)
        self.flowbox.set_min_children_per_line(3)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flowbox.set_homogeneous(True)
        self.flowbox.set_hexpand(False)
        self.flowbox.set_vexpand(True)

        scrolled_window.set_child(self.flowbox)

        albums_box.append(scrolled_window)

        self.load_albums()

        self.flowbox.connect("selected-children-changed", self.on_child_selected)

        return albums_box

    def album_menu_box(self):
        album_menu_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        album_menu_box.set_hexpand(True)
        album_menu_box.set_halign(Gtk.Align.FILL)
        album_menu_box.set_css_classes(["album-menu-box"])

        create_album_button = Gtk.Button()
        create_album_button_icon = Gtk.Image.new_from_icon_name("folder-new-symbolic")
        create_album_button_icon.set_pixel_size(25)
        create_album_button.set_child(create_album_button_icon)
        create_album_button.connect("clicked", self.create_album)

        album_menu_box.append(create_album_button)

        delete_album_btn = Gtk.Button(icon_name="user-trash-symbolic")
        delete_album_btn.set_halign(Gtk.Align.END)
        delete_album_btn.connect("clicked", self.open_delete_popup)
        delete_album_btn.set_css_classes(["delete-btn"])
        delete_album_btn.set_margin_start(5)
        album_menu_box.append(delete_album_btn)

        return album_menu_box

    def open_delete_popup(self, btn):
        self.flowbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)

        self.selected_files_label = Gtk.Label(label="Select albums")
        self.selected_files_label.set_hexpand(True)
        self.selected_files_label.set_halign(Gtk.Align.FILL)
        self.album_menu_box.append(self.selected_files_label)

        self.cancel_btn = Gtk.Button(label="Cancel")
        self.cancel_btn.set_margin_end(15)
        self.cancel_btn.connect("clicked", self.on_cancel_btn)
        self.album_menu_box.append(self.cancel_btn)

        self.delete_confirm_btn = Gtk.Button(label="Delete")
        self.delete_confirm_btn.connect("clicked", self.on_delete_confirmation)
        self.album_menu_box.append(self.delete_confirm_btn)

    def on_cancel_btn(self, btn):
        self.flowbox.unselect_all()
        self.album_menu_box.remove(self.selected_files_label)
        self.album_menu_box.remove(self.cancel_btn)
        self.album_menu_box.remove(self.delete_confirm_btn)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)

    def on_delete_confirmation(self, btn):
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Delete Album?",
            body=f"This will permanently delete the selected albums from your system"
        )

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        dialog.connect("response", lambda dialog, response: self.on_delete_media(dialog, response))

        dialog.present()

    def on_delete_media(self, dialog, response):
        if response == "delete":
            selected_children = self.flowbox.get_selected_children()
            for child in selected_children:
                album_name = child.album_name

                try:
                    sql = "DELETE FROM albums WHERE album_name = ?"
                    cur = self.app.conn.cursor()
                    cur.execute(sql, (album_name,))
                    self.app.conn.commit()
                    print(f"Album deleted: {album_name}")
                except Exception as e:
                    print(f"Error deleting album '{album_name}': {e}")

                self.flowbox.remove(child)
        else:
            self.flowbox.unselect_all()
            self.grid_view_menu.remove(self.selected_files_label)
            self.grid_view_menu.remove(self.cancel_btn)
            self.grid_view_menu.remove(self.delete_confirm_btn)
            self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)

        dialog.destroy()

        self.album_menu_box.remove(self.selected_files_label)
        self.album_menu_box.remove(self.cancel_btn)
        self.album_menu_box.remove(self.delete_confirm_btn)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)


    def load_albums(self):
        albums = list_database_albums(self.app.conn)

        for album in albums:
            flowbox_child = Gtk.FlowBoxChild()

            flowbox_child.album_name = album

            album_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            album_box.set_spacing(8)
            album_box.set_halign(Gtk.Align.CENTER)
            album_box.set_valign(Gtk.Align.CENTER)

            album_paths = get_album_media_paths(self.app.conn, album)
            if album_paths:
                last_media_url = album_paths[-1]
                print(last_media_url)
                if last_media_url.endswith(('.mp4', '.mkv', '.avi')):
                    thumbnail_path = self.thumbnail_generator.generate_thumbnail(last_media_url)
                    if thumbnail_path:
                        image = GdkPixbuf.Pixbuf.new_from_file_at_scale(thumbnail_path, width=400, height=400, preserve_aspect_ratio=False)
                        picture = Gtk.Picture.new_for_pixbuf(image)
                        picture.set_css_classes(["rounded-image"])
                else:
                    image = GdkPixbuf.Pixbuf.new_from_file_at_scale(last_media_url, width=400, height=400, preserve_aspect_ratio=False)
                    picture = Gtk.Picture.new_for_pixbuf(image)
                    picture.set_css_classes(["rounded-image"])
            else:
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

            label = Gtk.Label(label=album)
            label.set_wrap(False)
            label.set_max_width_chars(20)

            album_box.append(picture)
            album_box.append(label)

            flowbox_child.set_child(album_box)
            self.flowbox.append(flowbox_child)

        self.show()

    def on_child_selected(self, flowbox):
        if self.flowbox.get_selection_mode() == Gtk.SelectionMode.SINGLE:
            selected_children = flowbox.get_selected_children()
            if selected_children:
                selected_child = selected_children[0]
                album_name = selected_child.album_name

                if album_name == "Videos":
                    self.app.open_album("Videos")
                elif album_name == "Pictures":
                    self.app.open_album("Pictures")
                else:
                    self.app.open_album(album_name)

    def create_album(self, button):
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
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

        dialog.connect("response", lambda dialog, response: self.on_album_create_response(dialog, response, entry))

        dialog.present()

    def on_album_create_response(self, dialog, response, entry):
        if response == "create":
            album_name = entry.get_text().strip()
            if album_name:
                try:
                    check_sql = "SELECT album_name FROM albums WHERE album_name = ?"
                    cur = self.app.conn.cursor()
                    cur.execute(check_sql, (album_name,))
                    if cur.fetchone() is None:
                        insert_sql = "INSERT INTO albums (album_name) VALUES (?)"
                        cur.execute(insert_sql, (album_name,))
                        self.app.conn.commit()
                        print(f"Successfully added album '{album_name}' to the database.")

                        flowbox_child = Gtk.FlowBoxChild()
                        flowbox_child.album_name = album_name
                        album_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                        album_box.set_spacing(8)
                        album_box.set_halign(Gtk.Align.CENTER)
                        album_box.set_valign(Gtk.Align.CENTER)

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
                        label = Gtk.Label(label=album_name)
                        label.set_wrap(False)
                        label.set_max_width_chars(20)
                        album_box.append(picture)
                        album_box.append(label)
                        flowbox_child.set_child(album_box)
                        self.flowbox.append(flowbox_child)

                    else:
                        print(f"Album '{album_name}' already exists in the database.")
                except Exception as e:
                    print(f"Failed to create album '{album_name}': {e}")
            else:
                print("Album name cannot be empty")
        dialog.destroy()