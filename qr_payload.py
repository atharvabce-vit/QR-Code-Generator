import hashlib
import hmac
from urllib.parse import quote

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
        lines.append("END:VCARD")
        return "\n".join(lines)

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
