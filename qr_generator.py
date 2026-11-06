import argparse
import csv
import os
import tkinter as tk
from tkinter import filedialog, messagebox

import qrcode
from PIL import Image, ImageTk


def make_qr_image(data, box_size=10, border=4):
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def save_qr(data, path, box_size=10, border=4):
    image = make_qr_image(data, box_size, border)
    image.save(path)
    return path


def safe_name(text, limit=60):
    cleaned = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in text).strip("_")
    return cleaned[:limit] or "qr"


def run_batch(csv_path, out_dir, column, box_size):
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    os.makedirs(out_dir, exist_ok=True)

    with open(csv_path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if not fields:
            raise ValueError("CSV file has no header row")

        target = column or fields[0]
        if target not in fields:
            raise ValueError(f"Column '{target}' not in CSV. Available: {', '.join(fields)}")

        count = 0
        for row in reader:
            value = (row.get(target) or "").strip()
            if not value:
                continue
            filename = safe_name(value)
            path = os.path.join(out_dir, f"{count + 1:03d}_{filename}.png")
            save_qr(value, path, box_size)
            count += 1

    return count, target


def run_gui():
    class QRApp:
        def __init__(self, root):
            self.root = root
            self.image = None
            self.data = ""

            root.title("QR Code Generator")
            root.resizable(False, False)

            frame = tk.Frame(root, padx=12, pady=12)
            frame.pack()

            tk.Label(frame, text="Text or URL").grid(row=0, column=0, sticky="w")
            self.text = tk.Text(frame, width=42, height=5, wrap="word")
            self.text.grid(row=1, column=0, pady=(4, 10))
            self.text.insert("1.0", "https://example.com")

            buttons = tk.Frame(frame)
            buttons.grid(row=2, column=0, sticky="w")
            tk.Button(buttons, text="Generate", width=12, command=self.generate).pack(side="left")
            self.save_button = tk.Button(buttons, text="Save PNG", width=12, state="disabled", command=self.save)
            self.save_button.pack(side="left", padx=8)

            self.preview = tk.Label(frame, text="No QR code yet", width=40, height=14, bg="#f0f0f0")
            self.preview.grid(row=3, column=0, pady=10)

            self.status = tk.Label(frame, text="Ready", anchor="w", fg="#555555")
            self.status.grid(row=4, column=0, sticky="w")

        def generate(self):
            value = self.text.get("1.0", "end").strip()
            if not value:
                messagebox.showwarning("QR Code Generator", "Please enter some text first.")
                return
            image = make_qr_image(value).resize((260, 260), Image.LANCZOS)
            self.image = ImageTk.PhotoImage(image)
            self.data = value
            self.preview.config(image=self.image, text="")
            self.save_button.config(state="normal")
            self.status.config(text="QR code generated. Click 'Save PNG' to export.", fg="#555555")

        def save(self):
            path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG image", "*.png")],
                initialfile=f"{safe_name(self.data)}.png",
            )
            if not path:
                return
            save_qr(self.data, path)
            self.status.config(text=f"Saved: {path}", fg="#1a7f37")

    root = tk.Tk()
    QRApp(root)
    root.mainloop()


def build_parser():
    parser = argparse.ArgumentParser(description="Simple desktop QR code generator.")
    parser.add_argument("-t", "--text", help="Text or URL to encode as a single QR code")
    parser.add_argument("-o", "--output", help="Output PNG path for single mode (default: qr.png)")
    parser.add_argument("--csv", help="CSV file for batch mode")
    parser.add_argument("--column", help="CSV column to encode (default: first column)")
    parser.add_argument("--outdir", help="Output folder for batch mode (default: qr_output)")
    parser.add_argument("--box-size", type=int, default=10, help="Pixel size of each QR module (default: 10)")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.csv:
        count, column = run_batch(args.csv, args.outdir or "qr_output", args.column, args.box_size)
        print(f"Generated {count} QR code(s) from column '{column}' into '{args.outdir or 'qr_output'}'.")
    elif args.text:
        path = save_qr(args.text, args.output or "qr.png", args.box_size)
        print(f"Saved QR code to: {path}")
    else:
        run_gui()


if __name__ == "__main__":
    main()
