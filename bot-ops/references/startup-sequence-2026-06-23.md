# Bot Startup Sequence — Updated 2026-06-24

## Correct Startup Order
1. **Kill ALL old PIDs**: `ps aux | grep predator_v5 | grep -v grep` — kill ALL python3 instances
2. **Wait 2s** for processes to die
3. **Reset state** if needed: update `/root/mexc-scalper/state/state.json` with real balance
4. **Verify no duplicates**: `ps aux | grep predator_v5 | grep -v grep` — must be empty
5. **Verify auto-restart cron**: `hermes cron list --all | grep predator-auto-restart` — if `[paused]`, resume it with `hermes cron resume <job_id>`
6. **Start bot**: Use `terminal(command="cd /root/mexc-scalper && python3 predator_v5.py --live", background=True, notify_on_complete=True)` or nohup wrapper for persistent logs (see `references/cron-startup-pattern.md`)
7. **Wait 10s** for startup
8. **Verify process**: `ps aux | grep "[p]ython3.*predator_v5"` — must show python3 process
9. **Check for 6026**: Read first 30 lines of log output (process log or /tmp/predator_v5.log) — look for "6026" or "DISABLED_CONTRACT_OPEN_POSITION". If found → stop bot, pause auto-restart, set up 6026 monitor (see `mexc-position-rescue` skill)
10. **Wait 30s** for first scan cycle
11. **Verify heartbeat**: `stat -c %Y /root/mexc-scalper/state/shared_state.json` vs `$(date +%s)` — delta <60s. NOTE: heartbeat may be stale for 30-60s after startup while bot initializes its first cycle.

## Common Mistakes
- Starting new bot without killing old ones → duplicate PIDs, API race conditions
- `tail /tmp/predator.log` shows garbage → log is binary, use `strings` command
- Balance shows stale value → normal on first load, syncs on next scan cycle (~30s)
- `smart_tp_sl.py` missing → UPGRADES_LOADED = False silently. Verify imports first.
- Auto-restart cron is paused → bot starts but won't auto-restart after crash. Always verify cron status.
- 6026 block on startup → bot runs but can't open any positions. Check first 30 log lines for "6026".
- Heartbeat in shared_state.json is hours old → normal if bot was down. Updates after first scan cycle (~30-60s).
- `read_file` returns cached content → use `stat -c %Y` to check actual file modification time.

## Log Reading
```bash
# For nohup approach: ALWAYS use strings — log file may have ANSI codes
strings /tmp/predator.log | tail -20
strings /tmp/predator.log | grep -E "ENTRY|SL|TP|signal|score"

# For direct approach: use process tool
# process(action='log', session_id=<session_id>, limit=30)
```
