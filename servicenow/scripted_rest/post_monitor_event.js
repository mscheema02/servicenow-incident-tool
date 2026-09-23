// REST API record: ServiceBridge Monitoring; API ID: servicebridge; resource POST /monitor/events.
// Check "Requires authentication" on the API and resource. Assign x_msc_servicebridge.integration to the integration user.
(function process(request, response) {
    if (!gs.hasRole('x_2226838_servic_0.integration')) {
        response.setStatus(403);
        response.setBody({ error: 'integration role required' });
        return;
    }
    try {
        var input = request.body.data;
        var result = new BridgeEventProcessor().process(input);
        response.setStatus(result.status === 'created' ? 201 : 200);
        response.setBody(result);
    } catch (error) {
        // Do not echo request payload, credentials, or stack traces to callers.
        gs.error('ServiceBridge monitoring event failed: ' + String(error));
        response.setStatus(400);
        response.setBody({ error: String(error) });
    }
})(request, response);
