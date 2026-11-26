#!/usr/bin/env python3
"""
Sync src/*.js into the Zabbix template YAML `params:` fields.

Zabbix executes the JS embedded in the YAML, not the standalone .js files.
This tool rewrites every Script `params:` field in both language versions of
the Script template from
`src/kerio_api.js` (shared client) followed by the item's own collector file.

We parse the YAML, set the field, then re-serialise as PyYAML block-scalar
style so the diff stays readable.

Usage:
  python3 tools/sync_template_js.py        # sync (write)
  python3 tools/sync_template_js.py --check # exit 1 if drift exists
"""
import sys
from pathlib import Path

import yaml

SCRIPT_TEMPLATES = [
    Path("template/kerio_connect_script/template_app_kerio_connect_script.yaml"),
    Path("template/kerio_connect_script/template_app_kerio_connect_script_ru.yaml"),
]
COMMON_JS = Path("src/kerio_api.js")
# Script item / LLD rule key -> its collector.
SCRIPTS = {
    "kerio.api.master": Path("src/master_collector.js"),
    "kerio.queue.raw": Path("src/queue_collector.js"),
    "kerio.relay.unauth": Path("src/relay_collector.js"),
    "kerio.services.discovery": Path("src/lld_services.js"),
}


class _LiteralStr(str):
    """Marker subclass so PyYAML emits as `|` block scalar."""


def _literal_str_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


yaml.add_representer(_LiteralStr, _literal_str_representer)


def _normalize(s: str) -> str:
    return s.replace("\r\n", "\n").rstrip("\n") + "\n"


def compose(key: str) -> str:
    """The JS Zabbix runs for `key`: shared client first, then the collector."""
    return _normalize(COMMON_JS.read_text()) + "\n" + _normalize(SCRIPTS[key].read_text())


def apply(doc: dict) -> bool:
    """Mutate doc in place. Return True if anything changed."""
    changed = False
    for tpl in doc["zabbix_export"]["templates"]:
        for obj in tpl.get("items", []) + tpl.get("discovery_rules", []):
            if obj.get("type") == "SCRIPT" and obj.get("key") in SCRIPTS:
                js = compose(obj["key"])
                if _normalize(obj.get("params", "")) != js:
                    changed = True
                obj["params"] = _LiteralStr(js)
    return changed


def main():
    check_only = "--check" in sys.argv
    drift = []
    for path in SCRIPT_TEMPLATES:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not apply(doc):
            print(f"Already in sync: {path}")
            continue
        drift.append(path)
        if not check_only:
            path.write_text(yaml.dump(doc, sort_keys=False, allow_unicode=True, width=10000), encoding="utf-8")
            print(f"Updated {path}")
    if check_only and drift:
        sys.exit(
            "DRIFT: src/*.js differ from the embedded params: blocks in "
            + ", ".join(map(str, drift))
            + ". Run: python3 tools/sync_template_js.py"
        )

if __name__ == "__main__":
    main()
