import http.server
import os
import secrets
import socket
import sqlite3
import threading
from datetime import datetime, timezone
from urllib.parse import urlparse

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qr_links.db")

ALPHABET = "abcdefghijkmnpqrstuvwxyz23456789"


def connect(path=None):
    conn = sqlite3.connect(path or DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS links ("
        "code TEXT PRIMARY KEY, target TEXT NOT NULL, label TEXT, "
        "created TEXT, active INTEGER DEFAULT 1)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS scans ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, ts TEXT, "
        "agent TEXT, ip TEXT, referer TEXT)"
    )
    conn.commit()
    return conn


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _new_code(conn):
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(6))
        if not conn.execute("SELECT 1 FROM links WHERE code = ?", (code,)).fetchone():
            return code


def add_link(target, label="", path=None):
    conn = connect(path)
    try:
        code = _new_code(conn)
        conn.execute(
            "INSERT INTO links (code, target, label, created, active) VALUES (?, ?, ?, ?, 1)",
            (code, target, label, _now()),
        )
        conn.commit()
        return code
    finally:
        conn.close()


def lookup(code, path=None):
    conn = connect(path)
    try:
        row = conn.execute("SELECT target, active FROM links WHERE code = ?", (code,)).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return {"target": row[0], "active": bool(row[1])}


def list_links(path=None):
    conn = connect(path)
    try:
        rows = conn.execute(
            "SELECT l.code, l.target, l.label, l.created, l.active, "
            "(SELECT COUNT(*) FROM scans s WHERE s.code = l.code) "
            "FROM links l ORDER BY l.created DESC"
        ).fetchall()
    finally:
        conn.close()
    return [
        {"code": row[0], "target": row[1], "label": row[2] or "", "created": row[3],
         "active": bool(row[4]), "scans": row[5]}
        for row in rows
    ]


def update_target(code, target, path=None):
    conn = connect(path)
    try:
        conn.execute("UPDATE links SET target = ? WHERE code = ?", (target, code))
        conn.commit()
    finally:
        conn.close()


def set_active(code, active, path=None):
    conn = connect(path)
    try:
        conn.execute("UPDATE links SET active = ? WHERE code = ?", (1 if active else 0, code))
        conn.commit()
    finally:
        conn.close()


def delete_link(code, path=None):
    conn = connect(path)
    try:
        conn.execute("DELETE FROM links WHERE code = ?", (code,))
        conn.execute("DELETE FROM scans WHERE code = ?", (code,))
        conn.commit()
    finally:
        conn.close()


def record_scan(code, agent="", ip="", referer="", path=None):
    conn = connect(path)
    try:
        conn.execute(
            "INSERT INTO scans (code, ts, agent, ip, referer) VALUES (?, ?, ?, ?, ?)",
            (code, _now(), agent, ip, referer),
        )
        conn.commit()
    finally:
        conn.close()


def scans_by_day(code=None, path=None):
    conn = connect(path)
    try:
        if code:
            rows = conn.execute(
                "SELECT substr(ts, 1, 10) AS day, COUNT(*) FROM scans WHERE code = ? GROUP BY day ORDER BY day",
                (code,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT substr(ts, 1, 10) AS day, COUNT(*) FROM scans GROUP BY day ORDER BY day"
            ).fetchall()
    finally:
        conn.close()
    return [{"date": row[0], "count": row[1]} for row in rows]


def local_ip():
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


PAGE = (
    "<!doctype html><html><head><meta charset=\"utf-8\"><title>Dynamic QR links</title>"
    "<style>body{{font-family:system-ui,Segoe UI,Arial;margin:40px;background:#0b0b0b;color:#e5e7eb}}"
    "a{{color:#60a5fa}}table{{border-collapse:collapse;width:100%}}"
    "td,th{{padding:8px 12px;border-bottom:1px solid #333;text-align:left}}</style></head>"
    "<body><h1>Dynamic QR links</h1><p>{count} link(s)</p>"
    "<table><tr><th>Code</th><th>Target</th><th>Scans</th></tr>{rows}</table></body></html>"
)


class _Handler(http.server.BaseHTTPRequestHandler):
    db_path = DB_PATH

    def log_message(self, *_args):
        return

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/r/"):
            code = path[3:].strip("/").split("/")[0]
            link = lookup(code, self.db_path)
            if not link:
                self._send(404, "Link not found")
                return
            if not link["active"]:
                self._send(410, "This link is disabled")
                return
            record_scan(code, self.headers.get("User-Agent", ""), self.client_address[0],
                        self.headers.get("Referer", ""), self.db_path)
            self.send_response(302)
            self.send_header("Location", link["target"])
            self.end_headers()
            return
        if path in ("/", "/index.html"):
            self._send(200, self._index(), "text/html; charset=utf-8")
            return
        self._send(404, "Not found")

    def _index(self):
        links = list_links(self.db_path)
        rows = "".join(
            f'<tr><td><a href="/r/{link["code"]}">{link["code"]}</a></td>'
            f'<td>{link["target"]}</td><td>{link["scans"]}</td></tr>'
            for link in links
        )
        return PAGE.format(count=len(links), rows=rows or '<tr><td colspan="3">No links yet</td></tr>')

    def _send(self, status, body, content_type="text/plain; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def start_server(port=8080, host="0.0.0.0", db_path=None):
    handler = type("BoundHandler", (_Handler,), {"db_path": db_path or DB_PATH})
    server = http.server.ThreadingHTTPServer((host, int(port)), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread
