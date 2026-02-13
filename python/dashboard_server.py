#!/usr/bin/env python3
"""Local dashboard server with refresh endpoint.

Serves the data/ directory on port 8765 and exposes:
  POST /api/refresh        — re-runs search_staff.py + enrich_missing.py
  GET  /api/refresh-status  — check progress

Usage:
    cd /Users/jamie.cross/Documents/UKRI-GTR-Scanner
    python python/dashboard_server.py
    # Then open http://localhost:8765/dashboard.html
"""

import http.server
import json
import os
import subprocess
import sys
import threading

PORT = 8765
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PYTHON_DIR = os.path.join(BASE_DIR, "python")
SEARCH_SCRIPT = os.path.join(PYTHON_DIR, "search_staff.py")
ENRICH_SCRIPT = os.path.join(PYTHON_DIR, "enrich_missing.py")

_refresh_lock = threading.Lock()
_refresh_status = {"running": False, "last_result": None, "progress": ""}


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Extends SimpleHTTPRequestHandler with /api/* routes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DATA_DIR, **kwargs)

    def do_POST(self):
        if self.path == "/api/refresh":
            self.handle_refresh()
        else:
            self.send_error(404, "Not found")

    def do_GET(self):
        if self.path == "/api/refresh-status":
            self.handle_refresh_status()
        else:
            super().do_GET()

    def handle_refresh(self):
        """Kick off search_staff.py + enrich_missing.py in a background thread."""
        global _refresh_status

        if _refresh_status["running"]:
            self._json_response({"status": "already_running", "progress": _refresh_status["progress"]})
            return

        _refresh_status = {"running": True, "last_result": None, "progress": "Starting search..."}
        thread = threading.Thread(target=_run_refresh, daemon=True)
        thread.start()
        self._json_response({"status": "started"})

    def handle_refresh_status(self):
        """Return current refresh status as JSON."""
        self._json_response({
            "running": _refresh_status["running"],
            "progress": _refresh_status["progress"],
            "result": _refresh_status["last_result"],
        })

    def _json_response(self, data, code=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


def _run_refresh():
    """Run the search + enrich pipeline in a background thread."""
    global _refresh_status
    python = sys.executable

    try:
        # Phase 1: search_staff.py
        _refresh_status["progress"] = "Phase 1: Searching GTR for staff projects..."
        print(f"[REFRESH] Running {SEARCH_SCRIPT}...", file=sys.stderr, flush=True)

        result = subprocess.run(
            [python, SEARCH_SCRIPT],
            capture_output=True,
            text=True,
            timeout=1800,  # 30 min max
        )
        if result.returncode != 0:
            _refresh_status["progress"] = f"Search failed: {result.stderr[-500:]}"
            _refresh_status["running"] = False
            _refresh_status["last_result"] = {"status": "error", "phase": "search", "error": result.stderr[-500:]}
            print(f"[REFRESH] search_staff.py FAILED:\n{result.stderr[-500:]}", file=sys.stderr)
            return

        print(f"[REFRESH] search_staff.py completed.", file=sys.stderr, flush=True)

        # Phase 2: enrich_missing.py
        _refresh_status["progress"] = "Phase 2: Enriching missing data..."
        print(f"[REFRESH] Running {ENRICH_SCRIPT}...", file=sys.stderr, flush=True)

        result2 = subprocess.run(
            [python, ENRICH_SCRIPT],
            capture_output=True,
            text=True,
            timeout=600,  # 10 min max
        )
        if result2.returncode != 0:
            _refresh_status["progress"] = f"Enrich failed: {result2.stderr[-500:]}"
            _refresh_status["running"] = False
            _refresh_status["last_result"] = {"status": "error", "phase": "enrich", "error": result2.stderr[-500:]}
            print(f"[REFRESH] enrich_missing.py FAILED:\n{result2.stderr[-500:]}", file=sys.stderr)
            return

        print(f"[REFRESH] enrich_missing.py completed.", file=sys.stderr, flush=True)

        # Count projects in updated CSV
        csv_path = os.path.join(DATA_DIR, "uofg_sps_staff_gtr_projects.csv")
        n_projects = 0
        if os.path.exists(csv_path):
            with open(csv_path) as f:
                n_projects = sum(1 for _ in f) - 1  # minus header

        _refresh_status["progress"] = f"Done! {n_projects} projects updated."
        _refresh_status["running"] = False
        _refresh_status["last_result"] = {"status": "ok", "projects": n_projects}
        print(f"[REFRESH] Complete. {n_projects} projects.", file=sys.stderr, flush=True)

    except subprocess.TimeoutExpired:
        _refresh_status["progress"] = "Timed out!"
        _refresh_status["running"] = False
        _refresh_status["last_result"] = {"status": "error", "error": "Process timed out"}
        print("[REFRESH] TIMEOUT", file=sys.stderr)
    except Exception as e:
        _refresh_status["progress"] = f"Error: {e}"
        _refresh_status["running"] = False
        _refresh_status["last_result"] = {"status": "error", "error": str(e)}
        print(f"[REFRESH] ERROR: {e}", file=sys.stderr)


def main():
    print(f"╔══════════════════════════════════════════════════╗", file=sys.stderr)
    print(f"║  UofG SPS Dashboard Server                      ║", file=sys.stderr)
    print(f"║  Serving: {DATA_DIR:<39}║", file=sys.stderr)
    print(f"║  URL:     http://localhost:{PORT}/dashboard.html    ║", file=sys.stderr)
    print(f"╠══════════════════════════════════════════════════╣", file=sys.stderr)
    print(f"║  POST /api/refresh       — re-run GTR pipeline  ║", file=sys.stderr)
    print(f"║  GET  /api/refresh-status — check progress       ║", file=sys.stderr)
    print(f"╚══════════════════════════════════════════════════╝", file=sys.stderr)

    server = http.server.HTTPServer(("", PORT), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.", file=sys.stderr)
        server.server_close()


if __name__ == "__main__":
    main()
