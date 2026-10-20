# Transactions Dashboard — Interview Starter

You can build the frontend in **any language or framework**. This kit gives you a
running mock API and two optional starters.

## Before the interview (5 minutes)

You need **Python 3.9+** to run the mock API (standard library only, nothing to install), whatever stack you use for the UI.

```bash
cd mock-api
python3 server.py
```

You should see `Mock API on http://localhost:4000`. Check it:
<http://localhost:4000/api/health>

Then set up your frontend so it can call `http://localhost:4000/api/...`
(CORS is open to every origin). Please make sure a "hello world" page in your
chosen stack runs **before** the interview.

## Starters (optional)

| Starter | Run | Notes |
|---|---|---|
| Plain HTML/JS | Open <http://localhost:4000/> | No install. Edit `starters/vanilla/index.html` and refresh. |
| React + Vite | `cd starters/react && npm install && npm run dev` → <http://localhost:5173> | Needs Node 18+. `/api` is proxied to the mock API. |
| Anything else | Your own project | Call `http://localhost:4000/api/...` directly. |

## API reference

All responses are JSON. Errors look like `{ "error": "code", "message": "..." }`.

### Transaction object

```json
{
  "id": 42,
  "reference": "TXN-26-332598",
  "customer_name": "Ngozi Bello",
  "amount": "1250000.50",
  "currency": "NGN",
  "status": "Flagged",
  "flag_reason": "New beneficiary",
  "created_at": "2026-10-12T14:03:11.000Z",
  "reviewed_by": null,
  "reviewed_at": null,
  "version": 1
}
```

`status` is one of `Pending`, `Completed`, `Flagged`, `Reviewed`.
`amount` is a decimal **string**, so there are no floating-point rounding errors.

### Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/transactions` | List. Query: `q` (reference contains), `status`, `page` (default 1), `page_size` (default 50, max 500) |
| GET | `/api/transactions/:id` | One transaction, or 404 |
| GET | `/api/transactions/:id/history` | Review/audit history for a transaction |
| POST | `/api/transactions/:id/review` | Mark as reviewed (see below) |
| GET | `/api/health` | Health check |

**List response**

```json
{ "data": [ ... ], "page": 1, "page_size": 50, "total": 250, "total_pages": 5 }
```

For **client-side** pagination, fetch everything with `?page_size=500`.

**Review request**

```http
POST /api/transactions/42/review
Content-Type: application/json
X-User: your.name@ops.demo

{ "version": 1, "note": "Checked with customer" }
```

| Status | Meaning |
|---|---|
| 200 | `{ "transaction": { ...updated } }` |
| 403 | Caller isn't allowed to review (send `X-Role: viewer` to see this) |
| 404 | Transaction not found |
| 409 | `already_reviewed`, or `version_conflict` if `version` doesn't match. The current transaction is in the body. |

`version` is optional; send it to get optimistic-concurrency checks.

### Simulating slow or failing requests

Add these to any `/api` request:

- `?delay=3000` — respond after 3 seconds
- `?fail=500` — force that error status

Or start the server with `FAIL_RATE=0.2 python3 server.py` (20% of requests fail),
or `LATENCY_MS=1500 python3 server.py`. On Windows, set the variable first (`set FAIL_RATE=0.2` in cmd, `$env:FAIL_RATE=0.2` in PowerShell); use `python` if `python3` isn't found.

`POST /api/_reset` restores the original data.
