# Close Side Codes — CORRECTED 2026-06-25

## CRITICAL: Side codes are DIRECTION-DEPENDENT

### MEXC Futures API Side Codes
```
side=1: Open Long ✅
side=2: Close Short ✅ (for SHORT positions)
side=3: Open Short ✅
side=4: Close Long ✅ (for LONG positions)
```

### Implementation
```python
side = 4 if direction == 1 else 2  # Close Long=4, Close Short=2
```

### Test History

**2026-06-24 (Old key mx0v...8kqQ):**
- side=2 → ✅ Worked as "universal close" for both directions
- side=4 → ❌ Caused cascade failure + 6026 block

**2026-06-24 (New key mx0vgldDcio88RHM4D):**
- side=2 → ✅ Worked as "universal close"
- side=4 → ❌ 2001 "Order direction error"

**2026-06-25 (Same key mx0vgldDcio88RHM4D, key generated June 25):**
- side=2 → ❌ 2009 "Position is nonexistent or closed" for LONG positions
- side=4 → ✅ SUCCESS for closing LONG positions
- side=2 → ✅ SUCCESS for closing SHORT positions

### Key Insight
MEXC API behavior for close side codes CHANGED between June 24-25:
- June 24: side=2 was universal (worked for both directions)
- June 25: side=2 only works for SHORT, side=4 only works for LONG

**Root cause of 6026 block (June 24):**
Using side=4 on the OLD key caused rapid open/close spam → MEXC risk control → 6026 block.
This made everyone conclude "side=4 is broken" — but it was actually key-dependent.

### Safe Implementation (Works with ALL keys)
```python
# In close_position():
side = 4 if direction == 1 else 2

# In close_all.py:
pt = p.get('positionType', 0)  # 1=LONG, 2=SHORT
side = 4 if pt == 1 else 2
```

### Verification
- predator_v5.py close_position(): Uses `side = 4 if direction == 1 else 2` ✅
- close_all.py: Uses `side = 4 if pt == 1 else 2` ✅
- mexc-api skill: Documents direction-dependent codes ✅
