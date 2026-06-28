# Auth GET Routing Fix — 2026-06-23

## Problem
`MEXCClient.get()` always routed through CF Worker proxy (`mexc-proxy.refidsaputro369.workers.dev`), including authenticated calls to private endpoints like `/api/v1/private/account/assets` and `/api/v1/private/position/open_positions`. These returned **HTTP 403 Forbidden** via proxy.

## Root Cause
CF Worker proxy only handles **public** endpoints (ticker, kline, depth, contract info). Private/authenticated endpoints require direct access to `https://api.mexc.com`.

## Fix
In `MEXCClient.get()`, route based on `auth` parameter:
```python
def get(self, path, auth=False):
    base = 'https://api.mexc.com' if auth else self.base_url
    url = f"{base}{path}"
    ...
```

## Verification
```bash
# Public GET via proxy — works
python3 -c "import urllib.request,ssl,json; ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE; r=urllib.request.urlopen(urllib.request.Request('https://mexc-proxy.refidsaputro369.workers.dev/api/v1/contract/ticker?symbol=BTC_USDT',headers={'User-Agent':'Mozilla/5.0'}),timeout=15,context=ctx); print(json.loads(r.read().decode())['data'][0]['lastPrice'])"

# Auth GET direct — works (api.mexc.com)
# Auth GET via proxy — FAILS 403 (do NOT use for private endpoints)
```

## Lesson
When bot balance shows stale data or sync fails, check if `get_balance()` is routing through proxy. The fix is in MEXCClient.get() — auth calls must go direct.
