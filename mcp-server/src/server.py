"""
SD-WAN Traffic Generator MCP Server.

This is the main entry point for the Model Context Protocol (MCP) server
that orchestrates multiple SD-WAN traffic generator instances.

Supports both SSE (Server-Sent Events) and STDIO transports.
"""

import logging
import os
import sys
import time
import json
import inspect
import functools
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

# CRITICAL: All logs to stderr to avoid polluting stdio
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # NEVER use stdout
)

logger = logging.getLogger(__name__)

# DO NOT POLLUTE STDOUT (Reserved for JSON-RPC in stdio mode)
# Redirect any accidental print or library log to stderr
class StdoutRedirector:
    def write(self, data):
        sys.stderr.write(data)
    def flush(self):
        sys.stderr.flush()

if os.getenv("MCP_TRANSPORT", "stdio").lower() == "stdio":
    sys.stdout = StdoutRedirector()

try:
    from fastmcp import FastMCP
except ImportError:
    logger.error("Failed to import fastmcp. Please install it with: pip install fastmcp")
    sys.exit(1)

# Import Stigix Orchestrator components
from .lib.registry import RegistryClient
from .lib.orchestrator import TestOrchestrator
from .types import StigixEndpoint, TestStatus, TestRun

# Initialize FastMCP
mcp = FastMCP("stigix-orchestrator")

# Core services
registry = RegistryClient()
orchestrator = TestOrchestrator()


# -----------------------------------------------------------------------------
# MCP Interaction Logger
# Wraps all public async orchestrator methods to log calls to mcp-history.jsonl.
# Zero impact on Claude / MCP protocol — purely Stigix-side visibility.
# -----------------------------------------------------------------------------

_MCP_LOG_FILE = Path(os.getenv("LOG_DIR", "/app/logs")) / "mcp-history.jsonl"
_MCP_LOG_MAX_LINES = 500


def _append_mcp_log(tool: str, agent_id: str, duration_ms: int, status: str, error: str = None) -> None:
    """Append one interaction entry to mcp-history.jsonl."""
    try:
        _MCP_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        entry: dict = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "agent_id": str(agent_id) if agent_id else "—",
            "duration_ms": duration_ms,
            "status": status,
        }
        if error:
            entry["error"] = error[:120]
        with open(_MCP_LOG_FILE, "a") as fh:
            fh.write(json.dumps(entry) + "\n")
        # Rotate: keep only the last N lines
        try:
            lines = _MCP_LOG_FILE.read_text().splitlines()
            if len(lines) > _MCP_LOG_MAX_LINES:
                _MCP_LOG_FILE.write_text("\n".join(lines[-_MCP_LOG_MAX_LINES:]) + "\n")
        except Exception:
            pass
    except Exception:
        pass  # Never let logging break a tool


def _patch_orchestrator_logging(instance) -> None:
    """
    Monkey-patch all public async methods on the orchestrator instance
    to transparently log call metadata (tool name, agent_id, duration, status).
    Called once at startup — no changes required to individual tool functions.
    """
    for attr_name in list(vars(type(instance))):
        if attr_name.startswith("_"):
            continue
        method = getattr(instance, attr_name)
        if not inspect.iscoroutinefunction(method):
            continue

        def _make_wrapper(fn, name):
            @functools.wraps(fn)
            async def _wrapper(*args, **kwargs):
                start = time.monotonic()
                # Best-effort agent_id extraction from first positional arg or kwarg
                agent_id = kwargs.get("agent_id")
                if agent_id is None and args:
                    candidate = args[0]
                    if isinstance(candidate, str):
                        agent_id = candidate
                status = "ok"
                error_str = None
                try:
                    result = await fn(*args, **kwargs)
                    # Surface errors returned as dicts/lists
                    if isinstance(result, dict) and "error" in result:
                        status = "error"
                        error_str = str(result["error"])[:120]
                    elif isinstance(result, list) and result and isinstance(result[0], dict) and "error" in result[0]:
                        status = "error"
                        error_str = str(result[0]["error"])[:120]
                    return result
                except Exception as exc:
                    status = "error"
                    error_str = str(exc)[:120]
                    raise
                finally:
                    duration_ms = int((time.monotonic() - start) * 1000)
                    _append_mcp_log(name, agent_id, duration_ms, status, error_str)
            return _wrapper

        setattr(instance, attr_name, _make_wrapper(method, attr_name))


# Apply logging patch to orchestrator
_patch_orchestrator_logging(orchestrator)

# -----------------------------------------------------------------------------
# Tool Definitions
# -----------------------------------------------------------------------------

@mcp.tool()
async def list_endpoints(kind: Optional[str] = None) -> List[dict]:
    """
    List available Stigix endpoints (Fabric nodes and Internet targets).
    
    Args:
        kind: Optional filter ('fabric' or 'internet')
    """
    endpoints = await registry.list_endpoints(kind=kind)
    return [e.model_dump() for e in endpoints]


@mcp.tool()
async def run_test(
    source_id: str,
    target_id: str,
    profile: str = "CONV-001",
    duration: str = "30s",
    bitrate: Optional[str] = None,
    label: Optional[str] = None,
    protocol: Optional[str] = None,
    direction: Optional[str] = None,
    pps: Optional[int] = None
) -> dict:
    """
    Start a coordinated traffic test between Stigix endpoints.
    The source initiates (client) and the target receives (server).

    TARGET CONSTRAINTS (CRITICAL):
    - 'xfr': Target MUST be another Stigix node OR a dedicated XFR target.
    - 'conv': Target MUST be a Stigix Fabric node (internal probe daemon required).
    - 'voice': Target MUST be a Stigix Fabric node (voice echo server required).
    - 'iot': Target MUST be a Stigix Fabric node.

    PROFILES:
    - 'xfr' (speedtest): Data transfer test.
    - 'conv' (convergence): Network probe/failover test (Long-running).
    - 'voice' / 'iot': Application-specific simulations.
    
    Args:
        source_id: Node ID (initiator).
        target_id: Node ID(S) (receivers). Use comma-separated list for multi-target: 'T1,T2'.
        profile: Test type ('xfr', 'speedtest', 'conv', 'voice', 'iot').
        duration: [XFR ONLY] Duration (e.g. '30s'). Ignored for 'conv'.
        bitrate: [XFR ONLY] (e.g. '200M').
        pps: [CONV ONLY] Probe rate (e.g. 100).
        protocol: [XFR ONLY] ('tcp', 'udp', 'quic').
        direction: [XFR ONLY] ('client-to-server', 'server-to-client', 'bidirectional').
        label: [CONV ONLY] Custom label for correlation.
    """
    
    # Resolve source
    source = await registry.get_endpoint(source_id)
    if not source:
        return {"error": f"Source endpoint '{source_id}' not found."}

    # Resolve all targets
    target_ids = [t.strip() for t in target_id.split(',')]
    targets = []
    for tid in target_ids:
        target = await registry.get_endpoint(tid)
        if not target:
            return {"error": f"Target endpoint '{tid}' not found."}
        targets.append(target)

    try:
        results = await orchestrator.run_tests(
            source=source,
            targets=targets,
            profile=profile,
            duration=duration,
            bitrate=bitrate,
            label=label,
            protocol=protocol,
            direction=direction,
            pps=pps
        )
        
        # Return individual TestRun model_dumps in a list
        return {"tests": [t.model_dump() for t in results]}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def get_test_status(test_id: str) -> dict:
    """
    Get the status and metrics of a specific test.
    
    Args:
        test_id: The global test ID (e.g., G-20260313-ABCD) or a local ID (CONV-XXXX).
    """
    try:
        status = await orchestrator.get_status(test_id)
        return status.model_dump()
    except ValueError as e:
        return {"error": str(e)}


@mcp.tool()
async def stop_test(test_id: str) -> dict:
    """
    Stop an active traffic test (especially for convergence tests).
    
    Args:
        test_id: The global test ID (e.g., G-20260313-ABCD) or a local ID (CONV-XXXX).
    """
    try:
        return await orchestrator.stop_test(test_id)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def set_traffic_status(source_id: str, enabled: bool) -> dict:
    """
    Starts or stops the application traffic generation on a specific node.
    
    Args:
        source_id: ID of the node.
        enabled: True to start, False to stop.
    """
    source = await orchestrator.registry.get_endpoint(source_id)
    if not source:
        return {"error": f"Source {source_id} not found."}
    return await orchestrator.set_traffic_status(source, enabled)


@mcp.tool()
async def set_traffic_rate(agent_id: str, rate: float) -> dict:
    """
    Adjust the traffic generation speed (sleep interval between requests).
    
    Args:
        agent_id: ID of the node.
        rate: The delay in seconds between requests (0.1 to 10.0). 
              Lower is faster (0.1 = Turbo, 10.0 = Slow).
    """
    source = await orchestrator.registry.get_endpoint(agent_id)
    if not source:
        return {"error": f"Agent {agent_id} not found."}
    
    # Clip rate to reasonable values as per UI
    clipped_rate = max(0.1, min(10.0, rate))
    try:
        return await orchestrator.set_traffic_rate(source, clipped_rate)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def set_voice_status(source_id: str, enabled: bool) -> dict:
    """
    Start or stop voice simulation on a specific node.
    
    Args:
        source_id: ID of the node (must be kind='fabric')
        enabled: True to start, False to stop
    """
    source = await registry.get_endpoint(source_id)
    if not source:
        return {"error": f"Node '{source_id}' not found."}
    
    try:
        return await orchestrator.set_voice_status(source, enabled)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def get_diagnostics(agent_id: str) -> dict:
    """
    Fetch the full diagnostic dashboard for a node (CPU, Bitrate, App Stats, Voice, Peers).
    
    Args:
        agent_id: ID of the node.
    """
    return await orchestrator.get_agent_dashboard(agent_id)


@mcp.tool()
async def get_app_score(agent_id: str, app_name: str) -> dict:
    """
    Calculate the success/error rate for a specific application on a node.
    
    Args:
        agent_id: ID of the node.
        app_name: Name of the application (e.g., 'teams', 'zoom', 'webex', 'teams.microsoft.com').
    """
    data = await orchestrator.get_agent_dashboard(agent_id)
    if "error" in data:
        return data
        
    stats = data.get("stats", {})
    req_by_app = stats.get("requests_by_app", {})
    err_by_app = stats.get("errors_by_app", {})
    
    # Try fuzzy matching
    target_key = None
    app_lower = app_name.lower()
    for key in req_by_app.keys():
        if app_lower in key.lower():
            target_key = key
            break
            
    if not target_key:
        return {"error": f"Application '{app_name}' not found in stats. Available: {list(req_by_app.keys())[:5]}..."}
        
    requests = req_by_app.get(target_key, 0)
    errors = err_by_app.get(target_key, 0)
    success = requests - errors
    rate = (success / requests * 100) if requests > 0 else 0
    
    return {
        "agent": agent_id,
        "app": target_key,
        "total_requests": requests,
        "errors": errors,
        "success_rate": f"{rate:.2f}%",
        "status": "Healthy" if rate > 95 else "Degraded" if rate > 50 else "Critical"
    }


@mcp.tool()
async def get_security_test_options(probe_type: str) -> dict:
    """
    Get a list of available security test targets/categories for a specific probe type.
    Use this to propose destinations to the user before running a test.
    
    Args:
        probe_type: 'dns', 'url', or 'threat'.
    """
    options = {
        "dns": [
            {"name": "Abortion", "domain": "test-abortion.testpanw.com"},
            {"name": "DNS Tunneling", "domain": "test-dnstun.testpanw.com"},
            {"name": "Malware", "domain": "test-malware.testpanw.com"},
            {"name": "Phishing", "domain": "test-phishing.testpanw.com"},
            {"name": "Command & Control", "domain": "test-c2.testpanw.com"},
            {"name": "DGA (Domain Generation Algorithm)", "domain": "test-dga.testpanw.com"}
        ],
        "url": [
            {"category": "Abortion", "url": "http://urlfiltering.paloaltonetworks.com/test-abortion"},
            {"category": "Adult Content", "url": "http://urlfiltering.paloaltonetworks.com/test-adult"},
            {"category": "Malware", "url": "http://urlfiltering.paloaltonetworks.com/test-malware"},
            {"category": "Phishing", "url": "http://urlfiltering.paloaltonetworks.com/test-phishing"},
            {"category": "Proxy Avoidance", "url": "http://urlfiltering.paloaltonetworks.com/test-proxy-avoidance"}
        ],
        "threat": [
            {"name": "Standard EICAR Scenario", "target": "STIGIX-EICAR-01", "description": "Cloud-based EICAR test scenario"},
            {"name": "Direct EICAR Download (Hetzner)", "target": "http://142.132.193.157:8082/eicar.com.txt", "description": "Direct file download from Hetzner node"}
        ]
    }
    return {"probe_type": probe_type, "options": options.get(probe_type, [])}


@mcp.tool()
async def run_security_probe(agent_id: str, probe_type: str, target: str) -> dict:
    """
    Launch a security test to check for policy enforcement (DNS, URL Filtering, or Threat/AV).
    It is RECOMMENDED to use 'get_security_test_options' first to propose a destination to the user.
    
    Args:
        agent_id: ID of the node.
        probe_type: 'dns' (domain), 'url' (full url), or 'threat' (malware/EICAR).
        target: The domain, URL, or Scenario ID to test.
                For 'threat', you can use 'STIGIX-EICAR-01' or a direct file URL.
    """
    return await orchestrator.trigger_security_test(agent_id, probe_type, target)


@mcp.tool()
async def list_vyos_routers(agent_id: str) -> List[dict]:
    """
    List all VyOS routers managed by a specific Stigix node.
    
    Args:
        agent_id: ID of the Stigix node managing the VyOS routers (e.g., 'Raspi4-Ubuntu').
    """
    return await orchestrator.list_vyos_routers(agent_id)


@mcp.tool()
async def list_vyos_scenarios(agent_id: str) -> List[dict]:
    """
    List available VyOS configuration sequences (scenarios) on a specific Stigix node.
    
    Args:
        agent_id: ID of the Stigix node (e.g., 'BR1-Ubuntu').
    """
    return await orchestrator.list_vyos_sequences(agent_id)


@mcp.tool()
async def run_vyos_scenario(agent_id: str, scenario_id: str) -> dict:
    """
    Execute a VyOS configuration sequence (scenario) on a specific Stigix node.
    
    Args:
        agent_id: ID of the Stigix node.
        scenario_id: The ID of the sequence to run (e.g., 'failover-paris').
    """
    return await orchestrator.run_vyos_sequence(agent_id, scenario_id)


@mcp.tool()
async def get_vyos_timeline(agent_id: str, limit: int = 20) -> List[dict]:
    """
    Get the history of recent VyOS configuration changes on a specific Stigix node.
    
    Args:
        agent_id: ID of the Stigix node.
        limit: Number of recent actions to fetch (default 20).
    """
    return await orchestrator.get_vyos_history(agent_id, limit)


@mcp.tool()
async def set_vyos_scenario_status(agent_id: str, scenario_id: str, enabled: bool) -> dict:
    """
    Enable or disable a specific VyOS configuration sequence (scenario) on a node.
    Use this to stop a cyclic scenario that interferes with manual actions.
    
    Args:
        agent_id: ID of the Stigix node.
        scenario_id: The ID of the sequence/scenario (e.g., 'seq-12345').
        enabled: True to enable/start, False to disable/stop.
    """
    return await orchestrator.set_vyos_scenario_status(agent_id, scenario_id, enabled)


@mcp.tool()
async def get_vyos_interfaces(agent_id: str, router_id: Optional[str] = None) -> List[dict]:
    """
    List VyOS routers and their CHAOS-ELIGIBLE interfaces managed by a Stigix node.

    Only interfaces that have a description configured are returned — interfaces without
    a description are management interfaces and are silently excluded from this list.
    They are never proposed as targets and Claude should never act on them.

    ALWAYS CALL THIS FIRST before any vyos_execute_action.

    DISAMBIGUATION WORKFLOW (mandatory):
    ─────────────────────────────────────
    After receiving the list, you MUST:

    1. SCAN all returned interfaces across ALL routers for keyword matches with the
       user's intent (e.g. "MPLS", "WAN", "LAN", "DC1", "Internet" in the description).

    2. PRESENT the eligible interfaces to the user in a clean format:
       - Router name + status (online/offline)
       - For each chaos-eligible interface: name | description | IP

    3. IF exactly ONE interface matches the intent → propose it and ask for confirmation:
       "I found MPLS-Link-DC1 on vyoslandc1 / eth1 (192.168.281.18/24). Shall I apply
        [action] to this interface? (yes/no)"
       Wait for user confirmation before calling vyos_execute_action.

    4. IF multiple interfaces match → list ALL candidates and ask the user to choose:
       "I found MPLS links on 2 routers:
        1. vyoslandc1 / eth1 — MPLS-Link-DC1 (192.168.281.18/24) — online
        2. vyoslandc2new / eth1 — MPLS-Link-DC2 (192.168.386.4/24) — online
       Which one should I target?"
       Do NOT call vyos_execute_action until the user picks one.

    5. IF a router is offline → warn the user, skip its interfaces.

    6. IF no interface matches the user's intent → tell the user and list all available
       descriptions so they can rephrase or pick one explicitly.

    7. IF a router has NO chaos-eligible interfaces at all (all management, no descriptions)
       → it will appear with chaos_eligible_interfaces: [] and a note. Inform the user that
       this router has no interfaces configured for chaos and how to add one.

    8. IF no router has any chaos-eligible interface → inform the user that natural language
       targeting is not possible and guide them to add descriptions on the VyOS routers:
         set interfaces ethernet ethX description "MPLS-Link-DC1"
       Without descriptions no action can be performed via this tool.

    Args:
        agent_id: ID of the Stigix node managing the VyOS routers.
        router_id: Optional. Filter to a specific router ID. If omitted, returns all routers.
    """
    results = await orchestrator.get_vyos_interfaces(agent_id, router_id)

    # Filter: keep only chaos-eligible interfaces (those with a non-empty description).
    # Management interfaces (no description) are silently excluded.
    total_eligible = 0
    for r in results:
        if "error" in r:
            continue
        eligible = [
            iface for iface in r.get("interfaces", [])
            if iface.get("description") not in (None, "", "(no description)")
        ]
        r["interfaces"] = eligible
        r["chaos_eligible_count"] = len(eligible)
        total_eligible += len(eligible)
        if len(eligible) == 0:
            r["_note"] = (
                f"Router '{r.get('router_name', r.get('router_id'))}' has no chaos-eligible "
                "interfaces (no descriptions configured). To enable natural language targeting, "
                "add descriptions on the VyOS router: "
                "set interfaces ethernet ethX description 'MPLS-Link-DC1'"
            )

    if total_eligible == 0 and any("error" not in r for r in results):
        # Surface a top-level warning: nothing can be targeted by natural language
        for r in results:
            if "error" not in r:
                r["_global_warning"] = (
                    "No chaos-eligible interfaces found across any router on this node. "
                    "Natural language targeting is not possible until interface descriptions "
                    "are configured on the VyOS routers. "
                    "Example: set interfaces ethernet eth1 description 'MPLS-Link-DC1'"
                )
                break  # one warning is enough

    return results


@mcp.tool()
async def vyos_execute_action(
    agent_id: str,
    router_id: str,
    command: str,
    interface: Optional[str] = None,
    latency_ms: Optional[int] = None,
    loss_pct: Optional[float] = None,
    corruption_pct: Optional[float] = None,
    rate: Optional[str] = None,
    ip: Optional[str] = None
) -> dict:
    """
    Execute an ad-hoc VyOS network action on a specific router interface.
    Creates a temporary sequence, runs it immediately, then deletes it.
    Returns the result AND the VyOS CLI equivalent for full transparency.

    ⚠️  ONLY CALL THIS AFTER:
    1. Having called get_vyos_interfaces to list all routers and interfaces.
    2. Having identified the exact target router + interface (no ambiguity).
    3. Having presented the action to the user and received explicit confirmation.
       — For destructive commands (interface-down, deny-traffic) confirmation is MANDATORY.
       — For impairments (set-latency, set-loss, set-rate) always show what you are about to do.

    NEVER call this tool speculatively. Always resolve router_id and interface from
    get_vyos_interfaces output first.

    COMMANDS:
    - 'interface-down'   : Shut an interface down. Requires: interface
    - 'interface-up'     : Re-enable an interface. Requires: interface
    - 'set-latency'      : Add artificial latency via netem. Requires: interface, latency_ms
    - 'set-loss'         : Add packet loss. Requires: interface, loss_pct (0-100)
    - 'set-corruption'   : Add packet corruption. Requires: interface, corruption_pct (0-100)
    - 'set-rate'         : Limit bandwidth. Requires: interface, rate (e.g. '10mbit')
    - 'clear-qos'        : Remove all QoS impairments (latency/loss/rate). Requires: interface
    - 'deny-traffic'     : Add firewall rule to block an IP. Requires: ip
    - 'allow-traffic'    : Remove firewall block for an IP. Requires: ip
    - 'clear-all-blocks' : Remove all IP block rules.
    - 'show-denied'      : List currently blocked IPs.

    CONFIRMATION SCRIPT (use before calling):
    "I'm about to [command] on [router_name] / [interface] ([description]).
     This will [effect]. Confirm? (yes/no)"

    Args:
        agent_id:        Stigix node ID (e.g. 'BR8-Ubuntu').
        router_id:       VyOS router ID from get_vyos_interfaces (e.g. 'VYOS-DC1').
        command:         One of the commands listed above.
        interface:       Interface name (e.g. 'eth1'). Required for most commands.
        latency_ms:      Latency in ms. Used with 'set-latency'.
        loss_pct:        Packet loss % (0-100). Used with 'set-loss'.
        corruption_pct:  Corruption % (0-100). Used with 'set-corruption'.
        rate:            Bandwidth limit string (e.g. '10mbit'). Used with 'set-rate'.
        ip:              IP address. Used with 'deny-traffic' / 'allow-traffic'.
    """
    return await orchestrator.vyos_execute_adhoc(
        agent_id, router_id, command, interface,
        latency_ms, loss_pct, corruption_pct, rate, ip
    )


@mcp.tool()
async def get_dem_summary(agent_id: str) -> dict:
    """
    Get a summary of Digital Experience Monitoring (DEM) health and recent probe results.
    Returns global health score and individual probe statuses.
    
    Args:
        agent_id: ID of the Stigix node.
    """
    return await orchestrator.get_dem_stats(agent_id)


@mcp.tool()
async def get_probe_details(agent_id: str, probe_name: str) -> dict:
    """
    Get detailed performance metrics for a specific DEM probe (ICMP, HTTP, HTTPS, etc.).
    Returns rich stats like score, total_ms, and reachability.
    
    Args:
        agent_id: ID of the Stigix node.
        probe_name: Name or ID of the probe to investigate (e.g., 'Google DNS', 'SaaS App').
    """
    return await orchestrator.get_probe_performance(agent_id, probe_name)


# -----------------------------------------------------------------------------
# Phase 1 Tool Additions — Aligned with stigix-cli capabilities
# -----------------------------------------------------------------------------

@mcp.tool()
async def get_node_status(agent_id: str) -> dict:
    """
    Get a comprehensive status summary for a specific Stigix node.
    Aggregates health, version, traffic status, site info, and live convergence state.
    Use this as the first tool when troubleshooting or checking on a node.

    Args:
        agent_id: ID of the Stigix node (e.g., 'BR8', 'Hetzner').
    """
    return await orchestrator.get_node_status(agent_id)


@mcp.tool()
async def get_traffic_stats(agent_id: str) -> dict:
    """
    Get live traffic generation statistics for a specific node.
    Returns per-application request counts, error rates, client count,
    and current traffic running status.

    Args:
        agent_id: ID of the Stigix node.
    """
    return await orchestrator.get_traffic_stats(agent_id)


@mcp.tool()
async def get_traffic_logs(agent_id: str, limit: int = 50) -> dict:
    """
    Fetch recent traffic generation logs from a specific node.
    Useful for debugging application simulation issues.

    Args:
        agent_id: ID of the Stigix node.
        limit: Maximum number of log entries to return (default 50).
    """
    return await orchestrator.get_traffic_logs(agent_id, limit)


@mcp.tool()
async def get_security_results_stats(agent_id: str) -> dict:
    """
    Get the security test results scorecard for a specific node.
    Returns a summary of passed/failed/blocked results across DNS, URL, and Threat tests.
    Use this to quickly assess the security posture of a node.

    Args:
        agent_id: ID of the Stigix node.
    """
    return await orchestrator.get_security_results_stats(agent_id)


@mcp.tool()
async def get_security_config(agent_id: str) -> dict:
    """
    Get the security policy configuration for a specific node.
    Returns both the module enable/disable config and the full dynamic test target profile
    (DNS domains, URL categories, threat scenarios) configured on the node.

    Args:
        agent_id: ID of the Stigix node.
    """
    return await orchestrator.get_security_config(agent_id)


@mcp.tool()
async def get_security_test_options_dynamic(agent_id: str, probe_type: str) -> dict:
    """
    Get the DYNAMIC list of security test targets/categories for a specific probe type,
    fetched live from the node's actual configured profile.
    Prefer this over 'get_security_test_options' as it reflects the real configuration.

    Args:
        agent_id: ID of the Stigix node to fetch the profile from.
        probe_type: 'dns', 'url', or 'threat'.
    """
    return await orchestrator.get_security_profile_dynamic(agent_id, probe_type)


@mcp.tool()
async def list_dem_probes(agent_id: str) -> dict:
    """
    List all configured Digital Experience Monitoring (DEM) probes on a specific node.
    Returns probe names, types (HTTP, PING, DNS, TCP, UDP), targets, and enabled status.

    Args:
        agent_id: ID of the Stigix node.
    """
    return await orchestrator.list_dem_probes(agent_id)


@mcp.tool()
async def run_dem_probes_now(agent_id: str) -> dict:
    """
    Trigger an immediate run of all DEM experience probes on a specific node.
    Returns RTT, status, and reachability for each probe.
    Note: This may take up to 30-60 seconds depending on the number of probes.

    Args:
        agent_id: ID of the Stigix node.
    """
    return await orchestrator.run_probes_now(agent_id)


@mcp.tool()
async def get_dem_probe_stats(agent_id: str) -> dict:
    """
    Get historical DEM probe statistics for a specific node.
    Returns the global health score, per-probe average latency, and reliability
    over the last hour. Includes raw probe results for detailed analysis.

    Args:
        agent_id: ID of the Stigix node.
    """
    return await orchestrator.get_dem_probe_stats(agent_id)


@mcp.tool()
async def list_fabric_targets(agent_id: str) -> dict:
    """
    List all manually-configured Stigix peer/fabric targets on a specific node.
    Returns each target's name, host, capabilities (xfr, voice, convergence, security),
    enabled status, and source (managed vs autodiscovered).

    Args:
        agent_id: ID of the Stigix node to query.
    """
    return await orchestrator.list_fabric_targets(agent_id)


@mcp.tool()
async def list_speedtest_history(agent_id: str, limit: int = 20) -> dict:
    """
    Get the speedtest (XFR) history for a specific node.
    Returns past test results including target, protocol, throughput (Mbps), RTT, and status.

    Args:
        agent_id: ID of the Stigix node.
        limit: Maximum number of historical results to return (default 20).
    """
    return await orchestrator.list_speedtest_history(agent_id, limit)


# -----------------------------------------------------------------------------
# Phase 2 Tool Additions
# -----------------------------------------------------------------------------

@mcp.tool()
async def run_security_url_batch(agent_id: str) -> dict:
    """
    Run a FULL batch URL filtering audit on a specific node.
    Automatically reads the enabled URL categories from the node's security config
    and tests all of them at once. Returns a summary (blocked/allowed/unknown)
    and individual results for each category.
    Note: This test can take up to 3 minutes to complete.

    Args:
        agent_id: ID of the Stigix node to run the audit on.
    """
    return await orchestrator.run_security_url_batch(agent_id)


@mcp.tool()
async def run_security_dns_batch(agent_id: str) -> dict:
    """
    Run a FULL batch DNS security audit on a specific node.
    Automatically reads the enabled DNS test domains from the node's security config
    and tests all of them at once. Returns a summary (blocked/allowed/unknown)
    and individual results for each domain.
    Note: This test can take up to 3 minutes to complete.

    Args:
        agent_id: ID of the Stigix node to run the audit on.
    """
    return await orchestrator.run_security_dns_batch(agent_id)


@mcp.tool()
async def add_dem_probe(
    agent_id: str,
    name: str,
    target: str,
    probe_type: str = "HTTP",
    timeout_ms: int = 5000
) -> dict:
    """
    Add a new Digital Experience Monitoring (DEM) probe to a specific node.
    The probe is appended to the existing list — existing probes are preserved.

    Args:
        agent_id: ID of the Stigix node.
        name: Display name for the probe (e.g., 'Google DNS', 'Azure West').
        target: Target host/URL/IP (e.g., 'https://example.com', '8.8.8.8', '1.2.3.4:5201').
        probe_type: Type of probe — 'HTTP', 'HTTPS', 'PING', 'TCP', 'UDP', or 'DNS'. Default: 'HTTP'.
        timeout_ms: Probe timeout in milliseconds. Default: 5000.
    """
    return await orchestrator.add_dem_probe(agent_id, name, target, probe_type, timeout_ms)


@mcp.tool()
async def remove_dem_probe(agent_id: str, probe_name: str) -> dict:
    """
    Remove a DEM experience probe by name from a specific node.
    The match is case-insensitive. All other probes are preserved.

    Args:
        agent_id: ID of the Stigix node.
        probe_name: Exact name of the probe to remove (case-insensitive).
    """
    return await orchestrator.remove_dem_probe(agent_id, probe_name)


@mcp.tool()
async def add_fabric_target(
    agent_id: str,
    name: str,
    host: str,
    voice: bool = True,
    convergence: bool = True,
    xfr: bool = True,
    security: bool = True,
    connectivity: bool = True
) -> dict:
    """
    Add a new Stigix fabric peer/target to a specific node.
    Use this to register a new branch or node into the mesh.

    Args:
        agent_id: ID of the Stigix node that will manage this target.
        name: Display name for the new target (e.g., 'Branch-Paris').
        host: IP address or FQDN of the target node.
        voice: Enable voice simulation capability. Default: True.
        convergence: Enable convergence/failover probe capability. Default: True.
        xfr: Enable XFR speedtest capability. Default: True.
        security: Enable security probe capability. Default: True.
        connectivity: Enable connectivity probe capability. Default: True.
    """
    return await orchestrator.add_fabric_target(agent_id, name, host, voice, convergence, xfr, security, connectivity)


@mcp.tool()
async def remove_fabric_target(agent_id: str, target_name_or_host: str) -> dict:
    """
    Remove a Stigix fabric peer/target from a specific node.
    Matches by name (case-insensitive), host IP, or ID prefix.

    Args:
        agent_id: ID of the Stigix node managing the target.
        target_name_or_host: Name, IP address, or ID prefix of the target to remove.
    """
    return await orchestrator.remove_fabric_target(agent_id, target_name_or_host)


@mcp.tool()
async def set_fabric_target_enabled(agent_id: str, target_name_or_host: str, enabled: bool) -> dict:
    """
    Enable or disable a Stigix fabric peer/target on a specific node.
    Disabled targets are ignored for testing but remain configured.

    Args:
        agent_id: ID of the Stigix node managing the target.
        target_name_or_host: Name, IP address, or ID prefix of the target.
        enabled: True to enable, False to disable.
    """
    return await orchestrator.set_fabric_target_enabled(agent_id, target_name_or_host, enabled)


@mcp.tool()
async def set_traffic_client_count(agent_id: str, client_count: int) -> dict:
    """
    Set the number of parallel traffic worker clients on a specific node.
    Higher values generate more concurrent application traffic (simulates more users).
    Valid range: 1 to 20.

    Args:
        agent_id: ID of the Stigix node.
        client_count: Number of parallel workers (1 = minimal, 20 = maximum density).
    """
    return await orchestrator.set_traffic_client_count(agent_id, client_count)


# -----------------------------------------------------------------------------
# Phase 3 Tool Additions
# -----------------------------------------------------------------------------

@mcp.tool()
async def run_full_security_audit(agent_id: str) -> dict:
    """
    Run the COMPLETE security suite on a specific node in one command.
    Executes 3 phases sequentially:
      1. URL Filtering batch (all enabled categories)
      2. DNS Security batch (all enabled domains)
      3. EICAR Threat Prevention (cloud EICAR URL)
    Returns detailed results for each phase plus a global summary.
    Note: This test can take up to 7-10 minutes to complete.
    Use this when you want a comprehensive security posture report for a node.

    Args:
        agent_id: ID of the Stigix node to audit.
    """
    return await orchestrator.run_full_security_audit(agent_id)


@mcp.tool()
async def run_eicar_test(agent_id: str, custom_url: Optional[str] = None) -> dict:
    """
    Run an EICAR malware/threat prevention test on a specific node.
    By default, uses the cloud EICAR URL fetched from the node itself.
    Optionally, supply a custom URL to test a specific threat vector.

    Args:
        agent_id: ID of the Stigix node.
        custom_url: Optional custom threat URL to test (e.g. a direct EICAR file URL).
                    If not provided, the node's configured cloud EICAR URL is used.
    """
    return await orchestrator.run_eicar_test(agent_id, custom_url)


@mcp.tool()
async def get_public_ip(agent_id: str) -> dict:
    """
    Get the public (WAN) exit IP address of a specific node.
    Useful to verify which internet path a node is using or confirm VPN/SD-WAN routing.

    Args:
        agent_id: ID of the Stigix node.
    """
    return await orchestrator.get_public_ip(agent_id)


@mcp.tool()
async def list_apps(agent_id: str) -> dict:
    """
    List all applications configured in the traffic simulation profile of a specific node.
    Shows which apps (Teams, Zoom, Salesforce, etc.) are being simulated.

    Args:
        agent_id: ID of the Stigix node.
    """
    return await orchestrator.list_apps(agent_id)


@mcp.tool()
async def export_app_config(agent_id: str) -> dict:
    """
    Export the full application traffic configuration from a specific node as JSON.
    Use this to backup a node's app profile before making changes,
    or to copy the config to another node via import_app_config.

    Args:
        agent_id: ID of the Stigix node to export from.
    """
    return await orchestrator.export_app_config(agent_id)


@mcp.tool()
async def import_app_config(agent_id: str, config: dict) -> dict:
    """
    Import an application traffic configuration to a specific node.
    WARNING: This OVERWRITES the current app config on the node.
    Use export_app_config first to get the config from another node, then pass it here.

    Args:
        agent_id: ID of the Stigix node to import to.
        config: The application config JSON object (obtained from export_app_config).
    """
    return await orchestrator.import_app_config(agent_id, config)


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Phase 4 Tool Additions
# -----------------------------------------------------------------------------

@mcp.tool()
async def get_convergence_history(agent_id: str, limit: int = 10) -> dict:
    """
    Get the convergence/failover test history for a specific node.
    Returns past test results including the target peer, max blackout duration (ms),
    and a human-readable verdict (PERFECT / GOOD / DEGRADED / BAD / CRITICAL).

    Args:
        agent_id: ID of the Stigix node.
        limit: Maximum number of historical results to return (default 10).
    """
    return await orchestrator.get_convergence_history(agent_id, limit)


@mcp.tool()
async def list_security_results(agent_id: str, limit: int = 20) -> dict:
    """
    Get the last N individual security test results from a specific node.
    Returns all test types (URL, DNS, Threat) in chronological order (newest first).
    Useful for investigating recent security events or test failures.

    Args:
        agent_id: ID of the Stigix node.
        limit: Maximum number of results to return (default 20).
    """
    return await orchestrator.list_security_results(agent_id, limit)


@mcp.tool()
async def compare_nodes(agent_id_a: str, agent_id_b: str) -> dict:
    """
    Compare two Stigix nodes side-by-side across key dimensions.
    Fetches snapshots of both nodes in parallel and returns:
    - Per-node: health, version, traffic status, DEM health, security %, fabric peer count
    - A diff section highlighting any differences between the two nodes
    Use this to investigate why two nodes behave differently.

    Args:
        agent_id_a: ID of the first Stigix node.
        agent_id_b: ID of the second Stigix node.
    """
    return await orchestrator.compare_nodes(agent_id_a, agent_id_b)


@mcp.tool()
async def generate_report(agent_ids: Optional[List[str]] = None) -> dict:
    """
    Generate a fabric-wide summary report across all (or specified) Stigix nodes.
    Fetches node snapshots in parallel and returns:
    - Per-node: health, version, traffic status, DEM health, security %, peer count
    - Global summary: healthy/unhealthy count, traffic running count, total peers
    Use this to get an overview of the entire Stigix fabric at a glance.

    Args:
        agent_ids: Optional list of agent IDs to include. If omitted, reports on ALL registered nodes.
    """
    return await orchestrator.generate_report(agent_ids)


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info(f"Entrypoint reached with __name__ == {__name__}")
    # Read configuration from environment
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    port = int(os.getenv("MCP_PORT", "3101"))
    host = os.getenv("MCP_HOST", "0.0.0.0")
    
    logger.info(f"Starting Stigix MCP Orchestrator with {transport} transport")
    
    if transport == "sse":
        logger.info(f"SSE endpoint: http://{host}:{port}/sse")
        mcp.run(transport="sse", port=port, host=host)
    else:
        logger.info("STDIO transport (direct Claude Desktop connection)")
        mcp.run(transport="stdio")
