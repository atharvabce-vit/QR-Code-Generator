from PIL import Image, ImageDraw, ImageFont

LABEL = "#6B7280"
VALUE = "#111827"
BORDER = "#D0D7E2"
PANEL = "#F6F8FB"
ACCENT = "#0B5CFF"

FONT_FILES = {
    "regular": ["segoeui.ttf", "arial.ttf", "calibri.ttf", "DejaVuSans.ttf"],
    "bold": ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf", "DejaVuSans-Bold.ttf"],
}


def _font(size, bold=False):
    for name in FONT_FILES["bold" if bold else "regular"]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(draw, text, font, max_width, max_lines):
    lines = []
    for raw in (text or "").splitlines() or [""]:
        current = ""
        for word in raw.split(" "):
            candidate = f"{current} {word}".strip()
            if draw.textlength(candidate, font=font) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
            if len(lines) >= max_lines:
                break
        if current and len(lines) < max_lines:
            lines.append(current)
        if len(lines) >= max_lines:
            break
    return lines[:max_lines]


def render_qr_card(title, qr_image, content, caption="", accent=ACCENT):
    width = 720
    header_h = 60
    qr_y = 88
    info_y = qr_y + qr_image.height + 28
    height = info_y + 200

    card = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(card)

    draw.rectangle([0, 0, width - 1, height - 1], outline=BORDER, width=2)
    draw.rectangle([0, 0, width - 1, header_h], fill=accent)
    draw.text((28, 18), title.upper(), font=_font(20, True), fill="white")
    draw.text((width - 28, 22), "QR CODE", font=_font(14, True), fill="white", anchor="ra")

    card.paste(qr_image, ((width - qr_image.width) // 2, qr_y))

    if caption:
        draw.text((width // 2, info_y - 8), caption, font=_font(15, True), fill=VALUE, anchor="ma")

    box_top = info_y + 22
    draw.rectangle([24, box_top, width - 24, height - 24], fill=PANEL, outline=BORDER)
    draw.text((40, box_top + 14), "ENCODED CONTENT", font=_font(12), fill=LABEL)
    y = box_top + 38
    for line in _wrap(draw, content, _font(15), width - 80, 6):
        draw.text((40, y), line, font=_font(15), fill=VALUE)
        y += 22

    return card
