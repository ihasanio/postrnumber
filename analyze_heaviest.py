import urllib.request
import ssl
import json
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base = "https://api.7xwon.com/"

def fetch(endpoint, data=None):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer unlogged",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://7xwon.com"
    }
    body = json.dumps(data).encode('utf-8') if data else None
    t0 = time.perf_counter()
    req = urllib.request.Request(base + endpoint, data=body, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
        raw = r.read()
        dur = (time.perf_counter() - t0) * 1000
        js = json.loads(raw.decode('utf-8', errors='ignore'))
        return dur, len(raw), js

dur, size, res = fetch("main-events", {})
print(f"=== main-events Analysis ===")
print(f"Transfer Size: {size / 1024:.2f} KB ({size} bytes)")
print(f"Latency: {dur:.1f} ms")
events = res.get("data", [])
print(f"Total Matches in payload: {len(events)}")

# Inspect structure
if events:
    sample = events[0]
    print(f"Sample Match Keys: {list(sample.keys())}")
    print(f"Sample Match Content:\n{json.dumps(sample, indent=2, ensure_ascii=False)[:500]}")

# Let's count total nested objects / keys parsed in main-events
raw_str = json.dumps(res)
print(f"\nTotal characters: {len(raw_str)}")
print(f"Number of 'eventid': {raw_str.count('eventid')}")
print(f"Number of 'odds' or rates: {raw_str.count('price')}")
