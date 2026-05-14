import re
from pathlib import Path

import pytest
import yaml


SCRIPT_TEMPLATE = Path("template/kerio_connect_script/template_app_kerio_connect_script.yaml")
AGENT_TEMPLATE = Path("template/kerio_connect_agent/template_app_kerio_connect_agent.yaml")
ALL_TEMPLATES = [SCRIPT_TEMPLATE, AGENT_TEMPLATE]
PROJECT_DESCRIPTION = "Zabbix 7 templates for monitoring Kerio Connect via JSON-RPC Admin API"
PROJECT_URL = "https://github.com/IT-for-Prof/zabbix-kerio-connect"


def load_template(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


@pytest.mark.parametrize("path", ALL_TEMPLATES)
def test_valid_yaml(path):
    assert "zabbix_export" in load_template(path)


@pytest.mark.parametrize("path", ALL_TEMPLATES)
def test_zabbix_version_is_7(path):
    assert load_template(path)["zabbix_export"]["version"] == "7.0"


@pytest.mark.parametrize("path", ALL_TEMPLATES)
def test_template_description_contains_project_description_and_original_link(path):
    description = load_template(path)["zabbix_export"]["templates"][0]["description"]
    assert PROJECT_DESCRIPTION in description
    assert PROJECT_URL in description


def test_agent_template_tags_match_script_template():
    script = load_template(SCRIPT_TEMPLATE)["zabbix_export"]["templates"][0]
    agent = load_template(AGENT_TEMPLATE)["zabbix_export"]["templates"][0]
    assert agent.get("tags", []) == script.get("tags", [])

    script_items = {item["key"]: item for item in script.get("items", [])}
    agent_items = {item["key"]: item for item in agent.get("items", [])}
    for key, script_item in script_items.items():
        assert agent_items[key].get("tags", []) == script_item.get("tags", [])

    script_rules = {rule["key"]: rule for rule in script.get("discovery_rules", [])}
    agent_rules = {rule["key"]: rule for rule in agent.get("discovery_rules", [])}
    for key, script_rule in script_rules.items():
        script_prototypes = {prototype["key"]: prototype for prototype in script_rule.get("item_prototypes", [])}
        agent_prototypes = {prototype["key"]: prototype for prototype in agent_rules[key].get("item_prototypes", [])}
        for prototype_key, script_prototype in script_prototypes.items():
            assert agent_prototypes[prototype_key].get("tags", []) == script_prototype.get("tags", [])


@pytest.mark.parametrize("path", ALL_TEMPLATES)
def test_no_unfilled_uuid_placeholders(path):
    assert re.findall(r"<UUID_[A-Z0-9_]+>", path.read_text()) == []


@pytest.mark.parametrize("path", ALL_TEMPLATES)
def test_all_uuids_are_unique(path):
    uuids = re.findall(r"uuid:\s+([a-f0-9-]{36})", path.read_text())
    assert len(uuids) == len(set(uuids))


@pytest.mark.parametrize("path", ALL_TEMPLATES)
def test_all_dependent_items_reference_existing_master(path):
    template = load_template(path)["zabbix_export"]["templates"][0]
    master_keys = {
        item["key"]
        for item in template.get("items", [])
        if item.get("type", "ZABBIX_ACTIVE") != "DEPENDENT"
    }
    for item in template.get("items", []):
        if item.get("type") == "DEPENDENT":
            assert item.get("master_item", {}).get("key") in master_keys


@pytest.mark.parametrize("path", ALL_TEMPLATES)
def test_no_duplicate_item_keys(path):
    items = load_template(path)["zabbix_export"]["templates"][0].get("items", [])
    keys = [item["key"] for item in items]
    assert len(keys) == len(set(keys))


def test_script_template_has_credential_macros():
    # Script template drives the API directly, so credentials must be macros
    # the operator sets per host. The agent template reads them from a file on
    # the agent and intentionally does NOT declare these.
    template = load_template(SCRIPT_TEMPLATE)["zabbix_export"]["templates"][0]
    macro_names = {macro["macro"] for macro in template.get("macros", [])}
    for required in (
        "{$KERIO.API.HOST}",
        "{$KERIO.API.PORT}",
        "{$KERIO.API.USERNAME}",
        "{$KERIO.API.PASSWORD}",
        "{$KERIO.API.SCHEME}",
    ):
        assert required in macro_names, f"Script template missing {required}"


def test_script_template_password_macro_is_secret():
    template = load_template(SCRIPT_TEMPLATE)["zabbix_export"]["templates"][0]
    password_macro = next(m for m in template["macros"] if m["macro"] == "{$KERIO.API.PASSWORD}")
    assert password_macro.get("type") == "SECRET_TEXT"


def test_agent_template_does_not_declare_credential_macros():
    # Agent template reads credentials from the file at {$KERIO.AGENT.CONFIG}.
    # Declaring Kerio API credential macros would be misleading.
    template = load_template(AGENT_TEMPLATE)["zabbix_export"]["templates"][0]
    macro_names = {macro["macro"] for macro in template.get("macros", [])}
    for forbidden in (
        "{$KERIO.API.HOST}",
        "{$KERIO.API.PORT}",
        "{$KERIO.API.USERNAME}",
        "{$KERIO.API.PASSWORD}",
        "{$KERIO.API.SCHEME}",
    ):
        assert forbidden not in macro_names, f"Agent template should NOT declare {forbidden}"


@pytest.mark.parametrize("path", ALL_TEMPLATES)
def test_threshold_macros_present(path):
    template = load_template(path)["zabbix_export"]["templates"][0]
    macro_names = {macro["macro"] for macro in template.get("macros", [])}
    for required in ("{$KERIO.QUEUE.WARN}", "{$KERIO.DISK.WARN}", "{$KERIO.SMTP.AUTH.WARN}"):
        assert required in macro_names, f"{path.name} missing {required}"


@pytest.mark.parametrize("path", ALL_TEMPLATES)
def test_templates_do_not_use_unsupported_zabbix_js_headers_api(path):
    assert "getHeader(" not in path.read_text()


def test_source_js_does_not_use_unsupported_zabbix_headers_api():
    for path in (Path("src/master_collector.js"), Path("src/lld_services.js")):
        assert "getHeader(" not in path.read_text()


def test_template_js_matches_source():
    # Zabbix executes the JS embedded in the YAML, not src/*.js. tools/sync_template_js.py
    # rewrites the embedded blocks from the source files. If this test fails, the
    # source has diverged — run `python3 tools/sync_template_js.py`.
    import subprocess

    result = subprocess.run(
        ["python3", "tools/sync_template_js.py", "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_script_items_have_runtime_timeout():
    template = load_template(SCRIPT_TEMPLATE)["zabbix_export"]["templates"][0]
    master = next(item for item in template["items"] if item["key"] == "kerio.api.master")
    lld = next(rule for rule in template["discovery_rules"] if rule["key"] == "kerio.services.discovery")
    assert master["timeout"] == "30s"
    assert lld["timeout"] == "30s"


def test_script_template_master_is_script_type():
    items = load_template(SCRIPT_TEMPLATE)["zabbix_export"]["templates"][0]["items"]
    assert next(item for item in items if item["key"] == "kerio.api.master")["type"] == "SCRIPT"


def test_agent_template_master_is_active_agent_type():
    items = load_template(AGENT_TEMPLATE)["zabbix_export"]["templates"][0]["items"]
    assert next(item for item in items if item["key"] == "kerio.api.master")["type"] == "ZABBIX_ACTIVE"


@pytest.mark.parametrize("path", ALL_TEMPLATES)
def test_expected_dependent_items_exist(path):
    items = load_template(path)["zabbix_export"]["templates"][0]["items"]
    item_keys = {item["key"] for item in items}
    expected = {
        "kerio.disk.used",
        "kerio.disk.total",
        "kerio.disk.pct",
        "kerio.queue.total",
        "kerio.smtp.connections",
        "kerio.smtp.messages.in",
        "kerio.smtp.messages.out",
        "kerio.smtp.auth.failures",
        "kerio.imap.connections",
        "kerio.pop3.connections",
        "kerio.ldap.connections",
        "kerio.web.connections",
        "kerio.xmpp.connections",
        "kerio.spam.checked",
        "kerio.spam.rejected",
        "kerio.av.scanned",
        "kerio.av.infected",
        "kerio.greylisting.delayed",
        "kerio.antibombing.rejected",
        "kerio.uptime.days",
        "kerio.license.users",
        "kerio.license.expiry",
        "kerio.license.days",
        "kerio.version",
    }
    assert not expected - item_keys


@pytest.mark.parametrize("path", ALL_TEMPLATES)
def test_expected_jsonpath_mappings(path):
    template = load_template(path)["zabbix_export"]["templates"][0]
    expected = {
        "kerio.disk.used": "$.statistics.storage.occupied.value",
        "kerio.disk.total": "$.statistics.storage.total.value",
        "kerio.disk.pct": "$.statistics.storage.percentage",
        "kerio.queue.total": "$.statistics.storedInQueue.count",
        "kerio.uptime.days": "$.statistics.uptime.days",
        "kerio.smtp.connections": "$.statistics.smtpServer.totalIncomingConnections",
        "kerio.smtp.messages.in": "$.statistics.received.count",
        "kerio.smtp.messages.out": "$.statistics.transmitted.count",
        "kerio.smtp.auth.failures": "$.statistics.smtpServer.authenticationFailures",
        "kerio.imap.connections": "$.statistics.imapServer.totalIncomingConnections",
        "kerio.pop3.connections": "$.statistics.pop3Server.totalIncomingConnections",
        "kerio.ldap.connections": "$.statistics.ldapServer.totalIncomingConnections",
        "kerio.web.connections": "$.statistics.webServer.totalIncomingConnections",
        "kerio.xmpp.connections": "$.statistics.xmppServer.totalIncomingConnections",
        "kerio.spam.checked": "$.statistics.spam.checked",
        "kerio.spam.rejected": "$.statistics.spam.rejected",
        "kerio.av.scanned": "$.statistics.antivirus.checkedAttachments",
        "kerio.av.infected": "$.statistics.antivirus.foundViruses",
        "kerio.greylisting.delayed": "$.statistics.greylisting.messagesDelayed",
        "kerio.antibombing.rejected": "$.statistics.antibombing.rejectedConnections",
        "kerio.license.users": "$.license.users",
        "kerio.license.expiry": '$.license.expirations[?(@.type=="License")].date.first()',
        "kerio.license.days": '$.license.expirations[?(@.type=="License")].remainingDays.first()',
        "kerio.version": "$.server.version",
    }
    by_key = {item["key"]: item for item in template["items"]}
    for key, jsonpath in expected.items():
        assert by_key[key]["preprocessing"][0]["parameters"] == [jsonpath]
