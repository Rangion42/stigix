#!/usr/bin/env python3
"""
stigix-cli — Interactive local CLI for Stigix
Installed alongside Stigix, talks directly to the local backend on localhost:8080

Usage:
  stigix-cli                              # Interactive REPL
  stigix-cli --url http://10.0.0.5:8080   # Connect to remote
  stigix-cli --exec "security suite"      # Run single command headless
  stigix-cli --script cmds.txt            # Run a list of commands
"""

try:
    import os
    import sys
    import json
    import time
    import threading
    import getpass
    import argparse
    from datetime import datetime
    from pathlib import Path

    try:
        import requests
    except ImportError:
        print("Missing dependency: pip install requests prompt_toolkit")
        sys.exit(1)

    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.completion import Completer, Completion, NestedCompleter
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
        from prompt_toolkit.styles import Style
        from prompt_toolkit.formatted_text import HTML
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.document import Document
        from prompt_toolkit.history import FileHistory
        HAS_PROMPT_TOOLKIT = True
    except ImportError:
        HAS_PROMPT_TOOLKIT = False
        print("[warn] prompt_toolkit not found — pip install prompt_toolkit for best experience")
except KeyboardInterrupt:
    print("\nInterrupted.")
    try:
        import sys
        sys.exit(0)
    except Exception:
        import os
        os._exit(0)

# ─── Config ───────────────────────────────────────────────────────────────────

CONFIG_FILE  = Path.home() / ".stigix-cli.json"
HISTORY_FILE = Path.home() / ".stigix-cli.history"
DEFAULT_URL  = os.environ.get("STIGIX_URL", "http://localhost:8080")

JWT_TOKEN    = None
STIGIX_URL   = DEFAULT_URL
PROFILES     = {}          # {name: {"url": ..., "token": ...}}
INSTANCE_TOKENS = {}       # {url: token}

VERSION      = "1.1.0"
TIMEOUT      = 10

# ─── Session persistence ──────────────────────────────────────────────────────

def load_session():
    """Load saved token, URL and profiles from ~/.stigix-cli.json"""
    global JWT_TOKEN, STIGIX_URL, PROFILES, INSTANCE_TOKENS
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            PROFILES = data.get("profiles", {})
            INSTANCE_TOKENS = data.get("instance_tokens", {})
            
            saved_url = data.get("url")
            if saved_url and STIGIX_URL == DEFAULT_URL:
                STIGIX_URL = saved_url
                
            # Restore token specific to current STIGIX_URL, or fall back to legacy 'token'
            if STIGIX_URL in INSTANCE_TOKENS:
                JWT_TOKEN = INSTANCE_TOKENS[STIGIX_URL]
            else:
                JWT_TOKEN = data.get("token")
        except Exception:
            pass

def save_session():
    """Persist token, URL and profiles to ~/.stigix-cli.json (chmod 600)"""
    global JWT_TOKEN, STIGIX_URL, PROFILES, INSTANCE_TOKENS
    try:
        if STIGIX_URL:
            if JWT_TOKEN:
                INSTANCE_TOKENS[STIGIX_URL] = JWT_TOKEN
            else:
                INSTANCE_TOKENS.pop(STIGIX_URL, None)
                
        # Sync profile tokens
        for name, prof in PROFILES.items():
            prof_url = prof.get("url")
            if prof_url == STIGIX_URL:
                prof["token"] = JWT_TOKEN
            elif prof_url in INSTANCE_TOKENS:
                prof["token"] = INSTANCE_TOKENS[prof_url]

        CONFIG_FILE.write_text(json.dumps(
            {
                "token": JWT_TOKEN, 
                "url": STIGIX_URL, 
                "profiles": PROFILES,
                "instance_tokens": INSTANCE_TOKENS
            }, indent=2
        ))
        CONFIG_FILE.chmod(0o600)
    except Exception:
        pass

def read_json_file(filepath):
    """
    Reads a JSON file. Supports '-' to read from stdin.
    If running in a Docker container and a relative path is not found in the current directory,
    tries falling back to the mounted config/ directory.
    """
    if filepath == "-":
        try:
            return json.loads(sys.stdin.read())
        except Exception as e:
            err(f"Failed to read/parse from stdin: {e}")
            return None

    path = Path(filepath)
    
    # Check if the file exists in current working directory
    if path.exists():
        target_path = path
    else:
        # Fallback 1: check inside config/
        fallback_rel = Path("config") / path.name
        # Fallback 2: check inside /app/config/
        fallback_app = Path("/app/config") / path.name
        
        if fallback_rel.exists():
            target_path = fallback_rel
        elif fallback_app.exists():
            target_path = fallback_app
        else:
            target_path = path

    if not target_path.exists():
        err(f"File not found: '{filepath}'")
        # Check if we are likely in a Docker container
        is_docker = Path("/.dockerenv").exists() or Path("/app/config").exists()
        if is_docker:
            info("Note: Since stigix-cli is running inside a Docker container, it cannot access files on your host directly.")
            info("To import a host file, you can:")
            info(f"  1. Place the file in the './config' folder on the host, and import it as 'config/{path.name}'")
            info("  2. Pipe the file from your host terminal using stdin:")
            info(f"     docker exec -i stigix stigix-cli --exec \"... import -\" < {path.name}")
        return None

    try:
        with open(target_path, "r") as f:
            return json.load(f)
    except Exception as e:
        err(f"Failed to read/parse file: {e}")
        return None

def write_json_file(filepath, data):
    """
    Writes data to a JSON file.
    If the path is relative and we are running in a Docker container,
    automatically resolves it to the mounted config/ directory (which maps to the host's config/ folder),
    so that the exported file is visible outside the container.
    """
    path = Path(filepath)
    if not path.is_absolute():
        # Check if config directory exists and is writable
        config_dirs = [Path("config"), Path("/app/config")]
        for cdir in config_dirs:
            if cdir.exists() and os.access(cdir, os.W_OK):
                path = cdir / path.name
                break

    try:
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        ok(f"Exported configuration to {path}")
        # If it was resolved to config/ let the user know where it is on the host
        if not Path(filepath).is_absolute() and path.parent.name == "config":
            info(f"  (This corresponds to './config/{path.name}' on your host filesystem)")
        return True
    except Exception as e:
        err(f"Failed to write file: {e}")
        return False

# ─── Colors / output helpers ──────────────────────────────────────────────────

def c(code, text): return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text
def ok(msg):    print(c("32",  "✓ ") + msg)
def err(msg):   print(c("31",  "✗ ") + msg)
def warn(msg):  print(c("33",  "⚠ ") + msg)
def info(msg):  print(c("36",  "→ ") + msg)
def hdr(msg):   print(c("1;34", msg))
def dim(msg):   print(c("2",    msg))
def sep():      print(c("2", "  " + "─" * 50))

def table(headers, rows):
    if not rows:
        dim("  (empty)")
        return
    import re
    def clean_ansi(s):
        return re.sub(r'\033\[[0-9;]*m', '', str(s))
    
    widths = []
    for i, h in enumerate(headers):
        w = len(clean_ansi(h))
        for r in rows:
            if i < len(r):
                w = max(w, len(clean_ansi(r[i])))
        widths.append(w)
        
    def format_row(row):
        cols = []
        for i in range(len(widths)):
            val = row[i] if i < len(row) else ""
            w = widths[i]
            s_str = str(val)
            cols.append(s_str + (" " * max(0, w - len(clean_ansi(s_str)))))
        return "  " + "  ".join(cols)

    print(c("1", format_row(headers)))
    print("  " + "  ".join("─" * w for w in widths))
    for row in rows:
        print(format_row(row))

def status_badge(s):
    s = str(s).lower()
    if s in ("blocked", "stopped", "false", "disabled", "down", "error"):
        return c("31", f"[{s.upper()}]")
    if s in ("allowed", "running", "true", "enabled", "up", "ok", "healthy"):
        return c("32", f"[{s.upper()}]")
    return c("33", f"[{s.upper()}]")

def do_clear():
    os.system("clear" if os.name != "nt" else "cls")

# ─── HTTP helpers ──────────────────────────────────────────────────────────────

def _headers():
    h = {"Content-Type": "application/json"}
    if JWT_TOKEN:
        h["Authorization"] = f"Bearer {JWT_TOKEN}"
    return h

def api_get(path):
    try:
        r = requests.get(f"{STIGIX_URL}{path}", headers=_headers(), timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        err(f"Cannot reach Stigix at {STIGIX_URL} — is the container running?")
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            err("Unauthorized — run: auth login")
        else:
            err(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        err(str(e))
        return None

def api_post(path, body=None, method="POST"):
    try:
        if method == "POST":
            fn = requests.post
        elif method == "PUT":
            fn = requests.put
        else:
            fn = requests.delete
        r  = fn(f"{STIGIX_URL}{path}", json=body or {}, headers=_headers(), timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        err(f"Cannot reach Stigix at {STIGIX_URL}")
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            err("Unauthorized — run: auth login")
        else:
            err(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
        return None
    except Exception as e:
        err(str(e))
        return None

def api_put(path, body=None):
    return api_post(path, body, method="PUT")

def api_delete(path, body=None):
    return api_post(path, body, method="DELETE")

def require_auth():
    if not JWT_TOKEN:
        err("Not authenticated — run: auth login")
        return False
    return True

# ─── Live status cache (bottom toolbar) ───────────────────────────────────────

class _StatusCache:
    """Background-refreshed cache for the bottom toolbar. Fetches every 10s."""

    def __init__(self):
        self.traffic  = "?"
        self.version  = "?"
        self.reachable = False
        self._ts      = 0
        self._lock    = threading.Lock()
        self._busy    = False

    def invalidate(self):
        """Force next refresh immediately (call after state-changing commands)."""
        self._ts = 0

    def refresh(self):
        with self._lock:
            if self._busy or (time.time() - self._ts < 10):
                return
            self._busy = True
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        try:
            r = requests.get(f"{STIGIX_URL}/api/traffic/status", headers=_headers(), timeout=3)
            if r.ok:
                d = r.json()
                self.traffic   = "▶ RUNNING" if (d.get("enabled") or d.get("running")) else "■ STOPPED"
                self.reachable = True
            else:
                self.traffic   = "?"
                self.reachable = False
        except Exception:
            self.traffic   = "?"
            self.reachable = False
        try:
            r = requests.get(f"{STIGIX_URL}/api/version", headers=_headers(), timeout=3)
            if r.ok:
                self.version = r.json().get("version", "?")
        except Exception:
            self.version = "?"
        self._ts = time.time()
        with self._lock:
            self._busy = False

STATUS = _StatusCache()


def _toolbar():
    """Bottom toolbar rendered by prompt_toolkit on every keystroke."""
    STATUS.refresh()

    host = STIGIX_URL.replace("https://", "").replace("http://", "")

    # connection indicator
    if not STATUS.reachable:
        conn = '<style bg="#B71C1C" fg="white"> ✗ OFFLINE </style>'
    elif JWT_TOKEN:
        conn = '<style bg="#1B5E20" fg="white"> ● connected </style>'
    else:
        conn = '<style bg="#E65100" fg="white"> ● no auth </style>'

    # traffic badge
    if STATUS.traffic == "▶ RUNNING":
        traf = f'<b fg="#69F0AE">▶ RUNNING</b>'
    elif STATUS.traffic == "■ STOPPED":
        traf = f'<b fg="#FF5252">■ STOPPED</b>'
    else:
        traf = f'<b fg="#90A4AE">? UNKNOWN</b>'

    ver  = f'v{STATUS.version}' if STATUS.version != "?" else ""
    div  = ' <b fg="#546E7A"> │ </b> '

    return HTML(
        f' {conn}'
        f'{div}<b fg="#80CBC4">{host}</b>'
        f'{div}Traffic: {traf}'
        + (f'{div}<b fg="#78909C">{ver}</b>' if ver else "")
        + f'{div}<b fg="#546E7A">F1</b>:help  <b fg="#546E7A">F5</b>:status  <b fg="#546E7A">Ctrl+L</b>:clear'
    )


# ─── Key bindings ─────────────────────────────────────────────────────────────

def _make_bindings():
    kb = KeyBindings()

    @kb.add("f1")
    def _(event):
        event.current_buffer.set_document(Document("help"))
        event.current_buffer.validate_and_handle()

    @kb.add("f5")
    def _(event):
        event.current_buffer.set_document(Document("status"))
        event.current_buffer.validate_and_handle()

    @kb.add("c-l")
    def _(event):
        event.app.renderer.clear()

    return kb

# ─── Commands ──────────────────────────────────────────────────────────────────

def cmd_auth(args):
    global JWT_TOKEN
    sub = args[0] if args else "help"

    if sub == "login":
        user = input("Username [admin]: ").strip() or "admin"
        pwd  = getpass.getpass("Password: ")
        r = api_post("/api/auth/login", {"username": user, "password": pwd})
        if r and r.get("token"):
            JWT_TOKEN = r["token"]
            save_session()
            STATUS.invalidate()
            ok(f"Logged in as {user}  (session saved → {CONFIG_FILE})")
        else:
            err("Login failed")

    elif sub == "status":
        if JWT_TOKEN:
            ok(f"Authenticated  (token: {JWT_TOKEN[:16]}...)")
        else:
            warn("Not authenticated")

    elif sub == "logout":
        JWT_TOKEN = None
        save_session()
        STATUS.invalidate()
        ok("Logged out  (session cleared)")

    else:
        print("Usage: auth login | status | logout")


def cmd_status(args):
    if not require_auth(): return
    hdr("━━ Stigix Status ━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    health = api_get("/api/system/health")
    if health:
        s = health.get("status", "?")
        ok(f"Backend    {status_badge(s)}  uptime {health.get('uptime','?')}s")

    v = api_get("/api/version")
    if v:
        info(f"Version    {v.get('version', v)}")

    t = api_get("/api/traffic/status")
    if t:
        state = "running" if (t.get("enabled") or t.get("running")) else "stopped"
        print(f"Traffic    {status_badge(state)}")
        STATUS.traffic = "▶ RUNNING" if state == "running" else "■ STOPPED"

    ip = api_get("/api/connectivity/public-ip")
    if ip:
        info(f"Public IP  {ip.get('ip', ip)}")

    conv = api_get("/api/convergence/status")
    if conv and isinstance(conv, list):
        running = [t for t in conv if t.get("running")]
        if running:
            ok(f"Failover running: {', '.join(t.get('testId','?') for t in running)}")


    site = api_get("/api/siteinfo")
    if site and site.get("siteName"):
        info(f"Prisma site: {site['siteName']}")

PREV_STATS = {"total_requests": None, "timestamp": None}

def get_app_groups():
    app_to_group = {}
    truncated_to_group = {}
    
    r = api_get("/api/config/apps")
    if r and isinstance(r, list):
        for cat in r:
            cat_name = cat.get("name", "Uncategorized")
            apps = cat.get("apps", [])
            for app in apps:
                domain = app.get("domain", "")
                clean_name = domain.replace("https://", "").replace("http://", "")
                app_to_group[clean_name] = cat_name
                app_to_group[domain] = cat_name
                
                host_part = clean_name.split('.')[0]
                if host_part and host_part not in truncated_to_group:
                    truncated_to_group[host_part] = cat_name
                    
    return app_to_group, truncated_to_group

def render_traffic_dashboard(stats, status_str, app_to_group, truncated_to_group, show_all=False):
    total_req = stats.get("total_requests", 0)
    errors_by_app = stats.get("errors_by_app", {})
    requests_by_app = stats.get("requests_by_app", {})
    
    total_errors = sum(errors_by_app.values())
    success_rate = ((total_req - total_errors) / total_req * 100) if total_req > 0 else 100.0
    active_apps = len([k for k, v in requests_by_app.items() if v > 0])
    
    # Calculate Traffic Rate
    current_ts = stats.get("timestamp", 0)
    rpm_str = "Calculating..."
    if PREV_STATS["total_requests"] is not None and PREV_STATS["timestamp"] is not None:
        delta_req = total_req - PREV_STATS["total_requests"]
        delta_time = current_ts - PREV_STATS["timestamp"]
        if delta_time > 0 and delta_req >= 0:
            pps = delta_req / delta_time
            rpm = pps * 60
            rpm_str = f"{rpm:.1f} req/min ({pps:.1f} pps)"
        elif delta_req >= 0:
            rpm_str = "0.0 req/min (0.0 pps)"
            
    # Update previous stats for rate tracking
    PREV_STATS["total_requests"] = total_req
    PREV_STATS["timestamp"] = current_ts

    status_text = status_str.upper()
    status_color = "32" if status_str == "running" else "31"
    status_colored = c(status_color, f"[{status_text}]".ljust(13))
    col1_row1 = f" Status: {status_colored}"
    
    success_color = "32" if success_rate >= 95 else ("33" if success_rate >= 80 else "31")
    success_colored = c(success_color, f"{success_rate:>5.1f}%")
    col2_row1 = f" Success Rate: {success_colored} "
    
    rpm_colored = c("36", rpm_str.ljust(17))
    col3_row1 = f" Traffic Rate: {rpm_colored} "
    
    col1_row2 = f" Active Apps: {active_apps:>5}    "
    col2_row2 = f" Total Requests: {total_req:>6}"
    
    errors_color = "31" if total_errors > 0 else "32"
    errors_colored = c(errors_color, f"{total_errors}".ljust(17))
    col3_row2 = f" Total Errors: {errors_colored} "
    
    row1 = f"║{col1_row1}║{col2_row1}║{col3_row1}║"
    row2 = f"║{col1_row2}║{col2_row2}║{col3_row2}║"
    
    hdr("╔══════════════════════╦══════════════════════╦════════════════════════════════╗")
    hdr("║" + "TRAFFIC DASHBOARD".center(78) + "║")
    hdr("╠══════════════════════╬══════════════════════╬════════════════════════════════╣")
    hdr(row1)
    hdr(row2)
    hdr("╚══════════════════════╩══════════════════════╩════════════════════════════════╝")
    print()
    
    # Print App Table
    hdr("━━ Active Applications ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    app_rows = []
    for app, reqs in requests_by_app.items():
        if reqs == 0:
            continue
        clean_app = app.replace("https://", "").replace("http://", "")
        group = app_to_group.get(clean_app) or app_to_group.get(app) or truncated_to_group.get(clean_app.split('.')[0]) or "Uncategorized"
        errs = errors_by_app.get(app, 0)
        app_success = ((reqs - errs) / reqs * 100) if reqs > 0 else 100.0
        app_rows.append({
            "app": clean_app,
            "group": group,
            "requests": reqs,
            "errors": errs,
            "success_rate": app_success
        })
        
    # Sort by requests descending
    app_rows.sort(key=lambda x: x["requests"], reverse=True)
    
    table_rows = []
    for idx, row in enumerate(app_rows, 1):
        app_name = row["app"][:30]
        group_name = row["group"][:20]
        reqs_str = c("34" if row["requests"] > 0 else "0", f"{row['requests']:,}")
        errs_str = c("31", f"{row['errors']:,}") if row["errors"] > 0 else c("2", "0")
        
        sr = row["success_rate"]
        if sr >= 95:
            sr_color = "32"
        elif sr >= 80:
            sr_color = "33"
        else:
            sr_color = "31"
        sr_str = c(sr_color, f"{sr:.1f}%")
        
        table_rows.append([
            str(idx),
            app_name,
            group_name,
            reqs_str,
            errs_str,
            sr_str
        ])
        
    if not table_rows:
        dim("  No applications traffic recorded yet")
        return
        
    display_rows = table_rows if show_all else table_rows[:15]
    table(["#", "Application", "Group", "Requests", "Errors", "Success Rate"], display_rows)
    
    if not show_all and len(table_rows) > 15:
        print()
        dim(f"  (Showing top 15 of {len(table_rows)} active applications. Use 'traffic stats --all' to list all)")

def cmd_traffic(args):
    if not require_auth(): return
    sub = args[0] if args else "status"

    if sub == "start":
        r = api_post("/api/traffic/start")
        if r:
            ok("Traffic generation started")
            STATUS.invalidate()

    elif sub == "stop":
        r = api_post("/api/traffic/stop")
        if r:
            ok("Traffic generation stopped")
            STATUS.invalidate()

    elif sub == "status":
        r = api_get("/api/traffic/status")
        if r:
            state = "running" if (r.get("enabled") or r.get("running")) else "stopped"
            print(f"Traffic: {status_badge(state)}")

    elif sub == "stats":
        show_all = "--all" in args
        r = api_get("/api/stats")
        t = api_get("/api/traffic/status")
        if r:
            status_str = "stopped"
            if t:
                status_str = "running" if (t.get("enabled") or t.get("running")) else "stopped"
            app_to_group, truncated_to_group = get_app_groups()
            render_traffic_dashboard(r, status_str, app_to_group, truncated_to_group, show_all=show_all)

    elif sub == "logs":
        r = api_get("/api/logs")
        if r:
            lines = r if isinstance(r, list) else r.get("lines", [])
            hdr(f"━━ Last {len(lines)} log lines ━━━━━━━━━━━━━━━━━━━━━")
            for l in lines[-30:]:
                dim(l)

    elif sub == "reset":
        r = api_delete("/api/stats")
        if r:
            ok("Statistics reset")
            PREV_STATS["total_requests"] = None
            PREV_STATS["timestamp"] = None

    elif sub == "watch":
        show_all = "--all" in args
        clean_args = [a for a in args if a != "--all"]
        interval = int(clean_args[1]) if len(clean_args) > 1 else 3
        info(f"Live traffic watch — refresh every {interval}s  (Ctrl+C to stop)")
        try:
            app_to_group, truncated_to_group = get_app_groups()
            while True:
                do_clear()
                now = datetime.now().strftime("%H:%M:%S")
                hdr(f"━━ Traffic Stats  [{now}]  (Ctrl+C to stop) ━━━━━━━")
                print()
                r = api_get("/api/stats")
                t = api_get("/api/traffic/status")
                if r:
                    status_str = "stopped"
                    if t:
                        status_str = "running" if (t.get("enabled") or t.get("running")) else "stopped"
                    render_traffic_dashboard(r, status_str, app_to_group, truncated_to_group, show_all=show_all)
                time.sleep(interval)
        except KeyboardInterrupt:
            print()
            ok("Watch stopped")

    elif sub == "export":
        filepath = args[1] if len(args) > 1 else "stigix-traffic-export.json"
        r = api_get("/api/config/applications/export?format=json")
        if r is None:
            return
        write_json_file(filepath, r)

    elif sub == "import":
        filepath = args[1] if len(args) > 1 else None
        if not filepath:
            err("Usage: traffic import <filepath>")
            return
        data = read_json_file(filepath)
        if data is None:
            return
        content = json.dumps(data)
        r = api_post("/api/config/applications/import", {"content": content})
        if r:
            ok("Traffic applications config imported successfully")

    else:
        _help_section("TRAFFIC CONTROL / STATS", [
            ("traffic start",          "Start traffic generation"),
            ("traffic stop",           "Stop traffic generation"),
            ("traffic status",         "Show current traffic state"),
            ("traffic stats [--all]",  "Show traffic statistics & active apps dashboard"),
            ("traffic logs",           "Show last 30 backend log lines"),
            ("traffic reset",          "Reset traffic statistics"),
            ("traffic watch [sec] [--all]", "Live poll traffic stats and rate in real-time"),
            ("traffic export [file]",  "Export traffic configuration to JSON"),
            ("traffic import <file>",  "Import traffic configuration from JSON"),
        ])


def cmd_security(args):
    if not require_auth(): return
    sub = args[0] if args else "help"

    if sub == "status":
        r = api_get("/api/security/results/stats")
        if r:
            hdr("━━ Security Stats ━━━━━━━━━━━━━━━━━━━━━")
            ut = r.get("urlTests",    r.get("urltests",    {}))
            dt = r.get("dnsTests",    r.get("dnstests",    {}))
            tt = r.get("threatTests", r.get("threattests", {}))
            table(["Category", "Total", "Blocked", "Allowed"], [
                ["URL Filtering", ut.get("total",0), c("31",str(ut.get("blocked",0))), c("32",str(ut.get("allowed",0)))],
                ["DNS Security",  dt.get("total",0), c("31",str(dt.get("blocked",0))), c("32",str(dt.get("allowed",0)))],
                ["Threat Prev.",  tt.get("total",0), c("31",str(tt.get("blocked",0))), c("32",str(tt.get("allowed",0)))],
            ])

    elif sub == "url":
        url = args[1] if len(args) > 1 else None
        if not url:
            err("Usage: security url <url>")
            return
        info(f"Testing URL: {url}")
        r = api_post("/api/security/url-test", {"url": url, "category": "Manual"})
        if r:
            status = r.get("status", r.get("result", {}).get("status", "?"))
            print(f"Result: {status_badge(status)}  (HTTP {r.get('httpCode','?')})")

    elif sub == "url-batch":
        info("Running batch URL filter test (all enabled categories)...")
        r = api_get("/api/security/config")
        if not r: return
        cats = r.get("urlfiltering", r.get("urlFiltering", {})).get("enabledcategories", [])
        if not cats:
            warn("No URL categories enabled in config")
            return
        BASE  = "http://urlfiltering.paloaltonetworks.com/test-"
        tests = [{"url": f"{BASE}{cat.lower().replace(' ','-')}", "category": cat} for cat in cats]
        result = api_post("/api/security/url-test-batch", {"tests": tests})
        if result:
            rows = []
            for res in result.get("results", []):
                s = res.get("status") or res.get("result", {}).get("status", "?")
                rows.append([res.get("category","?"), res.get("url","?")[:50], status_badge(s)])
            table(["Category", "URL", "Result"], rows)

    elif sub == "dns":
        domain = args[1] if len(args) > 1 else None
        if not domain:
            err("Usage: security dns <domain>")
            return
        info(f"Testing DNS: {domain}")
        r = api_post("/api/security/dns-test", {"domain": domain, "testName": "Manual"})
        if r:
            status   = r.get("status", "?")
            resolved = r.get("resolved", False)
            print(f"Result: {status_badge(status)}  resolved={resolved}")

    elif sub == "dns-batch":
        info("Running batch DNS security test (all enabled domains)...")
        r = api_get("/api/security/config")
        if not r: return
        tests_conf = r.get("dnssecurity", r.get("dnsSecurity", {})).get("enabledtests", [])
        if not tests_conf:
            warn("No DNS tests enabled in config")
            return
        DOMAINS = {
            "malware":       "test-malware.testpanw.com",
            "phishing":      "test-phishing.testpanw.com",
            "dns-tunneling": "test-dnstunneling.testpanw.com",
            "botnet":        "test-botnet.testpanw.com",
        }
        tests  = [{"domain": DOMAINS.get(t, t), "testName": t.title()} for t in tests_conf if t in DOMAINS]
        result = api_post("/api/security/dns-test-batch", {"tests": tests})
        if result:
            rows = []
            for res in result.get("results", []):
                s = res.get("status", "?")
                rows.append([res.get("testName","?"), res.get("domain","?"), status_badge(s)])
            table(["Test Name", "Domain", "Result"], rows)

    elif sub == "eicar":
        target   = args[1] if len(args) > 1 else None
        r_cfg    = api_get("/api/security/config")
        if not r_cfg: return
        tp       = r_cfg.get("threatprevention", r_cfg.get("threatPrevention", {}))
        endpoints = tp.get("eicarendpoints", []) or tp.get("eicarEndpoints", [])
        if target:
            if not target.startswith("http"):
                target = f"http://{target}/eicar.com.txt"
            endpoints = [target]
        if not endpoints:
            err("No EICAR endpoints configured. Usage: security eicar [http://ip:8082/eicar.com.txt]")
            return
        info(f"Running EICAR threat prevention test ({len(endpoints)} endpoint(s))...")
        r = api_post("/api/security/threat-test", {"endpoints": endpoints})
        if r:
            rows = []
            for res in r.get("results", []):
                s  = res.get("status", "?")
                ep = res.get("endpoint", "?")
                rows.append([ep[:60], status_badge(s), res.get("message","")[:40]])
            table(["Endpoint", "Result", "Message"], rows)

    elif sub == "suite":
        hdr("━━ Security Suite ━━━━━━━━━━━━━━━━━━━━━━━━")
        print()
        info("1/3 — URL Filtering batch test")
        cmd_security(["url-batch"])
        print()
        info("2/3 — DNS Security batch test")
        cmd_security(["dns-batch"])
        print()
        info("3/3 — EICAR Threat Prevention")
        cmd_security(["eicar"])
        print()
        info("Done. Run 'security status' for aggregate stats.")

    elif sub == "results":
        limit = int(args[1]) if len(args) > 1 else 20
        r = api_get(f"/api/security/results?limit={limit}")
        if r:
            rows = []
            for res in r.get("results", []):
                ts    = datetime.fromtimestamp(res["timestamp"]/1000).strftime("%H:%M:%S") if "timestamp" in res else "?"
                s     = res.get("result", {}).get("status") or res.get("status","?")
                name  = res.get("testName") or res.get("category","?")
                ttype = res.get("testType","?")
                rows.append([ts, ttype[:4], name[:25], status_badge(s)])
            table(["Time", "Type", "Name", "Result"], rows)

    elif sub == "clear":
        r = api_delete("/api/security/results")
        if r: ok("Security results cleared")

    else:
        _help_section("SECURITY", [
            ("security status",            "Blocked/allowed aggregate stats"),
            ("security url <url>",         "Test a single URL"),
            ("security url-batch",         "Test all enabled URL categories"),
            ("security dns <domain>",      "Test a single DNS query"),
            ("security dns-batch",         "Test all enabled DNS domains"),
            ("security eicar [ip:8082]",   "EICAR threat prevention test"),
            ("security suite",             "Run all tests in sequence"),
            ("security results [n]",       "Last N results (default 20)"),
            ("security clear",             "Clear results history"),
        ])


def cmd_experience(args):
    if not require_auth(): return
    sub = args[0] if args else "list"

    if sub == "list":
        r = api_get("/api/connectivity/custom")
        if r:
            targets = r if isinstance(r, list) else r.get("targets", [])
            if not targets:
                dim("  No custom digital experience targets configured")
                return
            rows = []
            for idx, t in enumerate(targets, 1):
                enabled = "✓" if t.get("enabled", True) else "✗"
                rows.append([
                    str(idx),
                    t.get("name","?")[:30],
                    t.get("target") or t.get("host") or t.get("url","?"),
                    t.get("type","?"),
                    enabled
                ])
            table(["Index", "Name", "Target", "Type", "On"], rows)

    elif sub == "add":
        parsed = parse_flags(args[1:], ["name", "target", "host", "url", "type", "port", "timeout"])
        
        # 1. Probe Type
        ttype = parsed.get("type")
        if not ttype:
            if sys.stdin.isatty():
                print("\nSelect Probe Type:")
                print("  1: HTTP   (curl web check)")
                print("  2: HTTPS  (secure web check)")
                print("  3: PING   (ICMP echo)")
                print("  4: TCP    (netcat port check)")
                print("  5: UDP    (iperf3 jitter check)")
                print("  6: DNS    (dig lookup check)")
                print()
                try:
                    choice = input("Select type [1]: ").strip()
                    if not choice:
                        idx = 1
                    else:
                        idx = int(choice)
                except (ValueError, KeyboardInterrupt, EOFError):
                    print("\nAborted.")
                    return
                
                type_map = {1: "HTTP", 2: "HTTPS", 3: "PING", 4: "TCP", 5: "UDP", 6: "DNS"}
                ttype = type_map.get(idx, "HTTP")
            else:
                ttype = "HTTP"
        
        ttype = ttype.upper()
        if ttype == "ICMP":
            ttype = "PING"
        if ttype not in ["HTTP", "HTTPS", "PING", "TCP", "UDP", "DNS"]:
            err(f"Invalid probe type: {ttype}. Supported: HTTP, HTTPS, PING, TCP, UDP, DNS")
            return
            
        # 2. Target (Host/URL/IP)
        target = parsed.get("target") or parsed.get("host") or parsed.get("url")
        if not target:
            if sys.stdin.isatty():
                prompt_placeholder = {
                    "HTTP": "https://example.com",
                    "HTTPS": "https://example.com",
                    "PING": "8.8.8.8",
                    "DNS": "8.8.8.8",
                    "TCP": "1.2.3.4:5201",
                    "UDP": "1.2.3.4:5201"
                }.get(ttype, "1.2.3.4")
                try:
                    target = input(f"Enter Target Host/URL (e.g. {prompt_placeholder}): ").strip()
                except (KeyboardInterrupt, EOFError):
                    print()
                    return
            if not target:
                err("Target is required. Usage: experience add --target <host_or_url>")
                return
        
        # 3. Port (optional helper, mostly for TCP/UDP if not in target)
        port = parsed.get("port")
        if port and ":" not in target and ttype in ["TCP", "UDP"]:
            target = f"{target}:{port}"

        # 4. Name
        name = parsed.get("name")
        if not name:
            default_name = f"{ttype} Probe to {target}"
            if sys.stdin.isatty():
                try:
                    name = input(f"Enter Name [{default_name}]: ").strip()
                except (KeyboardInterrupt, EOFError):
                    print()
                    return
            name = name or default_name

        # 5. Timeout (ms)
        timeout_val = parsed.get("timeout")
        default_timeout = {
            "HTTP": 5000,
            "HTTPS": 5000,
            "PING": 2000,
            "DNS": 3000,
            "TCP": 5000,
            "UDP": 5000
        }.get(ttype, 2000)
        
        if not timeout_val:
            if sys.stdin.isatty():
                try:
                    t_str = input(f"Enter Timeout in ms [{default_timeout}]: ").strip()
                    timeout = int(t_str) if t_str else default_timeout
                except ValueError:
                    warn(f"Using default {default_timeout}ms")
                    timeout = default_timeout
                except (KeyboardInterrupt, EOFError):
                    print()
                    return
            else:
                timeout = default_timeout
        else:
            try:
                timeout = int(timeout_val)
            except ValueError:
                err("Timeout must be an integer.")
                return

        # Fetch existing probes list so we don't wipe it out!
        r_get = api_get("/api/connectivity/custom")
        if r_get is None:
            err("Failed to retrieve existing experience probes. Aborting add.")
            return
            
        probes_list = r_get if isinstance(r_get, list) else r_get.get("targets", [])
        
        # Build the new probe dict
        new_probe = {
            "name": name,
            "type": ttype,
            "target": target,
            "timeout": timeout,
            "enabled": True
        }
        
        # Append and POST back
        probes_list.append(new_probe)
        r = api_post("/api/connectivity/custom", {"endpoints": probes_list})
        if r:
            ok(f"Experience target '{name}' added successfully")
            print(f"→ Equivalent CLI: experience add --name \"{name}\" --target \"{target}\" --type \"{ttype}\" --timeout {timeout}")

    elif sub == "remove":
        match_val = args[1] if len(args) > 1 else None
        if not match_val:
            err("Usage: experience remove <index_or_name>")
            return
            
        r_get = api_get("/api/connectivity/custom")
        if r_get is None:
            err("Failed to retrieve existing experience probes.")
            return
        probes_list = r_get if isinstance(r_get, list) else r_get.get("targets", [])
        if not probes_list:
            err("No probes configured.")
            return
            
        # Try matching by index (1-based)
        matched_idx = None
        try:
            val_idx = int(match_val)
            if 1 <= val_idx <= len(probes_list):
                matched_idx = val_idx - 1
        except ValueError:
            pass
            
        # If not index, try matching by name (case-insensitive)
        if matched_idx is None:
            for idx, p in enumerate(probes_list):
                if p.get("name", "").lower() == match_val.lower():
                    matched_idx = idx
                    break
                    
        if matched_idx is None:
            err(f"Probe matching '{match_val}' not found (tried index and name)")
            return
            
        removed_probe = probes_list.pop(matched_idx)
        r = api_post("/api/connectivity/custom", {"endpoints": probes_list})
        if r:
            ok(f"Experience target '{removed_probe.get('name')}' removed")

    elif sub == "probe":
        r = api_get("/api/connectivity/test")
        if r:
            hdr("━━ Connectivity Probes ━━━━━━━━━━━━━━━━━━━")
            results = r if isinstance(r, list) else r.get("results", [r])
            rows    = []
            for probe in results:
                name = probe.get("name") or probe.get("host","?")
                rtt  = probe.get("rtt") or probe.get("latency","?")
                rows.append([name[:25], probe.get("type","?"),
                             str(rtt)+"ms" if rtt != "?" else "?",
                             status_badge(probe.get("status","?"))])
            table(["Target", "Type", "RTT", "Status"], rows)

    elif sub == "export":
        filepath = args[1] if len(args) > 1 else "stigix-probes-export.json"
        r = api_get("/api/connectivity/custom/export")
        if r is None:
            return
        write_json_file(filepath, r)

    elif sub == "import":
        filepath = args[1] if len(args) > 1 else None
        if not filepath:
            err("Usage: experience import <filepath>")
            return
        data = read_json_file(filepath)
        if data is None:
            return
        endpoints = data if isinstance(data, list) else data.get("endpoints")
        if not endpoints:
            err("Invalid format: expected a JSON array or an object containing an 'endpoints' array")
            return
        r = api_post("/api/connectivity/custom", {"endpoints": endpoints})
        if r:
            ok("Experience probes imported successfully")

    elif sub == "stats":
        import re
        stats_data = api_get("/api/connectivity/stats?range=1h")
        results_data = api_get("/api/connectivity/results?timeRange=1h&limit=1500")
        custom_data = api_get("/api/connectivity/custom")
        
        if custom_data is None:
            err("Failed to fetch custom experience probes config.")
            return
            
        probes_config = custom_data if isinstance(custom_data, list) else custom_data.get("targets", [])
        results_list = results_data.get("results", []) if results_data else []
        
        global_health = stats_data.get("globalHealth", 0) if stats_data else 0
        health_color = "32" if global_health >= 80 else ("33" if global_health >= 50 else "31")
        
        score_text = f"Global Score: {global_health:>3}/100"
        padding_total = 78 - len(score_text)
        left_pad = padding_total // 2
        right_pad = padding_total - left_pad
        score_part = c(health_color, f"{global_health}/100")
        row_content = " " * left_pad + "Global Score: " + score_part + " " * right_pad
        
        hdr("╔══════════════════════════════════════════════════════════════════════════════╗")
        hdr("║" + "DIGITAL EXPERIENCE GLOBAL SUMMARY".center(78) + "║")
        hdr("╠══════════════════════════════════════════════════════════════════════════════╣")
        hdr(f"║{row_content}║")
        hdr("╚══════════════════════════════════════════════════════════════════════════════╝")
        print()
        
        # Group results by endpointId
        results_by_id = {}
        for r in results_list:
            eid = r.get("endpointId")
            if eid:
                if eid not in results_by_id:
                    results_by_id[eid] = []
                results_by_id[eid].append(r)
                
        rows = []
        for p in probes_config:
            pname = p.get("name", "Unknown")
            pid = re.sub(r'\s+', '-', pname.lower())
            
            presults = results_by_id.get(pid, [])
            ptype = p.get("type") or (presults[0].get("endpointType") if presults else "HTTP")
            ptarget = p.get("target") or p.get("host") or p.get("url") or (presults[0].get("url") if presults else "---")
            
            enabled = p.get("enabled", True)
            status_str = "ACTIVE" if enabled else "INACTIVE"
            
            if presults:
                last_res = presults[0]
                reachable_results = [r for r in presults if r.get("reachable", False)]
                
                last_score = last_res.get("score", 0)
                
                if reachable_results:
                    avg_score = round(sum(r.get("score", 0) for r in reachable_results) / len(reachable_results))
                    min_score = min(r.get("score", 0) for r in reachable_results)
                    max_score = max(r.get("score", 0) for r in reachable_results)
                    
                    avg_lat = sum(r.get("metrics", {}).get("total_ms", 0) for r in reachable_results) / len(reachable_results)
                    avg_lat_str = f"{avg_lat:.1f}ms" if avg_lat < 10 else f"{avg_lat:.0f}ms"
                else:
                    avg_score = 0
                    min_score = 0
                    max_score = 0
                    avg_lat_str = "---"
                    
                reliability = round((len(reachable_results) / len(presults)) * 100)
            else:
                last_score = 0
                avg_score = 0
                min_score = 0
                max_score = 0
                avg_lat_str = "---"
                reliability = 0
                
            status_color = "32" if enabled else "30"
            status_colored = c(status_color, status_str)
            
            score_color = "32" if last_score >= 80 else ("33" if last_score >= 50 else "31")
            score_str = c(score_color, f"{last_score}")
            score_sub = c("2", f"({avg_score} avg)")
            score_display = f"{score_str} {score_sub}"
            
            rel_color = "32" if reliability >= 95 else ("33" if reliability >= 80 else "31")
            reliability_str = c(rel_color, f"{reliability}%")
            
            rows.append([
                pname[:20],
                ptarget[:30],
                ptype,
                status_colored,
                score_display,
                avg_lat_str,
                reliability_str
            ])
            
        if not rows:
            dim("  No synthetic probes configured")
            return
            
        rows.sort(key=lambda x: x[0].lower())
        table(["Probe Name", "Target/URL", "Type", "Status", "Score", "Latency (avg)", "Reliability"], rows)

    else:
        _help_section("DIGITAL EXPERIENCE", [
            ("experience list",           "List connectivity probe targets"),
            ("experience add",            "Add a new target (interactive or --flags)"),
            ("experience remove <id>",    "Remove a target"),
            ("experience probe",          "Run all probes now"),
            ("experience stats",          "Show historical scores, latency, and reliability"),
            ("experience export [file]",  "Export custom probes to JSON"),
            ("experience import <file>",  "Import custom probes from JSON"),
        ])
        dim("  Flags for add: --name  --host  --type {http,ping,dns}  --port  --timeout")


def cmd_peer(args):
    if not require_auth(): return
    sub = args[0] if args else "list"

    if sub == "list":
        r = api_get("/api/targets")
        if r:
            peers = r if isinstance(r, list) else r.get("targets", [])
            if not peers:
                dim("  No Stigix peers configured")
                return
            rows = []
            for p in peers:
                enabled = "✓" if p.get("enabled", True) else "✗"
                caps = p.get("capabilities", {})
                caps_list = []
                for k, v in caps.items():
                     if v:
                         caps_list.append("failover" if k == "convergence" else k)
                caps_str = ", ".join(caps_list) if caps_list else "none"
                source = p.get("source", "managed")
                rows.append([
                    p.get("id", "")[:12],
                    p.get("name", "")[:20],
                    p.get("host", ""),
                    caps_str,
                    enabled,
                    source
                ])
            table(["ID", "Name", "Host", "Capabilities", "On", "Source"], rows)

    elif sub == "add":
        parsed = parse_flags(args[1:], ["name", "host", "voice", "convergence", "failover", "xfr", "security", "connectivity"])
        name = parsed.get("name") or input("Name (e.g. Branch-1): ").strip()
        host = parsed.get("host") or input("Host (IP or FQDN): ").strip()
        
        voice = str(parsed.get("voice", "true")).lower() == "true"
        failover_val = parsed.get("failover")
        convergence_val = parsed.get("convergence")
        if failover_val is not None:
            failover = str(failover_val).lower() == "true"
        elif convergence_val is not None:
            failover = str(convergence_val).lower() == "true"
        else:
            failover = True
        xfr = str(parsed.get("xfr", "true")).lower() == "true"
        security = str(parsed.get("security", "true")).lower() == "true"
        connectivity = str(parsed.get("connectivity", "true")).lower() == "true"

        if not name or not host:
            err("Name and host are required.")
            return

        body = {
            "name": name,
            "host": host,
            "enabled": True,
            "capabilities": {
                "voice": voice,
                "convergence": failover,
                "xfr": xfr,
                "security": security,
                "connectivity": connectivity
            }
        }
        r = api_post("/api/targets", body)
        if r:
            ok(f"Peer '{name}' added successfully")

    elif sub in ("remove", "enable", "disable"):
        pid = args[1] if len(args) > 1 else None
        if not pid:
            err(f"Usage: peer {sub} <name/id/host>")
            return

        # Fetch targets from server to find match
        targets = api_get("/api/targets")
        if targets is None:
            targets = []
        else:
            targets = targets if isinstance(targets, list) else targets.get("targets", [])

        # Search for matching targets
        matches = []
        for p in targets:
            full_id = p.get("id", "")
            name = p.get("name", "")
            host = p.get("host", "")
            
            # Match by full ID, prefix match, name (case insensitive), or host IP
            if (full_id == pid or 
                (len(pid) >= 4 and full_id.startswith(pid)) or 
                name.lower() == pid.lower() or 
                host == pid):
                matches.append(p)

        if not matches:
            err(f"Peer target '{pid}' not found")
            return
        elif len(matches) > 1:
            err(f"Multiple peers matched '{pid}':")
            for m in matches:
                info(f"  - {m.get('id')[:12]} | {m.get('name')} | {m.get('host')}")
            return

        target = matches[0]
        full_id = target.get("id")
        name = target.get("name")
        host = target.get("host")

        if sub == "remove":
            if sys.stdin.isatty():
                try:
                    confirm = input(f"Are you sure you want to delete peer '{name}' ({host})? [y/N]: ").strip().lower()
                    if confirm != 'y':
                        return
                except (KeyboardInterrupt, EOFError):
                    print()
                    return
            r = api_delete(f"/api/targets/{full_id}")
            if r:
                ok(f"Peer target '{name}' ({host}) removed")
        else:
            body = {"enabled": sub == "enable"}
            r = api_put(f"/api/targets/{full_id}", body)
            if r:
                ok(f"Peer target '{name}' ({host}) {'enabled' if sub == 'enable' else 'disabled'}")

    elif sub == "export":
        filepath = args[1] if len(args) > 1 else "stigix-peers-export.json"
        targets = api_get("/api/targets")
        if targets is None:
            return
        targets_list = targets if isinstance(targets, list) else targets.get("targets", [])
        data_to_export = [{
            "name": t.get("name"),
            "host": t.get("host"),
            "enabled": t.get("enabled"),
            "capabilities": t.get("capabilities"),
            "ports": t.get("ports")
        } for t in targets_list]
        write_json_file(filepath, data_to_export)

    elif sub == "import":
        filepath = args[1] if len(args) > 1 else None
        if not filepath:
            err("Usage: peer import <filepath>")
            return
        data = read_json_file(filepath)
        if data is None:
            return
        targets_to_import = data if isinstance(data, list) else data.get("targets")
        if not targets_to_import:
            err("Invalid format: expected a JSON array or an object containing a 'targets' array")
            return
        r = api_post("/api/targets/import", {"targets": targets_to_import})
        if r:
            ok("Peer targets imported successfully")

    else:
        _help_section("PEER TARGETS", [
            ("peer list",             "List configured Stigix targets/peers"),
            ("peer add",              "Add a new Stigix target manually"),
            ("peer remove <id>",      "Remove a Stigix target"),
            ("peer enable <id>",      "Enable a Stigix target"),
            ("peer disable <id>",     "Disable a Stigix target"),
            ("peer export [file]",    "Export peer targets to JSON"),
            ("peer import <file>",    "Import peer targets from JSON"),
        ])
        dim("  Flags for add: --name  --host  --voice {true,false}  --failover {true,false}")
        dim("                 --xfr {true,false}  --security {true,false}  --connectivity {true,false}")


def cmd_speedtest(args):
    if not require_auth(): return
    sub = args[0] if args else "help"

    if sub in ("list", "history"):
        r = api_get("/api/tests/xfr")
        if r:
            jobs = r if isinstance(r, list) else r.get("jobs", [])
            if not jobs:
                dim("  No speedtest history found")
                return
            rows = []
            for j in jobs[:20]:
                started = j.get("started_at")
                if started:
                    try:
                        ts = started.split("T")[1][:8]
                    except Exception:
                        ts = started
                else:
                    ts = "?"
                params = j.get("params", {})
                host = params.get("host", "?")
                proto = params.get("protocol", "tcp")
                status = j.get("status", "?")
                
                summary = j.get("summary") or {}
                sent = summary.get("sent_mbps", 0)
                recv = summary.get("received_mbps", 0)
                rtt = summary.get("rtt_ms_avg", 0)
                
                rows.append([
                    j.get("sequence_id", j.get("id", ""))[:12],
                    ts,
                    host,
                    proto.upper(),
                    f"{sent:.1f} Tx / {recv:.1f} Rx" if summary else "-",
                    f"{rtt:.1f}ms" if summary else "-",
                    status_badge(status)
                ])
            table(["ID", "Time", "Target", "Proto", "Speed (Mbps)", "RTT", "Status"], rows)

    elif sub == "run":
        # Parse out target host and remaining options
        target_host = None
        remaining_opts = []
        if len(args) > 1:
            first_arg = args[1]
            if not first_arg.startswith("--"):
                target_host = first_arg
                remaining_opts = args[2:]
            else:
                remaining_opts = args[1:]
        else:
            remaining_opts = []

        # If target host not provided, propose available XFR targets or prompt
        if not target_host:
            targets = api_get("/api/targets")
            if targets is None:
                targets = []
            else:
                targets = targets if isinstance(targets, list) else targets.get("targets", [])
            
            xfr_targets = [
                t for t in targets 
                if t.get("enabled", True) and t.get("capabilities", {}).get("xfr")
            ]
            
            if not xfr_targets:
                if sys.stdin.isatty():
                    try:
                        target_host = input("Enter speedtest target host/IP: ").strip()
                    except (KeyboardInterrupt, EOFError):
                        print()
                        return
                    if not target_host:
                        err("Target host/IP cannot be empty. Aborting.")
                        return
                else:
                    err("No speedtest target specified and non-interactive. Usage: speedtest run <target-host> [options]")
                    return
            else:
                if sys.stdin.isatty():
                    print("\nAvailable Speedtest Targets:")
                    for idx, xt in enumerate(xfr_targets, 1):
                        print(f"  {idx}: {xt.get('name')} ({xt.get('host')})")
                    manual_idx = len(xfr_targets) + 1
                    print(f"  {manual_idx}: [Manual IP/Host]")
                    print()
                    try:
                        choice = input("Select target [1]: ").strip()
                        if not choice:
                            idx_choice = 1
                        else:
                            idx_choice = int(choice)
                    except ValueError:
                        err("Invalid choice. Aborting.")
                        return
                    except (KeyboardInterrupt, EOFError):
                        print()
                        return

                    if 1 <= idx_choice <= len(xfr_targets):
                        target_host = xfr_targets[idx_choice - 1].get("host")
                    elif idx_choice == manual_idx:
                        try:
                            target_host = input("Enter speedtest target host/IP: ").strip()
                        except (KeyboardInterrupt, EOFError):
                            print()
                            return
                        if not target_host:
                            err("Target host/IP cannot be empty. Aborting.")
                            return
                    else:
                        err("Invalid index. Aborting.")
                        return
                else:
                    # Non-interactive fallback
                    target_host = xfr_targets[0].get("host")
                    info(f"Auto-selected speedtest target: {target_host} ({xfr_targets[0].get('name')})")
        else:
            # Resolve target name/IP if target_host was provided
            targets = api_get("/api/targets")
            if targets:
                targets_list = targets if isinstance(targets, list) else targets.get("targets", [])
                match = None
                for t in targets_list:
                    if t.get("name", "").lower() == target_host.lower() or t.get("host") == target_host:
                        match = t
                        break
                if match:
                    target_host = match.get("host")

        parsed = parse_flags(remaining_opts, ["port", "protocol", "direction", "duration", "bitrate", "streams", "psk"])

        def prompt_option(name, default_val, validator=None):
            if not sys.stdin.isatty():
                return default_val
            while True:
                try:
                    val = input(f"{name} [{default_val}]: ").strip()
                    if not val:
                        return default_val
                    if validator:
                        valid, parsed_val = validator(val)
                        if valid:
                            return parsed_val
                        else:
                            err(f"Invalid value for {name}. Please try again.")
                    else:
                        return val
                except (KeyboardInterrupt, EOFError):
                    print()
                    raise

        def validate_port(v):
            try:
                p = int(v)
                if 1 <= p <= 65535:
                    return True, p
            except ValueError:
                pass
            return False, None

        def validate_protocol(v):
            p = str(v).strip().lower()
            if p in ("tcp", "udp", "quic"):
                return True, p
            return False, None

        def validate_direction(v):
            d = str(v).strip().lower()
            if d in ("client-to-server", "c2s"):
                return True, "client-to-server"
            if d in ("server-to-client", "s2c"):
                return True, "server-to-client"
            if d in ("bidirectional", "bi"):
                return True, "bidirectional"
            return False, None

        def validate_duration(v):
            try:
                d = int(v)
                if d > 0:
                    return True, d
            except ValueError:
                pass
            return False, None

        def validate_streams(v):
            try:
                s = int(v)
                if s > 0:
                    return True, s
            except ValueError:
                pass
            return False, None

        def validate_bitrate(v):
            v = str(v).strip()
            if v:
                return True, v
            return False, None

        has_cli_flags = len(parsed) > 0

        # Port
        port = None
        if "port" in parsed:
            is_valid, parsed_port = validate_port(parsed["port"])
            if is_valid:
                port = parsed_port
            elif sys.stdin.isatty():
                warn(f"Invalid port '{parsed['port']}' provided on command line.")
                port = prompt_option("Port", 9000, validate_port)
            else:
                port = 9000
        else:
            if not has_cli_flags and sys.stdin.isatty():
                port = prompt_option("Port", 9000, validate_port)
            else:
                port = 9000

        # Protocol
        protocol = None
        if "protocol" in parsed:
            is_valid, parsed_proto = validate_protocol(parsed["protocol"])
            if is_valid:
                protocol = parsed_proto
            elif sys.stdin.isatty():
                warn(f"Invalid protocol '{parsed['protocol']}' provided on command line.")
                protocol = prompt_option("Protocol (tcp/udp/quic)", "tcp", validate_protocol)
            else:
                protocol = "tcp"
        else:
            if not has_cli_flags and sys.stdin.isatty():
                protocol = prompt_option("Protocol (tcp/udp/quic)", "tcp", validate_protocol)
            else:
                protocol = "tcp"

        # Direction
        direction = None
        if "direction" in parsed:
            is_valid, parsed_dir = validate_direction(parsed["direction"])
            if is_valid:
                direction = parsed_dir
            elif sys.stdin.isatty():
                warn(f"Invalid direction '{parsed['direction']}' provided on command line.")
                direction = prompt_option("Direction (client-to-server/server-to-client/bidirectional)", "client-to-server", validate_direction)
            else:
                direction = "client-to-server"
        else:
            if not has_cli_flags and sys.stdin.isatty():
                direction = prompt_option("Direction (client-to-server/server-to-client/bidirectional)", "client-to-server", validate_direction)
            else:
                direction = "client-to-server"

        # Duration
        duration = None
        if "duration" in parsed:
            is_valid, parsed_dur = validate_duration(parsed["duration"])
            if is_valid:
                duration = parsed_dur
            elif sys.stdin.isatty():
                warn(f"Invalid duration '{parsed['duration']}' provided on command line.")
                duration = prompt_option("Duration (sec)", 10, validate_duration)
            else:
                duration = 10
        else:
            if not has_cli_flags and sys.stdin.isatty():
                duration = prompt_option("Duration (sec)", 10, validate_duration)
            else:
                duration = 10

        # Bitrate
        bitrate = None
        if "bitrate" in parsed:
            is_valid, parsed_bit = validate_bitrate(parsed["bitrate"])
            if is_valid:
                bitrate = parsed_bit
            elif sys.stdin.isatty():
                warn(f"Invalid bitrate '{parsed['bitrate']}' provided on command line.")
                bitrate = prompt_option("Bitrate", "200M", validate_bitrate)
            else:
                bitrate = "200M"
        else:
            if not has_cli_flags and sys.stdin.isatty():
                bitrate = prompt_option("Bitrate", "200M", validate_bitrate)
            else:
                bitrate = "200M"

        # Streams
        streams = None
        if "streams" in parsed:
            is_valid, parsed_str = validate_streams(parsed["streams"])
            if is_valid:
                streams = parsed_str
            elif sys.stdin.isatty():
                warn(f"Invalid streams '{parsed['streams']}' provided on command line.")
                streams = prompt_option("Streams", 4, validate_streams)
            else:
                streams = 4
        else:
            if not has_cli_flags and sys.stdin.isatty():
                streams = prompt_option("Streams", 4, validate_streams)
            else:
                streams = 4

        # PSK
        psk = None
        if "psk" in parsed:
            if isinstance(parsed["psk"], bool) and parsed["psk"]:
                if sys.stdin.isatty():
                    psk = prompt_option("PSK (optional)", "")
                else:
                    psk = ""
            else:
                psk = str(parsed["psk"])
        else:
            if not has_cli_flags and sys.stdin.isatty():
                psk = prompt_option("PSK (optional)", "")
            else:
                psk = ""

        is_custom = has_cli_flags or sys.stdin.isatty()

        if is_custom:
            body = {
                "mode": "custom",
                "target": {"host": target_host, "port": port, "psk": psk},
                "protocol": protocol,
                "direction": direction,
                "duration_sec": duration,
                "bitrate": bitrate,
                "parallel_streams": streams
            }
        else:
            body = {
                "mode": "default",
                "target": {"host": target_host, "port": 9000}
            }

        info(f"Starting speedtest to {target_host}:{port} ({protocol.upper()} / {direction})...")
        r = api_post("/api/tests/xfr", body)
        if not r:
            return
            
        job_id = r.get("id")
        seq_id = r.get("sequence_id", job_id)
        ok(f"Speedtest job {seq_id} accepted.")
        
        stream_url = f"/api/tests/xfr/{job_id}/stream?token={JWT_TOKEN}"
        info("Streaming real-time performance metrics (Ctrl+C to stop)...")
        
        try:
            resp = requests.get(f"{STIGIX_URL}{stream_url}", stream=True, timeout=90)
            current_event = None
            for line in resp.iter_lines():
                if not line:
                    continue
                line_str = line.decode('utf-8')
                if line_str.startswith("event:"):
                    current_event = line_str[6:].strip()
                elif line_str.startswith("data:"):
                    data_str = line_str[5:].strip()
                    try:
                        data = json.loads(data_str)
                        if current_event == "interval":
                            sent = data.get("sent_mbps", 0)
                            recv = data.get("received_mbps", 0)
                            rtt = data.get("rtt_ms", 0)
                            loss = data.get("loss_percent", 0)
                            print(f"  Tx: {sent:.1f} Mbps   Rx: {recv:.1f} Mbps   RTT: {rtt:.1f}ms   Loss: {loss:.1f}%")
                        elif current_event == "done":
                            print()
                            status = data.get("status", "completed").upper()
                            if status == "COMPLETED":
                                ok("Speedtest COMPLETED successfully!")
                            else:
                                err(f"Speedtest finished with status: {status}")
                            break
                    except Exception:
                        pass
        except KeyboardInterrupt:
            print()
            warn("Stopped watching speedtest stream.")
        except Exception as e:
            err(f"Stream error: {e}")

    else:
        _help_section("SPEEDTEST / XFR BANDWIDTH", [
            ("speedtest list / history",   "Show past bandwidth test jobs"),
            ("speedtest run <host>",       "Run default speedtest to target host"),
            ("speedtest run <host> [opts]","Run custom speedtest to target host"),
        ])
        dim("  Flags for run: --port  --protocol {tcp,udp,quic}  --direction {client-to-server,")
        dim("                 server-to-client,bidirectional}  --duration  --bitrate  --streams  --psk")


def cmd_failover(args):
    if not require_auth(): return
    sub = args[0] if args else "status"

    if sub == "status":
        r = api_get("/api/convergence/status")
        if isinstance(r, list) and r:
            running_tests = [t for t in r if t.get("running")]
            if running_tests:
                for t in running_tests:
                    ok(f"Running — ID: {t.get('testId','?')}  elapsed: {t.get('elapsed','?')}s")
                    for key in ("loss","blackout","rtt","ppsReceived"):
                        if key in t:
                            print(f"  {key}: {t[key]}")
            else:
                dim("No failover test running")
        else:
            dim("No failover test running")

    elif sub == "start":
        parsed = parse_flags(args[1:], ["target","pps","label"])
        target_host = parsed.get("target")
        pps    = int(parsed.get("pps", 50))
        label  = parsed.get("label", f"CLI-{int(time.time())}")

        # Fetch registry targets to propose/resolve
        targets = api_get("/api/targets")
        if targets is None:
            targets = []
        else:
            targets = targets if isinstance(targets, list) else targets.get("targets", [])

        # Filter targets with failover capability
        conv_targets = [
            t for t in targets
            if t.get("enabled", True) and (t.get("capabilities", {}).get("convergence") or t.get("capabilities", {}).get("failover"))
        ]

        if target_host:
            # Resolve target name/IP if target_host was provided
            match = None
            for t in targets:
                if t.get("name", "").lower() == target_host.lower() or t.get("host") == target_host:
                    match = t
                    break
            if match:
                target_host = match.get("host")
        else:
            # No target host provided: show selection menu or prompt
            if not conv_targets:
                if sys.stdin.isatty():
                    try:
                        target_host = input("Enter failover target IP/Host: ").strip()
                    except (KeyboardInterrupt, EOFError):
                        print()
                        return
                    if not target_host:
                        err("Target IP/Host cannot be empty. Aborting.")
                        return
                else:
                    err("No failover target specified. Usage: failover start --target <host>")
                    return
            else:
                if sys.stdin.isatty():
                    print("\nAvailable Failover Targets:")
                    for idx, ct in enumerate(conv_targets, 1):
                        print(f"  {idx}: {ct.get('name')} ({ct.get('host')})")
                    manual_idx = len(conv_targets) + 1
                    print(f"  {manual_idx}: [Manual IP/Host]")
                    print()
                    try:
                        choice = input("Select target [1]: ").strip()
                        if not choice:
                            idx_choice = 1
                        else:
                            idx_choice = int(choice)
                    except ValueError:
                        err("Invalid choice. Aborting.")
                        return
                    except (KeyboardInterrupt, EOFError):
                        print()
                        return

                    if 1 <= idx_choice <= len(conv_targets):
                        target_host = conv_targets[idx_choice - 1].get("host")
                    elif idx_choice == manual_idx:
                        try:
                            target_host = input("Enter failover target IP/Host: ").strip()
                        except (KeyboardInterrupt, EOFError):
                            print()
                            return
                        if not target_host:
                            err("Target IP/Host cannot be empty. Aborting.")
                            return
                    else:
                        err("Invalid index. Aborting.")
                        return
                else:
                    # Non-interactive fallback
                    target_host = conv_targets[0].get("host")
                    info(f"Auto-selected failover target: {target_host} ({conv_targets[0].get('name')})")

        r = api_post("/api/convergence/start", {"target": target_host, "pps": pps, "label": label})
        if r:
            ok(f"Failover test started: {r.get('testId','?')}")
            STATUS.invalidate()

    elif sub == "stop":
        r = api_post("/api/convergence/stop")
        if r:
            ok("Failover test stopped")
            STATUS.invalidate()

    elif sub == "history":
        limit = int(args[1]) if len(args) > 1 else 10
        r = api_get("/api/convergence/history")
        if r:
            rows = r if isinstance(r, list) else r.get("results", [])
            rows = rows[:limit]
            
            def get_verdict(max_blackout):
                if max_blackout is None:
                    return "?"
                try:
                    mb = float(max_blackout)
                except Exception:
                    return "?"
                if mb == 0:
                    return c("32", "PERFECT")
                if mb < 1000:
                    return c("32", "GOOD")
                if mb < 5000:
                    return c("33", "DEGRADED")
                if mb < 10000:
                    return c("31", "BAD")
                return c("1;31", "CRITICAL")

            history_rows = []
            for row in rows:
                tid = row.get("test_id") or row.get("testId") or "?"
                if " (" in tid:
                    tid = tid.split(" (")[0]
                label = row.get("label", "?")
                tgt = row.get("target", "?")
                max_bo = None
                for key in ("max_blackout_ms", "maxBlackout", "blackout"):
                    if key in row:
                        max_bo = row[key]
                        break
                if max_bo is not None:
                    bo_str = f"{max_bo}ms"
                else:
                    bo_str = "?"
                verd = get_verdict(max_bo)
                history_rows.append([
                    tid,
                    label,
                    tgt,
                    bo_str,
                    verd
                ])
            table(["ID", "Label", "Target", "Blackout", "Verdict"], history_rows)

    elif sub == "endpoints":
        r = api_get("/api/convergence/endpoints")
        if r:
            eps = r if isinstance(r, list) else r.get("endpoints",[])
            table(["Name","IP","Description"], [
                [e.get("name","?"), e.get("ip") or e.get("target","?"), e.get("description","")[:30]]
                for e in eps
            ])

    elif sub == "watch":
        interval = int(args[1]) if len(args) > 1 else 2
        info(f"Failover watch — refresh every {interval}s  (Ctrl+C to stop)")
        try:
            while True:
                do_clear()
                now = datetime.now().strftime("%H:%M:%S")
                hdr(f"━━ Failover Status  [{now}] ━━━━━━━━━━━━━━━━━")
                r = api_get("/api/convergence/status")
                if isinstance(r, list) and r:
                    running_tests = [t for t in r if t.get("running")]
                    if running_tests:
                        for t in running_tests:
                            ok(f"Running — ID: {t.get('testId','?')}  elapsed: {t.get('elapsed','?')}s")
                            for key in ("loss","blackout","rtt","ppsReceived"):
                                if key in t:
                                    info(f"  {key}: {t[key]}")
                    else:
                        dim("  No test running")
                else:
                    dim("  No test running")
                time.sleep(interval)
        except KeyboardInterrupt:
            print()
            ok("Watch stopped")

    else:
        _help_section("FAILOVER MONITORING", [
            ("failover status",          "Show running test state"),
            ("failover start",           "Start failover test (interactive or --flags)"),
            ("failover stop",            "Stop running test"),
            ("failover history [n]",     "Show past test results"),
            ("failover endpoints",       "List saved endpoints"),
            ("failover watch [sec]",     "Live poll test until stopped"),
        ])
        dim("  Flags for start: --target  --pps  --label")


def cmd_vyos(args):
    if not require_auth(): return
    sub = args[0] if args else "list"

    if sub == "list":
        r = api_get("/api/vyos/routers")
        if r:
            routers = r if isinstance(r, list) else r.get("routers", [])
            table(["ID", "Name", "Host", "Status"], [
                [rt.get("id","?")[:10], rt.get("name","?")[:15],
                 rt.get("host","?"), status_badge(rt.get("status","?"))]
                for rt in routers
            ])

    elif sub == "sequences":
        r = api_get("/api/vyos/sequences")
        if r:
            seqs = r if isinstance(r, list) else r.get("sequences", [])
            table(["ID", "Name", "Mode", "Steps"], [
                [s.get("id","?")[:10], s.get("name","?")[:20],
                 s.get("mode","?"), len(s.get("steps",[]))]
                for s in seqs
            ])

    elif sub == "run":
        sid = args[1] if len(args) > 1 else None
        if not sid: err("Usage: vyos run <sequence-id>"); return
        r = api_post(f"/api/vyos/sequences/run/{sid}")
        if r: ok(f"Sequence {sid} started")

    elif sub == "stop":
        sid = args[1] if len(args) > 1 else None
        if not sid: err("Usage: vyos stop <sequence-id>"); return
        r = api_post(f"/api/vyos/sequences/stop/{sid}")
        if r: ok(f"Sequence {sid} stopped")

    elif sub == "history":
        limit = int(args[1]) if len(args) > 1 else 15
        r = api_get("/api/vyos/history")
        if r:
            items = r if isinstance(r, list) else r.get("history", [])
            rows  = []
            for item in items[:limit]:
                ts = datetime.fromtimestamp(item["timestamp"]/1000).strftime("%H:%M:%S") if "timestamp" in item else "?"
                rows.append([ts, item.get("router","?")[:10],
                             item.get("command","?")[:20],
                             status_badge(item.get("status","?"))])
            table(["Time", "Router", "Command", "Status"], rows)

    else:
        _help_section("VyOS CONTROL", [
            ("vyos list",            "List configured routers"),
            ("vyos sequences",       "List action sequences"),
            ("vyos run <id>",        "Execute a sequence"),
            ("vyos stop <id>",       "Stop a sequence"),
            ("vyos history [n]",     "Show execution history"),
        ])


def cmd_voice(args):
    if not require_auth(): return
    sub = args[0] if args else "status"

    if sub == "status":
        r = api_get("/api/voice/status")
        if r:
            running = r.get("enabled") or r.get("running") or r.get("active", False)
            if running:
                ok(f"Voice simulation active — running calls in background (max_simultaneous={r.get('max_simultaneous_calls', 3)})")
            else:
                dim("Voice simulation is stopped")

    elif sub == "start":
        parsed = parse_flags(args[1:], ["target"])
        target = parsed.get("target")

        # 1. Fetch available voice targets from registry
        targets = api_get("/api/targets")
        if targets is None:
            targets = []
        else:
            targets = targets if isinstance(targets, list) else targets.get("targets", [])
        
        voice_targets = [
            t for t in targets 
            if t.get("enabled", True) and t.get("capabilities", {}).get("voice")
        ]

        selected_targets = []

        if not voice_targets:
            warn("No enabled peer targets with voice capability found in registry.")
            if sys.stdin.isatty() and not target:
                try:
                    choice = input("Start voice simulation daemon with default settings? [y/N]: ").strip().lower()
                    if choice != 'y':
                        return
                except (KeyboardInterrupt, EOFError):
                    print()
                    return
        else:
            # We have voice targets! Decide which to simulate.
            if target:
                if target.lower() == "all":
                    selected_targets = voice_targets
                else:
                    # Find by name or host IP
                    match = None
                    for vt in voice_targets:
                        if vt.get("name", "").lower() == target.lower() or vt.get("host") == target:
                            match = vt
                            break
                    if match:
                        selected_targets = [match]
                    else:
                        # Fallback: treat target as a raw IP/host
                        selected_targets = [{"name": target, "host": target, "ports": {"voice": 6100}}]
            elif sys.stdin.isatty():
                # Interactive target selection menu
                print("\nAvailable Voice Targets:")
                print("  0: [All Targets] (Simulate all concurrently)")
                for idx, vt in enumerate(voice_targets, 1):
                    print(f"  {idx}: {vt.get('name')} ({vt.get('host')})")
                
                print()
                try:
                    choice = input("Select target [0]: ").strip()
                    if not choice:
                        idx_choice = 0
                    else:
                        idx_choice = int(choice)
                except ValueError:
                    err("Invalid choice. Aborting.")
                    return
                except (KeyboardInterrupt, EOFError):
                    print()
                    return

                if idx_choice == 0:
                    selected_targets = voice_targets
                elif 1 <= idx_choice <= len(voice_targets):
                    selected_targets = [voice_targets[idx_choice - 1]]
                else:
                    err("Invalid index. Aborting.")
                    return
            else:
                # Non-interactive headless fallback: default to all available targets
                selected_targets = voice_targets

        # 2. Sync selected targets to voice configuration
        if selected_targets:
            # Get current config to preserve existing custom codecs/weights/durations
            cfg = api_get("/api/voice/config")
            current_servers = {}
            control_settings = {}
            if cfg and cfg.get("success"):
                control_settings = cfg.get("control", {})
                servers_str = cfg.get("servers", "")
                # Parse current servers string
                for line in servers_str.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("|")
                    if parts:
                        current_servers[parts[0]] = parts

            # Rebuild servers configuration string
            new_lines = []
            for st in selected_targets:
                host = st.get("host")
                port = st.get("ports", {}).get("voice") or 6100
                key = f"{host}:{port}"
                
                # Check if it was already configured
                if key in current_servers:
                    new_lines.append("|".join(current_servers[key]))
                else:
                    # Defaults: G.711-ulaw, weight 50, duration 30
                    new_lines.append(f"{key}|G.711-ulaw|50|30")
            
            new_servers_str = "\n".join(new_lines)
            
            # Post updated config to server
            api_post("/api/voice/config", {
                "servers": new_servers_str,
                "control": control_settings
            })
            
            targets_desc = "all targets" if len(selected_targets) > 1 else selected_targets[0].get("name")
            info(f"Synchronized voice target configuration ({targets_desc}).")

        # 3. Start the voice simulation daemon
        r = api_post("/api/voice/control", {"enabled": True})
        if r:
            ok("Voice simulation daemon started successfully.")

    elif sub == "stop":
        r = api_post("/api/voice/control", {"enabled": False})
        if r: ok("Voice simulation daemon stopped")

    elif sub == "stats":
        r = api_get("/api/voice/stats")
        if r and isinstance(r, dict) and r.get("success"):
            stats_list = r.get("stats", [])
            
            # Fetch targets from registry to map host/IP to site name
            targets = api_get("/api/targets")
            targets_list = []
            if targets:
                targets_list = targets if isinstance(targets, list) else targets.get("targets", [])
                
            # Map host:port -> friendly site name
            target_names = {}
            for t in targets_list:
                name = t.get("name")
                host = t.get("host")
                vport = t.get("ports", {}).get("voice") or 6100
                if name and host:
                    target_names[f"{host}:{vport}"] = name

            def get_target_name(target_str):
                if target_str in target_names:
                    return target_names[target_str]
                # Fallback: matching IP only
                ip = target_str.split(":")[0] if ":" in target_str else target_str
                for t in targets_list:
                    if t.get("host") == ip:
                        return t.get("name")
                return "Manual"

            def derive_source_port(call_id):
                if call_id and call_id.startswith('CALL-'):
                    try:
                        num = int(call_id[5:])
                        return str(30000 + (num % 10000))
                    except ValueError:
                        pass
                return '?'

            def format_time(ts_str):
                if not ts_str:
                    return "?"
                try:
                    if "T" in ts_str:
                        return ts_str.split("T")[1][:8]
                    return ts_str[:8]
                except Exception:
                    return ts_str

            def quality_badge(q):
                if q == "EXCELLENT":
                    return c("32", "● EXCELLENT")
                elif q == "FAIR":
                    return c("33", "● FAIR")
                else:
                    return c("31", "● POOR")

            # Filter ended calls with valid QoS metrics
            fin = [c_obj for c_obj in stats_list if c_obj.get("event") == "end" and c_obj.get("loss_pct") is not None]

            # 1. Render Overall QoS Summary
            hdr("━━ Voice / VoIP QoS Summary ━━━━━━━━━━━━━━━━━━")
            if not fin:
                print("  Total Calls : 0")
                print("  Avg MOS     : ?")
                print("  Avg Jitter  : ?ms")
                print("  Packet Loss : ?%")
                print("  Avg RTT     : ?ms")
            else:
                avg_loss = sum(c_obj.get("loss_pct", 0) for c_obj in fin) / len(fin)
                rtts = [c_obj.get("avg_rtt_ms", 0) for c_obj in fin if c_obj.get("avg_rtt_ms")]
                avg_rtt = sum(rtts) / len(rtts) if rtts else 0.0
                jitters = [c_obj.get("jitter_ms", 0) for c_obj in fin if c_obj.get("jitter_ms")]
                avg_jitter = sum(jitters) / len(jitters) if jitters else 0.0
                mos_scores = [c_obj.get("mos_score", 0) for c_obj in fin if c_obj.get("mos_score")]
                avg_mos = sum(mos_scores) / len(mos_scores) if mos_scores else 0.0
                
                overall_q = "EXCELLENT" if avg_loss < 1 and avg_rtt < 100 else "FAIR" if avg_loss < 5 and avg_rtt < 200 else "POOR"
                mos_color = "32" if avg_mos >= 4.0 else "33" if avg_mos >= 3.0 else "31"
                
                print(f"  Total Calls : {len(fin)}")
                print(f"  Avg MOS     : {c(mos_color, f'{avg_mos:.2f}')} ({overall_q})")
                print(f"  Avg Jitter  : {avg_jitter:.1f}ms")
                print(f"  Packet Loss : {avg_loss:.1f}%")
                print(f"  Avg RTT     : {avg_rtt:.1f}ms")
            print()

            # 2. Render Per-Target QoS Statistics Table
            hdr("━━ Per-Target QoS Statistics ━━━━━━━━━━━━━━━━━━")
            if not fin:
                dim("  (no stats data available)")
            else:
                grouped = {}
                for call_obj in fin:
                    tgt = call_obj.get("target")
                    if not tgt:
                        continue
                    if tgt not in grouped:
                        grouped[tgt] = []
                    grouped[tgt].append(call_obj)

                pt_rows = []
                for tgt, t_calls in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
                    calls_count = len(t_calls)
                    t_loss = sum(c_obj.get("loss_pct", 0) for c_obj in t_calls) / calls_count
                    t_rtts = [c_obj.get("avg_rtt_ms", 0) for c_obj in t_calls if c_obj.get("avg_rtt_ms")]
                    t_avg_rtt = sum(t_rtts) / len(t_rtts) if t_rtts else 0.0
                    t_jitters = [c_obj.get("jitter_ms", 0) for c_obj in t_calls if c_obj.get("jitter_ms")]
                    t_avg_jitter = sum(t_jitters) / len(t_jitters) if t_jitters else 0.0
                    t_mos_scores = [c_obj.get("mos_score", 0) for c_obj in t_calls if c_obj.get("mos_score")]
                    t_avg_mos = sum(t_mos_scores) / len(t_mos_scores) if t_mos_scores else 0.0
                    
                    t_q = "EXCELLENT" if t_loss < 1 and t_avg_rtt < 100 else "FAIR" if t_loss < 5 and t_avg_rtt < 200 else "POOR"
                    t_name = get_target_name(tgt)
                    
                    pt_rows.append([
                        t_name,
                        tgt,
                        str(calls_count),
                        f"{t_loss:.1f}%",
                        f"{t_avg_rtt:.1f}ms",
                        f"{t_avg_mos:.2f}" if t_avg_mos else "N/A",
                        f"{t_avg_jitter:.1f}ms",
                        quality_badge(t_q)
                    ])
                table(["Site", "Endpoint", "Calls", "Avg Loss", "Avg RTT", "Avg MOS", "Avg Jitter", "Quality"], pt_rows)
            print()

            # 3. Render Call History Table
            hdr("━━ Call History (Recent Events) ━━━━━━━━━━━━━━━━━━")
            history_events = [c_obj for c_obj in stats_list if c_obj.get("event") in ("start", "end", "skipped")]
            if not history_events:
                dim("  (no history events available)")
            else:
                history_rows = []
                for item in history_events[:15]:
                    t_str = format_time(item.get("timestamp"))
                    call_id = item.get("call_id", "?")
                    disp = f"#{call_id}"
                    evt = item.get("event")
                    if evt == "start":
                        status = c("36", "RUNNING")
                    elif evt == "skipped":
                        status = c("33", "SKIPPED")
                    else:
                        status = c("32", "COMPLETED")
                    
                    tgt = item.get("target", "?")
                    site = get_target_name(tgt)
                    sp = derive_source_port(call_id)
                    
                    if evt == "end" and item.get("loss_pct") is not None:
                        loss_val = item.get("loss_pct", 0)
                        loss_color = "32" if loss_val < 1 else "33" if loss_val < 5 else "31"
                        loss_mos = f"{c(loss_color, f'{loss_val:.1f}%')}"
                        if item.get("mos_score") is not None:
                            mos_val = item.get("mos_score")
                            mos_color = "32" if mos_val >= 4 else "33" if mos_val >= 3 else "31"
                            loss_mos += f" (MOS: {c(mos_color, f'{mos_val:.2f}')})"
                    else:
                        loss_mos = "─"
                    
                    if evt == "end" and item.get("avg_rtt_ms") is not None:
                        rtt_val = item.get("avg_rtt_ms", 0)
                        rtt_color = "32" if rtt_val < 100 else "33" if rtt_val < 200 else "31"
                        rtt_jitter = c(rtt_color, f"{rtt_val:.1f}ms")
                        if item.get("jitter_ms") is not None:
                            rtt_jitter += f" (Jitter: {item.get('jitter_ms'):.1f}ms)"
                    else:
                        rtt_jitter = "─"
                    
                    history_rows.append([
                        t_str,
                        disp,
                        status,
                        site,
                        tgt,
                        sp,
                        loss_mos,
                        rtt_jitter
                    ])
                table(["Time", "Call ID", "Status", "Site", "Endpoint", "Src Port", "Loss / MOS", "RTT / Jitter"], history_rows)

    else:
        _help_section("VOICE / VoIP", [
            ("voice start",    "Start global VoIP simulation daemon (calls all enabled targets)"),
            ("voice stop",     "Stop VoIP simulation daemon"),
            ("voice status",   "Show VoIP simulation status"),
            ("voice stats",    "Show MOS / jitter / loss stats"),
        ])


def cmd_iot(args):
    if not require_auth(): return
    sub = args[0] if args else "list"

    if sub == "list":
        r = api_get("/api/iot/devices")
        if r:
            devices = r if isinstance(r, list) else r.get("devices", [])
            rows    = []
            for d in devices:
                running = "✓" if d.get("running") else "✗"
                rows.append([
                    d.get("id","?")[:12], d.get("name","?")[:20],
                    d.get("vendor","?")[:12], d.get("protocol","?"), running
                ])
            table(["ID", "Name", "Vendor", "Protocol", "Run"], rows)

    elif sub == "start":
        did = args[1] if len(args) > 1 else None
        if not did:
            r = api_post("/api/iot/start-batch")
            if r: ok("All IoT devices started")
        else:
            r = api_post(f"/api/iot/start/{did}")
            if r: ok(f"Device {did} started")

    elif sub == "stop":
        did = args[1] if len(args) > 1 else None
        if not did:
            r = api_post("/api/iot/stop-batch")
            if r: ok("All IoT devices stopped")
        else:
            r = api_post(f"/api/iot/stop/{did}")
            if r: ok(f"Device {did} stopped")

    elif sub == "stats":
        r = api_get("/api/iot/stats")
        if r:
            hdr("━━ IoT Stats ━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            rows = [(k, v) for k, v in r.items() if not isinstance(v, (dict, list))]
            table(["Metric","Value"], rows)

    elif sub == "vulns":
        limit = int(args[1]) if len(args) > 1 else 20
        r = api_get(f"/api/iot/vulnerabilities?limit={limit}")
        if r:
            hdr("━━ IoT Vulnerabilities ━━━━━━━━━━━━━━━━━━━")
            items = r if isinstance(r, list) else r.get("vulnerabilities", [])
            rows  = []
            for v in items[:limit]:
                rows.append([
                    v.get("deviceId","?")[:12],
                    v.get("severity","?")[:8],
                    v.get("cve","?")[:15],
                    v.get("description","")[:35],
                ])
            table(["Device", "Severity", "CVE", "Description"], rows)

    else:
        _help_section("IoT SIMULATION", [
            ("iot list",          "List simulated devices"),
            ("iot start [id]",    "Start one or all devices"),
            ("iot stop [id]",     "Stop one or all devices"),
            ("iot stats",         "Show simulation stats"),
            ("iot vulns [n]",     "Show vulnerability findings"),
        ])


def cmd_system(args):
    if not require_auth(): return
    sub = args[0] if args else "info"

    if sub == "info":
        hdr("━━ System Info ━━━━━━━━━━━━━━━━━━━━━━━━━━")
        r = api_get("/api/admin/system/dashboard-data")
        if r:
            for k, v in r.items():
                if not isinstance(v, (dict, list)):
                    info(f"{k}: {v}")
        health = api_get("/api/system/health")
        if health:
            mem  = health.get("memory", {})
            disk = health.get("disk", {})
            print(f"  Memory  : {mem.get('percentage','?')}%  "
                  f"({mem.get('used',0)//1024//1024}MB / {mem.get('total',0)//1024//1024}MB)")
            print(f"  Disk    : {disk.get('percentage','?')}%  "
                  f"({disk.get('used',0)//1024//1024//1024}GB / {disk.get('total',0)//1024//1024//1024}GB)")

    elif sub == "restart":
        confirm = input("Restart Stigix containers? [y/N]: ").strip().lower()
        if confirm == "y":
            r = api_post("/api/admin/maintenance/restart")
            if r: ok("Restart initiated")
        else:
            dim("Cancelled")

    elif sub == "upgrade":
        confirm = input("Pull latest Docker image and upgrade? [y/N]: ").strip().lower()
        if confirm == "y":
            r = api_post("/api/admin/maintenance/upgrade")
            if r: ok("Upgrade initiated")
        else:
            dim("Cancelled")

    elif sub == "interfaces":
        r = api_get("/api/system/interfaces")
        if r:
            ifaces = r if isinstance(r, list) else r.get("interfaces", [])
            for iface in ifaces:
                n = iface if isinstance(iface, str) else iface.get("name","?")
                info(n)

    elif sub == "logs":
        r = api_get("/api/logs")
        if r:
            lines = r if isinstance(r, list) else r.get("lines", [])
            for line in lines[-30:]:
                dim(line)

    else:
        _help_section("SYSTEM", [
            ("system info",          "System health, memory, disk"),
            ("system interfaces",    "List network interfaces"),
            ("system logs",          "Show backend logs (last 30 lines)"),
            ("system restart",       "Restart Stigix containers"),
            ("system upgrade",       "Pull latest Docker image"),
        ])


def cmd_connect(args):
    """Connect to a Stigix instance by IP/URL or by saved profile name.

    connect                       — show current instance + saved profiles
    connect <ip[:port]|url>       — connect to instance (tests reachability)
    connect save <name> [url]     — save current (or given) URL as a named profile
    connect forget <name>         — delete a saved profile
    connect list                  — list all saved profiles
    """
    global STIGIX_URL, JWT_TOKEN, PROFILES, INSTANCE_TOKENS

    sub = args[0] if args else None

    # ── connect (no args) — show current + profiles ──────────────────────────
    if not sub:
        host = STIGIX_URL.replace("https://","").replace("http://","")
        print(f"  Current  : {c('1;36', host)}  {'(' + c('32','authenticated') + ')' if JWT_TOKEN else c('33','no auth')}")
        if PROFILES:
            print()
            hdr("  Saved profiles:")
            for name, prof in PROFILES.items():
                u = prof.get("url","?")
                has_tok = "✓ token" if prof.get("token") else "  no token"
                active  = " ◀ active" if u == STIGIX_URL else ""
                print(f"    {c('36', name):<20}  {u:<30}  {dim(has_tok)}{c('32', active)}")
        else:
            dim("  No saved profiles — use: connect save <name>")
        return

    # ── connect list ─────────────────────────────────────────────────────────
    if sub == "list":
        if not PROFILES:
            dim("No saved profiles")
            return
        rows = []
        for name, prof in PROFILES.items():
            u       = prof.get("url","?")
            has_tok = "✓" if prof.get("token") else "✗"
            active  = "◀" if u == STIGIX_URL else ""
            rows.append([name, u, has_tok, active])
        table(["Name", "URL", "Token", ""], rows)
        return

    # ── connect save <name> [url] ─────────────────────────────────────────────
    if sub == "save":
        name = args[1] if len(args) > 1 else None
        if not name:
            err("Usage: connect save <name> [url]"); return
        url  = args[2] if len(args) > 2 else STIGIX_URL
        if not url.startswith("http"):
            url = f"http://{url}"
        # Save current token only if the URL matches current session
        tok = JWT_TOKEN if url == STIGIX_URL else PROFILES.get(name, {}).get("token")
        PROFILES[name] = {"url": url, "token": tok}
        save_session()
        ok(f"Profile '{name}' saved → {url}")
        return

    # ── connect forget <name> ─────────────────────────────────────────────────
    if sub == "forget":
        name = args[1] if len(args) > 1 else None
        if not name:
            err("Usage: connect forget <name>"); return
        if name not in PROFILES:
            err(f"No profile named '{name}'"); return
        del PROFILES[name]
        save_session()
        ok(f"Profile '{name}' removed")
        return

    # ── connect <name-or-url> ─────────────────────────────────────────────────
    # Check if the argument matches a saved profile name first
    if sub in PROFILES:
        prof = PROFILES[sub]
        url  = prof["url"]
        tok  = prof.get("token")
        info(f"Connecting to profile '{sub}' → {url}")
    else:
        url = sub
        if not url.startswith("http"):
            # Bare IP or hostname — add port 8080 if no port given
            if ":" not in url.split("/")[-1]:
                url = f"http://{url}:8080"
            else:
                url = f"http://{url}"
        tok = INSTANCE_TOKENS.get(url)

    old_url = STIGIX_URL
    old_tok = JWT_TOKEN
    STIGIX_URL = url
    JWT_TOKEN  = tok  # restore profile token (may be None)

    r = api_get("/api/version")
    if r:
        # Update profile token after successful connect (token may come from profile)
        if sub in PROFILES:
            PROFILES[sub]["token"] = JWT_TOKEN
        save_session()
        STATUS.invalidate()
        ver = r.get("version","?")
        if JWT_TOKEN:
            ok(f"Connected to {url} — version {ver}  (token restored, session saved)")
        else:
            ok(f"Connected to {url} — version {ver}")
            warn("No token for this instance — run: auth login")
    else:
        warn(f"Could not reach {url}, reverting to {old_url}")
        STIGIX_URL = old_url
        JWT_TOKEN  = old_tok


def cmd_help(args):
    """Full help screen."""
    do_clear()
    hdr("╔══════════════════════════════════════════════════════════╗")
    hdr(f"║  stigix-cli v{VERSION:<8} (Beta) — Stigix Local Console      ║")
    hdr("╚══════════════════════════════════════════════════════════╝")
    print(f"""
  {c('1','GENERAL')}
    connect                Connect to instance (show current + profiles)
    connect <ip[:port]>    Connect to any Stigix instance by IP
    connect <name>         Connect to a saved profile
    connect save <name>    Save current instance as named profile
    connect forget <name>  Remove a saved profile
    connect list           List all saved profiles
    status                 Global overview: backend, traffic, public IP
    auth login|logout      Authenticate / clear session

  {c('1','TRAFFIC')}
    traffic start|stop     Enable / disable traffic generation
    traffic status|stats   Show traffic state, rate, and active apps dashboard
    traffic logs           Show last log lines
    traffic reset          Reset statistics
    traffic watch [sec]    {c('36','Live watch dashboard & real-time rate (use --all to show all apps)')}
    traffic export [file]  Export traffic configuration to JSON
    traffic import <file>  Import traffic configuration from JSON

  {c('1','SECURITY')}
    security status        Blocked / allowed aggregate stats
    security url <url>     Test a single URL
    security url-batch     Test all enabled URL categories
    security dns <domain>  Test a DNS domain
    security dns-batch     Test all enabled DNS domains
    security eicar [ip]    EICAR Threat Prevention test
    security suite         {c('36','Run full security test suite')}
    security results [n]   Last N results (default 20)
    security clear         Clear history

  {c('1','DIGITAL EXPERIENCE')}
    experience list        List connectivity probe targets
    experience stats       Show historical scores, latency, and reliability
    experience add         Add a new target (--name --host --type --port)
    experience remove <id> Remove a target
    experience probe       Run all probes now
    experience export [f]  Export custom probes to JSON
    experience import <f>  Import custom probes from JSON

  {c('1','PEER TARGETS')}
    peer list              List configured Stigix targets/peers
    peer add               Add a Stigix target manually (--name --host)
    peer remove <id>       Remove a Stigix target
    peer enable <id>       Enable a Stigix target
    peer disable <id>      Disable a Stigix target
    peer export [file]     Export peer targets to JSON
    peer import <file>     Import peer targets from JSON

  {c('1','SPEEDTEST / XFR BANDWIDTH')}
    speedtest list         Show past speedtest jobs
    speedtest run <host>   Run speedtest (--port --protocol --direction)

  {c('1','FAILOVER MONITORING')}
    failover start      Start failover test  (--target --pps --label)
    failover stop       Stop running test
    failover status     Running test state
    failover history    Past test results
    failover endpoints  Saved endpoints
    failover watch [s]  {c('36','Live poll until Ctrl+C')}

  {c('1','VOICE / VoIP')}
    voice start            Start global VoIP simulation daemon
    voice stop             Stop VoIP simulation daemon
    voice status           Show VoIP simulation status
    voice stats            MOS / jitter / loss stats

  {c('1','VyOS CONTROL')}
    vyos list              Configured routers
    vyos sequences         Action sequences
    vyos run <id>          Execute a sequence
    vyos stop <id>         Stop a sequence
    vyos history [n]       Execution history

  {c('1','IoT SIMULATION')}
    iot list               Simulated devices
    iot start [id]         Start one or all
    iot stop [id]          Stop one or all
    iot stats              Simulation stats
    iot vulns [n]          Vulnerability findings

  {c('1','SYSTEM')}
    system info            Health, memory, disk
    system interfaces      Network interfaces
    system logs            Backend logs (last 30 lines)
    system restart         Restart containers
    system upgrade         Pull latest Docker image

  {c('1','OTHER')}
    help / ?               This screen
    exit / quit            Exit stigix-cli

  {c('2','KEYBOARD SHORTCUTS')}
    F1                     Help
    F5                     Status
    Ctrl+L                 Clear screen
    Tab                    Autocomplete
    ↑ / ↓                  Command history

  {c('2','TIPS')}
    Session is saved to ~/.stigix-cli.json (auto-loaded on start)
    Set STIGIX_URL=http://host:port to change default instance
    stigix-cli --exec "security suite"  for headless / scripted use
""")


# ─── Inline help helper ───────────────────────────────────────────────────────

def _help_section(title, cmds):
    hdr(f"━━ {title} ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    w = max(len(cmd) for cmd, _ in cmds) + 2
    for cmd, desc in cmds:
        print(f"  {c('36', cmd):<{w+12}}  {desc}")


# ─── Utility ──────────────────────────────────────────────────────────────────

def parse_flags(args, keys):
    result = {}
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--"):
            k = a[2:]
            if k in keys:
                result[k] = args[i+1] if i+1 < len(args) else True
                i += 2
                continue
        i += 1
    return result


class StigixCompleter(Completer):
    def __init__(self, tree):
        self.tree = tree

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        words = text.split()
        if not text:
            for cmd in self.tree.keys():
                yield Completion(cmd, start_position=0)
            return

        in_space = text.endswith(' ')
        current_word = words[-1] if not in_space else ""
        prefix_words = words[:-1] if not in_space else words

        if len(prefix_words) == 0:
            for cmd in self.tree.keys():
                if cmd.startswith(current_word):
                    yield Completion(cmd, start_position=-len(current_word))
            return

        cmd = prefix_words[0].lower()
        if cmd not in self.tree or self.tree[cmd] is None:
            return

        if len(prefix_words) == 1:
            subcmds = self.tree[cmd]
            if isinstance(subcmds, dict):
                for sub in subcmds.keys():
                    if sub.startswith(current_word):
                        yield Completion(sub, start_position=-len(current_word))
            return

        subcmd = prefix_words[1].lower()
        subcmds = self.tree[cmd]
        if not isinstance(subcmds, dict) or subcmd not in subcmds:
            return

        options = subcmds[subcmd]
        if not isinstance(options, dict):
            return

        last_word = prefix_words[-1] if len(prefix_words) > 0 else ""
        if last_word in options and isinstance(options[last_word], (set, list, dict)):
            choices = options[last_word]
            for choice in choices:
                if choice.startswith(current_word):
                    yield Completion(choice, start_position=-len(current_word))
            return

        typed_flags = set(w for w in prefix_words if w.startswith('--'))
        for flag in options.keys():
            if flag.startswith('--') and flag not in typed_flags:
                if flag.startswith(current_word):
                    yield Completion(flag, start_position=-len(current_word))


DISPATCH = {
    "auth":        cmd_auth,
    "status":      cmd_status,
    "traffic":     cmd_traffic,
    "security":    cmd_security,
    "experience":  cmd_experience,
    "target":      cmd_experience,
    "peer":        cmd_peer,
    "speedtest":   cmd_speedtest,
    "failover":    cmd_failover,
    "convergence": cmd_failover,
    "vyos":        cmd_vyos,
    "voice":       cmd_voice,
    "iot":         cmd_iot,
    "system":      cmd_system,
    "connect":     cmd_connect,
    "help":        cmd_help,
    "?":           cmd_help,
}

COMPLETER_TREE = {
    "auth":        {"login": None, "logout": None, "status": None},
    "status":      None,
    "connect":     {"list": None, "save": None, "forget": None},
    "traffic":     {
        "start": None, "stop": None, "status": None,
        "stats": None, "logs": None, "reset": None, "watch": None,
        "import": None, "export": None,
    },
    "security":    {
        "status": None, "url": None, "url-batch": None,
        "dns": None, "dns-batch": None, "eicar": None,
        "suite": None, "results": None, "clear": None,
    },
    "experience":  {
        "list": None, "probe": None, "remove": None,
        "import": None, "export": None,
        "add":  {"--name": None, "--target": None, "--host": None, "--url": None,
                 "--type": {"http", "https", "ping", "icmp", "tcp", "udp", "dns"},
                 "--port": None, "--timeout": None},
    },
    "target":      {
        "list": None, "probe": None, "remove": None,
        "import": None, "export": None,
        "add":  {"--name": None, "--target": None, "--host": None, "--url": None,
                 "--type": {"http", "https", "ping", "icmp", "tcp", "udp", "dns"},
                 "--port": None, "--timeout": None},
    },
    "peer":        {
        "list": None, "remove": None, "enable": None, "disable": None,
        "import": None, "export": None,
        "add":  {"--name": None, "--host": None,
                 "--voice": {"true", "false"},
                 "--convergence": {"true", "false"},
                 "--failover": {"true", "false"},
                 "--xfr": {"true", "false"},
                 "--security": {"true", "false"},
                 "--connectivity": {"true", "false"}},
    },
    "speedtest":   {
        "list": None, "history": None,
        "run":  {"--port": None,
                 "--protocol": {"tcp", "udp", "quic"},
                 "--direction": {"client-to-server", "server-to-client", "bidirectional"},
                 "--duration": None, "--bitrate": None, "--streams": None, "--psk": None},
    },
    "failover": {
        "status": None, "stop": None, "history": None,
        "endpoints": None, "watch": None,
        "start": {"--target": None, "--pps": None, "--label": None},
    },
    "convergence": {
        "status": None, "stop": None, "history": None,
        "endpoints": None, "watch": None,
        "start": {"--target": None, "--pps": None, "--label": None},
    },
    "vyos":        {"list": None, "sequences": None, "run": None, "stop": None, "history": None},
    "voice":       {
        "status": None, "stop": None, "stats": None, "start": None,
    },
    "iot":         {"list": None, "start": None, "stop": None, "stats": None, "vulns": None},
    "system":      {"info": None, "interfaces": None, "logs": None, "restart": None, "upgrade": None},
    "help":        None,
    "?":           None,
    "exit":        None,
    "quit":        None,
}

# ─── Main loop ────────────────────────────────────────────────────────────────

def run_command(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return
    import shlex
    try:
        parts = shlex.split(line)
    except ValueError:
        parts = line.split()
    cmd    = parts[0].lower()
    rest   = parts[1:]
    if cmd in ("exit", "quit"):
        print("Goodbye.")
        sys.exit(0)
    handler = DISPATCH.get(cmd)
    if handler:
        try:
            handler(rest)
        except KeyboardInterrupt:
            print()
            warn("Interrupted")
    else:
        err(f"Unknown command: '{cmd}'  (type 'help' or '?' for list)")


def _prompt_text():
    """Dynamic prompt — changes colour based on auth state."""
    host = STIGIX_URL.replace("https://","").replace("http://","")
    if JWT_TOKEN:
        return HTML(f"<prompt>stigix</prompt><b>@</b><prompt>{host}</prompt><b> › </b>")
    else:
        return HTML(f"<warn>stigix</warn><b>@</b><warn>{host}</warn><b> ! </b>")


def run_interactive():
    do_clear()
    hdr("╔══════════════════════════════════════════════╗")
    hdr(f"║  stigix-cli v{VERSION:<8} (Beta) local console   ║")
    hdr("╚══════════════════════════════════════════════╝")
    info(f"Target  : {STIGIX_URL}")
    if JWT_TOKEN:
        ok(f"Session : token loaded from {CONFIG_FILE}")
    else:
        warn("Not authenticated — run: auth login")
    dim("Type 'help' for commands, F1 for help, F5 for status")
    print()

    # Kick off initial toolbar data fetch in background
    STATUS.invalidate()
    STATUS.refresh()

    if not HAS_PROMPT_TOOLKIT:
        # ── Fallback: plain input() ───────────────────────────────────────────
        while True:
            try:
                line = input(f"stigix@{STIGIX_URL}{'!' if not JWT_TOKEN else ''} > ")
                run_command(line)
            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                print("\nGoodbye.")
                break
        return

    # ── prompt_toolkit REPL ───────────────────────────────────────────────────
    style = Style.from_dict({
        "prompt":  "#4dd0e1 bold",
        "warn":    "#FFA726 bold",
        "b":       "bold",
    })

    completer = StigixCompleter(COMPLETER_TREE)
    history   = FileHistory(str(HISTORY_FILE))
    bindings  = _make_bindings()

    session = PromptSession(
        completer=completer,
        auto_suggest=AutoSuggestFromHistory(),
        style=style,
        key_bindings=bindings,
        bottom_toolbar=_toolbar,
        history=history,
        refresh_interval=10,      # redraws toolbar every 10s for live status
        wrap_lines=True,
        mouse_support=False,
    )

    while True:
        try:
            line = session.prompt(_prompt_text)
            run_command(line)
        except KeyboardInterrupt:
            print()
            continue
        except EOFError:
            print("\nGoodbye.")
            break


def main():
    global STIGIX_URL

    parser = argparse.ArgumentParser(
        description="stigix-cli — local interactive console for Stigix",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  stigix-cli                              # Interactive prompt (localhost:8080)
  stigix-cli --url http://10.0.0.5:8080   # Connect to remote instance
  stigix-cli --exec "auth login"          # Run single command and exit
  stigix-cli --exec "security suite"      # Run full security suite headless
  stigix-cli --script run.txt             # Execute commands from a file
        """,
    )
    parser.add_argument("--url",    default=None, metavar="URL",
                        help="Stigix backend URL (overrides env + saved session)")
    parser.add_argument("--exec",   metavar="CMD",
                        help="Execute a single command and exit (non-interactive)")
    parser.add_argument("--script", metavar="FILE",
                        help="Execute commands from a file, one per line")
    args = parser.parse_args()

    # Load saved session first, then override with --url if given
    load_session()
    if args.url:
        STIGIX_URL = args.url
        if not STIGIX_URL.startswith("http"):
            STIGIX_URL = f"http://{STIGIX_URL}"

    if args.exec:
        run_command(args.exec)
    elif args.script:
        path = Path(args.script)
        if not path.exists():
            err(f"Script not found: {args.script}")
            sys.exit(1)
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            info(f"[{lineno}] {line}")
            run_command(line)
    else:
        run_interactive()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)
