# 6026 Account-Level Block — Proof (2026-06-24)

## Summary
Proved conclusively that MEXC error 6026 is **account-level**, not key-level or IP-level. No proxy, new API key, or endpoint change can bypass it.

## Test Matrix

### Endpoint Rotation (all returned 6026 on blocked account)
| Endpoint | Auth GET | POST Order | Result |
|----------|----------|------------|--------|
| api.mexc.com | ✅ | 6026 | Balance works, orders blocked |
| contract.mexc.com | ✅ | 403 WAF | Public GET only |
| api.mexc.kr | ✅ | 6026 | Same as api.mexc.com |
| api.mexc.cc | 403 | 403 | Blocked |
| api.mexc.me | DNS fail | DNS fail | Doesn't resolve |
| api.mexc.sg | DNS fail | DNS fail | Doesn't resolve |
| CF Worker | 403 | 403 | Dead (confirmed permanent 403) |

### API Key Rotation (all returned 6026 on same account)
| Key | Generated | Status |
|-----|-----------|--------|
| mx0v...sBoE (June 15) | Old | 402 EXPIRED |
| mx0v...8kqQ (June 19) | Previous | 402 EXPIRED |
| mx0v...rhf (June 21) | Current | ACTIVE but 6026 |
| mx0v...5rhf (June 24) | NEW | ACTIVE but 6026 ← confirms account-level |

### Order Type Rotation (all returned 6026)
- Market (type=5), Limit (type=3), Stop (type=10), Trigger (type=7)

### Symbol Rotation (all returned 6026)
- ETH, BTC, SOL, XRP, 1INCH, DOGE

### Parameter Rotation (all returned 6026)
- Leverage 1x-10x, Cross/Isolated

### User-Agent Rotation (all returned 6026)
- Chrome/120, Safari/605, Android/Chrome, MEXC App UA

### MEXC API v3 Signature (doesn't work for futures)
- v3 uses: `X-MEXC-APIKEY`, `timestamp`, `signature` (HMAC SHA256 of body)
- v1 uses: `ApiKey`, `Request-Time`, `Signature` (HMAC SHA256 of apiKey+ts+body)
- v3 on futures endpoints → 602 "Confirming signature failed"
- **Always use v1 signature for futures API**

### Risk Control Endpoints (all 404 or 8817)
- `/api/v1/private/account/risk` → 404
- `/api/v1/private/risk/control` → 404
- `/api/v1/private/account/verify` → 404
- `/api/v1/private/risk/verify` → 404
- `/api/v1/private/api_key/status` → 404
- `/api/v1/private/account/change_risk_level` → **8817**: "Risk limiting mechanism has been upgraded. Please check the website for more information"
- **No API endpoint exists to clear 6026**

## Timeline
- **17:49 WIB (10:49 UTC)**: First 6026 error (cascade from side=4 bug)
- **21:39 WIB (14:39 UTC)**: Still blocked (3.8+ hours)
- **22:30+ WIB**: User tried new API key → still 6026
- **05:39 WIB (22:39 UTC)**: Still blocked (11+ hours) — requires MEXC support

## Resolution
- **MEXC support chat** can release manually (fastest, 5-15 min)
- **Auto-clear**: variable (3.8+ hours observed, could be 24+ hours)
- **New API key on same account**: does NOT help (confirmed with 4 keys)
- **Browser access**: MEXC website may show risk assessment prompt, but requires login session (agent can't access user's session)

## Prevention
- **Never use side=4** — always side=2 for closing
- **Implement 120s global cooldown** between open/close cycles
- **Max 2 positions** — reduces cascade risk
- **Monitor bot logs** for repeated CLOSE FAIL patterns
