⚠️ DEPRECATED (2026-06-28): Expired keys archived for historical reference. Active: mx0vglYKFYSflyEB2Y

# api.mexc.com Signing Incompatibility — 2026-06-26

## Summary
Contract API key (`mx0vglhMFsVtoy3GIi`) works on `contract.mexc.com` but returns **602 "Confirming signature failed"** on ALL `api.mexc.com` private endpoints regardless of signing format.

## Test Results

### Endpoint accessibility
| Endpoint | IP Blocked? | Auth Result |
|----------|-------------|-------------|
| `contract.mexc.com/api/v1/private/account/asset` | YES (403 Access Denied) | N/A |
| `api.mexc.com/api/v1/private/account/asset` | NO | 602 (signature failed) |
| `api.mexc.com/api/v1/contract/account/asset` | NO | 404 (Not Found) |

### Signing formats tested (ALL return 602 on api.mexc.com)

**Header variants:**
- `ApiKey` + `Request-Time` + `Signature` (standard)
- `X-MEXC-APIKEY` + `X-MEXC-TIMESTAMP` + `X-MEXC-SIGNATURE` (Kucoin style)
- `MEXC-APIKEY` + `MEXC-TIMESTAMP` + `MEXC-SIGNATURE`
- `apikey` + `timestamp` + `signature` (lowercase)

**Signing message formats:**
- `ts + method + path` (contract standard)
- `method + path + ts`
- `apikey + ts + method + path`
- `ts + apikey + method + path`
- `apikey + method + path + ts`
- `ts + method + base_url + path`
- `apikey + ts + body`
- `ts + apikey + secret`
- `secret + ts`
- `ts + path`
- `path + ts`
- `method + path`
- `ts` only
- `path` only
- Just API key (no signature)
- URL-encoded query string style

**Hash algorithms:**
- HMAC-SHA256 (standard)
- HMAC-SHA512
- HMAC-MD5
- SHA256(secret + message) (not HMAC)
- SHA256(message + secret)
- Double HMAC
- Base64-encoded HMAC digest
- Uppercase hex digest

**Separator formats (newline, space, pipe, comma):**
- `path\nmethod\nts`, `ts\nmethod\npath`, etc. (all 6 permutations)
- `path method ts`, etc.
- `path|method|ts`, etc.

**Other attempts:**
- Signature in URL query parameter (like Binance)
- POST with body signing
- Empty signing message

**All 30+ variants return code 602.**

## Conclusion
The `api.mexc.com` endpoint exists and is accessible from server IP, but the contract API key cannot authenticate. This is a **key/domain mismatch** — `api.mexc.com` may require:
1. A separately generated API key with `api.mexc.com` permissions
2. A different authentication mechanism (OAuth, session token)
3. Browser-based authentication (cookie/session)

## Recommended Next Steps
1. Generate new API key in MEXC UI specifically testing `api.mexc.com` endpoints
2. Compare key permissions/fields between contract and api keys
3. If MEXC uses session-based auth for `api.mexc.com`, extract token from browser login
