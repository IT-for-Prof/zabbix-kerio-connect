# Kerio Connect API Field Names

Verified against a live Kerio Connect 10.0.8.9228 server with an Auditor-role
API user.

## Authentication

```json
POST /admin/api/jsonrpc/
{
  "jsonrpc": "2.0", "id": 1, "method": "Session.login",
  "params": {
    "userName": "zabbix_api",
    "password": "...",
    "application": {"name": "ZbxProbe", "vendor": "Zabbix", "version": "1.0"}
  }
}
```
Response: `{"result": {"token": "<hex>"}}`
Cookie: `Set-Cookie: SESSION_CONNECT_WEBADMIN=...; Path=/`

**Critical:** `application` MUST be an object `{name, vendor, version}`.
A string value returns `-32602 Invalid params`.

User role queried via `Session.whoAmI` → `{"userDetails": {"effectiveRole": {"userRole": "Auditor"}}}`

---

## Statistics.get — CONFIRMED WORKING

```json
{"method": "Statistics.get", "params": {}}
```

Response path: `result.statistics`

```json
{
  "statistics": {
    "start": 1754246600,
    "uptime": {"days": 1, "hours": 2, "minutes": 34},
    "storage": {
      "total":    {"value": 716796, "units": "MegaBytes"},
      "occupied": {"value": 666175, "units": "MegaBytes"},
      "percentage": "92"
    },
    "received":         {"count": "617376", "volume": {"value": 119600, "units": "MegaBytes"}, "recipients": "4380038"},
    "storedInQueue":    {"count": "0",      "volume": {"value": 0,      "units": "Bytes"},     "recipients": "0"},
    "transmitted":      {"count": "319307", "volume": {"value": 135228, "units": "MegaBytes"}, "recipients": "394693"},
    "deliveredToLocals":{"count": "161811", "volume": {"value": 114199, "units": "MegaBytes"}, "recipients": "161811"},
    "mx":               {"count": "157497", "volume": {"value": 21029,  "units": "MegaBytes"}, "recipients": "232884"},
    "relay":            {"count": "0"},
    "failures": {"transientFailures": "43440208", "permanentFailures": "4009847"},
    "deliveryStatus": {"success": "110", "delay": "75209", "failure": "229979"},
    "antivirus": {"checkedAttachments": "579391", "foundViruses": "147", "prohibitedTypes": "2"},
    "spam": {"checked": "91714", "tagged": "4072", "rejected": "10895", "markedAsSpam": "1693", "markedAsNotSpam": "172"},
    "other": {"largest": {"value": 556545, "units": "KiloBytes"}, "loops": "849"},
    "smtpServer": {
      "totalIncomingConnections": "1506226",
      "lostConnections": "297216",
      "rejectedByBlacklist": "23589",
      "authenticationAttempts": "457665",
      "authenticationFailures": "334700",
      "rejectedRelays": "1126",
      "acceptedMessages": "257871"
    },
    "smtpClient": {
      "connectionAttempts": "12712121",
      "dnsFailures": "232500",
      "connectionFailures": "258536",
      "connectionLosses": "5250443"
    },
    "pop3Server": {"totalIncomingConnections": "1", "authenticationFailures": "0", "sentMessages": "0"},
    "pop3Client": {"connectionAttempts": "0", "connectionFailures": "0", "authenticationFailures": "0", "totalDownloads": "0"},
    "imapServer": {"totalIncomingConnections": "320268", "authenticationFailures": "9491"},
    "ldapServer": {"totalIncomingConnections": "1", "authenticationFailures": "0", "totalSearchRequests": "0"},
    "webServer":  {"totalIncomingConnections": "14695683"},
    "xmppServer": {"totalIncomingConnections": "0", "authenticationFailures": "0"},
    "dnsResolver": {"hostnameQueries": "24162601", "cachedHostnameQueries": "12920186", "mxQueries": "12746333", "cachedMxQueries": "12426283"},
    "antibombing": {"rejectedConnections": "0", "rejectedMessages": "0", "rejectedHarvestAttacks": "159"},
    "greylisting": {"messagesAccepted": "79688", "messagesDelayed": "2345", "messagesSkipped": "324"}
  }
}
```

### Data type notes
- Most counter fields are **strings** (e.g., `"617376"`), not integers
- `storage.total.value` and `storage.occupied.value` are **integers** (MegaBytes)
- `storage.percentage` is a **string** (e.g., `"92"`)
- `uptime.days` is an **integer**
- All connection counts are **cumulative since server start** (not active/current)

---

## Services.get — CONFIRMED WORKING

```json
{"method": "Services.get", "params": {}}
```

Response path: `result.services` (array)

```json
{
  "services": [
    {
      "id": "keriodb://service/61ad7ad5-60b8-4cae-ab82-f7c444dae102",
      "name": "SMTP",
      "howToStart": "Automatic",
      "defaultPort": 25,
      "isRunning": true,
      "listeners": [{"type": "AllAddresses", "address": "All addresses", "port": 25}],
      "connectionLimit": {"isSet": true, "value": 1000},
      "group": {"isUsed": false, "ipGroup": {"id": "", "name": ""}},
      "anonymousAccess": false
    }
  ]
}
```

### Service names returned by Kerio Connect (15 services on a default install)
`SMTP`, `Secure SMTP`, `SMTP Submission`, `POP3`, `Secure POP3`, `IMAP`, `Secure IMAP`,
`NNTP`, `Secure NNTP`, `LDAP`, `Secure LDAP`, `HTTP`, `Secure HTTP`, `XMPP`, `Secure XMPP`

`isRunning` is a **boolean** (`true`/`false`).

---

## ProductRegistration.getFullStatus — CONFIRMED WORKING

```json
{"method": "ProductRegistration.getFullStatus", "params": {}}
```

Response path: `result.status`

```json
{
  "status": {
    "regType": "rsProductRegistered",
            "Id": "REDACTED-LICENSE-ID",
    "company": "Kerio Connect User",
    "users": 5000,
    "expirations": [
      {
        "type": "License",
        "isUnlimited": false,
        "remainingDays": 1653,
        "date": 1921449599
      },
      {
        "type": "Subscription",
        "isUnlimited": false,
        "remainingDays": 1653,
        "date": 1921449599
      }
    ]
  }
}
```

- `users` is an **integer** — licensed user seat count
- `expirations[0].date` is a **Unix timestamp integer** — expiry date
- `expirations[0].remainingDays` is an **integer** — days until expiry
- `expirations[0].type` is `"License"` or `"Subscription"`
- Confirmed working with **Auditor role** (contrary to earlier failed `ProductRegistration.get` attempt — `getFullStatus` is the correct method name)

---

## Server.getVersion — CONFIRMED WORKING

```json
{"method": "Server.getVersion", "params": {}}
```

Response path: `result`

```json
{
  "product": "Kerio Connect",
  "version": "10.0.8.9228",
  "major": 10,
  "minor": 0,
  "revision": 8,
  "build": 9228
}
```

---

## NOT AVAILABLE with Auditor role

| Method | Error | Reason |
|--------|-------|--------|
| `SystemHealth.get` | `-32602 Invalid params` | Always fails regardless of params. Likely requires Admin role or is not implemented in this Kerio Connect version. CPU/memory/swap NOT available via API. |
| `ProductRegistration.get` | `-32602 Invalid params` | Wrong method name. Use `ProductRegistration.getFullStatus` instead — that works with Auditor role. |
| `Domains.get` | `1000 internal database error` | Requires Admin role. Per-domain storage NOT available with Auditor. |
| `MessageQueue.get` / `Queue.getMessages` / `Queue.get` | Timeout | These methods hang. Queue depth is available in `Statistics.get` → `storedInQueue.count`. |

---

## JSONPath mapping for Zabbix dependent items

All paths assume master item returns:
```json
{
  "statistics": <Statistics.get result.statistics>,
  "services":   <Services.get result.services>,
  "license":    <ProductRegistration.getFullStatus result.status>,
  "server":     <Server.getVersion result>
}
```

| Metric | JSONPath | Type | Unit | Notes |
|--------|----------|------|------|-------|
| `kerio.disk.used` | `$.statistics.storage.occupied.value` | Numeric | MB | integer |
| `kerio.disk.total` | `$.statistics.storage.total.value` | Numeric | MB | integer |
| `kerio.disk.pct` | `$.statistics.storage.percentage` | Numeric | % | string → needs `Matches regex (\d+)` or numeric conversion |
| `kerio.queue.total` | `$.statistics.storedInQueue.count` | Numeric | messages | string |
| `kerio.smtp.messages.in` | `$.statistics.received.count` | Numeric | messages | cumulative string |
| `kerio.smtp.messages.out` | `$.statistics.transmitted.count` | Numeric | messages | cumulative string |
| `kerio.smtp.auth.failures` | `$.statistics.smtpServer.authenticationFailures` | Numeric | | cumulative string |
| `kerio.smtp.connections` | `$.statistics.smtpServer.totalIncomingConnections` | Numeric | | cumulative string |
| `kerio.imap.connections` | `$.statistics.imapServer.totalIncomingConnections` | Numeric | | cumulative string |
| `kerio.pop3.connections` | `$.statistics.pop3Server.totalIncomingConnections` | Numeric | | cumulative string |
| `kerio.ldap.connections` | `$.statistics.ldapServer.totalIncomingConnections` | Numeric | | cumulative string |
| `kerio.web.connections` | `$.statistics.webServer.totalIncomingConnections` | Numeric | | cumulative string |
| `kerio.xmpp.connections` | `$.statistics.xmppServer.totalIncomingConnections` | Numeric | | cumulative string |
| `kerio.spam.checked` | `$.statistics.spam.checked` | Numeric | | cumulative string |
| `kerio.spam.rejected` | `$.statistics.spam.rejected` | Numeric | | cumulative string |
| `kerio.av.scanned` | `$.statistics.antivirus.checkedAttachments` | Numeric | | cumulative string |
| `kerio.av.infected` | `$.statistics.antivirus.foundViruses` | Numeric | | cumulative string |
| `kerio.greylisting.delayed` | `$.statistics.greylisting.messagesDelayed` | Numeric | | cumulative string |
| `kerio.antibombing.rejected` | `$.statistics.antibombing.rejectedConnections` | Numeric | | cumulative string |
| `kerio.uptime.days` | `$.statistics.uptime.days` | Numeric | days | integer |
| `kerio.service.status[{#SERVICE}]` | `$.services[?(@.name=="{#SERVICE}")].isRunning.first()` | Numeric | | boolean → needs "Boolean to decimal" preprocessing |
| `kerio.license.users` | `$.license.users` | Numeric | seats | integer |
| `kerio.license.expiry` | `$.license.expirations[0].date` | Numeric | unixtime | integer; use unixtime display format |
| `kerio.license.days` | `$.license.expirations[0].remainingDays` | Numeric | days | integer |
| `kerio.version` | `$.server.version` | Text | | string e.g. "10.0.8.9228"; informational |

### Removed from plan (not available via API):
- `kerio.cpu.usage` — SystemHealth.get unavailable with Auditor role (all param variants fail; Batch.run bypass also fails)
- `kerio.memory.used` / `kerio.memory.free` — same
- `kerio.swap.used` — same
- `kerio.domain.storage[{#DOMAIN}]` — Domains.get requires Admin role
- `kerio.domains.count` — Domains.get requires Admin role
- `kerio.queue.inprocess` / `kerio.queue.throughput.*` — no API

> CPU/memory/swap are available via the standard OS template (Windows or Linux by Zabbix agent) — link it to the host alongside this template.
