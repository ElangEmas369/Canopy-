# Daily Bot Start from Cron Job

## Context
The `🚀 Bot Start (19:55 WIB)` cron job fires daily at 12:55 UTC. It runs as a scheduled Hermes agent session with the `hermes-agent` skill loaded.

## Workflow
1. Check if bot already running: `ps aux | grep "[p]ython3.*predator_v5" | grep -v grep`
2. If NOT running → start via `terminal(command="cd /root/mexc-scalper && python3 predator_v5.py --live", background=True, notify_on_complete=True)`
3. Wait 10s, verify PID exists
4. Check for 6026 errors in first log output
5. Resume auto-restart cron if paused: `hermes cron resume <job_id>`
6. Verify heartbeat in shared_state.json

## Key Learnings (2026-06-24)
- **Auto-restart cron may be paused** from previous session (e.g., after 6026 block). Always check and resume.
- **shared_state.json heartbeat can be stale** (hours old) when bot starts. This is normal — it updates after first scan cycle (~30-60s). Don't report as error.
- **6026 block on startup** means the account is still blocked from previous session. Bot will scan but can't open positions. Report this clearly — user needs to resolve on MEXC.
- **Process output routing**: `terminal(background=true)` sends output to Hermes process pipe, not to log file. Use `process(action='log')` to read it.
- **Report format**: Include PID, auto-restart status, 6026 status, capital, and open positions.

## Example Report
```
🚀 BOT STARTED — PID [X], auto-restart ACTIVE, trading session 13:00-21:00 UTC

⚠️ CRITICAL: MEXC Error 6026 — All position opens blocked
[details]

Status summary:
| Item | Status |
|------|--------|
| Bot process | ✅ Running (PID X, uptime Ymin) |
| Auto-restart cron | ✅ Resumed |
| Signal scanning | ✅ Working |
| Position opens | ❌ All blocked (6026) |
| Capital | $XX.XX |
| Open positions | N |
```
