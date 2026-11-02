import asyncio
import os
import sys
import webbrowser

# Dizin ekle
api_dir = r"C:\Users\User\Desktop\7xwon_API"
sys.path.insert(0, api_dir)

from webapp import app

if __name__ == "__main__":
    port = 8080
    url = f"http://127.0.0.1:{port}"
    print(f"[*] 7xwon Cloudflare Bypass Load Tester Baslatiliyor: {url}")
    webbrowser.open(url)
    app.run(host="127.0.0.1", port=port, debug=False)
