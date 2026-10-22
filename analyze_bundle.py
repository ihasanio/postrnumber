import urllib.request
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

js_url = 'https://7xwon.com/assets/index-VJ2uOccI.js'
print(f"Downloading {js_url}...")
req = urllib.request.Request(js_url, headers=headers)
with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
    data = resp.read().decode('utf-8', errors='ignore')

print(f"Downloaded {len(data)} characters.")
with open('C:/Users/User/Desktop/7xwon_API/index_bundle.js', 'w', encoding='utf-8') as f:
    f.write(data)

# Analyze API routes, URLs, websockets, endpoints
endpoints = set()
for match in re.findall(r'[\'"`](https?://[^\'"`]+)[\'"`]', data):
    endpoints.add(match)

for match in re.findall(r'[\'"`](/api/[^\'"`]+)[\'"`]', data):
    endpoints.add(match)

for match in re.findall(r'[\'"`](wss?://[^\'"`]+)[\'"`]', data):
    endpoints.add(match)

print("\n--- Detected URLs and API Endpoints ---")
for ep in sorted(endpoints):
    print("  ", ep)

# Find BASE_URL or apiUrl
base_urls = re.findall(r'(baseURL|baseUrl|apiUrl|api_url|VITE_[A-Z_]+)\s*[:=]\s*[\'"`]([^\'"`]+)[\'"`]', data, re.IGNORECASE)
print("\n--- Detected Base URLs / Configs ---")
for k, v in base_urls:
    print(f"  {k} = {v}")

# Find axios / fetch paths
api_calls = re.findall(r'\.(get|post|put|delete)\([\'"`]([^\'"`]+)[\'"`]', data, re.IGNORECASE)
print("\n--- Detected HTTP Calls ---")
for method, path in sorted(set(api_calls))[:30]:
    print(f"  {method.upper()} {path}")
