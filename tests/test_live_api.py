"""
Live API discovery - run manually:
  python3 tests/test_live_api.py <kerio-host> 4040 <user> <password>

This probes Kerio Connect API method availability and response shapes.
"""
import json
import ssl
import sys
import urllib.request


def call(url, method, params=None, token=None, cookie=None):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params:
        payload["params"] = params
    if token:
        payload["token"] = token
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    if cookie:
        req.add_header("Cookie", cookie)
    if token:
        req.add_header("X-Token", token)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        cookie_out = None
        raw = resp.headers.get("Set-Cookie", "")
        if raw:
            cookie_out = raw.split(";")[0]
        return json.loads(resp.read().decode()), cookie_out


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python3 test_live_api.py <host> <port> <user> <password>")
        sys.exit(1)

    host, port, user, password = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    url = f"https://{host}:{port}/admin/api/jsonrpc/"
    print(f"\n=== {url} ===")

    resp, cookie = call(
        url,
        "Session.login",
        {
            "userName": user,
            "password": password,
            "application": {"name": "zabbix-probe", "vendor": "test", "version": "1"},
        },
    )
    assert "result" in resp, f"Login failed: {resp}"
    token = resp["result"]["token"]
    print(f"Login OK  token={token[:16]}...")

    candidates = [
        ("Statistics.get", None),
        ("Services.get", None),
        ("ProductRegistration.getFullStatus", None),
        ("Server.getVersion", None),
        ("SystemHealth.get", None),
        ("ProductRegistration.get", None),
        ("Domains.get", None),
    ]
    found = {}
    for method, params in candidates:
        try:
            result, _ = call(url, method, params, token=token, cookie=cookie)
            if "result" in result:
                found[method] = result["result"]
                print(f"  OK  {method}")
            else:
                print(f"  ERR {method}  {result.get('error', {}).get('message', '?')}")
        except Exception as exc:
            print(f"  ERR {method}  {exc}")

    print("\n=== Response shapes (first 1200 chars each) ===")
    for method, result in found.items():
        print(f"\n--- {method} ---")
        print(json.dumps(result, indent=2)[:1200])

    call(url, "Session.logout", token=token, cookie=cookie)
    print("\nLogout OK")
