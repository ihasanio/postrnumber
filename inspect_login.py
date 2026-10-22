import re

with open('C:/Users/User/Desktop/7xwon_API/index_bundle.js', 'r', encoding='utf-8') as f:
    code = f.read()

# Let's search for "login" form submission
pos = code.find('ye("login"')
if pos != -1:
    print("--- LOGIN CODE ---")
    print(code[max(0, pos-400):min(len(code), pos+300)])

# Find where device is generated: IU()
pos_iu = code.find('function IU()')
if pos_iu == -1:
    # search IU=
    matches = [m.start() for m in re.finditer(r'IU\s*=\s*', code)]
    for m in matches:
        print("--- IU DEFINITION ---")
        print(code[m-50:m+250])
else:
    print("--- IU FUNCTION ---")
    print(code[pos_iu-50:pos_iu+250])
