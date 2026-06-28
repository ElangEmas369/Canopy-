# Stop & Close: Emergency Bot Stop Script

## Working Pattern (2026-06-21)

The daily stopper cron must:
1. Close ALL open MEXC positions
2. Kill the bot process
3. Verify success

### Correct Script

```bash
cd /root/mexc-scalper && python3 -c "
import json, os, hmac, hashlib, time, requests
from urllib.parse import urlencode

# Load keys from project-local secrets
with open('secrets/api_keys.json') as f:
    keys = json.load(f)
active = [k for k in keys if k.get('status') == 'active' and k.get('type') == 'futures']
if not active:
    print('ERROR: No active futures key found')
    exit(1)
ak, sk = active[0]['api_key'], active[0]['api_secret']

# Get open positions
ts = str(int(time.time()*1000))
params = {'timestamp': ts}
qs = urlencode(params)
sig = hmac.new(sk.encode(), qs.encode(), hashlib.sha256).hexdigest()
headers = {'X-MEXC-APIKEY': ak}
r = requests.get(f'https://contract.mexc.com/api/v1/private/position/openPositions?{qs}&signature={sig}',
                 headers=headers, timeout=10)
data = r.json()
positions = data.get('data', []) or []
print(f'Found {len(positions)} open positions')

# Close each
for p in positions:
    cid = p.get('positionId')
    sym = p.get('symbol')
    if cid:
        params2 = {'positionId': cid, 'timestamp': ts}
        qs2 = urlencode(params2)
        sig2 = hmac.new(sk.encode(), qs2.encode(), hashlib.sha256).hexdigest()
        r2 = requests.post(f'https://contract.mexc.com/api/v1/private/position/close?{qs2}&signature={sig2}',
                          headers=headers, timeout=10)
        resp = r2.json()
        print(f'  Close {sym}: code={resp.get(\"code\")}')

# Verify
ts2 = str(int(time.time()*1000))
sig3 = hmac.new(sk.encode(), urlencode({'timestamp': ts2}).encode(), hashlib.sha256).hexdigest()
r3 = requests.get(f'https://contract.mexc.com/api/v1/private/position/openPositions?timestamp={ts2}&signature={sig3}',
                 headers=headers, timeout=10)
remaining = r3.json().get('data', []) or []
print(f'Remaining positions: {len(remaining)}')
"
```

### Then kill bot
```bash
# Kill bot process safely (avoid pkill -f self-match)
PIDS=$(ps aux | grep "[p]ython3.*predator_v5" | awk '{print $2}')
[ -n "$PIDS" ] && echo "$PIDS" | xargs kill -9 2>/dev/null
sleep 2
ps aux | grep "[p]ython3.*predator_v5" | grep -v grep || echo "STOPPED"
```

## Key Discoveries

| What | Wrong Assumption | Reality |
|------|-----------------|---------|
| Key location | `~/.hermes/.env` | `/root/mexc-scalper/secrets/api_keys.json` |
| Header | `ApiKey` (proxy) | `X-MEXC-APIKEY` (direct works) |
| Base URL | CF Worker proxy | `contract.mexc.com` direct works from server |
| Signing | `HMAC(secret, key+ts+body)` | `HMAC(secret, query_string)` for GET |
| `~/.hermes/secrets/` | Contains active key | May be stale or missing |

## Why the Original Stop Script Failed

The cron job template used:
```python
# WRONG: looks in ~/.hermes/.env for MEXC_ACCESS_KEY
env = {}
with open(os.path.expanduser('~/.hermes/.env')) as f:
    ...
ak, sk = env['MEXC_ACCESS_KEY'], env['MEXC_SECRET_KEY']
```
But `~/.hermes/.env` does NOT contain MEXC keys — it has OpenRouter, Telegram, Xiaomi keys. The MEXC keys live in the project-local secrets file.
