# Dahono Gateway — Model List (2026-06-24)

**Gateway URL:** `https://gateway.dahono.com/v1`
**API Key:** `dahono-c76b366c30ab75460e90da7138548007`
**Pricing:** ALL models $0.00 input & output (unlimited)

## Models (20 total)

### NEW (2026-06-24)
| Model | Context | Notes |
|-------|---------|-------|
| `dahono/deepseek-v4-flash` | 32K | Fast inference |
| `dahono/deepseek-v4-pro` | 32K | Pro quality |
| `dahono/qwen3-coder-next-thinking` | 1M | Coding + thinking |
| `dahono/qwen3-coder-next-thinking-agentic` | 1M | Agentic coding |
| `dahono/minimax-m2.7` | 1M | Large context |
| `dahono/glm-5.2` | 1M | Zhipu AI |
| `dahono/claude-sonnet-4.5-thinking-free` | — | Claude thinking |
| `dahono/claude-sonnet-4.5-thinking-agentic-free` | — | Claude agentic |
| `dahono/claude-sonnet-4.5-free` | — | Claude standard |
| `dahono/claude-sonnet-4.5-agentic-free` | — | Claude agentic |
| `dahono/anthropic.claude-fable-5` | — | Claude Fable |

### EXISTING
| Model | Context | Notes |
|-------|---------|-------|
| `dahono/mimo-auto` | — | Default |
| `dahono/mimo-v2.5-pro` | — | Primary |
| `dahono/horizon-beta` | — | OpenRouter free |
| `dahono/horizon-alpha` | — | OpenRouter free |
| `dahono/opencode-1` | — | OpenCode |
| `dahono/nemotron-3-super` | — | NVIDIA |
| `dahono/minimax-m2.5-free` | — | MiniMax |
| `dahono/deepseek-r1-0528` | — | DeepSeek R1 |
| `dahono/deepseek-chat-v3-0324` | — | DeepSeek V3 |
| `dahono/qwen3-coder-480b` | — | Qwen large |

## Usage
```python
# Via Hermes config
provider: dahono
model: dahono/claude-sonnet-4.5-thinking-free

# Direct API call
curl https://gateway.dahono.com/v1/chat/completions \
  -H "Authorization: Bearer dahono-c76b366c30ab75460e90da7138548007" \
  -H "Content-Type: application/json" \
  -d '{"model":"dahono/claude-sonnet-4.5-thinking-free","messages":[{"role":"user","content":"hello"}]}'
```

## Notes
- All models are FREE (unlimited usage)
- Gateway is stable and reliable
- Can be used as fallback when MiMo or OpenRouter rate-limited
- Thinking models show reasoning process in response
- Agentic models optimized for tool use
