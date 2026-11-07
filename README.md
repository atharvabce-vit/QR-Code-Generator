# QR Code Generator

A desktop QR code toolkit built with Python, CustomTkinter and Pillow. It generates styled QR codes for many content types, exports them in raster and vector formats, builds QR card graphics, handles CSV/Excel batch jobs, and can scan and verify existing codes.

The GUI lives in `qr_app.py`; the work is split across small modules (`qr_payload`, `qr_style`, `qr_export`, `qr_io`, `qr_scan`, `qr_card`). `qr_generator.py` is the older single-script version kept for quick CLI use.

## Features

### Content types
Text, URL, Email, Phone, SMS, Wi-Fi, Contact (vCard), UPI Payment, WhatsApp, Location, Event (iCalendar), Crypto, Social, App Store and Smart Link. Each type has its own fields, and **Quick paste** auto-detects the type from a pasted link, email, phone number, Wi-Fi string, etc.

### Appearance
- Error correction level L / M / Q / H
- Module styles: Square, Rounded, Dots, Classy
- Finder (eye) styles: Square, Rounded, Circle
- Custom foreground / background colors
- Optional two-color gradient fill
- Transparent background
- Adjustable quiet zone and module size
- Center logo with an automatic rounded plate (raises error correction to H)

### Export
- Raster: PNG, JPEG, WebP with a configurable DPI
- Vector: PDF, EPS (true vector via reportlab) and SVG
- Print sizing by real-world width in cm
- Copy the QR image straight to the clipboard
- Save the full QR card as PNG or PDF

### Batch mode
Import a CSV or Excel file, pick the column to encode, then generate numbered PNGs plus a combined multi-page A4 PDF.

### Scan & verify
- Decode a QR code from an image file
- Live webcam scanning (OpenCV)
- HMAC signature check to detect tampering
- Scannability check (quiet zone, module size, contrast, inversion, round-trip decode)

### Workflow extras
- Live preview as you type, with a zoom slider
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
| `qr_io.py` | CSV/Excel loading and PDF sheet export |
| `qr_scan.py` | Image/webcam decoding, signature and scannability checks |
| `qr_card.py` | Renders the composed QR card graphic |
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
python qr_generator.py --csv sample_data.csv --column content --outdir qr_output
```

## Notes

- The HMAC signing key is defined in `qr_payload.SIGNING_KEY`. Change it to a private value if you use the signature feature for anything real, since the code ships with a placeholder key.
- Sample inputs are included as `sample_data.csv` and `sample_batch.csv`.
