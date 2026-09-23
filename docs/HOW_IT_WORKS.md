# How ServiceBridge connects to ServiceNow

This document explains the integration path end to end: what the local dashboard sends, what ServiceNow receives, and how an Incident is created or updated.

## Architecture

```text
Local Flask dashboard (servicebridge_ui)
        |
        | HTTPS POST + Basic auth
        | Content-Type: application/json
        v
Scripted REST API
  /api/<scope>/servicebridge/monitor/events
        |
        | role check: <scope>.integration
        v
Script Include: BridgeEventProcessor.process(body)
        |
        +-- validate payload
        +-- reject duplicate event_id (Monitor Event.external_id)
        +-- resolve Monitored Service by service_key
        +-- correlate Incident by correlation_id
        |
        v
Native ITSM Incident  +  scoped Monitor Event receipt
```

The dashboard never inserts into `incident`. It is an HTTP client. All platform writes happen inside the scoped app on the instance.

## Authentication and endpoint

| Piece | Detail |
|-------|--------|
| Transport | HTTPS only |
| Auth | HTTP Basic, user `servicebridge.integration` |
| Role required | `<scope>.integration` (checked in the Scripted REST resource) |
| Method / path | `POST /api/<scope>/servicebridge/monitor/events` |
| Body | JSON object (see contract below) |

Environment variables used by the dashboard:

- `SERVICEBRIDGE_NOW_URL` — full Scripted REST URL
- `SERVICEBRIDGE_NOW_USER` — integration user
- `SERVICEBRIDGE_NOW_PASSWORD` — that user's password

## JSON contract

Each transmit builds a body like:

```json
{
  "event_id": "uuid-per-delivery",
  "source": "url_response",
  "service_key": "account-portal",
  "outage_id": "interview-001",
  "state": "DOWN",
  "observed_at": "2026-09-23T18:00:00.000Z"
}
```

| Field | Meaning |
|-------|---------|
| `event_id` | One HTTP delivery. Unique. Used for idempotent receipts. |
| `source` | Must be `url_response`. |
| `service_key` | Must match an active row in Monitored Service. |
| `outage_id` | Groups deliveries into one outage. Several `event_id`s can share one `outage_id`. |
| `state` | `DOWN` or `UP` only. |
| `observed_at` | ISO-8601 timestamp string. |

## Scripted REST resource

Source: `servicenow/scripted_rest/post_monitor_event.js`

1. Reject callers without the integration role → HTTP **403**.
2. Pass `request.body.data` to `new BridgeEventProcessor().process(input)`.
3. Return **201** when `status === 'created'`, otherwise **200**.
4. On processor exceptions, return **400** with an error string (no stack trace).

## BridgeEventProcessor

Source: `servicenow/script_includes/BridgeEventProcessor.js`

Processing order:

1. **Validate** required string fields, `source`, `state`, length limits, and timestamp shape.
2. **Duplicate delivery** — query Monitor Event where `external_id == event_id`. If found, return `duplicate_delivery` and the existing incident sys_id. No second receipt, no second Incident.
3. **Service lookup** — active Monitored Service with matching `service_key`. Unknown or inactive → error.
4. **Correlation** — build  
   `correlation_id = servicebridge:<service_key>:<outage_id>`  
   and query the platform `incident` table for that value.
5. **DOWN**
   - No matching Incident → `insert()` a native Incident (`short_description`, `correlation_id`, impact/urgency, optional assignment group / CMDB CI). Status: `created`.
   - Matching Incident → append a work note for the new observation. Status: `updated`.
6. **UP**
   - Matching Incident → work note that recovery was observed; **do not** set Incident state to Resolved. Status: `recovery_recorded`.
   - No Incident → `recovery_without_incident`.
7. **Receipt** — insert a Monitor Event row (`external_id`, keys, `event_type`, `processing_state`, `raw_json`, reference to Incident).

## Platform objects involved

| Object | Role |
|--------|------|
| Scripted REST API `servicebridge` | Inbound surface for the monitor |
| Script Include `BridgeEventProcessor` | Validation, correlation, Incident write |
| Table Monitored Service | Allow-list of `service_key` values |
| Table Monitor Event | Integration receipt / audit log per delivery |
| Table `incident` | Native ITSM ticket (not a custom ticket table) |

## HTTP results the dashboard shows

| HTTP | Typical `status` in body | Meaning |
|------|--------------------------|---------|
| 201 | `created` | First DOWN for that correlation id; Incident inserted |
| 200 | `updated` | Another DOWN for the same outage; same Incident |
| 200 | `recovery_recorded` | UP recorded on the existing Incident |
| 200 | `duplicate_delivery` | Same `event_id` sent again |
| 403 | — | Caller missing integration role |
| 400 | — | Validation or processing failure |

## Design choices

- **Native Incident** — reuse ITSM instead of a custom ticket table.
- **`event_id` vs `outage_id`** — delivery idempotency vs outage correlation.
- **UP does not resolve** — monitor recovery is evidence; an agent closes the Incident.
- **Scoped Script Include** — REST stays thin; business logic lives in one class.

## Limits

- Two first-time DOWN posts for the same outage at the same instant can still create two Incidents (no unique DB lock on the correlation id in this version).
- Processor failures are returned as HTTP 400; finer status codes are not implemented yet.
- This is a custom REST → ITSM path. It is not ServiceNow ITOM Event Management.
