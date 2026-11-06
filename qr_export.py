import os
import subprocess
import tempfile

from PIL import Image
from reportlab.graphics import renderPDF, renderPS
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.lib.colors import Color

import qr_style

CLIPBOARD_FILE = os.path.join(tempfile.gettempdir(), "qr_clipboard_image.png")

WINDOWS_SCRIPT = (
    "Add-Type -AssemblyName System.Windows.Forms;"
    "Add-Type -AssemblyName System.Drawing;"
    f"$img=[System.Drawing.Image]::FromFile('{CLIPBOARD_FILE}');"
    "[System.Windows.Forms.Clipboard]::SetImage($img);"
    "$img.Dispose()"
)


def _rgb(text, fallback):
    return qr_style._color(text, fallback)


def _color(text, fallback):
    red, green, blue = _rgb(text, fallback)
    return Color(red / 255, green / 255, blue / 255)


def save_raster(image, path, fmt, dpi=300):
    fmt = (fmt or "PNG").upper()
    dots = (int(dpi), int(dpi))
    if fmt == "JPEG":
        flat = Image.new("RGB", image.size, "white")
        flat.paste(image, (0, 0), image if image.mode == "RGBA" else None)
        flat.save(path, "JPEG", quality=95, dpi=dots)
    elif fmt == "WEBP":
        image.save(path, "WEBP", quality=95)
    else:
        image.save(path, "PNG", dpi=dots)
    return path


def _drawing(data, ec="M", border=4, fg="#000000", bg="#FFFFFF", width_cm=5.0, module=3.0):
    matrix = qr_style._matrix(data, ec)
    n = len(matrix)
    total = n + 2 * border
    if width_cm and width_cm > 0:
        module = (width_cm / 2.54 * 72) / total
    side = total * module

    drawing = Drawing(side, side)
    drawing.add(Rect(0, 0, side, side, fillColor=_color(bg, "#FFFFFF"), strokeColor=None))
    fill = _color(fg, "#000000")
    for r in range(n):
        for c in range(n):
            if matrix[r][c]:
                x = (c + border) * module
                y = (n - 1 - r + border) * module
                drawing.add(Rect(x, y, module, module, fillColor=fill, strokeColor=None))
    return drawing


def save_vector(data, path, fmt, width_cm=5.0, ec="M", border=4, fg="#000000", bg="#FFFFFF"):
    drawing = _drawing(data, ec=ec, border=border, fg=fg, bg=bg, width_cm=width_cm)
    if (fmt or "PDF").upper() == "EPS":
        renderPS.drawToFile(drawing, path)
    else:
        renderPDF.drawToFile(drawing, path)
    return path


def copy_to_clipboard(image):
    image.convert("RGBA").save(CLIPBOARD_FILE)
    subprocess.run(
        ["powershell", "-NoProfile", "-STA", "-Command", WINDOWS_SCRIPT],
        check=True,
        capture_output=True,
    )
    return CLIPBOARD_FILE
