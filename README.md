# ServiceBridge

A Flask client on localhost posts monitoring JSON to a ServiceNow Scripted REST API. A scoped Script Include validates the payload, writes a Monitor Event receipt, and creates or updates a native `incident` row keyed by `correlation_id`. Recovery (`UP`) appends work notes and does not resolve the Incident.

**What this helped me learn:** inbound Scripted REST with role checks, scoped Script Includes and `GlideRecord` against both custom tables and `incident`, delivery idempotency via `event_id` versus outage correlation via `outage_id`, and keeping the external UI as a pure HTTP client so Incident writes stay on the platform.

How the pieces connect: [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md).

![ServiceBridge dashboard. Box 1 is monitored services, box 2 is send event, box 3 is the event log, box 4 is the ServiceNow footer.](docs/dashboard.jpg)

1. **Monitored services.** Local SQLite view of each `service_key` and last observed DOWN/UP. Not the ServiceNow Incident.
2. **Send event.** Builds the JSON body (`event_id`, `source`, `service_key`, `outage_id`, `state`, `observed_at`) and POSTs it with Basic auth. The line under the button is the HTTP status and processor `status` from ServiceNow.
3. **Event log.** Local history of each POST: timestamp, state, service, outage id, OK/FAIL and status code.
4. **ServiceNow footer.** Configured Scripted REST host. **CONNECTED** means URL/user/password env vars are set; a successful transmit proves the call.

## Demo

[![Demo Video](https://img.youtube.com/vi/UHHJGj-Bgto/0.jpg)](https://youtu.be/UHHJGj-Bgto)

**Demo:** https://youtu.be/UHHJGj-Bgto

## Run the dashboard

Requires [uv](https://docs.astral.sh/uv/).

```powershell
cd servicebridge
uv sync
$env:SERVICEBRIDGE_NOW_URL = "https://YOUR_INSTANCE.service-now.com/api/YOUR_SCOPE/servicebridge/monitor/events"
$env:SERVICEBRIDGE_NOW_USER = "servicebridge.integration"
$env:SERVICEBRIDGE_NOW_PASSWORD = "YOUR_PASSWORD"
uv run python -m servicebridge_ui.app
```

Open **http://127.0.0.1:8080**.

The variable names are listed in `.env.example`. Keep the real instance URL and password in `LOCAL.md` on your machine. That file is gitignored. Do not commit it, and do not paste the password into this README.

Run the command from this directory, not from `servicebridge_ui/`.

## What is in this repository

```
servicebridge/
├── docs/HOW_IT_WORKS.md        # Integration path and processor behavior
├── docs/UI_GUIDE.md            # Dashboard layout
├── servicebridge_ui/           # Local dashboard
└── servicenow/
    ├── scripted_rest/post_monitor_event.js
    └── script_includes/BridgeEventProcessor.js
```

The dashboard sends JSON. It does not insert the Incident itself. `post_monitor_event.js` checks the integration role and calls `BridgeEventProcessor`. That class writes the platform Incident table. Table names in those scripts use the scoped app prefix from the developer instance.

The `servicenow/` files are the scripts installed on the instance. This repository is not an importable ServiceNow application.

## License

MIT. ServiceNow platform software is not included.
