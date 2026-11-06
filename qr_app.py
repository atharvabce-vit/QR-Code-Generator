import os
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

import qr_core
import qr_export
import qr_io
import qr_payload
import qr_style
from qr_card import render_qr_card

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


def _as_int(value, fallback):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return fallback


def _as_float(value, fallback):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return fallback


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
        self.logo_path = None

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

        ctk.CTkLabel(panel, text="Appearance", anchor="w").pack(fill="x", pady=(18, 0))

        ctk.CTkLabel(panel, text="Error correction (L / M / Q / H)", anchor="w").pack(fill="x", pady=(8, 0))
        self.ec_var = ctk.StringVar(value="M")
        ctk.CTkOptionMenu(panel, values=["L", "M", "Q", "H"], variable=self.ec_var).pack(fill="x")

        ctk.CTkLabel(panel, text="Module style", anchor="w").pack(fill="x", pady=(8, 0))
        self.style_var = ctk.StringVar(value="Square")
        ctk.CTkOptionMenu(panel, values=["Square", "Rounded", "Dots", "Classy"], variable=self.style_var).pack(fill="x")

        ctk.CTkLabel(panel, text="Finder (eyes) style", anchor="w").pack(fill="x", pady=(8, 0))
        self.finder_var = ctk.StringVar(value="Square")
        ctk.CTkOptionMenu(panel, values=["Square", "Rounded", "Circle"], variable=self.finder_var).pack(fill="x")

        ctk.CTkLabel(panel, text="Foreground color", anchor="w").pack(fill="x", pady=(8, 0))
        self.fg_entry = ctk.CTkEntry(panel, placeholder_text="#000000")
        self.fg_entry.insert(0, "#000000")
        self.fg_entry.pack(fill="x")

        ctk.CTkLabel(panel, text="Background color", anchor="w").pack(fill="x", pady=(8, 0))
        self.bg_entry = ctk.CTkEntry(panel, placeholder_text="#FFFFFF")
        self.bg_entry.insert(0, "#FFFFFF")
        self.bg_entry.pack(fill="x")

        self.gradient_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(panel, text="Gradient fill", variable=self.gradient_var).pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(panel, text="Gradient end color", anchor="w").pack(fill="x", pady=(8, 0))
        self.gradient_end_entry = ctk.CTkEntry(panel, placeholder_text="#3B82F6")
        self.gradient_end_entry.insert(0, "#3B82F6")
        self.gradient_end_entry.pack(fill="x")

        self.transparent_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(panel, text="Transparent background", variable=self.transparent_var).pack(
            fill="x", pady=(8, 0)
        )

        ctk.CTkLabel(panel, text="Quiet zone (modules)", anchor="w").pack(fill="x", pady=(8, 0))
        self.border_entry = ctk.CTkEntry(panel, placeholder_text="4")
        self.border_entry.insert(0, "4")
        self.border_entry.pack(fill="x")

        ctk.CTkLabel(panel, text="Module size (px, for saved PNG)", anchor="w").pack(fill="x", pady=(8, 0))
        self.box_entry = ctk.CTkEntry(panel, placeholder_text="10")
        self.box_entry.insert(0, "10")
        self.box_entry.pack(fill="x")

        ctk.CTkLabel(panel, text="Center logo", anchor="w").pack(fill="x", pady=(10, 0))
        ctk.CTkButton(panel, text="Choose logo image", command=self.choose_logo).pack(fill="x", pady=(6, 0))
        self.logo_label = ctk.CTkLabel(panel, text="No logo selected", anchor="w", text_color="#6B7280")
        self.logo_label.pack(fill="x")
        ctk.CTkButton(panel, text="Clear logo", command=self.clear_logo, fg_color="#4B5563",
                      hover_color="#374151").pack(fill="x", pady=(4, 0))

        ctk.CTkLabel(panel, text="Export", anchor="w").pack(fill="x", pady=(18, 0))
        ctk.CTkLabel(panel, text="Format", anchor="w").pack(fill="x", pady=(8, 0))
        self.format_var = ctk.StringVar(value="PNG")
        ctk.CTkOptionMenu(panel, values=["PNG", "JPEG", "WebP", "PDF", "EPS", "SVG"],
                          variable=self.format_var).pack(fill="x")

        ctk.CTkLabel(panel, text="DPI (for raster print)", anchor="w").pack(fill="x", pady=(8, 0))
        self.dpi_entry = ctk.CTkEntry(panel, placeholder_text="300")
        self.dpi_entry.insert(0, "300")
        self.dpi_entry.pack(fill="x")

        ctk.CTkLabel(panel, text="Print width in cm (0 = use module size)", anchor="w").pack(fill="x", pady=(8, 0))
        self.cm_entry = ctk.CTkEntry(panel, placeholder_text="5")
        self.cm_entry.insert(0, "5")
        self.cm_entry.pack(fill="x")

        ctk.CTkButton(panel, text="Generate QR code", command=self.generate).pack(fill="x", pady=(18, 4))
        ctk.CTkButton(panel, text="Export QR (selected format)", command=self.export_qr).pack(fill="x", pady=4)
        ctk.CTkButton(panel, text="Copy QR image to clipboard", command=self.copy_qr).pack(fill="x", pady=4)
        ctk.CTkButton(panel, text="Save card as PNG", command=self.save_png).pack(fill="x", pady=(12, 4))
        ctk.CTkButton(panel, text="Save card as PDF", command=self.save_pdf).pack(fill="x", pady=4)
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

    def _appearance(self, size=None, box_size=None):
        options = {
            "size": size,
            "box_size": box_size,
            "border": self.border_entry.get(),
            "ec": self.ec_var.get(),
            "style": self.style_var.get(),
            "finder": self.finder_var.get(),
            "fg": self.fg_entry.get(),
            "bg": self.bg_entry.get(),
            "gradient": self.gradient_var.get(),
            "gradient_end": self.gradient_end_entry.get(),
            "transparent": self.transparent_var.get(),
            "logo_path": self.logo_path,
        }
        if self.logo_path and options["ec"] != "H":
            options["ec"] = "H"
        return options

    def _export_options(self):
        dpi = _as_int(self.dpi_entry.get(), 300) or 300
        cm = _as_float(self.cm_entry.get(), 0.0)
        if cm > 0:
            return self._appearance(size=max(64, round(cm / 2.54 * dpi)))
        return self._appearance(box_size=self.box_entry.get())

    def choose_logo(self):
        path = filedialog.askopenfilename(
            title="Choose a logo image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")],
        )
        if not path:
            return
        self.logo_path = path
        self.logo_label.configure(text=os.path.basename(path))
        if self.ec_var.get() != "H":
            self.ec_var.set("H")
        self.status.configure(text="Logo set (error correction raised to H)")

    def clear_logo(self):
        self.logo_path = None
        self.logo_label.configure(text="No logo selected")
        self.status.configure(text="Logo cleared")

    def _render(self, kind, content, caption=""):
        qr = qr_style.render(content, **self._appearance(size=300))
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

    def export_qr(self):
        if not self.content:
            messagebox.showwarning("QR Code Generator", "Generate a QR code first.")
            return
        fmt = self.format_var.get()
        ext = {"JPEG": "jpg", "WebP": "webp"}.get(fmt, fmt.lower())
        path = filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            filetypes=[(f"{fmt} file", f"*.{ext}")],
            initialfile=f"{qr_io.safe_name(self.content)}.{ext}",
        )
        if not path:
            return
        try:
            if fmt in ("PDF", "EPS"):
                qr_export.save_vector(
                    self.content, path, fmt,
                    width_cm=_as_float(self.cm_entry.get(), 5.0) or 5.0,
                    ec=self.ec_var.get(),
                    border=_as_int(self.border_entry.get(), 4),
                    fg=self.fg_entry.get(),
                    bg=self.bg_entry.get(),
                )
            elif fmt == "SVG":
                qr_core.save_qr_svg(self.content, path)
            else:
                image = qr_style.render(self.content, **self._export_options())
                qr_export.save_raster(image, path, fmt, _as_int(self.dpi_entry.get(), 300))
        except Exception as error:
            messagebox.showerror("QR Code Generator", f"Export failed:\n{error}")
            return
        self.status.configure(text=f"Saved: {path}")

    def copy_qr(self):
        if not self.content:
            messagebox.showwarning("QR Code Generator", "Generate a QR code first.")
            return
        try:
            image = qr_style.render(self.content, **self._appearance(box_size=self.box_entry.get()))
            qr_export.copy_to_clipboard(image)
        except Exception as error:
            messagebox.showerror("QR Code Generator", f"Could not copy the image:\n{error}")
            return
        self.status.configure(text="QR image copied to clipboard")

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
