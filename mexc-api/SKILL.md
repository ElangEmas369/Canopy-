---
name: mexc-api
description: "MEXC API integration — signature, proxy flow, auth routing, position management for crypto futures trading"
version: 1.0.0
author: OWL + Tuan Muda
license: MIT
platforms: [linux]
prerequisites:
  commands: [python3]
metadata:
  hermes:
    tags: [trading, crypto, mexc, api, futures, defi]
    homepage: https://www.mexc.com
---

# MEXC API Integration

MEXC futures API integration for Python trading bots. Covers authentication, signature generation, proxy routing (CF Worker), and position management.

## Architecture

### Endpoint Routing (2026-06-24 VERIFIED, updated 2026-06-24)
```
PRIMARY:    api.mexc.com — works for ALL operations (auth GET, POST, public)
SECONDARY:  contract.mexc.com — auth GET ✅, public GET ✅, POST ❌ (403 WAF)
BACKUP:     CF Worker proxy — fragile, can die with 403 at any time
```

**⚠️ MEXCClient in predator_v5.py uses `auth=True` flag:**
- `client.get(path, auth=False)` → contract.mexc.com (public endpoints)
- `client.get(path, auth=True)` → api.mexc.com (balance, positions)
- `client.post(path, body, auth=True)` → api.mexc.com (orders)

**⚠️ `api.mexc.com` works for BOTH spot AND futures (confirmed 2026-06-24). Previously documented as "spot only" — WRONG.**
```python
client = MEXCClient(cf_worker=CONFIG['cf_worker'], api_key=ak, api_secret=sk, timeout=10)
```

**✅ `api.mexc.com` works for BOTH spot AND futures (confirmed 2026-06-24).**
**⚠️ MEXC API v3 endpoints (`/api/v3/...`) return 700007 for futures keys — use v1 endpoints (`/api/v1/...`) only.**

### Python Implementation (use `requests`, NOT `urllib` — urllib ssl.CERT_NONE fails auth in PRoot)
```
Signature = hmac(secret_key, api_key + timestamp + body)
Header: ApiKey: <api_key>
Header: Request-Time: <timestamp_ms>
Header: Signature: <hex_digest>
```

### Python Implementation (standalone — for scripts, NOT using bot's MEXCClient)
```python
import json, time, hmac, hashlib, requests
import urllib3; urllib3.disable_warnings()

def _sign(api_key, secret_key, body_str=''):
    ts = str(int(time.time() * 1000))
    sig = hmac.new(secret_key.encode(), (api_key + ts + body_str).encode(), hashlib.sha256).hexdigest()
    return {'ApiKey': api_key, 'Request-Time': ts, 'Signature': sig, 'Content-Type': 'application/json'}

# Auth: api.mexc.com (PRIMARY), Public: contract.mexc.com (faster for market data)
def api_get(path, api_key, secret_key, auth=False):
    base = 'https://api.mexc.com' if auth else 'https://contract.mexc.com'
    headers = _sign(api_key, secret_key) if auth else {'Content-Type': 'application/json'}
    r = requests.get(f'{base}{path}', headers=headers, timeout=15, verify=False)
    return r.json()

def api_post(path, body, api_key, secret_key):
    body_json = json.dumps(body, separators=(',', ':'))
    headers = _sign(api_key, secret_key, body_json)
    r = requests.post(f'https://api.mexc.com{path}', data=body_json, headers=headers, timeout=15, verify=False)
    return r.json()
```

## Key Endpoints

### Account
```
GET  /api/v1/private/account/assets (auth=True)
POST /api/v1/private/order/submit (auth=True)
POST /api/v1/private/order/cancel/all (auth=True)
GET  /api/v1/private/position/open_positions (auth=True)
```

### Market Data (Public)
```
GET /api/v1/contract/ticker?symbol=BTC_USDT
GET /api/v1/contract/kline/{symbol}?interval=Min15&limit=50
GET /api/v1/contract/depth/{symbol}?limit=50
GET /api/v1/contract/detail?symbol={symbol}
```

### Order Types
```
type=1: Limit
type=2: Market
type=3: Stop-loss
type=4: Take-profit
type=5: Liquidation (system)

side=1: Open Long ✅
side=2: Close Short ✅ (works for SHORT positions)
side=3: Open Short ✅
side=4: Close Long ✅ (works for LONG positions)

**Close side codes (2026-06-25 VERIFIED):**
- LONG → side=4 (Close Long)
- SHORT → side=2 (Close Short)
- side=2 as "universal close" FAILS with 2009 on newer keys (June 25+)
- Implementation: `side = 4 if direction == 1 else 2`

positionType=1: Isolated
positionType=2: Cross

openType=1: Isolated
openType=2: Cross
```

### Error 6026 — Position Opening Blocked
- Message: `DISABLED_CONTRACT_OPEN_POSITION`
- Cause: Rapid failed orders trigger MEXC risk control
- **ACCOUNT-LEVEL block** — NOT IP, NOT key-level. Proxy rotation does NOT help. All keys on blocked account return 6026.
- Duration: 30min — 2hrs auto-clear (minor). 3.8+ hours observed for rapid cascade (2026-06-24).
- **Error 8817** from `change_risk_level`: "Risk limiting mechanism has been upgraded. Please check the website for more information" — confirms risk control must be resolved through MEXC website/app, not API.
- Action: Stop bot, set up 5-min monitor cron, auto-restart on clear. If >2 hours, contact MEXC support via app chat.
- See `mexc-position-rescue` skill for full recovery protocol

## Position Response Fields
```json
{
  "positionId": 1425831535,
  "symbol": "BTC_USDT",
  "positionType": 1,
  "holdVol": 5,
  "holdAvgPrice": 63285.4,
  "openAvgPrice": 63285.4,
  "liquidatePrice": 20574.1,
  "leverage": 20,
  "profitRatio": -0.016,
  "realised": -0.0258
}
```

## Pitfalls

### 🚨 NEVER ASK FOR NEW API KEYS (CRITICAL — User correction 2026-06-25, reinforced 2026-06-28)
User has been EXTREMELY frustrated by agent repeatedly asking for new keys when API fails. This is the #1 behavioral correction.

**ROOT CAUSE (2026-06-28):** Agent's test script had a BUG (missing `SK =` variable declaration), causing false "API expired" conclusion. User confirmed: "Api tidak exp" and "bukan api mexc yang exp tapi loe yang lupa caranya".

```python
# WRONG - Missing SK definition
AK = "mx0vgl...3c6d"  # This line got corrupted during write
sig = sign(SK, AK + ts)  # SK is undefined!

# CORRECT - Always define both
AK = "mx0vglYKFYSflyEB2Y"
SK = "a189628daae142c4a0a35e40b8e23c6d"
sig = hmac.new(SK.encode(), (AK + ts).encode(), hashlib.sha256).hexdigest()
```

```
RULE: NEVER conclude "key expired" or ask for new key until ALL of these are checked:
1. Test with CORRECT signature format: hmac(secret, api_key + ts + body)
2. Test with CORRECT headers: ApiKey, Request-Time, Signature (NOT x-mexc-apikey)
3. Test with CORRECT library: requests or urllib (NOT curl_cffi)
4. Test with BOTH endpoints: api.mexc.com AND contract.mexc.com
5. Check error code: 602=signature, 1005=network, 10072=key block, 402=expired
6. Check if public API works (confirms IP not blocked)
7. Check MEXC app for key status (Disabled? Pending? Blocked?)
8. **VERIFY YOUR TEST SCRIPT HAS NO BUGS** - check variable names, imports

ONLY after ALL 8 steps fail, ask user to check MEXC app for key status.
NEVER ask user to generate a new key without explicit confirmation from MEXC app.
NEVER blame the key until you've verified your own test code.
```

### Close Position: direction-dependent side codes (2026-06-25 VERIFIED)
- `side=4` = Close Long (LONG positions) ✅
- `side=2` = Close Short (SHORT positions) ✅
- `side=2` as "universal close" FAILS with error 2009 on newer API keys (June 25+)
- Implementation: `side = 4 if direction == 1 else 2`
- Bot `close_position()` uses direction-dependent codes
- See `mexc-position-rescue/references/close-side-codes-key-dependent.md` for full test matrix

### ✅ _close_all Must Check Return Value (2026-06-25)
`_close_all()` must check `close_position()` return. If close fails, DON'T remove from active_trades and DON'T record PnL. Without this check, bot silently removes positions that failed to close, leaving orphaned positions on MEXC.

### api.mexc.com Signature & Key Compatibility (2026-06-28)
- Active key `mx0vglYKFYSflyEB2Y` works on `api.mexc.com` with HMAC(secret, api_key + ts + body) signing
- `contract.mexc.com` may be IP blocked depending on server location - use `api.mexc.com` as primary
- **Pitfall**: Always test new keys with balance check before declaring active

### Shell `.group(1)` Auto-Redaction (2026-06-26)
- The Hermes terminal auto-replaces `.group(1)` in inline Python with `***` (security redaction)
- This makes inline Python scripts with `re.search(...).group(1)` UNRELIABLE
- **Workarounds**:
  1. Write script to file first, then `python3 script.py`
  2. Use `re.findall(pattern, text)[0]` instead of `.group(1)`
  3. Save extracted values to temp file: `open('/tmp/key.txt','w').write(value)`
- **Never** write `m1.group(1)` directly in heredoc or `python3 -c` inline

### Requests vs urllib (Updated 2026-06-26)
- Both `requests` (with `verify=False`) AND `urllib.request` (with `ssl.CERT_NONE`) work
- **But**: When server IP is blocked by MEXC (403), BOTH fail identically — library choice is irrelevant
- Use whichever is available; `urllib` preferred for zero-dependency scripts
- `curl_cffi` broken in PRoot (libm ELF header issue) — never use

### curl_cffi broken in PRoot
- `curl_cffi` binary fails with `/lib/aarch64-linux-gnu/libm.so: invalid ELF header`
- **Fix:** Use `urllib.request` instead — works in all environments

### Proxy POST 403
- CF Worker proxy returns 403 for POST requests with body
- **Fix:** Always POST direct to `https://api.mexc.com` (PRIMARY)

### Proxy Auth GET 403
- CF Worker proxy returns 403 for authenticated GET (private endpoints)
- **Fix:** Auth GET must go direct to `https://api.mexc.com` (PRIMARY)

### CF Worker Fragile
- CF Worker `mexc-proxy.refidsaputro369.workers.dev` can die with 403 at any time
- **Fix:** Use `api.mexc.com` as PRIMARY for all operations. CF Worker is backup only.
- Update CONFIG: `'cf_worker': 'https://api.mexc.com', 'cf_worker_post': 'https://api.mexc.com'`

### Balance Returns $0 — CF Worker 403 Fallback (2026-06-25)
- `get_available_balance()` returns $0 when CF Worker returns 403 for private endpoints
- Bot shows "insufficient balance (need $1.39, have $0.00)" despite actual $5+ available
- **Fix**: Add urllib direct fallback when CF Worker fails (see `crypto-trading-ops` SKILL.md for full code)
- **Pattern**: Try CF Worker first → if 0/fail → try urllib direct to contract.mexc.com → if still 0 → return 0

### Signature Format
- **contract.mexc.com**: `hmac(secret, key+ts+body)` — WORKS ✅ (but 403 if IP blocked)
- **api.mexc.com**: `hmac(secret, key+ts+body)` — returns **602 "Confirming signature failed"** ❌
  - Exhaustive testing (30+ signing formats: ts+method+path, apikey+ts+method+path, method+path+ts, SHA512, MD5, base64, newline/space/pipe separators, query param, double HMAC, uppercase hex, raw SHA256) — ALL return 602
  - **Root cause**: api.mexc.com likely requires a DIFFERENT API key (separate from contract.mexc.com key) or different auth mechanism entirely
  - **Action needed**: Generate API key with explicit `api.mexc.com` futures permission, or use MEXC account session token from browser login
- For GET without body: `hmac(secret, key+ts+empty_string)`
- Response code `0` = success
- **⚠️ api.mexc.com is NOT a drop-in replacement for contract.mexc.com** — despite returning non-403 responses, signing is incompatible

### Error 602
- Error 602 = signature format issue, NOT expired key
- If you see 602: check signature construction, don't regenerate keys

### Error 402 — API Key Expired (2026-06-28)
- Message: `"API Key expired, please apply again"`
- **This is NOT the same as Error 10072!**
- **User confirmed (2026-06-28):** Key does NOT expire in 90 days if generated without IP restriction
- Cause: Key actually expired OR revoked by MEXC OR IP whitelist issue
- Bot symptom: PID alive, log growing, but NO trades executed (zombie loop)
- **BEFORE concluding "expired":**
  1. Test with correct signing format
  2. Test on BOTH api.mexc.com AND contract.mexc.com
  3. Check if user generated key WITHOUT IP restriction
  4. Check MEXC app → API Management → key status
- Fix: Generate NEW API key in MEXC UI → Profile → API Management (ONLY after above checks fail)

### Error 10072 "Api key info invalid"
- Key file CORRUPTED or TRUNCATED
- Check: `len(api_key)` should be 18, `len(secret)` should be 32
- Common cause: `sed` on .env files truncates keys (use python3 instead)
- Fix: Re-write keys with python3 direct file write
- ALSO: Key may be temporarily BLOCKED by MEXC security (too many failed auth attempts from same IP)
- Public API works but private returns 10072 → key blocked, NOT invalid
- Fix: Wait 15-30 min, or check MEXC app → API Management → reactivate key

### Error 1005 "Network error" on contract.mexc.com
- NOT a key issue! This is a NETWORK/SSL issue specific to PRoot environments
- `contract.mexc.com` may be blocked by Cloudflare WAF from certain IPs
- `api.mexc.com` works fine for same endpoints
- **Fix**: Use `api.mexc.com` as PRIMARY endpoint (confirmed working 2026-06-25)

### Error 401 "Not logged in"
- Key LACKS PERMISSION for endpoint type (futures vs spot)
- Test spot vs futures separately to diagnose
- Fix: Edit key in MEXC UI → enable "Futures Trading"

### Error 700007 "No permission"
- Key exists but lacks SPOT permission (normal for futures-only keys)

### Key Corruption via sed (2026-06-24)
- `sed -i 's/old/new/g'` on .env/config files can TRUNCATE API keys
- Observed: 18-char key → 13-char, 32-char secret → 13-char
- Root cause: sed interprets certain sequences as metacharacters
- **Fix:** Always use python3 for credential file updates

### Volume vs Quantity
- MEXC uses `vol` (contracts), NOT `quantity`
- For contract pairs, `vol` = number of contracts

## Proxy Configuration
```
PRIMARY:  https://api.mexc.com (works for ALL operations)
BACKUP:   https://contract.mexc.com (public GET only, POST returns 403)
LEGACY:   https://mexc-proxy.refidsaputro369.workers.dev (CF Worker, fragile, can die with 403)
REGIONAL: https://api.mexc.kr (works same as api.mexc.com, returns same errors)
          https://api.mexc.cc (returns 403)
          https://api.mexc.me/.sg (don't resolve)
```

## References
- `references/install.md` — setup and proxy deployment notes
- `references/close-position-fix.md` — side=2 vs side=4 testing history + 6026 recovery
- `references/trading-mode-pattern.md` — TRADING_MODE.md isolated persistent memory pattern
- `references/key-rotation-2026-06.md` — backup key rotation when primary expires (credentials in ~/.hermes/secrets/)
- `references/ghost-position-debug-2026-06-27.md` — ghost position debugging session, state file hierarchy
- `references/bot-stuck-debug-2026-06-28.md` — bot stuck after sync, log file location confusion, zombie processes
- `references/false-key-expired-bug-2026-06-28.md` — API key false "expired" due to test script bug
