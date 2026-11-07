import argparse
import csv
import hashlib
import os
import tkinter as tk
from tkinter import filedialog, messagebox

import qrcode
import qrcode.image.svg
from PIL import Image, ImageTk

import qr_dynamic
import qr_io
import qr_payload
import qr_style


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


def save_qr_svg(data, path, border=4):
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        border=border,
        image_factory=qrcode.image.svg.SvgPathImage,
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr.make_image().save(path)
    return path


def render_square(data, target=280, border=4):
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    modules = qr.modules_count + 2 * border
    box = max(1, target // modules)
    qr.box_size = box
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    canvas = Image.new("RGB", (target, target), "white")
    offset = (target - image.width) // 2
    canvas.paste(image, (offset, offset))
    return canvas


def safe_name(text, limit=60):
    cleaned = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in text).strip("_")
    if not cleaned:
        return "qr"
    if len(cleaned) > limit:
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:6]
        cleaned = f"{cleaned[:limit]}_{digest}"
    return cleaned


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
            self.save_svg_button = tk.Button(buttons, text="Save SVG", width=12, state="disabled", command=self.save_svg)
            self.save_svg_button.pack(side="left")

            self.preview_holder = tk.Frame(frame, width=280, height=280, bg="white",
                                           highlightthickness=1, highlightbackground="#cccccc")
            self.preview_holder.grid(row=3, column=0, pady=10)
            self.preview_holder.grid_propagate(False)
            self.preview = tk.Label(self.preview_holder, text="No QR code yet", bg="white", fg="#999999")
            self.preview.place(relx=0.5, rely=0.5, anchor="center")

            self.status = tk.Label(frame, text="Ready", anchor="w", fg="#555555")
            self.status.grid(row=4, column=0, sticky="w")

        def generate(self):
            value = self.text.get("1.0", "end").strip()
            if not value:
                messagebox.showwarning("QR Code Generator", "Please enter some text first.")
                return
            image = render_square(value, 280)
            self.image = ImageTk.PhotoImage(image)
            self.data = value
            self.preview.config(image=self.image, text="")
            self.save_button.config(state="normal")
            self.save_svg_button.config(state="normal")
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

        def save_svg(self):
            path = filedialog.asksaveasfilename(
                defaultextension=".svg",
                filetypes=[("SVG vector", "*.svg")],
                initialfile=f"{safe_name(self.data)}.svg",
            )
            if not path:
                return
            save_qr_svg(self.data, path)
            self.status.config(text=f"Saved: {path}", fg="#1a7f37")

    root = tk.Tk()
    QRApp(root)
    root.mainloop()


def build_parser():
    parser = argparse.ArgumentParser(description="Simple desktop QR code generator.")
    parser.add_argument("-t", "--text", help="Text or URL to encode as a single QR code")
    parser.add_argument("-o", "--output", help="Output path for single mode (default: qr.png / qr.svg)")
    parser.add_argument("--svg", action="store_true", help="Save the single QR code as SVG vector")
    parser.add_argument("--csv", help="CSV file for batch mode")
    parser.add_argument("--column", help="CSV column to encode (default: first column)")
    parser.add_argument("--outdir", help="Output folder for batch mode (default: qr_output)")
    parser.add_argument("--box-size", type=int, default=10, help="Pixel size of each QR module (default: 10)")
    parser.add_argument("--border", type=int, default=4, help="Quiet zone in modules (default: 4)")
    parser.add_argument("--ec", default="M", choices=["L", "M", "Q", "H"], help="Error correction level")
    parser.add_argument("--style", default="Square",
                        choices=["Square", "Rounded", "Dots", "Classy", "Diamond", "Star"],
                        help="Module style")
    parser.add_argument("--finder", default="Square", choices=["Square", "Rounded", "Circle"],
                        help="Finder (eye) style")
    parser.add_argument("--finder-fg", help="Finder (eye) colour, e.g. #0B5CFF")
    parser.add_argument("--fg", default="#000000", help="Foreground colour")
    parser.add_argument("--bg", default="#FFFFFF", help="Background colour")
    parser.add_argument("--sign", action="store_true", help="Add an HMAC signature to the payload")
    parser.add_argument("--detect", action="store_true", help="Auto-detect the payload type and rebuild it")
    parser.add_argument("--zip", action="store_true", help="Zip the batch output folder")
    parser.add_argument("--dynamic", action="store_true", help="Create a short link and encode that instead")
    parser.add_argument("--label", help="Label for a dynamic link")
    parser.add_argument("--base", help="Base URL of the short-link server (default: LAN IP)")
    parser.add_argument("--port", type=int, default=8080, help="Short-link server port (default: 8080)")
    return parser


def single_payload(args):
    content = args.text
    if args.detect:
        kind, values = qr_payload.detect(content)
        content = qr_payload.build(kind, values)
        print(f"Detected type: {kind}")
    if args.sign:
        content = qr_payload.sign(content)
    if args.dynamic:
        code = qr_dynamic.add_link(content, args.label or "cli")
        base = args.base or f"http://{qr_dynamic.local_ip()}:{args.port}"
        short = f"{base.rstrip('/')}/r/{code}"
        print(f"Dynamic link: {short}")
        content = short
    return content


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.csv:
        out_dir = args.outdir or "qr_output"
        count, column = run_batch(args.csv, out_dir, args.column, args.box_size)
        print(f"Generated {count} QR code(s) from column '{column}' into '{out_dir}'.")
        if args.zip:
            print(f"ZIP archive: {qr_io.zip_folder(out_dir)}")
    elif args.text:
        content = single_payload(args)
        options = {
            "box_size": args.box_size,
            "border": args.border,
            "ec": args.ec,
            "style": args.style,
            "finder": args.finder,
            "finder_fg": args.finder_fg,
            "fg": args.fg,
            "bg": args.bg,
        }
        if args.svg:
            path = qr_style.render_svg(content, args.output or "qr.svg", **options)
        else:
            path = args.output or "qr.png"
            qr_style.render(content, **options).save(path)
        print(f"Saved QR code to: {path}")
    else:
        run_gui()


if __name__ == "__main__":
    main()
