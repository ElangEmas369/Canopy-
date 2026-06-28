# Termux Platform Limitations — Package Install Failures (2026-06-28)

## Problem

Attempted to install CloakBrowser on Termux (PRoot Linux on Android aarch64):
```
pip3 install cloakbrowser → FAILED
pip3 install playwright → FAILED  
pip3 install cryptography → FAILED
```

## Root Cause

Python 3.13.5 on aarch64-linux-android (Termux) has **no prebuilt wheels** for:
- `cryptography` — requires Rust compiler (`maturin` build fails: "Target triple not supported by rustup: aarch64-unknown-linux-android")
- `playwright` — no wheel for platform
- `cloakbrowser` — depends on both above

## Error Messages

```
Rust not found, installing into a temporary directory
Python reports SOABI: cpython-313-aarch64-linux-android
Computed rustc target triple: aarch64-unknown-linux-android
Target triple not supported by rustup: aarch64-unknown-linux-android

error: metadata-generation-failed
× Encountered error while generating package metadata.
╰─> maturin

ERROR: Failed to build 'cryptography' when installing build dependencies for cryptography
```

## What DOES Work on Termux

| Package | Status | Notes |
|---------|--------|-------|
| `requests` | ✅ | Prebuilt wheel available |
| `urllib3` | ✅ | Prebuilt wheel available |
| `hmac`, `hashlib` | ✅ | stdlib |
| `numpy` | ✅ | Has aarch64 wheels |
| `pandas` | ✅ | Has aarch64 wheels |
| `playwright` | ❌ | No aarch64-android wheel |
| `cryptography` | ❌ | No Rust toolchain for target |
| `curl_cffi` | ❌ | libm ELF header issue in PRoot |

## Workarounds Attempted

1. **pip3 install cloakbrowser** → Failed (cryptography dependency)
2. **pip3 install --only-binary :all: cryptography** → Failed (no matching version)
3. **CloakBrowser binary directly** → `cloakserve` needs `aiohttp` (also blocked)

## Solution for Tuan Muda

CloakBrowser **CANNOT be installed** on this Termux instance. Options:

### Option 1: Run on HP Different Environment
- Install Python + CloakBrowser on HP's main Android (not Termux)
- Requires Termux:API or chroot with full Linux

### Option 2: Docker (if Termux supports)
```bash
pkg install docker
docker run --rm cloakhq/cloakbrowser cloaktest
```

### Option 3: Use Alternative Anti-Bot Tools
Tools that work on Termux:
- `undetected-chromedriver` (Python, pure JS injection)
- `DrissionPage` (Python, no extra deps)
- `selenium-stealth` (Python, pure JS injection)

### Option 4: Run from Different Server
- VPS with x86_64 Linux ($5-10/month)
- Full Python + CloakBrowser support

## ADB/Termux Connection Attempts

Attempted to connect local Termux on same WiFi:
- Server IP: `192.168.1.3`
- ADB installed: `apt-get install android-tools-adb`
- ADB daemon started successfully
- **Problem:** Could not scan network for HP device
- **Root cause:** PRoot environment has isolated network namespace — `/proc/net/arp` blocked, `nmap` unavailable

## User Instruction (2026-06-28)

Tuan Muda said: "1 sudah ada termux di android, kau gas saja dari sini langsung connect termux"

**Status:** BLOCKED by PRoot network isolation. Cannot auto-discover HP.

**Required action:** Tuan Muda must manually:
1. Enable ADB over WiFi on HP: `adb tcpip 5555`
2. Get HP IP: `ip addr | grep "inet "`
3. Provide IP to agent for `adb connect <IP>:5555`

OR use Cloudflare Tunnel approach (ssh port 8022 + cloudflared).

## Lesson

Before attempting complex installs on Termux, CHECK:
1. Python version (`python3 --version`)
2. Architecture (`uname -m`)  
3. Package wheel availability (`pip3 download --only-binary :all: <pkg>`)
4. Rust availability (`rustc --version`) — required for cryptography

**Don't attempt installs that require Rust on aarch64-android without checking first.**
