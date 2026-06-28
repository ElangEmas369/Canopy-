# Agent Amnesia Pattern — MEXC API Key (2026-06-28)

## Problem

Agent repeatedly asked Tuan Muda to generate new API keys despite:
1. Skills `mexc-sync` + `mexc-api` containing current key + signing format
2. Key being only 90 days old (not expired)
3. Files in `~/.hermes/secrets/` containing both key and secret
4. Test scripts in skills showing exactly how to verify

## User Frustration Signals

- "Cari saja lu sudah punya Skills itu" — Agent failed to check skills
- "Kok ngeyel" — Agent being stubborn/wrong
- "Saya sampai hafal" — Agent asked same thing too many times
- "bukan api mexc yang exp tapi loe yang lupa caranya" — Root cause was agent's bug, not actual key expiration
- "jangan ngeyel itu exp nya 90 hari" — Agent misdiagnosed error 402 as expired key

## Root Cause Analysis

1. **Agent didn't load skills first** before asking user
2. **Test script had bugs** (missing `SK =` variable declaration)
3. **Misdiagnosed error 402** — it was IP whitelist issue, not expired key
4. **Didn't check key creation date** — key was valid (90 days from generation)

## Mandatory Workflow (NEVER skip)

When MEXC API issue arises OR user reports API errors:

1. **LOAD skills** — `skill_view(name='mexc-sync')` + `skill_view(name='mexc-api')`
2. **READ files** — `open('/root/.hermes/secrets/mexc_api_key.txt').read().strip()`
3. **TEST API** with balance check (skills contain working test scripts)
4. **SEARCH sessions** — `session_search(query="mexc api key expired")` for previous solutions
5. **VERIFY test script** — check variable names (AK + SK both defined?), correct imports
6. **ONLY ask user** if all above fail — and ask for STATUS (check MEXC UI) not new key generation

## Error Code Clarity

| Error | Meaning | Example |
|-------|---------|---------|
| **402** | Key expired OR IP not whitelisted | "API key expired, please apply again" |
| **602** | Signature format wrong | "Confirming signature failed" |
| **10072** | Key corrupted/truncated | "Api key info invalid" |
| **6026** | Risk control (account-level) | "DISABLED_CONTRACT_OPEN_POSITION" |

**CRITICAL:** Error 402 is MISLEADING — it's often IP whitelist, not actual expiration.

## Key Protection Rules

1. NEVER ask user to generate new key without exhausting all self-check steps
2. NEVER define API secrets inline (shell escapes/truncates them)
3. NEVER trust `status: active` in JSON — always test with actual API call
90-day countdown starts from key generation, not user creation
5. Track creation dates in TRADING_MODE.md

## Git Commit History

This incident (2026-06-28) prompted major updates to:
- `mexc-sync/SKILL.md` — Added error code clarity, mandatory workflow
- `mexc-api/SKILL.md` — Added testing protocol with correct SK definition
- `MEMORY.md` — Added "NEVER ask for new key" rule
- Bot skill list — Added mexc-sync and mexc-api as required loads for trading issues
