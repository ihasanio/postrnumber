import re

with open('C:/Users/User/Desktop/7xwon_API/index_bundle.js', 'r', encoding='utf-8') as f:
    code = f.read()

# Let's search where setInterval or setTimeout is used with ye or tc
intervals = []
for m in re.finditer(r'setInterval\(([^,]+),\s*(\d+)\)', code):
    fn_body = m.group(1)
    ms = m.group(2)
    start = max(0, m.start() - 150)
    end = min(len(code), m.end() + 150)
    intervals.append((int(ms), code[start:end]))

print(f"Total setInterval found: {len(intervals)}")
for ms, snippet in sorted(intervals, key=lambda x: x[0]):
    print(f"\n--- Interval: {ms}ms ({ms/1000}s) ---")
    print(snippet.replace('\n', ' '))
