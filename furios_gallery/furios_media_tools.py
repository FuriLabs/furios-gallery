# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import gi, os

gi.require_version("GdkPixbuf", "2.0")

from gi.repository import GdkPixbuf
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
            return True, new_path
        except OSError as e:
            return False, str(e)

    @staticmethod
    def crop_image_to_disk(
        image_path: str,
        x: int, y: int, w: int, h: int,
        *,
        overwrite: bool = False,
        out_path: str | None = None,
        suffix: str = "_cropped",
    ) -> str:
        if not os.path.exists(image_path):
            raise FileNotFoundError(image_path)

        pixbuf = GdkPixbuf.Pixbuf.new_from_file(image_path)
        img_w = pixbuf.get_width()
        img_h = pixbuf.get_height()

        # Clamp crop rect
        x = max(0, min(int(x), img_w - 1))
        y = max(0, min(int(y), img_h - 1))
        w = max(1, min(int(w), img_w - x))
        h = max(1, min(int(h), img_h - y))

        cropped = pixbuf.new_subpixbuf(x, y, w, h).copy()

        out_path = FuriOSMediaTools.compute_output_path(
            image_path,
            overwrite=overwrite,
            out_path=out_path,
            suffix=suffix,
        )

        ext = os.path.splitext(out_path)[1].lower()

        if ext in (".jpg", ".jpeg"):
            fmt = "jpeg"
            keys = ["quality"]
            values = ["95"]   # Lets use 95% quality fidelity for jpeg since we cant guarantee byte to byte cuz its jpeg.
        elif ext == ".png":
            fmt = "png"
            keys, values = [], []
        elif ext in (".tif", ".tiff"):
            fmt = "tiff"
            keys, values = [], []
        elif ext == ".bmp":
            fmt = "bmp"
            keys, values = [], []
        else:
            # fallback to PNG
            fmt = "png"
            keys, values = [], []
            if not out_path.lower().endswith(".png"):
                out_path = os.path.splitext(out_path)[0] + ".png"

        if overwrite:
            tmp = out_path + ".tmp"
            cropped.savev(tmp, fmt, keys, values)
            os.replace(tmp, out_path)
        else:
            cropped.savev(out_path, fmt, keys, values)

        return out_path

    @staticmethod
    def compute_output_path(
        image_path: str,
        *,
        overwrite: bool = False,
        out_path: str | None = None,
        suffix: str = "_cropped",
    ) -> str:
        if out_path:
            return out_path

        if overwrite:
            return image_path

        base_dir = os.path.dirname(image_path)
        name = os.path.basename(image_path)
        stem, ext = os.path.splitext(name)

        return os.path.join(base_dir, f"{stem}{suffix}{ext}")
