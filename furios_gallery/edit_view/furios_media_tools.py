# SPDX-License-Identifier: GPL-2.0
# Copyright (C) 2026 Furi Labs
#
# Authors:
# Joaquin Philco <joaquin@furilabs.com>

import gi, os
import numpy as np

gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")

from PIL import Image, ImageDraw, ImageFilter
from gi.repository import GdkPixbuf
from .color_space_standards import ColorSpaceStandards

# ********************** #
# * FuriOS Media Tools * #
# ********************** #
def basename_without_ext(path: str) -> str:
    base = os.path.basename(path)
    name, _ext = os.path.splitext(base)
    return name

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

def crop_image_to_disk(image_path: str, x: int, y: int, w: int, h: int, overwrite: bool = False, out_path: str | None = None, suffix: str = "_cropped") -> str:
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

    out_path = compute_output_path(image_path, overwrite=overwrite, out_path=out_path, suffix=suffix)

    ext = os.path.splitext(out_path)[1].lower()

    if ext in (".jpg", ".jpeg"):
        fmt = "jpeg"
        keys = ["quality"]
        values = ["95"] # Lets use 95% quality fidelity for jpeg since we cant guarantee byte to byte cuz its jpeg.
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

def compute_output_path(image_path: str, overwrite: bool = False, out_path: str | None = None, suffix: str = "_cropped") -> str:
    if out_path:
        return out_path

    if overwrite:
        return image_path

    base_dir = os.path.dirname(image_path)
    name = os.path.basename(image_path)
    stem, ext = os.path.splitext(name)

    return os.path.join(base_dir, f"{stem}{suffix}{ext}")

def rasterize_strokes_to_disk(image_path: str, strokes: list[dict], overwrite: bool = False, out_path: str | None = None, suffix: str = "_drawn", jpeg_quality: int = 95) -> str:
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)
    out_path = compute_output_path(image_path, overwrite=overwrite, out_path=out_path, suffix=suffix)
    ext = os.path.splitext(out_path)[1].lower()
    with Image.open(image_path) as src:
        has_alpha = src.mode in ("RGBA", "LA") or "transparency" in src.info
        image = src.convert("RGBA" if has_alpha else "RGB")
        draw = ImageDraw.Draw(image, "RGBA" if has_alpha else None)
        for stroke in strokes or []:
            pts = stroke.get("pts") or []
            if len(pts) < 2:
                continue
            width = max(1, round(float(stroke.get("width_img", stroke.get("width", 4.0)))))
            color = stroke.get("color")
            r = round(float(getattr(color, "red", 0.0)) * 255)
            g = round(float(getattr(color, "green", 0.0)) * 255)
            b = round(float(getattr(color, "blue", 0.0)) * 255)
            a = round(float(getattr(color, "alpha", 1.0)) * 255)
            points = [(round(x), round(y)) for x, y in pts]
            fill = (r, g, b, a) if has_alpha else (r, g, b)
            draw.line(points, fill=fill, width=width, joint="curve")
            radius = width / 2
            for px, py in (points[0], points[-1]):
                draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=fill)
        if ext in (".jpg", ".jpeg"):
            if image.mode != "RGB":
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.getchannel("A"))
                image = background
            save_format = "JPEG"
            save_kwargs = {"quality": jpeg_quality, "subsampling": 0}
        elif ext == ".png":
            save_format = "PNG"
            save_kwargs = {}
        elif ext == ".webp":
            save_format = "WEBP"
            save_kwargs = {"quality": jpeg_quality}
        elif ext in (".tif", ".tiff"):
            save_format = "TIFF"
            save_kwargs = {}
        elif ext == ".bmp":
            save_format = "BMP"
            save_kwargs = {}
        else:
            out_path = os.path.splitext(out_path)[0] + ".png"
            save_format = "PNG"
            save_kwargs = {}
        if overwrite:
            tmp = out_path + ".tmp"
            image.save(tmp, format=save_format, **save_kwargs)
            os.replace(tmp, out_path)
        else:
            image.save(out_path, format=save_format, **save_kwargs)
    return out_path

def _get_unique_path(out_path: str) -> str:
    if not os.path.exists(out_path):
        return out_path

    directory = os.path.dirname(out_path)
    filename = os.path.basename(out_path)

    stem, ext = os.path.splitext(filename)

    counter = 2

    while True:
        candidate = os.path.join(directory, f"{stem}_{counter}{ext}")

        if not os.path.exists(candidate):
            return candidate

        counter += 1

def save_rgb_numpy(rgb: np.ndarray, out_path: str, overwrite: bool = False) -> str:
    if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"Expected uint8 (H,W,3), got {rgb.dtype} {rgb.shape}")

    if not overwrite:
        out_path = _get_unique_path(out_path)

    ext = os.path.splitext(out_path)[1].lower()
    im = Image.fromarray(rgb, mode="RGB")

    if ext in [".jpg", ".jpeg"]:
        im.save(out_path, format="JPEG", quality=95, subsampling=0)
    elif ext == ".png":
        im.save(out_path, format="PNG")
    elif ext == ".webp":
        im.save(out_path, format="WEBP", quality=95, method=6)
    else:
        im.save(out_path, format="PNG")

    return out_path

def apply_custom_color_filters(rgb: np.ndarray, brightness: float, contrast: float, saturation: float, sepia: float) -> np.ndarray:
    transforms = []
    if brightness != 1.0:
        transforms.append(brightness_transform(brightness))
    if contrast != 1.0:
        transforms.append(contrast_transform(contrast, 128.0))
    if saturation != 1.0:
        transforms.append(saturation_transform(saturation))
    if sepia != 0.0:
        transforms.append(sepia_transform(sepia))
    if not transforms:
        return rgb
    M, b = compose_transforms(*transforms)
    return apply_affine_rgb(rgb, M, b)

def apply_custom_filters(in_path: str, out_path: str, brightness: float | None, contrast: float | None, saturation: float | None, sepia: float | None, blur: float | None):
    with Image.open(in_path) as im:
        rgb = np.array(im.convert("RGB"), dtype=np.uint8)
    out_rgb = apply_custom_color_filters(rgb, brightness, contrast, saturation, sepia)
    if blur != 0.0:
        out_rgb = apply_gaussian_blur(out_rgb, min(blur * 2.2, 10.0))
    save_rgb_numpy(out_rgb, out_path)

def bake_filter_to_file(in_path: str, out_path: str, css_class: str, overwrite: bool = False) -> str:
    with Image.open(in_path) as im:
        rgb = np.array(im.convert("RGB"), dtype=np.uint8)

    out_rgb = apply_filter_to_rgb(rgb, css_class)
    return save_rgb_numpy(out_rgb, out_path, overwrite=overwrite)

# *********************************** #
# * Computational Imaging Functions * #
# *********************************** #
IDENTITY = np.eye(3, dtype=np.float32)
ZERO = np.zeros(3, dtype=np.float32)
LUMA = np.array([ColorSpaceStandards.Y_R, ColorSpaceStandards.Y_G, ColorSpaceStandards.Y_B], dtype=np.float32)

def contrast_transform(contrast: float, reference_intensity: float = 128.0):
    c = float(contrast)
    M = IDENTITY + (c - 1.0) * np.outer(np.ones(3, dtype=np.float32), LUMA)
    b = (1.0 - c) * float(reference_intensity) * np.ones(3, dtype=np.float32)
    return M, b

def brightness_transform(amount: float):
    return IDENTITY * float(amount), ZERO.copy()

def apply_luma_brightness(rgb_img, brightness):
    Y, Cb, Cr = ColorSpaceStandards.rgb_to_ycbcr(rgb_img)
    Y = Y * brightness
    out = ColorSpaceStandards.ycbcr_to_rgb(Y, Cb, Cr)
    return np.clip(out, 0.0, 255.0).astype(np.uint8)

def grayscale_transform():
    return np.tile(LUMA, (3, 1)), ZERO.copy()

SOFT_BLUR_FRACTION = 0.005
SOFT_BRIGHTNESS = 1.02

def soft_blur_sigma(image_width: int, image_height: int) -> float:
    return SOFT_BLUR_FRACTION * max(image_width, image_height)

def soft_preview_sigma(image_width: int, image_height: int, display_width: int, display_height: int) -> float:
    if image_width <= 0 or image_height <= 0 or display_width <= 0 or display_height <= 0:
        return 0.0
    scale = min(display_width / image_width, display_height / image_height)
    return soft_blur_sigma(image_width, image_height) * scale

def apply_gaussian_blur(img: np.ndarray, sigma: float) -> np.ndarray:
    if not isinstance(img, np.ndarray):
        raise TypeError("img must be a numpy ndarray")

    if sigma <= 0:
        return img.copy()
    pil_img = Image.fromarray(img, mode="RGB")
    blurred = pil_img.filter(ImageFilter.GaussianBlur(radius=float(sigma)))
    return np.asarray(blurred, dtype=np.uint8).copy()

def invert_transform(amount: float = 1.0):
    a = float(amount)
    M = (1.0 - 2.0 * a) * IDENTITY
    b = 255.0 * a * np.ones(3, dtype=np.float32)
    return M, b

def sepia_transform(amount: float):
    a = float(amount)
    M = (1.0 - a) * IDENTITY + a * ColorSpaceStandards.SEPIA_MATRIX
    return M, ZERO.copy()

def saturation_transform(amount: float):
    s = float(amount)
    inv = 1.0 - s
    lr, lg, lb = LUMA
    M = np.array([
        [inv * lr + s, inv * lg, inv * lb],
        [inv * lr, inv * lg + s, inv * lb],
        [inv * lr, inv * lg, inv * lb + s],
    ], dtype=np.float32)
    return M, ZERO.copy()

def compose_transforms(*transforms):
    M = IDENTITY.copy()
    b = ZERO.copy()
    for A, offset in transforms:
        b = A @ b + offset
        M = A @ M
    return M, b

def apply_affine_rgb(rgb: np.ndarray, M: np.ndarray, b: np.ndarray) -> np.ndarray:
    if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[-1] != 3:
        raise ValueError(f"Expected uint8 (H,W,3), got {rgb.dtype} {rgb.shape}")
    out = rgb @ M.T
    out += b
    np.clip(out, 0.0, 255.0, out=out)
    np.rint(out, out=out)
    return out.astype(np.uint8)

def apply_filter_to_rgb(rgb: np.ndarray, css_class: str) -> np.ndarray:
    css_class = (css_class or "filter-original").strip()

    if css_class == "filter-original":
        return rgb.copy()

    if css_class == "filter-bw":
        M, b = grayscale_transform()
        return apply_affine_rgb(rgb, M, b)

    if css_class == "filter-invert":
        M, b = invert_transform(1.0)
        return apply_affine_rgb(rgb, M, b)

    if css_class == "filter-vivid":
        M, b = compose_transforms(saturation_transform(1.7), contrast_transform(1.15, 128.0))
        return apply_affine_rgb(rgb, M, b)

    if css_class == "filter-warm":
        M, b = compose_transforms(sepia_transform(0.35), saturation_transform(1.3), brightness_transform(1.05))
        return apply_affine_rgb(rgb, M, b)

    if css_class == "filter-soft":
        h, w = rgb.shape[:2]
        x = apply_gaussian_blur(rgb, soft_blur_sigma(w, h))
        M, b = brightness_transform(SOFT_BRIGHTNESS)
        return apply_affine_rgb(x, M, b)

    return rgb