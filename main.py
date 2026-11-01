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

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from furios_gallery import Gallery

if __name__ == '__main__':
    app = Gallery()
    app.run()
