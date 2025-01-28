#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2025 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>
# Bardia Moshiri <bardia@furilabs.com>
# Jesús Higueras <jesus@furilabs.com>
# Luis Garcia <git@luigi311.com>

import gi

from gi.repository import GLib, Gio

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from furios_gallery import GalleryApp
from asyncio import run, sleep

async def pump_gtk_events():
    main_context = GLib.MainContext.default()
    app = GalleryApp()
    app.connect('shutdown', lambda _: exit(0))

    Gio.Application.set_default(app)
    app.register()

    app.activate()

    while True:
        while main_context.pending():
            main_context.iteration(False)
        await sleep(1 / 160)

if __name__ == '__main__':
    run(pump_gtk_events())
