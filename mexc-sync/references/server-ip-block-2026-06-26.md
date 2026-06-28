# MEXC Server IP Block Incident — 2026-06-26

## Summary
Server IP 103.247.13.75 (PRoot/Android ARM datacenter) permanently blocked by MEXC WAF. All `contract.mexc.com` requests return 403 Access Denied.

## Diagnosis Steps
1. Test direct: `curl -sI https://contract.mexc.com/api/v1/ticker/price?symbol=S_USDT` → 403
2. Test API key: Valid (not expired, correct signature)
3. Test via proxy farm: 62 proxies tested — all failed
   - HTTP proxies: Tunnel connection failed (400/502/timeout)
   - Connected proxies: Still 403 from MEXC
   - SOCKS5: No valid entries
4. Test api.mexc.com: Returns 404 (no futures support from this IP)
5. Conclusion: IP-level block, not key/signature issue

## Proxy Test Results
| Proxy | Port | Type | Result |
|-------|------|------|--------|
| 178.212.144.7 | 80 | http | Tunnel 400 Bad Request |
| 65.108.203.36 | 18080 | http | Tunnel 502 Bad Gateway |
| 91.107.182.124 | 82 | http | 403 Access Denied |
| 8.215.25.3 | 2080 | http | 403 Access Denied |
| 174.137.134.182 | 2999 | http | 403 Access Denied |
| 3.137.86.220 | 443 | http | 403 Access Denied |
| Others | various | http | Timeout / Connection Refused / Reset |

## Solution
Run bot from Termux on Android HP using mobile data (residential IP).

Command: `cd /root/mexc-scalper && python3 predator_v5.py`

## Alternative Solutions (Untested)
1. SSH tunnel: `ssh -R 8080:localhost:8080 user@server` from HP
2. Residential proxy: $5-10/month (e.g., Bright Data, Oxylabs)
3. Different VPS: Oracle Free Tier, residential IP VPS

## Key Lessons
- Free proxy farms cannot bypass MEXC WAF
- HTTPS CONNECT tunneling requires paid residential proxies
- Don't waste time testing 60+ proxies when server IP is blocked — go straight to residential solution
- MEXC blocks datacenter IPs at WAF level, not just rate-limiting
