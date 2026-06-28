# MEXC Header Auth Confirmed — 2026-06-22

## Discovery

During session 2026-06-22, MEXC API signature 602 errors were investigated exhaustively.

**Root cause**: The MEXC API requires HEADER-based authentication, NOT query-param auth.

## Working Method (CONFIRMED)

```python
import hmac, hashlib, time, json, subprocess

api_key = open('/root/.hermes/secrets/mexc_api_key.txt').read().strip()
secret_key = open('/root/.hermes/secrets/mexc_secret_key.txt').read().strip()

ts = str(int(time.time() * 1000))
sig = hmac.new(secret_key.encode(), (api_key + ts).encode(), hashlib.sha256).hexdigest()

# Use HEADERS — this works
headers = {'ApiKey': api_key, 'Request-Time': ts, 'Signature': sig, 'Content-Type': application/json'}

# curl equivalent
cmd = ['curl', '-s', '-L', '-H', f'ApiKey: {api_key}', '-H', f'Request-Time: {ts}', 
       '-H', f'Signature: {sig}', 'https://api.mexc.com/api/v1/private/account/assets']
```

## Non-Working Methods (ALL return 602)

```python
# ❌ Query params — returns 602
url = f'https://api.mexc.com/api/v1/private/account/assets?api_key={ak}&timestamp={ts}&signature={sig}'
r = requests.get(url)

# ❌ X-MEXC-APIKEY header — wrong header name
headers = {'X-MEXC-APIKEY': ak}

# ❌ contract.mexc.com — 403 Cloudflare WAF from this server IP

# ❌ CF Worker proxy — DEAD (SSL reset)
```

## Response Field Names

The MEXC API returns these field names (NOT the ones you might expect):
- `currency` (NOT `asset`)
- `availableBalance` 
- `equity`
- `holdVol` for position volume (NOT `vol` or `volume`)
- `unrealized` for PnL (NOT `unrealizedPnl`)

## Test Results (2026-06-22 21:00 UTC)

```
Method A (headers):     code=0 success=True ✅
Method B (query params): code=602 ❌
Method C (other paths): 404/400 ❌

USDT Balance: available=$21.42 equity=$21.42
Open positions: 0
```

## Key Takeaway

**Always use HEADER-based auth for MEXC API. Never use query params.**
The bot's MEXCClient already does this correctly — it uses curl subprocess with `-H` headers.
