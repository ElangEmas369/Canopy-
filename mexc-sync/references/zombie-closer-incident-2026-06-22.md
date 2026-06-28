# Zombie Closer Incident — 2026-06-22

## What Happened

The `zombie_closer.py` cron job crashed with `JSONDecodeError` when trying to close zombie positions.

## Root Cause

The script called `r.json()` on the response from `POST /api/v1/private/order/submit` without checking:
1. HTTP status code (was **403 Access Denied** — HTML body, not JSON)
2. Response body was empty/non-JSON

MEXC's WAF blocks the order-submission POST endpoint from this server IP, while GET endpoints (positions, balance) work fine.

## Positions Detected

| Symbol | Side | Volume | Entry | PNL |
|--------|------|--------|-------|-----|
| CRV_USDT | SHORT | 6,483 | 0.2086 | -$0.10 |
| CSPR_USDT | LONG | 5,025 | 0.002128 | -$0.01 |

Both were zombies (MEXC had them open, bot state had 0 tracked trades).

## Fix Applied to `zombie_closer.py`

```python
# BEFORE (crashes on non-JSON response):
r = requests.post(...)
return r.json()

# AFTER (defensive):
r = requests.post(...)
if r.status_code != 200 or not r.text.strip():
    print(f'  WARN: close returned status={r.status_code} body={r.text[:200]}')
    return None
try:
    return r.json()
except json.JSONDecodeError:
    print(f'  WARN: close returned non-JSON: {r.text[:200]}')
    return None
```

Also fixed caller to handle `None` return instead of passing it to `json.dumps()`.

## MEXC API Behavior Update

| Endpoint | Method | Status from server |
|----------|--------|--------------------|
| `/api/v1/private/position/open_positions` | GET | ✅ Works (200) |
| `/api/v1/private/account/assets` | GET | ✅ Works (200) |
| `/api/v1/private/order/submit` | POST | ❌ **403 Access Denied** (WAF blocked) |

## Recommended Close Strategy

Since `order/submit` is blocked, use one of these alternatives:

1. **`close_all` endpoint** — `POST /api/v1/private/position/close_all` with empty body (mentioned in skill)
2. **Direct `position/close`** — `POST /api/v1/private/position/close` with `X-MEXC-APIKEY` signing (query-param style, see stop-and-close-script.md)

## Balance Drift

- MEXC equity at incident time: **$17.34**
- State capital before sync: **$22.47**
- Drift: **$5.12** (synced after detection)
