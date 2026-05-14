// lld_services.js - Zabbix Script item for service LLD (Duktape engine)
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
    if (result.error) throw result.error.message;
    if (method === 'Session.login') {
        var headers = http.getHeaders ? http.getHeaders() : {};
        var sc = headers['set-cookie'] || headers['Set-Cookie'] || '';
        if (sc) cookie = sc.split(';')[0];
    }
    return result.result;
}

try {
    var loginResult = apiCall('Session.login', {
        userName: params.username,
        password: params.password,
        application: { name: 'Zabbix LLD', vendor: 'Zabbix', version: '7.0' }
    });
    token = loginResult.token;

    var svcs = apiCall('Services.get');
    try { apiCall('Session.logout'); } catch (e) {}

    var list = svcs.services || [];
    var out = [];
    for (var i = 0; i < list.length; i++) {
        out.push({ '{#SERVICE}': list[i].name });
    }
    return JSON.stringify(out);
} catch (e) {
    try { apiCall('Session.logout'); } catch (x) {}
    throw e;
}
