# QR Code Generator

A desktop QR code toolkit built with Python, CustomTkinter and Pillow. It generates styled QR codes for many content types, exports them in raster and vector formats, builds QR card graphics, handles CSV/Excel batch jobs, and can scan and verify existing codes.

The GUI lives in `qr_app.py`; the work is split across small modules (`qr_payload`, `qr_style`, `qr_export`, `qr_io`, `qr_scan`, `qr_card`, `qr_dynamic`). `qr_generator.py` is the older single-script version kept for quick CLI use.

## Features

### Content types
Text, URL, Email (with optional CC), Phone, SMS (with a `SMSTO` / `sms` scheme choice), Wi-Fi, Contact (vCard), MECARD, UPI Payment, WhatsApp, Location, Event (iCalendar), Crypto, Social, App Store, Maps (Google Maps directions), PayPal, and Smart Link (Telegram, Zoom, Spotify, YouTube, Google Meet, Discord). Each type has its own fields, and **Quick paste** auto-detects the type from a pasted link, email, phone number, Wi-Fi string, MECARD or PayPal.me link.

### Appearance
- Error correction level L / M / Q / H
- Module styles: Square, Rounded, Dots, Classy, Diamond, Star
- Finder (eye) styles: Square, Rounded, Circle, with an optional separate eye color
- Built-in center logo icons (Wi-Fi, Mail, Cart, Location, Link, Info) or your own image, drawn on an automatic rounded plate (raises error correction to H)
- Custom foreground / background colors
- Optional two-color gradient fill
- Transparent background
- Adjustable quiet zone and module size
- Optional caption rendered under the QR code on the card
- Optional card frame band with a preset label (SCAN ME, SCAN TO PAY, SCAN FOR MENU, SCAN TO CONNECT)

### Export
- Raster: PNG, JPEG, WebP with a configurable DPI
- Vector: PDF, EPS (true vector via reportlab) and SVG that matches the chosen style, colors and gradient
- Print sizing by real-world width in cm
- Copy the QR image straight to the clipboard
- Save the full QR card as PNG or PDF

### Batch mode
Import a CSV or Excel file, pick the column to encode, then generate numbered PNGs plus a combined multi-page A4 PDF and a ZIP archive of the whole output folder.

### Scan & verify
- Decode a QR code from an image file
- Scan a QR image straight from the clipboard
- Batch-scan a whole folder of images into a CSV report
- Live webcam scanning (OpenCV) with a selectable camera index
- HMAC signature check to detect tampering
- Load a scanned payload back into the matching form fields (reverse of Quick paste)
- Scannability check (quiet zone, module size, contrast, inversion, round-trip decode)

### Dynamic links
- Batteries-included short-link server (runs locally on your LAN) with editable targets
- Create a short link from the current content, then encode the short URL instead
- Scan analytics per link, viewable in the app and on the server's built-in index page
- Links, targets and scans are stored in a local SQLite database (`qr_links.db`)

### Workflow extras
- Live preview as you type, with a zoom slider
- Live version, module count and error-correction level in the status bar
- Recent QR history (last 8, click a thumbnail to reuse)
- Save / load appearance settings as a JSON preset
- Drag & drop `.csv`, `.xlsx` or image files onto the window
- Theme switch: System / Light / Dark
- Keyboard shortcuts: `Ctrl+G` generate, `Ctrl+S` save PNG, `Ctrl+D` duplicate

## Project structure

| File | Purpose |
| --- | --- |
| `qr_app.py` | Main CustomTkinter GUI |
| `qr_payload.py` | Build, detect, sign and verify payloads |
| `qr_style.py` | QR rendering (styles, colors, gradient, logo) |
| `qr_export.py` | Raster/vector export and clipboard copy |
| `qr_core.py` | Basic qrcode helpers and SVG export |
| `qr_io.py` | CSV/Excel loading, PDF sheet export and ZIP packaging |
| `qr_scan.py` | Image/webcam/clipboard decoding, signature and scannability checks |
| `qr_card.py` | Renders the composed QR card graphic |
| `qr_dynamic.py` | Dynamic short links, local redirect server and scan analytics |
| `qr_theme.json` | CustomTkinter color theme |
| `qr_generator.py` | Older single-script GUI + CLI version |

## Requirements

```
pip install -r requirements.txt
```

`opencv-python` is only needed for scanning (image files, webcam and round-trip tests). Everything else works without it.

## Usage

Run the GUI:

```
python qr_app.py
```

The legacy script also works from the command line:

```
python qr_generator.py -t "https://example.com" -o qr.png
python qr_generator.py -t "https://example.com" --svg -o qr.svg
python qr_generator.py -t "https://example.com" --style Star --finder Rounded --fg "#111827" --ec H
python qr_generator.py -t "mailto:hi@example.com?subject=Hello" --detect --sign -o card.png
python qr_generator.py -t "https://example.com" --dynamic --base http://192.168.1.5:8080
python qr_generator.py --csv sample_data.csv --column content --outdir qr_output --zip
```

## Notes

- The HMAC signing key is defined in `qr_payload.SIGNING_KEY`. Change it to a private value if you use the signature feature for anything real, since the code ships with a placeholder key.
- Dynamic links use a small local server. Devices that scan the QR must be on the same network as this machine and able to reach the server address shown in the app; `qr_links.db` is created next to the code and is git-ignored.
- Sample inputs are included as `sample_data.csv` and `sample_batch.csv`.
