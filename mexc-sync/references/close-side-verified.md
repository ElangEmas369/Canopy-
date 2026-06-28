# MEXC Close Position — Verified 2026-06-24

## CRITICAL: side=2 NOT side=4

`side=4` returns error 2009. Use `side=2` for ALL closes.

```
side=1: Open Long ✅
side=2: Close ANY ✅  
side=3: Open Short ✅
side=4: DOES NOT WORK ❌
```

## Close Order Format
```json
{"symbol":"XXX_USDT","price":"0","vol":N,"side":2,"type":5,"openType":2,"leverage":30}
```

## Error 6026
Temporary block from risk control. Clears 30min-2hrs. Stop bot, monitor, auto-restart.
