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
        box = max(1, round(_as_int(size, 300) / total))
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


def _hex(text, fallback):
    red, green, blue = _color(text, fallback)
    return f"#{red:02x}{green:02x}{blue:02x}"


def _svg_rect(x, y, w, h, radius=0.0):
    if radius <= 0:
        return f"M{x:g} {y:g}H{x + w:g}V{y + h:g}H{x:g}Z"
    return (
        f"M{x + radius:g} {y:g}H{x + w - radius:g}A{radius:g} {radius:g} 0 0 1 {x + w:g} {y + radius:g}"
        f"V{y + h - radius:g}A{radius:g} {radius:g} 0 0 1 {x + w - radius:g} {y + h:g}"
        f"H{x + radius:g}A{radius:g} {radius:g} 0 0 1 {x:g} {y + h - radius:g}"
        f"V{y + radius:g}A{radius:g} {radius:g} 0 0 1 {x + radius:g} {y:g}Z"
    )


def _svg_ellipse(x, y, w, h):
    rx, ry = w / 2, h / 2
    cx, cy = x + rx, y + ry
    return (
        f"M{cx - rx:g} {cy:g}A{rx:g} {ry:g} 0 1 0 {cx + rx:g} {cy:g}"
        f"A{rx:g} {ry:g} 0 1 0 {cx - rx:g} {cy:g}Z"
    )


def _svg_module(matrix, r, c, n, style):
    x, y = c, r
    if style == "Dots":
        return f'<circle cx="{x + 0.5:g}" cy="{y + 0.5:g}" r="0.5"/>'
    if style == "Rounded":
        return f'<path d="{_svg_rect(x, y, 1, 1, 0.30)}"/>'
    if style == "Classy":
        radius = 1 / 3
        corners = _round_corners(matrix, r, c, n)
        path = _svg_rect(x, y, 1, 1, radius)
        patches = [(0, 0), (1 - radius, 0), (1 - radius, 1 - radius), (0, 1 - radius)]
        for corner, (px, py) in zip(corners, patches):
            if not corner:
                path += _svg_rect(x + px, y + py, radius, radius)
        return f'<path d="{path}"/>'
    return f'<path d="{_svg_rect(x, y, 1, 1)}"/>'


def _svg_finder(top, left, style):
    x, y = left, top
    if style == "Circle":
        ring = _svg_ellipse(x, y, 7, 7) + _svg_ellipse(x + 1, y + 1, 5, 5)
        center = _svg_ellipse(x + 2, y + 2, 3, 3)
    elif style == "Rounded":
        ring = _svg_rect(x, y, 7, 7, 7 * 0.32) + _svg_rect(x + 1, y + 1, 5, 5, 5 * 0.32)
        center = _svg_rect(x + 2, y + 2, 3, 3, 3 * 0.32)
    else:
        ring = _svg_rect(x, y, 7, 7) + _svg_rect(x + 1, y + 1, 5, 5)
        center = _svg_rect(x + 2, y + 2, 3, 3)
    return f'<path d="{ring}" fill-rule="evenodd"/><path d="{center}"/>'


def render_svg(data, path, size=None, box_size=None, border=4, ec="M", style="Square",
               finder="Square", fg="#000000", bg="#FFFFFF", gradient=False,
               gradient_end="#3B82F6", transparent=False, logo_path=None):
    matrix = _matrix(data, ec)
    n = len(matrix)
    border = max(0, _as_int(border, 4))
    total = n + 2 * border

    box = _as_int(box_size, 0)
    if box <= 0:
        box = max(1, round(_as_int(size, 300) / total))
    side = total * box

    foreground = "url(#qr-gradient)" if gradient else _hex(fg, "#000000")
    crisp = ' shape-rendering="crispEdges"' if style == "Square" and finder == "Square" else ""
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{side}" height="{side}" '
        f'viewBox="0 0 {total} {total}"{crisp}>'
    ]
    if gradient:
        parts.append(
            '<defs><linearGradient id="qr-gradient" gradientUnits="userSpaceOnUse" '
            f'x1="0" y1="0" x2="{total}" y2="{total}">'
            f'<stop offset="0" stop-color="{_hex(fg, "#000000")}"/>'
            f'<stop offset="1" stop-color="{_hex(gradient_end, "#3B82F6")}"/>'
            "</linearGradient></defs>"
        )
    if not transparent:
        parts.append(f'<rect width="{total}" height="{total}" fill="{_hex(bg, "#FFFFFF")}"/>')

    parts.append(f'<g fill="{foreground}" transform="translate({border} {border})">')
    for r in range(n):
        for c in range(n):
            if matrix[r][c] and not _in_finders(r, c, n):
                parts.append(_svg_module(matrix, r, c, n, style))
    for top, left in _finder_zones(n):
        parts.append(_svg_finder(top, left, finder))
    parts.append("</g></svg>")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("".join(parts))
    return path
