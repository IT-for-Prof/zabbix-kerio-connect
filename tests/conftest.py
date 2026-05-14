import json
from unittest.mock import MagicMock

import pytest


SAMPLE_LOGIN_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {"token": "testtoken123"},
}

SAMPLE_STATS_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 2,
    "result": {
        "statistics": {
            "start": 1754246600,
            "uptime": {"days": 1, "hours": 2, "minutes": 34},
            "storage": {
                "total": {"value": 716796, "units": "MegaBytes"},
                "occupied": {"value": 666175, "units": "MegaBytes"},
                "percentage": "92",
            },
            "received": {
                "count": "617376",
                "volume": {"value": 119600, "units": "MegaBytes"},
                "recipients": "4380038",
            },
            "storedInQueue": {
                "count": "0",
                "volume": {"value": 0, "units": "Bytes"},
                "recipients": "0",
            },
            "transmitted": {
                "count": "319307",
                "volume": {"value": 135228, "units": "MegaBytes"},
                "recipients": "394693",
            },
            "failures": {
                "transientFailures": "43440208",
                "permanentFailures": "4009847",
            },
            "antivirus": {
                "checkedAttachments": "579391",
                "foundViruses": "147",
                "prohibitedTypes": "2",
            },
            "spam": {
                "checked": "91714",
                "tagged": "4072",
                "rejected": "10895",
                "markedAsSpam": "1693",
                "markedAsNotSpam": "172",
            },
            "smtpServer": {
                "totalIncomingConnections": "1506226",
                "lostConnections": "297216",
                "authenticationFailures": "334700",
                "rejectedByBlacklist": "23589",
                "acceptedMessages": "257871",
            },
            "smtpClient": {"connectionAttempts": "12712121", "dnsFailures": "232500"},
            "imapServer": {
                "totalIncomingConnections": "320268",
                "authenticationFailures": "9491",
            },
            "pop3Server": {"totalIncomingConnections": "1", "authenticationFailures": "0"},
            "ldapServer": {"totalIncomingConnections": "1", "authenticationFailures": "0"},
            "webServer": {"totalIncomingConnections": "14695683"},
            "xmppServer": {"totalIncomingConnections": "0", "authenticationFailures": "0"},
            "antibombing": {
                "rejectedConnections": "0",
                "rejectedMessages": "0",
                "rejectedHarvestAttacks": "159",
            },
            "greylisting": {
                "messagesAccepted": "79688",
                "messagesDelayed": "2345",
                "messagesSkipped": "324",
            },
        }
    },
}

SAMPLE_SERVICES_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 5,
    "result": {
        "services": [
            {"id": "keriodb://service/aaa", "name": "SMTP", "isRunning": True, "defaultPort": 25},
            {"id": "keriodb://service/bbb", "name": "Secure SMTP", "isRunning": True, "defaultPort": 465},
            {"id": "keriodb://service/ccc", "name": "IMAP", "isRunning": True, "defaultPort": 143},
            {"id": "keriodb://service/ddd", "name": "Secure IMAP", "isRunning": True, "defaultPort": 993},
            {"id": "keriodb://service/eee", "name": "POP3", "isRunning": False, "defaultPort": 110},
            {"id": "keriodb://service/fff", "name": "Secure POP3", "isRunning": True, "defaultPort": 995},
            {"id": "keriodb://service/ggg", "name": "Secure HTTP", "isRunning": True, "defaultPort": 443},
            {"id": "keriodb://service/hhh", "name": "XMPP", "isRunning": False, "defaultPort": 5222},
        ],
    },
}

SAMPLE_LICENSE_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 6,
    "result": {
        "status": {
            "regType": "rsProductRegistered",
            "Id": "REDACTED-LICENSE-ID",
            "company": "Kerio Connect User",
            "users": 5000,
            "expirations": [
                {"type": "License", "isUnlimited": False, "remainingDays": 1653, "date": 1921449599},
                {"type": "Subscription", "isUnlimited": False, "remainingDays": 1653, "date": 1921449599},
            ],
        }
    },
}

SAMPLE_SERVER_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 7,
    "result": {
        "product": "Kerio Connect",
        "version": "10.0.8.9228",
        "major": 10,
        "minor": 0,
        "revision": 8,
        "build": 9228,
    },
}

SAMPLE_LOGOUT_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 8,
    "result": {"redirectUrl": "https://host:4040/admin/login"},
}

API_RESPONSES = {
    "Session.login": SAMPLE_LOGIN_RESPONSE,
    "Statistics.get": SAMPLE_STATS_RESPONSE,
    "Services.get": SAMPLE_SERVICES_RESPONSE,
    "ProductRegistration.getFullStatus": SAMPLE_LICENSE_RESPONSE,
    "Server.getVersion": SAMPLE_SERVER_RESPONSE,
    "Session.logout": SAMPLE_LOGOUT_RESPONSE,
}


class _FakeHeaders:
    def __init__(self, cookie=None):
        self._headers = {}
        if cookie:
            self._headers["Set-Cookie"] = f"{cookie}; path=/; HttpOnly"

    def get(self, key, default=None):
        return self._headers.get(key, default)

    def __contains__(self, key):
        return key in self._headers

    def __getitem__(self, key):
        return self._headers[key]


class FakeHttp:
    def __init__(self):
        self._responses = {}
        self._errors = {}
        self.calls = []
        self.bodies = {}
        self.last_url = ""

    def set_response(self, method: str, body: dict, cookie: str = None):
        self._responses[method] = (body, cookie)

    def set_error(self, method: str, exc: Exception):
        self._errors[method] = exc

    def was_called(self, method: str) -> bool:
        return method in self.calls

    def last_body(self, method: str) -> dict:
        return self.bodies[method]

    def urlopen(self, req, context=None, timeout=None):
        self.last_url = req.full_url
        body = json.loads(req.data.decode())
        method = body["method"]
        self.calls.append(method)
        self.bodies[method] = body

        if method in self._errors:
            raise self._errors[method]
        if method not in self._responses:
            raise AssertionError(f"FakeHttp: no mock configured for method '{method}'")

        resp_body, cookie = self._responses[method]
        mock = MagicMock()
        mock.read.return_value = json.dumps(resp_body).encode()
        mock.headers = _FakeHeaders(cookie)
        mock.__enter__.return_value = mock
        mock.__exit__.return_value = False
        return mock


@pytest.fixture
def fake_http(monkeypatch):
    tracker = FakeHttp()
    import kerio_collector

    monkeypatch.setattr(kerio_collector.urllib.request, "urlopen", tracker.urlopen)
    return tracker


@pytest.fixture
def all_responses(fake_http):
    for method, body in API_RESPONSES.items():
        fake_http.set_response(
            method,
            body,
            cookie="SESSION_CONNECT_WEBADMIN=abc123" if method == "Session.login" else None,
        )
    return fake_http
