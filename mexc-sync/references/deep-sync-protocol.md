# Deep Sync Protocol — Complete Reference

## When to Run
- User requests "Deep Sync" or "Jalankan Deep Sync Protocol"
- After API key rotation
- After bot crash/restart
- When state drift suspected

## Phase 1: Rekonsiliasi MEXC vs Local State
1. Read MEXC balance via API (GET /api/v1/private/account/assets)
2. Read shared state (~/.hermes/data/shared_state.json)
3. Read file state (/root/mexc-scalper/state/state.json)
4. Compare: MEXC equity vs shared state capital vs file state capital
5. Report: BALANCED or DRIFT

## Phase 2: Audit Config vs Code
Check CONFIG dict matches plan:
- session_filter: True
- best_sessions: [(7,13), (13,21)]
- dead_zones: [(0,7), (21,24)]
- allowed_scores: [13, 16, 19]
- secondary_scores: [14, 15, 17, 18, 20]
- leverage: 30, max_positions: 3
- tp_pct: 0.05, sl_pct: 0.02
- dynamic_tp_by_score: True
- tp_score_map: {13:0.05, 16:0.07, 19:0.10}
- us_open_trap_hours: [13]
- btc_session_filter: True
- smart_reentry: False

## Phase 3: Cek Infra & Cron
- RAM: free > 200MB
- Disk: < 95% used
- Bot: PID running, heartbeat < 60s
- Cron: <= 12 jobs, no errors

## Phase 4: Report
Structured report with VERDICT (HEALTHY or NEEDS ATTENTION)
