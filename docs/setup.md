# Setup

## Script Template

Import `template/kerio_connect_script/template_app_kerio_connect_script.yaml`
into Zabbix 7 and link it to the Kerio Connect host.

Set host macros:

```text
{$KERIO.API.HOST}=<Kerio host or IP>
{$KERIO.API.PORT}=4040
{$KERIO.API.USERNAME}=<Auditor user>
{$KERIO.API.PASSWORD}=<secret password>
```

The Zabbix server or proxy must be able to reach
`https://<Kerio host>:4040/admin/api/jsonrpc/`.

## Agent Template

Copy the collector and the UserParameter file to the agent host:

```bash
install -m 0755 src/kerio_collector.py /opt/zabbix-kerio-connect/src/kerio_collector.py
install -m 0644 template/kerio_connect_agent/zabbix_agent2.d/kerio_connect.conf \
                /etc/zabbix/zabbix_agent2.d/kerio_connect.conf
```

Create `/etc/zabbix/kerio_connect.conf`:

```ini
[api]
host = 127.0.0.1
port = 4040
scheme = https
username = zabbix_api
password = change-me
```

Restrict permissions:

```bash
chown zabbix:zabbix /etc/zabbix/kerio_connect.conf
chmod 0600 /etc/zabbix/kerio_connect.conf
```

Edit `/etc/zabbix/zabbix_agent2.conf` and ensure:

```text
Timeout=30
Include=/etc/zabbix/zabbix_agent2.d/*.conf
```

`Timeout` must be at least 30 — the UserParameter performs an HTTPS login + 4
JSON-RPC calls and easily exceeds the default 3 seconds.

Restart the agent (`systemctl restart zabbix-agent2`), import
`template/kerio_connect_agent/template_app_kerio_connect_agent.yaml`, and link
it to the host.

## Verification

Run local non-live checks:

```bash
pytest tests/ -v --ignore=tests/test_deployment.py
```

After linking a template in Zabbix and waiting for the first polling interval:

```bash
pytest tests/test_deployment.py -m live -v
```
