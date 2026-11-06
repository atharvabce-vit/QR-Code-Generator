import csv
import os
from io import BytesIO

PREFERRED_COLUMNS = ("content", "text", "value", "data", "url", "qr")


def safe_name(text, limit=60):
    cleaned = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in text).strip("_")
    return cleaned[:limit] or "qr"


def _csv_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header = [name for name in (reader.fieldnames or []) if name]
        rows = [dict(row) for row in reader]
    return rows, header


def _excel_rows(path):
    import openpyxl

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    values_iter = sheet.iter_rows(values_only=True)
    header = [str(cell).strip() for cell in next(values_iter) if cell is not None]
    rows = []
    for values in values_iter:
        rows.append({header[i]: (values[i] if i < len(values) else None) for i in range(len(header))})
    return rows, header


def _pick_column(header):
    lowered = {name.lower(): name for name in header}
    for candidate in PREFERRED_COLUMNS:
        if candidate in lowered:
            return lowered[candidate]
    return header[0] if header else None


def load_values(path, column=None):
    if os.path.splitext(path)[1].lower() in (".xlsx", ".xlsm"):
        rows, header = _excel_rows(path)
    else:
        rows, header = _csv_rows(path)

    if not header:
        raise ValueError("File has no header row")

    target = column or _pick_column(header)
    if target not in header:
        raise ValueError(f"Column '{target}' not found. Available: {', '.join(header)}")

    values = []
    for row in rows:
        value = str(row.get(target) or "").strip()
        if value:
            values.append(value)
    return values, target


def export_pdf(cards, path):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas as pdf_canvas

    page_width, page_height = A4
    margin = 36
    gap = 20
    canvas = pdf_canvas.Canvas(path, pagesize=A4)
    y = page_height - margin
    for card in cards:
        draw_width = page_width - 2 * margin
        draw_height = draw_width * card.height / card.width
        if y - draw_height < margin:
            canvas.showPage()
            y = page_height - margin
        buffer = BytesIO()
        card.save(buffer, format="PNG")
        buffer.seek(0)
        canvas.drawImage(ImageReader(buffer), margin, y - draw_height, width=draw_width, height=draw_height)
        y -= draw_height + gap
    canvas.save()
    return path
