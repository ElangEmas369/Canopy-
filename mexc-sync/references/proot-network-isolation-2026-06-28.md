# PRoot Network Isolation — Cannot Scan Local Network (2026-06-28)

## Problem

Attempted to connect to Termux on HP Android from PRoot Linux environment:
- ADB installed and daemon started
- `adb devices` shows empty list
- Cannot scan network for HP device

## Root Cause

PRoot (proot) creates an **isolated network namespace** on Android:
- `/proc/net/arp` → Permission denied
- `/proc/net/route` → Permission denied  
- `nmap` → Not available
- `ip neigh` → Not available
- `arp -a` → Not available
- Background processes with `&` → Blocked by Hermes terminal

## What Works

| Tool | Status | Notes |
|------|--------|-------|
| `ifconfig` | ✅ | Shows wlan0 IP |
| `socket` (Python) | ✅ | Can connect to known IPs |
| `adb` | ✅ | Installed, daemon runs |
| `ssh` | ✅ | Client available |
| Network scan | ❌ | Blocked by PRoot |
| ARP table | ❌ | Permission denied |

## Server Network Info

```
lo:   127.0.0.1 (loopback)
wlan0: 192.168.1.3 (WiFi)
```

## Solutions for HP Connection

### Option 1: Manual IP (requires Tuan Muda action)
1. HP Termux: `adb tcpip 5555`
2. HP Termux: `ip addr show wlan0 | grep inet`
3. Agent: `adb connect <HP_IP>:5555`

### Option 2: Cloudflare Tunnel (no IP needed)
1. HP Termux: `pkg install cloudflared`
2. HP Termux: `cloudflared tunnel --url localhost:8022`
3. Agent connects to provided URL

### Option 3: SSH Reverse Tunnel
1. HP Termux: `sshd -p 8022`
2. HP Termux: `ssh -R 8022:localhost:8022 user@server`
3. Agent: `ssh -p 8022 localhost`

## Lesson

**PRoot environments cannot scan local network.** Always ask user for:
- IP address of target device
- OR use tunnel-based approach (Cloudflare/ngrok)

Don't waste time trying `nmap`, `arp-scan`, or Python network scanners — they're all blocked.
