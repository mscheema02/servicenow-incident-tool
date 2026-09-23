# ServiceBridge video

Record one path only. Two systems. Do not open Lifecycle, Flow Designer, or the identity mock.

| Window | Where | What it is |
|--------|--------|------------|
| **Local** | Browser at `http://127.0.0.1:8080` | Your dashboard. It only sends JSON. |
| **ServiceNow** | Browser at `https://YOUR_INSTANCE.service-now.com` | The platform. Logged in as admin. This is where the Incident exists. |

Put the windows side by side if the screen is wide enough. Otherwise record Local, then switch to ServiceNow, then come back. Every shot below says which window.

Before you hit record, send nothing. If `interview-001` was already used, pick `interview-002` and use that same id in every shot.

The **OUTAGE ID** box on the local page **clears itself** after each successful transmit. Write the id down. You must type it again for shot 3 and shot 5.

Do not show `LOCAL.md`, passwords, the integration password, or the terminal if the password is visible in the command.

## Before the first shot

**Local.** If the page is not open:

```powershell
cd F:\ServiceNow\Projects\servicebridge-complete-starter\servicebridge
uv run python -m servicebridge_ui.app
```

The three `SERVICEBRIDGE_NOW_*` variables must already be set in that terminal. Open `http://127.0.0.1:8080`.

Check the local page before recording:

- Top right says **● CONNECTED**. That only means the URL and user are configured. The proof is the HTTP line you get after transmit.
- Footer contains `SERVICENOW:` and your instance host.
- **SEND EVENT** panel is on the right: **SERVICE**, **OUTAGE ID**, **▼ DOWN**, **▲ UP**, **TRANSMIT EVENT**.
- **▼ DOWN** is the selected state (it has the active style). If **▲ UP** is selected, click **▼ DOWN**.

**ServiceNow.** Stay on the homepage until shot 2. Australia UI: the top bar has **All**. There is no left navigator.

## Shot 1 — Local dashboard sends DOWN

**Window: Local only.** `http://127.0.0.1:8080`

Point at the address bar and say: this is my machine, not ServiceNow.

Then, in the **SEND EVENT** panel only:

1. **SERVICE** dropdown: `account-portal`.
2. **OUTAGE ID**: type `interview-001`. Leave it on screen long enough to read.
3. **STATE**: **▼ DOWN** is selected. Do not click **▲ UP**.
4. Click **TRANSMIT EVENT**. The button briefly says **TRANSMITTING...**

Highlight the line directly under the button. It must read:

```text
✓ EVENT TRANSMITTED
HTTP 201 | "created"
```

`201` and `"created"` mean ServiceNow inserted a new Incident. If you see `200` and `"updated"`, this outage id was already used. Stop, pick a new id, and re-record this shot.

Then highlight two other local facts. Do not switch windows yet.

- **MONITORED SERVICES** (left): the `account-portal` row shows a filled circle **●** and the word DOWN. This is the dashboard's own copy of the state. It is not the Incident.
- **EVENT LOG** (bottom): the newest row shows a time, **DOWN**, `account-portal`, `interview-001`, **OK 201**.

Say: the dashboard did not open an Incident screen. It posted JSON to ServiceNow. The next window is the only place the ticket exists.

The **OUTAGE ID** box is now empty. That is normal.

## Shot 2 — ServiceNow shows the new Incident

**Window: ServiceNow only.**

Paste this in the address bar:

```text
https://YOUR_INSTANCE.service-now.com/incident_list.do?sysparm_query=correlation_idSTARTSWITHservicebridge:
```

Highlight the filter breadcrumb at the top of the list: **Correlation ID starts with servicebridge:**

In the list, find the row whose **Short description** is `Website unavailable: Account Portal`. Click the **Number** (INC00…). Remember that number. Call it the Incident number for the rest of the video.

On the Incident form, point at these fields and no others:

| Field on the form | What the camera should read |
|-------------------|-----------------------------|
| Number | The INC number you just opened |
| Short description | `Website unavailable: Account Portal` |
| Correlation ID | `servicebridge:account-portal:interview-001` |
| State | New, or still open. Not Resolved, not Closed. |
| Impact | 2 - Medium |
| Urgency | 1 - High |

Scroll to **Activity** or **Notes**. Work notes should not yet say recovery. Do not click **Resolve** or **Close**.

Say: this row is the platform **Incident** table. The dashboard never inserted this row. Correlation ID is how a later event finds this same record: `servicebridge:` plus service `account-portal` plus outage `interview-001`.

## Shot 3 — Local dashboard sends a second DOWN for the same outage

**Window: Local only.** `http://127.0.0.1:8080`

The **OUTAGE ID** box is empty. Type `interview-001` again. If you leave it blank, the page invents a new outage id and ServiceNow will open a second Incident.

1. **SERVICE** is still `account-portal`.
2. **OUTAGE ID** is `interview-001`.
3. **▼ DOWN** is selected.
4. Click **TRANSMIT EVENT**.

Highlight the line under the button. It must read:

```text
✓ EVENT TRANSMITTED
HTTP 200 | "updated"
```

This is not another `201` / `"created"`. `200` and `"updated"` mean ServiceNow found the existing Incident and added a note.

Highlight the new **EVENT LOG** row: **DOWN**, `account-portal`, `interview-001`, **OK 200**. The previous row is still there with **OK 201**. Two local rows, same outage id, different HTTP results.

Say: each click builds a new `event_id`. The outage id is the same, so it is a second observation of one outage, not a second ticket.

## Shot 4 — ServiceNow: same Incident, not a second one

**Window: ServiceNow only.**

Go back to the same list:

```text
https://YOUR_INSTANCE.service-now.com/incident_list.do?sysparm_query=correlation_id=servicebridge:account-portal:interview-001
```

Highlight the list. There is **one** row for that correlation id. The Number is the same INC number as shot 2.

Open it. Highlight:

- **Correlation ID** still `servicebridge:account-portal:interview-001`
- **State** still not Resolved
- **Work notes** (Activity): `Additional DOWN observation from Url Response:` followed by a long id

That long id is the second delivery's `event_id`. It will not match a field on the local form, because the local form does not show `event_id`. The **EVENT LOG** on the local page only shows state, service, outage id, and HTTP status.

Say: one Incident. Two deliveries. The work note is the second DOWN. I am not resolving it.

## Shot 5 — Local dashboard sends UP

**Window: Local only.**

1. **SERVICE**: `account-portal`.
2. Type **OUTAGE ID** `interview-001` again. The box was cleared.
3. Click **▲ UP** so that button is the selected one, not **▼ DOWN**.
4. Click **TRANSMIT EVENT**.

Highlight:

```text
✓ EVENT TRANSMITTED
HTTP 200 | "recovery_recorded"
```

Then highlight **MONITORED SERVICES**: `account-portal` now shows an empty circle **○** (the local page treats that as up).

Highlight the new **EVENT LOG** row: **UP**, `account-portal`, `interview-001`, **OK 200**.

Say: locally the monitor now says the site is up. That does not close the Incident. Next shot is the proof.

## Shot 6 — ServiceNow: recovery is a work note, Incident stays open

**Window: ServiceNow only.**

Reload the same Incident (same INC number). Do not open a different record.

Highlight, in this order:

1. **State** is still New or otherwise open. Point at it and say it is not Resolved.
2. **Work notes** newest entry: `Url Response reports recovery at` then a timestamp, then `Agent must verify before resolution.`
3. The older work note from shot 4 is still there (`Additional DOWN observation`).

Compare, out loud, to shot 5:

| Local page (shot 5) | This Incident (shot 6) |
|---------------------|------------------------|
| Service row shows up | State is still open |
| Log says **UP** and **OK 200** | Work notes quote the recovery and say an agent must verify |
| No Resolve button on the dashboard | You do not click Resolve |

Say: the monitor reported recovery. Closing the Incident is a person's decision. I am leaving it open.

## Shot 7 — ServiceNow: three Monitor Event rows, one Incident

**Window: ServiceNow only.**

Paste:

```text
https://YOUR_INSTANCE.service-now.com/x_2226838_servic_0_monitor_event_list.do?sysparm_query=outage_id=interview-001^ORDERBYDESCsys_created_on
```

Highlight the list. Three rows. Same **Outage ID** `interview-001`. Same **Incident** number as shots 2, 4, and 6.

Point across the rows:

| Event Type | Processing State | What it matches |
|------------|------------------|-----------------|
| DOWN | `created` | Shot 1, local **HTTP 201 \| "created"** |
| DOWN | `updated` | Shot 3, local **HTTP 200 \| "updated"** |
| UP | `recovery_recorded` | Shot 5, local **HTTP 200 \| "recovery_recorded"** |

**External ID** is different on every row. That is `event_id`, one per transmit. **Outage ID** is `interview-001` on all three. **Incident** is one number.

Open the `created` row. Highlight **Incident** (the reference) and **Raw JSON**. Raw JSON contains `"source":"url_response"`, `"service_key":"account-portal"`, `"outage_id":"interview-001"`, `"state":"DOWN"`. This is the payload the local page sent. The Incident form does not store that raw body. This table does.

Say: Monitor Event is the integration log. Incident is the ITSM ticket. Three logs, one ticket.

## Shot 8 — ServiceNow Studio: the API and the Script Include

**Window: ServiceNow only.** Do not go back to the local page.

1. Click **All**, type `studio`, open **System Applications > Studio**.
2. Open the **ServiceBridge** application.
3. Open Scripted REST resource **Monitor Events** (API **ServiceBridge Monitoring**, path `POST /monitor/events`).

Highlight these lines and nothing else:

- `gs.hasRole('x_2226838_servic_0.integration')` — the caller must be the integration user, not admin.
- `new BridgeEventProcessor().process(input)` — the REST script does not create the Incident itself.
- `response.setStatus(result.status === 'created' ? 201 : 200)` — this is why shot 1 was 201 and shots 3 and 5 were 200.

Say: the dashboard authenticates as `servicebridge.integration`. This resource checks that role, then hands the body to one class.

4. Open Script Include **BridgeEventProcessor**.

Highlight these three spots:

- The query on `x_2226838_servic_0_monitor_event` where `external_id` equals `event_id`. Say: a repeated delivery id returns `duplicate_delivery` and does not insert another log. The video did not repeat an event id. Each click was a new one.
- `var correlation = 'servicebridge:' + data.service_key + ':' + data.outage_id` and `new GlideRecord('incident')`. Say: same service and same outage id select the Incident you already opened.
- The `else` branch that sets `incident.work_notes` to the recovery sentence and does **not** set `incident.state`. Say: this is why shot 6 stayed open.

Do not scroll the whole file.

## What you say, mapped to the shot

| Shot | Window | Sentence |
|------|--------|----------|
| 1 | Local | The external system only sends JSON. It never inserts an Incident. |
| 2 | ServiceNow | The ticket is the platform Incident table. Correlation ID ties it to `account-portal` and `interview-001`. |
| 3 and 4 | Local, then ServiceNow | `event_id` is one delivery. `outage_id` is the outage. Two deliveries, one Incident. |
| 5 and 6 | Local, then ServiceNow | A monitor saying the site is back is evidence. An agent still closes the Incident. |
| 7 | ServiceNow | Monitor Event is the receipt. The Incident is the operational record. |
| 8 | ServiceNow | The REST resource checks the integration role and calls one Script Include. |

## One sentence if they ask about limits

- Two DOWN clicks at the exact same moment, both the first for that outage, can create two Incidents. The video shows the normal case: the second send happens after the first Incident exists.
- The integration user has the `itil` role so it can insert Incidents. A production design would use a narrower Incident ACL.
- This is not ITOM Event Management. There is no ITOM Event and no Alert. It is a REST integration into ITSM.

## Do not open in this video

- Lifecycle Request, Lifecycle Task, Flow Designer, Provision access
- `http://127.0.0.1:8088` (identity mock)
- Users, roles, passwords, `LOCAL.md`

## Already built — not this video

Lifecycle Request, Validate Lifecycle, Complete Lifecycle, flow **ServiceBridge | Lifecycle fulfillment**, Provision access, the portal widget, and the identity mock are on the instance. Leave them. Their files are in `F:\ServiceNow\Projects\servicebridge-outside-demo`.

## Next project

Notifications, SLAs, UI Policies, ACLs, Import Sets, ATF, GlideAjax, GlideAggregate, Service Portal, SOAP, REST status codes, and native HRSD, ITOM, or CSM are a different project:

`F:\ServiceNow\Projects\servicenow-platform-lab`

Do not add them to this directory.
