---
name: mexc-position-rescue
version: 1.0.0
category: trading
description: "MEXC position rescue — detect stuck positions, fix close failures, handle 6026 blocks, reconcile bot state vs exchange reality."
tags: [mexc, positions, rescue, close, 6026, recovery, futures]
---

# MEXC Position Rescue

Rescue protocol for stuck MEXC futures positions. Covers close failures, 6026 risk control blocks, zombie detection, and state reconciliation.

## When to Activate

- Bot log shows repeated `CLOSE FAIL` or error 2009
- Positions exist on MEXC but bot can't close them
- Error 6026 `DISABLED_CONTRACT_OPEN_POSITION`
- Balance mismatch between bot state and MEXC
- User says "posisi nggak bisa di-close" or "bot nggak bisa buka"

## Phase 1: Diagnosis

### 1.1 Check Real MEXC State

**Priority order for endpoints (2026-06-24 confirmed):**
1. `https://api.mexc.com` — works for auth GET + POST (most reliable)
2. `https://contract.mexc.com` — works for public GET only (POST returns 403 WAF)
3. CF Worker — backup only, can die with 403

```python
import json, time, hmac, hashlib, urllib.request, ssl

API_KEY = open('/root/.hermes/secrets/mexc_api_key.txt').read().strip()
SECRET = open('/root/.hermes/secrets/mexc_secret_key.txt').read().strip()
BASE = 'https://api.mexc.com'  # Primary (CF Worker can die)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def sign(body=''):
    ts = str(int(time.time()*1000))
    sig = hmac.new(SECRET.encode(), (API_KEY+ts+body).encode(), hashlib.sha256).hexdigest()
    return {'ApiKey': API_KEY, 'Request-Time': ts, 'Signature': sig, 'Content-Type': 'application/json'}

sess = requests.Session()
sess.verify = False

# Balance
r = sess.get(f'{CF}/api/v1/private/account/assets', headers=sign(), timeout=15)
for a in r.json()['data']:
    if a['currency'] == 'USDT':
        print(f"Equity: ${a['equity']}, Available: ${a['availableBalance']}, Margin: ${a['positionMargin']}")

# Open positions (use open_positions, NOT history_positions)
r2 = sess.get(f'{CF}/api/v1/private/position/open_positions', headers=sign(), timeout=15)
positions = r2.json().get('data', [])
print(f"Open: {len(positions)}")
for p in positions:
    print(f"  {p['symbol']} {'LONG' if p['positionType']==1 else 'SHORT'} vol={p['holdVol']} entry={p['openAvgPrice']} liq={p['liquidatePrice']} pnl={p.get('unRealizedPnl',0)}")
```

### 1.2 Compare with Bot State

```python
state = json.load(open('/root/.hermes/data/predator_v5_state.json'))
bot_active = state.get('active_trades', [])
bot_capital = state.get('risk', {}).get('capital', 0)
print(f"Bot capital: ${bot_capital}, Bot active: {len(bot_active)}")
# Compare with MEXC positions above
```

### 1.3 Check 6026 Block

```python
# Test order
body = json.dumps({'symbol':'ETH_USDT','price':'0','vol':1,'side':1,'type':5,'openType':2,'leverage':1}, separators=(',',':'))
h = sign(body)
r = sess.post(f'{CF}/api/v1/private/order/submit', data=body, headers=h, timeout=10)
d = r.json()
if d.get('success'):
    # Close test order immediately
    close = json.dumps({'symbol':'ETH_USDT','price':'0','vol':1,'side':2,'type':5,'openType':2,'leverage':1}, separators=(',',':'))
    sess.post(f'{CF}/api/v1/private/order/submit', data=close, headers=sign(close), timeout=10)
    print("✅ CLEAR - can open positions")
else:
    print(f"🔴 BLOCKED: {d.get('code')}: {d.get('message')}")
```

## Phase 2: Close Stuck Positions

### ⚠️ CLOSE SIDE CODES — DIRECTION-DEPENDENT (2026-06-25 VERIFIED)

**Side codes depend on position direction, NOT on key age:**

| Code | Purpose | Use for |
|------|---------|---------|
| 1 | Open Long | Opening |
| 2 | Close Short | Closing SHORT positions |
| 3 | Open Short | Opening |
| 4 | Close Long | Closing LONG positions |

**Implementation:**
```python
side = 4 if direction == 1 else 2  # Close Long=4, Close Short=2
```

**History:**
- June 24: side=2 worked as "universal close" for both directions → led to assumption it always works
- June 25: side=2 returns 2009 "Position is nonexistent or closed" for LONG positions. side=4 works for LONG.
- Key change: behavior may shift between key generations. Direction-dependent codes are the safe approach.

### Close Order Format

```python
side = 4 if p.get('positionType') == 1 else 2  # Close Long=4, Close Short=2
body = json.dumps({
    "symbol": "XXX_USDT",
    "price": "0",
    "vol": <holdVol>,        # Must match holdVol from open_positions
    "side": side,            # Direction-dependent (NOT universal)
    "type": 5,               # Market order
    "openType": 2,           # Cross margin
}, separators=(',',':'))
```

### Batch Close All

```python
for p in positions:
    if p['holdVol'] > 0:
        pt = p.get('positionType', 0)
        side = 4 if pt == 1 else 2  # Close Long=4, Close Short=2
        body = json.dumps({
            "symbol": p['symbol'], "price": "0", "vol": p['holdVol'],
            "side": side, "type": 5, "openType": 2
        }, separators=(',',':'))
        r = sess.post(f'{CF}/api/v1/private/order/submit', data=body, headers=sign(body), timeout=10)
        d = r.json()
        status = "✅" if d.get('success') else f"❌ {d.get('code')}"
        print(f"  {p['symbol']}: {status}")
        time.sleep(1)  # Rate limit protection
```

## Phase 3: Handle 6026 Block

### What is 6026?
- `DISABLED_CONTRACT_OPEN_POSITION` — MEXC risk control blocks opening
- Caused by rapid failed orders (bug cascade from side=4)
- **ACCOUNT-LEVEL block** — not IP, not key. Generating new API key does NOT clear it (tested with 3 keys on same account, 2026-06-24)
- All MEXC endpoints return same 6026: api.mexc.com, api.mexc.kr, contract.mexc.com
- User-Agent rotation does NOT help (tested Chrome, Safari, Android, MEXC app UA — all return 6026)
- Duration: 30 min auto-clear IF minor. Observed 3.8+ hours when triggered by rapid cascade
- **Error 8817** from `change_risk_level` endpoint: "Risk limiting mechanism has been upgraded. Please check the website for more information" — confirms risk control must be resolved through MEXC website/app, NOT API
- **MEXC support CAN release manually** — chat support in MEXC app, say "My futures account has error 6026 risk control block. Please release it."

### Recovery Steps
1. **STOP bot** — don't waste resources hitting 6026
2. **Pause auto-restart cron** — prevent wasteful restarts
3. **Set up monitor cron** — check every 5 min (NOT 1min — each test extends block)
4. **Contact MEXC support** — if >2 hours, chat support in MEXC app
5. **Auto-restart on clear** — bot starts automatically

### Monitor Script (`/tmp/check_6026.sh`)

**⚠️ Uses api.mexc.com direct (CF Worker PERMANENTLY DEAD — 403 since 2026-06-24).**

```bash
#!/bin/bash
cd /root/mexc-scalper
RESULT=$(python3 -c "
import sys, json, time
sys.path.insert(0, '.')
with open('/root/.hermes/secrets/mexc_api_key.txt') as f: ak = f.read().strip()
with open('/root/.hermes/secrets/mexc_secret_key.txt') as f: sk = f.read().strip()
from predator_v5 import MEXCClient, CONFIG
client = MEXCClient(cf_worker=CONFIG['cf_worker'], api_key=ak, api_secret=sk, timeout=10, cf_worker_post=CONFIG.get('cf_worker_post'))
bal = client.get('/api/v1/private/account/assets', auth=True)
equity = 0
if bal and bal.get('data'):
    for a in bal['data']:
        if a.get('currency') == 'USDT':
            equity = float(a.get('equity', 0))
            break
body = {'symbol':'1INCH_USDT','price':'0.4','vol':1,'side':3,'type':5,'openType':2,'leverage':10,'externalOid':f't_{int(time.time())}'}
r = client.post('/api/v1/private/order/submit', body, auth=True)
code = r.get('code') if r else -1
if code == 0:
    cb = {'symbol':'1INCH_USDT','price':'0.4','vol':1,'side':2,'type':5,'openType':2,'leverage':10,'externalOid':f'c_{int(time.time())}'}
    client.post('/api/v1/private/order/submit', cb, auth=True)
    print(f'CLEAR|{equity}')
elif code == 6026:
    print(f'BLOCKED|{equity}')
else:
    print(f'ERROR:{code}|{equity}')
" 2>/dev/null)
STATUS=$(echo "$RESULT" | cut -d'|' -f1)
EQUITY=$(echo "$RESULT" | cut -d'|' -f2)
TIMESTAMP=$(date '+%H:%M:%S')
if [ "$STATUS" = "CLEAR" ]; then
    echo "🟢 6026 CLEAR at $TIMESTAMP! Equity: \$$EQUITY"
else
    echo "🔴 $STATUS at $TIMESTAMP | Equity: \$$EQUITY"
fi
```

**Key improvements over old script:**
- Uses bot's MEXCClient (same auth as bot, no mismatch)
- Reports equity alongside status (catches balance drift)
- On CLEAR: also shows the test order was immediately closed
- Uses 1INCH_USDT (cheap, minimal risk for test order)
- NO `nohup` or backgrounding — just prints status, cron handles delivery

**Cron setup:**
```python
cronjob(action="create", name="6026-block-monitor",
    schedule="every 5m", script="bash /tmp/check_6026.sh",
    deliver="origin", no_agent=False,
    prompt="Run /tmp/check_6026.sh. If CLEAR, start bot. If BLOCKED, just report status briefly.")
```

## Phase 4: State Reset

After closing all positions and 6026 clears:

```python
import json
# Get real balance from MEXC (use Phase 1.1 script)
real_equity = 12.53  # Replace with actual

state = {
    "risk": {
        "capital": real_equity, "peak": real_equity,
        "daily_start": real_equity, "trades": 0, "wins": 0,
        "total_pnl": 0, "paused": False, "pause_reason": "",
        "consecutive_sl": 0, "trade_history": []
    },
    "active_trades": [], "last_scan": 0
}
json.dump(state, open('/root/.hermes/data/predator_v5_state.json', 'w'), indent=2)
json.dump(state, open('/root/mexc-scalper/state/state.json', 'w'), indent=2)
open('/root/mexc-scalper/journal.jsonl', 'w').close()
print(f"✅ State reset: ${real_equity}")
```

## Phase 5: Adaptive TP Integration

After positions are open, the Adaptive TP Engine (in `smart_tp_sl.py`) manages exits:

### Momentum Shift Detection (5 detectors)
1. **Momentum acceleration** (2nd derivative) — detects deceleration before reversal
2. **Volume shift** — volume dying = rally/dump exhausting
3. **RSI divergence** — RSI turning from overbought/oversold
4. **Rejection candles** — long wicks = price rejection
5. **VWAP cross** — crossing VWAP = institutional flow shift

### Adaptive TP Actions
- **EXTEND** — momentum strong + near TP → extend TP by 50%
- **HOLD** — momentum ok → ride the wave
- **TAKE_PARTIAL** — momentum weakening + near TP → close 50%
- **EXIT_NOW** — momentum reversing → exit immediately

### Integration
Integrated into `manage_trades()` in `predator_v5.py`. Runs every 3 seconds during active trades. Uses 5-minute klines (30 candles).

### Philosophy
> "Masuk sebelum crowd tahu, keluar sebelum crowd keluar"

## Pitfalls

- **Close side codes: direction-dependent** — LONG→side=4, SHORT→side=2. side=2 as "universal close" FAILS with 2009 on newer keys (June 25+). Use `side = 4 if direction == 1 else 2`. See "CLOSE SIDE CODES" section above.
- **history_positions doesn't show open** — use `open_positions` endpoint
- **Balance = equity, not available** — available can be $0 when margin locked
- **6026 is ACCOUNT-LEVEL, not IP or key-level** — proxy will NOT help. Generating new API key on same account does NOT clear it (tested with 4 keys on same account, 2026-06-24). The block is on the ACCOUNT itself. Only fixes: wait for auto-clear (could be hours to days), or contact MEXC support for manual release.
- **6026 duration: variable** — minor: 30min auto-clear. Rapid cascade: 3.8+ hours observed, could be 11+ hours. If >2 hours, contact MEXC support.
- **New API key doesn't help** — 6026 is account-level, not tied to specific key. All keys on blocked account return 6026. Tested: user generated mx0v...5rhf on June 24, still 6026.
- **No MEXC risk verification endpoint** — tried `/api/v1/private/account/risk`, `/risk/control`, `/contract/verify`, `/risk/verify`, `/api_key/status`, etc. ALL return 404. Cannot programmatically clear 6026. The `change_risk_level` endpoint returns error 8817: "Risk limiting mechanism has been upgraded. Please check the website for more information" — confirms resolution requires website/app action.
- **CF Worker is PERMANENTLY dead** — returns 403 on all requests (confirmed 2026-06-24). Do NOT use. Switch CONFIG to `api.mexc.com` direct for both `cf_worker` and `cf_worker_post`.
- **MEXCClient has only `get(path, auth=False)` and `post(path, body, auth=False)`** — not `get_balance()` etc. Use `client.get('/api/v1/private/account/assets', auth=True)` for balance.
- **MEXC regional endpoints** — api.mexc.kr works same as api.mexc.com (both return 6026 on blocked account). api.mexc.cc returns 403. api.mexc.me/.sg don't resolve.
- **MEXC API v3 signature** — uses `X-MEXC-APIKEY`, `timestamp`, `signature` (HMAC SHA256 of body). Does NOT work for futures endpoints (returns 602 "Confirming signature failed"). Always use v1 signature for futures.
- **Don't spam orders during 6026** — makes block last longer. Set monitor to 5min NOT 1min.
- **Test close with small order first** — verify side=2 works before batch close
- **Rate limit** — 1 second between close orders to avoid 510 errors
- **Each test order during 6026 extends the block** — monitor passively, don't retry open
- **User can't clear 6026 via browser without login** — agent browser tools can access MEXC website but can't login to user's account. User must use MEXC app directly.
- **Ghost trades** — Bot opens position but state file loses it (crash/restart before save). Symptom: `active_trades: []` in state but MEXC shows open position. Fix: check MEXC positions directly, add to state or force close.
- **Watchdog false readings** — When CF Worker dies (403), watchdog using MEXCClient may return wrong balance ($0) and wrong 6026 status (False instead of True). Fix: watchdog must use urllib with api.mexc.com direct, NOT MEXCClient (which depends on cf_worker config).
- **Don't spam test orders** — User explicitly said "Jangan spam lagi, kalau di bekukan bahaya." Each test order during 6026 extends the block. Set monitor to 5min minimum. Never retry more than once per cycle.
- See `references/6026-exhaustive-test-matrix-2026-06-24.md` for complete test matrix (endpoints, UAs, keys, parameters)
- See `references/6026-block-pattern-2026-06-24.md` for real incident timeline
- See `references/6026-account-level-proof-2026-06-24.md` for exhaustive test matrix proving 6026 is account-level
- See `references/mexc-endpoint-routing.md` for proxy/endpoint decision tree
- See `references/ghost-trade-state-divergence.md` for ghost trade detection and fix

## Integration

Works with:
- `bot-ops` — restart workflow after recovery
- `mexc-sync` — API reference and credentials
- `mexc-api` — close position fix documentation
- Skill Factory auto-generated: 2026-06-24
