"""
7xwon Live Events & Odds Poller / Monitor
Directly queries POST https://api.7xwon.com/main-events
"""
import ssl
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List

class SevenXWonEventsPoller:
    API_URL = "https://api.7xwon.com/main-events"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer unlogged",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://7xwon.com",
            "Referer": "https://7xwon.com/"
        }

    def fetch_main_events(self, type_val: int = 0, sport_id: int = 0) -> Dict[str, Any]:
        """
        Sends POST request to /main-events endpoint.
        Returns parsed JSON dict with latency and status.
        """
        payload = {}
        if type_val or sport_id:
            payload = {"type": type_val, "s": sport_id}

        body = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(self.API_URL, data=body, headers=self.headers, method="POST")

        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=self.timeout) as resp:
                elapsed_ms = (time.perf_counter() - t0) * 1000
                raw = resp.read()
                data = json.loads(raw.decode('utf-8', errors='ignore'))
                return {
                    "success": True,
                    "status_code": resp.status,
                    "latency_ms": round(elapsed_ms, 2),
                    "bytes": len(raw),
                    "data": data.get("data", [])
                }
        except urllib.error.HTTPError as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            err_body = e.read().decode('utf-8', errors='ignore')
            return {
                "success": False,
                "status_code": e.code,
                "latency_ms": round(elapsed_ms, 2),
                "error": err_body
            }
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return {
                "success": False,
                "status_code": 0,
                "latency_ms": round(elapsed_ms, 2),
                "error": str(e)
            }

    def print_live_summary(self, limit: int = 10):
        """Fetches and displays live matches in a clean terminal table."""
        res = self.fetch_main_events()
        if not res["success"]:
            print(f"[HATA] İstek başarısız: {res.get('error')} (Status: {res.get('status_code')})")
            return

        matches: List[Dict[str, Any]] = res["data"]
        live_matches = [m for m in matches if m.get("live") == 1]

        print("=" * 80)
        print(f"7XWON - CANLI VE BÜLTEN MAÇLARI (/main-events)")
        print(f"Yanıt Süresi: {res['latency_ms']} ms | Veri Boyutu: {res['bytes'] / 1024:.1f} KB")
        print(f"Toplam Maç: {len(matches)} | Canlı Maç: {len(live_matches)}")
        print("=" * 80)

        # Print top live matches
        for m in (live_matches[:limit] if live_matches else matches[:limit]):
            ev_id = m.get("eventid")
            home = m.get("home")
            away = m.get("away")
            league = m.get("league_name", "")
            info = m.get("info", {})
            score = f"{info.get('hs', 0)} - {info.get('as', 0)}"
            period = info.get("p", "")
            minute = f"{info.get('m', '')}'" if info.get('m') else ""
            is_live = "[CANLI]" if m.get("live") == 1 else "[BÜLTEN]"

            # Extract 1X2 odds if available
            odds_str = []
            for market in m.get("odds", []):
                if market.get("code") == "MATCH_ODDS":
                    for runner in market.get("runners", []):
                        back_p = runner.get("back", [{}])[0].get("price", "-") if runner.get("back") else "-"
                        lay_p = runner.get("lay", [{}])[0].get("price", "-") if runner.get("lay") else "-"
                        odds_str.append(f"B:{back_p}/L:{lay_p}")

            odds_repr = " | ".join(odds_str) if odds_str else "Oran Yok"
            print(f"{is_live:<8} ID: {ev_id} | {home} {score} {away} ({period} {minute}) [{league}]")
            if odds_str:
                print(f"         Oranlar (Back/Lay): {odds_repr}")
            print("-" * 80)

if __name__ == "__main__":
    poller = SevenXWonEventsPoller()
    poller.print_live_summary()
