import asyncio
import json
import ssl
import time
import os
import threading
import urllib.request
from typing import Dict, Any, Optional
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Universal HTTP POST / Request Runner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BIG_PAYLOAD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "big_payload.json")

# State
state = {
    "is_running": False,
    "workers": 1,
    "url": "https://api.7xwon.com/main-events",
    "method": "POST",
    "interval_seconds": 0.1,
    "headers_raw": json.dumps({
        "Content-Type": "application/json",
        "Authorization": "Bearer unlogged",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin": "https://7xwon.com",
        "Referer": "https://7xwon.com/"
    }, indent=2),
    "body_raw": json.dumps({
        "type": 0,
        "odds": False,
        "code": False,
        "s": 1,
        "t": False
    }, indent=2),
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "last_status_code": None,
    "last_latency_ms": 0,
    "last_bytes": 0,
    "last_update_time": None,
    "last_response": "",
    "last_error": None,
    "history": [],
    "active_workers": 0,
    "requests_per_second": 0.0,
}

# Track per-second throughput
_rps_counter = {"count": 0, "last_reset": time.time()}
_state_lock = threading.Lock()

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def execute_http_request(url: str, method: str, headers_dict: dict, body_str: str) -> Dict[str, Any]:
    t0 = time.perf_counter()
    data_bytes = body_str.encode('utf-8') if (body_str and method.upper() in ["POST", "PUT", "PATCH"]) else None
    req = urllib.request.Request(url, data=data_bytes, headers=headers_dict, method=method.upper())
    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=15) as resp:
            elapsed = (time.perf_counter() - t0) * 1000
            raw = resp.read()
            text = raw.decode('utf-8', errors='ignore')
            return {"success": True, "status_code": resp.status, "latency_ms": round(elapsed, 1), "bytes": len(raw), "body": text, "error": None}
    except urllib.error.HTTPError as e:
        elapsed = (time.perf_counter() - t0) * 1000
        raw = e.read()
        text = raw.decode('utf-8', errors='ignore')
        return {"success": False, "status_code": e.code, "latency_ms": round(elapsed, 1), "bytes": len(raw), "body": text, "error": f"HTTP {e.code}"}
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        return {"success": False, "status_code": 0, "latency_ms": round(elapsed, 1), "bytes": 0, "body": "", "error": str(e)}

async def single_worker(worker_id: int):
    """Tek bir worker — durana kadar istek atar."""
    while state["is_running"]:
        try:
            headers = json.loads(state["headers_raw"]) if state["headers_raw"].strip() else {}
        except Exception:
            headers = {"Content-Type": "application/json"}

        body = state["body_raw"]
        url = state["url"]
        method = state["method"]

        res = await asyncio.to_thread(execute_http_request, url, method, headers, body)

        with _state_lock:
            state["total_requests"] += 1
            state["last_latency_ms"] = res["latency_ms"]
            state["last_bytes"] = res["bytes"]
            state["last_status_code"] = res["status_code"]
            state["last_update_time"] = time.strftime("%H:%M:%S")
            state["last_response"] = res["body"][:4000]

            if res["success"]:
                state["successful_requests"] += 1
                state["last_error"] = None
            else:
                state["failed_requests"] += 1
                state["last_error"] = res["error"]

            state["history"].insert(0, {
                "time": state["last_update_time"],
                "status": res["status_code"],
                "latency": res["latency_ms"],
                "bytes": res["bytes"],
                "success": res["success"]
            })
            if len(state["history"]) > 50:
                state["history"].pop()

            _rps_counter["count"] += 1
            now = time.time()
            elapsed_sec = now - _rps_counter["last_reset"]
            if elapsed_sec >= 1.0:
                state["requests_per_second"] = round(_rps_counter["count"] / elapsed_sec, 1)
                _rps_counter["count"] = 0
                _rps_counter["last_reset"] = now

        interval = max(0.01, float(state["interval_seconds"]))
        await asyncio.sleep(interval)


# Global runner task holder
_runner_tasks: list = []

async def runner_manager():
    """Worker sayısını takip eder, ekler/kaldırır."""
    global _runner_tasks
    while True:
        if state["is_running"]:
            desired = int(state["workers"])
            current = len([t for t in _runner_tasks if not t.done()])
            state["active_workers"] = current

            if current < desired:
                for i in range(desired - current):
                    task = asyncio.create_task(single_worker(current + i))
                    _runner_tasks.append(task)
            elif current > desired:
                # fazla worker'ları iptal et
                to_cancel = current - desired
                cancelled = 0
                for t in _runner_tasks:
                    if not t.done() and cancelled < to_cancel:
                        t.cancel()
                        cancelled += 1
                _runner_tasks = [t for t in _runner_tasks if not t.done()]
        else:
            # Dur komutu: tüm worker'ları iptal et
            for t in _runner_tasks:
                if not t.done():
                    t.cancel()
            _runner_tasks = []
            state["active_workers"] = 0

        await asyncio.sleep(0.3)


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(runner_manager())

@app.get("/api/state")
def get_state():
    return JSONResponse(state)

@app.get("/api/get-big-payload")
def get_big_payload():
    if os.path.exists(BIG_PAYLOAD_PATH):
        with open(BIG_PAYLOAD_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content, media_type="application/json")
    return JSONResponse({"error": "Dosya bulunamadi"}, status_code=404)

@app.post("/api/update-config")
def update_config(payload: Dict[str, Any]):
    if "url" in payload:
        state["url"] = payload["url"].strip()
    if "method" in payload:
        state["method"] = payload["method"].strip().upper()
    if "interval_seconds" in payload:
        state["interval_seconds"] = max(0.01, float(payload["interval_seconds"]))
    if "headers_raw" in payload:
        state["headers_raw"] = payload["headers_raw"]
    if "body_raw" in payload:
        state["body_raw"] = payload["body_raw"]
    if "workers" in payload:
        state["workers"] = max(1, min(50, int(payload["workers"])))
    return JSONResponse({"success": True, "state": state})

@app.post("/api/start")
def start_runner(payload: Optional[Dict[str, Any]] = None):
    if payload:
        update_config(payload)
    state["is_running"] = True
    return JSONResponse({"status": "running"})

@app.post("/api/stop")
def stop_runner():
    state["is_running"] = False
    return JSONResponse({"status": "stopped"})

@app.post("/api/clear-stats")
def clear_stats():
    state["total_requests"] = 0
    state["successful_requests"] = 0
    state["failed_requests"] = 0
    state["history"] = []
    state["last_error"] = None
    state["requests_per_second"] = 0.0
    _rps_counter["count"] = 0
    _rps_counter["last_reset"] = time.time()
    return JSONResponse({"status": "cleared"})

@app.post("/api/send-once")
async def send_once(payload: Dict[str, Any]):
    url = payload.get("url", state["url"]).strip()
    method = payload.get("method", state["method"]).strip().upper()
    body = payload.get("body_raw", state["body_raw"])
    try:
        headers = json.loads(payload.get("headers_raw", state["headers_raw"]))
    except Exception:
        headers = {"Content-Type": "application/json"}
    res = await asyncio.to_thread(execute_http_request, url, method, headers, body)
    return JSONResponse(res)

@app.get("/", response_class=HTMLResponse)
def index_html():
    return """<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Canlı POST & İstek Paneli</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { background-color: #0b0f19; color: #f1f5f9; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; }
    textarea, input, select { background-color: #151c2c; border: 1px solid #2d3748; }
    textarea:focus, input:focus, select:focus { border-color: #f59e0b; outline: none; }
    .worker-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin: 1px; }
  </style>
</head>
<body class="p-4 md:p-8">
  <div class="max-w-7xl mx-auto space-y-6">

    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between border-b border-slate-800 pb-4 gap-4">
      <div>
        <h1 class="text-2xl font-black text-amber-400 tracking-wide flex items-center gap-2">
          ⚡ Canlı POST & İstek Paneli
        </h1>
        <p class="text-xs text-slate-400 mt-1">İstediğin URL'ye, istediğin JSON Body ve Header ile belirlediğin saniyede bir otomatik POST at.</p>
      </div>
      <div class="flex items-center gap-3">
        <span id="rpsCounter" class="px-3 py-1.5 rounded-full text-xs font-black bg-purple-950 text-purple-300 border border-purple-800">
          0 req/s
        </span>
        <span id="runnerStatus" class="px-4 py-1.5 rounded-full text-xs font-bold bg-rose-950 text-rose-300 border border-rose-800">
          DURDURULDU
        </span>
        <button onclick="clearStats()" class="text-xs text-slate-400 hover:text-slate-200 bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700">
          Sayaçları Sıfırla
        </button>
      </div>
    </div>

    <!-- Quick Preset Buttons -->
    <div class="flex flex-wrap items-center gap-2 text-xs bg-slate-900/90 p-3 rounded-xl border border-slate-800">
      <span class="text-amber-400 font-bold uppercase tracking-wider text-[11px]">Şablon Seç:</span>
      <button id="btn2MB" onclick="load2MBPayload()" class="bg-gradient-to-r from-red-600 to-amber-600 hover:from-red-500 hover:to-amber-500 text-white font-black px-4 py-2 rounded-lg border border-amber-400 shadow-lg shadow-red-900/50 flex items-center gap-1.5 cursor-pointer text-sm">
        💥 2 MB BÜYÜK PAYLOAD YÜKLE
      </button>
      <button onclick="loadPreset('7xwon_main')" class="bg-slate-800 hover:bg-slate-700 text-amber-300 px-3 py-1.5 rounded-lg border border-slate-700">Orijinal /main-events (Normal)</button>
      <button onclick="loadPreset('7xwon_login')" class="bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700">/login (Giriş)</button>
      <button onclick="loadPreset('7xwon_countries')" class="bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700">/countries</button>
      <button onclick="loadPreset('7xwon_search')" class="bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg border border-slate-700">/search</button>
    </div>

    <!-- Main Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

      <!-- Left Config Section -->
      <div class="lg:col-span-7 space-y-4 bg-slate-900/80 p-5 rounded-2xl border border-slate-800">

        <!-- URL & Method Bar -->
        <div class="flex flex-col sm:flex-row gap-2">
          <select id="inputMethod" class="rounded-xl px-3 py-2.5 font-bold text-amber-400 text-xs w-full sm:w-28 cursor-pointer">
            <option value="POST">POST</option>
            <option value="GET">GET</option>
            <option value="PUT">PUT</option>
            <option value="DELETE">DELETE</option>
          </select>
          <input id="inputUrl" type="text" placeholder="https://api.example.com/endpoint" class="flex-1 rounded-xl px-4 py-2.5 text-xs font-mono text-slate-100 placeholder-slate-500">
        </div>

        <!-- Interval + Worker Controls -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-950/60 p-4 rounded-xl border border-slate-800/80">
          <div>
            <label class="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">
              İstek Aralığı (Saniye)
            </label>
            <div class="flex items-center gap-2">
              <input id="inputInterval" type="number" step="0.05" min="0.01" value="0.1" class="rounded-lg px-3 py-2 w-28 text-center text-amber-300 font-black text-sm">
              <span class="text-xs text-slate-400">saniye</span>
              <button onclick="saveConfigOnly()" class="ml-auto bg-slate-800 hover:bg-slate-700 text-[11px] font-semibold px-3 py-2 rounded-lg border border-slate-700">Kaydet</button>
            </div>
            <span class="text-[10px] text-emerald-400 mt-1 block">Örnek: 0.1 sn = saniyede 10 istek/worker</span>
          </div>

          <!-- Worker Slider -->
          <div>
            <label class="block text-[11px] font-bold text-purple-400 uppercase tracking-wider mb-1">
              ⚡ Eşzamanlı Worker Sayısı
            </label>
            <div class="flex items-center gap-3">
              <input id="inputWorkers" type="range" min="1" max="50" step="1" value="1"
                oninput="document.getElementById('workerVal').textContent = this.value"
                class="flex-1 accent-purple-500 cursor-pointer h-2">
              <span id="workerVal" class="text-purple-300 font-black text-lg w-8 text-center">1</span>
              <span class="text-xs text-slate-400">w</span>
            </div>
            <div id="workerDots" class="flex flex-wrap gap-0.5 mt-1.5 min-h-[14px]"></div>
            <span class="text-[10px] text-purple-400 mt-1 block">Aktif: <span id="lblActiveWorkers">0</span> worker — Toplam: <span id="lblRps">0</span> req/s</span>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center gap-2">
          <button id="btnStart" onclick="startRunner()" class="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-black py-2.5 rounded-xl text-xs uppercase tracking-wider shadow-lg shadow-emerald-900/30 transition">
            ▶ DÖNGÜYÜ BAŞLAT
          </button>
          <button id="btnStop" onclick="stopRunner()" class="flex-1 bg-rose-600 hover:bg-rose-500 text-white font-black py-2.5 rounded-xl text-xs uppercase tracking-wider shadow-lg shadow-rose-900/30 transition">
            ⏹ DURDUR
          </button>
          <button onclick="sendSingleTest()" title="Döngüye sokmadan sadece 1 kere test et" class="bg-blue-600 hover:bg-blue-500 text-white font-bold px-3 py-2.5 rounded-xl text-xs">
            Tek Sefer
          </button>
        </div>

        <!-- Headers Input -->
        <div>
          <div class="flex justify-between items-center mb-1">
            <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">HTTP Headers (JSON)</label>
            <span class="text-[10px] text-slate-500">Authorization, Content-Type vs.</span>
          </div>
          <textarea id="inputHeaders" rows="4" class="w-full rounded-xl p-3 text-xs font-mono text-emerald-400 resize-y"></textarea>
        </div>

        <!-- Body Input -->
        <div>
          <div class="flex justify-between items-center mb-1">
            <label class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">İstek Gövdesi / POST Body (JSON)</label>
            <span id="lblBodySize" class="text-[11px] font-mono text-amber-400 font-bold"></span>
          </div>
          <textarea id="inputBody" rows="8" class="w-full rounded-xl p-3 text-xs font-mono text-amber-300 resize-y"></textarea>
        </div>

      </div>

      <!-- Right Output & Stats Section -->
      <div class="lg:col-span-5 space-y-4 flex flex-col">

        <!-- Stats Cards -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div class="bg-slate-900/80 p-3 rounded-xl border border-slate-800 text-center">
            <div class="text-[10px] text-slate-400 uppercase font-semibold">Toplam</div>
            <div id="statTotal" class="text-xl font-black text-slate-100 mt-0.5">0</div>
          </div>
          <div class="bg-slate-900/80 p-3 rounded-xl border border-slate-800 text-center">
            <div class="text-[10px] text-slate-400 uppercase font-semibold">Başarılı</div>
            <div id="statSuccess" class="text-xl font-black text-emerald-400 mt-0.5">0</div>
          </div>
          <div class="bg-slate-900/80 p-3 rounded-xl border border-slate-800 text-center">
            <div class="text-[10px] text-slate-400 uppercase font-semibold">Hata</div>
            <div id="statFailed" class="text-xl font-black text-rose-400 mt-0.5">0</div>
          </div>
          <div class="bg-slate-900/80 p-3 rounded-xl border border-slate-800 text-center">
            <div class="text-[10px] text-slate-400 uppercase font-semibold">Gecikme</div>
            <div id="statLatency" class="text-xl font-black text-amber-400 mt-0.5">0 ms</div>
          </div>
        </div>

        <!-- req/s Throughput Bar -->
        <div class="bg-slate-900/80 p-3 rounded-xl border border-purple-900/40">
          <div class="flex justify-between text-[11px] font-bold text-purple-400 mb-1">
            <span>📊 Gerçek Zamanlı Throughput</span>
            <span id="rpsLabel">0 req/s</span>
          </div>
          <div class="w-full bg-slate-800 rounded-full h-3 overflow-hidden">
            <div id="rpsBar" class="h-3 rounded-full bg-gradient-to-r from-purple-600 to-pink-500 transition-all duration-500" style="width:0%"></div>
          </div>
          <div class="flex justify-between text-[10px] text-slate-600 mt-0.5">
            <span>0</span><span>50</span><span>100</span><span>200+</span>
          </div>
        </div>

        <!-- Last Response Preview -->
        <div class="bg-slate-900/80 p-4 rounded-2xl border border-slate-800 flex-1 flex flex-col min-h-[260px]">
          <div class="flex justify-between items-center pb-2 border-b border-slate-800 text-xs">
            <span class="font-bold text-slate-300">Sunucu Yanıtı (Son Gelen Cevap)</span>
            <div class="flex items-center gap-2">
              <span id="lblBytes" class="text-[11px] font-mono text-blue-300">-</span>
              <span id="lblStatus" class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400">STATUS: -</span>
            </div>
          </div>
          <div id="errorBox" class="hidden mt-2 p-2 bg-rose-950/60 border border-rose-800 rounded-lg text-rose-300 text-xs font-mono"></div>
          <pre id="responsePreview" class="mt-3 flex-1 overflow-auto max-h-[300px] bg-slate-950 p-3 rounded-xl text-xs font-mono text-slate-300 whitespace-pre-wrap leading-relaxed select-all">Henüz istek gönderilmedi...</pre>
        </div>

        <!-- History Log Table -->
        <div class="bg-slate-900/80 p-4 rounded-2xl border border-slate-800">
          <div class="text-xs font-bold text-slate-300 mb-2">Son İstek Geçmişi (Log)</div>
          <div class="overflow-y-auto max-h-40">
            <table class="w-full text-[11px] text-left">
              <thead class="text-slate-500 uppercase border-b border-slate-800">
                <tr>
                  <th class="py-1">Saat</th>
                  <th class="py-1">HTTP</th>
                  <th class="py-1">Süre</th>
                  <th class="py-1">Boyut</th>
                </tr>
              </thead>
              <tbody id="historyBody" class="divide-y divide-slate-800/40 text-slate-400 font-mono">
                <tr><td colspan="4" class="py-2 text-center text-slate-600">Geçmiş yok</td></tr>
              </tbody>
            </table>
          </div>
        </div>

      </div>

    </div>
  </div>

  <script>
    let isEditing = false;

    const presets = {
      '7xwon_main': {
        url: 'https://api.7xwon.com/main-events',
        method: 'POST', interval: 0.1,
        headers: {"Content-Type":"application/json","Authorization":"Bearer unlogged","User-Agent":"Mozilla/5.0","Origin":"https://7xwon.com","Referer":"https://7xwon.com/"},
        body: {"type":0,"odds":false,"code":false,"s":1,"t":false}
      },
      '7xwon_login': {
        url: 'https://api.7xwon.com/login',
        method: 'POST', interval: 1.0,
        headers: {"Content-Type":"application/json","Origin":"https://7xwon.com"},
        body: {"username":"test_user","password":"123","device":"web_probe","remember":false}
      },
      '7xwon_countries': {
        url: 'https://api.7xwon.com/countries',
        method: 'POST', interval: 2.0,
        headers: {"Content-Type":"application/json","Origin":"https://7xwon.com"},
        body: {}
      },
      '7xwon_search': {
        url: 'https://api.7xwon.com/search',
        method: 'POST', interval: 1.0,
        headers: {"Content-Type":"application/json","Origin":"https://7xwon.com"},
        body: {"search":"Galatasaray"}
      }
    };

    function loadPreset(key) {
      const p = presets[key];
      if (!p) return;
      document.getElementById('inputUrl').value = p.url;
      document.getElementById('inputMethod').value = p.method;
      document.getElementById('inputInterval').value = p.interval;
      document.getElementById('inputHeaders').value = JSON.stringify(p.headers, null, 2);
      document.getElementById('inputBody').value = JSON.stringify(p.body, null, 2);
      updateBodySize();
      saveConfigOnly();
    }

    async function load2MBPayload() {
      const btn = document.getElementById('btn2MB');
      const orig = btn.innerHTML;
      btn.innerHTML = '⏳ 2 MB YÜKLENİYOR...';
      try {
        const res = await fetch('/api/get-big-payload');
        const text = await res.text();
        document.getElementById('inputBody').value = text;
        document.getElementById('inputInterval').value = 0.1;
        updateBodySize();
        await saveConfigOnly();
        btn.innerHTML = '✅ 2 MB YÜKLENDİ!';
        setTimeout(() => { btn.innerHTML = orig; }, 2000);
      } catch (e) {
        alert("Hata: " + e);
        btn.innerHTML = orig;
      }
    }

    function updateBodySize() {
      const len = document.getElementById('inputBody').value.length;
      document.getElementById('lblBodySize').textContent =
        `Boyut: ${(len/1024).toFixed(1)} KB (${(len/1048576).toFixed(2)} MB)`;
    }
    document.getElementById('inputBody').addEventListener('input', updateBodySize);

    function updateWorkerDots(active, total) {
      const container = document.getElementById('workerDots');
      let html = '';
      for (let i = 0; i < total; i++) {
        const on = i < active;
        html += `<span class="worker-dot" style="background:${on ? '#a855f7' : '#374151'}"></span>`;
      }
      container.innerHTML = html;
    }

    async function fetchState() {
      try {
        const res = await fetch('/api/state');
        const data = await res.json();

        const badge = document.getElementById('runnerStatus');
        const w = data.workers || 1;
        if (data.is_running) {
          badge.textContent = `ÇALIŞIYOR (${data.interval_seconds}s × ${w}w)`;
          badge.className = "px-4 py-1.5 rounded-full text-xs font-bold bg-emerald-950 text-emerald-300 border border-emerald-700 animate-pulse";
        } else {
          badge.textContent = "DURDURULDU";
          badge.className = "px-4 py-1.5 rounded-full text-xs font-bold bg-rose-950 text-rose-300 border border-rose-800";
        }

        if (!isEditing) {
          if (!document.getElementById('inputUrl').value) document.getElementById('inputUrl').value = data.url;
          if (!document.getElementById('inputInterval').value) document.getElementById('inputInterval').value = data.interval_seconds;
          if (!document.getElementById('inputHeaders').value) document.getElementById('inputHeaders').value = data.headers_raw;
          if (!document.getElementById('inputBody').value) { document.getElementById('inputBody').value = data.body_raw; updateBodySize(); }
          if (!document.getElementById('inputMethod').value) document.getElementById('inputMethod').value = data.method;
        }

        document.getElementById('statTotal').textContent = data.total_requests;
        document.getElementById('statSuccess').textContent = data.successful_requests;
        document.getElementById('statFailed').textContent = data.failed_requests;
        document.getElementById('statLatency').textContent = (data.last_latency_ms || 0) + ' ms';

        // RPS
        const rps = data.requests_per_second || 0;
        document.getElementById('rpsCounter').textContent = rps + ' req/s';
        document.getElementById('rpsLabel').textContent = rps + ' req/s';
        document.getElementById('lblRps').textContent = rps;
        const pct = Math.min(100, (rps / 200) * 100);
        document.getElementById('rpsBar').style.width = pct + '%';

        // Worker dots
        const activeW = data.active_workers || 0;
        document.getElementById('lblActiveWorkers').textContent = activeW;
        updateWorkerDots(activeW, w);

        if (data.last_response) {
          try {
            const parsed = JSON.parse(data.last_response);
            document.getElementById('responsePreview').textContent = JSON.stringify(parsed, null, 2);
          } catch(e) {
            document.getElementById('responsePreview').textContent = data.last_response;
          }
        }
        document.getElementById('lblBytes').textContent = data.last_bytes ? (data.last_bytes/1024).toFixed(1) + ' KB' : '-';

        const statusSpan = document.getElementById('lblStatus');
        if (data.last_status_code) {
          statusSpan.textContent = 'STATUS: ' + data.last_status_code;
          statusSpan.className = (data.last_status_code >= 200 && data.last_status_code < 300)
            ? "px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-900 text-emerald-200"
            : "px-2 py-0.5 rounded text-[10px] font-bold bg-rose-900 text-rose-200";
        }

        const errBox = document.getElementById('errorBox');
        if (data.last_error) {
          errBox.textContent = "Hata: " + data.last_error;
          errBox.classList.remove('hidden');
        } else {
          errBox.classList.add('hidden');
        }

        if (data.history && data.history.length > 0) {
          document.getElementById('historyBody').innerHTML = data.history.map(h => `
            <tr>
              <td class="py-1">${h.time}</td>
              <td class="py-1"><span class="${h.success ? 'text-emerald-400' : 'text-rose-400'} font-bold">${h.status}</span></td>
              <td class="py-1 text-amber-300">${h.latency}ms</td>
              <td class="py-1">${(h.bytes/1024).toFixed(1)}KB</td>
            </tr>
          `).join('');
        }

      } catch (err) {
        console.error(err);
      }
    }

    function getPayloadFromUI() {
      return {
        url: document.getElementById('inputUrl').value,
        method: document.getElementById('inputMethod').value,
        interval_seconds: parseFloat(document.getElementById('inputInterval').value) || 0.1,
        headers_raw: document.getElementById('inputHeaders').value,
        body_raw: document.getElementById('inputBody').value,
        workers: parseInt(document.getElementById('inputWorkers').value) || 1
      };
    }

    async function saveConfigOnly() {
      await fetch('/api/update-config', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(getPayloadFromUI())
      });
      fetchState();
    }

    async function startRunner() {
      await fetch('/api/start', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(getPayloadFromUI())
      });
      fetchState();
    }

    async function stopRunner() {
      await fetch('/api/stop', {method:'POST'});
      fetchState();
    }

    async function clearStats() {
      await fetch('/api/clear-stats', {method:'POST'});
      fetchState();
    }

    async function sendSingleTest() {
      const btn = event.target;
      btn.textContent = '...';
      const res = await fetch('/api/send-once', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(getPayloadFromUI())
      });
      const data = await res.json();
      btn.textContent = 'Tek Sefer';
      document.getElementById('lblStatus').textContent = 'STATUS: ' + data.status_code;
      document.getElementById('lblBytes').textContent = (data.bytes/1024).toFixed(1) + ' KB';
      document.getElementById('statLatency').textContent = data.latency_ms + ' ms';
      try {
        document.getElementById('responsePreview').textContent = JSON.stringify(JSON.parse(data.body), null, 2);
      } catch(e) {
        document.getElementById('responsePreview').textContent = data.body;
      }
    }

    // Workers slider: anlık kaydet
    document.getElementById('inputWorkers').addEventListener('change', saveConfigOnly);

    ['inputUrl','inputHeaders','inputBody','inputInterval','inputWorkers'].forEach(id => {
      const el = document.getElementById(id);
      el.addEventListener('focus', () => isEditing = true);
      el.addEventListener('blur', () => isEditing = false);
    });

    setInterval(fetchState, 800);
    fetchState();
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8083))
    uvicorn.run("custom_post_runner:app", host="0.0.0.0", port=port)
