# Stigix MCP Server

**Model Context Protocol (MCP) Server for Distributed Natural Language Orchestration**

---

## 🎯 Overview

The Stigix MCP Server provides a **natural language interface** to orchestrate your entire SD-WAN validation mesh. Using Claude Desktop, you can manage traffic tests, security probes, network impairments, DEM experience monitoring, and fabric topology — all from conversational commands.

### Key Features

✅ **Mesh-Ready Orchestration** - Control any node in the mesh from any other node via distributed discovery.  
✅ **Natural Language** - Command your infrastructure in plain English or French.  
✅ **Distributed Control** - The MCP server runs on every Stigix instance, providing total redundancy.  
✅ **Full Toolset** - 48 tools covering 100% of stigix-cli capabilities: traffic, security, DEM probes, fabric targets, VyOS, and analytics.  
✅ **SSE Transport** - Native support for Server-Sent Events (SSE) for easy remote access.  

---

## 🏗️ Distributed Architecture

Starting with **v1.2.1-patch.204**, Stigix uses a fully distributed "Any-Node Control" architecture.

```text
┌─────────────────────┐      (Remote or Local)
│  Claude Desktop     │      Natural Language Interface
│  (User)             │
└──────────┬──────────┘
           │
           ▼ SSE (Port 3100)
┌─────────────────────┐      1. Registry Sync
│  Target MCP Server  │ ────────────────────────► ┌──────────────────────┐
│  (on Any Node)      │                           │   Stigix Registry    │
└──────────┬──────────┘ ◄──────────────────────── └──────────────────────┘
           │                 Full Mesh Visibility
           ▼ HTTP APIs (JWT Auth)
┌─────────────────────────────────────┐
│  Distributed Stigix Mesh            │
│  ┌─────────┐  ┌─────────┐  ┌──────┐│
│  │ Branch-1│  │ Branch-2│  │ DC-1 ││
│  └─────────┘  └─────────┘  └──────┘│
└─────────────────────────────────────┘
```

**How it works:**
1. **Registry Sync**: The Registry Leader distributes target configurations to all nodes.
2. **Ubiquitous MCP**: Every Stigix node runs an MCP server.
3. **Redundant Entry Points**: You can connect Claude to **any** node's IP. That node will use its synchronized registry to pilot any other node in the mesh.

---

## 🚀 Quick Start

### 1. Deployment
The MCP server is included by default in the Stigix `docker-compose.yml`. It starts automatically on port **3100** using the **SSE** transport.

### 2. Prerequisites
Depending on the setup method you choose below, you will need:
* **Option A (Node/npx Method - Recommended):** Node.js installed on your machine (provides the `npx` command).
* **Option B (Python Bridge Method):** Python 3 installed on your machine.

---

## 🚦 Claude Desktop Configuration

Stigix uses **Server-Sent Events (SSE)** for remote connectivity. Since Claude Desktop primarily supports **STDIO**, you can connect to it using one of the following two options:

### 1. Locate your Configuration File
Open the `claude_desktop_config.json` file on your machine:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

---

### Option A: Zero-Setup (Node/npx Method) — Recommended
If you have **Node.js** installed, this is the easiest option because it does not require cloning this repository, setting up Python, or configuring virtual environments.

Add this entry under `mcpServers` (replace the URL with the IP/port of your Stigix instance):

```json
{
  "mcpServers": {
    "stigix-cloud": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/inspector",
        "http://<STIGIX_NODE_IP>:3100/sse"
      ]
    }
  }
}
```

---

### Option B: Local Python Bridge Method
Use this option if you do not have Node.js installed, or if you prefer running the Python bridge script locally.

#### Step 0: Clone the Repository
Since this method relies on local scripts (`setup-bridge.sh`, `bridge.py`, etc.), you must first clone the Stigix repository to your machine if you haven't already:
```bash
git clone https://github.com/jsuzanne/stigix.git
cd stigix
```

#### Step 1: Initialize the local python environment

Choose the setup instructions matching your operating system:

##### 🍎 macOS / Linux
Open your terminal, navigate to your cloned `stigix` repository directory, and run:
```bash
# Make the setup script executable
chmod +x ./mcp-server/setup-bridge.sh

# Run the setup script
./mcp-server/setup-bridge.sh
```
This script automatically checks for Python 3, creates a `.venv` folder, and installs all the required libraries for you.

##### 🪟 Windows (PowerShell)
Open PowerShell, navigate to your cloned `stigix` repository directory, and run:
```powershell
# Navigate into the mcp-server directory
cd mcp-server

# Create the Python virtual environment
python -m venv .venv

# Upgrade pip and install the required dependencies
.\.venv\Scripts\pip.exe install --upgrade pip
.\.venv\Scripts\pip.exe install -r .\requirements.txt
```

#### Step 2: Configure Claude Desktop
Add this entry under `mcpServers` in your configuration file:

**macOS / Linux:**
```json
{
  "mcpServers": {
    "stigix-bridge": {
      "command": "<PATH_TO_STIGIX_REPOSITORY>/mcp-server/.venv/bin/python3",
      "args": [
        "<PATH_TO_STIGIX_REPOSITORY>/mcp-server/bridge.py",
        "http://<STIGIX_NODE_IP>:3100/sse"
      ],
      "env": {
        "PYTHONPATH": "<PATH_TO_STIGIX_REPOSITORY>/mcp-server"
      }
    }
  }
}
```

**Windows (PowerShell):**
```json
{
  "mcpServers": {
    "stigix-bridge": {
      "command": "C:\\path\\to\\stigix\\mcp-server\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\path\\to\\stigix\\mcp-server\\bridge.py",
        "http://<STIGIX_NODE_IP>:3100/sse"
      ],
      "env": {
        "PYTHONPATH": "C:\\path\\to\\stigix\\mcp-server"
      }
    }
  }
}
```

> [!IMPORTANT]
> - **Paths**: Replace `<PATH_TO_STIGIX_REPOSITORY>` (or `C:\path\to\stigix`) with the actual absolute path to where you cloned the repository.
> - **URL**: Replace `<STIGIX_NODE_IP>` with the IP of the Stigix instance you want to pilot.
> - **Windows paths**: Use double backslashes `\\` in JSON strings, or forward slashes `/`.

---

### 3. Verify Connection
1. **Restart Claude Desktop** completely (Cmd+Q, then reopen).
2. Click the 🔨 **hammer icon** (bottom right of the prompt box).
3. If everything is correct, you should see your configured server with a green status and the full list of tools.

### 4. Troubleshooting
If the server doesn't appear or shows a red error:
- Check the bridge logs on macOS: `tail -f ~/Library/Logs/Claude/mcp.log`
- Manually test the Python bridge (if using Option B):
  ```bash
  <PATH_TO_STIGIX_REPOSITORY>/mcp-server/.venv/bin/python3 <PATH_TO_STIGIX_REPOSITORY>/mcp-server/bridge.py http://<STIGIX_NODE_IP>:3100/sse
  ```
  If it says `"Bridge initialized. Ready for Claude"`, the python setup is correct.

---

## 🛠️ Available MCP Tools (48 tools)

> [!TIP]
> All tools that target a specific node accept an `agent_id` parameter — this is the node's name as shown in `list_endpoints` (e.g., `"BR8"`, `"Paris"`, `"Hetzner"`).

### Discovery & Status

| Tool | Description | Example |
|---|---|---|
| `list_endpoints` | List all fabric nodes or internet targets | *"Active nodes?", "Internet targets?"* |
| `get_node_status` | Full status summary (health, version, traffic, site, convergence) | *"Status of BR8?", "Is Paris healthy?"* |
| `get_public_ip` | WAN exit IP of a node | *"What's the public IP of BR8?"* |
| `generate_report` | Fabric-wide report across all (or specified) nodes in parallel | *"Give me an overview of all nodes"* |
| `compare_nodes` | Side-by-side comparison of two nodes | *"Compare BR8 and Hetzner"* |

### Traffic Generation

| Tool | Description | Example |
|---|---|---|
| `set_traffic_status` | Start or stop application traffic simulation | *"Start traffic on BR8"* |
| `set_traffic_rate` | Adjust traffic speed (0.1s – 10s delay) | *"Turbo mode on BR8"* |
| `set_traffic_client_count` | Set number of parallel workers (1–20) | *"Set 10 clients on Paris"* |
| `set_voice_status` | Start or stop voice simulation | *"Launch voice sim on BR8"* |
| `get_traffic_stats` | Live per-app request counts, error rates, client count | *"Traffic stats for BR8?"* |
| `get_traffic_logs` | Recent traffic generation logs | *"Show last 50 logs for BR8"* |
| `list_apps` | Apps configured in the traffic profile | *"What apps is BR8 simulating?"* |
| `export_app_config` | Export app config as JSON (for backup or cloning) | *"Export BR8's app config"* |
| `import_app_config` | Import app config to a node (overwrites current) | *"Copy Paris app config to BR8"* |

### Test Orchestration

| Tool | Description | Example |
|---|---|---|
| `run_test` | Start XFR, convergence, voice, or IoT test | *"Speedtest BR8 → Paris"* |
| `get_test_status` | Get metrics for a running or completed test | *"Status of test CONV-1234?"* |
| `stop_test` | Stop a running test | *"Stop the convergence test"* |

### XFR Speedtest

| Tool | Description | Example |
|---|---|---|
| `list_speedtest_history` | Past XFR speedtest results with throughput, RTT, status | *"Last speedtests from BR8?"* |

### Convergence / Failover

| Tool | Description | Example |
|---|---|---|
| `get_convergence_history` | Past failover tests with max blackout (ms) and verdict | *"Convergence history for BR8?"* |

### Security Testing

| Tool | Description | Example |
|---|---|---|
| `get_security_results_stats` | Security test scorecard (blocked/allowed summary) | *"Security score for BR8?"* |
| `list_security_results` | Last N individual security test results (all types) | *"Last 20 security tests on BR8"* |
| `get_security_config` | Security policy config + dynamic test target profile | *"Security config on BR8?"* |
| `get_security_test_options` | Available test options (static list, legacy) | *"DNS test options?"* |
| `get_security_test_options_dynamic` | Live test options fetched from node profile | *"URL filtering options on BR8?"* |
| `run_security_probe` | Run a single DNS / URL / Threat test | *"Test malware.com on BR8"* |
| `run_security_url_batch` | Full URL filtering audit (all enabled categories) | *"Run full URL audit on BR8"* |
| `run_security_dns_batch` | Full DNS security audit (all enabled domains) | *"Run full DNS audit on BR8"* |
| `run_eicar_test` | EICAR threat prevention test (cloud URL or custom) | *"EICAR test on BR8"* |
| `run_full_security_audit` | Complete suite: URL batch + DNS batch + EICAR | *"Full security audit on BR8"* |

### DEM / Experience Probes

| Tool | Description | Example |
|---|---|---|
| `get_dem_summary` | Global DEM health score and status | *"DEM overview for BR8?"* |
| `get_probe_details` | Detailed metrics for one probe by name | *"Details for Google DNS probe on BR8"* |
| `list_dem_probes` | List all configured DEM probes | *"What probes are on BR8?"* |
| `run_dem_probes_now` | Trigger immediate probe run, return results | *"Run probes now on BR8"* |
| `get_dem_probe_stats` | Historical DEM stats (1h): health score, latency, reliability | *"DEM stats for BR8 last hour"* |
| `add_dem_probe` | Add a new DEM probe (HTTP/HTTPS/PING/TCP/UDP/DNS) | *"Add a PING probe to 8.8.8.8 on BR8"* |
| `remove_dem_probe` | Remove a probe by name | *"Remove 'Google DNS' probe from BR8"* |

### Fabric Target Management

| Tool | Description | Example |
|---|---|---|
| `list_fabric_targets` | List all peer targets with capabilities | *"What are BR8's fabric targets?"* |
| `add_fabric_target` | Register a new peer in the mesh | *"Add Hetzner (1.2.3.4) as a target on BR8"* |
| `remove_fabric_target` | Remove a peer by name, host, or ID | *"Remove Hetzner target from BR8"* |
| `set_fabric_target_enabled` | Enable or disable a peer target | *"Disable Paris target on BR8"* |

### Diagnostics & Analytics

| Tool | Description | Example |
|---|---|---|
| `get_diagnostics` | Full node dashboard: CPU, bitrate, app stats, voice, peers | *"Health of BR8", "CPU/RAM Paris"* |
| `get_app_score` | Success rate for a specific application | *"Teams score on BR8?"* |

### VyOS Router Management

| Tool | Description | Example |
|---|---|---|
| `list_vyos_routers` | List managed VyOS routers | *"VyOS routers managed by BR8"* |
| `list_vyos_scenarios` | List available config sequences | *"Available VyOS scenarios?"* |
| `run_vyos_scenario` | Execute a config sequence | *"Apply failover-paris scenario"* |
| `get_vyos_timeline` | History of VyOS configuration changes | *"Recent VyOS changes on BR8"* |
| `set_vyos_scenario_status` | Enable or disable a cyclic scenario | *"Stop cyclic flapping on BR8"* |
| `get_vyos_interfaces` | List VyOS router interfaces with descriptions — required first step before ad-hoc actions | *"Show interfaces of the router on BR8"* |
| `vyos_execute_action` | Execute any VyOS action via natural language: shut/enable interface, add latency/loss/rate, block/unblock IP | *"Shut MPLS on BR1"*, *"Add 150ms latency on WAN"*, *"Block 10.0.0.5"* |

> [!TIP]
> `get_vyos_interfaces` reads interface **descriptions** to resolve natural language intent. For `vyos_execute_action` to work with prompts like *"shut the MPLS link"*, descriptions must be set on the VyOS router (e.g., `set interfaces ethernet eth1 description "MPLS-Link-DC1"`). See [VYOS_CONTROL.md](VYOS_CONTROL.md) → *Interface Naming Best Practices*.

---

## 💡 Usage Examples

### 1. Target Compatibility Rules (Important)
Before launching a test, ensure the target endpoint supports the requested profile:

- **`xfr` (Speedtest)**: Requires a Stigix node or a dedicated XFR target.
- **`conv` (Convergence)**: Requires a Stigix Fabric node (uses internal probing daemons).
- **`voice` (VoIP)**: Requires a Stigix Fabric node (uses the Voice Echo server).
- **`iot` (Data)**: Requires a Stigix Fabric node.

> [!TIP]
> Use `list_endpoints` to check the `kind` and `capabilities` of each node before proposing a test.

### 2. Performance Investigation
**User:** *"Teams quality is bad at the Paris site, can you investigate?"*
```
get_node_status("Paris-BR1")
get_app_score("Paris-BR1", app_name="Teams")
get_dem_summary("Paris-BR1")
get_probe_details("Paris-BR1", probe_name="Microsoft 365")
```

### 3. Full Security Audit
**User:** *"Run a complete security audit on BR8."*
```
run_full_security_audit("BR8")
→ Runs URL batch (all categories) + DNS batch (all domains) + EICAR threat test
→ Returns per-phase results + global score (e.g., "14/15 blocked")
```

### 4. Node Comparison
**User:** *"Why is Paris behaving differently from BR8?"*
```
compare_nodes("Paris-BR1", "BR8")
→ Returns side-by-side: version, traffic running, DEM health, security %, peer count
→ Highlights differences automatically in the "diff" section
```

### 5. Network Orchestration (VyOS)
**User:** *"Main link is down in Paris, failover to 4G."*
```
list_vyos_scenarios("Paris-BR1")
run_vyos_scenario("Paris-BR1", scenario_id="force-4g-failover")
get_vyos_timeline("Paris-BR1")
```

### 6. Traffic Stress Test
**User:** *"I want to stress the network from London."*
```
set_traffic_client_count("London", client_count=20)
set_traffic_rate("London", rate=0.1)
run_test(source_id="London", target_id="Paris,DC1", profile="xfr", bitrate="200M")
```

### 7. Fabric-Wide Overview
**User:** *"Give me a status report of all my nodes."*
```
generate_report()
→ Fetches all nodes in parallel, returns health, traffic, DEM, security, peer count per node
→ Global summary: healthy/unhealthy count, traffic running count
```

### 8. DEM Probe Management
**User:** *"Add a probe to monitor our Azure endpoint from BR8."*
```
add_dem_probe("BR8", name="Azure West", target="https://azure.microsoft.com", probe_type="HTTPS")
run_dem_probes_now("BR8")
```

### 9. VyOS Natural Language Control
**User:** *"Simulate a WAN outage on BR1 — shut the MPLS link, then restore after 30 seconds."*
```
get_vyos_interfaces("BR1")
→ eth0: WAN-Internet-Bouygues
→ eth1: MPLS-Link-DC1          ← match
→ eth2: LAN-Users-Branch

vyos_execute_action("BR1", router_id="vyos-br1", command="interface-down", interface="eth1")
→ CLI: set interfaces ethernet eth1 disable + commit
→ Returns: {success: true, cli_equivalent: ["set interfaces...", "commit"]}

# ... wait 30s ...

vyos_execute_action("BR1", router_id="vyos-br1", command="interface-up", interface="eth1")
→ CLI: delete interfaces ethernet eth1 disable + commit
```

**User:** *"Add 200ms latency and 3% loss on the WAN of BR8, then block 10.0.0.5."*
```
get_vyos_interfaces("BR8")    → eth0 = WAN-Internet-*
vyos_execute_action("BR8", router_id="...", command="set-latency", interface="eth0", latency_ms=200)
vyos_execute_action("BR8", router_id="...", command="set-loss", interface="eth0", loss_pct=3)
vyos_execute_action("BR8", router_id="...", command="deny-traffic", ip="10.0.0.5")
```

> [!IMPORTANT]
> Interface descriptions must be configured on the VyOS router for natural language targeting to work.
> If Claude reports "no descriptions found", see [VYOS_CONTROL.md](VYOS_CONTROL.md) → *Interface Naming Best Practices*.

---

## 🔄 Keeping MCP Tools Up-to-Date

When `stigix-cli.py` is updated (new commands, bug fixes, new API parameters), the MCP server tools should be synchronized to match. The project includes an agent skill for this:

**`.agent/skills/stigix-mcp-sync/`** — Run this skill after any CLI changes to:
1. Detect new or modified API endpoints in the CLI
2. Cross-reference against the living CLI→MCP registry (`references/cli_to_mcp_map.md`)
3. Implement missing tools following the existing orchestrator pattern
4. Deploy the updated MCP server

---

## 🔁 Upgrading Stigix — Do I Need to Restart Claude Desktop?

**Short answer: yes, typically.**

### Why

Claude Desktop connects to the Stigix MCP server through a persistent SSE connection:

```
Claude Desktop
    │  spawns (child process)
    ▼
npx @modelcontextprotocol/inspector     ← stdio bridge
    │  SSE persistent connection
    ▼
http://<node>:3100/sse                  ← MCP Server (Python, in Docker)
```

When the Stigix container restarts during an upgrade:
1. The SSE connection **drops** immediately
2. The `npx inspector` child process receives a connection error and **dies**
3. Claude Desktop detects its MCP child is dead → marks the server as **unavailable**
4. The MCP tools are no longer accessible until reconnection

### How to Reconnect

**Option A — Fastest:** In Claude Desktop settings, find `stigix-cloud` under Developer → MCP Servers and toggle it off/on (if supported by your Claude Desktop version).

**Option B — Reliable:** Fully quit Claude Desktop (`Cmd+Q` on macOS), then relaunch. The `npx inspector` process restarts and re-establishes the SSE connection.

> [!NOTE]
> You do **not** need to change `claude_desktop_config.json` — only the running connection needs to be refreshed.

### Typical Upgrade Workflow

```bash
# On the Stigix node
docker compose pull && docker compose up -d

# On your Mac — after the container is back online
# Quit Claude Desktop → Reopen
# Verify: Settings → MCP Server → Service Status should show ● Online
```

---

## 🧠 What Does Stigix Actually Receive from Claude?

**The natural language text never reaches Stigix.**

When you type a prompt in Claude Desktop (e.g. *"What is the security score for BR8?"*), the translation happens entirely on Anthropic's servers:

```
You type:  "What is the security score for BR8?"
                │
                ▼  sent to Anthropic (Claude LLM)
           Claude reasons, selects the right tool and arguments
                │
                ▼  generates a structured JSON-RPC call
           {
             "method": "tools/call",
             "params": {
               "name": "get_security_score",
               "arguments": { "agent_id": "BR8-Ubuntu" }
             }
           }
                │
                ▼  npx inspector → SSE → port 3100
           Stigix MCP Server receives ONLY this structured call
```

**Stigix never sees** *"What is the security score for BR8?"*. It only receives the resolved tool name and arguments. The natural language stays between you and Anthropic's API.

This also means:
- **Privacy**: your conversational text is not logged by Stigix
- **What Stigix logs** (`mcp-history.jsonl`): only `tool_name`, `agent_id`, `duration_ms`, `status` — never the prompt
- **Debugging**: if a tool is called with wrong arguments, the issue is in Claude's reasoning (docstring quality), not in Stigix

---

*Last Updated: v1.4.0-patch.108 — 2026-05-30*

