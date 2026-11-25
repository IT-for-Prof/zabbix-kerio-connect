return withSession('Zabbix LLD', function () {
    var list = apiCall('Services.get').services || [];
    var out = [];
    for (var i = 0; i < list.length; i++) {
        out.push({ '{#SERVICE}': list[i].name, '{#STARTTYPE}': list[i].howToStart || '' });
    }
    return JSON.stringify(out);
});
