# Close Position Fix — CORRECTED 2026-06-25

## CRITICAL: Side codes are DIRECTION-DEPENDENT

### MEXC Futures Side Codes
```
side=1: Open Long ✅
side=2: Close Short ✅ (SHORT positions)
side=3: Open Short ✅
side=4: Close Long ✅ (LONG positions)
```

### Implementation
```python
side = 4 if direction == 1 else 2  # Close Long=4, Close Short=2
```

### Test History

**2026-06-24 (Old key):** side=2 worked universal, side=4 caused 6026 cascade
**2026-06-24 (New key):** side=2 worked universal, side=4 returned 2001
**2026-06-25 (Same new key):** side=2 returns 2009 for LONG, side=4 works for LONG

### Key Insight
MEXC behavior CHANGED between June 24-25. Direction-dependent codes are the safe approach.

### _close_all Fix (2026-06-25)
```python
# BEFORE (BUG): ignores close failure, removes trade anyway
executor.close_position(t['symbol'], t['direction'], remaining)
self.active_trades.remove(trade)  # WRONG if close failed!

# AFTER (FIX): check return value
result = executor.close_position(t['symbol'], t['direction'], remaining)
if not result.get('success'):
    log.error(f"CLOSE FAILED: keeping in active_trades")
    return 'HOLDING'  # Don't remove trade
```
