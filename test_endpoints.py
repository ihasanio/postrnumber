import urllib.request
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base = "https://api.7xwon.com/"

def make_req(endpoint, method="POST", data=None, token="unlogged"):
    url = base + endpoint
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://7xwon.com",
        "Referer": "https://7xwon.com/"
    }
    body = json.dumps(data).encode('utf-8') if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            try:
                js = json.loads(content)
                return resp.status, js
            except:
                return resp.status, content[:500]
    except urllib.error.HTTPError as e:
        err_content = e.read().decode('utf-8', errors='ignore')
        try:
            return e.code, json.loads(err_content)
        except:
            return e.code, err_content[:500]
    except Exception as e:
        return 0, str(e)

print("1. Testing GET /user without token:")
status, res = make_req("user", method="GET")
print("Status:", status, "Response:", res)

print("\n2. Testing POST /main-events:")
status, res = make_req("main-events", method="POST", data={})
print("Status:", status)
if isinstance(res, list):
    print("Items count:", len(res))
    if len(res) > 0:
        print("Sample item:", json.dumps(res[0], indent=2, ensure_ascii=False)[:300])
elif isinstance(res, dict):
    print("Dict keys:", list(res.keys()))
    print("Sample:", json.dumps(res, indent=2, ensure_ascii=False)[:300])
else:
    print("Response:", res)

print("\n3. Testing POST /matches:")
status, res = make_req("matches", method="POST", data={})
print("Status:", status)
if isinstance(res, list):
    print("Matches count:", len(res))
    if len(res) > 0:
        print("Sample match:", json.dumps(res[0], indent=2, ensure_ascii=False)[:400])
elif isinstance(res, dict):
    print("Dict keys:", list(res.keys()))
    print("Sample:", json.dumps(res, indent=2, ensure_ascii=False)[:400])
else:
    print("Response:", res)

print("\n4. Testing POST /countries:")
status, res = make_req("countries", method="POST", data={})
print("Status:", status, "Result count/keys:", len(res) if isinstance(res, (list, dict)) else res)
