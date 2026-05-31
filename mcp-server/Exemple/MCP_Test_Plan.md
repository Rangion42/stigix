# 🧪 Stigix MCP — Full Validation Test Plan

> **Version**: v1.4.0-patch.128+  
> **Goal**: Validate all 52+ MCP tools via Claude Desktop under real conditions.  
> **Notation**: ✅ Pass | ❌ Fail | ⚠️ Partial response

---

## 📖 How to Use This Document

Copy-paste each prompt exactly into Claude Desktop.  
After each response, mark ✅ (pass), ❌ (fail), or ⚠️ (partial).  
For troubleshooting: ask Claude to dump the raw MCP tool request and response.

---

## 🛠️ Universal Debug Command

If any tool fails, ask Claude:

```
Can you show me exactly which MCP request you sent and what raw response you received?
```

---

## 📋 Table of Contents

| Section | Topic | Tools |
|---------|-------|-------|
| [1 — Discovery & Inventory](#section-1--discovery--inventory-foundation) | List endpoints, global report | `list_endpoints`, `generate_report` |
| [2 — Node Status](#section-2--node-status-per-node-diagnostics) | Health, diagnostics, public IP, comparison | `get_node_status`, `get_diagnostics`, `get_public_ip`, `compare_nodes` |
| [3 — Traffic Generation](#section-3--traffic-generation) | Start/stop traffic, apps, logs, export | `set_traffic_status`, `list_apps`, `get_traffic_stats`, `export_app_config` |
| [4 — DEM Probes](#section-4--digital-experience-monitoring-dem) | Probe list, stats, add/remove | `list_dem_probes`, `add_dem_probe`, `remove_dem_probe`, `run_dem_probes_now` |
| [5 — Fabric Targets](#section-5--fabric-targets-peers) | Peer management, enable/disable | `list_fabric_targets`, `set_fabric_target_enabled` |
| [6 — Traffic Tests](#section-6--traffic-tests-xfr--speedtest--convergence) | Speedtest, convergence, stop | `run_test`, `get_test_status`, `stop_test`, `get_convergence_history` |
| [7 — Security Testing](#section-7--security-testing) | URL/DNS/EICAR probes, batches, audit | `get_security_test_options`, `run_security_probe`, `run_full_security_audit` |
| [8 — VyOS Chaos](#section-8--vyos-network-chaos) | Latency, loss, IP blocks, scenarios | `vyos_execute_action`, `vyos_bulk_reset`, `run_vyos_scenario` |
| [9 — Voice Simulation](#section-9--voice-simulation) | Start/stop voice | `set_voice_status` |
| [10 — Edge Cases](#section-10--advanced-tests--edge-cases) | Error handling, ambiguity, import/export | `export_app_config`, `import_app_config` |
| [11 — Clone Node Config](#section-11--clone-node-config-multi-deployment) | Multi-node deployment clone | `clone_node_config` |
| [Results Table](#-results-tracking-table) | Full tracking spreadsheet | All 52 tools |
| [Debug Questions](#-key-debug-questions) | Troubleshooting guide | — |

---

## SECTION 1 — Discovery & Inventory (Foundation)

**Goal**: Verify that Claude can list available endpoints. This is a prerequisite for all other tests.

### Test 1.1 — List all endpoints

```
Show me all available Stigix endpoints.
```

- **Expected tool**: `list_endpoints()`
- **Expected result**: List of fabric nodes and/or internet targets with their IDs.
- **Note**: The IDs returned here are the ones to use in all subsequent tests.

---

### Test 1.2 — Filter by Fabric type

```
List only Stigix Fabric nodes.
```

- **Expected tool**: `list_endpoints(kind="fabric")`
- **Expected result**: Subset of the previous list containing only internal fabric nodes.

---

### Test 1.3 — Filter by Internet type

```
List only Stigix Internet targets.
```

- **Expected tool**: `list_endpoints(kind="internet")`
- **Expected result**: Subset containing only external targets.

---

### Test 1.4 — Full Fabric report

```
Generate a full report across all Stigix nodes in the fabric.
```

- **Expected tool**: `generate_report()`
- **Expected result**: Summary view of all nodes (health, version, traffic, DEM, security, peers).

---

## SECTION 2 — Node Status (Per-Node Diagnostics)

**Goal**: Validate status and diagnostic tools. Replace `<NODE_ID>` with a real ID obtained in Section 1.

### Test 2.1 — Full node status

```
Give me the full status of node <NODE_ID>.
```

- **Expected tool**: `get_node_status(agent_id="<NODE_ID>")`
- **Expected result**: Health, version, traffic status, site info, convergence state.

---

### Test 2.2 — Full diagnostics dashboard

```
Show me the full diagnostics dashboard for node <NODE_ID>.
```

- **Expected tool**: `get_diagnostics(agent_id="<NODE_ID>")`
- **Expected result**: CPU, bitrate, app stats, voice, peers.

---

### Test 2.3 — Public IP / WAN path

```
What is the public IP of node <NODE_ID>? What WAN path does it use to reach the internet?
```

- **Expected tool**: `get_public_ip(agent_id="<NODE_ID>")`
- **Expected result**: WAN IP of the node.

---

### Test 2.4 — Side-by-side node comparison

```
Compare nodes <NODE_ID_A> and <NODE_ID_B> side by side.
```

- **Expected tool**: `compare_nodes(agent_id_a="<NODE_ID_A>", agent_id_b="<NODE_ID_B>")`
- **Expected result**: Comparison table: health / version / traffic / DEM / security.

---

## SECTION 3 — Traffic Generation

**Goal**: Validate application traffic control tools.

### Test 3.1 — Live traffic stats

```
Show me the live application traffic generation stats for node <NODE_ID>.
```

- **Expected tool**: `get_traffic_stats(agent_id="<NODE_ID>")`
- **Expected result**: Requests per app, error rates, active clients.

---

### Test 3.2 — Simulated applications

```
Which applications are being simulated on node <NODE_ID>?
```

- **Expected tool**: `list_apps(agent_id="<NODE_ID>")`
- **Expected result**: List including Teams, Zoom, Salesforce, etc.

---

### Test 3.3 — App-specific score

```
What is the success rate of Teams on node <NODE_ID>?
```

- **Expected tool**: `get_app_score(agent_id="<NODE_ID>", app_name="teams")`
- **Expected result**: Success rate %, status Healthy/Degraded/Critical.

---

### Test 3.4 — Traffic logs

```
Show me the last 20 traffic logs for node <NODE_ID>.
```

- **Expected tool**: `get_traffic_logs(agent_id="<NODE_ID>", limit=20)`
- **Expected result**: Recent log entries.

---

### Test 3.5 — Start traffic

```
Start application traffic generation on node <NODE_ID>.
```

- **Expected tool**: `set_traffic_status(source_id="<NODE_ID>", enabled=True)`
- **Expected result**: Start confirmation.
- ⚠️ **Verify**: Re-run Test 3.1 to confirm traffic is running.

---

### Test 3.6 — Adjust traffic rate

```
Set the traffic rate on node <NODE_ID> to 0.5 seconds between requests.
```

- **Expected tool**: `set_traffic_rate(agent_id="<NODE_ID>", rate=0.5)`
- **Expected result**: Change confirmation.

---

### Test 3.7 — Increase simulated client count

```
Set node <NODE_ID> to 5 parallel simulated clients.
```

- **Expected tool**: `set_traffic_client_count(agent_id="<NODE_ID>", client_count=5)`
- **Expected result**: Confirmation.

---

### Test 3.8 — Stop traffic

```
Stop application traffic generation on node <NODE_ID>.
```

- **Expected tool**: `set_traffic_status(source_id="<NODE_ID>", enabled=False)`
- **Expected result**: Stop confirmation.

---

### Test 3.9 — Export application config

```
Export the application configuration from node <NODE_ID>.
```

- **Expected tool**: `export_app_config(agent_id="<NODE_ID>")`
- **Expected result**: JSON configuration object.

---

## SECTION 4 — Digital Experience Monitoring (DEM)

**Goal**: Validate all DEM / connectivity probe tools.

### Test 4.1 — DEM global summary

```
Give me the DEM summary for node <NODE_ID>.
```

- **Expected tool**: `get_dem_summary(agent_id="<NODE_ID>")`
- **Expected result**: Global health score, individual probe statuses.

---

### Test 4.2 — List DEM probes

```
List all DEM probes configured on node <NODE_ID>.
```

- **Expected tool**: `list_dem_probes(agent_id="<NODE_ID>")`
- **Expected result**: Name, type (HTTP/PING/DNS/TCP/UDP), target, enabled status.

---

### Test 4.3 — Historical probe stats

```
Show me the historical DEM probe statistics for node <NODE_ID> over the last hour.
```

- **Expected tool**: `get_dem_probe_stats(agent_id="<NODE_ID>")`
- **Expected result**: Global score, average latency, reliability per probe.

---

### Test 4.4 — Specific probe details

```
Give me the performance details for the "Google DNS" probe on node <NODE_ID>.
```

- **Expected tool**: `get_probe_details(agent_id="<NODE_ID>", probe_name="Google DNS")`
- **Expected result**: Score, total latency, reachability.

---

### Test 4.5 — Run probes immediately

```
Trigger an immediate run of all DEM probes on node <NODE_ID>.
```

- **Expected tool**: `run_dem_probes_now(agent_id="<NODE_ID>")`
- **Expected result**: RTT, status, reachability for each probe.
- ⚠️ **Note**: May take 30-60 seconds.

---

### Test 4.6 — Add a new probe

```
Add a PING probe to 8.8.8.8 named "Google DNS Test" on node <NODE_ID>.
```

- **Expected tool**: `add_dem_probe(agent_id="<NODE_ID>", name="Google DNS Test", target="8.8.8.8", probe_type="PING")`
- **Expected result**: Add confirmation.
- ⚠️ **Verify**: Re-run Test 4.2 to confirm the probe appears.

---

### Test 4.7 — Remove a probe

```
Remove the "Google DNS Test" probe from node <NODE_ID>.
```

- **Expected tool**: `remove_dem_probe(agent_id="<NODE_ID>", probe_name="Google DNS Test")`
- **Expected result**: Removal confirmation.
- ⚠️ **Verify**: Re-run Test 4.2 to confirm deletion.

---

## SECTION 5 — Fabric Targets (Peers)

**Goal**: Validate Fabric peer management.

### Test 5.1 — List fabric targets

```
List all Fabric peers configured on node <NODE_ID>.
```

- **Expected tool**: `list_fabric_targets(agent_id="<NODE_ID>")`
- **Expected result**: Name, host, capabilities (xfr, voice, conv, security), enabled status.

---

### Test 5.2 — Disable a fabric target

```
Disable the fabric target "<TARGET_NAME>" on node <NODE_ID>.
```

- **Expected tool**: `set_fabric_target_enabled(agent_id="<NODE_ID>", target_name_or_host="<TARGET_NAME>", enabled=False)`
- **Expected result**: Confirmation.

---

### Test 5.3 — Re-enable a fabric target

```
Re-enable the fabric target "<TARGET_NAME>" on node <NODE_ID>.
```

- **Expected tool**: `set_fabric_target_enabled(agent_id="<NODE_ID>", target_name_or_host="<TARGET_NAME>", enabled=True)`
- **Expected result**: Confirmation.

---

## SECTION 6 — Traffic Tests (XFR / Speedtest / Convergence)

**Goal**: Validate launch and monitoring of performance tests.

### Test 6.1 — Speedtest history

```
Show me the last 10 speedtests from node <NODE_ID>.
```

- **Expected tool**: `list_speedtest_history(agent_id="<NODE_ID>", limit=10)`
- **Expected result**: Historical results with target, protocol, throughput Mbps, RTT.

---

### Test 6.2 — Launch a simple XFR speedtest

```
Run a 30-second speedtest between <SOURCE_ID> and <TARGET_ID> using TCP.
```

- **Expected tool**: `run_test(source_id="<SOURCE_ID>", target_id="<TARGET_ID>", profile="xfr", duration="30s", protocol="tcp")`
- **Expected result**: Test ID and initial status.

---

### Test 6.3 — Check test status

```
What is the status of test <TEST_ID>?
```

- **Expected tool**: `get_test_status(test_id="<TEST_ID>")`
- **Expected result**: Status (running/completed/error), metrics.

---

### Test 6.4 — Speedtest with bitrate limit

```
Run a speedtest between <SOURCE_ID> and <TARGET_ID> capped at 100M bidirectional.
```

- **Expected tool**: `run_test(source_id="<SOURCE_ID>", target_id="<TARGET_ID>", profile="xfr", bitrate="100M", direction="bidirectional")`
- **Expected result**: Test launch confirmation.

---

### Test 6.5 — Stop a running test

```
Stop test <TEST_ID>.
```

- **Expected tool**: `stop_test(test_id="<TEST_ID>")`
- **Expected result**: Stop confirmation + final metrics.

---

### Test 6.6 — Convergence test (CONV)

```
Start a convergence test between <SOURCE_ID> and <TARGET_ID> at 100 pps.
```

- **Expected tool**: `run_test(source_id="<SOURCE_ID>", target_id="<TARGET_ID>", profile="conv", pps=100)`
- **Expected result**: Convergence test ID + Claude announces the ID and **waits for the user to say "stop"**.
- ⚠️ **Expected behavior**: Claude MUST NOT poll or call `get_test_status` automatically.

---

### Test 6.7 — Convergence history

```
Show me the last 5 convergence tests for node <NODE_ID>.
```

- **Expected tool**: `get_convergence_history(agent_id="<NODE_ID>", limit=5)`
- **Expected result**: Results with max blackout (ms) and verdict (PERFECT/GOOD/DEGRADED/BAD/CRITICAL).

---

## SECTION 7 — Security Testing

**Goal**: Validate all security testing tools.

### Test 7.1 — Node security configuration

```
Show me the security configuration for node <NODE_ID>.
```

- **Expected tool**: `get_security_config(agent_id="<NODE_ID>")`
- **Expected result**: Enabled modules, test profile (DNS, URL, threat).

---

### Test 7.2 — Security scorecard (posture)

```
What is the current security score for node <NODE_ID>?
```

- **Expected tool**: `get_security_results_stats(agent_id="<NODE_ID>")`
- **Expected result**: `posture_scores` (url_filter, dns_security, threat_prevention 0-100) + 24h trend.

---

### Test 7.3 — Recent security test results

```
Show me the last 10 security test results for node <NODE_ID>.
```

- **Expected tool**: `list_security_results(agent_id="<NODE_ID>", limit=10)`
- **Expected result**: Chronological URL/DNS/Threat results.

---

### Test 7.4 — DNS test options (live from node)

```
What DNS security targets are available on node <NODE_ID>?
```

- **Expected tool**: `get_security_test_options(agent_id="<NODE_ID>", probe_type="dns")`
- **Expected result**: List of configured test domains (malware, phishing, c2, etc.) from the node's actual profile.
- ℹ️ **Note**: `get_security_test_options` is now **dynamic** and requires `agent_id`. It replaces the former static tool.

---

### Test 7.5 — URL test options (live from node)

```
What URL categories are configured on node <NODE_ID>?
```

- **Expected tool**: `get_security_test_options(agent_id="<NODE_ID>", probe_type="url")`
- **Expected result**: URL category list from the node's actual profile (not hardcoded Palo Alto URLs).

---

### Test 7.6 — Available EICAR targets

```
What EICAR targets are available on node <NODE_ID>?
```

- **Expected tool**: `get_security_test_options(agent_id="<NODE_ID>", probe_type="threat")`
- **Expected result**: List of EICAR targets: fabric targets with `capabilities.security=true` + cloud if configured, with human-readable names (e.g., "Hetzner", "DC1").

---

### Test 7.7 — Single DNS test

```
Run a DNS security test for the malware domain on node <NODE_ID>.
```

**Expected Claude workflow**:
1. `get_security_test_options(agent_id="<NODE_ID>", probe_type="dns")` → fetches real targets
2. `run_security_probe(agent_id="<NODE_ID>", probe_type="dns", target="<malware-domain-from-profile>")` → runs the test

- **Expected result**: Blocked/Allowed + reason. **MCP** badge visible in the Security Log.

---

### Test 7.8 — Single URL filtering test

```
Test URL filtering for the "Hacking" category on node <NODE_ID>.
```

**Expected Claude workflow**:
1. `get_security_test_options(agent_id="<NODE_ID>", probe_type="url")` → fetches exact URL for the category
2. `run_security_probe(agent_id="<NODE_ID>", probe_type="url", target="<url-from-profile>")` → runs the test

- **Expected result**: Blocked/Allowed. **MCP** badge visible in the Security Log.

---

### Test 7.9 — EICAR test against a specific target

```
Run an EICAR threat prevention test against the Hetzner target from node <NODE_ID>.
```

**Expected Claude workflow**:
1. `get_security_test_options(agent_id="<NODE_ID>", probe_type="threat")` → sees list (Hetzner, DC1, Cloud...)
2. Selects "Hetzner" target
3. `run_security_probe(agent_id="<NODE_ID>", probe_type="threat", target="http://<hetzner-ip>:8082/eicar.com.txt")`

- **Expected result**: Blocked 🟢 (IPS active) or Allowed 🔴 (policy issue). **MCP** badge visible.

---

### Test 7.10 — Full DNS security batch

```
Run a full DNS security audit on node <NODE_ID>.
```

- **Expected tool**: `run_security_dns_batch(agent_id="<NODE_ID>")`
- **Expected result**: Summary (blocked/allowed/unknown) per domain.
- ⚠️ **Note**: May take up to 3 minutes.

---

### Test 7.11 — Full URL filtering batch

```
Run a full URL filtering audit on node <NODE_ID>.
```

- **Expected tool**: `run_security_url_batch(agent_id="<NODE_ID>")`
- **Expected result**: Summary per URL category.
- ⚠️ **Note**: May take up to 3 minutes.

---

### Test 7.12 — Full security audit (all 3 phases)

```
Run a full security audit on node <NODE_ID> — URL, DNS, and EICAR.
```

- **Expected tool**: `run_full_security_audit(agent_id="<NODE_ID>")`
- **Expected result**: Results from all 3 phases + global summary.
- ⚠️ **Note**: May take 7-10 minutes.

---

## SECTION 8 — VyOS Network Chaos

**Goal**: Validate VyOS network manipulation tools.  
⚠️ **Sensitive section** — always confirm actions before execution.

### Test 8.1 — List VyOS routers

```
List the VyOS routers managed by node <NODE_ID>.
```

- **Expected tool**: `list_vyos_routers(agent_id="<NODE_ID>")`
- **Expected result**: List of routers with their IDs.

---

### Test 8.2 — List available scenarios

```
What VyOS scenarios are available on node <NODE_ID>?
```

- **Expected tool**: `list_vyos_scenarios(agent_id="<NODE_ID>")`
- **Expected result**: List of sequences (failover, etc.).

---

### Test 8.3 — List chaos-eligible interfaces

```
Show me the network interfaces available for chaos engineering on node <NODE_ID>.
```

- **Expected tool**: `get_vyos_interfaces(agent_id="<NODE_ID>")`
- **Expected result**: Interfaces with description, IP, up/down status. Only interfaces with a description are returned.

---

### Test 8.4 — Live VyOS router state

```
What is the current state of router <ROUTER_ID> managed by node <NODE_ID>?
```

- **Expected tool**: `get_vyos_router_state(agent_id="<NODE_ID>", router_id="<ROUTER_ID>")`
- **Expected result**: Interfaces (up/down), active QoS, active IP blocks.

---

### Test 8.5 — VyOS change history

```
Show me the last 10 VyOS changes applied via node <NODE_ID>.
```

- **Expected tool**: `get_vyos_timeline(agent_id="<NODE_ID>", limit=10)`
- **Expected result**: Action history.

---

### Test 8.6 — Add latency (NL flow → confirmation)

```
Add 100ms of latency on the MPLS link of BR1 via node <NODE_ID>.
```

**Expected Claude workflow**:
1. `get_vyos_interfaces(agent_id="<NODE_ID>")` → finds the MPLS interface for BR1
2. Presents: "I found eth1 (BR1-MPLS-197) on vyosrouter. Apply 100ms? (yes/no)"
3. On confirmation → `vyos_execute_action(agent_id, router_id, "set-impairment", interface="eth1", latency_ms=100)`

- ⚠️ **IMPORTANT**: Claude MUST NOT apply the action without explicit user confirmation.

---

### Test 8.7 — Add packet loss

```
Add 5% packet loss on the WAN interface of router <ROUTER_ID> on node <NODE_ID>.
```

- **Expected workflow**: Same NL → identification → confirmation → `set-impairment` with `loss_pct=5`.

---

### Test 8.8 — Clear QoS on an interface

```
Remove QoS on eth1 of router <ROUTER_ID> managed by node <NODE_ID>.
```

- **Expected tool**: `vyos_execute_action(agent_id, router_id, "clear-qos", interface="eth1")`

---

### Test 8.9 — Global QoS reset

```
Clear all active QoS on router <ROUTER_ID> managed by node <NODE_ID>.
```

- **Expected tool**: `vyos_bulk_reset(agent_id="<NODE_ID>", router_id="<ROUTER_ID>", scope="all-qos")`
- **Expected result**: List of executed actions.

---

### Test 8.10 — Full reset

```
Do a full reset of router <ROUTER_ID> — QoS, IP blocks, and downed interfaces.
```

- **Expected tool**: `vyos_bulk_reset(agent_id="<NODE_ID>", router_id="<ROUTER_ID>", scope="full-reset")`

---

### Test 8.11 — Block an IP

```
Block traffic to 1.2.3.4 on router <ROUTER_ID> managed by node <NODE_ID>.
```

- **Expected tool**: `vyos_execute_action(agent_id, router_id, "deny-traffic", ip="1.2.3.4")`
- ⚠️ **IMPORTANT**: Claude must ask for confirmation before executing.

---

### Test 8.12 — Unblock an IP

```
Unblock traffic to 1.2.3.4 on router <ROUTER_ID> managed by node <NODE_ID>.
```

- **Expected tool**: `vyos_execute_action(agent_id, router_id, "allow-traffic", ip="1.2.3.4")`

---

### Test 8.13 — Run a VyOS scenario

```
Run scenario "<SCENARIO_ID>" on node <NODE_ID>.
```

- **Expected tool**: `run_vyos_scenario(agent_id="<NODE_ID>", scenario_id="<SCENARIO_ID>")`

---

### Test 8.14 — Enable/disable a cyclic scenario

```
Disable the cyclic scenario "<SCENARIO_ID>" running on node <NODE_ID>.
```

- **Expected tool**: `set_vyos_scenario_status(agent_id="<NODE_ID>", scenario_id="<SCENARIO_ID>", enabled=False)`

---

## SECTION 9 — Voice Simulation

### Test 9.1 — Start voice simulation

```
Start voice simulation on node <NODE_ID>.
```

- **Expected tool**: `set_voice_status(source_id="<NODE_ID>", enabled=True)`
- **Expected result**: Confirmation.
- ⚠️ **Note**: Node must be of fabric type.

---

### Test 9.2 — Stop voice simulation

```
Stop voice simulation on node <NODE_ID>.
```

- **Expected tool**: `set_voice_status(source_id="<NODE_ID>", enabled=False)`

---

## SECTION 10 — Advanced Tests & Edge Cases

### Test 10.1 — Non-existent node ID (error test)

```
Give me the status of node "NODE-THAT-DOES-NOT-EXIST".
```

- **Expected result**: Clean error from Claude (no crash), clear message that the node does not exist.

---

### Test 10.2 — Ambiguous VyOS NL resolution

```
Add 200ms of latency on the Internet link of BR2 via node <NODE_ID>.
```

**Expected Claude workflow**:
1. Calls `get_vyos_interfaces`
2. Finds MULTIPLE Internet links on BR2 (or ambiguity)
3. Lists the candidates and asks the user to choose
4. Does NOT execute without explicit choice

---

### Test 10.3 — Export application configuration

```
Export the application configuration from node <NODE_ID_SOURCE>.
```

- **Expected tool**: `export_app_config(agent_id="<NODE_ID_SOURCE>")`
- **Expected result**: JSON config object returned.

---

### Test 10.4 — Import application configuration

```
Copy the application configuration from node <NODE_ID_SOURCE> to <NODE_ID_DEST>.
```

**Expected Claude workflow**:
1. `export_app_config(agent_id="<NODE_ID_SOURCE>")` → fetches JSON config
2. Warns that import will overwrite the existing config
3. On confirmation → `import_app_config(agent_id="<NODE_ID_DEST>", config=<JSON>)`

---

## 📊 Results Tracking Table

| # | Tool | Status | Notes |
|---|------|--------|-------|
| 1.1 | `list_endpoints` | ⬜ | |
| 1.2 | `list_endpoints(kind=fabric)` | ⬜ | |
| 1.3 | `list_endpoints(kind=internet)` | ⬜ | |
| 1.4 | `generate_report` | ⬜ | |
| 2.1 | `get_node_status` | ⬜ | |
| 2.2 | `get_diagnostics` | ⬜ | |
| 2.3 | `get_public_ip` | ⬜ | |
| 2.4 | `compare_nodes` | ⬜ | |
| 3.1 | `get_traffic_stats` | ⬜ | |
| 3.2 | `list_apps` | ⬜ | |
| 3.3 | `get_app_score` | ⬜ | |
| 3.4 | `get_traffic_logs` | ⬜ | |
| 3.5 | `set_traffic_status(start)` | ⬜ | |
| 3.6 | `set_traffic_rate` | ⬜ | |
| 3.7 | `set_traffic_client_count` | ⬜ | |
| 3.8 | `set_traffic_status(stop)` | ⬜ | |
| 3.9 | `export_app_config` | ⬜ | |
| 4.1 | `get_dem_summary` | ⬜ | |
| 4.2 | `list_dem_probes` | ⬜ | |
| 4.3 | `get_dem_probe_stats` | ⬜ | |
| 4.4 | `get_probe_details` | ⬜ | |
| 4.5 | `run_dem_probes_now` | ⬜ | |
| 4.6 | `add_dem_probe` | ⬜ | |
| 4.7 | `remove_dem_probe` | ⬜ | |
| 5.1 | `list_fabric_targets` | ⬜ | |
| 5.2 | `set_fabric_target_enabled(disable)` | ⬜ | |
| 5.3 | `set_fabric_target_enabled(enable)` | ⬜ | |
| 6.1 | `list_speedtest_history` | ⬜ | |
| 6.2 | `run_test(xfr)` | ⬜ | |
| 6.3 | `get_test_status` | ⬜ | |
| 6.4 | `run_test(xfr+bitrate)` | ⬜ | |
| 6.5 | `stop_test` | ⬜ | |
| 6.6 | `run_test(conv)` — start/stop | ⬜ | Claude must wait for "stop" |
| 6.7 | `get_convergence_history` | ⬜ | |
| 7.1 | `get_security_config` | ⬜ | |
| 7.2 | `get_security_results_stats` | ⬜ | |
| 7.3 | `list_security_results` | ⬜ | |
| 7.4 | `get_security_test_options(agent_id, dns)` | ⬜ | Dynamic — requires agent_id |
| 7.5 | `get_security_test_options(agent_id, url)` | ⬜ | Dynamic — requires agent_id |
| 7.6 | `get_security_test_options(agent_id, threat)` | ⬜ | Returns fabric.security targets |
| 7.7 | `run_security_probe(dns)` + MCP badge | ⬜ | |
| 7.8 | `run_security_probe(url)` + MCP badge | ⬜ | |
| 7.9 | `run_security_probe(threat/eicar)` + MCP badge | ⬜ | |
| 7.10 | `run_security_dns_batch` | ⬜ | |
| 7.11 | `run_security_url_batch` | ⬜ | |
| 7.12 | `run_full_security_audit` | ⬜ | |
| 8.1 | `list_vyos_routers` | ⬜ | |
| 8.2 | `list_vyos_scenarios` | ⬜ | |
| 8.3 | `get_vyos_interfaces` | ⬜ | |
| 8.4 | `get_vyos_router_state` | ⬜ | |
| 8.5 | `get_vyos_timeline` | ⬜ | |
| 8.6 | `vyos_execute_action(set-impairment+latency)` | ⬜ | Confirmation required |
| 8.7 | `vyos_execute_action(set-impairment+loss)` | ⬜ | Confirmation required |
| 8.8 | `vyos_execute_action(clear-qos)` | ⬜ | |
| 8.9 | `vyos_bulk_reset(all-qos)` | ⬜ | |
| 8.10 | `vyos_bulk_reset(full-reset)` | ⬜ | |
| 8.11 | `vyos_execute_action(deny-traffic)` | ⬜ | Confirmation required |
| 8.12 | `vyos_execute_action(allow-traffic)` | ⬜ | |
| 8.13 | `run_vyos_scenario` | ⬜ | |
| 8.14 | `set_vyos_scenario_status` | ⬜ | |
| 9.1 | `set_voice_status(start)` | ⬜ | |
| 9.2 | `set_voice_status(stop)` | ⬜ | |
| 10.1 | Non-existent node error | ⬜ | |
| 10.2 | Ambiguous VyOS NL resolution | ⬜ | |
| 10.3 | `export_app_config` | ⬜ | |
| 10.4 | `import_app_config` | ⬜ | |
| 11.1 | `clone_node_config` (all scope) | ⬜ | |
| 11.2 | `clone_node_config` (partial scope) | ⬜ | |
| 11.3 | `clone_node_config` (JWT mismatch) | ⬜ | Must return per-component error |

---

## 📦 SECTION 11 — Clone Node Config (Multi-Deployment)

**Goal**: Validate the `clone_node_config` tool that clones apps, DEM probes, security profile, and VyOS scenarios from a source node to a target node.

> ⚠️ Prerequisite: JWT_SECRET must be identical on both nodes. Verify with `docker exec stigix printenv JWT_SECRET` on each node.

### Test 11.1 — Full clone BR8 → BR5

```
Clone the full configuration from BR8 to BR5: apps, DEM probes, security profile, and VyOS scenarios.
```

- **Expected tool**: `clone_node_config(source_id='<BR8_ID>', target_id='<BR5_ID>')`
- **Expected result**: Per-component report with `status: ok` for each item.
- **Verify**: Open BR5's UI and confirm that apps / DEM probes match BR8's configuration.

---

### Test 11.2 — Partial clone (DEM probes only)

```
Clone only the DEM probes from BR8 to BR5, without touching apps or the security profile.
```

- **Expected tool**: `clone_node_config(source_id='<BR8_ID>', target_id='<BR5_ID>', scope=['dem_probes'])`
- **Expected result**: `components.dem_probes.status: ok`, other components absent from the report.

---

### Test 11.3 — Clone security profile only

```
Copy the security profile from BR8 to BR5.
```

- **Expected tool**: `clone_node_config(..., scope=['security_profile'])`
- **Expected result**: `components.security_profile.status: ok` with `vendor`, `url_categories`, `dns_domains`.

---

### Test 11.4 — Clone to an invalid target node

```
Clone the configuration from BR8 to a node that does not exist: "BR999".
```

- **Expected tool**: `clone_node_config(source_id='<BR8_ID>', target_id='BR999')`
- **Expected result**: `{"error": "Target node 'BR999' not found."}`

---

## 🔍 Key Debug Questions

If a tool returns an error, ask Claude:

1. "Show me the raw JSON response you received from the MCP tool."
2. "What exact parameter did you pass to the tool?"
3. "Did the tool return an `error` field or a Python exception?"
4. "Can you retry with the exact ID `<NODE_ID>` as returned by `list_endpoints`?"
5. "Are there any messages in the MCP container logs? (`docker logs stigix-mcp-server --tail 50`)"
6. "Is the JWT_SECRET the same on both nodes? (`docker exec stigix printenv JWT_SECRET`)"
