# API Key False "Expired" Bug (2026-06-28)

## What Happened
Agent wrote a test script to check MEXC API key status. Script returned `NameError: name 'SK' is not defined`. Agent misinterpreted this as "API key expired" and asked user to generate new key.

User corrected: "Api tidak exp" and "bouxit api mexc yang exp tapi loe yang lupa caranya".

## The Bug
```python
# Line 4 got corrupted during write_file - missing SK definition!
AK = "mx0v...3c6d"  # Should have been two separate lines

# Line 11 references SK which was never defined
sig = sign(SK, AK + ts)  # NameError!
```

## Lesson
**ALWAYS verify your test script has no bugs before concluding external failure.**

### Debugging Order
1. Check for Python errors FIRST (syntax, NameError, etc.)
2. Check HTTP status code
3. Check API response body
4. Check error code in response
5. ONLY THEN conclude key/endpoint issue

### Safe Key Testing Pattern
```python
import time, hmac, hashlib, requests

AK = open("/root/.hermes/secrets/mexc_api_key.txt").read().strip()
SK = open("/root/.hermes/secrets/mexc_secret_key.txt").read().strip()

def test_key():
    ts = str(int(time.time() * 1000))
    sig = hmac.new(SK.encode(), (AK + ts).encode(), hashlib.sha256).hexdigest()
    H = {"ApiKey": AK, "Request-Time": ts, "Signature": sig}
    
    r = requests.get("https://api.mexc.com/api/v1/private/account/assets", 
                     headers=H, timeout=10, verify=False)
    
    if r.status_code == 200 and r.json().get("success"):
        for a in r.json().get("data", []):
            if a.get("currency") == "USDT":
                return True, a.get("availableBalance", 0)
    return False, r.text[:200]

ok, result = test_key()
print(f"Key OK: {ok}, Balance/Error: {result}")
```

## User Frustration Pattern
User gets extremely frustrated when:
1. Agent asks for API keys repeatedly
2. Agent claims key is expired without verifying
3. Agent wastes time on false problems

**Remember: The key is in MASTER_CONFIG.json + ~/.hermes/secrets/. NEVER ask where it is.**
