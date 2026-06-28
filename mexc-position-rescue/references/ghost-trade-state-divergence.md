# State Divergence: Ghost Trades

**Date:** 2026-06-24
**Incident:** Bot opened BTC_USDT position but state file had `active_trades: []`

## What Happened

1. Bot was killed and restarted during position open
2. MEXC accepted the order (position exists on exchange)
3. Bot crashed/restarted before saving state
4. State file had empty `active_trades`
5. Bot showed `active=0` in logs but MEXC showed 1 open position
6. Bot tried to open 2nd position → rejected (insufficient balance, $8.72 locked in margin)

## Detection

```python
# Compare MEXC positions vs bot state
mexc_positions = api_get('/api/v1/private/position/open_positions')  # from MEXC
bot_state = json.load(open('/root/.hermes/data/predator_v5_state.json'))
bot_active = bot_state.get('active_trades', [])

mexc_count = len(mexc_positions.get('data', []))
bot_count = len(bot_active)

if mexc_count != bot_count:
    print(f"⚠️ DIVERGENCE: MEXC={mexc_count}, Bot={bot_count}")
```

## Fix Options

### Option A: Add missing trade to state (preferred if position is profitable)
```python
for p in mexc_positions.get('data', []):
    # Check if this position exists in bot state
    found = any(t['symbol'] == p['symbol'] for t in bot_active)
    if not found:
        bot_active.append({
            'symbol': p['symbol'],
            'direction': 1 if p['positionType'] == 1 else -1,
            'entry': float(p['openAvgPrice']),
            'vol': p['holdVol'],
            'remaining_vol': p['holdVol'],
            'time': p['createTime'] / 1000,
            'tp_pct': 0.03,  # default
            'sl_pct': 0.025,  # default
            'pnl_pct': 0,
        })
json.dump(bot_state, open(state_file, 'w'), indent=2)
```

### Option B: Force close all and reset (preferred if position is losing)
```bash
python3 /root/mexc-scalper/close_all.py
# Then reset state
```

## Prevention

- Bot should save state BEFORE opening position (pre-allocate)
- Bot should reconcile on startup: check MEXC positions vs state
- If divergence detected, log warning and either add or close

## Related

- Balance `availableBalance` vs `equity` — when position is open, available is much lower than equity
- Bot correctly rejects new orders when available < estimated cost
- This is NOT a bug — it's correct risk management
