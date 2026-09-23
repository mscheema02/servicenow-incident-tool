# ServiceBridge Monitor Dashboard

A Bloomberg terminal-style web UI for sending monitoring events to ServiceNow.

## Features

- **Real-time stats:** Services up/down, events sent, success/failure counts
- **Service monitoring:** Visual status of all monitored services
- **Event transmission:** Send DOWN/UP events to ServiceNow
- **Event log:** Recent events with transmission status
- **Auto-refresh:** Dashboard updates every 5 seconds

## Quick Start

### 1. Install dependencies

```powershell
cd F:\ServiceNow\Projects\servicebridge-complete-starter\servicebridge
uv sync
```

### 2. Run the dashboard (local testing)

```powershell
uv run python -m servicebridge_ui.app
```

Open your browser to:

```
http://127.0.0.1:8080
```

### 3. Configure ServiceNow connection

Set environment variables before running:

```powershell
$env:SERVICEBRIDGE_NOW_URL = "https://YOUR-INSTANCE.service-now.com/api/YOUR_SCOPE/servicebridge/monitor/events"
$env:SERVICEBRIDGE_NOW_USER = "servicebridge.integration"
$env:SERVICEBRIDGE_NOW_PASSWORD = "YOUR_SECRET"

uv run python -m servicebridge_ui.app
```

How to get those values (do not use `admin`):

1. Request a PDI at [developer.servicenow.com](https://developer.servicenow.com). If asked **Australia** or **Zurich**, choose **Australia** (latest). The names are version names, not locations.
2. Log in. The Australia homepage often says **Build anywhere with Build Agent**. There is no left filter navigator. Click **All** (top-left, next to Favorites).
3. Search `Users` or type `sys_user.list`, then create user `servicebridge.integration` and set its password.
4. Copy your instance host from the browser, for example `https://devXXXXX.service-now.com`.
5. After you create the scoped app and Scripted REST API, `YOUR_SCOPE` is the app scope (not `x_msc_servicebridge`).

The video shot list is [DEMO_GUIDE.md](DEMO_GUIDE.md). Setup notes that are not part of this demo live in `F:\ServiceNow\Projects\servicebridge-outside-demo\docs`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICEBRIDGE_NOW_URL` | (none) | ServiceNow Scripted REST API endpoint |
| `SERVICEBRIDGE_NOW_USER` | (none) | ServiceNow integration user |
| `SERVICEBRIDGE_NOW_PASSWORD` | (none) | ServiceNow user password |
| `SERVICEBRIDGE_UI_HOST` | `127.0.0.1` | Dashboard bind address |
| `SERVICEBRIDGE_UI_PORT` | `8080` | Dashboard port |
| `SERVICEBRIDGE_UI_DB` | `servicebridge_ui.sqlite3` | Local database path |
| `SERVICEBRIDGE_UI_DEBUG` | `false` | Enable Flask debug mode |

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ ▶ SERVICEBRIDGE MONITOR TERMINAL              2026-09-20 UTC   │
├─────────────────────────────────────────────────────────────────┤
│ SERVICES UP │ SERVICES DOWN │ EVENTS │ SUCCESS │ FAIL │ PENDING │
│      3      │       1       │   42   │    38   │   2  │    2    │
├───────────────────────────────┬─────────────────────────────────┤
│ MONITORED SERVICES            │ SEND EVENT                      │
│                               │                                 │
│ ● booking-site    Booking...  │ SERVICE:  [booking-site ▼]      │
│ ○ help-center     Help Cen... │ OUTAGE:   [____________]        │
│ ● payment-api     Payment...  │ STATE:    [▼ DOWN] [▲ UP]       │
│                               │                                 │
│                               │ [ TRANSMIT EVENT ]              │
├───────────────────────────────┴─────────────────────────────────┤
│ EVENT LOG                                                       │
│ 14:32:01  DOWN  booking-site  outage-abc123  OK 201             │
│ 14:31:45  UP    payment-api   outage-def456  OK 200             │
│ 14:30:12  DOWN  payment-api   outage-def456  OK 201             │
├─────────────────────────────────────────────────────────────────┤
│ SERVICEBRIDGE v1.0    SERVICENOW: dev12345.service-now.com      │
└─────────────────────────────────────────────────────────────────┘
```

## Usage

### Sending a DOWN event

1. Select a service from the dropdown
2. Optionally enter an outage ID (auto-generated if blank)
3. Click **▼ DOWN** button
4. Click **TRANSMIT EVENT**

The event is sent to ServiceNow, which:
- Creates a new incident if this is the first DOWN for the outage
- Updates the existing incident if one exists for this outage ID

### Sending an UP event

1. Select the same service
2. Enter the same outage ID used for the DOWN
3. Click **▲ UP** button
4. Click **TRANSMIT EVENT**

ServiceNow adds a recovery work note to the incident. The incident remains open for agent verification.

### Monitoring status indicators

- **●** (solid circle, red) — Service is DOWN
- **○** (hollow circle, green) — Service is UP
- Stats show count of DOWN events (↓) and UP events (↑) per service

## API Endpoints

The dashboard exposes these REST endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Dashboard HTML |
| GET | `/api/config` | Connection configuration status |
| GET | `/api/services` | List monitored services |
| GET | `/api/events?limit=N` | Recent events |
| GET | `/api/stats` | Dashboard statistics |
| POST | `/api/send` | Send event to ServiceNow |
| POST | `/api/services` | Add a new service |

### Send event payload

```json
{
  "service_key": "booking-site",
  "outage_id": "outage-12345",
  "state": "DOWN"
}
```

### Send event response

```json
{
  "event": {
    "event_id": "uuid",
    "source": "url_response",
    "service_key": "booking-site",
    "outage_id": "outage-12345",
    "state": "DOWN",
    "observed_at": "2026-09-20T14:30:00+00:00"
  },
  "http_status": 201,
  "response": {"status": "created", "incident": "INC0012345"},
  "success": true
}
```

## Local Database

The dashboard stores events locally in SQLite for history and statistics. This is independent of ServiceNow storage.

Default location:

```
servicebridge_ui.sqlite3
```

Tables:
- `events` — All transmitted events with status
- `services` — Monitored services and current state

## Run the dashboard

```powershell
cd F:\ServiceNow\Projects\servicebridge-complete-starter\servicebridge
uv run python -m servicebridge_ui.app
```

Open **http://127.0.0.1:8080**. The identity mock is not part of this demo.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| F5 | Refresh all data |

## Troubleshooting

### "SERVICENOW: NOT CONFIGURED"

Set the three environment variables:
- `SERVICEBRIDGE_NOW_URL`
- `SERVICEBRIDGE_NOW_USER`
- `SERVICEBRIDGE_NOW_PASSWORD`

If you just opened the PDI and cannot find Users: click **All** in the top-left of the Australia UI, then `sys_user.list`.

### "TRANSMISSION FAILED"

Check:
1. ServiceNow URL uses HTTPS
2. Integration user has the correct role
3. Scripted REST API is configured and accessible
4. Service key exists in ServiceNow's Monitored Service table

### Events succeed locally but fail in ServiceNow

The dashboard records success/failure based on HTTP status. Check:
- ServiceNow application logs
- Event processor Script Include
- Table ACLs for the integration user
