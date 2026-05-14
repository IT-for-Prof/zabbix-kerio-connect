# CLAUDE.md

This repository contains Zabbix 7 templates for monitoring Kerio Connect via
the JSON-RPC Admin API.

## Commands

```bash
pytest tests/ -v --ignore=tests/test_deployment.py
pytest tests/test_deployment.py -m live -v
python3 tests/test_live_api.py <kerio-host> 4040 <user> <password>
node --check src/master_collector.js
node --check src/lld_services.js
python3 tools/generate_uuids.py template/kerio_connect_script/template_app_kerio_connect_script.yaml
```

## Architecture

`src/kerio_collector.py` logs in once, calls `Statistics.get`,
`Services.get`, `ProductRegistration.getFullStatus`, and `Server.getVersion`,
then logs out. Its JSON output shape is the contract used by template JSONPath
preprocessing.

`src/master_collector.js` is the Zabbix Script item equivalent for Duktape. It
uses Zabbix `HttpRequest`, not browser or Node APIs.

`docs/api_fields.md` is the source of truth for live Kerio field names. Update
fixtures and JSONPath expressions from that document before changing collector
logic.

## Credentials

The Script template passes host macros into the Zabbix Script item. The agent
template reads credentials from `/etc/zabbix/kerio_connect.conf`; do not put
secrets in `zabbix_agent2.conf` because Zabbix host macros are not expanded
there.

## UUIDs

Run `tools/generate_uuids.py` once when creating a template. Do not regenerate
UUIDs in committed templates because changed UUIDs create duplicates on import.
