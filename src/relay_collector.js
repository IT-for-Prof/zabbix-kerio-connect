// Counts unauthenticated SMTP from private addresses to external recipients in the last hour of
// the mail log: a sign of SNAT on the path to Kerio, which makes "Local clients" an open relay.
var PRIVATE = /^(10(\.\d{1,3}){3}|172\.(1[6-9]|2\d|3[01])(\.\d{1,3}){2}|192\.168(\.\d{1,3}){2})$/;
// Recv fields: Queue-ID, Service, From, To, Size, Sender-Host, [User], [SSL], [Subject], [Msg-Id].
var SENDER = /, Size: \d+, Sender-Host: ([^,]+)(, User: [^,]*)?(?=, SSL: |, Subject: |, Msg-Id: |$)/g;
var WINDOW = 3600; // equals the item delay (tests/test_templates.py): runs neither overlap nor leave gaps

// From, To and Subject are sender-controlled and may imitate the Size/Sender-Host run, so every
// candidate counts: an injected fake can raise a false alarm but cannot hide the real sender.
function unauthRelayHost(line, localDomains) {
    var i = line.indexOf('] Recv: ');
    if (i < 0) return null;
    var rest = line.substr(i + 8);
    if (!/^Queue-ID: \S+, Service: SMTP, From: /.test(rest)) return null;
    var to = rest.indexOf(', To: ');
    if (to < 0) return null;
    SENDER.lastIndex = 0;
    var m, first = -1, host = null;
    while ((m = SENDER.exec(rest)) !== null) {
        if (first < 0 && m.index > to) first = m.index;
        if (!m[2] && PRIVATE.test(m[1])) host = m[1];
    }
    if (host === null || first < 0) return null;
    var re = /@([^<>@\s,]+)>/g, d, external = false;
    var recipients = rest.substring(to, first);
    while ((d = re.exec(recipients)) !== null) {
        if (!localDomains[d[1].toLowerCase()]) external = true;
    }
    return external ? host : null;
}

function relayStats(lines, now, offsetMinutes, localDomains, allow, truncatable) {
    var since = now - WINDOW, count = 0, oldest = null;
    for (var i = 0; i < lines.length; i++) {
        var text = lines[i].content || '';
        var t = serverTime(text.substr(1), offsetMinutes);
        if (t === null) continue;
        if (oldest === null) oldest = t;
        if (t <= since) continue;
        var host = unauthRelayHost(text, localDomains);
        if (host !== null && !(allow && allow.test(host))) count++;
    }
    return { count: count, truncated: truncatable && oldest !== null && oldest > since ? 1 : 0 };
}

return withSession('Zabbix Relay', function () {
    var r = batchCall([
        { method: 'Server.getServerTime', params: {} },
        { method: 'Domains.get', params: { query: { fields: ['name'], start: 0, limit: 1000 } } },
        { method: 'Logs.get', params: { logName: 'mail', fromLine: 0, countLines: 1 } }
    ]);
    var local = {}, domains = r[1].list || [];
    for (var i = 0; i < domains.length; i++) local[String(domains[i].name).toLowerCase()] = true;
    var limit = parseInt(params.lines, 10), total = r[2].totalItems || 0;
    var view = total ? apiCall('Logs.get', { logName: 'mail', fromLine: Math.max(0, total - limit), countLines: limit }).viewport || [] : [];
    var allow = params.allow ? new RegExp(params.allow) : null;
    return JSON.stringify(relayStats(view, r[0].info.currentTime, r[0].info.timezoneOffset, local, allow, total > limit));
});
