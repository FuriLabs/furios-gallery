# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>
# Bardia Moshiri <bardia@furilabs.com>
# Jesús Higueras <jesus@furilabs.com>
# Luis Garcia <git@luigi311.com>

import gi
gi.require_version('Adw', '1')
from gi.repository import Adw

from furios_gallery.gallery_window import GalleryWindow

class GalleryApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='io.FuriOS.Gallery')
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = GalleryWindow(application=app)
        self.win.present()
