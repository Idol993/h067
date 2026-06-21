import urllib.request
import urllib.error
import json

print("=== Test 1: Redirect (should 302) ===")
try:
    req = urllib.request.Request('http://localhost:8000/mygoogle')
    resp = urllib.request.urlopen(req)
    print(f"Final URL: {resp.url}")
    print(f"Status: {resp.status}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(f"Headers: {dict(e.headers)}")

print("\n=== Test 2: Non-existent short code (should 404) ===")
try:
    req = urllib.request.Request('http://localhost:8000/nonexistent123')
    resp = urllib.request.urlopen(req)
    print(f"Unexpected success: {resp.status}")
except urllib.error.HTTPError as e:
    print(f"Status: {e.code}")

print("\n=== Test 3: Admin API - list links (without API key - should fail) ===")
try:
    req = urllib.request.Request('http://localhost:8000/admin/links')
    resp = urllib.request.urlopen(req)
    print(f"Unexpected success: {resp.status}")
except urllib.error.HTTPError as e:
    print(f"Status: {e.code}")
    print(f"Detail: {e.read().decode()}")

print("\n=== Test 4: Admin API - list links (with API key) ===")
try:
    req = urllib.request.Request(
        'http://localhost:8000/admin/links',
        headers={'X-API-Key': 'admin-key-123'}
    )
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read().decode())
    print(f"Status: {resp.status}")
    print(f"Links count: {len(data)}")
    for link in data[:3]:
        print(f"  - {link['short_code']}: {link['original_url']}")
except urllib.error.HTTPError as e:
    print(f"Status: {e.code}")
    print(f"Detail: {e.read().decode()}")

print("\n=== Test 5: Admin stats summary ===")
try:
    req = urllib.request.Request(
        'http://localhost:8000/admin/stats/summary',
        headers={'X-API-Key': 'admin-key-123'}
    )
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read().decode())
    print(f"Status: {resp.status}")
    print(json.dumps(data, indent=2))
except urllib.error.HTTPError as e:
    print(f"Status: {e.code}")
    print(f"Detail: {e.read().decode()}")

print("\n=== Test 6: Link with password ===")
data = json.dumps({
    'url': 'https://example.com/secret',
    'custom_code': 'myprivatelink',
    'password': 'mypassword123'
}).encode('utf-8')
req = urllib.request.Request(
    'http://localhost:8000/links',
    data=data,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
resp = urllib.request.urlopen(req)
result = json.loads(resp.read().decode())
print(f"Created password-protected link: {result['short_code']}")
print(f"Has password: {result['has_password']}")

print("\n=== Test 7: Batch stats ===")
try:
    req = urllib.request.Request(
        'http://localhost:8000/stats/batch?codes=mygoogle,secretlink,nope'
    )
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read().decode())
    print(f"Status: {resp.status}")
    print(f"Number of results: {len(data['results'])}")
    for code, stats in data['results'].items():
        print(f"  {code}: {stats['total_visits']} visits")
except urllib.error.HTTPError as e:
    print(f"Status: {e.code}")
    print(f"Detail: {e.read().decode()}")

print("\n=== All tests completed! ===")
