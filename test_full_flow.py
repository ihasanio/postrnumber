import urllib.request
import ssl
import json
import uuid

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base = "https://api.7xwon.com/"

def post(endpoint, data, token="unlogged"):
    url = base + endpoint
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://7xwon.com",
        "Referer": "https://7xwon.com/"
    }
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8', errors='ignore'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8', errors='ignore'))
    except Exception as e:
        return 0, str(e)

print("1. Fetching /main-events:")
s, res = post("main-events", {})
print(f"Status: {s}, Success: {res.get('status')}")
events = res.get('data', [])
print(f"Total live/main events: {len(events)}")

if events:
    sample_ev = events[0]
    ev_id = sample_ev.get('eventid')
    print(f"\nSample Event: ID={ev_id}, {sample_ev.get('home')} vs {sample_ev.get('away')} (Live: {sample_ev.get('live')})")
    
    print(f"\n2. Fetching detailed odds for event {ev_id} via /event:")
    s, ev_detail = post("event", {"id": ev_id})
    print(f"Status: {s}, Success: {ev_detail.get('status')}")
    if ev_detail.get('status'):
        data = ev_detail.get('data', {})
        odds = data.get('odds', [])
        print(f"Markets count: {len(odds)}")
        for m in odds[:3]:
            print(f"\n  Market: {m.get('market_name')} (ID: {m.get('market_id')}, Code: {m.get('market_code')})")
            runners = m.get('runners', [])
            for r in runners[:3]:
                back = r.get('back', [])
                lay = r.get('lay', [])
                print(f"    Runner: {r.get('runner_name')} (ID: {r.get('selection_id')}) | Back: {back[:1]} | Lay: {lay[:1]}")

print("\n3. Testing dummy login to verify login response format:")
device_id = str(uuid.uuid4())
s, login_res = post("login", {"username": "test_probe", "password": "wrong_password", "device": device_id, "remember": False})
print(f"Login test: Status={s}, Response={login_res}")
