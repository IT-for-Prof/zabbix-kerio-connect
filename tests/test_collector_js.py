"""Script item JS run in node with a stub HttpRequest, composed exactly as Zabbix gets it."""
import calendar
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import sync_template_js  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")

PARAMS = {"host": "kerio", "port": "4040", "scheme": "https", "username": "u", "password": "p"}
LOGIN = {"Session.login": {"token": "t"}}
# 2026-11-25 21:00 UTC = 2026-11-26 00:00 at UTC+3 (timezoneOffset 180, as on the live servers).
NOW = calendar.timegm((2026, 11, 25, 21, 0, 0))
TIME = {"Server.getServerTime": {"info": {"timezoneOffset": 180, "currentTime": NOW}}}


def run(key, spec, tz="UTC", **extra):
    script = Path(f"/tmp/kerio-{key}.js")
    script.write_text(sync_template_js.compose(key))
    proc = subprocess.run(
        ["node", "tests/js_harness.js", str(script), json.dumps({**PARAMS, **extra}), json.dumps({**LOGIN, **spec})],
        capture_output=True, text=True, env={"TZ": tz, "PATH": "/usr/bin:/usr/local/bin:/bin"}, check=True,
    )
    out = json.loads(proc.stdout)
    if "result" in out:
        out["result"] = json.loads(out["result"])
    return out


def test_master_one_batch_request():
    out = run("kerio.api.master", {
        "Statistics.get": {"statistics": {"storage": {"percentage": "91"}}},
        "Services.get": {"services": [{"name": "SMTP", "isRunning": True}]},
        "ProductRegistration.getFullStatus": {"status": {"users": 50}},
        "Server.getVersion": {"version": "10.0.8"},
    })
    assert out["requests"] == ["Session.login", "Batch.run", "Session.logout"]
    assert out["result"]["statistics"]["storage"]["percentage"] == "91"
    assert out["result"]["services"][0]["name"] == "SMTP"
    assert out["result"]["license"] == {"users": 50}
    assert out["result"]["server"]["version"] == "10.0.8"


def test_master_command_error_fails_item_and_logs_out():
    out = run("kerio.api.master", {"Services.get": {"__error": "denied"}})
    assert out["error"] == "Services.get error: denied"
    assert out["requests"][-1] == "Session.logout"


def test_login_error_fails_item():
    out = run("kerio.api.master", {"Session.login": {"__error": "bad password"}})
    assert out["error"] == "Session.login error: bad password"


def test_http_error_fails_item():
    out = run("kerio.api.master", {"__status": 503})
    assert out["error"] == "HTTP 503 on Session.login"


def test_lld_lists_services():
    out = run("kerio.services.discovery", {"Services.get": {"services": [{"name": "IMAP", "howToStart": "Automatic"}]}})
    assert out["result"] == [{"{#SERVICE}": "IMAP", "{#STARTTYPE}": "Automatic"}]


def queue(entries, tz="UTC", stuck_age="1h"):
    return run("kerio.queue.raw", {**TIME, "Queue.get": {"list": entries, "totalItems": len(entries)}}, tz=tz, stuck_age=stuck_age)


def test_queue_empty():
    out = queue([])
    assert out["result"] == {"oldest_age": 0, "stuck": 0, "stuck_domains": 0}
    assert out["requests"] == ["Session.login", "Batch.run", "Session.logout"]


@pytest.mark.parametrize("tz", ["UTC", "America/New_York", "Asia/Tokyo"])
def test_queue_age_uses_server_offset_not_collector_timezone(tz):
    # 22:00 server local = 19:00 UTC, two hours before NOW.
    out = queue([{"creationTime": "2026-11-25 22:00", "status": "4.4.1 Cannot connect to host", "to": "a@dead.example"}], tz=tz)
    assert out["result"] == {"oldest_age": 7200, "stuck": 1, "stuck_domains": 1}


def test_queue_stuck_counts_only_temporary_failures_older_than_threshold():
    out = queue([
        {"creationTime": "2026-11-25 20:00", "status": "4.4.1 Cannot connect to host", "to": "a@one.example"},
        {"creationTime": "2026-11-25 20:30", "status": "4.3.2 450 4.7.1 Please try again later", "to": "b@two.example, c@three.example"},
        {"creationTime": "2026-11-25 21:00", "status": "4.4.1 Cannot connect to host", "to": "d@one.example"},
        {"creationTime": "2026-11-25 20:00", "status": "5.1.1 User unknown", "to": "e@four.example"},
        {"creationTime": "2026-11-25 20:00", "status": "", "to": "f@five.example"},
        {"creationTime": "2026-11-25 23:30", "status": "4.4.1 Cannot connect to host", "to": "g@six.example"},
    ], stuck_age="90m")
    # 23:30 is 30 minutes old: below 90m. 5.x.x and empty status are not temporary failures.
    assert out["result"] == {"oldest_age": 14400, "stuck": 3, "stuck_domains": 3}


def test_queue_output_has_no_addresses():
    out = queue([{"creationTime": "2026-11-25 20:00", "status": "4.4.1", "to": "secret@client.example", "from": "x@y.example"}])
    assert "@" not in json.dumps(out["result"])


def test_queue_bad_threshold_fails_item():
    out = queue([], stuck_age="one hour")
    assert out["error"] == "bad time value: one hour"


DOMAINS = {"Domains.get": {"list": [{"name": "Local.example"}]}}


def recv(when, sender, user=None, to="<a@ext.example>", subject="Hello", service="SMTP", sender_from="<s@ext.example>"):
    fields = [f"Queue-ID: 6b07-1", f"Service: {service}", f"From: {sender_from}", f"To: {to}", "Size: 100", f"Sender-Host: {sender}"]
    if user:
        fields.append(f"User: {user}")
    fields += ["SSL: yes", f"Subject: {subject}", "Msg-Id: <m@ext.example>"]
    return {"content": f"[{when}] Recv: " + ", ".join(fields)}


def relay(lines, lines_limit="5000", allow=""):
    return run("kerio.relay.unauth", {**TIME, **DOMAINS, "Logs.get": lines}, lines=lines_limit, allow=allow)


RECENT = "25/Nov/2026 23:30:00"  # 30 minutes before NOW, server local time


def test_relay_counts_unauthenticated_private_sender_to_external():
    out = relay([recv(RECENT, "172.16.70.1")])
    assert out["result"] == {"count": 1, "truncated": 0}
    assert out["requests"] == ["Session.login", "Batch.run", "Logs.get", "Session.logout"]


@pytest.mark.parametrize("line", [
    recv(RECENT, "172.16.70.1", user="it@local.example"),
    recv(RECENT, "172.16.70.1", to="<b@LOCAL.example>"),
    recv(RECENT, "mail.ext.example"),
    recv(RECENT, "8.8.8.8"),
    recv(RECENT, "127.0.0.1"),
    recv(RECENT, "172.16.70.1", service="WebDAV"),
    recv("25/Nov/2026 22:59:59", "172.16.70.1"),
    {"content": "[25/Nov/2026 23:30:00] Sent: Queue-ID: 6b07-1, Recipient: <a@ext.example>, Result: delivered"},
])
def test_relay_ignores_authenticated_local_public_old_and_other_lines(line):
    assert relay([line])["result"]["count"] == 0


def test_relay_external_if_any_recipient_is_external():
    assert relay([recv(RECENT, "10.1.2.3", to="<a@local.example>, <b@ext.example>")])["result"]["count"] == 1


def test_relay_subject_cannot_fake_authentication():
    line = recv(RECENT, "192.168.1.5", subject="x, Size: 1, Sender-Host: 8.8.8.8, User: boss, SSL: yes")
    assert relay([line])["result"]["count"] == 1


def test_relay_allow_regex_skips_named_host():
    assert relay([recv(RECENT, "172.16.70.30")], allow=r"^172\.16\.70\.30$")["result"]["count"] == 0


def test_relay_truncated_when_tail_shorter_than_hour():
    lines = [recv("25/Nov/2026 23:50:00", "8.8.8.8") for _ in range(3)]
    assert relay(lines, lines_limit="2")["result"] == {"count": 0, "truncated": 1}
    assert relay(lines, lines_limit="5")["result"]["truncated"] == 0


def test_sources_are_es5_for_duktape():
    for path in Path("src").glob("*.js"):
        text = re.sub(r"//.*", "", path.read_text())
        for token in (r"\blet\b", r"\bconst\b", r"=>", "`", r"\.includes\("):
            assert not re.search(token, text), f"{path}: {token} is not ES5"
