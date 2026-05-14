"""
Post-deployment verification against a live Zabbix instance.

Run manually:
  KERIO_HOSTID=<id> MCP_URL=http://127.0.0.1:8180/mcp \
      pytest tests/test_deployment.py -m live -v

Requires a Zabbix MCP server (https://github.com/MarkFlamenco/zabbix-mcp or
similar) reachable at MCP_URL and the Kerio Connect template linked to the
host whose Zabbix hostid is KERIO_HOSTID.
"""
import json
import os
import re
import urllib.request

import pytest


HOSTID = os.environ.get("KERIO_HOSTID", "")
MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8180/mcp")

if not HOSTID:
    pytest.skip("Set KERIO_HOSTID to enable live deployment tests", allow_module_level=True)


def mcp_call(session_id, tool, arguments):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": {**arguments, "server": "production"}},
    }
    request = urllib.request.Request(
        MCP_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "mcp-session-id": session_id,
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        raw = response.read().decode()
    data_lines = [line[6:] for line in raw.splitlines() if line.startswith("data: ")]
    if not data_lines:
        raise RuntimeError(f"MCP response had no `data:` line:\n{raw}")
    result = json.loads(data_lines[-1])
    if "error" in result:
        raise RuntimeError(f"MCP error: {result['error']}")
    text = result["result"]["content"][0]["text"]
    match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
    if not match:
        raise RuntimeError(f"MCP response had no JSON payload:\n{text}")
    return json.loads(match.group(1))


@pytest.fixture(scope="module")
def mcp_session():
    init = urllib.request.Request(
        MCP_URL,
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            }
        ).encode(),
        headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(init, timeout=10) as response:
        return response.headers.get("mcp-session-id", "")


@pytest.mark.live
def test_master_item_has_recent_value(mcp_session):
    items = mcp_call(
        mcp_session,
        "item_get",
        {"hostids": [HOSTID], "search": {"key_": "kerio.api.master"}, "output": "extend"},
    )
    assert items, "kerio.api.master item not found on host"
    master = items[0]
    assert master["lastvalue"], "kerio.api.master has no value"
    data = json.loads(master["lastvalue"])
    assert "statistics" in data and "services" in data and "license" in data and "server" in data


@pytest.mark.live
def test_disk_item_has_numeric_value(mcp_session):
    items = mcp_call(
        mcp_session,
        "item_get",
        {"hostids": [HOSTID], "filter": {"key_": "kerio.disk.pct"}, "output": "extend"},
    )
    assert items, "kerio.disk.pct not found"
    assert items[0]["lastvalue"] != "", "kerio.disk.pct has no value"
    assert 0 <= float(items[0]["lastvalue"]) <= 100


@pytest.mark.live
def test_no_items_in_error_state(mcp_session):
    items = mcp_call(
        mcp_session,
        "item_get",
        {
            "hostids": [HOSTID],
            "search": {"key_": "kerio."},
            "filter": {"state": 1},
            "output": "extend",
        },
    )
    errors = [(item["key_"], item.get("error", "")) for item in items]
    assert not errors, f"Items in error state: {errors}"


@pytest.mark.live
def test_service_lld_discovered_services(mcp_session):
    rules = mcp_call(
        mcp_session,
        "discoveryrule_get",
        {"hostids": [HOSTID], "filter": {"key_": "kerio.services.discovery"}, "output": "extend"},
    )
    assert rules, "kerio.services.discovery LLD rule not found"
    assert rules[0]["lastvalue"], "Service LLD has not run yet"
    assert len(json.loads(rules[0]["lastvalue"])) > 0


@pytest.mark.live
def test_license_days_remaining(mcp_session):
    items = mcp_call(
        mcp_session,
        "item_get",
        {"hostids": [HOSTID], "filter": {"key_": "kerio.license.days"}, "output": "extend"},
    )
    assert items, "kerio.license.days not found"
    assert items[0]["lastvalue"] != "", "kerio.license.days has no value"
    assert int(items[0]["lastvalue"]) > 0
