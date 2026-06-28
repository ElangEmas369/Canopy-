# State File Desync Incident — 2026-06-25

## What happened
- Bot was running (PID 20262, started ~2026-06-25 00:30 UTC)
- State file at `~/.hermes/data/predator_v5_state.json` had:
  - `active_trades: []` (empty)
  - `capital: $17.72`
  - `saved_at: 2026-06-24T17:22:37` (stale — 7+ hours old)
- MEXC API showed:
  - BTC_USDT LONG position: Entry $59,416.10, 43 contracts, 30x leverage, margin $8.72
  - Unrealized PnL: +$6.53
  - Equity: $17.70, Available: $2.58
- Bot was rejecting ALL new entries with "insufficient balance (need $X, have $2.58)"
- Bot had NO TP/SL management for the BTC LONG position
- Only MEXC liquidation price ($56,870) was the safety net

## Root cause
State file was likely overwritten/reset during a previous session (compaction, restart, or manual reset). The bot loaded the empty state and didn't know about the existing MEXC position.

## Detection method
1. Checked state file → `active_trades: []`
2. Used MEXC futures API (header auth: `ApiKey`, `Request-Time`, `Signature`) to get real positions
3. Found BTC LONG with +$6.53 unrealized PnL
4. Compared: MEXC has 1 position, state has 0 → DESYNC!

## Key API details
- Endpoint: `https://api.mexc.com/api/v1/private/position/open_positions`
- Auth: Header-based (`ApiKey`, `Request-Time`, `Signature`)
- Response fields:
  - `positionType: 1` = LONG, `2` = SHORT
  - `holdAvgPrice` = entry price
  - `unRealizedPnl` = actual unrealized PnL (USE THIS, not `profitRatio`)
  - `profitRatio` = unreliable (showed -0.023 when position was actually +2.5% profitable)
  - `im` = initial margin
  - `liquidatePrice` = liquidation price
  - `holdVol` = position volume

## Pitfall: Spot vs Futures API
- `api.mexc.com/api/v3/account` = SPOT endpoint, uses `X-MEXC-APIKEY` + query param signing → returns 400 with futures signing
- `api.mexc.com/api/v1/private/account/assets` = FUTURES endpoint, uses `ApiKey`+`Request-Time`+`Signature` headers → WORKS
- Always use futures endpoints for bot operations

## Resolution
- User confirmed position was safe ("Posisi masih aman")
- State file needs to be synced with MEXC reality (pending user approval)
- Bot needs restart after sync to load new state
