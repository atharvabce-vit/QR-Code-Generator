import qrcode
import qrcode.image.svg
from PIL import Image


def make_qr(data, box_size=10, border=4):
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def render_square(data, target=280, border=4):
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    modules = qr.modules_count + 2 * border
    qr.box_size = max(1, target // modules)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    canvas = Image.new("RGB", (target, target), "white")
    offset = (target - image.width) // 2
    canvas.paste(image, (offset, offset))
    return canvas


def save_qr_image(image, path):
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
