# Bot Pause Bug — Root Cause & Fix (2026-06-25)

## Problem
Bot pauses on 3 consecutive SL and NEVER recovers. State file persists `paused=True` across restarts.

## Root Cause
1. Bot hits 3 consecutive SL → `can_trade()` sets `paused=True`
2. Bot saves state to file with `paused=True`
3. Bot exits or restarts
4. `_load_state()` calls `from_dict()` which loads `paused=True`
5. `can_trade()` returns False immediately → bot runs but never trades
6. Bot saves `paused=True` on exit → infinite loop

## Symptoms
- Bot process is RUNNING (PID alive)
- Log shows startup but no scanning activity
- State file shows `paused: true, pause_reason: "3 consecutive SL"`
- Bot CPU usage = 0% (sleeping)
- No position management happening

## Fix Applied (2026-06-25)
Added daily auto-unpause in `can_trade()`:

```python
def can_trade(self):
    # Daily reset — clear pause state on new day
    today = datetime.now().strftime('%Y-%m-%d')
    if not hasattr(self, '_last_daily_date') or self._last_daily_date != today:
        self.daily_start = self.capital
        self._last_daily_date = today
        # Auto-unpause on new day (give bot fresh start)
        if self.paused:
            log.info(f"🌅 New day! Clearing pause: {self.pause_reason}")
            self.paused = False
            self.pause_reason = None
            self.consecutive_sl = 0
    
    if self.paused:
        return False, self.pause_reason
```

## Manual Fix (Immediate)
```python
import json
state_path = '/root/.hermes/data/predator_v5_state.json'
d = json.load(open(state_path))
d['risk']['paused'] = False
d['risk']['pause_reason'] = None
d['risk']['consecutive_sl'] = 0
d['risk']['last_sl_time'] = 0
json.dump(d, open(state_path, 'w'), indent=2)
```

## Critical: SIGKILL Required
When editing state file manually, MUST kill bot with SIGKILL (-9), NOT SIGTERM.
SIGTERM triggers exit handler which calls `_save_state()`, overwriting your manual fix.

```bash
# ✅ CORRECT:
kill -9 $(pgrep -f "predator_v5.py")
# ... edit state file ...
# ... start bot ...

# ❌ WRONG:
kill $(pgrep -f "predator_v5.py")  # SIGTERM → exit handler → overwrite
```

## Verification
After fix, check log for:
```
✅ TRADING_MODE: ON (from TRADING_MODE.md)
State loaded: capital=$X.XX trades=N
PREDATOR V5 APEX — 🔴 LIVE
Session: [session_name]  # Should NOT show "PAUSED"
```

If log shows scanning activity (🎯 SIGNAL, 🔍 TRY_OPEN, ❌ REJECT), bot is working.
