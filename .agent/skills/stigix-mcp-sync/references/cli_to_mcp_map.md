# Stigix CLI → MCP Tool Registry

> **Last synced:** v1.4.0-patch.142 (2026-06-01)  
> **MCP tools total:** 48  
> **Coverage:** ~96% of CLI capabilities

This is the living reference file for the `stigix-mcp-sync` skill.
Update this file every time you add, fix, or remove MCP tools.

---

## Legend

| Symbol | Meaning |
|---|---|
| ✅ MAPPED | CLI command has a fully equivalent MCP tool |
| ⚠️ PARTIAL | Tool exists but missing parameters or has payload drift |
| ❌ NOT MAPPED | No MCP tool exists for this CLI command |

---

## Status & Health

| CLI Command / API | MCP Tool | Status | Notes |
|---|---|---|---|
| `status` → `/api/system/health` | `get_node_status` | ✅ MAPPED | Also aggregates version, traffic, siteinfo, convergence |
| `status` → `/api/version` | `get_node_status` | ✅ MAPPED | Included in aggregation |
| `status` → `/api/siteinfo` | `get_node_status` | ✅ MAPPED | Included in aggregation |
| `status` → `/api/connectivity/public-ip` | `get_public_ip` | ✅ MAPPED | Dedicated tool |
| `status` → `/api/convergence/status` | `get_node_status` | ✅ MAPPED | Included in aggregation |
| `status` → `/api/system/interfaces` | — | ❌ NOT MAPPED | Individual interface data not exposed |
| `status` → `/api/system/gateway-ip` | — | ❌ NOT MAPPED | Gateway IP not exposed |
| `status` → `/api/config/interfaces` | — | ❌ NOT MAPPED | Traffic interface config not exposed |

---

## Traffic Generation

| CLI Command / API | MCP Tool | Status | Notes |
|---|---|---|---|
| `traffic start` → `/api/traffic/start` | `set_traffic_status(enabled=True)` | ✅ MAPPED | |
| `traffic stop` → `/api/traffic/stop` | `set_traffic_status(enabled=False)` | ✅ MAPPED | |
| `traffic status` → `/api/traffic/status` | `get_traffic_stats` | ✅ MAPPED | Also returns per-app stats |
| `traffic speed` → `/api/traffic/settings` (sleep_interval) | `set_traffic_rate` | ✅ MAPPED | Rate = sleep interval in seconds |
| `traffic density` → `/api/traffic/rate` (client_count) | `set_traffic_client_count` | ✅ MAPPED | Range 1–20 |
| `traffic stats` → `/api/stats` + `/api/traffic/status` | `get_traffic_stats` | ✅ MAPPED | |
| `traffic logs` → `/api/logs` | `get_traffic_logs` | ✅ MAPPED | configurable limit |
| `traffic reset` → `DELETE /api/stats` | — | ❌ NOT MAPPED | Stats reset not exposed |
| `traffic voice start/stop` → `/api/voice/control` | `set_voice_status` | ✅ MAPPED | |
| `traffic apps list` → `/api/config/apps` | `list_apps` | ✅ MAPPED | |
| `traffic apps export` → `/api/config/applications/export` | `export_app_config` | ✅ MAPPED | |
| `traffic apps import` → `/api/config/applications/import` | `import_app_config` | ✅ MAPPED | ⚠️ Overwrites config |

---

## XFR Speedtest

| CLI Command / API | MCP Tool | Status | Notes |
|---|---|---|---|
| `speedtest run` → `/api/tests/xfr` (POST) | `run_test(profile='xfr')` | ✅ MAPPED | Source must be fabric node |
| `speedtest list/history` → `/api/tests/xfr` (GET) | `list_speedtest_history` | ✅ MAPPED | Configurable limit |

---

## Convergence / Failover

| CLI Command / API | MCP Tool | Status | Notes |
|---|---|---|---|
| `convergence start` → `/api/convergence/start` | `run_test(profile='conv')` | ✅ MAPPED | |
| `convergence stop` → `/api/convergence/stop` | `stop_test` | ✅ MAPPED | Waits for final metrics |
| `convergence status` → `/api/convergence/status` | `get_test_status` / `get_node_status` | ✅ MAPPED | |
| `convergence history` → `/api/convergence/history` | — | ❌ NOT MAPPED | **Phase 4 target** |

---

## Security Testing

| CLI Command / API | MCP Tool | Status | Notes |
|---|---|---|---|
| `security url <url>` → `/api/security/url-test` | `run_security_probe(type='url')` | ✅ MAPPED | |
| `security url-batch` → `/api/security/url-test-batch` | `run_security_url_batch` | ✅ MAPPED | Auto-reads config+profile |
| `security dns <domain>` → `/api/security/dns-test` | `run_security_probe(type='dns')` | ✅ MAPPED | |
| `security dns-batch` → `/api/security/dns-test-batch` | `run_security_dns_batch` | ✅ MAPPED | Auto-reads config+profile |
| `security threat <url>` → `/api/security/threat-test` | `run_security_probe(type='threat')` | ✅ MAPPED | |
| `security eicar` → `/api/security/cloud-eicar-url` + `/api/security/threat-test` | `run_eicar_test` | ✅ MAPPED | Auto-fetches cloud EICAR URL |
| `security suite` → (all 3 above combined) | `run_full_security_audit` | ✅ MAPPED | URL+DNS+EICAR with global summary |
| `security status` (options list) | `get_security_test_options` (static) | ⚠️ PARTIAL | Hardcoded list — use dynamic version |
| `security status` → `/api/security/profile` | `get_security_test_options_dynamic` | ✅ MAPPED | Live from node |
| `security results` → `/api/security/results/stats` | `get_security_results_stats` | ✅ MAPPED | |
| `security results <n>` → `/api/security/results?limit=N` | — | ❌ NOT MAPPED | Individual result list not exposed |
| `security config` → `/api/security/config` + `/api/security/profile` | `get_security_config` | ✅ MAPPED | Returns both config and profile |
| `security config set` → `POST /api/security/config` | — | ❌ NOT MAPPED | Config write not exposed (by design) |

---

## DEM / Experience Probes

| CLI Command / API | MCP Tool | Status | Notes |
|---|---|---|---|
| `probes list` → `/api/connectivity/custom` | `list_dem_probes` | ✅ MAPPED | |
| `probes add` → `POST /api/connectivity/custom` | `add_dem_probe` | ✅ MAPPED | Appends, preserves existing |
| `probes remove` → `POST /api/connectivity/custom` (minus entry) | `remove_dem_probe` | ✅ MAPPED | Case-insensitive match by name |
| `probes probe` → `/api/connectivity/test` | `run_dem_probes_now` | ✅ MAPPED | 90s timeout |
| `probes stats` → `/api/connectivity/stats` + `/api/connectivity/results` | `get_dem_probe_stats` | ✅ MAPPED | 1h window |
| `probes export` → `/api/connectivity/custom/export` | — | ❌ NOT MAPPED | Export to file not needed for Claude |
| `probes import` → `POST /api/connectivity/custom` | — | ❌ NOT MAPPED | Import from file not needed for Claude |
| `dem summary` → `/api/admin/system/dashboard-data` (dem section) | `get_dem_summary` | ✅ MAPPED | |
| `dem probe details` → same dashboard-data | `get_probe_details` | ✅ MAPPED | Fuzzy match by name |

---

## Fabric Targets / Peers

| CLI Command / API | MCP Tool | Status | Notes |
|---|---|---|---|
| `target list` → `/api/targets` | `list_fabric_targets` | ✅ MAPPED | |
| `target add` → `POST /api/targets` | `add_fabric_target` | ✅ MAPPED | All capability flags supported |
| `target remove` → `DELETE /api/targets/{id}` | `remove_fabric_target` | ✅ MAPPED | Match by name/host/ID prefix |
| `target enable` → `PUT /api/targets/{id}` | `set_fabric_target_enabled(True)` | ✅ MAPPED | |
| `target disable` → `PUT /api/targets/{id}` | `set_fabric_target_enabled(False)` | ✅ MAPPED | |
| `target export` → (file export) | — | ❌ NOT MAPPED | File export not relevant for Claude |
| `target import` → `POST /api/targets/import` | — | ❌ NOT MAPPED | File import not relevant for Claude |

---

## VyOS Router Management

| CLI Command / API | MCP Tool | Status | Notes |
|---|---|---|---|
| `vyos list routers` → `/api/vyos/routers` | `list_vyos_routers` | ✅ MAPPED | |
| `vyos scenarios` → `/api/vyos/sequences` | `list_vyos_scenarios` | ✅ MAPPED | |
| `vyos run <scenario>` → `/api/vyos/sequences/run/{id}` | `run_vyos_scenario` | ✅ MAPPED | |
| `vyos history` → `/api/vyos/history` | `get_vyos_timeline` | ✅ MAPPED | |
| `vyos enable/disable` → `POST /api/vyos/sequences` | `set_vyos_scenario_status` | ✅ MAPPED | |
| `vyos configure router` (custom config) | — | ❌ NOT MAPPED | **Phase 4 target** |

---

## Test Orchestration (Multi-node)

| CLI Command / API | MCP Tool | Status | Notes |
|---|---|---|---|
| `list endpoints` → registry | `list_endpoints` | ✅ MAPPED | Can filter by kind=fabric/internet |
| `run test (any profile)` | `run_test` | ✅ MAPPED | xfr/conv/voice/iot; multi-target via comma list |
| `get test status` | `get_test_status` | ✅ MAPPED | Global or local ID |
| `stop test` | `stop_test` | ✅ MAPPED | Waits for final conv metrics |

---

## Diagnostics & Analytics

| CLI Command / API | MCP Tool | Status | Notes |
|---|---|---|---|
| `diagnostics` → `/api/admin/system/dashboard-data` | `get_diagnostics` | ✅ MAPPED | CPU, bitrate, app stats, voice, peers |
| `app score <app>` | `get_app_score` | ✅ MAPPED | Fuzzy match on app name |
| Node comparison (two nodes) | `compare_nodes` | ✅ MAPPED | Side-by-side node comparison |
| Summary report (fabric-wide) | `generate_report` | ✅ MAPPED | Fabric-wide status report |

---

## Prisma Flow Browser

| CLI Command / API | MCP Tool | Status | Notes |
|---|---|---|---|
| `flows query` → `/api/prisma/flows` | `get_prisma_flows` | ✅ MAPPED | Filter by ports, IPs, protocol, minutes |

---

## NOT MAPPED Summary (Phase 4 targets)

| Missing Tool | CLI Equivalent | API | Priority |
|---|---|---|---|
| `get_convergence_history` | `convergence history` | `/api/convergence/history` | 🔴 High |
| `configure_vyos_router` | `vyos configure` | `/api/vyos/routers` (PUT) | 🟢 Low |
| `list_security_results` | `security results <n>` | `/api/security/results?limit=N` | 🟢 Low |
| `reset_stats` | `traffic reset` | `DELETE /api/stats` | 🟢 Low |
