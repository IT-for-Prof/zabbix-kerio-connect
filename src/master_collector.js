return withSession('Zabbix Monitoring', function () {
    var r = batchCall([
        { method: 'Statistics.get', params: {} },
        { method: 'Services.get', params: {} },
        { method: 'ProductRegistration.getFullStatus', params: {} },
        { method: 'Server.getVersion', params: {} }
    ]);
    return JSON.stringify({
        statistics: r[0].statistics || {},
        services: r[1].services || [],
        license: r[2].status || {},
        server: r[3] || {}
    });
});
