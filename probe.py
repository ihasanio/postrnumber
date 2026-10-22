import urllib.request
import ssl
import json
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7'
}

url = 'https://7xwon.com/'
print(f"Requesting {url}...")
try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        final_url = resp.geturl()
        status = resp.status
        html = resp.read().decode('utf-8', errors='ignore')
        print(f"Status: {status}")
        print(f"Final URL: {final_url}")
        print(f"Response Length: {len(html)}")
        
        # Look for script tags, API endpoints, frameworks
        scripts = re.findall(r'<script[^>]*src=[\'"]([^\'"]+)[\'"]', html, re.IGNORECASE)
        print("\nScripts found:")
        for s in scripts[:15]:
            print("  ", s)
            
        # Check titles, meta tags
        title = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        if title:
            print("\nTitle:", title.group(1))
            
        # Look for keywords
        keywords = ['bet', 'sports', 'live', 'api', 'token', 'auth', 'sport']
        for kw in keywords:
            matches = len(re.findall(kw, html, re.IGNORECASE))
            print(f"Keyword '{kw}': {matches} occurrences")
            
        with open('C:/Users/User/Desktop/7xwon_API/index_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("\nSaved index_page.html to Desktop/7xwon_API/")

except Exception as e:
    print(f"Error fetching {url}: {e}")
