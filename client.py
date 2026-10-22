import ssl
import json
import uuid
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

class SevenXWonClient:
    """
    7xwon (Bet Exchange Systems) API Client.
    Connects directly to https://api.7xwon.com/
    """
    BASE_URL = "https://api.7xwon.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.device_id = str(uuid.uuid4())
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def _request(self, endpoint: str, method: str = "POST", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        token_str = self.token if self.token else "unlogged"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token_str}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": "https://7xwon.com",
            "Referer": "https://7xwon.com/"
        }
        body = json.dumps(data).encode('utf-8') if data is not None else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=15) as resp:
                res_bytes = resp.read().decode('utf-8', errors='ignore')
                return json.loads(res_bytes)
        except urllib.error.HTTPError as e:
            err_bytes = e.read().decode('utf-8', errors='ignore')
            try:
                return json.loads(err_bytes)
            except:
                return {"status": False, "msg": f"HTTP {e.code}: {err_bytes[:200]}"}
        except Exception as e:
            return {"status": False, "msg": str(e)}

    def login(self, username: str, password: str) -> Dict[str, Any]:
        payload = {
            "username": username,
            "password": password,
            "device": self.device_id,
            "remember": False
        }
        res = self._request("login", method="POST", data=payload)
        if res.get("status") and isinstance(res.get("data"), dict):
            self.token = res["data"].get("token")
        return res

    def get_user_info(self) -> Dict[str, Any]:
        return self._request("user", method="GET")

    def get_main_events(self) -> Dict[str, Any]:
        """Fetch all live and upcoming exchange events."""
        return self._request("main-events", method="POST", data={})

    def get_event_detail(self, event_id: int) -> Dict[str, Any]:
        """Fetch odds, Back & Lay runners for a specific event."""
        return self._request("event", method="POST", data={"id": event_id})

    def send_bet(self, eventid: int, market_id: str, selection_id: int, side: str, amount: float, price: float, handicap: float = 0, co: int = 0, special: bool = False) -> Dict[str, Any]:
        """
        Place an exchange order.
        side: 'back' (Lehine) or 'lay' (Aleyhine)
        price: Desired exchange odds
        amount: Stake in TL
        """
        payload = {
            "eventid": eventid,
            "market_id": market_id,
            "selection_id": selection_id,
            "handicap": handicap,
            "side": side.lower(),
            "amount": amount,
            "price": price,
            "co": co,
            "special": special
        }
        return self._request("send", method="POST", data=payload)

    def get_bets(self, limit: int = 50, offset: int = 0, status: Optional[str] = None) -> Dict[str, Any]:
        payload = {"limit": limit, "offset": offset}
        if status is not None:
            payload["status"] = status
        return self._request("bets", method="POST", data=payload)

    def cancel_bet(self, bet_id: str) -> Dict[str, Any]:
        """Cancel an unmatched exchange order."""
        return self._request("cancel", method="POST", data={"id": bet_id})

if __name__ == "__main__":
    client = SevenXWonClient()
    print("Testing 7xwon client...")
    events = client.get_main_events()
    data = events.get("data", [])
    print(f"Loaded {len(data)} events from 7xwon API!")
    if data:
        ev = data[0]
        print(f"Top Event: {ev.get('home')} vs {ev.get('away')} (ID: {ev.get('eventid')})")
        detail = client.get_event_detail(ev.get('eventid'))
        print(f"Detail markets count: {len(detail.get('data', {}).get('odds', []))}")
