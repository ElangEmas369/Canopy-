---
name: bot-ops
description: Bot Operations — restart, cron management, state reset, trade limiter reset. All-in-one skill for Predator V5 bot maintenance.
tags: [mexc, bot, predator, ops, maintenance, cron, restart, state, limiter]
triggers:
  - "restart bot"
  - "bot mati"
  - "cron job"
  - "state reset"
  - "trade limiter"
  - "bot stuck"
  - "schedule task"
---

# BOT OPS — All-in-One Bot Operations

## 1. Bot Restart Workflow

### Quick Restart
```bash
# 1. Fix paused state (CRITICAL)
python3 -c "
import json
d=json.load(open('/root/.hermes/data/predator_v5_state.json'))
if d['risk']['paused']:
    d['risk']['paused'] = False
    d['risk']['pause_reason'] = ''
    d['risk']['consecutive_sl'] = 0
    json.dump(d, open('/root/.hermes/data/predator_v5_state.json','w'), indent=2)
    print('✅ Fixed: paused=False')
"

# 2. Kill bot
pkill -9 -f "predator_v5.py --live" 2>/dev/null; sleep 3

# 3. Clear pycache
rm -rf /root/mexc-scalper/__pycache__

# 4. Start fresh (use terminal(background=true) in Hermes)
# terminal(command="cd /root/mexc-scalper && python3 predator_v5.py --live", background=True, notify_on_complete=True)

# 5. Verify (wait 20s)
sleep 20 && tail -15 /root/.hermes/logs/mexc_predator_v5.log
```

### Bot Stop (No Restart)
```bash
# 1. Close all positions first (load keys from project-local secrets)
cd /root/mexc-scalper && python3 -c "
import json, hmac, hashlib, time, requests
from urllib.parse import urlencode
keys = json.load(open('secrets/api_keys.json'))
active = [k for k in keys if k.get('status')=='active' and k.get('type')=='futures'][0]
ak, sk = active['api_key'], active['api_secret']
ts = str(int(time.time()*1000))
sig = hmac.new(sk.encode(), urlencode({'timestamp': ts}).encode(), hashlib.sha256).hexdigest()
headers = {'X-MEXC-APIKEY': ak}
r = requests.get(f'https://contract.mexc.com/api/v1/private/position/openPositions?timestamp={ts}&signature={sig}', headers=headers, timeout=10)
positions = r.json().get('data', []) or []
for p in positions:
    cid = p.get('positionId')
    if cid:
        sig2 = hmac.new(sk.encode(), urlencode({'positionId': cid, 'timestamp': ts}).encode(), hashlib.sha256).hexdigest()
        requests.post(f'https://contract.mexc.com/api/v1/private/position/close?positionId={cid}&timestamp={ts}&signature={sig2}', headers=headers, timeout=10)
        print(f'Closed {p.get(\"symbol\")}')
print(f'Done: {len(positions)} closed')
"

# 2. Kill safely (cron-safe, no pkill -f self-kill)
PIDS=$(ps aux | grep "[p]ython3.*predator_v5" | awk '{print $2}')
[ -n "$PIDS" ] && echo "$PIDS" | xargs kill -9 2>/dev/null
sleep 2
ps aux | grep "[p]ython3.*predator_v5" | grep -v grep || echo "STOPPED"
```

### Health Check (Reliable)
```bash
# Process: NEVER use pgrep -f (false positives from Hermes shell)
ps aux | grep "[p]ython3.*predator_v5" | awk '{print $2}'

# Heartbeat: check state/shared_state.json FIRST (heartbeat key, ~5s updates)
echo $(( $(date +%s) - $(stat -c %Y /root/mexc-scalper/state/shared_state.json) ))

# Real log (authoritative liveness — check redirect log if bot started via nohup)
# IMPORTANT: log file is binary! Use `strings` to read it
strings /tmp/predator_v5.log 2>/dev/null | tail -5 || strings /root/.hermes/logs/mexc_predator_v5.log 2>/dev/null | tail -5
```

**Note on log paths**: When bot is started via `nohup python3 predator_v5.py --live > /tmp/predator_v5.log 2>&1 &`, output goes to `/tmp/predator_v5.log`. The Hermes log at `~/.hermes/logs/mexc_predator_v5.log` only gets output when started via Hermes `terminal(background=true)`. Current session uses `terminal(background=true)` with `tee /tmp/predator_v5_live.log` — readable via both `process(action='log')` and `tail /tmp/predator_v5_live.log`.

### Post-Start Verification (CRITICAL)
After confirming the process is alive, ALWAYS run these 3 checks:

```bash
# 1. Check for 6026 block in first log output
#    (use process(action='log') if started via terminal(background=true))
#    or: tail -30 /tmp/predator_v5.log if nohup wrapper was used
#    Look for: "6026: Position opening is unavailable until risk control verification"
#    If 6026 present → STOP bot, pause auto-restart, set up 6026 monitor (see mexc-position-rescue)

# 2. Verify auto-restart cron is ACTIVE (not paused)
hermes cron list --all | grep -A2 "predator-auto-restart"
# If [paused] → hermes cron resume <job_id>

# 3. Verify heartbeat freshness (wait 15s after start, then check)
stat -c %Y /root/mexc-scalper/state/shared_state.json
# Compare with $(date +%s) — delta should be <30s
# NOTE: heartbeat may be stale for 30-60s after startup while bot initializes
# If still stale after 60s → check process log for errors (import failures, API errors)
```

### Pitfalls
- **WRONG STATE FILE** (2026-06-27 CRITICAL): PRIMARY state file is `~/.hermes/data/predator_v5_state.json`, NOT `/root/mexc-scalper/state/state.json`. When debugging ghost positions or state issues, ALWAYS edit the PRIMARY file. Bot config line 201 shows: `'state_file': os.path.expanduser('~/.hermes/data/predator_v5_state.json')`. Editing secondary files has NO EFFECT because bot never reads them. Verify which file bot is using BEFORE making state edits.
- **Duplicate PIDs**: ALWAYS check `ps aux | grep predator_v5 | grep -v grep` — if 2+ python3 instances running, kill OLD PIDs (higher PID numbers). Duplicate bots cause race conditions on API calls.
- **Log file is binary**: `/tmp/predator.log` is NOT plain text — it contains ANSI escape codes and null bytes. Always `strings /tmp/predator.log | grep ...` or `strings /tmp/predator.log | tail -20`. `tail -f` and `cat` will show garbage.
- **Balance mismatch with MEXC app**: Bot may show stale balance from state.json on first load. It syncs from MEXC API on next scan cycle. If mismatch persists >2 min after restart, force kill + restart bot.
- **Existing positions not tracked (zombies)**: Bot has no position reconciliation on startup. If positions exist in MEXC from a previous session (before bot restart), the bot won't track or TP/SL them. These are "zombie positions." Detection procedure: load `mexc-sync` skill → run Zombie Detection (Manual Procedure) to compare MEXC API positions vs `shared_state.json` active_trades. Response: blacklisted-pair zombies are harmless (report only), non-blacklisted zombies need immediate close via reverse market order or manual MEXC close.
- **State file divergence**: Bot writes to `state/shared_state.json` (heartbeat ~5s) and `state/state.json` (on events). Hermes cron reads `~/.hermes/data/predator_v5_state.json`. These 3 files can diverge. Always check `shared_state.json` for live heartbeat, `state.json` for last event, and reconcile against MEXC API equity. Drift > $0.50 between files = stale state, sync all 3 from MEXC equity.
- **Watchdog script path mismatch**: The `predator-watchdog` cron references `/root/.hermes/scripts/zombie_closer.py` and `force_sync.py` — these DO NOT EXIST. The zombie detection protocol lives in `predator-v5-recovery` skill's inline procedure. When the watchdog fires, perform the inline check (see predator-v5-recovery → Zombie Detection & Balance Sync Protocol) rather than calling external scripts.
- **Smart TP/SL file missing**: If `smart_tp_sl.py` not in `/root/mexc-scalper/`, UPGRADES_LOADED will be False silently. Verify with `python3 -c "from smart_tp_sl import smart_sl; print('OK')"`. File may need to be copied from `~/.hermes/cache/documents/`.
- `pkill -f` in cron = self-kill. Use `ps aux | grep "[p]ython3.*predator_v5" | awk '{print $2}' | xargs kill -9`
- `pgrep -f` matches Hermes shell wrappers → FALSE POSITIVES
- Root `shared_state.json` = SNAPSHOT (stale often). PRIMARY = `state/shared_state.json` (heartbeat key, ~5s)
- `cat | python3` blocked by security. Use `stat -c %Y` + `date` arithmetic
- After code fix: ALWAYS `rm -rf /root/mexc-scalper/__pycache__`
- Dead zone stale heartbeat = NORMAL. Check session before alarming
- Low capital + stale state = Margin Guard blocking. Check real log for scanning activity
- **Script HTTP calls**: ALWAYS use defensive `.json()` handling — check `status_code` and `text` before parsing. MEXC WAF returns 403+HTML on some POST endpoints. See `mexc-sync` skill references.
- **Starting bot from cron — TWO approaches**:
  - **With nohup wrapper**: `terminal(background=True, command="bash -c 'cd /root/mexc-scalper && nohup python3 predator_v5.py --live > /tmp/predator_v5.log 2>&1 & echo PID=\\$!'")` — output goes to `/tmp/predator_v5.log` (readable via `tail`/`strings`). The wrapper bash process gets tracked by Hermes; the actual python process runs on the host.
  - **Direct (no wrapper)**: `terminal(command="cd /root/mexc-scalper && python3 predator_v5.py --live", background=True)` — output goes to the Hermes process pipe, readable via `process(action='log', session_id=...)`. Simpler but log is not persistent on disk.
  - **Verify via**: `ps aux | grep "[p]ython3.*predator_v5"` (the `[p]` trick prevents self-match). For nohup: `tail /tmp/predator_v5.log`. For direct: `process(action='log')`.
  - See `references/cron-startup-pattern.md` for full workflow.
- **`pgrep -f` is unreliable**: Hermes wraps every command in `bash -c ... eval ...`, so `pgrep -f predator_v5.py` matches the wrapper shell, not the python process. Always use `ps aux | grep "[p]ython3.*predator_v5"` instead. **CRITICAL in cron**: `pgrep -f` returns exit code 0 with the wrapper PID, so `pgrep -f predator_v5.py && echo "running"` falsely reports the bot is alive. This caused a monitor cron to miss a DOWN bot (2026-06-28 incident — see `references/zombie-pid-false-positive-2026-06-28.md`). **Even after `ps aux`, verify `/proc/<PID>/cmdline` is readable** — zombie PIDs show up in `ps` but cmdline is unreadable = dead.
- **Syntax errors prevent startup**: If bot fails to start, check `/tmp/predator_v5.log` (or the redirect log) for `IndentationError` / `SyntaxError` BEFORE retrying. Common after code edits: unindented blocks, missing colons. Fix the `.py` file, clear `__pycache__`, then restart.
- **Exchange SL parameter order bug (2026-06-26)**: `set_sl_for_position()` in `exchange_sl.py` has signature `(sym, position_id, sl_price, direction, sl_pct=None, vol=None)`. Calling it with wrong parameter order causes "too many values to unpack (expected 2)" error. Correct call: `set_sl_for_position(sym, None, sl_price, sig['direction'], sig['sl_pct'], vol)` where `sl_price` is calculated as `sig['price'] * (1 - sig['sl_pct'] if direction==1 else 1 + sig['sl_pct'])`.
- **close_all.py uses urllib, NOT requests**: Updated 2026-06-24. Uses `urllib.request` + `ssl.CERT_NONE` + `api.mexc.com` direct. No external deps needed. Uses side=4 primary, side=2 fallback. If close_all.py fails, check which side code works on current API key.
- **Watchdog false readings when CF Worker dies**: If watchdog reports `$0.00 balance` and `6026 blocked: False` but bot is actually blocked, the watchdog is using MEXCClient with dead CF Worker (403). Fix: watchdog must use `urllib.request` with `api.mexc.com` direct, NOT MEXCClient (which depends on cf_worker config). Also handle `real_balance = -1` as "check failed", not "$0".
- **Session PnL accumulates on restart (2026-06-25)**: `record_trade()` adds pnl to `session_pnl`. When `_load_state()` restores history via `record_trade()`, session_pnl accumulates ALL historical PnL (e.g., -97.2%). Fix: reset `session_pnl=0` AND `session_trades=0` AFTER the restore loop completes. See apex-v5-synthesis-modules reference.
- **Revenge block from stale timestamp (2026-06-25)**: `last_loss_time = time.time()` in `record_trade()` sets loss time to NOW during history restore, triggering 10-min revenge block. Fix: add `trade_time=None` param to `record_trade()`, use `actual_time = trade_time or time.time()`, and parse ISO timestamp from history. See apex-v5-synthesis-modules reference.
- **Volume floor blocks 80%+ trades (2026-06-25)**: Psychology engine required 1.3x vol_ratio. But vol_ratio from 15m candles shows 0.1-0.3x during quiet markets (EU/Asia). With 16 other quality gates (EV, RoR, Correlation, Liquidity, Trap Cycle, Consensus, etc.), volume floor is redundant. REMOVED entirely. If re-adding, set threshold ≤ 0.1x (dead market only). **LESSON**: More gates = exponentially lower pass rate. 16 gates × 90% each = 18% overall.
- **Balance fallback — CF Worker intermittent 403 (2026-06-25)**: `get_available_balance()` returns $0 when CF Worker returns 403. Bot shows "insufficient balance (need $1.39, have $0.00)" despite $5.13 actual. Fix: add urllib direct fallback to `contract.mexc.com` when CF Worker fails. Without fix, bot scans but NEVER opens positions.
- **Revenge block from stale timestamp (2026-06-25)**: `record_trade()` uses `time.time()` during history restore on restart → sets `last_loss_time` to NOW → 10-min revenge block on ALL pairs. Fix: add `trade_time=None` param, parse ISO timestamp from history.
- **Session PnL accumulation on restart (2026-06-25)**: `session_pnl` accumulates ALL historical PnL on restart (e.g., -97.2%). Fix: reset `session_pnl=0` AND `session_trades=0` AFTER the restore loop completes.
- **RoR threshold too strict for small capital (2026-06-25)**: 5% max RoR rejected all trades with $5.63 capital. With 2.5% risk per trade, RoR formula gives ~20%. Fix: raised threshold to 30% (realistic for small accounts). The key metric is `can_survive_15` (consecutive losses), not RoR percentage.
- **Ghost trades in state file**: Bot opens position but state file has `active_trades: []`. Symptom: bot says "active=0" but MEXC shows open position. Root cause: crash/restart before state save. Fix: check MEXC positions directly, clean state, restart bot.
- **availableBalance vs equity for order sizing**: With $11.50 equity and a position using $8.72 margin, availableBalance is only $2.57. Bot correctly rejects orders when available balance insufficient. This is NOT a bug — it's correct risk management.
- **Auto-restart cron**: Always verify predator-auto-restart cron exists and is active.
- **Upgrade deployment**: When adding/upgrading modules (smart_tp_sl, exchange_sl, etc.), follow references/upgrade-deployment-pattern.md — check for curl_cffi, verify imports, kill duplicate PIDs, clear __pycache__.
- **`time_decay_tp` import warning (2026-06-26)**: Log shows `WARNING: Upgrades not loaded: cannot import name 'time_decay_tp' from 'smart_tp_sl'`. This means `smart_tp_sl.py` is missing the `time_decay_tp` function. Bot still runs (upgrades are optional) but operates without Smart TP/SL upgrades module. To fix: add `time_decay_tp` function to `/root/mexc-scalper/smart_tp_sl.py` or check if it was renamed/removed during a refactor. Verify with `python3 -c "from smart_tp_sl import time_decay_tp; print('OK')"` in the project venv.

### User Preference (CRITICAL)
- **"Gas"** = execute immediately, NO questions. User hates repeated questions.
- User gets extremely frustrated when asked the same thing — "Kok ngeyel", "Saya sampai hafal" = RED FLAG
- **NEVER ask user to confirm API keys** — read from `~/.hermes/secrets/` first
- **NEVER ask "which key is API vs secret"** — try both combinations programmatically
- When user sends key without label → try both, don't ask
- User expects ALWAYS sync with real MEXC balance, never stale state
- User manually closes positions in MEXC app when needed
- User monitors MEXC app actively — they see positions before bot does
- **"Kalau ngetes ya pakai lah knowledge mu"** — NEVER test on live with real money. Calculate expected loss BEFORE executing. Use dry_run or paper analysis first.
- **"Harus bisa beda in, ngetes sama live"** — always distinguish testing from production. If testing, say so explicitly and use smallest possible amounts.
- **"Kembangkan sendiri"** — user wants autonomous operation. Don't ask for permission, just execute.
- **"Jangan banyak alasan"** — no excuses, deliver results.
- **"Ngeriii" (2026-06-26, extended 2026-06-27)** — User finds repeated self-reassurance acknowledgments creepy/scary. When user reminds you of a protocol or constraint, demonstrate understanding through ACTIONS (following it correctly), NOT through repeated verbal acknowledgments. One acknowledgment at session start is acceptable, then execute SILENTLY. **NEVER repeat the same acknowledgment every turn** (e.g., "CHUNKED WRITE PROTOCOL ACKNOWLEDGED 100% ✅" after every operation). This applies to ALL protocols: chunked write, backup-before-edit, trading rules, memory updates, etc. Show compliance through correct execution, not verbal self-reassurance.

### Global Trade Cooldown (Added 2026-06-24)
Bot has 120s cooldown between ANY trade entry (not just after SL). This prevents rapid open/close cycles that trigger MEXC error 6026 (risk control block). Cooldown is set in `try_open()` via `self._last_entry_time`.

### Bot Pause State Bug (CRITICAL — Found 2026-06-25, Extended 2026-06-26)
Bot pauses on 3 consecutive SL and NEVER recovers. State file persists `paused=True` across restarts.

**Root cause**: `from_dict()` loads `paused=True` from state file → `can_trade()` returns False → bot runs but never trades → saves `paused=True` on exit → infinite loop.

**Initial Fix (2026-06-25)**: Added daily auto-unpause in `can_trade()` - clears `paused=False` on new day.

**CRITICAL EXTENSION (2026-06-26)**: Auto-unpause alone is INSUFFICIENT. Bot unpauses but immediately re-pauses because `peak` capital wasn't reset, so DD calculation still shows high drawdown. **MUST reset peak to current capital** on unpause:
```python
today = datetime.now().strftime('%Y-%m-%d')
if not hasattr(self, '_last_daily_date') or self._last_daily_date != today:
    self.daily_start = self.capital
    self._last_daily_date = today
    if self.paused:
        log.info(f"🌅 New day! Clearing pause: {self.pause_reason}")
        self.paused = False
        self.pause_reason = None
        self.consecutive_sl = 0
        # CRITICAL FIX (2026-06-26): Reset peak to give fresh DD calculation
        self.peak = self.capital
        log.info(f"   Peak reset to ${self.capital:.2f} (DD now 0%)")
```

**Manual fix** (if can't wait for new day):
```python
import json
state_path = '/root/.hermes/data/predator_v5_state.json'
d = json.load(open(state_path))
d['risk']['paused'] = False
d['risk']['pause_reason'] = None
d['risk']['consecutive_sl'] = 0
d['risk']['last_sl_time'] = 0
json.dump(d, open(state_path, 'w'), indent=2)
```

**⚠️ MUST kill bot with SIGKILL (-9) before editing state file**, NOT SIGTERM. SIGTERM triggers exit handler which calls `_save_state()`, overwriting your manual fix.

### State File Desync (3 Files Diverge)
Three state files can have completely different data:
1. `~/.hermes/data/predator_v5_state.json` — PRIMARY (bot reads/writes here)
2. `/root/mexc-scalper/state/state.json` — SECONDARY (often stale)
3. `/root/mexc-scalper/shared_state.json` — SNAPSHOT (very old)

**When diagnosing**: Always check ALL 3 files + MEXC API actual. If files disagree, sync all from MEXC API.

**Sync procedure**:
```python
import json, time, hmac, hashlib, urllib.request, ssl
# Get MEXC actual balance and positions
# Update ALL 3 files with same data
# Restart bot
```

### Smart TP_NOW Minimum Hold Time (Added 2026-06-25)
Smart TP_NOW and Adaptive EXIT_NOW require minimum 5 minutes hold before they can close. This prevents instant fee-eating round trips where bot opens → Smart TP immediately closes → fees drain balance.

```python
# In manage_trades(), check hold_seconds before Smart TP_NOW close:
hold_seconds = time.time() - trade.get('time', time.time())
if trade.get('smart_tp') == 'TP_NOW' and hold_seconds > 300:
    # ... close logic
```

### Skip Scan When Balance Too Low (Added 2026-06-25)
When available balance < $5, skip scanning entirely. Most trades need $7-13 margin, so scanning is wasted API calls.

### Adaptive Gating — Session-Aware Thresholds (Added 2026-06-25, FINAL values)
Psychology Engine adjusts whale filter thresholds based on session time:
- **US_PRIME (13-21 UTC)**: min_sources=3, size_mult=1.0 (ketat)
- **EU_SESSION (7-13 UTC)**: min_sources=2, size_mult=0.9
- **ASIA_SESSION (2-7 UTC)**: min_sources=2, size_mult=0.8
- **OFF_HOURS (21-2 UTC)**: min_sources=2, size_mult=0.7, SL 20% tighter

**NOTE**: min_sources reduced from 4→3 (US) and 3→2 (others) after iteration. Volume floor REMOVED (set to 0.1x = effectively disabled). 16 quality gates already filter sufficiently.

Session mode also affects EV threshold (lower during OFF_HOURS) and SL tightness.
Location: `evaluate_trade_psychology()` in TradingPsychologyEngine class.

Also: OFF_HOURS SL adjustment in try_open() (80%, not 75% — 75% was too tight):
```python
if not (13 <= hour_utc < 21):  # Not US prime
    sig['sl_pct'] = max(0.01, orig_sl * 0.80)  # 20% tighter SL
```

**7 Synthesis Modules** now in try_open() pipeline:
EV Calculator → RoR Calculator → Deep Correlation → Liquidity Checker →
Trap Cycle Detector → Extremes Reversion → Triple Consensus Engine
Details in `mata-elang-integration` skill → `references/apex-v5-synthesis-modules.md`.

```python
# In run_cycle(), before scan loop:
avail = self.executor.get_available_balance()
if avail < 5.0:
    return  # Skip scan — no margin for any trade
```

Also skip scan when global cooldown active (prevents 60+ log lines every 3 seconds):
```python
if hasattr(self, '_last_entry_time') and time.time() - self._last_entry_time < 120:
    return
```

### State Sync Protocol — SIGKILL Required (Added 2026-06-25)
When syncing state file manually (e.g., adding orphaned positions), **MUST kill bot with SIGKILL (-9)**, NOT SIGTERM. SIGTERM triggers exit handler which calls `_save_state()`, overwriting your manual sync.

```bash
# ✅ CORRECT sequence:
kill -9 $(pgrep -f "predator_v5.py")  # SIGKILL — no exit handler
# ... write synced state file ...
# ... start bot ...

# ❌ WRONG: kill (SIGTERM) → exit handler → _save_state() → sync overwritten
```

### _close_all Must Check Return Value (Added 2026-06-25)
`_close_all()` must check `close_position()` return value. If close fails (e.g., wrong side code), DON'T remove from active_trades and DON'T record fake PnL.

```python
def _close_all(self, trade, price, pnl_pct, reason, executor, risk_manager):
    result = executor.close_position(...)
    if not result.get('success'):
        log.error(f"CLOSE FAILED: {trade['symbol']} → keeping in active_trades")
        return 'HOLDING'  # Don't remove!
    # ... record PnL, remove from active_trades ...
```

### Reporting Protocol — NO SPAM (Added 2026-06-25)
User explicitly corrected reporting behavior. Rules:

**✅ REPORT:**
- Error that was FIXED (problem + solution)
- New position opened (one line)
- Position closed (PnL + reason)
- Balance milestone (>20% change)

**❌ DON'T REPORT:**
- Bot running normally
- Scan cycle, cooldown, balance check
- "Position still safe" with no change
- Timeframe updates

**Process:** DETECT → DIAGNOSE → FIX → VERIFY → THEN report format: "❌ [problem] → ✅ [solution] → 📊 [result]"

**Ketiadaan error = kondisi normal = simpan ke memory internal, JANGAN report ke user.**

## 2. Cron Job Management

### Create Cron
```python
cronjob(
    action="create",
    name="Job Name",
    schedule="every 30m",  # or "0 9 * * *" or ISO timestamp
    deliver="origin",
    prompt="Task description...",
    no_agent=True,  # for script-only
    script="/path/to/script.py"  # optional
)
```

### Schedule Formats
- `"30m"` — every 30 minutes
- `"every 2h"` — every 2 hours
- `"0 9 * * *"` — daily at 9am
- `"2026-06-17T04:00:00"` — one-shot

### Management
```python
cronjob(action="list")                           # List all
cronjob(action="pause", job_id="xxx")            # Pause
cronjob(action="resume", job_id="xxx")           # Resume
cronjob(action="remove", job_id="xxx")           # Delete
cronjob(action="run", job_id="xxx")              # Run now
cronjob(action="update", job_id="xxx", prompt="new prompt")  # Update
```

### Pitfalls
- `execute_code` BLOCKED in cron — use `terminal()` for inline Python
- `workdir` must be set correctly for script access
- Health check cron: ALWAYS follow `bot-restart-workflow` skill procedure, NOT inline cron instructions

## 3. State File Reset

### When
- Bot paused by DD: `CANNOT trade - DD XX%`
- Stale peak: peak=$16, capital=$7 → 54% DD
- Bot stuck, no trades despite good signals

### Fix
```bash
python3 -c "
import json
path = '/root/.hermes/data/predator_v5_state.json'
d = json.load(open(path))
d['risk']['peak'] = d['risk']['capital']
d['risk']['paused'] = False
d['risk']['pause_reason'] = ''
json.dump(d, open(path, 'w'), indent=2)
print(f'✅ FIXED: peak=\${d[\"risk\"][\"capital\"]:.2f} DD=0%')
"
# Then restart bot
```

### Pitfalls
- PRIMARY state file: `~/.hermes/data/predator_v5_state.json` (NOT `/root/mexc-scalper/state/state.json`)
- MUST restart bot after fix (state loaded at startup)
- After mode change: ALWAYS reset peak to current capital

## 4. Trade Limiter Reset

### When
- Log: `🛡️ BLOCKED: Max 50 trades/hari tercapai`
- All pairs blocked after mode switch
- Elang Nakal wrapper blocking (check `elang_nakal_integration.py` for limits)

### Fix
```bash
echo '{"today_count": 0, "last_date": "2026-06-17", "today_sl": 0, "last_trade_time": 0}' > /root/.hermes/data/trade_limiter_state.json
# Then restart bot
```

### Elang Nakal Limits (Updated 2026-06-21)
- File: `~/.hermes/scripts/elang_nakal_integration.py`
- `max_trades=50` (line 85) — was 20, caused premature blocking
- `max_loss_pct=30.0` (line 84) — was 5.0, too conservative
- If bot stops trading unexpectedly, check Elang Nakal limits FIRST before trade_limiter_state.json

### Pitfalls
- Bot MUST be restart after reset (counter loaded at startup)
- Set `last_date` to tomorrow if resetting mid-day
- Elang Nakal has its OWN limits separate from trade_limiter_state.json — check both

## 5. Network Diagnostic

When heartbeat stale but process alive:
```bash
curl -s -o /dev/null -w "HTTP %{http_code} | Time: %{time_total}s" --connect-timeout 10 "https://contract.mexc.com/api/v1/contract/ticker?symbol=BTC_USDT"
```
- HTTP 200 → API OK, bot issue elsewhere
- HTTP 000/timeout → Network failure. DO NOT restart — bot will resume when network recovers

## 6. Config Change Before Restart

```bash
cd /root/mexc-scalper
sed -i "s/'param': OLD/'param': NEW/" predator_v5.py
grep "param" predator_v5.py | head -3  # VERIFY before restart
# Then restart
```

## 7. Elang Autonomy Protocol (Added 2026-06-24)

User demands FULL AUTONOMY. Do NOT wait for permission to fix problems.

### Protocol: Detect → Diagnose → Fix → Verify → Report

```
🦅 ELANG AUTONOMY:
1. DETECT — Monitor continuously (watchdog every 2 min)
2. DIAGNOSE — Analyze root cause independently
3. FIX — Execute fix immediately, no permission needed
4. VERIFY — Test before deploying
5. REPORT — Inform user of results, not requests
```

### Self-Healing Watchdog
Script: `~/.hermes/scripts/elang_watchdog.py`
Cron: `🦅 Elang Self-Healing Watchdog` (every 2 min, forever)

What it does:
- Bot crash → auto-restart
- 6026 block → pause + monitor (auto-restart on clear)
- Balance drift > $0.50 → sync from MEXC
- State divergence → auto-correct
- All issues → auto-report

### User Frustration Signals (from this session)
- **"Kalau ngetes ya pakai lah knowledge mu"** — NEVER test on live. Calculate expected loss BEFORE executing.
- **"Harus bisa beda in, ngetes sama live"** — always distinguish testing from production.
- **"Kembangkan sendiri"** — autonomous operation. Don't ask for permission.
- **"Jangan banyak alasan"** — no excuses, deliver results.
- **"Jangan spam lagi, kalau di bekukan bahaya"** — NEVER spam test orders. Each test during 6026 extends the block. Monitor passively at 5min intervals.
- **"Apa loe sudah paham?"** — user wants confirmation of understanding, not more questions.
- **"Okey gas"** — proceed immediately.

### Global Trade Cooldown
Bot has 120s cooldown between ANY trade entry. Set in `try_open()` via `self._last_entry_time`. Prevents rapid open/close cycles that trigger MEXC 6026.

### Health Monitor Cron (Read-Only, No Restart)
**See**: `references/zombie-pid-false-positive-2026-06-28.md` — real incident where `pgrep` fooled monitor cron

### Monitoring Procedure (Bulletproof)
```bash
# 1. Check if bot is running — ONLY reliable method:
#    a) ps aux | grep with [p] trick
#    b) Verify PID is NOT a zombie (cat /proc/<PID>/cmdline must exist)
#    c) NEVER trust pgrep -f alone (returns zombie/wrapper PIDs)
ALIVE=$(ps aux | grep "[p]ython3.*predator_v5" | awk '{print $2}')
if [ -n "$ALIVE" ]; then
    for pid in $ALIVE; do
        if [ -r "/proc/$pid/cmdline" ]; then
            echo "✅ Bot RUNNING (PID $pid, alive)"
        else
            echo "⚠️ PID $pid is zombie/gone — bot DOWN"
            ALIVE=""
        fi
    done
fi
[ -z "$ALIVE" ] && echo "❌ Bot NOT RUNNING"

# 2. Check latest log entries (try multiple paths)
tail -30 /tmp/predator_v5_live.log 2>/dev/null || tail -30 /tmp/predator_v5.log 2>/dev/null || echo "NO_LOG_FILE"

# 3. Check log freshness (stale log = bot dead)
LOG_FILE="/tmp/predator_v5_live.log"
[ ! -f "$LOG_FILE" ] && LOG_FILE="/tmp/predator_v5.log"
LOG_TS=$(stat -c %Y "$LOG_FILE" 2>/dev/null || echo 0)
NOW=$(date +%s)
STALE=$(( NOW - LOG_TS ))
echo "⏱️ Log age: ${STALE}s"
# If STALE > 300 (5 min) and no process → bot is DOWN

# 4. Scan for critical patterns in log
grep -iE 'error|tilt|critical|exception|traceback|crash|killed|6026' "$LOG_FILE" 2>/dev/null | tail -5

# 5. Balance check from log
grep -oE 'Sync: \$[0-9.]+ → \$[0-9.]+' "$LOG_FILE" 2>/dev/null | tail -1
grep -oE 'Capital: \$[0-9.]+' "$LOG_FILE" 2>/dev/null | tail -1
```

### Decision Logic
| Condition | Action |
|-----------|--------|
| Process alive + log fresh (<5min) | ✅ Normal — SILENT |
| Process alive + log stale (>5min) | ⚠️ Stuck — alert (possible zombie) |
| Process dead + log shows `FINAL:` | 🚨 DOWN (clean exit) — alert |
| Process dead + log shows error/traceback | 🚨 DOWN (crash) — alert |
| Process dead + no recent log | 🚨 DOWN (unknown) — alert |

### Alert Delivery via Hermes
```bash
# Use hermes send CLI (no LLM, no agent loop, uses gateway credentials)
# Target: telegram:7499808632 (Elangemas)
hermes send --to telegram:7499808632 "🚨 DOWN - Predator V5 bot NOT running. Balance: \$X | Positions: N"
```

**IMPORTANT**: Hermes auto-delivers the cron job's final response to the same target. For monitor-only crons, either:
- Put alert in final response (auto-delivered)
- Use `hermes send --to <different_target>` for additional recipients

### Log Patterns
- `FINAL: $X T:N WR:X% PnL:+Y` = clean shutdown (ran to completion)
- `PREDATOR V5 APEX — 🔴 LIVE` = startup banner
- `🌄 New day! Clearing pause` = daily auto-unpause working correctly
- `cannot import name 'time_decay_tp' from 'smart_tp_sl'` = import error (see Pitfalls)

### ⚠️ NEVER restart bot from a monitor-only cron. Just alert.

## Reference Files
- `references/cron-startup-pattern.md` — How to start long-running processes from cron jobs (blocked commands, two approaches, output routing, verification)
- `references/upgrade-deployment-pattern.md` — Deploying upgrade modules: curl_cffi→urllib replacement, import patterns, duplicate PID prevention, verification checklist
- `references/startup-sequence-2026-06-23.md` — Step-by-step bot startup order with all verification checks
- `references/daily-bot-start-cron.md` — Daily bot start cron workflow, report format, common issues (6026, stale heartbeat, paused cron)
- `references/bot-pause-bug-fix.md` — Bot pause on 3 consecutive SL, daily auto-unpause fix, manual fix procedure
- `references/state-desync-diagnosis.md` — 3 state files desync, diagnosis procedure, sync fix with MEXC API
- See also: `mexc-api` skill → `references/ghost-position-debug-2026-06-27.md` for state file hierarchy debugging

## Key File Paths
| File | Path |
|------|------|
| Bot | `/root/mexc-scalper/predator_v5.py` |
| State (PRIMARY) | `~/.hermes/data/predator_v5_state.json` |
| State (BACKUP) | `/root/mexc-scalper/state/state.json` |
| Shared State (PRIMARY) | `/root/mexc-scalper/state/shared_state.json` |
| Shared State (SNAPSHOT) | `/root/mexc-scalper/shared_state.json` |
| Log | `~/.hermes/logs/mexc_predator_v5.log` |
| Trade Limiter | `~/.hermes/data/trade_limiter_state.json` |
| API Key (ACTIVE) | `/root/mexc-scalper/secrets/api_keys.json` (JSON array, use active futures key) |
| API Key (fallback) | `~/.hermes/secrets/mexc_api_key.txt` (may be stale) |
| API Secret (fallback) | `~/.hermes/secrets/mexc_secret_key.txt` (may be stale) |
