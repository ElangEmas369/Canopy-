# TRADING_MODE.md — Isolated Persistent Memory Pattern

## Problem (2026-06-25)
User wanted trading config + API keys + rules to persist across gateway restarts WITHOUT depending on:
- `.env` files (ephemeral, can be overwritten)
- Hermes memory (gets compacted/lost during context window)
- Agent memory (gets full, entries replaced)

## Solution: TRADING_MODE.md
Single file at `/root/mexc-scalper/TRADING_MODE.md` containing:
- MODE switch (ON/OFF)
- API keys
- Trading config (leverage, TP, SL, scores)
- Blacklist
- Rules (session, direction, side codes)
- Error code reference
- Last known state

## How It Works
1. `predator_v5.py` reads TRADING_MODE.md on startup via `load_trading_mode()` function
2. If MODE=ON → use keys from file
3. If MODE=OFF or file missing → fallback to `.secrets` files
4. Agent reads file for config without loading full skill

## Benefits
- Survives gateway restarts
- Not dependent on .env or memory
- Single source of truth
- Easy to switch modes (edit one line)
- User can edit directly

## Implementation
```python
def load_trading_mode():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TRADING_MODE.md')
    config = {}
    if not os.path.exists(config_path):
        return config
    with open(config_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('```'):
                continue
            if ':' in line:
                key, val = line.split(':', 1)
                key = key.strip()
                val = val.strip()
                if val.startswith('[') and val.endswith(']'):
                    val = [x.strip().strip("'\"") for x in val[1:-1].split(',')]
                elif val.upper() in ('ON', 'TRUE'):
                    val = True
                elif val.upper() in ('OFF', 'FALSE'):
                    val = False
                elif val.replace('.', '').isdigit():
                    val = float(val) if '.' in val else int(val)
                config[key] = val
    return config
```

## File Location
`/root/mexc-scalper/TRADING_MODE.md`

## User Quote
"Switch skill+memory nya jangan di .env. Di integrate dalam satu mode, terpisah dari tubuh serta ingatan utama, selama mode itu on, memory nya gak longsor ketika gateway off"
