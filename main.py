#!/usr/bin/env python3

import gi

from gi.repository import GLib, Gio

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from furios_gallery import FuriosGalleryApp
from asyncio import run, sleep
from sys import exit

async def pump_gtk_events():
    main_context = GLib.MainContext.default()
    app = FuriosGalleryApp()
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