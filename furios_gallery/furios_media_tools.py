# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import cairo
import gi, os
import numpy as np

gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import GdkPixbuf, Gdk

class ColorSpaceStandards:
    #All coefficients follow ITU-R BT.601 (full-range, approximate).

    # RGB -> Y (luma) coefficients
    # Contribution of each RGB channel to perceived brightness
    Y_R = 0.2990 # Red contribution to luma
    Y_G = 0.5870 # Green contribution to luma (dominant for human vision)
    Y_B = 0.1140 # Blue contribution to luma

    # RGB -> Cb coefficients
    # Blue-difference chroma channel
    CB_R = -0.168736 # Red contribution to Cb
    CB_G = -0.331264 # Green contribution to Cb
    CB_B = 0.500000 # Blue contribution to Cb
    CB_OFFSET = 128.0 # Center chroma around mid-range for 8-bit storage

    # RGB -> Cr coefficients
    # Red-difference chroma channel
    CR_R = 0.500000 # Red contribution to Cr
    CR_G = -0.418688 # Green contribution to Cr
    CR_B = -0.081312 # Blue contribution to Cr
    CR_OFFSET = 128.0 # Center chroma around mid-range for 8-bit storage

    # YCbCr -> RGB coefficients
    # Inverse transform constants
    R_CR = 1.402000 # Cr contribution back to Red
    G_CB = 0.344136 # Cb contribution back to Green
    G_CR = 0.714136 # Cr contribution back to Green
    B_CB = 1.772000 # Cb contribution back to Blue

    @staticmethod
    def rgb_to_ycbcr(rgb: np.ndarray):
        x = rgb.astype(np.float32, copy=False)

        R = x[..., 0]
        G = x[..., 1]
        B = x[..., 2]

        Y = (
            ColorSpaceStandards.Y_R * R +
            ColorSpaceStandards.Y_G * G +
            ColorSpaceStandards.Y_B * B
        )

        Cb = (
            ColorSpaceStandards.CB_R * R +
            ColorSpaceStandards.CB_G * G +
            ColorSpaceStandards.CB_B * B +
            ColorSpaceStandards.CB_OFFSET
        )

        Cr = (
            ColorSpaceStandards.CR_R * R +
            ColorSpaceStandards.CR_G * G +
            ColorSpaceStandards.CR_B * B +
            ColorSpaceStandards.CR_OFFSET
        )

        return Y, Cb, Cr

    @staticmethod
    def ycbcr_to_rgb(Y: np.ndarray, Cb: np.ndarray, Cr: np.ndarray):
        R = Y + ColorSpaceStandards.R_CR * (Cr - ColorSpaceStandards.CR_OFFSET)
        G = (
            Y -
            ColorSpaceStandards.G_CB * (Cb - ColorSpaceStandards.CB_OFFSET) -
            ColorSpaceStandards.G_CR * (Cr - ColorSpaceStandards.CR_OFFSET)
        )
        B = Y + ColorSpaceStandards.B_CB * (Cb - ColorSpaceStandards.CB_OFFSET)

        return np.stack([R, G, B], axis=-1)

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

    @staticmethod
    def rasterize_strokes_to_disk_cairo(
        image_path: str,
        strokes: list[dict],
        *,
        overwrite: bool = False,
        out_path: str | None = None,
        suffix: str = "_drawn",
        jpeg_quality: int = 95,
    ) -> str:
        if not os.path.exists(image_path):
            raise FileNotFoundError(image_path)

        base = GdkPixbuf.Pixbuf.new_from_file(image_path)
        w, h = base.get_width(), base.get_height()

        # Cairo surface: ARGB32 (premultiplied), memory layout on little-endian is BGRA
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(surface)

        # Paint original image into surface
        Gdk.cairo_set_source_pixbuf(ctx, base, 0, 0)
        ctx.paint()

        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)

        for s in strokes or []:
            pts = s.get("pts") or []
            if len(pts) < 2:
                continue

            width = float(s.get("width_img", s.get("width", 4.0)))
            color = s.get("color")

            r = float(getattr(color, "red", 0.0))
            g = float(getattr(color, "green", 0.0))
            b = float(getattr(color, "blue", 0.0))
            a = float(getattr(color, "alpha", 1.0))

            ctx.set_source_rgba(r, g, b, a)
            ctx.set_line_width(max(0.5, width))

            ctx.new_path()
            x0, y0 = pts[0]
            ctx.move_to(float(x0), float(y0))
            for (x, y) in pts[1:]:
                ctx.line_to(float(x), float(y))
            ctx.stroke()

        out_path = FuriOSMediaTools.compute_output_path(
            image_path,
            overwrite=overwrite,
            out_path=out_path,
            suffix=suffix,
        )

        ext = os.path.splitext(out_path)[1].lower()

        # Convert cairo surface (BGRA premultiplied) -> RGBA straight alpha for Pixbuf
        stride = surface.get_stride()
        src = surface.get_data()
        rgba = bytearray(h * w * 4)

        for y in range(h):
            srow = y * stride
            drow = y * (w * 4)
            for x in range(w):
                si = srow + x * 4
                di = drow + x * 4

                b0 = src[si + 0]
                g0 = src[si + 1]
                r0 = src[si + 2]
                a0 = src[si + 3]

                if a0:
                    # Un-premultiply for "straight alpha"
                    r1 = (r0 * 255 + a0 // 2) // a0
                    g1 = (g0 * 255 + a0 // 2) // a0
                    b1 = (b0 * 255 + a0 // 2) // a0
                else:
                    r1 = g1 = b1 = 0

                rgba[di + 0] = r1
                rgba[di + 1] = g1
                rgba[di + 2] = b1
                rgba[di + 3] = a0

        pix = GdkPixbuf.Pixbuf.new_from_data(bytes(rgba), GdkPixbuf.Colorspace.RGB, True, 8, w, h, w * 4, None, None,).copy()

        if ext in (".jpg", ".jpeg"):
            fmt = "jpeg"
            keys = ["quality"]
            values = [str(int(jpeg_quality))]
        elif ext == ".png":
            fmt = "png"
            keys, values = [], []
        elif ext == ".webp":
            fmt = "webp"
            keys = ["quality"]
            values = [str(int(jpeg_quality))]
        elif ext in (".tif", ".tiff"):
            fmt = "tiff"
            keys, values = [], []
        elif ext == ".bmp":
            fmt = "bmp"
            keys, values = [], []
        else:
            fmt = "png"
            keys, values = [], []
            if not out_path.lower().endswith(".png"):
                out_path = os.path.splitext(out_path)[0] + ".png"

        if overwrite:
            tmp = out_path + ".tmp"
            pix.savev(tmp, fmt, keys, values)
            os.replace(tmp, out_path)
        else:
            pix.savev(out_path, fmt, keys, values)

        return out_path

    '''
    * Computational Imaging Functions *
    '''
    @staticmethod
    def apply_linear_contrast(rgb, contrast, reference_intensity):
        r = ((rgb[0] - reference_intensity) * contrast) + reference_intensity
        g = ((rgb[1] - reference_intensity) * contrast) + reference_intensity
        b = ((rgb[2] - reference_intensity) * contrast) + reference_intensity

        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))

        return (int(round(r)), int(round(g)), int(round(b)))

    @staticmethod
    def apply_luma_contrast(rgb, contrast, reference_intensity):
        if not isinstance(rgb, np.ndarray):
            raise TypeError("rgb must be a numpy ndarray")
        if rgb.ndim != 3 or rgb.shape[-1] != 3:
            raise ValueError(f"rgb must have shape (H, W, 3); got {rgb.shape}")

        # RGB -> YCbCr
        Y, Cb, Cr = ImageColorStandards.rgb_to_ycbcr(rgb)

        # Apply contrast ONLY to luma
        Y = contrast * (Y - reference_intensity) + reference_intensity

        # YCbCr -> RGB
        out = ImageColorStandards.ycbcr_to_rgb(Y, Cb, Cr)

        # Clip + convert for output
        return np.clip(out, 0.0, 255.0).astype(np.uint8)

    @staticmethod
    def apply_brightness(rgb, brightness):
        r = rgb[0] * brightness
        g = rgb[1] * brightness
        b = rgb[2] * brightness
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return (int(round(r)), int(round(g)), int(round(b)))

    @staticmethod
    def apply_luma_brightness(rgb_img, brightness):
        Y, Cb, Cr = ImageColorStandards.rgb_to_ycbcr(rgb_img)
        Y = Y * brightness
        out = ImageColorStandards.ycbcr_to_rgb(Y, Cb, Cr)
        return np.clip(out, 0.0, 255.0).astype(np.uint8)
