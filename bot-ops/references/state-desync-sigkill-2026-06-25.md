# State Desync Incident — 2026-06-25

## What Happened
Bot state file had `active_trades: []` but MEXC had open BTC_USDT LONG position (entry $59,416, vol 43, 30x). Bot was blind — no TP/SL management.

## Root Cause Chain
1. Old bot running with 0 active trades in state
2. Manual state sync wrote BTC position to state file
3. Killed old bot with SIGTERM (`kill`, not `kill -9`)
4. Exit handler fired `_save_state()` — overwrote manual sync with 0 trades
5. New bot started with 0 trades — position remained orphaned

## Key Learning
**SIGKILL (-9) required for state sync.** SIGTERM triggers exit handler which calls `_save_state()`, overwriting your work.

## Correct Sequence
```bash
# 1. Kill with SIGKILL — no exit handler
kill -9 $(pgrep -f "predator_v5.py")

# 2. Write synced state
python3 /tmp/sync_final.py  # Auto-detects positions from MEXC API

# 3. Start bot
cd /root/mexc-scalper && python3 -u predator_v5.py &
```

## Close Side Code Discovery
Same incident revealed: `side=2` as universal close FAILS with error 2009 on newer API keys (June 25+).

**Verified working:**
- Close LONG → `side=4`
- Close SHORT → `side=2`

**Test result:**
```
side=2 on BTC_LONG: code=2009 "Position is nonexistent or closed"
side=4 on BTC_LONG: code=0 (SUCCESS)
```

## Bot Code Fix
```python
# In close_position():
side = 4 if direction == 1 else 2  # LONG→4, SHORT→2
```

## Fee-Eating Round Trip Discovery
Same session found: bot opens position → Smart TP_NOW immediately closes → fees drain balance.

**Fix:** 5-minute minimum hold before Smart TP_NOW or Adaptive EXIT_NOW can close.
