# Stalled Bot Detection — 2026-06-24

## Scenario

Bot PID is alive (`pgrep -f predator_v5.py` returns PIDs) but it's not actually trading. Log shows only blacklist blocks and scan cycles with no orders placed.

## Detection Commands

```bash
# 1. Confirm bot process is alive
pgrep -f predator_v5.py

# 2. Check if any trades have been placed recently
# (Look for ENTER, order_submit, or trade execution in logs)
grep -c "ENTER\|ORDER\|SUBMIT" /tmp/predator.log
# If 0 for hours → bot is stalled

# 3. Check API connectivity
python3 -c "
import hmac, hashlib, time, json, subprocess, ssl
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

with open('/root/mexc-scalper/secrets/api_keys.json') as f:
    keys = json.load(f)
active = [k for k in keys if k.get('status')=='active'][0]
ak, sk = active['api_key'], active['api_secret']

ts = str(int(time.time()*1000))
sig = hmac.new(sk.encode(), (ak + ts).encode(), hashlib.sha256).hexdigest()
cmd = ['curl', '-s', '-L', '--max-time', '15',
       '-H', f'ApiKey: {ak}', '-H', f'Request-Time: {ts}', '-H', f'Signature: {sig}',
       'https://api.mexc.com/api/v1/private/account/assets']
r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
try:
    d = json.loads(r.stdout)
    print(f'code={d.get(\"code\")} msg={d.get(\"message\",\"\")}')
    if d.get('code') == 0:
        for a in (d.get('data') or []):
            if a.get('currency') == 'USDT':
                print(f'Balance: \${a.get(\"availableBalance\")}')
except:
    print(f'Non-JSON response: {r.stdout[:200]}')
"

# 4. Check log age of last meaningful activity
tail -5 /tmp/predator.log
```

## Failures That Cause Stalling

| Failure | Log Pattern | API Test Result |
|---------|-------------|-----------------|
| API key expired (402) | Bot loads state, then only scan loops | `{"code": 402, "message": "API Key expired"}` |
| API key WAF-blocked (403) | POST calls fail, GET may work | 403 on order/submit, 200 on positions |
| State file corruption | Bot loads with capital=0 or stale values | API returns valid balance but state doesn't match |
| Log file rotated | Old log has trades, new log doesn't | N/A — check file mtimes |

## Resolution by Cause

### API Key Expired (402)
1. Generate new key in MEXC UI
2. Update `/root/mexc-scalper/secrets/api_keys.json`
3. Restart bot (`kill <PID>`, then `cd /root/mexc-scalper && nohup python3 predator_v5.py > /tmp/predator.log 2>&1 &`)

### Key Works But Bot Stalled
1. Bot may have loaded stale state — restart it
2. Check if config loaded correctly from log startup lines
3. Check if scan sessions are active (OFF_HOURS is normal, but prolonged inactivity during active hours = problem)

## Related Incidents
- 2026-06-22: WAF blocking POST → zombie_closer.py broken
- 2026-06-13: Zombie bot cascade (bot tracked positions that MEXC had closed)
- 2026-06-24: Key expired, bot running but zero trades for 24+ hours
