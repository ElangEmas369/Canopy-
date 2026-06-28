# State File Desync — Diagnosis & Fix (2026-06-25)

## Problem
Three state files can have completely different data, causing confusion and incorrect decisions.

## The Three Files
1. `~/.hermes/data/predator_v5_state.json` — PRIMARY (bot reads/writes here)
2. `/root/mexc-scalper/state/state.json` — SECONDARY (often stale)
3. `/root/mexc-scalper/shared_state.json` — SNAPSHOT (very old)

## Example Desync (2026-06-25)
```
PRIMARY:   capital=$5.72, paused=true, positions=0
SECONDARY: capital=$17.7, paused=false, positions=1 (BTC_USDT)
SHARED:    capital=$20.85, positions=0
MEXC ACTUAL: equity=$5.79, positions=1 (S_USDT SHORT)
```

## Root Cause
- Bot writes to PRIMARY on events (trade open/close, state change)
- SECONDARY updated less frequently
- SHARED updated on heartbeat (~5s)
- Old bot sessions leave stale data in SECONDARY/SHARED
- Manual edits to one file don't propagate to others

## Diagnosis
Always check ALL 3 files + MEXC API actual:

```python
import json, time, hmac, hashlib, urllib.request, ssl

# Check MEXC actual
k = open('/root/.hermes/secrets/mexc_api_key.txt').read().strip()
s = open('/root/.hermes/secrets/mexc_secret_key.txt').read().strip()
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

ts = str(int(time.time()*1000))
sig = hmac.new(s.encode(), (k+ts).encode(), hashlib.sha256).hexdigest()
req = urllib.request.Request('https://contract.mexc.com/api/v1/private/account/assets',
    headers={'ApiKey':k, 'Request-Time':ts, 'Signature':sig, 'Content-Type':'application/json'})
resp = urllib.request.urlopen(req, timeout=15, context=ctx)
data = json.loads(resp.read())
for a in data.get('data', []):
    if a['currency'] == 'USDT':
        print(f"MEXC: equity={a['equity']} avail={a['availableBalance']}")

# Check all 3 files
for path in ['~/.hermes/data/predator_v5_state.json', 
             '/root/mexc-scalper/state/state.json',
             '/root/mexc-scalper/shared_state.json']:
    try:
        d = json.load(open(path))
        cap = d.get('risk', {}).get('capital') or d.get('capital', '?')
        paused = d.get('risk', {}).get('paused', '?')
        print(f"{path}: capital=${cap} paused={paused}")
    except:
        print(f"{path}: ERROR")
```

## Fix Procedure
1. Kill bot with SIGKILL (-9) — NOT SIGTERM
2. Get MEXC actual balance and positions
3. Update ALL 3 files with same data
4. Restart bot

```bash
# 1. Kill
kill -9 $(pgrep -f "predator_v5.py")

# 2. Sync
python3 << 'EOF'
import json, time, hmac, hashlib, urllib.request, ssl

# Get MEXC actual
k = open('/root/.hermes/secrets/mexc_api_key.txt').read().strip()
s = open('/root/.hermes/secrets/mexc_secret_key.txt').read().strip()
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

ts = str(int(time.time()*1000))
sig = hmac.new(s.encode(), (k+ts).encode(), hashlib.sha256).hexdigest()
req = urllib.request.Request('https://contract.mexc.com/api/v1/private/account/assets',
    headers={'ApiKey':k, 'Request-Time':ts, 'Signature':sig, 'Content-Type':'application/json'})
resp = urllib.request.urlopen(req, timeout=15, context=ctx)
data = json.loads(resp.read())
equity = 0
for a in data.get('data', []):
    if a['currency'] == 'USDT':
        equity = float(a['equity'])

# Get positions
ts2 = str(int(time.time()*1000))
sig2 = hmac.new(s.encode(), (k+ts2).encode(), hashlib.sha256).hexdigest()
req2 = urllib.request.Request('https://contract.mexc.com/api/v1/private/position/open_positions',
    headers={'ApiKey':k, 'Request-Time':ts2, 'Signature':sig2, 'Content-Type':'application/json'})
resp2 = urllib.request.urlopen(req2, timeout=15, context=ctx)
pos_data = json.loads(resp2.read())
positions = []
for p in pos_data.get('data', []):
    positions.append({
        'symbol': p.get('symbol'),
        'side': 'SHORT' if p.get('positionType') == 2 else 'LONG',
        'entry_price': float(p.get('openAvgPrice', 0)),
        'volume': p.get('holdVol'),
        'unrealized_pnl': float(p.get('profitRatio', 0))
    })

# Update PRIMARY
state_path = '/root/.hermes/data/predator_v5_state.json'
try:
    with open(state_path) as f:
        state = json.load(f)
except:
    state = {}

state['risk'] = state.get('risk', {})
state['risk']['capital'] = equity
state['risk']['paused'] = False
state['risk']['pause_reason'] = None
state['risk']['consecutive_sl'] = 0
state['open_positions'] = positions
state['balance'] = equity
state['last_update'] = time.time()

with open(state_path, 'w') as f:
    json.dump(state, f, indent=2)

print(f"✅ PRIMARY: capital=${equity:.4f} positions={len(positions)}")
EOF

# 3. Restart
# Use terminal(background=True) in Hermes
```

## Prevention
- Always use SIGKILL (-9) when manually editing state files
- Check MEXC API actual before making decisions based on state files
- Don't trust SECONDARY or SHARED files — they may be stale
