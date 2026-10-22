import urllib.request
import ssl
import json
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base = "https://api.7xwon.com/"

endpoints_to_test = [
    # (name, endpoint, method, payload)
    ("Ana Maçlar / Canlı Bülten", "main-events", "POST", {}),
    ("Ülkeler Listesi", "countries", "POST", {}),
    ("Ligler Listesi", "leagues", "POST", {}),
    ("Arama", "search", "POST", {"search": "Madrid"}),
    ("Hızlı Bülten (Fast)", "fast", "POST", {}),
    ("Perform Verisi", "perform", "POST", {}),
    ("Oran Tipleri", "oddstypes", "POST", {}),
    ("Sistem Durumu", "system-status", "POST", {}),
    ("Tek Maç Detay ve Oranlar (Event)", "event", "POST", {}), # ID doldurulacak
    ("Kullanıcı Bilgisi (Oturumsuz)", "user", "GET", None),
    ("Giriş Denemesi (Login)", "login", "POST", {"username": "test", "password": "123", "device": "probe"}),
    ("Kupon Gönderimi (Send)", "send", "POST", {}),
    ("Bahis Listesi (Bets)", "bets", "POST", {"limit": 10, "offset": 0}),
    ("Bahis İptali (Cancel)", "cancel", "POST", {"id": 12345}),
    ("Özel Oranlar (special-odds)", "special-odds", "POST", {}),
    ("Özel Oran Merkezi (special-odds-center)", "special-odds-center", "POST", {}),
    ("Risk Verisi (risks)", "risks", "POST", {}),
    ("Para İşlemleri (money)", "money", "POST", {}),
    ("Transfer İşlemleri (transactions)", "transactions", "POST", {}),
    ("Kullanıcı Yönetimi (users)", "users", "POST", {})
]

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
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            dur = (time.perf_counter() - t0) * 1000
            res_raw = resp.read().decode('utf-8', errors='ignore')
            try:
                js = json.loads(res_raw)
            except:
                js = res_raw[:150]
            return resp.status, dur, js, len(res_raw)
    except urllib.error.HTTPError as e:
        dur = (time.perf_counter() - t0) * 1000
        res_raw = e.read().decode('utf-8', errors='ignore')
        try:
            js = json.loads(res_raw)
        except:
            js = res_raw[:150]
        return e.code, dur, js, len(res_raw)
    except Exception as e:
        dur = (time.perf_counter() - t0) * 1000
        return 0, dur, str(e), 0

print(f"{'Endpoint':<30} | {'Status':<6} | {'Süre (ms)':<9} | {'Boyut':<8} | {'Sonuç Özeti'}")
print("-" * 95)

# First get main events to find an event ID
_, _, ev_res, _ = make_req("main-events", "POST", {})
sample_event_id = None
if isinstance(ev_res, dict) and ev_res.get("data"):
    sample_event_id = ev_res["data"][0].get("eventid")

for name, ep, method, payload in endpoints_to_test:
    if ep == "event" and sample_event_id:
        payload = {"id": sample_event_id}
        
    code, dur, res, size = make_req(ep, method, payload)
    
    # Summary of response
    if isinstance(res, dict):
        status_field = res.get("status")
        msg = res.get("msg") or res.get("message")
        data_len = len(res.get("data", [])) if isinstance(res.get("data"), list) else ("dict" if isinstance(res.get("data"), dict) else "-")
        summary = f"status={status_field}"
        if msg:
            summary += f", msg='{msg}'"
        if data_len != "-":
            summary += f", items={data_len}"
    else:
        summary = str(res)[:40]
        
    print(f"{method + ' /' + ep:<30} | {code:<6} | {dur:>7.1f}ms | {size:>6} B | {summary}")
