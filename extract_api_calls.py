import re

with open('C:/Users/User/Desktop/7xwon_API/index_bundle.js', 'r', encoding='utf-8') as f:
    code = f.read()

# BC is the base fetch wrapper function!
# ye = POST wrapper: ye(path, body, options)
# tc = GET wrapper: tc(path, options)
# Let's inspect the definition of BC
pos = 261593
print("--- BC DEFINITION ---")
print(code[pos-400:pos+300])

print("\n--- Calls to ye( and tc( ---")
# Let's find calls to ye("...", ...) or tc("...", ...)
ye_calls = re.findall(r'ye\([\'"`]([^\'"`]+)[\'"`]', code)
tc_calls = re.findall(r'tc\([\'"`]([^\'"`]+)[\'"`]', code)

# Also template strings: ye(`...`, ...) or tc(`...`, ...)
ye_tmpl = re.findall(r'ye\(`([^`]+)`', code)
tc_tmpl = re.findall(r'tc\(`([^`]+)`', code)

print("POST endpoints (ye):")
for ep in sorted(set(ye_calls + ye_tmpl)):
    print("  POST", ep)

print("\nGET endpoints (tc):")
for ep in sorted(set(tc_calls + tc_tmpl)):
    print("  GET", ep)

# Also check any other fetch or HTTP calls or function names near ye / tc
