# Upgrade Module Deployment Pattern

## Problem
When replacing bot files with Ahmad Agent (or other external) packages, upgrade modules may:
1. Be missing from the working directory entirely
2. Use `curl_cffi` which is broken in PRoot/Android
3. Have wrong CF Worker URLs
4. Export functions (not classes) — import pattern differs from class-based modules

## Pre-Deployment Checklist

```bash
# 1. Verify ALL upgrade files exist
ls -la /root/mexc-scalper/smart_tp_sl.py
ls -la /root/mexc-scalper/trade_journal.py
ls -la /root/mexc-scalper/exchange_sl.py
ls -la /root/mexc-scalper/session_filter.py
ls -la /root/mexc-scalper/pair_blacklist.py
ls -la /root/mexc-scalper/slippage_tracker.py
ls -la /root/mexc-scalper/challenge_phase_tracker.py

# 2. Check for curl_cffi imports (MUST be replaced)
grep -l "curl_cffi" /root/mexc-scalper/*.py

# 3. Check Worker URLs match
grep "workers.dev" /root/mexc-scalper/*.py
# Should all use: mexc-proxy.refidsaputro369.workers.dev
# NOT: mexc-proxy.bellasintyaa28.workers.dev or others

# 4. Verify imports work
cd /root/mexc-scalper && python3 -c "
from smart_tp_sl import smart_sl, smart_tp, get_klines
from trade_journal import record_open, record_close
from exchange_sl import set_sl_for_position, cancel_all_orders
from session_filter import is_good_session, get_session_multiplier, get_session_info
from pair_blacklist import is_blacklisted, filter_symbols
from slippage_tracker import record_slippage, check_slippage_ok
from challenge_phase_tracker import update_phase
print('ALL OK')
"
```

## curl_cffi → urllib Replacement Template

Every file that uses `curl_cffi` needs this pattern:

### Before (broken in PRoot):
```python
from curl_cffi import requests as curl_requests

# ... in function:
r = curl_requests.get(url, impersonate="chrome", timeout=15, verify=False)
data = r.json()
```

### After (PRoot-compatible):
```python
import urllib.request, urllib.error, ssl

# ... in function:
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
r = urllib.request.urlopen(req, timeout=15, context=ctx)
data = json.loads(r.read().decode())
```

### For POST requests:
```python
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
data = json.dumps(body, separators=(',', ':')).encode('utf-8')
req = urllib.request.Request(url, data=data, headers=headers, method='POST')
r = urllib.request.urlopen(req, timeout=15, context=ctx)
result = json.loads(r.read().decode())
```

## Import Pattern (Function-Based Modules)

Upgrade modules are function-based, NOT class-based:

```python
# ✅ CORRECT — function imports
from smart_tp_sl import smart_sl, smart_tp, get_klines
from trade_journal import record_open, record_close
from exchange_sl import set_sl_for_position, cancel_all_orders
from session_filter import is_good_session, get_session_multiplier, get_session_info
from pair_blacklist import is_blacklisted, filter_symbols
from slippage_tracker import record_slippage, check_slippage_ok
from challenge_phase_tracker import update_phase

# ❌ WRONG — class imports (will fail)
from smart_tp_sl import SmartTPSL
from trade_journal import TradeJournal
```

## Duplicate PID Prevention

Before restarting bot, ALWAYS kill ALL old processes:

```bash
# Kill ALL predator processes (both bash wrapper and python)
pkill -9 -f "predator_v5" 2>/dev/null
sleep 2

# Verify clean
ps aux | grep "[p]redator_v5" | grep -v grep
# Should return nothing

# Then start fresh
```

## Post-Deployment Verification

```bash
# Wait 10s for startup
sleep 10

# Check log for UPGRADES_LOADED
strings /tmp/predator.log | grep -E "Upgrades:|UPGRADES"

# Check balance is reading from MEXC (not stale)
strings /tmp/predator.log | grep "Capital:"

# Check no errors
strings /tmp/predator.log | grep -i "error\|fail\|traceback" | tail -5
```

## Common Pitfalls

1. **Forgot to copy file from cache** — Files arrive in `~/.hermes/cache/documents/` but must be copied to `/root/mexc-scalper/`
2. **Left curl_cffi in one file** — even one file with curl_cffi import will crash the entire bot startup
3. **Wrong Worker URL** — each file may have its own WORKER constant; ALL must point to the same working proxy
4. **Old __pycache__** — always `rm -rf /root/mexc-scalper/__pycache__` after changes
5. **Hardcoded upgrade list** — the `Upgrades:` log line in predator_v5.py is hardcoded string, not dynamic
