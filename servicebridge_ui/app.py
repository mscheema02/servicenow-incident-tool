"""ServiceBridge monitoring dashboard - Bloomberg terminal style."""
import base64
import json
import os
import sqlite3
import urllib.error
import urllib.request
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request

app = Flask(__name__, 
            template_folder=Path(__file__).parent / "templates",
            static_folder=Path(__file__).parent / "static")

# Dashboard state database
DB_PATH = os.getenv("SERVICEBRIDGE_UI_DB", "servicebridge_ui.sqlite3")


def init_db():
    """Initialize the dashboard database."""
    with closing(sqlite3.connect(DB_PATH)) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            service_key TEXT NOT NULL,
            outage_id TEXT NOT NULL,
            state TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            http_status INTEGER,
            response TEXT,
            success INTEGER DEFAULT 0
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS services (
            service_key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            current_state TEXT DEFAULT 'UP',
            last_event_at TEXT,
            down_count INTEGER DEFAULT 0,
            up_count INTEGER DEFAULT 0
        )""")
        db.commit()
        
        # Seed default services
        default_services = [
            ("booking-site", "Booking Site"),
            ("help-center", "Help Center"),
            ("account-portal", "Account Portal"),
            ("payment-api", "Payment API"),
            ("storefront", "Storefront"),
        ]
        for key, name in default_services:
            db.execute(
                "INSERT OR IGNORE INTO services (service_key, name) VALUES (?, ?)",
                (key, name)
            )
        db.commit()


def get_config():
    """Get ServiceNow connection configuration."""
    return {
        "url": os.getenv("SERVICEBRIDGE_NOW_URL", ""),
        "user": os.getenv("SERVICEBRIDGE_NOW_USER", ""),
        "configured": bool(os.getenv("SERVICEBRIDGE_NOW_URL") and 
                          os.getenv("SERVICEBRIDGE_NOW_USER") and
                          os.getenv("SERVICEBRIDGE_NOW_PASSWORD")),
    }


def send_to_servicenow(event_data):
    """Send event to ServiceNow Scripted REST API."""
    url = os.getenv("SERVICEBRIDGE_NOW_URL", "")
    user = os.getenv("SERVICEBRIDGE_NOW_USER", "")
    password = os.getenv("SERVICEBRIDGE_NOW_PASSWORD", "")
    
    if not all([url, user, password]):
        return None, {"error": "ServiceNow not configured", "detail": "Set SERVICEBRIDGE_NOW_URL, SERVICEBRIDGE_NOW_USER, SERVICEBRIDGE_NOW_PASSWORD"}
    
    if not url.startswith("https://"):
        return None, {"error": "URL must use HTTPS", "detail": f"Got: {url[:50]}..."}
    
    auth = base64.b64encode((user + ":" + password).encode()).decode()
    req = urllib.request.Request(
        url,
        data=json.dumps(event_data).encode(),
        headers={
            "Authorization": "Basic " + auth,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        
        # Parse and provide actionable error messages
        diagnosis = _diagnose_servicenow_error(exc.code, error_body, user, url)
        
        try:
            parsed = json.loads(error_body)
            parsed["_diagnosis"] = diagnosis
            return exc.code, parsed
        except json.JSONDecodeError:
            return exc.code, {"raw_error": error_body, "_diagnosis": diagnosis}
    except urllib.error.URLError as e:
        return None, {"error": "Connection failed", "detail": str(e.reason), "_diagnosis": "Check instance URL and network connectivity. Instance may be hibernating."}
    except Exception as e:
        return None, {"error": "Unexpected error", "detail": str(e)}


def _diagnose_servicenow_error(status_code, error_body, user, url):
    """Provide actionable diagnosis for ServiceNow errors."""
    
    if status_code == 401:
        # Authentication failed - most common causes
        causes = []
        
        if "User is not authenticated" in error_body:
            causes.append("LIKELY CAUSE: User cannot access REST APIs via Basic Auth.")
            causes.append("")
            causes.append("FIX IN SERVICENOW:")
            causes.append(f"1. Go to All > Users > find '{user}'")
            causes.append("2. Scroll to 'Web service access only' - must be CHECKED")
            causes.append("3. OR add role 'snc_internal' to the user")
            causes.append("4. If recently changed password, wait 1 minute and retry")
            causes.append("")
            causes.append("ALTERNATIVE: Test with admin user to confirm API works")
        else:
            causes.append("Invalid credentials or user does not exist.")
            causes.append(f"Verify user '{user}' exists and password is correct.")
        
        return " | ".join(causes)
    
    elif status_code == 403:
        return f"User '{user}' authenticated but lacks permission. Grant role YOUR_SCOPE.integration to user."
    
    elif status_code == 404:
        return f"API endpoint not found. Verify Scripted REST API exists and URL path is correct: {url}"
    
    elif status_code == 400:
        return "Bad request - check the Script Include BridgeEventProcessor exists and script has no errors."
    
    elif status_code == 500:
        return "ServiceNow server error - check System Logs > Application Logs in ServiceNow for details."
    
    return f"HTTP {status_code} - check ServiceNow logs for details."


@app.route("/")
def dashboard():
    """Render the main dashboard."""
    return render_template("index.html")


@app.route("/api/config")
def api_config():
    """Return current configuration status."""
    return jsonify(get_config())


@app.route("/api/diagnose")
def api_diagnose():
    """Test ServiceNow connection and diagnose issues."""
    url = os.getenv("SERVICEBRIDGE_NOW_URL", "")
    user = os.getenv("SERVICEBRIDGE_NOW_USER", "")
    password = os.getenv("SERVICEBRIDGE_NOW_PASSWORD", "")
    
    result = {
        "config": {
            "url_set": bool(url),
            "user_set": bool(user),
            "password_set": bool(password),
            "url": url[:60] + "..." if len(url) > 60 else url,
            "user": user,
        },
        "tests": []
    }
    
    if not all([url, user, password]):
        result["tests"].append({
            "name": "Configuration",
            "status": "FAIL",
            "message": "Missing environment variables"
        })
        return jsonify(result)
    
    # Extract instance base URL
    import re
    match = re.match(r'(https://[^/]+)', url)
    if not match:
        result["tests"].append({
            "name": "URL Format",
            "status": "FAIL",
            "message": f"Invalid URL format: {url}"
        })
        return jsonify(result)
    
    base_url = match.group(1)
    
    # Test 1: Instance reachability
    try:
        req = urllib.request.Request(base_url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result["tests"].append({
                "name": "Instance Reachable",
                "status": "PASS",
                "message": f"{base_url} returned HTTP {resp.status}"
            })
    except Exception as e:
        result["tests"].append({
            "name": "Instance Reachable",
            "status": "FAIL",
            "message": f"Cannot reach {base_url}: {e}"
        })
        return jsonify(result)
    
    # Test 2: Basic Auth with Table API (standard endpoint)
    auth = base64.b64encode((user + ":" + password).encode()).decode()
    table_url = f"{base_url}/api/now/table/sys_user?sysparm_limit=1&sysparm_fields=user_name"
    
    try:
        req = urllib.request.Request(
            table_url,
            headers={"Authorization": "Basic " + auth, "Accept": "application/json"},
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result["tests"].append({
                "name": "Basic Auth (Table API)",
                "status": "PASS",
                "message": f"User '{user}' can access REST APIs"
            })
    except urllib.error.HTTPError as e:
        if e.code == 401:
            result["tests"].append({
                "name": "Basic Auth (Table API)", 
                "status": "FAIL",
                "message": f"HTTP 401 - User '{user}' CANNOT access REST APIs. Enable 'Web service access only' on user record OR add 'snc_internal' role."
            })
            result["fix_instructions"] = [
                f"1. In ServiceNow: All > Users > find '{user}'",
                "2. Check 'Web service access only' checkbox",
                "3. OR: Add role 'snc_internal' or 'rest_api_explorer'",
                "4. Save and retry"
            ]
        else:
            result["tests"].append({
                "name": "Basic Auth (Table API)",
                "status": "FAIL", 
                "message": f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:200]}"
            })
        return jsonify(result)
    except Exception as e:
        result["tests"].append({
            "name": "Basic Auth (Table API)",
            "status": "FAIL",
            "message": str(e)
        })
        return jsonify(result)
    
    # Test 3: Scripted REST API endpoint
    try:
        test_payload = {
            "event_id": "diagnose-test",
            "source": "diagnose",
            "service_key": "test",
            "outage_id": "test",
            "state": "UP",
            "observed_at": datetime.now(timezone.utc).isoformat()
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(test_payload).encode(),
            headers={
                "Authorization": "Basic " + auth,
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
            result["tests"].append({
                "name": "Scripted REST API",
                "status": "PASS",
                "message": f"API returned HTTP {resp.status}",
                "response": body
            })
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        
        if e.code == 401:
            msg = "HTTP 401 on Scripted REST but Table API worked. Check 'Requires authentication' and ACL settings on the API."
        elif e.code == 403:
            msg = f"HTTP 403 - User needs role YOUR_SCOPE.integration. Grant it in ServiceNow."
        elif e.code == 404:
            msg = f"HTTP 404 - API endpoint not found. Verify the Scripted REST API and resource exist."
        elif e.code == 400:
            msg = f"HTTP 400 - Script error. Check BridgeEventProcessor Script Include exists. Error: {error_body[:200]}"
        else:
            msg = f"HTTP {e.code}: {error_body[:200]}"
        
        result["tests"].append({
            "name": "Scripted REST API",
            "status": "FAIL",
            "message": msg
        })
    except Exception as e:
        result["tests"].append({
            "name": "Scripted REST API",
            "status": "FAIL",
            "message": str(e)
        })
    
    return jsonify(result)


@app.route("/api/services")
def api_services():
    """Return all monitored services."""
    with closing(sqlite3.connect(DB_PATH)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT * FROM services ORDER BY service_key"
        ).fetchall()
        return jsonify([dict(row) for row in rows])


@app.route("/api/events")
def api_events():
    """Return recent events."""
    limit = request.args.get("limit", 50, type=int)
    with closing(sqlite3.connect(DB_PATH)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return jsonify([dict(row) for row in rows])


@app.route("/api/stats")
def api_stats():
    """Return dashboard statistics."""
    with closing(sqlite3.connect(DB_PATH)) as db:
        total_events = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        successful = db.execute(
            "SELECT COUNT(*) FROM events WHERE success = 1"
        ).fetchone()[0]
        failed = db.execute(
            "SELECT COUNT(*) FROM events WHERE success = 0 AND http_status IS NOT NULL"
        ).fetchone()[0]
        services_down = db.execute(
            "SELECT COUNT(*) FROM services WHERE current_state = 'DOWN'"
        ).fetchone()[0]
        services_up = db.execute(
            "SELECT COUNT(*) FROM services WHERE current_state = 'UP'"
        ).fetchone()[0]
        
        return jsonify({
            "total_events": total_events,
            "successful": successful,
            "failed": failed,
            "pending": total_events - successful - failed,
            "services_down": services_down,
            "services_up": services_up,
        })


@app.route("/api/send", methods=["POST"])
def api_send():
    """Send a monitoring event to ServiceNow."""
    data = request.get_json()
    service_key = data.get("service_key", "booking-site")
    outage_id = data.get("outage_id") or f"outage-{uuid.uuid4().hex[:8]}"
    state = data.get("state", "DOWN")
    event_id = data.get("event_id") or str(uuid.uuid4())
    
    now = datetime.now(timezone.utc).isoformat()
    
    event_data = {
        "event_id": event_id,
        "source": "url_response",
        "service_key": service_key,
        "outage_id": outage_id,
        "state": state,
        "observed_at": now,
    }
    
    # Send to ServiceNow
    http_status, response = send_to_servicenow(event_data)
    success = http_status in (200, 201) if http_status else False
    
    # Record in local database
    with closing(sqlite3.connect(DB_PATH)) as db:
        db.execute("""
            INSERT INTO events 
            (event_id, service_key, outage_id, state, observed_at, sent_at, http_status, response, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id, service_key, outage_id, state, now, now,
            http_status, json.dumps(response) if response else None, 
            1 if success else 0
        ))
        
        # Update service state
        if state == "DOWN":
            db.execute("""
                UPDATE services 
                SET current_state = 'DOWN', last_event_at = ?, down_count = down_count + 1
                WHERE service_key = ?
            """, (now, service_key))
        else:
            db.execute("""
                UPDATE services 
                SET current_state = 'UP', last_event_at = ?, up_count = up_count + 1
                WHERE service_key = ?
            """, (now, service_key))
        
        db.commit()
    
    return jsonify({
        "event": event_data,
        "http_status": http_status,
        "response": response,
        "success": success,
    })


@app.route("/api/services", methods=["POST"])
def api_add_service():
    """Add a new monitored service."""
    data = request.get_json()
    service_key = data.get("service_key", "").strip().lower().replace(" ", "-")
    name = data.get("name", "").strip()
    
    if not service_key or not name:
        return jsonify({"error": "service_key and name required"}), 400
    
    with closing(sqlite3.connect(DB_PATH)) as db:
        try:
            db.execute(
                "INSERT INTO services (service_key, name) VALUES (?, ?)",
                (service_key, name)
            )
            db.commit()
            return jsonify({"service_key": service_key, "name": name})
        except sqlite3.IntegrityError:
            return jsonify({"error": "Service already exists"}), 409


def main():
    """Run the dashboard server."""
    init_db()
    host = os.getenv("SERVICEBRIDGE_UI_HOST", "127.0.0.1")
    port = int(os.getenv("SERVICEBRIDGE_UI_PORT", "8080"))
    debug = os.getenv("SERVICEBRIDGE_UI_DEBUG", "").lower() in ("1", "true")
    
    print(f"\n{'='*60}")
    print("  SERVICEBRIDGE MONITOR DASHBOARD")
    print(f"{'='*60}")
    print(f"  URL: http://{host}:{port}")
    print(f"  ServiceNow configured: {get_config()['configured']}")
    print(f"{'='*60}\n")
    
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
