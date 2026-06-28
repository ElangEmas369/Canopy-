#!/usr/bin/env python3
"""
Zombie Detection Script for Predator V5
Detects positions open on MEXC that the bot doesn't track.
Does NOT auto-close — reports only, returns structured data for decision-making.

Usage: python3 zombie_detection_script.py
Output: JSON report to stdout
"""
import urllib.request, json, hmac, hashlib, time, ssl, sys

# Config
API_KEY = 'mx0vglus6c8TsD9Vr0'
API_SECRET = 'ac50d13d61f44b92b383575481f51216'
BOT_STATE_PATH = '/root/mexc-scalper/state/shared_state.json'
BALANCE_DRIFT_THRESHOLD = 0.50  # USD

# Blacklisted pairs (bot won't trade these — zombies of blacklisted pairs are harmless)
BLACKLISTED = {'BTC_USDT', 'ETH_USDT', 'WBTC_USDT', 'FRAX_USDT', 'USDC_USDT', 'ONE_USDT'}

# SSL context
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def api_get(path):
    """Authenticated GET to MEXC API (direct, not proxy)."""
    ts = str(int(time.time() * 1000))
    sig = hmac.new(API_SECRET.encode(), (API_KEY + ts).encode(), hashlib.sha256).hexdigest()
    url = f'https://api.mexc.com{path}'
    req = urllib.request.Request(url, headers={
        'ApiKey': API_KEY, 'Request-Time': ts,
        'Signature': sig, 'Content-Type': 'application/json'
    })
    resp = urllib.request.urlopen(req, timeout=15, context=CTX)
    return json.loads(resp.read())

def get_bot_state():
    """Read bot internal state."""
    try:
        with open(BOT_STATE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def main():
    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        'bot_running': False,
        'mexc_positions': [],
        'bot_active_trades': [],
        'zombies': [],
        'balance_drift': 0.0,
        'mexC_equity': 0.0,
        'bot_equity': 0.0,
        'alerts': []
    }

    # 1. Check bot process
    import subprocess
    result = subprocess.run(['pgrep', '-f', 'predator_v5.py'], capture_output=True, text=True)
    report['bot_running'] = bool(result.stdout.strip())

    # 2. Get MEXC positions
    try:
        pos_data = api_get('/api/v1/private/position/open_positions')
        report['mexc_positions'] = pos_data.get('data', []) or []
    except Exception as e:
        report['alerts'].append(f'MEXC positions API error: {e}')
        print(json.dumps(report, indent=2))
        return

    # 3. Get MEXC balance
    try:
        bal_data = api_get('/api/v1/private/account/assets')
        for asset in bal_data.get('data', []):
            if asset.get('currency') == 'USDT':
                report['mexC_equity'] = float(asset.get('equity', 0))
    except Exception as e:
        report['alerts'].append(f'MEXC balance API error: {e}')

    # 4. Get bot state
    bot_state = get_bot_state()
    report['bot_active_trades'] = bot_state.get('active_trades', [])
    report['bot_equity'] = bot_state.get('equity', 0)

    # 5. Calculate balance drift
    report['balance_drift'] = abs(report['mexC_equity'] - report['bot_equity'])
    if report['balance_drift'] > BALANCE_DRIFT_THRESHOLD:
        report['alerts'].append(
            f'Balance drift ${report["balance_drift"]:.4f} exceeds threshold ${BALANCE_DRIFT_THRESHOLD}'
        )

    # 6. Detect zombies (MEXC positions not tracked by bot)
    mexc_count = len(report['mexc_positions'])
    bot_count = len(report['bot_active_trades'])

    if mexc_count > bot_count:
        # Extract symbols bot is tracking
        bot_symbols = {t.get('symbol', '') for t in report['bot_active_trades']}
        # Find MEXC positions not in bot's tracked symbols
        for pos in report['mexc_positions']:
            symbol = pos.get('symbol', '')
            if symbol not in bot_symbols:
                is_blacklisted = symbol in BLACKLISTED
                zombie_info = {
                    'symbol': symbol,
                    'positionType': pos.get('positionType'),  # 1=LONG, 2=SHORT
                    'holdVol': pos.get('holdVol', 0),
                    'holdAvgPrice': pos.get('holdAvgPrice', 0),
                    'unrealized': pos.get('unrealized', 0),
                    'marginUsed': pos.get('oim', 0),
                    'blacklisted': is_blacklisted
                }
                report['zombies'].append(zombie_info)
                if is_blacklisted:
                    report['alerts'].append(
                        f'Zombie {symbol}: {pos.get("holdVol")} contracts @ {pos.get("holdAvgPrice")} (blacklisted, harmless)'
                    )
                else:
                    report['alerts'].append(
                        f'⚠️ Zombie {symbol}: {pos.get("holdVol")} contracts @ {pos.get("holdAvgPrice")} — NEEDS CLOSE'
                    )

    # 7. Bot health (if running but no trades for extended period = stale key)
    if report['bot_running'] and report['bot_equity'] == 0 and report['mexC_equity'] > 0:
        report['alerts'].append('Bot running but shows $0 equity — possible API key expiration (Error 402)')

    # Verdict
    report['verdict'] = 'ALERT' if report['alerts'] else 'ALL_CLEAR'
    report['summary'] = (
        f"Bot {'RUNNING' if report['bot_running'] else 'STOPPED'} | "
        f"MEXC: {mexc_count} positions, ${report['mexC_equity']:.4f} | "
        f"Bot: {bot_count} active, ${report['bot_equity']:.4f} | "
        f"Drift: ${report['balance_drift']:.4f} | "
        f"Zombies: {len(report['zombies'])}"
    )

    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
