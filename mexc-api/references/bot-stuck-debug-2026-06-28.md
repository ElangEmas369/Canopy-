# Bot Stuck After Sync — Debugging Notes (2026-06-28)

## Symptom
Bot launches, syncs balance ($5.2355), then stops logging. Process alive but no further output. User thinks bot is stuck/dead.

## Root Cause Analysis

### 1. Log File Location Confusion
Bot uses TWO log handlers:
- `FileHandler` → `/root/.hermes/logs/mexc_predator_v5.log`
- `StreamHandler` → stdout (captured by `tee` or background process)

**Problem:** Agent was checking `/tmp/predator_v5_live.log` (stdout) which only showed startup messages. The real log was in `/root/.hermes/logs/`.

**Fix:** Always check BOTH locations:
```bash
tail -50 /root/.hermes/logs/mexc_predator_v5.log  # File handler
tail -50 /tmp/predator_v5_live.log                 # stdout (if tee'd)
```

### 2. DEBUG Logs Hidden
Bot uses `log.debug()` for scan cycle messages, but logging level is INFO. So scan activity is invisible.

**Fix:** Either:
- Change `level=logging.INFO` to `level=logging.DEBUG` in basicConfig
- Or change `log.debug()` to `log.info()` for scan messages

### 3. Zombie Processes
Multiple bot instances running simultaneously from failed restart attempts:
```
PID 4246  - bash wrapper (from background=true)
PID 4388  - python3 predator_v5.py
PID 11674 - bash wrapper (another instance)
PID 11708 - python3 -c "..."
```

**Fix:** Always kill ALL related processes:
```bash
pkill -f "predator"  # Kill all predator processes
sleep 2
ps aux | grep predator | grep -v grep | wc -l  # Verify 0
```

### 4. SIGTERM Handler
Bot has signal handler that sets `self.running = False` on SIGTERM. If something sends SIGTERM (like pkill), bot exits gracefully without error.

**Fix:** Use `kill -9` only when necessary. For graceful stop, use `kill -15` (SIGTERM) or Ctrl+C.

## Debugging Checklist
When bot appears stuck:
1. Check process: `ps aux | grep predator | grep -v grep`
2. Check file log: `tail -50 /root/.hermes/logs/mexc_predator_v5.log`
3. Check stdout log: `tail -50 /tmp/predator_v5_live.log`
4. Check for zombies: `ps aux | grep predator | wc -l` (should be 2: bash + python)
5. Test API directly: `python3 /root/TRADING_MODE_ISOLATED/tmi.py balance`
6. Run single cycle test: `python3 -c "from predator_v5 import PredatorV5; bot=PredatorV5(dry_run=False); bot.run_cycle()"`

## Key Insight
Bot was NOT stuck — it was running but logging to a different file than expected. The scan cycles were happening (visible in file log) but agent was looking at stdout log which only had startup messages.
