# MEXC Position Close Endpoint Investigation — 2026-06-22

## Problem
All tested MEXC Futures API endpoints for closing positions return 404.

## Tested Endpoints (ALL 404)
- POST /api/v1/private/position/close with positionId in body → 404
- POST /api/v1/private/position/close with positionId in query → 404
- POST /api/v1/private/position/closeAll with empty body → 404
- POST /api/v1/private/position/liquidate with positionId → 404
- POST /api/v1/private/position/liquidate with symbol → 404
- POST /api/v1/private/order/cancel with orderId → 404
- POST /api/v1/trade/cancel with symbol → 404
- POST https://futures.mexc.com/api/v1/private/position/close → 404
- POST https://futures.mexc.com/api/v1/trade/close → 404

## What WORKS
- GET /api/v1/private/position/open_positions → Returns position data (code=0)
- GET /api/v1/private/account/assets → Returns balance (code=0)

## Signature Format (CONFIRMED WORKING)
```python
import hmac, hashlib, time

ts = str(int(time.time() * 1000))
sig = hmac.new(secret.encode(), (api_key + ts).encode(), hashlib.sha256).hexdigest()
headers = {
    'ApiKey': api_key,
    'Request-Time': ts,
    'Signature': sig,
    'Content-Type': 'application/json'
}
```

## Workaround
To close positions, user must:
1. Close manually in MEXC app, OR
2. Place a reverse MARKET order via /api/v1/private/order/submit (may be WAF-blocked)

## Lesson
Don't waste time trying multiple close endpoints — they all 404. The correct endpoint is not documented or doesn't exist in the standard API. Need to investigate MEXC's official SDK or documentation for the correct close mechanism.
