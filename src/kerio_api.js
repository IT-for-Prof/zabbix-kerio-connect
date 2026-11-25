// kerio_api.js - shared Kerio JSON-RPC client (Duktape engine). tools/sync_template_js.py
// prepends it to every collector, because a Zabbix Script item cannot import code.
var params = JSON.parse(value);
var baseUrl = params.scheme + '://' + params.host + ':' + params.port + '/admin/api/jsonrpc/';
var reqId = 0;
var token = null;
var cookie = null;

function apiCall(method, callParams) {
    reqId++;
    var body = { jsonrpc: '2.0', id: reqId, method: method };
    if (callParams) body.params = callParams;
    if (token) body.token = token;

    var http = new HttpRequest();
    http.addHeader('Content-Type: application/json');
    http.addHeader('Accept: application/json');
    if (cookie) http.addHeader('Cookie: ' + cookie);
    if (token) http.addHeader('X-Token: ' + token);

    var resp = http.post(baseUrl, JSON.stringify(body));
    var status = http.getStatus();
    if (status < 200 || status >= 300) throw 'HTTP ' + status + ' on ' + method;

    var result = JSON.parse(resp);
    if (result.error) throw method + ' error: ' + result.error.message;
    if (method === 'Session.login') {
        var headers = http.getHeaders ? http.getHeaders() : {};
        var sc = headers['set-cookie'] || headers['Set-Cookie'] || '';
        if (sc) cookie = sc.split(';')[0];
    }
    return result.result;
}

// Several methods in one HTTP request: Kerio closes the connection after every
// response, so each request pays the full connection setup.
function batchCall(commands) {
    var results = apiCall('Batch.run', { commandList: commands });
    var out = [];
    for (var i = 0; i < commands.length; i++) {
        var r = results[i] || {};
        if (r.error) throw commands[i].method + ' error: ' + r.error.message;
        out.push(r.result || {});
    }
    return out;
}

function withSession(appName, body) {
    token = apiCall('Session.login', {
        userName: params.username,
        password: params.password,
        application: { name: appName, vendor: 'Zabbix', version: '7.0' }
    }).token;
    try {
        return body();
    } finally {
        try { apiCall('Session.logout'); } catch (e) {}
    }
}

// 'YYYY-MM-DD HH:MM[:SS]' or 'DD/Mon/YYYY HH:MM:SS' in server local time -> unix seconds.
var MONTHS = { Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5, Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11 };
function serverTime(text, offsetMinutes) {
    var m = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})(?::(\d{2}))?/.exec(text);
    var utc;
    if (m) utc = Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0));
    else {
        m = /^(\d{2})\/(\w{3})\/(\d{4}) (\d{2}):(\d{2}):(\d{2})/.exec(text);
        if (!m || !(m[2] in MONTHS)) return null;
        utc = Date.UTC(+m[3], MONTHS[m[2]], +m[1], +m[4], +m[5], +m[6]);
    }
    return utc / 1000 - offsetMinutes * 60;
}

// Zabbix time suffix ('90', '30m', '4h', '1d', '1w') -> seconds.
function seconds(text) {
    var m = /^\s*(\d+)\s*([smhdw]?)\s*$/.exec(String(text));
    if (!m) throw 'bad time value: ' + text;
    return +m[1] * { '': 1, s: 1, m: 60, h: 3600, d: 86400, w: 604800 }[m[2]];
}
