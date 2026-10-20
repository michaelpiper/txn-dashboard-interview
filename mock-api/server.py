#!/usr/bin/env python3
"""Mock transactions API for the full-stack interview.

Standard library only — run with `python3 server.py` (Python 3.9+).

Env vars:
  PORT=4000          port to listen on
  LATENCY_MS=300     artificial delay on every /api request
  FAIL_RATE=0        0..1 chance that any /api request returns 500
  COUNT=250          number of seeded transactions

Per-request overrides (handy for demos):
  ?delay=3000        override latency for this request
  ?fail=500          force this status code for this request
"""

import json
import os
import random
import re
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PORT = int(os.environ.get("PORT", 4000))
LATENCY_MS = int(os.environ.get("LATENCY_MS", 300))
FAIL_RATE = float(os.environ.get("FAIL_RATE", 0))
COUNT = int(os.environ.get("COUNT", 250))
MAX_PAGE_SIZE = 500

STATUSES = ["Pending", "Completed", "Flagged", "Reviewed"]
FIRST = ["Adaeze", "Bola", "Chinedu", "Damilola", "Emeka", "Funmi", "Garba", "Halima", "Ifeanyi", "Jumoke", "Kelechi",
         "Lami", "Musa", "Ngozi", "Olu", "Kemi", "Segun", "Tobi", "Uche", "Yetunde", "Zainab"]
LAST = ["Okafor", "Adeyemi", "Bello", "Eze", "Ibrahim", "Okon", "Balogun", "Nwosu", "Abubakar", "Ogunleye", "Danjuma",
        "Obi", "Lawal", "Chukwu"]
ANALYSTS = ["amina.yusuf@ops.demo", "tunde.bakare@ops.demo", "grace.okon@ops.demo"]
FLAG_REASONS = ["Amount above threshold", "Unusual time of day", "New beneficiary", "Velocity check", "Name mismatch"]

STARTER = Path(__file__).resolve().parent.parent / "starters" / "vanilla" / "index.html"

# In-memory store. The lock makes check-then-update on review atomic across request threads.
lock = threading.Lock()
transactions = []
history = []
next_history_id = 1


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def seed():
    global transactions, history, next_history_id
    state = {"s": 20261020}

    def rand():
        state["s"] = (state["s"] * 1664525 + 1013904223) & 0xFFFFFFFF
        return state["s"] / 2**32

    def pick(items):
        return items[int(rand() * len(items))]

    now = int(datetime(2026, 10, 20, 9, tzinfo=timezone.utc).timestamp() * 1000)
    txs, hist, hid = [], [], 1

    for i in range(1, COUNT + 1):
        r = rand()
        status = "Pending" if r < 0.35 else "Completed" if r < 0.75 else "Flagged" if r < 0.9 else "Reviewed"
        created_ms = now - int(rand() * 60 * 86400000)
        currency = "NGN" if rand() < 0.9 else "USD"
        # Amounts are generated in minor units and returned as decimal strings (no float money).
        minor = int(rand() * 500000000) + 1000 if currency == "NGN" else int(rand() * 2000000) + 100

        tx = {
            "id": i,
            "reference": f"TXN-26-{(i * 7919) % 1000000:06d}",
            "customer_name": f"{pick(FIRST)} {pick(LAST)}",
            "amount": f"{minor // 100}.{minor % 100:02d}",
            "currency": currency,
            "status": status,
            "flag_reason": pick(FLAG_REASONS) if status == "Flagged" else None,
            "created_at": iso(created_ms),
            "reviewed_by": None,
            "reviewed_at": None,
            "version": 1,
        }

        if status == "Reviewed":
            tx["reviewed_by"] = pick(ANALYSTS)
            tx["reviewed_at"] = iso(created_ms + int(rand() * 48 * 3600000))
            tx["version"] = 2
            hist.append({
                "id": hid,
                "transaction_id": i,
                "action": "reviewed",
                "actor": tx["reviewed_by"],
                "at": tx["reviewed_at"],
                "from_status": "Flagged",
                "to_status": "Reviewed",
                "note": None,
            })
            hid += 1
        txs.append(tx)

    txs.sort(key=lambda t: t["created_at"], reverse=True)
    with lock:
        transactions, history, next_history_id = txs, hist, hid


CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,X-User,X-Role,If-Match",
}

TX_ROUTE = re.compile(r"^/api/transactions/(\d+)(/history|/review)?$")


class BadRequest(Exception):
    pass


class Handler(BaseHTTPRequestHandler):
    server_version = "MockTransactionsAPI/1.0"

    # ---- helpers -------------------------------------------------------

    def send_json(self, status, body):
        payload = json.dumps(body, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        for k, v in CORS.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)

    def read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > 100_000:
            raise BadRequest("Body too large")
        if not length:
            return {}
        try:
            body = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            raise BadRequest("Invalid JSON")
        if not isinstance(body, dict):
            raise BadRequest("Body must be a JSON object")
        return body

    def log_message(self, fmt, *args):
        print(f"{self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")

    # ---- HTTP verbs ----------------------------------------------------

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in CORS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        self.dispatch()

    def do_POST(self):
        self.dispatch()

    def dispatch(self):
        url = urlparse(self.path)
        query = {k: v[-1] for k, v in parse_qs(url.query).items()}

        if self.command == "GET" and url.path == "/":
            html = STARTER.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return

        if not url.path.startswith("/api/"):
            return self.send_json(404, {"error": "not_found"})

        try:
            self.handle_api(url.path, query)
        except Exception as e:  # noqa: BLE001 — a mock API should never crash the demo
            print("Unexpected error:", repr(e))
            self.send_json(500, {"error": "internal_error", "message": "Unexpected error"})

    # ---- API -----------------------------------------------------------

    def handle_api(self, path, query):
        if self.command == "GET" and path == "/api/health":
            return self.send_json(200, {"ok": True, "count": len(transactions)})
        if self.command == "POST" and path == "/api/_reset":
            seed()
            return self.send_json(200, {"ok": True, "count": len(transactions)})

        try:
            delay = int(query.get("delay", LATENCY_MS))
        except ValueError:
            delay = LATENCY_MS
        time.sleep(max(0, delay) / 1000)

        forced = query.get("fail", "")
        if forced.isdigit() and int(forced) >= 400:
            return self.send_json(int(forced), {"error": "simulated_failure", "message": f"Forced {forced} via ?fail"})
        if random.random() < FAIL_RATE:
            return self.send_json(500, {"error": "internal_error", "message": "Simulated server error"})

        if self.command == "GET" and path == "/api/transactions":
            return self.list_transactions(query)

        m = TX_ROUTE.match(path)
        if m:
            tx_id, sub = int(m.group(1)), m.group(2)
            tx = next((t for t in transactions if t["id"] == tx_id), None)
            if tx is None:
                return self.send_json(404, {"error": "not_found", "message": f"Transaction {tx_id} not found"})
            if self.command == "GET" and not sub:
                return self.send_json(200, tx)
            if self.command == "GET" and sub == "/history":
                return self.send_json(200, {"data": [h for h in history if h["transaction_id"] == tx_id]})
            if self.command == "POST" and sub == "/review":
                return self.review_transaction(tx)

        self.send_json(404, {"error": "not_found", "message": f"No route for {self.command} {path}"})

    def list_transactions(self, query):
        q = query.get("q", "").strip().lower()
        status = query.get("status", "")
        try:
            page = int(query.get("page", 1))
            page_size = int(query.get("page_size", 50))
        except ValueError:
            page = page_size = 0

        if status and status not in STATUSES:
            return self.send_json(400, {"error": "invalid_status",
                                        "message": f"status must be one of {', '.join(STATUSES)}"})
        if page < 1 or not 1 <= page_size <= MAX_PAGE_SIZE:
            return self.send_json(400, {"error": "invalid_pagination",
                                        "message": f"page >= 1, 1 <= page_size <= {MAX_PAGE_SIZE}"})

        rows = [t for t in transactions
                if (not q or q in t["reference"].lower()) and (not status or t["status"] == status)]
        total = len(rows)
        self.send_json(200, {
            "data": rows[(page - 1) * page_size: page * page_size],
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(1, -(-total // page_size)),
        })

    def review_transaction(self, tx):
        global next_history_id
        role = self.headers.get("X-Role", "analyst")
        if role not in ("analyst", "admin"):
            return self.send_json(403, {"error": "forbidden", "message": "Only analysts can review transactions"})

        try:
            body = self.read_body()
        except BadRequest as e:
            return self.send_json(400, {"error": "bad_request", "message": str(e)})

        actor = self.headers.get("X-User") or body.get("reviewer") or "analyst@ops.demo"
        expected = body.get("version", self.headers.get("If-Match"))
        note = body.get("note")

        with lock:
            if tx["status"] == "Reviewed":
                return self.send_json(409, {"error": "already_reviewed",
                                            "message": f"Already reviewed by {tx['reviewed_by']}", "transaction": tx})
            try:
                stale = expected is not None and int(expected) != tx["version"]
            except (TypeError, ValueError):
                stale = True
            if stale:
                return self.send_json(409, {"error": "version_conflict",
                                            "message": "Transaction changed since you loaded it", "transaction": tx})

            at = iso(time.time() * 1000)
            history.append({
                "id": next_history_id,
                "transaction_id": tx["id"],
                "action": "reviewed",
                "actor": actor,
                "at": at,
                "from_status": tx["status"],
                "to_status": "Reviewed",
                "note": note[:500] if isinstance(note, str) else None,
            })
            next_history_id += 1
            tx.update(status="Reviewed", reviewed_by=actor, reviewed_at=at, version=tx["version"] + 1)
            self.send_json(200, {"transaction": tx})


if __name__ == "__main__":
    seed()
    server = ThreadingHTTPServer(("", PORT), Handler)
    print(f"Mock API on http://localhost:{PORT}  ({len(transactions)} transactions, "
          f"latency {LATENCY_MS}ms, fail rate {FAIL_RATE})")
    print(f"Plain-HTML starter: http://localhost:{PORT}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
