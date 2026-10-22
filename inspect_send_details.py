import re

with open('C:/Users/User/Desktop/7xwon_API/index_bundle.js', 'r', encoding='utf-8') as f:
    code = f.read()

# Let's inspect where runner name is mapped or where 'send' is called
send_matches = [m.start() for m in re.finditer(r'ye\("send"', code)]
for idx, pos in enumerate(send_matches):
    print(f"--- SEND MATCH #{idx+1} ---")
    print(code[max(0, pos-250):min(len(code), pos+350)])
    print("=" * 60)
