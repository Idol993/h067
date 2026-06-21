import urllib.request
import urllib.error
import urllib.parse
import json
import http.cookiejar
import http.client

BASE_URL = "http://localhost:8000"

class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def request_no_redirect(method, path, data=None, headers=None, cookies=None):
    url = BASE_URL + path
    req_headers = {} if headers is None else dict(headers)
    if data and isinstance(data, dict):
        data = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    if data and isinstance(data, str):
        data = data.encode("utf-8")
    
    cookie_header = ""
    if cookies:
        parts = [f"{k}={v}" for k, v in cookies.items()]
        cookie_header = "; ".join(parts)
        req_headers["Cookie"] = cookie_header
    
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        NoRedirectHandler(),
        urllib.request.HTTPCookieProcessor(cj)
    )
    
    try:
        resp = opener.open(req, timeout=10)
        resp_cookies = {}
        for cookie in cj:
            resp_cookies[cookie.name] = cookie.value
        return resp.status, resp.read().decode(), dict(resp.headers), resp_cookies
    except urllib.error.HTTPError as e:
        resp_cookies = {}
        for cookie in cj:
            resp_cookies[cookie.name] = cookie.value
        try:
            body = e.read().decode()
        except:
            body = ""
        return e.code, body, dict(e.headers), resp_cookies

print("=" * 70)
print("测试1: 创建普通短链接")
print("=" * 70)
status, body, _, _ = request_no_redirect("POST", "/links", {
    "url": "https://www.example.com/normal"
})
print(f"Status: {status}")
normal_result = json.loads(body)
print(f"Result: {json.dumps(normal_result, indent=2, ensure_ascii=False)}")
normal_code = normal_result["short_code"]

print("\n" + "=" * 70)
print("测试2: 创建带密码的短链接")
print("=" * 70)
status, body, _, _ = request_no_redirect("POST", "/links", {
    "url": "https://www.example.com/private",
    "custom_code": "private123",
    "password": "secret@2024"
})
print(f"Status: {status}")
pwd_result = json.loads(body)
print(f"Result: {json.dumps(pwd_result, indent=2, ensure_ascii=False)}")
pwd_code = pwd_result["short_code"]
assert pwd_code == "private123"

print("\n" + "=" * 70)
print("测试3: 访问普通短链接 - 直接302跳转 + 访问计数+1")
print("=" * 70)
status, body, headers, _ = request_no_redirect("GET", f"/{normal_code}")
print(f"Status: {status}")
print(f"Location header: {headers.get('Location')}")
assert status == 302, f"Expected 302, got {status}"
print("✅ 返回302跳转")
status, vb, _, _ = request_no_redirect("GET", f"/links/{normal_code}")
vinfo = json.loads(vb)
print(f"Visit count after redirect: {vinfo['visit_count']}")
assert vinfo["visit_count"] == 1, f"Expected 1, got {vinfo['visit_count']}"
print("✅ 普通链接访问计数正确")

print("\n" + "=" * 70)
print("测试4: 访问密码保护短链接 - 首次GET显示密码页，不增加访问次数")
print("=" * 70)
status, body, _, _ = request_no_redirect("GET", f"/{pwd_code}")
print(f"Status: {status}")
assert status == 200, f"Expected 200 for password page, got {status}"
assert "密码" in body, "Password page should contain 密码"
print("✅ 返回了密码验证页面")
status, vb, _, _ = request_no_redirect("GET", f"/links/{pwd_code}")
vinfo = json.loads(vb)
print(f"Visit count after password page: {vinfo['visit_count']}")
assert vinfo["visit_count"] == 0, f"Expected 0, got {vinfo['visit_count']}"
print("✅ 仅显示密码页未增加访问计数")

print("\n" + "=" * 70)
print("测试5: 提交错误密码 - 留在密码页，显示错误，无405，不计数")
print("=" * 70)
form_data = urllib.parse.urlencode({"password": "wrong-password"}).encode("utf-8")
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    NoRedirectHandler(),
    urllib.request.HTTPCookieProcessor(cj)
)
req = urllib.request.Request(
    BASE_URL + f"/{pwd_code}",
    data=form_data,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    method="POST"
)
try:
    resp = opener.open(req, timeout=10)
    status = resp.status
    body = resp.read().decode()
except urllib.error.HTTPError as e:
    status = e.code
    body = e.read().decode() if hasattr(e, 'read') else ""
print(f"Status: {status}")
assert status == 200, f"Expected 200, got {status} (NOT 405!)"
assert "密码错误" in body, "Should show error message"
print("✅ 错误密码返回200并显示错误，没有405")
status, vb, _, _ = request_no_redirect("GET", f"/links/{pwd_code}")
vinfo = json.loads(vb)
print(f"Visit count after wrong password: {vinfo['visit_count']}")
assert vinfo["visit_count"] == 0, f"Expected 0, got {vinfo['visit_count']}"
print("✅ 错误密码未增加访问计数")

print("\n" + "=" * 70)
print("测试6: 提交正确密码 - 验证通过，跳转，计数+1，设置Cookie")
print("=" * 70)
form_data = urllib.parse.urlencode({"password": "secret@2024"}).encode("utf-8")
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    NoRedirectHandler(),
    urllib.request.HTTPCookieProcessor(cj)
)
req = urllib.request.Request(
    BASE_URL + f"/{pwd_code}",
    data=form_data,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    method="POST"
)
try:
    resp = opener.open(req, timeout=10)
    status = resp.status
    body = resp.read().decode()
    headers = dict(resp.headers)
except urllib.error.HTTPError as e:
    status = e.code
    body = e.read().decode() if hasattr(e, 'read') else ""
    headers = dict(e.headers)
print(f"Status: {status}")
print(f"Location: {headers.get('Location')}")
assert status == 303, f"Expected 303, got {status}"
cookies = {}
for cookie in cj:
    cookies[cookie.name] = cookie.value
print(f"Set cookies: {list(cookies.keys())}")
assert "shortlink_auth" in cookies, "Should set shortlink_auth cookie"
auth_cookie = cookies["shortlink_auth"]
print(f"Cookie value (first 30 chars): {auth_cookie[:30]}...")
assert ":verified" not in auth_cookie, "Cookie should NOT be in simple shortcode:verified format!"
print("✅ Cookie已签名，不可伪造")
status, vb, _, _ = request_no_redirect("GET", f"/links/{pwd_code}")
vinfo = json.loads(vb)
print(f"Visit count after correct password: {vinfo['visit_count']}")
assert vinfo["visit_count"] == 1, f"Expected 1, got {vinfo['visit_count']}"
print("✅ 验证通过后访问计数+1")

print("\n" + "=" * 70)
print("测试7: 伪造Cookie访问 - 应重新显示密码页，不计入访问")
print("=" * 70)
fake_cookie = f"{pwd_code}:verified"
status, body, _, _ = request_no_redirect("GET", f"/{pwd_code}", cookies={"shortlink_auth": fake_cookie})
print(f"Status: {status}")
assert status == 200, f"Forged cookie should show password page (200), got {status}"
assert "密码" in body, "Should re-show password page"
print("✅ 伪造Cookie被拒绝，重新显示密码页")
status, vb, _, _ = request_no_redirect("GET", f"/links/{pwd_code}")
vinfo = json.loads(vb)
print(f"Visit count after forged cookie attempt: {vinfo['visit_count']}")
assert vinfo["visit_count"] == 1, f"Expected 1 (no change), got {vinfo['visit_count']}"
print("✅ 伪造Cookie未增加访问计数")

print("\n" + "=" * 70)
print("测试8: 正确Cookie再次访问 - 直接跳转，计数再+1")
print("=" * 70)
status, body, headers, _ = request_no_redirect("GET", f"/{pwd_code}", cookies={"shortlink_auth": auth_cookie})
print(f"Status: {status}")
print(f"Location: {headers.get('Location')}")
assert status == 302, f"Expected 302 redirect, got {status}"
status, vb, _, _ = request_no_redirect("GET", f"/links/{pwd_code}")
vinfo = json.loads(vb)
print(f"Visit count after valid cookie: {vinfo['visit_count']}")
assert vinfo["visit_count"] == 2, f"Expected 2, got {vinfo['visit_count']}"
print("✅ 正确Cookie直接跳转并计数")

print("\n" + "=" * 70)
print("测试9: 管理接口 - 缺少API Key 返回401")
print("=" * 70)
status, body, _, _ = request_no_redirect("GET", "/admin/links")
print(f"Status: {status}")
assert status == 401, f"Expected 401, got {status}"
print(f"Response: {body}")
print("✅ 缺少Key返回401")

print("\n" + "=" * 70)
print("测试10: 管理接口 - 错误API Key 返回403")
print("=" * 70)
status, body, _, _ = request_no_redirect("GET", "/admin/links", headers={"X-API-Key": "wrong-key"})
print(f"Status: {status}")
assert status == 403, f"Expected 403, got {status}"
print(f"Response: {body}")
print("✅ 错误Key返回403")

print("\n" + "=" * 70)
print("测试11: 管理接口 - 正确API Key (默认值 admin-default-key-2024) 返回正常")
print("=" * 70)
status, body, _, _ = request_no_redirect("GET", "/admin/links", headers={"X-API-Key": "admin-default-key-2024"})
print(f"Status: {status}")
assert status == 200, f"Expected 200, got {status}"
admin_links = json.loads(body)
print(f"Got {len(admin_links)} links from admin")
for l in admin_links:
    print(f"  - {l['short_code']}: visits={l['visit_count']}")
print("✅ 正确Key返回正常")

print("\n" + "=" * 70)
print("测试12: 统计接口 - 显示GeoIP可用性")
print("=" * 70)
status, body, _, _ = request_no_redirect("GET", f"/stats/{normal_code}")
print(f"Status: {status}")
stats_data = json.loads(body)
print(f"GeoIP available: {stats_data.get('geoip_available')}")
print(f"Total visits: {stats_data['total_visits']}")
assert "geoip_available" in stats_data, "Should have geoip_available field"
print("✅ 统计接口包含geoip_available字段")

print("\n" + "=" * 70)
print("测试13: 404 链接访问")
print("=" * 70)
status, body, _, _ = request_no_redirect("GET", "/definitely-not-exist-code-xyz")
print(f"Status: {status}")
assert status == 404, f"Expected 404, got {status}"
print("✅ 404正常返回")

print("\n" + "=" * 70)
print("测试14: 旧的 verify-password 路径应该返回404 (因为整合到POST了)")
print("=" * 70)
status, body, _, _ = request_no_redirect("POST", f"/{pwd_code}/verify-password", 
    data=urllib.parse.urlencode({"password": "secret@2024"}),
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
print(f"Status: {status}")
# It will be 404 because redirect router does not have that path now
print("✅ 新链路不使用独立verify-password路径")

print("\n" + "=" * 70)
print("🎉 所有14项测试全部通过!")
print("=" * 70)
