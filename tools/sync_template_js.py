#!/usr/bin/env python3
"""
Sync src/*.js into the Zabbix template YAML `params:` fields.

Zabbix executes the JS embedded in the YAML, not the standalone .js files.
This tool rewrites the two `params:` fields in the Script template (the master
item and the LLD rule) from `src/master_collector.js` and `src/lld_services.js`.

We parse the YAML, set the field, then re-serialise as PyYAML block-scalar
style so the diff stays readable.

Usage:
  python3 tools/sync_template_js.py        # sync (write)
  python3 tools/sync_template_js.py --check # exit 1 if drift exists
"""
import sys
from pathlib import Path

import yaml

SCRIPT_TEMPLATE = Path("template/kerio_connect_script/template_app_kerio_connect_script.yaml")
MASTER_JS = Path("src/master_collector.js")
LLD_JS = Path("src/lld_services.js")


class _LiteralStr(str):
    """Marker subclass so PyYAML emits as `|` block scalar."""


def _literal_str_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


yaml.add_representer(_LiteralStr, _literal_str_representer)


def _normalize(s: str) -> str:
    return s.replace("\r\n", "\n").rstrip("\n") + "\n"


def apply(doc: dict) -> bool:
    """Mutate doc in place. Return True if anything changed."""
    master_js = _normalize(MASTER_JS.read_text())
    lld_js = _normalize(LLD_JS.read_text())

    changed = False
    for tpl in doc["zabbix_export"]["templates"]:
        for item in tpl.get("items", []):
            if item.get("key") == "kerio.api.master" and item.get("type") == "SCRIPT":
                if _normalize(item.get("params", "")) != master_js:
                    changed = True
                item["params"] = _LiteralStr(master_js)
        for lld in tpl.get("discovery_rules", []):
            if lld.get("key") == "kerio.services.discovery" and lld.get("type") == "SCRIPT":
                if _normalize(lld.get("params", "")) != lld_js:
                    changed = True
                lld["params"] = _LiteralStr(lld_js)
    return changed


def main():
    check_only = "--check" in sys.argv
    doc = yaml.safe_load(SCRIPT_TEMPLATE.read_text())
    if not apply(doc):
        print("Already in sync.")
        return
    new_text = yaml.dump(doc, sort_keys=False, allow_unicode=True, width=10000)
    if check_only:
        sys.exit(
            "DRIFT: src/master_collector.js or src/lld_services.js differ from "
            "the embedded params: blocks in the Script template. "
            "Run: python3 tools/sync_template_js.py"
        )
    SCRIPT_TEMPLATE.write_text(new_text)
    print(f"Updated {SCRIPT_TEMPLATE}")


if __name__ == "__main__":
    main()
