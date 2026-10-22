import json, random, string, os

def random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Aim for approx 2 MB (2_048_000 bytes)
# Each element ~200 chars, we'll create 10000 elements => ~2 MB
payload = {
    "type": 0,
    "odds": False,
    "code": False,
    "s": 1,
    "t": False,
    "big_data": [random_string(200) for _ in range(10000)]
}

output_path = os.path.join('C:/Users/User/Desktop/7xwon_API', 'big_payload.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(payload, f, ensure_ascii=False)
print(f"2 MB payload created at {output_path}, size: {os.path.getsize(output_path)} bytes")
