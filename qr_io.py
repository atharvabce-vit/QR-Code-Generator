import csv
import hashlib
import os
import zipfile
from io import BytesIO

PREFERRED_COLUMNS = ("content", "text", "value", "data", "url", "qr")


def safe_name(text, limit=60):
    cleaned = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in text).strip("_")
    if not cleaned:
        return "qr"
    if len(cleaned) > limit:
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:6]
        cleaned = f"{cleaned[:limit]}_{digest}"
    return cleaned


def _stable_header(names):
    header = []
    counts = {}
    for index, name in enumerate(names):
        label = str(name).strip() if name is not None else ""
        if not label:
            label = f"Column {index + 1}"
        if label in counts:
            counts[label] += 1
            label = f"{label} ({counts[label]})"
        else:
            counts[label] = 0
        header.append(label)
    return header


def _csv_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        records = list(csv.reader(handle))
    if not records:
        return [], []
    header = _stable_header(records[0])
    rows = []
    for values in records[1:]:
        rows.append({header[i]: (values[i] if i < len(values) else None) for i in range(len(header))})
    return rows, header


def _excel_rows(path):
    import openpyxl

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    values_iter = sheet.iter_rows(values_only=True)
    first = next(values_iter, None)
    if first is None:
        return [], []
    header = _stable_header(first)
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


def zip_folder(folder, path=None):
    if path is None:
        path = folder.rstrip("\\/") + ".zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(os.listdir(folder)):
            full = os.path.join(folder, name)
            if os.path.isfile(full):
                archive.write(full, name)
    return path


def write_rows(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return path
