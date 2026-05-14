import json
import os
import socket
import subprocess
import sys
import urllib.error

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kerio_collector import KerioClient, collect_all, discover_services, load_config


class TestKerioClient:
    def test_login_stores_token_and_cookie(self, fake_http):
        fake_http.set_response(
            "Session.login",
            {"jsonrpc": "2.0", "id": 1, "result": {"token": "tok123"}},
            cookie="SESSION_CONNECT_WEBADMIN=abc",
        )
        client = KerioClient("host", 4040, "admin", "pass")
        client.login()
        assert client.token == "tok123"
        assert client.cookie == "SESSION_CONNECT_WEBADMIN=abc"

    def test_login_raises_on_api_error(self, fake_http):
        fake_http.set_response(
            "Session.login",
            {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32001, "message": "Invalid credentials"},
            },
        )
        client = KerioClient("host", 4040, "admin", "bad")
        with pytest.raises(RuntimeError, match="Invalid credentials"):
            client.login()

    def test_login_request_sends_correct_method(self, fake_http):
        fake_http.set_response(
            "Session.login",
            {"jsonrpc": "2.0", "id": 1, "result": {"token": "t"}},
            cookie="SESSION_CONNECT_WEBADMIN=x",
        )
        client = KerioClient("host", 4040, "admin", "pass")
        client.login()
        assert fake_http.was_called("Session.login")

    def test_login_sends_application_as_object(self, fake_http):
        # Kerio returns -32602 Invalid params if `application` is sent as a string.
        # It MUST be an object {name, vendor, version}. See docs/api_fields.md.
        fake_http.set_response(
            "Session.login",
            {"jsonrpc": "2.0", "id": 1, "result": {"token": "t"}},
            cookie="SESSION=x",
        )
        client = KerioClient("host", 4040, "admin", "pass")
        client.login()
        app = fake_http.last_body("Session.login")["params"]["application"]
        assert isinstance(app, dict), f"application must be object, got {type(app).__name__}"
        for key in ("name", "vendor", "version"):
            assert key in app, f"application missing required key: {key}"

    def test_request_sends_token_after_login(self, all_responses):
        client = KerioClient("host", 4040, "admin", "pass")
        client.login()
        client.get_statistics()
        assert all_responses.was_called("Statistics.get")

    def test_logout_clears_token_and_cookie(self, all_responses):
        client = KerioClient("host", 4040, "admin", "pass")
        client.login()
        client.logout()
        assert client.token is None
        assert client.cookie is None

    def test_logout_called_even_when_stats_raises(self, fake_http):
        fake_http.set_response(
            "Session.login",
            {"jsonrpc": "2.0", "id": 1, "result": {"token": "t"}},
            cookie="SESSION=x",
        )
        fake_http.set_response(
            "Statistics.get",
            {"jsonrpc": "2.0", "id": 2, "error": {"code": -32000, "message": "Internal"}},
        )
        fake_http.set_response("Session.logout", {"jsonrpc": "2.0", "id": 3, "result": {}})
        with pytest.raises(RuntimeError):
            collect_all("host", 4040, "admin", "pass")
        assert fake_http.was_called("Session.logout")

    def test_uses_https_by_default(self, all_responses):
        collect_all("myhost", 4040, "admin", "pass")
        assert all_responses.last_url.startswith("https://myhost:4040")

    def test_http_scheme_override(self, all_responses):
        collect_all("myhost", 4040, "admin", "pass", scheme="http")
        assert all_responses.last_url.startswith("http://myhost:4040")

    def test_network_timeout_raises_runtime_error(self, fake_http):
        fake_http.set_response(
            "Session.login",
            {"jsonrpc": "2.0", "id": 1, "result": {"token": "t"}},
            cookie="SESSION=x",
        )
        fake_http.set_error("Statistics.get", socket.timeout("timed out"))
        fake_http.set_response("Session.logout", {"jsonrpc": "2.0", "id": 3, "result": {}})
        with pytest.raises(RuntimeError, match="timed out"):
            collect_all("host", 4040, "admin", "pass")

    def test_connection_refused_raises_runtime_error(self, fake_http):
        fake_http.set_error("Session.login", urllib.error.URLError("Connection refused"))
        with pytest.raises(RuntimeError, match="Connection refused"):
            collect_all("host", 4040, "admin", "pass")


class TestCollectAll:
    def test_returns_valid_json(self, all_responses):
        assert isinstance(json.loads(collect_all("host", 4040, "admin", "pass")), dict)

    def test_output_has_required_top_level_keys(self, all_responses):
        data = json.loads(collect_all("host", 4040, "admin", "pass"))
        for key in ("statistics", "services", "license", "server"):
            assert key in data

    def test_license_users_in_output(self, all_responses):
        data = json.loads(collect_all("host", 4040, "admin", "pass"))
        assert data["license"]["users"] == 5000

    def test_license_expiry_is_unix_timestamp(self, all_responses):
        data = json.loads(collect_all("host", 4040, "admin", "pass"))
        assert data["license"]["expirations"][0]["date"] == 1921449599

    def test_license_days_remaining(self, all_responses):
        data = json.loads(collect_all("host", 4040, "admin", "pass"))
        assert data["license"]["expirations"][0]["remainingDays"] == 1653

    def test_server_version_in_output(self, all_responses):
        data = json.loads(collect_all("host", 4040, "admin", "pass"))
        assert data["server"]["version"] == "10.0.8.9228"

    def test_services_array_contains_isrunning(self, all_responses):
        data = json.loads(collect_all("host", 4040, "admin", "pass"))
        names = {s["name"] for s in data["services"]}
        assert "SMTP" in names
        assert next(s for s in data["services"] if s["name"] == "SMTP")["isRunning"] is True
        assert next(s for s in data["services"] if s["name"] == "XMPP")["isRunning"] is False

    def test_domains_list_unavailable(self, all_responses):
        data = json.loads(collect_all("host", 4040, "admin", "pass"))
        assert "domains" not in data


class TestDiscoverServices:
    def test_returns_valid_json_array(self, all_responses):
        assert isinstance(json.loads(discover_services("host", 4040, "admin", "pass")), list)

    def test_each_entry_has_service_name_key(self, all_responses):
        data = json.loads(discover_services("host", 4040, "admin", "pass"))
        for entry in data:
            assert "{#SERVICE}" in entry

    def test_all_services_discovered_including_stopped(self, all_responses):
        data = json.loads(discover_services("host", 4040, "admin", "pass"))
        names = [entry["{#SERVICE}"] for entry in data]
        assert "XMPP" in names
        assert "SMTP" in names

    def test_empty_service_list(self, fake_http):
        from tests.conftest import API_RESPONSES

        for method, body in API_RESPONSES.items():
            cookie = "SESSION=x" if method == "Session.login" else None
            fake_http.set_response(method, body, cookie=cookie)
        fake_http.set_response("Services.get", {"jsonrpc": "2.0", "id": 5, "result": {"services": []}})
        assert json.loads(discover_services("host", 4040, "admin", "pass")) == []

    def test_always_logs_out_on_error(self, fake_http):
        fake_http.set_response(
            "Session.login",
            {"jsonrpc": "2.0", "id": 1, "result": {"token": "t"}},
            cookie="SESSION=x",
        )
        fake_http.set_error("Services.get", RuntimeError("API down"))
        fake_http.set_response("Session.logout", {"jsonrpc": "2.0", "id": 3, "result": {}})
        with pytest.raises(RuntimeError):
            discover_services("host", 4040, "admin", "pass")
        assert fake_http.was_called("Session.logout")


class TestLoadConfig:
    def test_reads_all_fields_from_ini(self, tmp_path):
        conf = tmp_path / "kerio.conf"
        conf.write_text(
            "[api]\n"
            "host = mail.example.com\n"
            "port = 4040\n"
            "scheme = https\n"
            "username = monuser\n"
            "password = s3cret\n"
        )
        cfg = load_config(str(conf))
        assert cfg == {
            "host": "mail.example.com",
            "port": 4040,
            "scheme": "https",
            "username": "monuser",
            "password": "s3cret",
        }

    def test_port_is_integer(self, tmp_path):
        conf = tmp_path / "kerio.conf"
        conf.write_text("[api]\nhost=h\nport=9999\nscheme=https\nusername=u\npassword=p\n")
        assert isinstance(load_config(str(conf))["port"], int)

    def test_missing_file_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/kerio.conf")

    def test_missing_required_key_raises_value_error(self, tmp_path):
        conf = tmp_path / "kerio.conf"
        conf.write_text("[api]\nhost=h\nport=4040\nscheme=https\n")
        with pytest.raises(ValueError, match="username"):
            load_config(str(conf))

    def test_config_used_when_no_cli_args(self, tmp_path):
        conf = tmp_path / "kerio.conf"
        conf.write_text(
            "[api]\n"
            "host = localhost\nport = 4040\nscheme = https\n"
            "username = admin\npassword = pass\n"
        )
        cfg = load_config(str(conf))
        assert cfg["host"] == "localhost"


class TestCLI:
    def _run(self, args):
        script = os.path.join(os.path.dirname(__file__), "..", "src", "kerio_collector.py")
        result = subprocess.run([sys.executable, script] + args, capture_output=True, text=True, timeout=35)
        return result.stdout.strip(), result.returncode

    def test_insufficient_args_exits_nonzero(self):
        stdout, code = self._run([])
        assert code != 0
        assert "error" in json.loads(stdout)

    def test_unknown_mode_exits_nonzero(self):
        stdout, code = self._run(["badmode", "h", "4040", "u", "p"])
        assert code != 0
        assert "error" in json.loads(stdout)

    def test_bad_credentials_outputs_json_error(self):
        stdout, code = self._run(["collect", "127.0.0.1", "4040", "baduser", "badpass"])
        assert code != 0
        assert "error" in json.loads(stdout)
