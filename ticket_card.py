from PIL import Image, ImageDraw, ImageFont

LABEL = "#6B7280"
VALUE = "#111827"
BORDER = "#D0D7E2"
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


def render_ticket(ticket, qr_image, accent=ACCENT):
    width, height = 1000, 440
    card = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(card)

    draw.rectangle([0, 0, width - 1, height - 1], outline=BORDER, width=2)
    draw.rectangle([0, 0, width - 1, 66], fill=accent)
    draw.text((28, 20), "TRAIN TICKET", font=_font(24, True), fill="white")
    draw.text((width - 28, 24), ticket.get("status") or "-", font=_font(20, True), fill="white", anchor="ra")

    draw.text((28, 84), "PNR", font=_font(13), fill=LABEL)
    draw.text((28, 100), ticket.get("pnr") or "-", font=_font(34, True), fill=VALUE)

    divider_x = 724
    for y in range(90, height - 30, 14):
        draw.line([(divider_x, y), (divider_x, y + 7)], fill=BORDER, width=2)

    train = " ".join(x for x in [ticket.get("train_no"), ticket.get("train_name")] if x) or "-"
    coach_seat = "/".join(x for x in [ticket.get("coach"), ticket.get("seat")] if x) or "-"
    info = [
        ("PASSENGER", ticket.get("name") or "-"),
        ("TRAIN", train),
        ("FROM", ticket.get("source") or "-"),
        ("TO", ticket.get("destination") or "-"),
        ("COACH / SEAT", coach_seat),
        ("DATE", ticket.get("date") or "-"),
        ("FARE", ticket.get("fare") or "-"),
        ("STATUS", ticket.get("status") or "-"),
    ]

    col_x = [28, 392]
    row_y = 170
    row_h = 58
    for index, (label, value) in enumerate(info):
        x = col_x[index % 2]
        y = row_y + (index // 2) * row_h
        draw.text((x, y), label, font=_font(13), fill=LABEL)
        draw.text((x, y + 17), value, font=_font(21), fill=VALUE)

    qr_x = divider_x + (width - divider_x - qr_image.width) // 2
    qr_y = 96
    card.paste(qr_image, (qr_x, qr_y))
    caption_x = divider_x + (width - divider_x) // 2
    draw.text((caption_x, qr_y + qr_image.height + 14), "Scan to verify", font=_font(13), fill=LABEL, anchor="ma")

    return card
