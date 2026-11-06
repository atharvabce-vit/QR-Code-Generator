import csv
import os
from io import BytesIO

from ticket_model import Ticket

ALIASES = {
    "pnr": "pnr",
    "ticket": "pnr",
    "ticket_id": "pnr",
    "ticketid": "pnr",
    "name": "name",
    "passenger": "name",
    "passenger_name": "name",
    "train_no": "train_no",
    "train_number": "train_no",
    "train": "train_no",
    "train_name": "train_name",
    "coach": "coach",
    "seat": "seat",
    "berth": "seat",
    "from": "source",
    "source": "source",
    "origin": "source",
    "to": "destination",
    "destination": "destination",
    "date": "date",
    "journey_date": "date",
    "travel_date": "date",
    "status": "status",
    "fare": "fare",
    "amount": "fare",
    "price": "fare",
}


def _key(value):
    return str(value).strip().lower().replace(" ", "_")


def _row_to_ticket(row):
    data = {}
    for key, value in row.items():
        target = ALIASES.get(_key(key))
        if target and value is not None and str(value).strip():
            data[target] = str(value).strip()
    return Ticket(**data)


def tickets_from_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return [_row_to_ticket(row) for row in reader]


def tickets_from_excel(path):
    import openpyxl

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    rows = sheet.iter_rows(values_only=True)
    header = [(_key(cell) if cell is not None else "") for cell in next(rows)]
    tickets = []
    for row in rows:
        data = {header[i]: value for i, value in enumerate(row) if i < len(header) and header[i]}
        tickets.append(_row_to_ticket(data))
    return tickets


def load_tickets(path):
    if os.path.splitext(path)[1].lower() in (".xlsx", ".xlsm"):
        return tickets_from_excel(path)
    return tickets_from_csv(path)


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
