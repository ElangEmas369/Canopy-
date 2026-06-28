# MEXC Endpoint Routing — Decision Tree

## Confirmed Working (2026-06-24)

### api.mexc.com (PRIMARY — most reliable)
- Auth GET (`/api/v1/private/account/assets`, `/position/open_positions`) ✅
- Auth POST (`/api/v1/private/order/submit`) ✅
- Public GET (ticker, klines) ✅
- **Use this as default for all operations**

### contract.mexc.com (SECONDARY)
- Public GET (ticker, klines) ✅
- Auth GET ✅
- Auth POST ❌ (403 WAF block)
- **Use only for public data when api.mexc.com is down**

### CF Worker (DEAD — confirmed permanent 403)
- **Status: PERMANENTLY BLOCKED** (confirmed 2026-06-24)
- Returns 403 Forbidden on all requests
- URL: `https://mexc-proxy.refidsaputro369.workers.dev`
- **Do NOT use — switch to api.mexc.com direct**

### Regional Endpoints
| Endpoint | Status | Notes |
|----------|--------|-------|
| api.mexc.com | ✅ Primary | Works for all operations |
| api.mexc.kr | ✅ Works | Same as api.mexc.com |
| api.mexc.cc | ❌ 403 | Blocked |
| api.mexc.me | ❌ DNS | Doesn't resolve |
| api.mexc.sg | ❌ DNS | Doesn't resolve |

## MEXCClient Config

**Always use api.mexc.com direct:**
```python
CONFIG = {
    'cf_worker': 'https://api.mexc.com',
    'cf_worker_post': 'https://api.mexc.com',
    'cf_worker_fallback': ['https://contract.mexc.com'],
    ...
}
```

## Endpoint Decision Tree

```
Need to call MEXC?
├── Auth operation (balance, positions, orders)?
│   ├── api.mexc.com (always first)
│   ├── If 403/timeout → api.mexc.kr
│   └── If all fail → report "API unreachable"
├── Public operation (ticker, klines)?
│   ├── contract.mexc.com (fast)
│   ├── If fail → api.mexc.com
│   └── If all fail → report "Market data unreachable"
└── POST operation (open/close orders)?
    ├── api.mexc.com (always first)
    ├── If 403 → api.mexc.kr
    └── NEVER use contract.mexc.com for POST (WAF blocks)
```

## MEXC API Signature Format (v1 — use for futures)

```python
def sign(body=''):
    ts = str(int(time.time()*1000))
    sig = hmac.new(SECRET.encode(), (API_KEY+ts+body).encode(), hashlib.sha256).hexdigest()
    return {
        'ApiKey': API_KEY,
        'Request-Time': ts,
        'Signature': sig,
        'Content-Type': 'application/json'
    }
```

**v3 signature (X-MEXC-APIKEY, timestamp) does NOT work for futures** — returns 602 "Confirming signature failed"

## Key Lessons

1. **api.mexc.com is NOT dead** — previously documented as "404" but actually works for all operations
2. **contract.mexc.com blocks POST** — WAF returns 403 on any POST request
3. **CF Worker is permanently dead** — returns 403, do not use
4. **6026 is account-level** — no endpoint or proxy can bypass it
5. **Always backup before endpoint change** — `cp predator_v5.py predator_v5.py.bak.$(date +%s)`
6. **Error 8817** from `change_risk_level` — confirms risk control must be resolved through MEXC website/app, NOT API
