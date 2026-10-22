import re

with open('C:/Users/User/Desktop/7xwon_API/index_bundle.js', 'r', encoding='utf-8') as f:
    code = f.read()

for interval_val in ['2e3', '3e3', '4e3', '3e4']:
    print(f"=== INTERVAL {interval_val} ===")
    matches = [m.start() for m in re.finditer(rf'setInterval\([^,]+,\s*{interval_val}\)', code)]
    for pos in matches:
        print(code[max(0, pos-200):min(len(code), pos+200)])
        print("-" * 50)
