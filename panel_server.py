import asyncio
import json
import ssl
import time
import urllib.request
from typing import Dict, Any, Optional
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="7xwon Monitor Panel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global monitor state
state = {
    "is_running": False,
    "interval_seconds": 2.5,  # default same as original site
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "last_latency_ms": 0,
    "last_bytes": 0,
    "last_update_time": None,
    "last_error": None,
    "live_matches_count": 0,
    "total_matches_count": 0,
    "matches_sample": []
}

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer unlogged",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Origin": "https://7xwon.com",
    "Referer": "https://7xwon.com/"
}

def perform_single_fetch() -> Dict[str, Any]:
    url = "https://api.7xwon.com/main-events"
    req = urllib.request.Request(url, data=b"{}", headers=HEADERS, method="POST")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=10) as resp:
            dur = (time.perf_counter() - t0) * 1000
            raw = resp.read()
            data = json.loads(raw.decode('utf-8', errors='ignore'))
            return {"success": True, "code": resp.status, "dur": dur, "bytes": len(raw), "data": data.get("data", [])}
    except Exception as e:
        dur = (time.perf_counter() - t0) * 1000
        return {"success": False, "code": 0, "dur": dur, "bytes": 0, "error": str(e)}

async def background_loop():
    while True:
        if state["is_running"]:
            state["total_requests"] += 1
            res = await asyncio.to_thread(perform_single_fetch)
            state["last_latency_ms"] = round(res["dur"], 1)
            state["last_bytes"] = res["bytes"]
            state["last_update_time"] = time.strftime("%H:%M:%S")

            if res["success"]:
                state["successful_requests"] += 1
                state["last_error"] = None
                matches = res["data"]
                state["total_matches_count"] = len(matches)
                live = [m for m in matches if m.get("live") == 1]
                state["live_matches_count"] = len(live)

                # Store sample matches for display
                sample = []
                for m in (live[:12] if live else matches[:12]):
                    info = m.get("info", {})
                    score = f"{info.get('hs', 0)} - {info.get('as', 0)}"
                    time_str = f"{info.get('p', '')} {info.get('m', '')}'".strip()
                    sample.append({
                        "id": m.get("eventid"),
                        "home": m.get("home"),
                        "away": m.get("away"),
                        "league": m.get("league_name"),
                        "score": score,
                        "time": time_str,
                        "live": m.get("live") == 1,
                        "matched": m.get("matched", 0)
                    })
                state["matches_sample"] = sample
            else:
                state["failed_requests"] += 1
                state["last_error"] = res.get("error")

            # Sleep configured interval
            interval = max(0.5, float(state["interval_seconds"]))
            await asyncio.sleep(interval)
        else:
            await asyncio.sleep(0.5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_loop())

@app.get("/api/state")
def get_state():
    return JSONResponse(state)

@app.post("/api/start")
def start_monitor():
    state["is_running"] = True
    return JSONResponse({"status": "started", "interval": state["interval_seconds"]})

@app.post("/api/stop")
def stop_monitor():
    state["is_running"] = False
    return JSONResponse({"status": "stopped"})

@app.post("/api/set-interval")
def set_interval(payload: Dict[str, Any]):
    sec = float(payload.get("seconds", 2.5))
    if sec < 0.5:
        sec = 0.5  # minimum 0.5s safety limit
    state["interval_seconds"] = sec
    return JSONResponse({"interval_seconds": state["interval_seconds"]})

@app.get("/", response_class=HTMLResponse)
def index_page():
    return """
<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <title>7xwon /main-events Hız & İstek Paneli</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { background-color: #0f172a; color: #f8fafc; font-family: system-ui, -apple-system, sans-serif; }
  </style>
</head>
<body class="p-6">
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between border-b border-slate-700 pb-4">
      <div>
        <h1 class="text-2xl font-bold text-amber-400">7xwon /main-events Kontrol Paneli</h1>
        <p class="text-xs text-slate-400 mt-1">Hedef: https://api.7xwon.com/main-events (Canlı Borsa ve Bülten)</p>
      </div>
      <div class="flex items-center gap-3">
        <span id="badgeStatus" class="px-3 py-1 rounded-full text-xs font-semibold bg-red-900/60 text-red-300 border border-red-700">DURDURULDU</span>
      </div>
    </div>

    <!-- Controls Card -->
    <div class="bg-slate-800/80 p-5 rounded-xl border border-slate-700 grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
      <div>
        <label class="block text-xs uppercase font-semibold text-slate-400 mb-2">İstek Aralığı (Saniye)</label>
        <div class="flex items-center gap-2">
          <input id="secInput" type="number" step="0.5" min="0.5" value="2.5" class="bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 w-32 text-center text-amber-300 font-bold focus:outline-none focus:border-amber-400">
          <button onclick="applyInterval()" class="bg-slate-700 hover:bg-slate-600 px-4 py-2 rounded-lg text-xs font-semibold">Uygula</button>
        </div>
        <span class="text-[11px] text-slate-400 mt-1 block">Orijinal sitede: 2.5 sn</span>
      </div>

      <div class="flex gap-3">
        <button id="btnStart" onclick="startMonitor()" class="flex-1 bg-emerald-600 hover:bg-emerald-500 font-bold py-3 rounded-lg text-sm transition">BAŞLAT</button>
        <button id="btnStop" onclick="stopMonitor()" class="flex-1 bg-rose-600 hover:bg-rose-500 font-bold py-3 rounded-lg text-sm transition">DURDUR</button>
      </div>

      <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-700 text-xs space-y-1">
        <div class="flex justify-between"><span class="text-slate-400">Son Güncelleme:</span> <span id="lblTime" class="font-mono text-amber-300">-</span></div>
        <div class="flex justify-between"><span class="text-slate-400">Son Gecikme:</span> <span id="lblLatency" class="font-mono text-emerald-400">-</span></div>
        <div class="flex justify-between"><span class="text-slate-400">Paket Boyutu:</span> <span id="lblBytes" class="font-mono text-blue-300">-</span></div>
      </div>
    </div>

    <!-- Metrics Stats -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
        <span class="text-xs text-slate-400">Toplam İstek</span>
        <div id="statTotal" class="text-2xl font-black text-slate-100 mt-1">0</div>
      </div>
      <div class="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
        <span class="text-xs text-slate-400">Başarılı</span>
        <div id="statSuccess" class="text-2xl font-black text-emerald-400 mt-1">0</div>
      </div>
      <div class="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
        <span class="text-xs text-slate-400">Hata</span>
        <div id="statFailed" class="text-2xl font-black text-rose-400 mt-1">0</div>
      </div>
      <div class="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
        <span class="text-xs text-slate-400">Canlı / Toplam Maç</span>
        <div id="statMatches" class="text-2xl font-black text-amber-400 mt-1">0 / 0</div>
      </div>
    </div>

    <!-- Error Banner -->
    <div id="errorBanner" class="hidden bg-rose-900/40 border border-rose-700 p-3 rounded-lg text-rose-300 text-xs"></div>

    <!-- Matches Table -->
    <div class="bg-slate-800/80 rounded-xl border border-slate-700 overflow-hidden">
      <div class="p-4 border-b border-slate-700 flex justify-between items-center">
        <h2 class="text-sm font-bold uppercase tracking-wider text-slate-300">Gelen Canlı Maçlar</h2>
        <span class="text-xs text-slate-400">Her istekte güncellenir</span>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-900/60 text-slate-400 uppercase text-[10px] tracking-wider">
            <tr>
              <th class="p-3">ID</th>
              <th class="p-3">Durum</th>
              <th class="p-3">Karşılaşma</th>
              <th class="p-3">Lig</th>
              <th class="p-3">Skor / Süre</th>
              <th class="p-3">Hacim (Matched)</th>
            </tr>
          </thead>
          <tbody id="matchesBody" class="divide-y divide-slate-700/60">
            <tr><td colspan="6" class="p-4 text-center text-slate-500">Henüz istek gönderilmedi veya maç yok.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    async function updateUI() {
      try {
        const res = await fetch('/api/state');
        const data = await res.json();

        // Status badge
        const badge = document.getElementById('badgeStatus');
        if (data.is_running) {
          badge.textContent = `ÇALIŞIYOR (${data.interval_seconds}s)`;
          badge.className = "px-3 py-1 rounded-full text-xs font-semibold bg-emerald-900/60 text-emerald-300 border border-emerald-700 animate-pulse";
        } else {
          badge.textContent = "DURDURULDU";
          badge.className = "px-3 py-1 rounded-full text-xs font-semibold bg-red-900/60 text-red-300 border border-red-700";
        }

        // Stats
        document.getElementById('lblTime').textContent = data.last_update_time || '-';
        document.getElementById('lblLatency').textContent = data.last_latency_ms ? data.last_latency_ms + ' ms' : '-';
        document.getElementById('lblBytes').textContent = data.last_bytes ? (data.last_bytes / 1024).toFixed(1) + ' KB' : '-';

        document.getElementById('statTotal').textContent = data.total_requests;
        document.getElementById('statSuccess').textContent = data.successful_requests;
        document.getElementById('statFailed').textContent = data.failed_requests;
        document.getElementById('statMatches').textContent = `${data.live_matches_count} / ${data.total_matches_count}`;

        // Error
        const errBanner = document.getElementById('errorBanner');
        if (data.last_error) {
          errBanner.textContent = "Son Hata: " + data.last_error;
          errBanner.classList.remove('hidden');
        } else {
          errBanner.classList.add('hidden');
        }

        // Table
        const tbody = document.getElementById('matchesBody');
        if (data.matches_sample && data.matches_sample.length > 0) {
          tbody.innerHTML = data.matches_sample.map(m => `
            <tr class="hover:bg-slate-700/30">
              <td class="p-3 font-mono text-slate-400">${m.id}</td>
              <td class="p-3">${m.live ? '<span class="px-2 py-0.5 rounded text-[10px] bg-red-900/60 text-red-300 border border-red-700 font-bold">CANLI</span>' : '<span class="px-2 py-0.5 rounded text-[10px] bg-slate-700 text-slate-300">BÜLTEN</span>'}</td>
              <td class="p-3 font-semibold text-slate-200">${m.home} - ${m.away}</td>
              <td class="p-3 text-slate-400">${m.league || '-'}</td>
              <td class="p-3 font-mono text-amber-300 font-bold">${m.score} <span class="text-xs font-normal text-slate-400">(${m.time})</span></td>
              <td class="p-3 font-mono text-slate-300">${m.matched || 0}</td>
            </tr>
          `).join('');
        }
      } catch (e) {
        console.error(e);
      }
    }

    async function startMonitor() {
      await fetch('/api/start', { method: 'POST' });
      updateUI();
    }

    async function stopMonitor() {
      await fetch('/api/stop', { method: 'POST' });
      updateUI();
    }

    async function applyInterval() {
      const val = parseFloat(document.getElementById('secInput').value);
      if (val >= 0.5) {
        await fetch('/api/set-interval', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ seconds: val })
        });
        updateUI();
      }
    }

    setInterval(updateUI, 1000);
    updateUI();
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8082)
