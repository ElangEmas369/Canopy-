# MEXC API Key Rotation Pattern (2026-06-26)

## Context
Primary MEXC API key expired mid-session. Bot went blind — could not access account, positions, or balance despite processes running.

## Symptoms
- Public endpoints: ✅ Working (ticker, kline data)
- Private endpoints: ❌ 403 Forbidden
- Bot shows old capital ($20.24) but actual equity dropped to $11.98
- Bot cannot manage open positions

## Root Cause
Primary API key `mx0vglhMFsVtoy3GIi` expired/revoked by MEXC.

## Solution: Backup Key Rotation

### 1. Credentials Storage Location
Keys stored in `~/.hermes/secrets/` (NOT .env):
```
~/.hermes/secrets/mexc_api_key.txt
~/.hermes/secrets/mexc_secret_key.txt
```

Bot reads from these files:
```python
with open(os.path.expanduser('~/.hermes/secrets/mexc_api_key.txt')) as f:
    API_KEY = f.read().strip()
with open(os.path.expanduser('~/.hermes/secrets/mexc_secret_key.txt')) as f:
    SECRET_KEY = f.read().strip()
```

### 2. Backup Key from TRADING_MODE.md
Project maintains backup credentials in `TRADING_MODE.md`:
```markdown
# Backup: api.mexc.com (ACTIVE — primary expired June 26)
MEXC_API_KEY: mx0vglYKFYSflyEB2Y
MEXC_SECRET_KEY: a189628daae142c4a0a35e40b8e23c6d
```

### 3. Rotation Steps
```bash
# Update API key file
echo "mx0vglYKFYSflyEB2Y" > ~/.hermes/secrets/mexc_api_key.txt

# Update secret key file
echo "a189628daae142c4a0a35e40b8e23c6d" > ~/.hermes/secrets/mexc_secret_key.txt

# Verify files
cat ~/.hermes/secrets/mexc_api_key.txt  # Should show 18 chars
cat ~/.hermes/secrets/mexc_secret_key.txt  # Should show 32 chars

# Restart bot
pkill -f predator_v5.py
cd /root/mexc-scalper && python3 predator_v5.py &
```

### 4. Verification
Test backup key with quick position check:
```python
import hmac, hashlib, time, requests

API_KEY = 'mx0vglYKFYSflyEB2Y'
SECRET = 'a189628daae142c4a0a35e40b8e23c6d'

def sign_request(path, body=''):
    ts = str(int(time.time() * 1000))
    msg = API_KEY + ts + body
    sign = hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return {
        'ApiKey': API_KEY,
        'Request-Time': ts,
        'Signature': sign,
        'Content-Type': 'application/json'
    }

r = requests.get(
    'https://api.mexc.com/api/v1/private/position/open_positions',
    headers=sign_request('/api/v1/private/position/open_positions'),
    timeout=15
)
print(r.json())
```

Expected: `{"code": 0, "data": [...]}`
If 403/602: key invalid or signing wrong
If 0 positions: rotation successful

### 5. Update TRADING_MODE.md
Mark which key is active:
```markdown
# Backup: api.mexc.com (ACTIVE — primary expired June 26)
# Primary key mx0vglhMFsVtoy3GIi...[truncated]
```

## Key Insights
1. **Backup keys in TRADING_MODE.md** survive gateway restarts (isolated profile pattern)
2. **Backup key worked immediately** with api.mexc.com — no signing changes needed
3. **Bot blind period** — positions can move against you while bot can't manage them
4. **Proactive monitoring** — check key expiry dates in MEXC dashboard weekly

## Prevention
- Generate 2-3 API keys upfront
- Store in TRADING_MODE.md (survives restarts)
- Test rotation flow before primary expires
- Set calendar reminder for key expiry (MEXC keys expire after 90 days by default)

## Related
- See main SKILL.md for endpoint routing (api.mexc.com vs contract.mexc.com)
- See `close-position-fix.md` for position management during recovery
