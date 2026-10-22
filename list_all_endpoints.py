import re

with open('C:/Users/User/Desktop/7xwon_API/index_bundle.js', 'r', encoding='utf-8') as f:
    code = f.read()

# Find all occurrences of ye( and tc( and fetch(
ye_all = re.findall(r'ye\([\'"`]([^\'"`]+)[\'"`]', code)
tc_all = re.findall(r'tc\([\'"`]([^\'"`]+)[\'"`]', code)

print("Unique POST endpoints (ye):", len(set(ye_all)))
for ep in sorted(set(ye_all)):
    # count how many times it's called
    cnt = len(re.findall(rf'ye\([\'"`]{re.escape(ep)}[\'"`]', code))
    print(f"  POST {ep:<25} (called {cnt} times)")

print("\nUnique GET endpoints (tc):", len(set(tc_all)))
for ep in sorted(set(tc_all)):
    cnt = len(re.findall(rf'tc\([\'"`]{re.escape(ep)}[\'"`]', code))
    print(f"  GET  {ep:<25} (called {cnt} times)")
