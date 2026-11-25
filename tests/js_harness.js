// Runs a composed Zabbix Script item in node with a stub HttpRequest.
// argv: script path, item value (JSON), spec (JSON: method -> result, or {"__error": msg}).
var fs = require('fs');
var src = fs.readFileSync(process.argv[2], 'utf8');
var spec = JSON.parse(process.argv[4]);
var requests = [];

function answer(method, params) {
    var a = spec[method];
    if (a && a.__error) return { error: { code: 1, message: a.__error } };
    if (method === 'Logs.get') {
        var lines = a || [];
        if (params.countLines === 1 && params.fromLine === 0) return { result: { totalItems: lines.length, viewport: lines.slice(0, 1) } };
        return { result: { totalItems: lines.length, viewport: lines.slice(params.fromLine, params.fromLine + params.countLines) } };
    }
    return { result: a === undefined ? {} : a };
}

function HttpRequest() {}
HttpRequest.prototype.addHeader = function () {};
HttpRequest.prototype.getStatus = function () { return spec.__status || 200; };
HttpRequest.prototype.getHeaders = function () { return {}; };
HttpRequest.prototype.post = function (url, body) {
    var b = JSON.parse(body);
    requests.push(b.method);
    if (b.method === 'Batch.run') {
        return JSON.stringify({ result: b.params.commandList.map(function (c) { return answer(c.method, c.params); }) });
    }
    return JSON.stringify(answer(b.method, b.params || {}));
};

var out = { requests: requests };
try { out.result = new Function('value', 'HttpRequest', src)(process.argv[3], HttpRequest); }
catch (e) { out.error = String(e); }
process.stdout.write(JSON.stringify(out));
