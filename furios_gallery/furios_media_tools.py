# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import os

class FuriOSMediaTools:
    @staticmethod
    def _basename_without_ext(path: str) -> str:
        base = os.path.basename(path)
        name, _ext = os.path.splitext(base)
        return name

    @staticmethod
    def change_file_name(src_path: str, new_base_name: str) -> tuple[bool, str]:
        if not src_path or not os.path.exists(src_path):
            return False, "Source file does not exist."

        new_base_name = new_base_name.strip()

        if not new_base_name:
            return False, "File name cannot be empty."
        if "/" in new_base_name or "\x00" in new_base_name:
            return False, "Invalid characters in file name."
        if new_base_name in (".", ".."):
            return False, "Invalid file name."

        directory = os.path.dirname(src_path)
        old_base, ext = os.path.splitext(os.path.basename(src_path))

        # Enforce: no extension change
        if "." in new_base_name:
            return False, "Do not include a file extension."

        new_path = os.path.join(directory, new_base_name + ext)

        if os.path.exists(new_path):
            return False, "A file with that name already exists."

        try:
            os.rename(src_path, new_path)
            #TBD: Update any media database, refresh header, refresh carousel and gridview.
            return True, new_path
        except OSError as e:
            return False, str(e)