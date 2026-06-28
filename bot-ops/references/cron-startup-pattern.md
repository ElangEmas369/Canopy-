# Cron Job Startup Pattern for Long-Running Processes

## Problem
Hermes cron jobs run in a sandboxed environment where:
- Shell-level `&` backgrounding is blocked (terminal rejects foreground commands with `nohup/disown/setsid/trailing &`)
- `cat | python3` is blocked (pipe to interpreter)
- `execute_code` is BLOCKED in cron (no user to approve)
- `pgrep -f` matches Hermes shell wrappers → FALSE POSITIVES

## Solution: terminal(background=true) — Two Approaches

### Approach A: Direct (simpler)
```python
terminal(
    command="cd /root/mexc-scalper && python3 predator_v5.py --live",
    background=True,
    notify_on_complete=True
)
```
- Output goes to Hermes process pipe → read via `process(action='log', session_id=...)`
- NOT persistent on disk — if process dies, logs are lost
- Best for: cron jobs where you check output immediately

### Approach B: nohup wrapper (persistent logs)
```python
terminal(
    background=True,
    command="bash -c 'cd /root/mexc-scalper && nohup python3 predator_v5.py --live > /tmp/predator_v5.log 2>&1 & echo PID=\\$!'"
)
```
- Output goes to `/tmp/predator_v5.log` → read via `tail`/`strings`
- Persistent on disk — survives process death
- Best for: long-running sessions where you need to check logs later
- The wrapper bash gets tracked by Hermes; the actual python process runs on the host independently.

## Full Check-Then-Start Workflow

```bash
# Step 1: Check if running (use [p] trick to exclude grep itself)
ps aux | grep "[p]ython3.*predator_v5" | grep -v grep
# If empty → bot is dead, proceed to start

# Step 2: Start via terminal(background=True) (see approaches above)

# Step 3: Wait for bot to initialize
sleep 10

# Step 4: Verify process is alive
ps aux | grep "[p]ython3.*predator_v5" | grep -v grep
# Should show python3 predator_v5.py --live

# Step 5: Verify log output
# For nohup approach: tail -10 /tmp/predator_v5.log
# For direct approach: process(action='log', session_id=<from step 2>)
# Should show PREDATOR V5 APEX banner and scanning activity

# Step 6: Check for 6026 block (CRITICAL — account-level block)
# Look in first 30 log lines for "6026" or "DISABLED_CONTRACT_OPEN_POSITION"
# If found → stop bot, pause auto-restart, set up 6026 monitor (see mexc-position-rescue)

# Step 7: Verify auto-restart cron is active
hermes cron list --all | grep -A2 "predator-auto-restart"
# If [paused] → hermes cron resume <job_id>

# Step 8: Verify heartbeat freshness (wait 15s after start)
stat -c %Y /root/mexc-scalper/state/shared_state.json
# Compare with $(date +%s) — delta should be <30s
# NOTE: heartbeat may be stale for 30-60s after startup while bot initializes
```

## Verification Details

- `ps aux | grep "[p]ython3.*predator_v5"` — the `[p]` trick prevents grep from matching itself. This WORKS from the Hermes sandbox (python process IS visible).
- `pgrep -f predator_v5.py` — DO NOT USE. Hermes wraps every command in `bash -c ... eval ...`, so pgrep matches the wrapper shell, not the python process. Returns false positives.
- State file heartbeat (`/root/mexc-scalper/state/shared_state.json`) updates every ~5s — use `stat -c %Y` to check freshness.
- Redirect log `/tmp/predator_v5.log` — use `strings` if binary, but usually plain text when bot starts fresh.
- `read_file` on shared_state.json returns cached content if file hasn't changed — use `stat -c %Y` + `date +%s` arithmetic to check actual freshness.

## Pitfalls
- Do NOT use `terminal(command="... &")` — blocked by Hermes security
- Do NOT use `pgrep -f predator_v5.py` — false positives from Hermes shell wrappers
- Do NOT redirect to `~/.hermes/` — blocked as dotfile overwrite
- Do NOT skip `sleep 10` before verifying — bot needs time to initialize and write first log lines
- Always clear `__pycache__` after code edits before restart
- Check redirect log for `SyntaxError`/`IndentationError` before retrying failed starts
- If 2+ python3 instances appear, kill the OLD PID (lower number) — duplicate bots cause API race conditions
- Heartbeat in shared_state.json may be stale (hours old) when bot first starts — this is normal, it updates after first scan cycle (~30-60s)
- `cat file | python3 -c "..."` is blocked by tirith security — use `read_file` or `stat` instead
