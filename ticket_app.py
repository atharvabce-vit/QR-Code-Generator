import os
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

import qr_core
import ticket_io
from ticket_card import render_ticket
from ticket_model import SECRET, Ticket, safe_name

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

STATUS_OPTIONS = ["CNF", "RAC", "WL", "CAN"]
PREVIEW_WIDTH = 640

FIELDS = [
    ("pnr", "PNR"),
    ("name", "Passenger name"),
    ("train_no", "Train number"),
    ("train_name", "Train name"),
    ("coach", "Coach"),
    ("seat", "Seat"),
    ("source", "From"),
    ("destination", "To"),
    ("date", "Journey date"),
    ("fare", "Fare"),
]

SAMPLE = {
    "pnr": "4218765432",
    "name": "A. Sharma",
    "train_no": "12951",
    "train_name": "Rajdhani Express",
    "coach": "B3",
    "seat": "42",
    "source": "Mumbai Central",
    "destination": "New Delhi",
    "date": "2026-11-20",
    "fare": "2450",
}


class TicketApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Ticket QR Generator")
        self.geometry("1100x640")
        self.minsize(1000, 600)

        self.card_image = None
        self.preview_image = None
        self.ticket = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_form()
        self._build_preview()

    def _build_form(self):
        panel = ctk.CTkScrollableFrame(self, width=340, label_text="Ticket details")
        panel.grid(row=0, column=0, sticky="nsw", padx=(12, 6), pady=12)

        self.entries = {}
        for key, label in FIELDS:
            ctk.CTkLabel(panel, text=label, anchor="w").pack(fill="x", pady=(6, 0))
            entry = ctk.CTkEntry(panel, placeholder_text=label)
            entry.pack(fill="x")
            entry.insert(0, SAMPLE.get(key, ""))
            self.entries[key] = entry

        ctk.CTkLabel(panel, text="Status", anchor="w").pack(fill="x", pady=(6, 0))
        self.status_var = ctk.StringVar(value="CNF")
        ctk.CTkOptionMenu(panel, values=STATUS_OPTIONS, variable=self.status_var).pack(fill="x")

        ctk.CTkButton(panel, text="Generate ticket", command=self.generate).pack(fill="x", pady=(18, 4))
        ctk.CTkButton(panel, text="Save card as PNG", command=self.save_png).pack(fill="x", pady=4)
        ctk.CTkButton(panel, text="Save card as PDF", command=self.save_pdf).pack(fill="x", pady=4)
        ctk.CTkButton(
            panel,
            text="Import CSV / Excel (batch)",
            fg_color="#2f855a",
            hover_color="#276749",
            command=self.batch_import,
        ).pack(fill="x", pady=(18, 4))

    def _build_preview(self):
        panel = ctk.CTkFrame(self)
        panel.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(0, weight=1)

        self.preview = ctk.CTkLabel(
            panel,
            text="Generate a ticket to see the preview",
            fg_color="white",
            text_color="#6B7280",
            corner_radius=12,
            wraplength=520,
        )
        self.preview.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        self.status = ctk.CTkLabel(panel, text="Ready", anchor="w")
        self.status.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))

    def _collect(self):
        values = {key: entry.get().strip() for key, entry in self.entries.items()}
        values["status"] = self.status_var.get()
        return Ticket(**values)

    def _render(self, ticket):
        qr = qr_core.render_square(ticket.payload(SECRET), 236)
        return render_ticket(ticket, qr)

    def generate(self):
        ticket = self._collect()
        if not ticket.get("pnr") and not ticket.get("name"):
            messagebox.showwarning("Ticket QR Generator", "Enter at least a PNR or passenger name.")
            return
        card = self._render(ticket)
        self.card_image = card
        self.ticket = ticket
        height = int(PREVIEW_WIDTH * card.height / card.width)
        preview = card.resize((PREVIEW_WIDTH, height), Image.LANCZOS)
        self.preview_image = ctk.CTkImage(light_image=preview, size=(PREVIEW_WIDTH, height))
        self.preview.configure(image=self.preview_image, text="")
        self.status.configure(text=f"Generated ticket for PNR {ticket.get('pnr') or '-'}")

    def save_png(self):
        if self.card_image is None:
            messagebox.showwarning("Ticket QR Generator", "Generate a ticket first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png")],
            initialfile=f"{safe_name(self.ticket.get('pnr') or self.ticket.get('name'))}.png",
        )
        if not path:
            return
        self.card_image.save(path)
        self.status.configure(text=f"Saved: {path}")

    def save_pdf(self):
        if self.card_image is None:
            messagebox.showwarning("Ticket QR Generator", "Generate a ticket first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF document", "*.pdf")],
            initialfile=f"{safe_name(self.ticket.get('pnr') or self.ticket.get('name'))}.pdf",
        )
        if not path:
            return
        ticket_io.export_pdf([self.card_image], path)
        self.status.configure(text=f"Saved: {path}")

    def batch_import(self):
        path = filedialog.askopenfilename(
            filetypes=[("Ticket files", "*.csv *.xlsx *.xlsm"), ("CSV", "*.csv"), ("Excel", "*.xlsx *.xlsm")]
        )
        if not path:
            return
        try:
            tickets = ticket_io.load_tickets(path)
        except Exception as error:
            messagebox.showerror("Ticket QR Generator", f"Could not read file:\n{error}")
            return
        tickets = [t for t in tickets if t.get("pnr") or t.get("name")]
        if not tickets:
            messagebox.showwarning("Ticket QR Generator", "No usable rows found in that file.")
            return

        out_dir = filedialog.askdirectory(title="Choose output folder for ticket PNGs")
        if not out_dir:
            return

        self.status.configure(text=f"Generating {len(tickets)} ticket(s)…")
        self.update_idletasks()

        cards = []
        for index, ticket in enumerate(tickets, 1):
            card = self._render(ticket)
            name = safe_name(ticket.get("pnr") or ticket.get("name"))
            card.save(os.path.join(out_dir, f"{index:03d}_{name}.png"))
            cards.append(card)

        pdf_path = ticket_io.export_pdf(cards, os.path.join(out_dir, "tickets.pdf"))
        self.status.configure(text=f"Generated {len(cards)} ticket(s) + PDF in {out_dir}")
        messagebox.showinfo(
            "Ticket QR Generator",
            f"Generated {len(cards)} ticket PNG(s) and a combined PDF in:\n{out_dir}",
        )


def main():
    TicketApp().mainloop()


if __name__ == "__main__":
    main()
