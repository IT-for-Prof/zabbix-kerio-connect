#!/usr/bin/env python3
"""
Kerio Connect collector for Zabbix monitoring.

CLI usage:
  python3 kerio_collector.py collect <config_file>
  python3 kerio_collector.py lld_services <config_file>
  python3 kerio_collector.py collect <host> <port> <user> <password> [scheme]
  python3 kerio_collector.py lld_services <host> <port> <user> <password> [scheme]
"""
import configparser
import json
import os
import socket
import ssl
import sys
import urllib.error
import urllib.request


REQUIRED_CONFIG_KEYS = ("host", "port", "username", "password")


def load_config(path: str) -> dict:
    """Read Kerio API credentials from an INI config file."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    cfg = configparser.ConfigParser()
    cfg.read(path)
    if "api" not in cfg:
        raise ValueError("Config file must have an [api] section")

    section = cfg["api"]
    for key in REQUIRED_CONFIG_KEYS:
        if key not in section:
            raise ValueError(f"Missing required config key: {key}")

    return {
        "host": section["host"],
        "port": int(section["port"]),
        "scheme": section.get("scheme", "https"),
        "username": section["username"],
        "password": section["password"],
    }


class KerioClient:
    def __init__(self, host: str, port: int, username: str, password: str, scheme: str = "https"):
        self.url = f"{scheme}://{host}:{port}/admin/api/jsonrpc/"
        self.username = username
        self.password = password
        self.token = None
        self.cookie = None
        self._req_id = 0
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE

    def _call(self, method: str, params: dict = None) -> dict:
        self._req_id += 1
        payload = {"jsonrpc": "2.0", "id": self._req_id, "method": method}
        if params:
            payload["params"] = params
        if self.token:
            payload["token"] = self.token

        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        if self.cookie:
            req.add_header("Cookie", self.cookie)
        if self.token:
            req.add_header("X-Token", self.token)

        try:
            with urllib.request.urlopen(req, context=self._ssl_ctx, timeout=30) as resp:
                raw_cookie = resp.headers.get("Set-Cookie", "")
                if raw_cookie and not self.cookie:
                    self.cookie = raw_cookie.split(";")[0]
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, socket.timeout) as exc:
            raise RuntimeError(str(exc)) from exc

        if "error" in data:
            raise RuntimeError(data["error"].get("message", "Kerio API error"))
        return data["result"]

    def login(self) -> None:
        result = self._call(
            "Session.login",
            {
                "userName": self.username,
                "password": self.password,
                "application": {
                    "name": "Zabbix Monitoring",
                    "vendor": "Zabbix",
                    "version": "7.0",
                },
            },
        )
        self.token = result["token"]

    def logout(self) -> None:
        try:
            self._call("Session.logout")
        except Exception:
            pass
        finally:
            self.token = None
            self.cookie = None

    def get_statistics(self) -> dict:
        return self._call("Statistics.get")

    def get_services(self) -> dict:
        return self._call("Services.get")

    def get_license(self) -> dict:
        return self._call("ProductRegistration.getFullStatus")

    def get_server_version(self) -> dict:
        return self._call("Server.getVersion")


def collect_all(host: str, port: int, username: str, password: str, scheme: str = "https") -> str:
    """Collect all Kerio metrics available to the Auditor role."""
    client = KerioClient(host, port, username, password, scheme)
    client.login()
    try:
        stats = client.get_statistics()
        services = client.get_services()
        license_info = client.get_license()
        server = client.get_server_version()
    finally:
        client.logout()

    return json.dumps(
        {
            "statistics": stats.get("statistics", {}),
            "services": services.get("services", []),
            "license": license_info.get("status", {}),
            "server": server,
        }
    )


def discover_services(host: str, port: int, username: str, password: str, scheme: str = "https") -> str:
    """Return Zabbix LLD JSON for Kerio services."""
    client = KerioClient(host, port, username, password, scheme)
    client.login()
    try:
        services = client.get_services()
    finally:
        client.logout()

    return json.dumps([{"{#SERVICE}": svc["name"]} for svc in services.get("services", [])])


def _usage() -> str:
    return (
        "Usage:\n"
        "  kerio_collector.py <mode> <config_file>\n"
        "  kerio_collector.py <mode> <host> <port> <user> <password> [scheme]\n"
        "  mode: collect | lld_services"
    )


def _main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(json.dumps({"error": _usage()}))
        return 1

    mode = argv[1]
    dispatch = {"collect": collect_all, "lld_services": discover_services}
    if mode not in dispatch:
        print(json.dumps({"error": f"Unknown mode '{mode}'. Use: collect, lld_services"}))
        return 1

    if len(argv) == 3:
        try:
            cfg = load_config(argv[2])
        except (FileNotFoundError, ValueError) as exc:
            print(json.dumps({"error": str(exc)}))
            return 1
        host, port, username, password, scheme = (
            cfg["host"],
            cfg["port"],
            cfg["username"],
            cfg["password"],
            cfg["scheme"],
        )
    elif len(argv) >= 6:
        host, port_str, username, password = argv[2:6]
        scheme = argv[6] if len(argv) > 6 else "https"
        try:
            port = int(port_str)
        except ValueError:
            print(json.dumps({"error": f"Invalid port: {port_str}"}))
            return 1
    else:
        print(json.dumps({"error": "Insufficient arguments"}))
        return 1

    try:
        print(dispatch[mode](host, port, username, password, scheme))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
