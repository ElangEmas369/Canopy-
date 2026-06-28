# Profile Isolation for Skills+Memory — 2026-06-24

## User Request
"switch skill+memory nya jangan di .env. Di integrate dalam satu mode, terpisah dari tubuh serta ingatan utama, selama mode itu on, memory nya gak longsor ketika gateway off"

Translation: Skills+memory should NOT be in .env. Integrate into an isolated mode, separate from the main body and memory. When mode is on, memory doesn't erode when gateway restarts.

## Solution: Hermes Profiles

Hermes profiles provide COMPLETE isolation:
- Each profile has its own `config.yaml`, `.env`, `skills/`, `memories/`, `sessions/`, `SOUL.md`
- Memory in one profile is independent of another
- Gateway restart on default profile does NOT affect trading profile
- Skills can be profile-specific (trading skills in trading profile, general in default)

## Setup Steps

### 1. Create Profile
```bash
hermes profile create trading --clone
```
This clones default config, .env, SOUL.md, and skills to new profile.

### 2. Configure Memory (Persist on Restart)
```yaml
# ~/.hermes/profiles/trading/config.yaml
memory:
  memory_enabled: true
  provider: local        # SQLite backend, persists across restarts
  persist_on_restart: true
  memory_char_limit: 2200
  user_char_limit: 1375
```

### 3. Set Model/Provider
```yaml
model:
  default: dahono/mimo-v2.5-pro
  provider: dahono
  base_url: https://gateway.dahono.com/v1
```

### 4. Update .env with Profile-Specific Keys
```bash
# ~/.hermes/profiles/trading/.env
MEXC_API_KEY=mx0vgl...Vr0
MEXC_SECRET_KEY=ac50...1216
XIAOMIMIMO_API_KEY=tp-src...5on3
Dahono_API_KEY=dahono...8007
TELEGRAM_BOT_TOKEN=<trading_bot_token>
```

### 5. Seed Memory
```bash
# Trading-specific knowledge
cat > ~/.hermes/profiles/trading/memories/MEMORY.md << 'EOF'
# Trading Memory
- Platform: MEXC Futures
- Bot: Predator V5 APEX
- Capital: $19.78 USDT
- ...trading-specific knowledge...
EOF

# User profile
cat > ~/.hermes/profiles/trading/memories/USER.md << 'EOF'
# Tuan Muda
- Crypto Trader
- "Gas" = execute immediately
- ...user preferences...
EOF
```

### 6. Create SOUL.md (Persona)
```markdown
# OWL Trading Agent
You are OWL — the trading intelligence...
...trading-specific persona and rules...
```

### 7. Start Isolated Gateway
```bash
# Gateway mode (Telegram bot)
hermes gateway run --profile trading

# CLI mode
hermes chat --profile trading
```

## Key Benefits

| Aspect | Default Profile | Trading Profile |
|--------|----------------|-----------------|
| Memory | General knowledge | Trading-specific |
| Skills | All skills | Trading-focused |
| Sessions | General conversations | Trading operations |
| Config | Main provider | Dahono (unlimited) |
| .env | All API keys | Trading API keys only |

## Verification
```bash
# List all profiles
hermes profile list

# Check trading profile structure
ls ~/.hermes/profiles/trading/
# Should show: config.yaml, .env, SOUL.md, skills/, memories/, sessions/

# Check memory persistence
cat ~/.hermes/profiles/trading/memories/MEMORY.md
# Should contain trading-specific knowledge

# Check config
grep "provider:" ~/.hermes/profiles/trading/config.yaml | head -1
# Should show: provider: dahono
```

## Pitfalls

1. **Telegram token must be valid** — Each profile needs its own valid Telegram bot token. Sharing tokens between profiles causes conflicts.

2. **Memory is profile-scoped** — Memory saved in default profile is NOT visible in trading profile and vice versa.

3. **Skills are cloned, not shared** — If you update a skill in default profile, trading profile still has the old version. Must update both.

4. **Gateway can only run one profile at a time per port** — Multiple profiles need different ports or different bot tokens.

5. **sed corrupts .env keys** — Always use python3 for credential updates across profiles.

## Multi-Profile Key Update Pattern
When updating API keys, update ALL profiles:
```python
import glob, re
new_key = 'NEW_KEY'
files = glob.glob('/root/.hermes/profiles/*/.env') + ['/root/.hermes/.env']
for f in files:
    content = open(f).read()
    new_content = re.sub(r'tp-s[a-z0-9]+', new_key, content)
    if new_content != content:
        open(f, 'w').write(new_content)
```
