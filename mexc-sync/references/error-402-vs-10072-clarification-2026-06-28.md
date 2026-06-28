# MEXC Error 402 vs 10072 — Key Clarification (2026-06-28)

## Problem
These two errors were conflated in debugging, leading to wrong fixes.

## Error 402 — "API Key expired, please apply again"
```json
{"success": false, "code": 402, "message": "API Key expired, please apply again"}
```
- **Meaning:** The key has actually expired or been revoked by MEXC
- **Key format:** Still correct (starts with `mx0...`)
- **Signing:** Works fine, but key is dead
- **Bot symptom:** 
  - PID is alive and log is growing
  - Bot connects successfully but every API call returns 402
  - No trades are executed (zombie loop)
  - Balance/position calls fail silently or with 402
- **Fix:** User must generate NEW API key in MEXC UI
- **NOT fixable by:** Changing signing format, rotating endpoints, whitelisting IP

## Error 10072 — "Api key info invalid"
```json
{"code": 10072, "msg": "Api key info invalid"}
```
- **Meaning:** Key file corrupted/truncated, OR key format wrong, OR key blocked by MEXC security
- **Key format:** May be wrong length (should be 18 for key, 32 for secret)
- **Common cause:** `sed` on credential files, shell truncation, copy-paste error
- **Also cause:** Key temporarily BLOCKED by MEXC security (too many failed auth attempts from same IP). Public API works but private returns 10072.
- **Fix:** 
  1. Re-write keys with python3 (NOT sed)
  2. If key file correct: Wait 15-30 min for security block to clear
  3. Check MEXC app → API Management → reactivate key

## Diagnostic Flowchart
```
API call fails
├── Error 402?
│   └── YES → Key expired → Generate new key in MEXC UI
│   └── NO ↓
├── Error 10072?
│   ├── Key length wrong? → Re-write from MEXC dashboard
│   ├── Public API works but private fails? → Security block → Wait 30 min
│   └── Key length correct + all endpoints fail? → Key revoked → Generate new
├── Error 602?
│   └── Signing format wrong → Check HMAC construction
└── Error 403?
    └── IP blocked → Use api.mexc.com instead of contract.mexc.com
```

## Key Rule
**NEVER ask for new key until you've confirmed the key file is correct AND both endpoints fail.** A wrong signing format returns 602, not 402/10072. Don't confuse signature issues with key validity issues.
