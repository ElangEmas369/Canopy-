# API Key Cleanup Workflow (2026-06-28)

## Context
MEXC API keys expire after 90 days. When user requests cleanup of expired keys ("yang tidak aktif di hapus semua saja"), perform systematic removal across all locations while preserving historical documentation.

## Workflow

### 1. Identify Active Key First
```bash
# Test current key from TRADING_MODE.md
python3 -c "
import predator_v5 as p5
from predator_v5 import load_trading_mode
tm = load_trading_mode()
client = p5.MEXCClient('https://mexc-cf-7phn.pages.dev', 
                        tm.get('MEXC_API_KEY'), 
                        tm.get('MEXC_SECRET_KEY'), 10, None)
result = client.get('/api/v1/private/account/assets', auth=True)
# Look for USDT balance in result['data']
"
```

### 2. Locate All Files Containing Old Keys
```bash
# Find in project
cd /root/mexc-scalper
grep -l "OLD_KEY_PREFIX" *.md *.json 2>/dev/null

# Find in skills
find ~/.hermes/skills -name "*.md" -exec grep -l "OLD_KEY_PREFIX" {} \;
```

### 3. Update Active Config Files (Surgical Edits Only)
**Priority order:**
1. `/root/mexc-scalper/TRADING_MODE.md` (source of truth)
2. `/root/mexc-scalper/CRITICAL_NOTES.md`
3. `/root/mexc-scalper/secrets/api_keys.json`
4. `~/.hermes/secrets/mexc_api_key.txt`
5. `~/.hermes/secrets/mexc_secret_key.txt`

Use `patch(mode='replace')` with targeted old_string/new_string. **NEVER rewrite entire files.**

### 4. Update Skills (Large Files: 200-1200 lines)
**Files typically affected:**
- `~/.hermes/skills/trading/mexc-sync/SKILL.md` (1152 lines)
- `~/.hermes/skills/trading/mexc-api/SKILL.md` (279 lines)
- `~/.hermes/skills/trading/trading-mode-isolated/SKILL.md` (135 lines)
- `~/.hermes/skills/master-recovery/SKILL.md` (637 lines)

**Strategy:**
- Use `patch(mode='replace')` for each occurrence
- **Multiple small patches > one large rewrite**
- Update only the sections containing old keys
- Preserve structure and surrounding content

**Example pattern:**
```bash
# Find line numbers first
grep -n "OLD_KEY" skill.md

# Then patch specific sections
patch(mode='replace',
      old_string='OLD_KEY: mx0vglOLDKEY\nSecret: oldsecret',
      new_string='Active key: mx0vglNEWKEY\nSecret: newsecret')
```

### 5. Handle Reference Files (Historical Documentation)
Reference files under `skills/*/references/*.md` are **historical records** - do NOT rewrite history.

**Instead, add deprecation warnings:**
```bash
# Prepend warning to reference files
for f in api-key-recovery-*.md api-key-rotation-*.md; do
  sed -i '1i\⚠️ DEPRECATED (2026-06-28): Expired keys archived for historical reference. Active: NEW_KEY\n' "$f"
done
```

### 6. Verify Cleanup
```bash
# Should return 0 or only reference files with warnings
grep -r "OLD_KEY_PREFIX" ~/.hermes/skills --include="*.md" | wc -l
```

## Key Principles

1. **Active configs = clean state** (only current key)
2. **Skills = surgical patches** (never full rewrites on large files)
3. **References = preserve + warn** (historical value maintained)
4. **Chunked write protocol = mandatory** (max 350 lines per operation)

## Files Updated (2026-06-28 Session)
- 5 active config files (full updates)
- 4 skill files (surgical patches)
- 4 reference files (deprecation warnings added)
- Total: 13 files, 0 chunked write violations

## Timing
Complete cleanup: ~8-10 operations, 2-3 minutes wall time when following surgical edit protocol.

## User Expectation
"Gas sampai bisa" - execute systematically without asking for confirmation on each file. User wants final state: only one active key across entire system.
