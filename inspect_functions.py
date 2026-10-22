import re

with open('C:/Users/User/Desktop/7xwon_API/index_bundle.js', 'r', encoding='utf-8') as f:
    code = f.read()

keywords = ['login', 'bets', 'cancel', 'event', 'oddstypes', 'send']
for kw in keywords:
    print(f"==================== KEYWORD: {kw} ====================")
    for m in re.finditer(rf'ye\([\'"`]{kw}[\'"`]', code):
        start = max(0, m.start() - 100)
        end = min(len(code), m.end() + 300)
        print("MATCH:", code[start:end])
        print("-" * 50)
