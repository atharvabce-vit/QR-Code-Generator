import hashlib
import hmac
from datetime import datetime, timezone
from urllib.parse import parse_qs, quote

SIGNING_KEY = "change-this-shared-secret"

WIFI_SPECIALS = "\\;,:\""


def _escape_wifi(value):
    out = []
    for ch in str(value or ""):
        if ch in WIFI_SPECIALS:
            out.append("\\")
        out.append(ch)
    return "".join(out)


def _unescape(value):
    out = []
    escaped = False
    for ch in str(value or ""):
        if escaped:
            out.append(ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        else:
            out.append(ch)
    if escaped:
        out.append("\\")
    return "".join(out)


def _split_escaped(text, separator):
    parts = []
    current = []
    escaped = False
    for ch in text:
        if escaped:
            current.append(ch)
            escaped = False
        elif ch == "\\":
            current.append(ch)
            escaped = True
        elif ch == separator:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    parts.append("".join(current))
    return parts


def _first_unescaped(text, char):
    escaped = False
    for index, ch in enumerate(text):
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == char:
            return index
    return -1


def _escape_text(value):
    text = str(value or "")
    text = text.replace("\\", "\\\\")
    text = text.replace(";", "\\;").replace(",", "\\,")
    text = text.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
    return text


def _take_bytes(text, limit):
    total = 0
    for index, ch in enumerate(text):
        size = len(ch.encode("utf-8"))
        if total + size > limit:
            return text[:index], text[index:]
        total += size
    return text, ""


def _fold(lines, limit=75):
    folded = []
    for line in lines:
        prefix = ""
        remaining = line
        while True:
            room = limit - len(prefix.encode("utf-8"))
            chunk, remaining = _take_bytes(remaining, room)
            folded.append(prefix + chunk)
            if not remaining:
                break
            prefix = " "
    return "\r\n".join(folded)


def _digest(*parts):
    joined = "\u0000".join(str(part or "") for part in parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]


def _utc_time(value):
    text = str(value or "").strip()
    if not text or text.endswith("Z"):
        return text
    return text + "Z"


def build(kind, values):
    get = lambda key: (values.get(key) or "").strip()

    if kind == "Text":
        return get("text")

    if kind == "URL":
        return get("url")

    if kind == "Email":
        to, cc, subject, body = get("to"), get("cc"), get("subject"), get("body")
        params = []
        if cc:
            params.append("cc=" + quote(cc))
        if subject:
            params.append("subject=" + quote(subject))
        if body:
            params.append("body=" + quote(body))
        query = "&".join(params)
        return f"mailto:{to}?{query}" if query else f"mailto:{to}"

    if kind == "Phone":
        return f"tel:{get('number')}"

    if kind == "SMS":
        number, message = get("number"), get("message")
        if (get("scheme") or "SMSTO").lower() == "sms":
            suffix = f"?body={quote(message)}" if message else ""
            return f"sms:{number}{suffix}"
        return f"SMSTO:{number}:{message}"

    if kind == "Wi-Fi":
        security = get("security") or "WPA"
        hidden = "true" if get("hidden").lower() in ("yes", "true", "1") else "false"
        ssid = _escape_wifi(get("ssid"))
        password = _escape_wifi(get("password"))
        return f"WIFI:T:{security};S:{ssid};P:{password};H:{hidden};;"

    if kind == "Contact":
        name = get("name")
        tokens = name.split()
        if len(tokens) > 1:
            family, given = tokens[-1], " ".join(tokens[:-1])
        else:
            family, given = "", name
        lines = [
            "BEGIN:VCARD",
            "VERSION:3.0",
            f"N:{_escape_text(family)};{_escape_text(given)};;;",
            f"FN:{_escape_text(name)}",
        ]
        if get("org"):
            lines.append(f"ORG:{_escape_text(get('org'))}")
        if get("title"):
            lines.append(f"TITLE:{_escape_text(get('title'))}")
        if get("phone"):
            lines.append(f"TEL:{_escape_text(get('phone'))}")
        if get("email"):
            lines.append(f"EMAIL:{_escape_text(get('email'))}")
        if get("website"):
            lines.append(f"URL:{_escape_text(get('website'))}")
        if get("address"):
            lines.append(f"ADR:;;{_escape_text(get('address'))};;;;")
        if get("notes"):
            lines.append(f"NOTE:{_escape_text(get('notes'))}")
        lines.append(f"UID:{_digest('vcard', name, get('email'), get('phone'))}@qrcode")
        lines.append("END:VCARD")
        return _fold(lines)

    if kind == "UPI Payment":
        params = [("pa", get("pa")), ("pn", get("pn"))]
        if get("tn"):
            params.append(("tn", get("tn")))
        if get("am"):
            params.append(("am", get("am")))
        params.append(("cu", "INR"))
        query = "&".join(f"{key}={quote(value, safe='@')}" for key, value in params if value)
        return f"upi://pay?{query}"

    if kind == "Location":
        coords = f"{get('lat')},{get('lng')}"
        label = get("label")
        return f"geo:{coords}?q={coords}({quote(label)})" if label else f"geo:{coords}"

    if kind == "Event":
        start = _utc_time(get("start"))
        end = _utc_time(get("end"))
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        uid = f"{_digest('event', get('title'), get('location'), start, end)}@qrcode"
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//QR Code Generator//EN",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{stamp}",
            f"SUMMARY:{_escape_text(get('title'))}",
        ]
        if get("location"):
            lines.append(f"LOCATION:{_escape_text(get('location'))}")
        if start:
            lines.append(f"DTSTART:{start}")
        if end:
            lines.append(f"DTEND:{end}")
        if get("description"):
            lines.append(f"DESCRIPTION:{_escape_text(get('description'))}")
        lines.extend(["END:VEVENT", "END:VCALENDAR"])
        return _fold(lines)

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
            "Google Meet": "https://meet.google.com/",
            "Discord": "https://discord.gg/",
        }.get(get("service") or "Telegram", "https://t.me/")
        return base + value

    if kind == "Maps":
        destination = quote(get("destination"))
        origin = quote(get("origin"))
        url = f"https://www.google.com/maps/dir/?api=1&destination={destination}&travelmode={get('mode') or 'driving'}"
        if origin:
            url += f"&origin={origin}"
        return url

    if kind == "PayPal":
        handle = get("handle")
        if handle.startswith("http"):
            return handle
        link = "https://paypal.me/" + handle.lstrip("@").strip("/")
        if get("amount"):
            link += f"/{get('amount')}{get('currency') or 'USD'}"
        return link

    if kind == "MECARD":
        parts = [f"MECARD:N:{_escape_text(get('name'))}"]
        if get("phone"):
            parts.append(f"TEL:{_escape_text(get('phone'))}")
        if get("email"):
            parts.append(f"EMAIL:{_escape_text(get('email'))}")
        if get("org"):
            parts.append(f"ORG:{_escape_text(get('org'))}")
        if get("url"):
            parts.append(f"URL:{_escape_text(get('url'))}")
        return ";".join(parts) + ";;"

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
        for chunk in _split_escaped(text[5:], ";"):
            index = _first_unescaped(chunk, ":")
            if index == -1:
                continue
            parts[chunk[:index].strip().upper()] = _unescape(chunk[index + 1:])
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
            "cc": query.get("cc", [""])[0],
            "subject": query.get("subject", [""])[0],
            "body": query.get("body", [""])[0],
        }

    if low.startswith("tel:"):
        return "Phone", {"number": text[4:]}

    if low.startswith("smsto:"):
        number, _, message = text[6:].partition(":")
        return "SMS", {"number": number, "message": message, "scheme": "SMSTO"}

    if low.startswith("sms:"):
        number, _, query = text[4:].partition("?")
        message = parse_qs(query).get("body", [""])[0] if query else ""
        return "SMS", {"number": number, "message": message, "scheme": "sms"}

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

    if low.startswith("mecard:"):
        parts = {}
        for chunk in text[7:].split(";"):
            key, _, value = chunk.partition(":")
            if key.strip():
                parts[key.strip().upper()] = _unescape(value)
        return "MECARD", {
            "name": parts.get("N", ""),
            "phone": parts.get("TEL", ""),
            "email": parts.get("EMAIL", ""),
            "org": parts.get("ORG", ""),
            "url": parts.get("URL", ""),
        }

    if "paypal.me/" in low:
        handle = text.split("paypal.me/", 1)[1].split("?", 1)[0]
        return "PayPal", {"handle": handle, "amount": "", "currency": "USD"}

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
