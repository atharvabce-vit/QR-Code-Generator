import hashlib
import hmac

FIELDS = [
    "pnr",
    "name",
    "train_no",
    "train_name",
    "coach",
    "seat",
    "source",
    "destination",
    "date",
    "status",
    "fare",
]

SECRET = "change-this-shared-secret"


class Ticket:
    def __init__(self, **values):
        for field in FIELDS:
            setattr(self, field, str(values.get(field, "") or "").strip())

    def get(self, field):
        return getattr(self, field, "")

    def body(self):
        return "|".join(self.get(field) for field in FIELDS)

    def signature(self, secret=SECRET):
        digest = hmac.new(secret.encode(), self.body().encode(), hashlib.sha256)
        return digest.hexdigest()[:16]

    def payload(self, secret=SECRET):
        return f"TICKET|{self.body()}|{self.signature(secret)}"

    def as_dict(self):
        return {field: self.get(field) for field in FIELDS}


def verify_payload(payload, secret=SECRET):
    parts = payload.split("|")
    if len(parts) != len(FIELDS) + 2 or parts[0] != "TICKET":
        return False
    body = "|".join(parts[1:-1])
    expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()[:16]
    return hmac.compare_digest(parts[-1], expected)


def safe_name(text, limit=60):
    cleaned = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in text).strip("_")
    return cleaned[:limit] or "ticket"
