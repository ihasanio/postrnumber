import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request("https://api.7xwon.com/main-events", 
                             data=b"{}", 
                             headers={
                                 "Content-Type": "application/json",
                                 "User-Agent": "Mozilla/5.0",
                                 "Origin": "https://7xwon.com"
                             }, 
                             method="POST")

try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        print("Status:", r.status)
        print("Server Headers:")
        for k, v in r.getheaders():
            print(f"  {k}: {v}")
except Exception as e:
    print("Error:", e)
