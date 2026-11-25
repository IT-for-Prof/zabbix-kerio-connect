// queue_collector.js - Zabbix Script item (Duktape engine), prefixed with kerio_api.js.
// Returns aggregates only: queue entries carry customer addresses, which must not reach history.
function recipientDomains(to) {
    var out = [];
    var parts = String(to || '').split(/[,;\s]+/);
    for (var i = 0; i < parts.length; i++) {
        var at = parts[i].lastIndexOf('@');
        if (at >= 0) out.push(parts[i].substr(at + 1).replace(/[<>]/g, '').toLowerCase());
    }
    return out;
}

function queueStats(list, now, offsetMinutes, stuckAge) {
    var oldest = 0, stuck = 0, domains = {}, domainCount = 0;
    for (var i = 0; i < list.length; i++) {
        var created = serverTime(list[i].creationTime || '', offsetMinutes);
        if (created === null) continue;
        var age = Math.max(0, now - created);
        if (age > oldest) oldest = age;
        if (!/^4\./.test(list[i].status || '') || age <= stuckAge) continue;
        stuck++;
        var d = recipientDomains(list[i].to);
        for (var j = 0; j < d.length; j++) {
            if (!domains[d[j]]) { domains[d[j]] = true; domainCount++; }
        }
    }
    return { oldest_age: oldest, stuck: stuck, stuck_domains: domainCount };
}

return withSession('Zabbix Queue', function () {
    var r = batchCall([
        { method: 'Server.getServerTime', params: {} },
        // shortcut: the oldest 500 entries only; a bigger queue already fires the stuck-domains trigger.
        { method: 'Queue.get', params: { query: { start: 0, limit: 500, orderBy: [{ columnName: 'creationTime', direction: 'Asc' }] } } }
    ]);
    return JSON.stringify(queueStats(r[1].list || [], r[0].info.currentTime, r[0].info.timezoneOffset, seconds(params.stuck_age)));
});
