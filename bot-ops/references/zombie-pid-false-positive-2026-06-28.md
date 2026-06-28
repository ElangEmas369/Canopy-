# Zombie PID False Positive — 2026-06-28

## Incident
Monitor cron reported `pgrep -f predator_v5.py` returned exit code 0 with PID 560. Initial assessment was "bot running." But:
- `ps -p 560` → PID not found
- `ps aux | grep predator_v5` → no match
- `pgrep -f predator_v5.py` returned new PIDs (2236, 2450, 2457, 2461) that were all gone/zombie
- **Bot was actually DOWN** — last log entry was 45+ minutes old

## Root Cause
`pgrep -f` matches against `/proc/<pid>/cmdline` which can include:
1. Zombie processes (exited but not yet reaped by parent)
2. Wrapper shells (`bash -c 'eval "..."'`) that have the pattern in their args but the actual python process is gone
3. Hermes internal routing PIDs

## Why This Is Dangerous
In a monitoring cron, `pgrep -f predator_v5.py && echo "alive"` gives a FALSE POSITIVE — exit code 0 with no actual bot running. Downstream logic assumes everything is fine and stays silent while the bot is dead and losing money on unmonitored positions.

## Bulletproof Check (Use in ALL monitor crons)
```bash
# Triple-check: ps + proc cmdline + log freshness
ALIVE_PIDS=$(ps aux | grep "[p]ython3.*predator_v5" | awk '{print $2}')
if [ -n "$ALIVE_PIDS" ]; then
    for p in $ALIVE_PIDS; do
        [ -r "/proc/$p/cmdline" ] || ALIVE_PIDS=""
    done
fi

if [ -n "$ALIVE_PIDS" ]; then
    echo "✅ Bot ALIVE | PIDs: $ALIVE_PIDS"
else
    echo "❌ Bot DOWN"
    # Alert logic here
fi

# Cross-check: log should be <5 min old if bot is alive
LOG_AGE=$(( $(date +%s) - $(stat -c %Y /tmp/predator_v5_live.log 2>/dev/null || echo 0) ))
echo "Log age: $LOG_AGE seconds"
# If log age > 300s AND no alive PID → definite DOWN
```

## Timestamps of Incident
- 15:55 UTC: Bot started, synced balance $11.50 → $5.23
- 15:55 UTC: Only log entry — no trades executed
- 16:40 UTC: Monitor cron detected bot down, sent alert
- **Gap**: ~45 minutes of unmonitored downtime

## Lesson
1. `pgrep -f` is NEVER reliable for confirmation — it can return exit code 0 with zombie PIDs
2. Always verify with `ps aux` + `/proc/<pid>/cmdline` readability
3. Cross-check with log freshness — process alive but log stale = zombie bot
4. When in doubt, report as DOWN — false alarms are better than missed outages
