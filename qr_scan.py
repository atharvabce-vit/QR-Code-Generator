import os

from PIL import Image

import qr_payload
import qr_style

try:
    import cv2
    import numpy as np

    SCAN_READY = True
except ImportError:
    cv2 = None
    np = None
    SCAN_READY = False


def _require():
    if not SCAN_READY:
        raise RuntimeError("Scanning needs opencv-python. Run: pip install opencv-python")


def _flatten(image):
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        flat = Image.new("RGB", image.size, "white")
        flat.paste(image, (0, 0), image)
        return flat
    return image.convert("RGB")


def _to_bgr(image):
    return np.array(_flatten(image))[:, :, ::-1].copy()


def _decode(array):
    detector = cv2.QRCodeDetector()
    gray = cv2.cvtColor(array, cv2.COLOR_BGR2GRAY)
    attempts = [
        array,
        gray,
        cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR),
        cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)[1],
    ]
    for attempt in attempts:
        text, _, _ = detector.detectAndDecode(attempt)
        if text:
            return text
    return None


def decode_image(path):
    _require()
    return _decode(_to_bgr(Image.open(path)))


def decode_clipboard():
    _require()
    from PIL import ImageGrab

    grabbed = ImageGrab.grabclipboard()
    if not isinstance(grabbed, Image.Image):
        return None
    return _decode(_to_bgr(grabbed))


def scan_folder(folder):
    _require()
    extensions = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tif", ".tiff")
    results = []
    for name in sorted(os.listdir(folder)):
        if os.path.splitext(name)[1].lower() not in extensions:
            continue
        try:
            text = decode_image(os.path.join(folder, name))
        except Exception:
            text = None
        results.append((name, text))
    return results


def decode_frame(frame):
    _require()
    return _decode(frame)


def open_camera(index=0):
    _require()
    camera = cv2.VideoCapture(int(index), cv2.CAP_DSHOW)
    if not camera.isOpened():
        camera.release()
        camera = cv2.VideoCapture(int(index))
    return camera


def frame_to_image(frame, width=None):
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    if width and image.width > width:
        height = int(width * image.height / image.width)
        image = image.resize((width, height))
    return image


def verify_signed(text):
    return qr_payload.verify(text)


def unsigned_content(text):
    if "|SIG:" in text:
        return text.rsplit("|SIG:", 1)[0]
    return text


def _luminance(rgb):
    red, green, blue = rgb[:3]
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def scannability(data, ec="M", border=4, box_size=None, size=None, fg="#000000", bg="#FFFFFF", decode=True):
    messages = []
    matrix = qr_style._matrix(data, ec)
    modules = len(matrix)
    version = (modules - 17) // 4
    quiet = max(0, qr_style._as_int(border, 4))
    total = modules + 2 * quiet

    if box_size and qr_style._as_int(box_size, 0) > 0:
        box = qr_style._as_int(box_size, 10)
    else:
        box = max(1, round(qr_style._as_int(size, 300) / total))

    if quiet < 2:
        messages.append("Quiet zone is under 2 modules, so the scanner has no clear margin.")
    if box < 3:
        messages.append(f"Each module is only {box} px. Aim for 4 px or more.")
    if version > 20:
        messages.append(f"This is version {version} ({modules} x {modules}). Try to shorten the content.")

    front = qr_style._color(fg, "#000000")
    back = qr_style._color(bg, "#FFFFFF")
    contrast = abs(_luminance(front) - _luminance(back))
    if contrast < 90:
        messages.append("Foreground and background are too close in brightness.")
    if _luminance(front) > _luminance(back):
        messages.append("The code is inverted (light modules on a dark background).")

    if decode and SCAN_READY:
        image = qr_style.render(
            data,
            ec=ec,
            border=max(4, quiet),
            box_size=max(4, box),
            fg="#000000",
            bg="#FFFFFF",
        )
        if not _decode(_to_bgr(image)):
            messages.append("A round-trip test could not read this code back.")

    return {
        "modules": modules,
        "version": version,
        "box_size": box,
        "contrast": round(contrast, 1),
        "ok": not messages,
        "messages": messages,
    }
