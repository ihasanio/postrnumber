import re

with open('C:/Users/User/Desktop/7xwon_API/index_bundle.js', 'r', encoding='utf-8') as f:
    code = f.read()

pos = code.find('2500')
if pos != -1:
    print("Around 2500ms poller:")
    print(code[pos-400:pos+300])

# Let's also search for other intervals or timers like 1000, 3000, 5000, 2e3, 3e3
more_intervals = re.findall(r'setInterval\([^,]+,\s*([^)]+)\)', code)
print("\nAll intervals found:", more_intervals)
