import os

import qrcode
from PIL import Image, ImageColor, ImageDraw

EC_LEVELS = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H,
}


def _color(text, fallback):
    try:
        return ImageColor.getrgb((text or "").strip())
    except (ValueError, AttributeError):
        return ImageColor.getrgb(fallback)


def _as_int(value, fallback):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return fallback


def _matrix(data, ec):
    qr = qrcode.QRCode(error_correction=EC_LEVELS.get(ec, qrcode.constants.ERROR_CORRECT_M), border=0)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.get_matrix()


def _finder_zones(n):
    return [(0, 0), (0, n - 7), (n - 7, 0)]


def _in_finders(r, c, n):
    for top, left in _finder_zones(n):
        if top <= r < top + 7 and left <= c < left + 7:
            return True
    return False


def _round_corners(matrix, r, c, n):
    def dark(rr, cc):
        return 0 <= rr < n and 0 <= cc < n and matrix[rr][cc]

    up, down, left, right = dark(r - 1, c), dark(r + 1, c), dark(r, c - 1), dark(r, c + 1)
    return (not up and not left, not up and not right, not down and not right, not down and not left)


def _shape(draw, rect, style, fill):
    span = min(rect[2] - rect[0], rect[3] - rect[1])
    if style == "Circle":
        draw.ellipse(rect, fill=fill)
    elif style == "Rounded":
        draw.rounded_rectangle(rect, radius=max(1, int(span * 0.32)), fill=fill)
    else:
        draw.rectangle(rect, fill=fill)


def _module_shape(draw, rect, style, fill, corners):
    x0, y0, x1, y1 = rect
    span = min(x1 - x0, y1 - y0)
    if style == "Dots":
        draw.ellipse(rect, fill=fill)
    elif style == "Rounded":
        draw.rounded_rectangle(rect, radius=max(1, int(span * 0.30)), fill=fill)
    elif style == "Classy":
        radius = max(1, span // 3)
        draw.rounded_rectangle(rect, radius=radius, fill=fill)
        if not corners[0]:
            draw.rectangle([x0, y0, x0 + radius, y0 + radius], fill=fill)
        if not corners[1]:
            draw.rectangle([x1 - radius, y0, x1, y0 + radius], fill=fill)
        if not corners[2]:
            draw.rectangle([x1 - radius, y1 - radius, x1, y1], fill=fill)
        if not corners[3]:
            draw.rectangle([x0, y1 - radius, x0 + radius, y1], fill=fill)
    else:
        draw.rectangle(rect, fill=fill)


def _draw_finder(draw, top, left, box, border, style):
    def rect(r0, c0, span):
        x0 = (c0 + border) * box
        y0 = (r0 + border) * box
        return [x0, y0, x0 + span * box - 1, y0 + span * box - 1]

    _shape(draw, rect(top, left, 7), style, 255)
    _shape(draw, rect(top + 1, left + 1, 5), style, 0)
    _shape(draw, rect(top + 2, left + 2, 3), style, 255)


def _gradient(size, start, end):
    steps = 128
    small = Image.new("RGBA", (steps, steps))
    pixels = small.load()
    for y in range(steps):
        for x in range(steps):
            t = (x + y) / (2 * (steps - 1))
            pixels[x, y] = tuple(round(start[i] + (end[i] - start[i]) * t) for i in range(3)) + (255,)
    return small.resize((size, size), Image.BILINEAR)


def _add_logo(image, path, plate_color):
    logo = Image.open(path).convert("RGBA")
    target = max(24, int(image.width * 0.22))
    logo.thumbnail((target, target), Image.LANCZOS)

    pad = max(4, int(target * 0.10))
    side = logo.width + 2 * pad
    plate = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    ImageDraw.Draw(plate).rounded_rectangle(
        [0, 0, side - 1, side - 1],
        radius=max(1, int(side * 0.16)),
        fill=_color(plate_color, "#FFFFFF") + (255,),
    )
    plate.paste(logo, (pad, pad), logo)
    image.alpha_composite(plate, ((image.width - side) // 2, (image.height - side) // 2))
    return image


def render(data, size=None, box_size=None, border=4, ec="M", style="Square", finder="Square",
           fg="#000000", bg="#FFFFFF", gradient=False, gradient_end="#3B82F6",
           transparent=False, logo_path=None):
    matrix = _matrix(data, ec)
    n = len(matrix)
    border = max(0, _as_int(border, 4))
    total = n + 2 * border

    if box_size and _as_int(box_size, 0) > 0:
        box = _as_int(box_size, 10)
    else:
        box = max(1, _as_int(size, 300) // total)
    side = box * total

    mask = Image.new("L", (side, side), 0)
    painter = ImageDraw.Draw(mask)
    for r in range(n):
        for c in range(n):
            if not matrix[r][c] or _in_finders(r, c, n):
                continue
            x0 = (c + border) * box
            y0 = (r + border) * box
            rect = [x0, y0, x0 + box - 1, y0 + box - 1]
            _module_shape(painter, rect, style, 255, _round_corners(matrix, r, c, n))

    for top, left in _finder_zones(n):
        _draw_finder(painter, top, left, box, border, finder)

    if gradient:
        fill = _gradient(side, _color(fg, "#000000"), _color(gradient_end, "#3B82F6"))
    else:
        fill = Image.new("RGBA", (side, side), _color(fg, "#000000") + (255,))

    base = Image.new("RGBA", (side, side), (0, 0, 0, 0) if transparent else _color(bg, "#FFFFFF") + (255,))
    base.paste(fill, (0, 0), mask)

    if logo_path and os.path.isfile(logo_path):
        base = _add_logo(base, logo_path, "#FFFFFF" if transparent else bg)
    return base
