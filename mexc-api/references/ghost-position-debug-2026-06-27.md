# Ghost Position Debugging Session (2026-06-27)

## Scenario
Bot showed "Resume: ACE_USDT SHORT entry=0.0756" on startup despite state file showing `active_trades: []`. Position was stuck in retry loop trying to close.

## Root Cause
**Wrong state file edited.** Bot reads from `~/.hermes/data/predator_v5_state.json` (line 201 in predator_v5.py), but debugging edits were applied to `/root/mexc-scalper/state/state.json`.

## State File Hierarchy
Three files exist with potentially different data:
1. **PRIMARY**: `~/.hermes/data/predator_v5_state.json` (bot reads/writes here)
2. **SECONDARY**: `/root/mexc-scalper/state/state.json` (local backup, often stale)
3. **SNAPSHOT**: `/root/mexc-scalper/shared_state.json` (very old, read-only reference)

## Discovery Process
1. Bot logs showed "Resume: ACE_USDT" on startup
2. File check: `cat /root/mexc-scalper/state/state.json` → `active_trades: []` (empty)
3. Tried clearing file, restarting bot → ghost persisted
4. Checked bot code: `grep "Resume:" predator_v5.py` → found `_load_state()` function
5. Traced persistence: `self.persistence = Persistence(self.config['state_file'])`
6. Found config: `'state_file': os.path.expanduser('~/.hermes/data/predator_v5_state.json')`
7. **Checked ACTUAL state file**: `cat ~/.hermes/data/predator_v5_state.json` → found ACE_USDT still in active_trades
8. Cleared CORRECT file → ghost resolved

## API Discovery
Position was already closed on MEXC (error 2009: "Position is nonexistent or closed"). Bot was trying to close a position that didn't exist.

**Header auth verification**:
```python
import requests, time, hmac, hashlib

api_key = 'mx0vglYKFYSflyEB2Y'
secret = 'a189628daae142c4a0a35e40b8e23c6d'

timestamp = str(int(time.time() * 1000))
body_str = ''
sig = hmac.new(secret.encode(), (api_key + timestamp + body_str).encode(), hashlib.sha256).hexdigest()

headers = {
    'ApiKey': api_key,
    'Request-Time': timestamp,
    'Signature': sig,
    'Content-Type': 'application/json'
}

# Test backup endpoint
url = 'https://api.mexc.com/api/v1/private/account/assets'
resp = requests.get(url, headers=headers, timeout=10)
# Result: 200 OK, auth successful
```

**Key lesson**: `api.mexc.com` works with backup API key when using correct header-based signature format.

## Fix
```bash
# 1. Kill bot
pkill -9 -f "python3.*predator_v5.py"

# 2. Clear CORRECT state file (PRIMARY)
python3 -c "
import json
state = {
  'risk': {
    'capital': 5.23,
    'peak': 18.53,
    'daily_start': 11.5,
    '_last_daily_date': '2026-06-27',
    'consecutive_sl': 0,
    'last_sl_time': 0,
    'trades': 1,
    'wins': 0,
    'total_pnl': -0.0577,
    'paused': False,
    'pause_reason': None,
    'trade_history': []
  },
  'active_trades': [],
  'last_scan': $(date +%s),
  'saved_at': '$(date -Iseconds)'
}
with open('/root/.hermes/data/predator_v5_state.json', 'w') as f:
    json.dump(state, f, indent=2)
"

# 3. Restart bot
cd /root/mexc-scalper && python3 -u predator_v5.py 2>&1 | tee /tmp/predator_v5_live.log &

# 4. Verify
sleep 8 && tail -20 /tmp/predator_v5_live.log | grep "State loaded"
# Expected: "State loaded: capital=$5.23 trades=0" (no "Resume: ACE_USDT")
```

## Prevention
1. **ALWAYS check bot config** for `state_file` location before editing state
2. **ALWAYS verify file modification time** after edit: `stat -c %Y <file>`
3. **When ghost persists**, check ALL THREE state files + MEXC API actual
4. **Cross-check with MEXC API** to confirm position status before manual state edits

## Related Skills
- `bot-ops` → State File Reset section
- `mexc-position-rescue` → Ghost position detection
