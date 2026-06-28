# curl_cffi Broken on PRoot — Replacement Guide

## Problem
`curl_cffi` fails on PRoot/Android with:
```
ImportError: /lib/aarch64-linux-gnu/libm.so: invalid ELF header
```

This affects ALL files that import `curl_cffi`. The fix is to replace with `urllib.request`.

## Affected Files (as of 2026-06-23)
- `/root/mexc-scalper/predator_v5.py` — main bot (already fixed)
- `/root/mexc-scalper/exchange_sl.py` — already fixed
- `/root/mexc-scalper/smart_tp_sl.py` — fixed 2026-06-23
- Any future upgrade modules from external packages

## Detection
```bash
grep -rn "curl_cffi" /root/mexc-scalper/*.py
```

## Replacement Pattern

### Step 1: Replace import
```python
# REMOVE:
from curl_cffi import requests as curl_requests

# ADD:
import urllib.request, urllib.error, ssl
```

### Step 2: Replace GET calls
```python
# BEFORE:
r = curl_requests.get(url, impersonate="chrome", timeout=15, verify=False)
data = r.json()

# AFTER:
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
r = urllib.request.urlopen(req, timeout=15, context=ctx)
data = json.loads(r.read().decode())
```

### Step 3: Replace POST calls
```python
# BEFORE:
r = curl_requests.post(url, json=body, impersonate="chrome", timeout=15, verify=False)
data = r.json()

# AFTER:
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
data = json.dumps(body, separators=(',', ':')).encode('utf-8')
req = urllib.request.Request(url, data=data, headers=headers, method='POST')
r = urllib.request.urlopen(req, timeout=15, context=ctx)
result = json.loads(r.read().decode())
```

### Step 4: Replace Worker URL if needed
```python
# Check what URL the file uses:
grep "workers.dev" /root/mexc-scalper/FILE.py

# Should be: https://mexc-proxy.refidsaputro369.workers.dev
# If different, update with sed:
sed -i 's|https://mexc-proxy.OLD.workers.dev|https://mexc-proxy.refidsaputro369.workers.dev|g' FILE.py
```

## Verification
```bash
cd /root/mexc-scalper && python3 -c "
import urllib.request, ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request('https://mexc-proxy.refidsaputro369.workers.dev/api/v1/contract/ticker?symbol=BTC_USDT', headers={'User-Agent': 'Mozilla/5.0'})
r = urllib.request.urlopen(req, timeout=15, context=ctx)
import json
data = json.loads(r.read().decode())
print('urllib works:', data.get('success'))
"
```
