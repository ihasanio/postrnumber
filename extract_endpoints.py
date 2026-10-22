import re

with open('C:/Users/User/Desktop/7xwon_API/index_bundle.js', 'r', encoding='utf-8') as f:
    code = f.read()

# Let's search around VITE_GENERAL_API_URL or axios creation
matches = [m.start() for m in re.finditer(r'api\.7xwon\.com', code)]
for pos in matches:
    start = max(0, pos - 200)
    end = min(len(code), pos + 300)
    print("--- MATCH AT ---", pos)
    print(code[start:end])
    print()

# Let's search for endpoint patterns like url: "...", path: "...", "/auth", "/login", "/sports", "/match", "/coupon"
# Also search for axios.create or request callers
print("--- AXIOS / FETCH INSTANCES ---")
for m in re.finditer(r'axios\.create\(\{([^\}]+)\}', code):
    print(m.group(0))

print("\n--- API PATHS (quotes starting with / or word) ---")
found_paths = set()
for m in re.finditer(r'[\'"`](/api/[^\'"`]+|/auth/[^\'"`]+|/v1/[^\'"`]+|/user/[^\'"`]+|/sport[^\'"`]+|/bet[^\'"`]+|/live[^\'"`]+)[\'"`]', code):
    found_paths.add(m.group(1))

for p in sorted(found_paths):
    print(" ", p)
