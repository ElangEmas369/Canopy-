# MEXC Balance False Negative — USDT Array Index Bug (2026-06-28)

## Incident Summary

**Duration**: ~50 tool calls (1.5 hours debugging)  
**Symptom**: Bot synced to $5.2355, but manual balance checks consistently returned $0  
**Root Cause**: Checking `data['data'][0]` instead of iterating to find USDT  
**Impact**: False "account is empty" diagnosis, blocked bot verification  

## Timeline

1. **Initial state**: Bot log showed `Sync: $11.5 → $5.2355` ✅
2. **Manual verification**: Direct API test showed `equity: $0` ❌
3. **Key testing**: Tested both active keys (`mx0vglYKFYSflyEB2Y`, `mx0vglhMFsVtoy3GIi`) → both $0
4. **Endpoint testing**: Tried `api.mexc.com`, `contract.mexc.com` → still $0
5. **Spot vs Futures**: Checked both account types → $0
6. **Transfer check**: Looked for pending transfers → none
7. **Finally discovered**: Bot code iterates to find USDT, manual tests checked index [0]

## The Bug Pattern

### ❌ WRONG (what I did):
```python
r = requests.get('https://api.mexc.com/api/v1/private/account/assets', 
                 headers=headers, timeout=10)
data = r.json()

if data.get('success'):
    assets = data.get('data', [])
    # BUG: Assumes USDT is first in array
    balance = assets[0].get('availableBalance', 0)
    equity = assets[0].get('equity', 0)
    
    print(f'Balance: ${balance}')  # Shows $0 (wrong currency!)
```

### ✅ CORRECT (what bot does):
```python
r = requests.get('https://api.mexc.com/api/v1/private/account/assets',
                 headers=headers, timeout=10)
data = r.json()

if data.get('success'):
    assets = data.get('data', [])
    
    # CORRECT: Find USDT in array
    usdt = [a for a in assets if a.get('currency') == 'USDT']
    
    if usdt:
        balance = float(usdt[0].get('availableBalance', 0))
        equity = float(usdt[0].get('equity', 0))
        print(f'Balance: ${balance}')  # Shows $5.2355 ✅
    else:
        print('No USDT account found')
```

## Actual API Response Structure

```json
{
  "success": true,
  "code": 0,
  "data": [
    {
      "currency": "BTC",
      "equity": 0,
      "availableBalance": 0,
      ...
    },
    {
      "currency": "ETH",
      "equity": 0,
      "availableBalance": 0,
      ...
    },
    {
      "currency": "USDT",
      "equity": 5.23545427,
      "availableBalance": 5.2354542789765,
      ...
    },
    {
      "currency": "USDC",
      "equity": 0,
      ...
    },
    ...
    // Total: ~45 currencies
  ]
}
```

**Key observation**: USDT was at index **~20-30** in the array, not index [0]. The order is not guaranteed and varies by account.

## Why This Was Hard to Diagnose

1. **Bot worked correctly** — used proper iteration pattern from day 1
2. **My manual tests were wrong** — but I didn't know the bug was in MY code
3. **Both methods used same key** — so seemed like account issue, not code issue
4. **Response was "valid"** — both returned `success: true, code: 0`
5. **No obvious error** — checking [0] doesn't raise an exception, just returns wrong currency

## Prevention Steps

1. **ALWAYS iterate multi-currency endpoints**:
   - `/api/v1/private/account/assets` returns ALL currencies
   - `/api/v1/private/account/asset?currency=USDT` returns USDT only (but less reliable)
   - Never assume array order

2. **When testing bot's API pattern, USE THE BOT'S CODE**:
   ```python
   import sys
   sys.path.insert(0, '/root/mexc-scalper')
   from predator_v5 import MEXCClient
   
   # Use bot's client directly — zero mismatch risk
   client = MEXCClient(...)
   result = client.get('/api/v1/private/account/assets', auth=True)
   ```

3. **Verify test assumptions early**:
   - If bot shows $5.23 but manual test shows $0, suspect TEST BUG first
   - Check: am I testing the same way the bot does?
   - Check: am I looking at the same field/index?

4. **Document API response structure**:
   - Don't assume documented field order matches reality
   - Capture actual response samples for reference
   - Note which fields are arrays vs single values

## Lesson Learned

**Trust the bot's working code over manual ad-hoc tests**. When bot shows a balance and manual tests show zero, the divergence is more likely a testing methodology bug than an API issue. The bot's MEXCClient has been battle-tested over hundreds of hours; a quick manual curl/requests test hasn't.

## Related Files

- Bot's balance check: `/root/mexc-scalper/predator_v5.py` line 1682-1689
- Skill pitfall: mexc-sync #30
