# CF Worker Proxy Death — 2026-06-22

## What Happened

The Cloudflare Workers proxy `mexc-proxy.refidsaputro369.workers.dev` died on 2026-06-22. All HTTPS connections were reset during SSL handshake (`ConnectionResetError: [Errno 104] Connection reset by peer`).

## Symptoms

- `zombie_closer.py` and all proxy-dependent scripts crashed with `requests.exceptions.ConnectionError: ('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))`
- Direct `curl https://contract.mexc.com` returned 401 (expected without auth) — confirming MEXC API itself was fine
- Only the proxy was down

## Fix Applied

Replaced `https://mexc-proxy.refidsaputro369.workers.dev` → `https://contract.mexc.com` in 21 scripts:

| Script | Fixed |
|--------|-------|
| zombie_closer.py | ✓ |
| force_sync.py | ✓ |
| exchange_sl.py | ✓ |
| recovery_mode.py | ✓ |
| session_watchdog.py | ✓ |
| mexc_api.py | ✓ |
| smart_capital_sync.py | ✓ |
| orphan_scanner.py | ✓ |
| position_health_monitor.py | ✓ |
| realtime_monitor.py | ✓ |
| auto_sync.py | ✓ |
| capital_sync_5m.py | ✓ |
| margin_monitor.py | ✓ |
| daily_position_audit.py | ✓ |
| zombie_ghost_watchdog.py | ✓ |
| exchange_history_fetcher.py | ✓ |
| auto_api_manager.py | ✓ |
| auto_rotate_keys.py | ✓ |
| monitor.py | ✓ |
| daily_report.sh | ✓ |
| weekly_review.sh | ✓ |
| elang_nakal/elang_nakal_predator.py | ✓ (4 occurrences) |

## Lessons

1. **Single point of failure**: A proxy used by 21 scripts is a SPOF. Direct API is more reliable.
2. **Bulk fix tooling**: Use `patch` tool per-file for URL replacements. Do NOT use `sed` via terminal — the security scanner (`tirith:invalid_host_chars`) blocks shell commands containing URL patterns.
3. **Detection**: When cron scripts fail with SSL/connection reset errors, check if the proxy is dead before investigating MEXC API itself.
4. **Verification**: Always test with direct `curl` to `contract.mexc.com` to confirm MEXC API is reachable before debugging signing/auth issues.

## Current State (2026-06-22 04:30)

- All scripts use direct `https://contract.mexc.com`
- Bot running (PID 18234)
- MEXC equity: $24.4308
- 0 open positions, 0 zombies
- State file synced
