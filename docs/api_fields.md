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
- `transmitted.count` = `deliveredToLocals.count` + `mx.count` + `relay.count` (checked on three live servers: the sum
  matches within 1–3 messages). It includes local delivery, so `kerio.smtp.messages.out` does not measure mail
  leaving the server. On a server that delivers straight to recipient MX (`relay.count` = 0), external delivery is `mx.count`

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

`howToStart` is a **string**, observed values `Automatic` / `Manual` (a service's
start type in Kerio). The service-discovery LLD emits it as `{#STARTTYPE}`
alongside `{#SERVICE}`. The "service is not running" trigger is gated with
`… and "{#STARTTYPE}"="Automatic"`, so Manual-start services (stopped on purpose)
keep a status item but never alert, and no per-host exclude list is needed.

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
- Works with the **Auditor role**. The method is `getFullStatus`; an earlier attempt with `ProductRegistration.get` failed

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

## Methods added in 1.1.0 — verified 2026-11-25 under Auditor (Kerio 10.0.8, three servers)

### Batch.run
```json
{"method": "Batch.run", "params": {"commandList": [{"method": "Server.getVersion", "params": {}}, {"method": "Queue.get", "params": {...}}]}}
```
`result` is an array in command order; each element is `{"result": ...}` or `{"error": {...}}`.
Kerio answers every request with `Connection: Close`, so batching saves a full connection setup per method.

### Server.getServerTime
`result.info = {"timezoneOffset": 180, "startTime": <unix>, "currentTime": <unix>}`.
Server local time = UTC + `timezoneOffset` minutes. Queue and log timestamps are server local time without a zone.

### Queue.get
```json
{"method": "Queue.get", "params": {"query": {"start": 0, "limit": 500, "orderBy": [{"columnName": "creationTime", "direction": "Asc"}]}}}
```
`result = {"list": [...], "totalItems": N, "volume": {...}}`, entry:
`{"id", "creationTime": "YYYY-MM-DD HH:MM", "nextTry": "YYYY-MM-DD HH:MM", "messageSize", "from", "to", "status": "4.4.1 Cannot connect to host", "authSender", "senderIp"}`.
Entries carry customer addresses: the template returns aggregates only.
`status` is the only error field: there is no remote host or attempt count. `4.4.1 Cannot connect to host` looks the
same for a dead recipient server and for a blocked outbound path. A DNS failure in Kerio is `5.5.4 Cannot find hostname
in DNS`, a permanent error: the message leaves the queue, so the stuck counters never see it.

### Logs.get
```json
{"method": "Logs.get", "params": {"logName": "mail", "fromLine": 0, "countLines": 1}}
```
`result = {"viewport": [{"content": "[25/Nov/2026 21:51:04] Recv: ...", "highlight": ""}], "totalItems": N}`.
The window starts at `fromLine` and goes forward: the tail is `fromLine = totalItems - count`.
`Recv` fields in order: `Queue-ID, Service, From, To, Size, Sender-Host, [User], [SSL], [Subject], [Msg-Id]`;
`User` only for authenticated sessions; `Sender-Host` is the PTR name or the IP when there is none.
`From`, `To` and `Subject` are sender-controlled.

### Domains.get (names)
```json
{"method": "Domains.get", "params": {"query": {"fields": ["name"], "start": 0, "limit": 1000}}}
```
`result.list = [{"name": "example.com"}, ...]`.

### Smtp.get
`retryInterval`, `bounceInterval`, `warningInterval` as `{"value": 3, "units": "Days"}`; also `verifyClientRDnsEntry`,
`blockUnknownDns`. The fields may sit under `result.server` (Batch.run) or directly in `result`.

`relayControl = {"isRestricted": true, "ipAddressGroupName": "Local clients", "ipAddressGroupId": "keriodb://ipaddressgroup/<uuid>", "authenticateOutgoing": true, ...}`.
`isRestricted` false means relay for everyone (open relay). With relay restricted to authenticated users only,
`ipAddressGroupName` is empty. Entries of the relay group: `IpAddressGroups.get` rows whose `groupId` equals
`ipAddressGroupId`.

### IpAddressGroups.get
```json
{"method": "IpAddressGroups.get", "params": {"query": {"start": 0, "limit": 1000}}}
```
`result.list` entries: `groupName`, `type` (`Host` / `Network`), `enabled`, `host`, `addr1`, `addr2`, `description`.

---

## NOT AVAILABLE with Auditor role

| Method | Error | Reason |
|--------|-------|--------|
| `SystemHealth.get` | `-32602 Invalid params` | Always fails regardless of params. Likely requires Admin role or is not implemented in this Kerio Connect version. CPU/memory/swap NOT available via API. |
| `ProductRegistration.get` | `-32602 Invalid params` | Wrong method name. Use `ProductRegistration.getFullStatus` instead — that works with Auditor role. |
| `Domains.get` (storage fields) | `1000 internal database error` | Per-domain storage NOT available with Auditor. `Domains.get` with `fields: ["name"]` works (see below). |
| `MessageQueue.get` / `Queue.getMessages` | Timeout | These methods hang. `Queue.get` works (see below); the earlier timeout was a slow server, not the role. |

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
| `kerio.queue.oldest.age` | `$.oldest_age` of `kerio.queue.raw` | Numeric | s | computed in JS |
| `kerio.queue.stuck` / `kerio.queue.stuck.domains` | `$.stuck` / `$.stuck_domains` of `kerio.queue.raw` | Numeric | | computed in JS |
| `kerio.relay.unauth.count` / `.truncated` | `$.count` / `$.truncated` of `kerio.relay.unauth` | Numeric | | computed in JS |
| `kerio.relay.restricted` | `$.restricted` of `kerio.relay.unauth` | Numeric | | 1 restricted, 0 open relay |
| `kerio.relay.group.entries` | `$.group_entries` of `kerio.relay.unauth` | Text | | sorted `"<type> <address>"` list |
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
| `kerio.service.status[{#SERVICE}]` | `$.services[?(@.name=="{#SERVICE}")].isRunning.first()` | Numeric | | boolean → needs "Boolean to decimal" preprocessing; LLD also emits `{#STARTTYPE}` (= `howToStart`) used to gate the trigger to Automatic services |
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
