import json

# Read your firebase-key.json
with open('gulmohur-service-account.json', 'r') as f:
    data = json.load(f)

# Write as compact single-line JSON
with open('firebase-key-oneline.txt', 'w') as f:
    json.dump(data, f, separators=(',', ':'))

print("✅ Created firebase-key-oneline.txt")
print("\n📋 First 200 characters:")
with open('firebase-key-oneline.txt', 'r') as f:
    content = f.read()
    print(content[:200])
print("\n📏 Total length:", len(content))