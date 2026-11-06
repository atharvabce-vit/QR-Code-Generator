import hashlib
import hmac
from urllib.parse import parse_qs, quote

SIGNING_KEY = "change-this-shared-secret"


def build(kind, values):
    get = lambda key: (values.get(key) or "").strip()

    if kind == "Text":
        return get("text")

    if kind == "URL":
        return get("url")

    if kind == "Email":
        to, subject, body = get("to"), get("subject"), get("body")
        params = []
        if subject:
            params.append("subject=" + quote(subject))
        if body:
            params.append("body=" + quote(body))
        query = "&".join(params)
        return f"mailto:{to}?{query}" if query else f"mailto:{to}"

    if kind == "Phone":
        return f"tel:{get('number')}"

    if kind == "SMS":
        return f"SMSTO:{get('number')}:{get('message')}"

    if kind == "Wi-Fi":
        security = get("security") or "WPA"
        hidden = "true" if get("hidden").lower() in ("yes", "true", "1") else "false"
        return f"WIFI:T:{security};S:{get('ssid')};P:{get('password')};H:{hidden};;"

    if kind == "Contact":
        lines = ["BEGIN:VCARD", "VERSION:3.0", f"N:{get('name')}", f"FN:{get('name')}"]
        if get("org"):
            lines.append(f"ORG:{get('org')}")
        if get("title"):
            lines.append(f"TITLE:{get('title')}")
        if get("phone"):
            lines.append(f"TEL:{get('phone')}")
        if get("email"):
            lines.append(f"EMAIL:{get('email')}")
        if get("website"):
            lines.append(f"URL:{get('website')}")
        if get("address"):
            lines.append(f"ADR:;;{get('address')};;;;")
        if get("notes"):
            lines.append(f"NOTE:{get('notes')}")
        lines.append("END:VCARD")
        return "\n".join(lines)

    if kind == "UPI Payment":
        params = [("pa", get("pa")), ("pn", get("pn"))]
        if get("am"):
            params.append(("am", get("am")))
        params.append(("cu", "INR"))
        if get("tn"):
            params.append(("tn", get("tn")))
        query = "&".join(f"{key}={quote(value)}" for key, value in params if value)
        return f"upi://pay?{query}"

    if kind == "Location":
        coords = f"{get('lat')},{get('lng')}"
        label = get("label")
        return f"geo:{coords}?q={coords}({quote(label)})" if label else f"geo:{coords}"

    if kind == "Event":
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "BEGIN:VEVENT", f"SUMMARY:{get('title')}"]
        if get("location"):
            lines.append(f"LOCATION:{get('location')}")
        if get("start"):
            lines.append(f"DTSTART:{get('start')}")
        if get("end"):
            lines.append(f"DTEND:{get('end')}")
        if get("description"):
            lines.append(f"DESCRIPTION:{get('description')}")
        lines.extend(["END:VEVENT", "END:VCALENDAR"])
        return "\n".join(lines)

    if kind == "WhatsApp":
        number = "".join(ch for ch in get("number") if ch.isdigit())
        text = quote(get("message"))
        return f"https://wa.me/{number}?text={text}" if text else f"https://wa.me/{number}"

    if kind == "Crypto":
        scheme = "bitcoin" if (get("coin") or "Bitcoin") == "Bitcoin" else "ethereum"
        address, amount = get("address"), get("amount")
        if not amount:
            return f"{scheme}:{address}"
        param = "amount" if scheme == "bitcoin" else "value"
        return f"{scheme}:{address}?{param}={amount}"

    if kind == "Social":
        handle, platform = get("handle"), get("platform") or "Instagram"
        if handle.startswith("http"):
            return handle
        base = {
            "Instagram": "https://instagram.com/",
            "YouTube": "https://youtube.com/@",
            "LinkedIn": "https://linkedin.com/in/",
            "Facebook": "https://facebook.com/",
            "X (Twitter)": "https://x.com/",
        }.get(platform, "https://instagram.com/")
        return base + handle.lstrip("@")

    if kind == "App Store":
        app_id = get("app")
        if app_id.startswith("http"):
            return app_id
        if (get("store") or "Play Store") == "App Store":
            return f"https://apps.apple.com/app/id{app_id}"
        return f"https://play.google.com/store/apps/details?id={app_id}"

    if kind == "Smart Link":
        value = get("value")
        if value.startswith("http"):
            return value
        base = {
            "Telegram": "https://t.me/",
            "Zoom": "https://zoom.us/j/",
            "Spotify": "https://open.spotify.com/",
            "YouTube": "https://www.youtube.com/watch?v=",
        }.get(get("service") or "Telegram", "https://t.me/")
        return base + value

    return get("text")


def sign(content, key=SIGNING_KEY):
    digest = hmac.new(key.encode(), content.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{content}|SIG:{digest}"


def verify(signed, key=SIGNING_KEY):
    if "|SIG:" not in signed:
        return False
    content, signature = signed.rsplit("|SIG:", 1)
    expected = hmac.new(key.encode(), content.encode(), hashlib.sha256).hexdigest()[:16]
    return hmac.compare_digest(signature, expected)


def _query(text):
    if "?" not in text:
        return {}
    return parse_qs(text.split("?", 1)[1])


def detect(text):
    text = (text or "").strip()
    low = text.lower()
    if not text:
        return None, {}

    if low.startswith("wifi:"):
        parts = {}
        for chunk in text[5:].split(";"):
            if ":" in chunk:
                key, value = chunk.split(":", 1)
                parts[key.upper()] = value
        return "Wi-Fi", {
            "ssid": parts.get("S", ""),
            "password": parts.get("P", ""),
            "security": parts.get("T", "WPA") or "WPA",
            "hidden": "yes" if parts.get("H", "false").lower() in ("true", "1", "yes") else "no",
        }

    if low.startswith("mailto:"):
        query = _query(text)
        return "Email", {
            "to": text[7:].split("?", 1)[0],
            "subject": query.get("subject", [""])[0],
            "body": query.get("body", [""])[0],
        }

    if low.startswith("tel:"):
        return "Phone", {"number": text[4:]}

    if low.startswith("smsto:"):
        number, _, message = text[6:].partition(":")
        return "SMS", {"number": number, "message": message}

    if low.startswith("upi://"):
        query = _query(text)
        return "UPI Payment", {
            "pa": query.get("pa", [""])[0],
            "pn": query.get("pn", [""])[0],
            "am": query.get("am", [""])[0],
            "tn": query.get("tn", [""])[0],
        }

    if low.startswith("geo:"):
        coords = text[4:].split("?", 1)[0].split(",")
        if len(coords) == 2:
            return "Location", {"lat": coords[0], "lng": coords[1], "label": ""}
        return "Text", {"text": text}

    if low.startswith("bitcoin:"):
        return "Crypto", {"coin": "Bitcoin", "address": text[8:], "amount": ""}

    if low.startswith("ethereum:"):
        return "Crypto", {"coin": "Ethereum", "address": text[9:], "amount": ""}

    if "wa.me/" in low:
        number, _, query = text.split("wa.me/", 1)[1].partition("?")
        message = parse_qs(query).get("text", [""])[0] if query else ""
        return "WhatsApp", {"number": "".join(ch for ch in number if ch.isdigit()), "message": message}

    if low.startswith("http://") or low.startswith("https://"):
        return "URL", {"url": text}

    if "@" in text and " " not in text and len(text) > 3:
        return "Email", {"to": text, "subject": "", "body": ""}

    if text[0] in "+0123456789" and len(text) <= 20 and all(ch.isdigit() or ch in "+- ()." for ch in text):
        digits = "".join(ch for ch in text if ch.isdigit())
        if len(digits) >= 7:
            return "Phone", {"number": text}

    if " " not in text:
        host = text.split("/", 1)[0]
        if "." in host[1:-1] and host[-1].isalpha():
            return "URL", {"url": "https://" + text}

    return "Text", {"text": text}
