import os
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

import qr_core
import qr_io
import qr_payload
from qr_card import render_qr_card

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

PREVIEW_WIDTH = 520
TYPES = [
    "Text",
    "URL",
    "Email",
    "Phone",
    "SMS",
    "Wi-Fi",
    "Contact",
    "UPI Payment",
    "WhatsApp",
    "Location",
    "Event",
    "Crypto",
    "Social",
    "App Store",
    "Smart Link",
]

FIELD_DEFS = {
    "Text": [("text", "Text or message", "text", "Hello from a QR code")],
    "URL": [("url", "Link / URL", "entry", "https://example.com")],
    "Email": [
        ("to", "Recipient email", "entry", "hello@example.com"),
        ("subject", "Subject", "entry", "Hello"),
        ("body", "Message", "text", ""),
    ],
    "Phone": [("number", "Phone number", "entry", "+91 99999 99999")],
    "SMS": [
        ("number", "Phone number", "entry", "+91 99999 99999"),
        ("message", "Message", "text", ""),
    ],
    "Wi-Fi": [
        ("ssid", "Network name (SSID)", "entry", "MyNetwork"),
        ("password", "Password", "entry", ""),
        ("security", "Security (WPA / WEP / nopass)", "entry", "WPA"),
        ("hidden", "Hidden network (yes / no)", "entry", "no"),
    ],
    "Contact": [
        ("name", "Full name", "entry", "A. Sharma"),
        ("phone", "Phone", "entry", "+91 99999 99999"),
        ("email", "Email", "entry", "hello@example.com"),
        ("org", "Company", "entry", ""),
        ("title", "Job title", "entry", ""),
        ("website", "Website", "entry", ""),
        ("address", "Address", "entry", ""),
        ("notes", "Notes", "text", ""),
    ],
    "UPI Payment": [
        ("pa", "UPI ID / VPA", "entry", "name@bank"),
        ("pn", "Payee name", "entry", "Shop name"),
        ("am", "Amount (optional)", "entry", ""),
        ("tn", "Note (optional)", "entry", ""),
    ],
    "WhatsApp": [
        ("number", "Phone with country code", "entry", "919999999999"),
        ("message", "Prefilled message", "text", ""),
    ],
    "Location": [
        ("lat", "Latitude", "entry", "19.0760"),
        ("lng", "Longitude", "entry", "72.8777"),
        ("label", "Label (optional)", "entry", ""),
    ],
    "Event": [
        ("title", "Event title", "entry", "Team meeting"),
        ("location", "Location", "entry", ""),
        ("start", "Start (YYYYMMDDTHHMMSS)", "entry", "20261106T100000"),
        ("end", "End (YYYYMMDDTHHMMSS)", "entry", "20261106T110000"),
        ("description", "Details", "text", ""),
    ],
    "Crypto": [
        ("coin", "Coin", "choice", "Bitcoin", ["Bitcoin", "Ethereum"]),
        ("address", "Wallet address", "entry", ""),
        ("amount", "Amount (optional)", "entry", ""),
    ],
    "Social": [
        ("platform", "Platform", "choice", "Instagram",
         ["Instagram", "YouTube", "LinkedIn", "Facebook", "X (Twitter)"]),
        ("handle", "Username / handle (or full URL)", "entry", "yourname"),
    ],
    "App Store": [
        ("store", "Store", "choice", "Play Store", ["Play Store", "App Store"]),
        ("app", "Package name / app ID (or full URL)", "entry", "com.example.app"),
    ],
    "Smart Link": [
        ("service", "Service", "choice", "Telegram", ["Telegram", "Zoom", "Spotify", "YouTube"]),
        ("value", "Link or ID", "entry", ""),
    ],
}


class QRApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("QR Code Generator")
        self.geometry("1120x700")
        self.minsize(1020, 660)

        self.card_image = None
        self.preview_image = None
        self.content = ""
        self.fields = {}

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_form()
        self._build_preview()
        self._rebuild_fields("Text")

    def _build_form(self):
        panel = ctk.CTkScrollableFrame(self, width=360, label_text="QR settings")
        panel.grid(row=0, column=0, sticky="nsw", padx=(12, 6), pady=12)

        ctk.CTkLabel(panel, text="Content type", anchor="w").pack(fill="x", pady=(4, 0))
        self.type_var = ctk.StringVar(value="Text")
        ctk.CTkOptionMenu(panel, values=TYPES, variable=self.type_var, command=self._rebuild_fields).pack(fill="x")

        self.fields_frame = ctk.CTkFrame(panel, fg_color="transparent")
        self.fields_frame.pack(fill="x", pady=(4, 0))

        ctk.CTkLabel(panel, text="Caption (optional)", anchor="w").pack(fill="x", pady=(10, 0))
        self.caption_entry = ctk.CTkEntry(panel, placeholder_text="Shown under the QR code")
        self.caption_entry.pack(fill="x")

        self.sign_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(panel, text="Add HMAC signature (tamper check)", variable=self.sign_var).pack(
            fill="x", pady=(12, 0)
        )

        ctk.CTkButton(panel, text="Generate QR code", command=self.generate).pack(fill="x", pady=(18, 4))
        ctk.CTkButton(panel, text="Save card as PNG", command=self.save_png).pack(fill="x", pady=4)
        ctk.CTkButton(panel, text="Save card as PDF", command=self.save_pdf).pack(fill="x", pady=4)
        ctk.CTkButton(panel, text="Save QR as SVG (vector)", command=self.save_svg).pack(fill="x", pady=4)
        ctk.CTkButton(
            panel,
            text="Batch: import CSV / Excel",
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
            text="Pick a content type, fill the fields, then Generate",
            fg_color="white",
            text_color="#6B7280",
            corner_radius=12,
            wraplength=460,
        )
        self.preview.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        self.status = ctk.CTkLabel(panel, text="Ready", anchor="w")
        self.status.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))

    def _rebuild_fields(self, kind):
        for widget in self.fields_frame.winfo_children():
            widget.destroy()
        self.fields = {}
        for entry in FIELD_DEFS[kind]:
            key, label, widget_kind, default = entry[:4]
            options = entry[4] if len(entry) > 4 else None
            ctk.CTkLabel(self.fields_frame, text=label, anchor="w").pack(fill="x", pady=(8, 0))
            if widget_kind == "text":
                widget = ctk.CTkTextbox(self.fields_frame, height=80)
                widget.pack(fill="x")
                if default:
                    widget.insert("1.0", default)
            elif widget_kind == "choice":
                widget = ctk.CTkOptionMenu(self.fields_frame, values=options or [])
                widget.set(default)
                widget.pack(fill="x")
            else:
                widget = ctk.CTkEntry(self.fields_frame, placeholder_text=label)
                widget.pack(fill="x")
                if default:
                    widget.insert(0, default)
            self.fields[key] = widget
        self.status.configure(text=f"Content type: {kind}")

    def _collect(self):
        values = {}
        for key, widget in self.fields.items():
            if isinstance(widget, ctk.CTkTextbox):
                values[key] = widget.get("1.0", "end").strip()
            else:
                values[key] = widget.get().strip()
        return values

    def _build_content(self):
        kind = self.type_var.get()
        content = qr_payload.build(kind, self._collect())
        if self.sign_var.get() and content:
            content = qr_payload.sign(content)
        return kind, content

    def _render(self, kind, content, caption=""):
        qr = qr_core.render_square(content, 300)
        return render_qr_card(kind, qr, content, caption)

    def _show(self, card):
        height = int(PREVIEW_WIDTH * card.height / card.width)
        preview = card.resize((PREVIEW_WIDTH, height), Image.LANCZOS)
        self.preview_image = ctk.CTkImage(light_image=preview, size=(PREVIEW_WIDTH, height))
        self.preview.configure(image=self.preview_image, text="")

    def generate(self):
        kind, content = self._build_content()
        if not content:
            messagebox.showwarning("QR Code Generator", "Please fill in the fields first.")
            return
        card = self._render(kind, content, self.caption_entry.get().strip())
        self.card_image = card
        self.content = content
        self._show(card)
        self.status.configure(text=f"Generated {kind} QR code")

    def save_png(self):
        if self.card_image is None:
            messagebox.showwarning("QR Code Generator", "Generate a QR code first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png")],
            initialfile=f"{qr_io.safe_name(self.content)}.png",
        )
        if not path:
            return
        self.card_image.save(path)
        self.status.configure(text=f"Saved: {path}")

    def save_pdf(self):
        if self.card_image is None:
            messagebox.showwarning("QR Code Generator", "Generate a QR code first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF document", "*.pdf")],
            initialfile=f"{qr_io.safe_name(self.content)}.pdf",
        )
        if not path:
            return
        qr_io.export_pdf([self.card_image], path)
        self.status.configure(text=f"Saved: {path}")

    def save_svg(self):
        if not self.content:
            messagebox.showwarning("QR Code Generator", "Generate a QR code first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".svg",
            filetypes=[("SVG vector", "*.svg")],
            initialfile=f"{qr_io.safe_name(self.content)}.svg",
        )
        if not path:
            return
        qr_core.save_qr_svg(self.content, path)
        self.status.configure(text=f"Saved: {path}")

    def batch_import(self):
        path = filedialog.askopenfilename(
            filetypes=[("Data files", "*.csv *.xlsx *.xlsm"), ("CSV", "*.csv"), ("Excel", "*.xlsx *.xlsm")]
        )
        if not path:
            return
        try:
            values, column = qr_io.load_values(path)
        except Exception as error:
            messagebox.showerror("QR Code Generator", f"Could not read file:\n{error}")
            return
        if not values:
            messagebox.showwarning("QR Code Generator", "No usable rows found in that file.")
            return

        out_dir = filedialog.askdirectory(title="Choose output folder for QR PNGs")
        if not out_dir:
            return

        self.status.configure(text=f"Generating {len(values)} QR code(s)…")
        self.update_idletasks()

        cards = []
        for index, value in enumerate(values, 1):
            card = self._render("Text", value)
            card.save(os.path.join(out_dir, f"{index:03d}_{qr_io.safe_name(value)}.png"))
            cards.append(card)

        qr_io.export_pdf(cards, os.path.join(out_dir, "qr_codes.pdf"))
        self.status.configure(text=f"Generated {len(cards)} QR code(s) from column '{column}'")
        messagebox.showinfo(
            "QR Code Generator",
            f"Generated {len(cards)} QR PNG(s) and a combined PDF in:\n{out_dir}",
        )


def main():
    QRApp().mainloop()


if __name__ == "__main__":
    main()
