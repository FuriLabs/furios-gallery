# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

from gi.repository import Gtk
from furios_gallery.thumbnail_utils import ensure_cache_dir, generate_thumbnail

class ThumbnailGenerator:
    def __init__(self):
        ensure_cache_dir()

    def generate_thumbnail(self, media_path):
        thumbnail = generate_thumbnail(media_path)
        return thumbnail

    def update_ui_with_thumbnail(self, flowbox_child, thumbnail_path):
        thumbnail_picture = Gtk.Picture.new_for_filename(str(thumbnail_path))
        thumbnail_picture.set_content_fit(Gtk.ContentFit.COVER)
        flowbox_child.set_child(thumbnail_picture)
