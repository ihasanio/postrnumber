import re

with open('C:/Users/User/Desktop/7xwon_API/index_bundle.js', 'r', encoding='utf-8') as f:
    code = f.read()

# Let's search for "main-events" in code
pos = code.find('ye("main-events"')
if pos != -1:
    print("Found 'main-events' at pos:", pos)
    print(code[max(0, pos-300):min(len(code), pos+500)])
else:
    # search where main-events is mentioned
    matches = [m.start() for m in re.finditer(r'main-events', code)]
    for p in matches:
        print(f"Match at {p}:")
        print(code[max(0, p-200):min(len(code), p+300)])
