#!/usr/bin/env python3
"""Check if MEXC 6026 block has cleared. Uses urllib direct (NOT MEXCClient/CF Worker).
Exit 0 = CLEAR, Exit 1 = BLOCKED, Exit 2 = ERROR."""
import json, time, hmac, hashlib, urllib.request, ssl, sys

AK = open('/root/.hermes/secrets/mexc_api_key.txt').read().strip()
SK = open('/root/.hermes/secrets/mexc_secret_key.txt').read().strip()

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def sign(body=''):
    ts = str(int(time.time()*1000))
    sig = hmac.new(SK.encode(), (AK+ts+body).encode(), hashlib.sha256).hexdigest()
    return {'ApiKey': AK, 'Request-Time': ts, 'Signature': sig, 'Content-Type': 'application/json'}, ts

# Balance
try:
    h, _ = sign()
    req = urllib.request.Request('https://api.mexc.com/api/v1/private/account/assets', headers=h)
    resp = urllib.request.urlopen(req, timeout=10, context=ctx)
    d = json.loads(resp.read())
    equity = 0
    for a in d.get('data', []):
        if a.get('currency') == 'USDT':
            equity = float(a.get('equity', 0))
            break
except:
    equity = -1

# 6026 test
try:
    body = json.dumps({'symbol':'ETH_USDT','price':'0','vol':1,'side':1,'type':5,'openType':2,'leverage':1}, separators=(',',':'))
    h, ts = sign(body)
    req = urllib.request.Request('https://api.mexc.com/api/v1/private/order/submit', data=body.encode(), headers=h, method='POST')
    resp = urllib.request.urlopen(req, timeout=10, context=ctx)
    d = json.loads(resp.read())
    if d.get('success') or d.get('code') == 0:
        close = json.dumps({'symbol':'ETH_USDT','price':'0','vol':1,'side':2,'type':5,'openType':2,'leverage':1}, separators=(',',':'))
        h2, _ = sign(close)
        req2 = urllib.request.Request('https://api.mexc.com/api/v1/private/order/submit', data=close.encode(), headers=h2, method='POST')
        urllib.request.urlopen(req2, timeout=10, context=ctx)
        print(f'CLEAR|{equity}')
        sys.exit(0)
    else:
        print(f'BLOCKED|{equity}|{d.get("code")}')
        sys.exit(1)
except urllib.error.HTTPError as e:
    try:
        d = json.loads(e.read().decode())
        if d.get('code') == 6026:
            print(f'BLOCKED|{equity}|6026')
            sys.exit(1)
        else:
            print(f'ERROR|{equity}|{d.get("code")}')
            sys.exit(2)
    except:
        print(f'ERROR|{equity}|-1')
        sys.exit(2)
except Exception as e:
    print(f'ERROR|{equity}|{str(e)[:50]}')
    sys.exit(2)
