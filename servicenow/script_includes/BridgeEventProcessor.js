// Script Include name: BridgeEventProcessor; Accessible from: This application scope only.
// Replace x_2226838_servic_0 with the scope assigned to YOUR app before creating records.
var BridgeEventProcessor = Class.create();
BridgeEventProcessor.prototype = {
    initialize: function () {},

    process: function (data) {
        var fields = ['event_id', 'source', 'service_key', 'outage_id', 'state', 'observed_at'];
        if (!data || typeof data !== 'object') throw new Error('JSON object required');
        for (var i = 0; i < fields.length; i++) {
            if (typeof data[fields[i]] !== 'string' || !data[fields[i]] || data[fields[i]].length > 128)
                throw new Error('Invalid ' + fields[i]);
        }
        if (data.source !== 'url_response' || ['DOWN', 'UP'].indexOf(data.state) === -1)
            throw new Error('Invalid source or state');
        if (data.service_key.length > 40 || data.outage_id.length > 40)
            throw new Error('service_key and outage_id must be at most 40 chars');
        if (!/^\d{4}-\d\d-\d\dT/.test(data.observed_at))
            throw new Error('observed_at must be an ISO timestamp');

        var events = new GlideRecord('x_2226838_servic_0_monitor_event');
        events.addQuery('external_id', data.event_id);
        events.query();
        if (events.next()) return { status: 'duplicate_delivery', event: events.getUniqueValue(),
            incident: String(events.incident) };

        var service = new GlideRecord('x_2226838_servic_0_monitored_service');
        service.addQuery('service_key', data.service_key);
        service.addQuery('active', true);
        service.query();
        if (!service.next()) throw new Error('Unknown or inactive service_key');

        var correlation = 'servicebridge:' + data.service_key + ':' + data.outage_id;
        var incident = new GlideRecord('incident');
        incident.addQuery('correlation_id', correlation);
        incident.orderByDesc('sys_created_on');
        incident.setLimit(1);
        incident.query();
        var found = incident.next();
        var result;
        if (data.state === 'DOWN') {
            if (!found) {
                incident.initialize();
                incident.short_description = 'Website unavailable: ' + String(service.name);
                incident.description = 'Url Response observed a service outage. Service key: ' + data.service_key;
                incident.correlation_id = correlation;
                incident.contact_type = 'monitoring'; // Remove if not present in your instance.
                incident.impact = 2;
                incident.urgency = 1;
                if (!service.assignment_group.nil()) incident.assignment_group = String(service.assignment_group);
                if (!service.cmdb_ci.nil()) incident.cmdb_ci = String(service.cmdb_ci);
                var incidentId = incident.insert();
                if (!incidentId) throw new Error('Failed to create incident: ' + incident.getLastErrorMessage());
                result = 'created';
            } else {
                incident.work_notes = 'Additional DOWN observation from Url Response: ' + data.event_id;
                incident.update();
                incidentId = incident.getUniqueValue();
                result = 'updated';
            }
        } else {
            incidentId = found ? incident.getUniqueValue() : '';
            if (found) {
                incident.work_notes = 'Url Response reports recovery at ' + data.observed_at +
                    '. Agent must verify before resolution.';
                incident.update();
                result = 'recovery_recorded';
            } else result = 'recovery_without_incident';
        }

        // Record a processed delivery; create a unique index on external_id in the table dictionary.
        var log = new GlideRecord('x_2226838_servic_0_monitor_event');
        log.initialize();
        log.external_id = data.event_id;
        log.service_key = data.service_key;
        log.outage_id = data.outage_id;
        log.event_type = data.state;
        log.observed_at = data.observed_at;
        log.processing_state = result;
        log.raw_json = JSON.stringify(data);
        if (incidentId) log.incident = incidentId;
        var eventId = log.insert();
        if (!eventId) throw new Error('Failed to save delivery record');
        return { status: result, event: eventId, incident: incidentId };
    },

    type: 'BridgeEventProcessor'
};
