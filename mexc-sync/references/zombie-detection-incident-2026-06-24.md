# Zombie Detection — Incident Log

## 2026-06-24: Blacklisted BTC Zombie

**Detected by:** Manual zombie detection procedure (cron `zombie_closer.py` missing)

**Findings:**
- MEXC had 1 open position: `BTC_USDT LONG 5 contracts @ $63,285.40 (20x leverage)`
- Bot `shared_state.json` showed `active_trades: []` — no positions tracked
- BTC_USDT is in the bot's pair blacklist
- Position was small: ~0.005 BTC notional, ~$1.61 margin, unrealized PnL -$0.147
- Balance drift: $0.07 (within $0.50 threshold)

**Diagnosis:** Leftover position from a previous session or manual trade. Bot correctly ignores it (blacklisted). No action needed beyond reporting.

**Key learning:** When `zombie_closer.py` is missing, the manual detection procedure (compare MEXC API positions vs bot state) is sufficient. Blacklisted zombies are harmless — they consume margin but won't interfere with bot trading.

**Script status:** `zombie_closer.py` and `force_sync.py` confirmed missing from `/root/.hermes/scripts/`. Watchdog cron should be updated to reference the manual procedure instead.
