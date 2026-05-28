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

# ─── Config ───────────────────────────────────────────────────────────────────

CONFIG_FILE  = Path.home() / ".stigix-cli.json"
HISTORY_FILE = Path.home() / ".stigix-cli.history"
DEFAULT_URL  = os.environ.get("STIGIX_URL", "http://localhost:8080")

JWT_TOKEN    = None
STIGIX_URL   = DEFAULT_URL
PROFILES     = {}          # {name: {"url": ..., "token": ...}}

VERSION      = "1.1.0"
TIMEOUT      = 10

# ─── Session persistence ──────────────────────────────────────────────────────

def load_session():
    """Load saved token, URL and profiles from ~/.stigix-cli.json"""
    global JWT_TOKEN, STIGIX_URL, PROFILES
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            JWT_TOKEN = data.get("token")
            saved_url = data.get("url")
            if saved_url and STIGIX_URL == DEFAULT_URL:
                STIGIX_URL = saved_url
            PROFILES = data.get("profiles", {})
        except Exception:
            pass

def save_session():
    """Persist token, URL and profiles to ~/.stigix-cli.json (chmod 600)"""
    try:
        CONFIG_FILE.write_text(json.dumps(
            {"token": JWT_TOKEN, "url": STIGIX_URL, "profiles": PROFILES}, indent=2
        ))
        CONFIG_FILE.chmod(0o600)
    except Exception:
        pass

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
    widths = [
        max(len(str(h)), max((len(str(r[i])) for r in rows), default=0))
        for i, h in enumerate(headers)
    ]
    fmt = "  " + "  ".join(f"{{:<{w}}}" for w in widths)
    print(c("1", fmt.format(*headers)))
    print("  " + "  ".join("─" * w for w in widths))
    for row in rows:
        print(fmt.format(*[str(v) for v in row]))

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
    if conv and conv.get("running"):
        ok(f"Convergence running: {conv.get('testId','?')}")

    site = api_get("/api/siteinfo")
    if site and site.get("siteName"):
        info(f"Prisma site: {site['siteName']}")

    STATUS.invalidate()


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
        r = api_get("/api/stats")
        if r:
            hdr("━━ Traffic Stats ━━━━━━━━━━━━━━━━━━━━━")
            rows = [(k, v) for k, v in r.items() if not isinstance(v, dict)]
            table(["Metric", "Value"], rows[:20])

    elif sub == "logs":
        r = api_get("/api/logs")
        if r:
            lines = r if isinstance(r, list) else r.get("lines", [])
            hdr(f"━━ Last {len(lines)} log lines ━━━━━━━━━━━━━━━━━━━━━")
            for l in lines[-30:]:
                dim(l)

    elif sub == "reset":
        r = api_delete("/api/stats")
        if r: ok("Statistics reset")

    elif sub == "watch":
        interval = int(args[1]) if len(args) > 1 else 3
        info(f"Live traffic watch — refresh every {interval}s  (Ctrl+C to stop)")
        try:
            while True:
                do_clear()
                now = datetime.now().strftime("%H:%M:%S")
                hdr(f"━━ Traffic Stats  [{now}]  (Ctrl+C to stop) ━━━━━━━")
                print()
                r = api_get("/api/stats")
                if r:
                    rows = [(k, v) for k, v in r.items() if not isinstance(v, dict)]
                    table(["Metric", "Value"], rows[:20])
                print()
                t = api_get("/api/traffic/status")
                if t:
                    state = "running" if (t.get("enabled") or t.get("running")) else "stopped"
                    print(f"  Status: {status_badge(state)}")
                time.sleep(interval)
        except KeyboardInterrupt:
            print()
            ok("Watch stopped")

    else:
        print("Usage: traffic start | stop | status | stats | logs | reset | watch [interval_sec]")


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
            for t in targets:
                enabled = "✓" if t.get("enabled", True) else "✗"
                rows.append([
                    t.get("id","?")[:12],
                    t.get("name","?")[:20],
                    t.get("host") or t.get("url","?"),
                    t.get("type","?"),
                    enabled
                ])
            table(["ID", "Name", "Host/URL", "Type", "On"], rows)

    elif sub == "add":
        parsed  = parse_flags(args[1:], ["name","host","type","port","url","timeout"])
        name    = parsed.get("name")    or input("Name: ").strip()
        host    = parsed.get("host")    or parsed.get("url") or input("Host/URL: ").strip()
        ttype   = parsed.get("type",   "http")
        port    = int(parsed.get("port",   80))
        timeout = int(parsed.get("timeout", 5))
        body    = {"name": name, "host": host, "type": ttype, "port": port, "timeout": timeout, "enabled": True}
        r = api_post("/api/connectivity/custom", body)
        if r: ok(f"Experience target '{name}' added")

    elif sub == "remove":
        tid = args[1] if len(args) > 1 else None
        if not tid: err("Usage: experience remove <id>"); return
        r = api_delete(f"/api/connectivity/custom/{tid}")
        if r: ok(f"Experience target {tid} removed")

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

    else:
        _help_section("DIGITAL EXPERIENCE", [
            ("experience list",           "List connectivity probe targets"),
            ("experience add",            "Add a new target (interactive or --flags)"),
            ("experience remove <id>",    "Remove a target"),
            ("experience probe",          "Run all probes now"),
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
                        caps_list.append(k)
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
        parsed = parse_flags(args[1:], ["name", "host", "voice", "convergence", "xfr", "security", "connectivity"])
        name = parsed.get("name") or input("Name (e.g. Branch-1): ").strip()
        host = parsed.get("host") or input("Host (IP or FQDN): ").strip()
        
        voice = str(parsed.get("voice", "true")).lower() == "true"
        convergence = str(parsed.get("convergence", "true")).lower() == "true"
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
                "convergence": convergence,
                "xfr": xfr,
                "security": security,
                "connectivity": connectivity
            }
        }
        r = api_post("/api/targets", body)
        if r:
            ok(f"Peer '{name}' added successfully")

    elif sub == "remove":
        pid = args[1] if len(args) > 1 else None
        if not pid:
            err("Usage: peer remove <id>")
            return
        r = api_delete(f"/api/targets/{pid}")
        if r:
            ok(f"Peer target {pid} removed")

    elif sub in ("enable", "disable"):
        pid = args[1] if len(args) > 1 else None
        if not pid:
            err(f"Usage: peer {sub} <id>")
            return
        body = {"enabled": sub == "enable"}
        r = api_put(f"/api/targets/{pid}", body)
        if r:
            ok(f"Peer target {pid} {'enabled' if sub == 'enable' else 'disabled'}")

    else:
        _help_section("PEER TARGETS", [
            ("peer list",             "List configured Stigix targets/peers"),
            ("peer add",              "Add a new Stigix target manually"),
            ("peer remove <id>",      "Remove a Stigix target"),
            ("peer enable <id>",      "Enable a Stigix target"),
            ("peer disable <id>",     "Disable a Stigix target"),
        ])
        dim("  Flags for add: --name  --host  --voice {true,false}  --convergence {true,false}")
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
                target = params.get("target", {})
                host = target.get("host", "?")
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
        if len(args) < 2:
            err("Usage: speedtest run <target-host> [options]")
            return
        target_host = args[1]
        
        parsed = parse_flags(args[2:], ["port", "protocol", "direction", "duration", "bitrate", "streams", "psk"])
        
        has_custom = len(parsed) > 0
        
        port = int(parsed.get("port", 9000))
        protocol = parsed.get("protocol", "tcp")
        direction = parsed.get("direction", "client-to-server")
        duration = int(parsed.get("duration", 10))
        bitrate = parsed.get("bitrate", "200M")
        streams = int(parsed.get("streams", 4))
        psk = parsed.get("psk", "")

        if has_custom:
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


def cmd_convergence(args):
    if not require_auth(): return
    sub = args[0] if args else "status"

    if sub == "status":
        r = api_get("/api/convergence/status")
        if r:
            if r.get("running"):
                ok(f"Running — test ID: {r.get('testId','?')}  elapsed: {r.get('elapsed','?')}s")
            else:
                dim("No convergence test running")

    elif sub == "start":
        parsed = parse_flags(args[1:], ["target","pps","label"])
        target = parsed.get("target") or input("Target IP: ").strip()
        pps    = int(parsed.get("pps", 50))
        label  = parsed.get("label", f"CLI-{int(time.time())}")
        r = api_post("/api/convergence/start", {"target": target, "pps": pps, "label": label})
        if r:
            ok(f"Convergence test started: {r.get('testId','?')}")
            STATUS.invalidate()

    elif sub == "stop":
        r = api_post("/api/convergence/stop")
        if r:
            ok("Convergence test stopped")
            STATUS.invalidate()

    elif sub == "history":
        limit = int(args[1]) if len(args) > 1 else 10
        r = api_get("/api/convergence/history")
        if r:
            rows = r if isinstance(r, list) else r.get("results", [])
            rows = rows[:limit]
            table(["ID", "Label", "Target", "Blackout", "Score"], [
                [
                    row.get("testId","?")[:12],
                    row.get("label","?")[:15],
                    row.get("target","?"),
                    str(row.get("maxBlackout", row.get("blackout","?")))+("ms" if isinstance(row.get("maxBlackout","?"), (int,float)) else ""),
                    row.get("score", row.get("result","?"))
                ] for row in rows
            ])

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
        info(f"Convergence watch — refresh every {interval}s  (Ctrl+C to stop)")
        try:
            while True:
                do_clear()
                now = datetime.now().strftime("%H:%M:%S")
                hdr(f"━━ Convergence Status  [{now}] ━━━━━━━━━━━━━━━━━")
                r = api_get("/api/convergence/status")
                if r:
                    if r.get("running"):
                        ok(f"Running — ID: {r.get('testId','?')}  elapsed: {r.get('elapsed','?')}s")
                        for key in ("loss","blackout","rtt","ppsReceived"):
                            if key in r:
                                info(f"  {key}: {r[key]}")
                    else:
                        dim("  No test running")
                time.sleep(interval)
        except KeyboardInterrupt:
            print()
            ok("Watch stopped")

    else:
        _help_section("CONVERGENCE / FAILOVER", [
            ("convergence status",          "Show running test state"),
            ("convergence start",           "Start failover test (interactive or --flags)"),
            ("convergence stop",            "Stop running test"),
            ("convergence history [n]",     "Show past test results"),
            ("convergence endpoints",       "List saved endpoints"),
            ("convergence watch [sec]",     "Live poll test until stopped"),
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
        if r:
            hdr("━━ Voice / MOS Stats ━━━━━━━━━━━━━━━━━━━")
            mos    = r.get("mos") or r.get("mosScore","?")
            jitter = r.get("jitter","?")
            loss   = r.get("packetLoss","?")
            rtt    = r.get("rtt") or r.get("latency","?")
            try:
                mos_val = float(mos)
            except Exception:
                mos_val = 0.0
            color = "1;32" if mos_val > 3.5 else "1;31"
            print(f"  MOS Score   : {c(color, str(mos))}")
            print(f"  Jitter      : {jitter}ms")
            print(f"  Packet Loss : {loss}%")
            print(f"  RTT         : {rtt}ms")

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
    global STIGIX_URL, JWT_TOKEN, PROFILES

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
        tok = None
        if not url.startswith("http"):
            # Bare IP or hostname — add port 8080 if no port given
            if ":" not in url.split("/")[-1]:
                url = f"http://{url}:8080"
            else:
                url = f"http://{url}"

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
    traffic status|stats   State and counters
    traffic logs           Show last log lines
    traffic reset          Reset statistics
    traffic watch [sec]    {c('36','Live watch — refreshes every N seconds')}

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
    experience add         Add a new target (--name --host --type --port)
    experience remove <id> Remove a target
    experience probe       Run all probes now

  {c('1','PEER TARGETS')}
    peer list              List configured Stigix targets/peers
    peer add               Add a Stigix target manually (--name --host)
    peer remove <id>       Remove a Stigix target
    peer enable <id>       Enable a Stigix target
    peer disable <id>      Disable a Stigix target

  {c('1','SPEEDTEST / XFR BANDWIDTH')}
    speedtest list         Show past speedtest jobs
    speedtest run <host>   Run speedtest (--port --protocol --direction)

  {c('1','CONVERGENCE / FAILOVER')}
    convergence start      Start failover test  (--target --pps --label)
    convergence stop       Stop running test
    convergence status     Running test state
    convergence history    Past test results
    convergence endpoints  Saved endpoints
    convergence watch [s]  {c('36','Live poll until Ctrl+C')}

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
    "convergence": cmd_convergence,
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
    },
    "security":    {
        "status": None, "url": None, "url-batch": None,
        "dns": None, "dns-batch": None, "eicar": None,
        "suite": None, "results": None, "clear": None,
    },
    "experience":  {
        "list": None, "probe": None, "remove": None,
        "add":  {"--name": None, "--host": None,
                 "--type": {"http", "ping", "dns"},
                 "--port": None, "--timeout": None},
    },
    "target":      {
        "list": None, "probe": None, "remove": None,
        "add":  {"--name": None, "--host": None,
                 "--type": {"http", "ping", "dns"},
                 "--port": None, "--timeout": None},
    },
    "peer":        {
        "list": None, "remove": None, "enable": None, "disable": None,
        "add":  {"--name": None, "--host": None,
                 "--voice": {"true", "false"},
                 "--convergence": {"true", "false"},
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
    parts  = line.split()
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
    main()
