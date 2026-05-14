#!/usr/bin/env python3
"""Replace <UUID_*> placeholders in Zabbix template YAML files."""
import re
import sys
import uuid
from pathlib import Path


def fill_uuids(path: str) -> int:
    content = Path(path).read_text()
    placeholders = re.findall(r"<UUID_[A-Z0-9_]+>", content)
    if not placeholders:
        print(f"No placeholders found in {path}")
        return 0

    seen = {}
    replaced = 0

    def replacer(match):
        nonlocal replaced
        placeholder = match.group(0)
        if placeholder not in seen:
            seen[placeholder] = str(uuid.uuid4())
        replaced += 1
        return seen[placeholder]

    Path(path).write_text(re.sub(r"<UUID_[A-Z0-9_]+>", replacer, content))
    print(f"Replaced {replaced} UUID placeholders in {path}")
    return replaced


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tools/generate_uuids.py <template.yaml>")
        sys.exit(1)
    fill_uuids(sys.argv[1])
