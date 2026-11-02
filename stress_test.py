"""
Gercek async stres testi - aiohttp ile 500 eslezamanli baglanti
"""
import asyncio
import aiohttp
import time
import json
import ssl
import random
from collections import defaultdict

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer unlogged",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://7xwon.com",
    "Referer": "https://7xwon.com/"
}

SEARCH_TERMS = ["Galatasaray","Fenerbahce","Besiktas","Barcelona","Real Madrid",
                "Liverpool","Chelsea","Bayern","Juventus","Manchester","Ajax"]

ENDPOINTS = [
    {"name": "/main-events",  "url": "https://api.7xwon.com/main-events",
     "body": lambda: {"type": 0, "odds": False, "code": False, "s": 1, "t": False, "_ts": int(time.time()*1000)}},
    {"name": "/search",       "url": "https://api.7xwon.com/search",
     "body": lambda: {"search": random.choice(SEARCH_TERMS)}},
    {"name": "/countries",    "url": "https://api.7xwon.com/countries",
     "body": lambda: {}},
    {"name": "/login",        "url": "https://api.7xwon.com/login",
     "body": lambda: {"username": f"user{random.randint(1,9999)}", "password": "test123"}},
]

WORKERS_PER_ENDPOINT = 250   # 250x4 = 1000 baglanti
DURATION = 20                # saniye
stats = defaultdict(lambda: {"total":0,"ok":0,"errors":defaultdict(int),"lats":[]})
stop = asyncio.Event()

async def worker(session: aiohttp.ClientSession, ep: dict):
    name = ep["name"]
    url  = ep["url"]
    while not stop.is_set():
        body = ep["body"]()
        t0 = time.perf_counter()
        try:
            async with session.post(url, json=body, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as r:
                await r.read()
                lat = (time.perf_counter() - t0) * 1000
                stats[name]["total"] += 1
                stats[name]["lats"].append(lat)
                if r.status in (200,201):
                    stats[name]["ok"] += 1
                else:
                    stats[name]["errors"][r.status] += 1
        except Exception as ex:
            lat = (time.perf_counter() - t0) * 1000
            stats[name]["total"] += 1
            stats[name]["errors"][0] += 1
            stats[name]["lats"].append(lat)

async def reporter():
    t0 = time.time()
    while not stop.is_set():
        await asyncio.sleep(5)
        el = time.time() - t0
        print(f"\n{'='*72}")
        print(f"  Sure: {el:.0f}s / {DURATION}s  |  {WORKERS_PER_ENDPOINT*len(ENDPOINTS)} eslezamanli worker")
        print(f"{'='*72}")
        print(f"{'Endpoint':<18} {'Total':>6} {'200OK':>6} {'HATA':>6} {'req/s':>6} {'Ort ms':>7} {'Durum'}")
        print(f"{'-'*72}")
        for ep in ENDPOINTS:
            n = ep["name"]
            d = stats[n]
            tot = d["total"]; ok = d["ok"]; errs = tot - ok
            rps = tot / max(el,1)
            avg = sum(d["lats"][-100:])/len(d["lats"][-100:]) if d["lats"] else 0
            err_codes = dict(d["errors"])
            icon = "GREEN OK" if errs < tot*0.1 else "RED HATA"
            print(f"{n:<18} {tot:>6} {ok:>6} {errs:>6} {rps:>6.1f} {avg:>6.0f}ms  {icon}")
            if err_codes:
                print(f"  Hata kodlari: {err_codes}")

async def main():
    conn = aiohttp.TCPConnector(limit=0, ssl=False)
    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = []
        for ep in ENDPOINTS:
            for _ in range(WORKERS_PER_ENDPOINT):
                tasks.append(asyncio.create_task(worker(session, ep)))
        tasks.append(asyncio.create_task(reporter()))

        print(f"\nSTRES TESTI BASLIYOR: {len(ENDPOINTS)} endpoint x {WORKERS_PER_ENDPOINT} worker = {len(ENDPOINTS)*WORKERS_PER_ENDPOINT} BAGLANTI")
        print(f"Sure: {DURATION}s\n")

        await asyncio.sleep(DURATION)
        stop.set()
        await asyncio.gather(*tasks, return_exceptions=True)

    print(f"\n{'='*72}")
    print("  FINAL RAPOR")
    print(f"{'='*72}")
    for ep in ENDPOINTS:
        n = ep["name"]
        d = stats[n]
        tot = d["total"]; ok = d["ok"]
        rps = tot / DURATION
        avg = sum(d["lats"]) / len(d["lats"]) if d["lats"] else 0
        err_codes = dict(d["errors"])
        print(f"\n  {n}")
        print(f"    Toplam: {tot}  Basarili: {ok}  Hata: {tot-ok}  req/s: {rps:.1f}  Gecikme: {avg:.0f}ms")
        if err_codes:
            print(f"    Hata detay: {err_codes}")
            if 429 in err_codes:
                print(f"    *** 429 RATE-LIMIT! Bu endpoint baskiyi hissetti ***")
            if any(k>=500 for k in err_codes if k):
                print(f"    *** 5xx SUNUCU HATASI! Bu endpoint coktu/yavasladl ***")

if __name__ == "__main__":
    asyncio.run(main())
