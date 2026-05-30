# MCP Batch Test Prompts — Stigix
*Copie-colle le contenu de chaque section "PROMPT" dans Claude Desktop*

---

## PROMPT — Test Phase 1 (Read-only, sans risque)

```
I need you to run a complete diagnostic of my Stigix network using the MCP tools.
Execute each step in order.

⚠️ IMPORTANT RULES — follow exactly for EACH step:

After every tool call, show THREE things in this exact order:

**1. 📊 Full Output** — the complete data returned: tables, lists, all fields, all numbers. Do NOT truncate.

**2. 📌 Synthesis** — 1-3 sentences: what does this data mean? What is notable or unexpected?

**3. ✅ Validation line** (one line, always):
`[TOOL: tool_name | STATUS: OK or ERROR | NOTE: error message if any, or "none"]`

Rules:
- One step = one tool call = 3-part output. Never group steps.
- Always include the validation line, even when successful.
- If a tool returns an error, show the full error in the Full Output section.

**NODE TO TEST: BR8**

---

Step 1 — Call list_endpoints. Show the complete list of all nodes with IPs, capabilities, and source. Then synthesize: how many nodes, managed vs synthesized.

Step 2 — Call get_node_status for BR8. Show all details: health, version, uptime, memory, disk, traffic, tools. Then synthesize: overall node health in one sentence.

Step 3 — Call get_public_ip for BR8. Show the WAN IP. Then synthesize: the exit IP and location if available.

Step 4 — Call get_traffic_stats for BR8. Show total requests, error count, top 10 apps, apps with errors. Then synthesize: traffic health and notable error patterns.

Step 5 — Call get_traffic_logs for BR8 with limit=20. Show each log line with timestamp, level, URL, result. Then synthesize: any recurring errors or patterns.

Step 6 — Call list_dem_probes for BR8. Show all probes grouped by category with type, target, status. Then synthesize: total probes, active vs disabled vs stale count.

Step 7 — Call get_dem_summary for BR8. Show the global DEM health score and probe statistics. Then synthesize: global DEM health and main issues.

Step 8 — Call get_probe_details for the first active probe found on BR8. Show all available metrics. Then synthesize: latency, availability, trend.

Step 9 — Call list_speedtest_history for BR8. Show last tests with throughput, protocol, target, duration. Then synthesize: best and worst throughput.

Step 10 — Call list_fabric_targets for BR8. Show all targets with capabilities and enabled status. Then synthesize: active targets count and any missing capabilities.

Step 11 — Call list_apps for BR8. Show all app categories with domains and weights. Then synthesize: top 3 simulated categories.

Step 12 — Call get_app_score for BR8. Show quality scores per application. Then synthesize: best and worst scored apps.

Step 13 — Call get_diagnostics for BR8. Show full diagnostic results (curl, DNS, connectivity...). Then synthesize: any failing checks.

Step 14 — Call get_security_config for BR8. Show the active security policy configuration. Then synthesize: which security features are enabled.

Step 15 — Call get_security_test_options for BR8. Show available test types and scenarios. Then synthesize: what's available to test.

Step 16 — Call get_security_results_stats for BR8. Show full breakdown: blocked, sinkholed, allowed by count and percentage. Then synthesize: overall blocking rate.

Step 17 — Call list_security_results for BR8 with limit=20. Show each result with ID, type, domain, status. Then synthesize: dominant threat type and neutralization rate.

Step 18 — Call get_convergence_history for BR8 with limit=10. Show each test with target, RTT, loss, blackout, verdict. Then synthesize: best and worst convergence path.

Step 19 — Call compare_nodes for BR8 and DC1. Show the full side-by-side comparison. Then synthesize: key differences between the two nodes.

---

After all 19 steps, give me a final summary table:
| Step | Tool | 📌 Key Takeaway | Status |
|---|---|---|---|
```

---

## PROMPT — Test Phase 2 (Tests actifs — déclenche des actions)

```
Run the following Stigix security and network tests in sequence on node BR8.

⚠️ IMPORTANT RULES — follow exactly for EACH step:

After every tool call, show THREE things in this exact order:

**1. 📊 Full Output** — the complete data returned: tables, lists, all fields, all numbers. Do NOT truncate.

**2. 📌 Synthesis** — 1-3 sentences: what does this data mean? What is notable or unexpected?

**3. ✅ Validation line** (one line, always):
`[TOOL: tool_name | STATUS: OK or ERROR | NOTE: error message if any, or "none"]`

Rules:
- One step = one tool call = 3-part output. Never group steps.
- Always include the validation line, even when successful.
- If a tool returns an error, show the full error in the Full Output section.

**NODE TO TEST: BR8**

---

Step 1 — Call run_security_url_batch for BR8. Show all URL categories tested with their status (blocked/allowed/error). Then synthesize: total blocked vs allowed, notable categories.

Step 2 — Call run_security_dns_batch for BR8. Show all DNS threat categories tested with their status. Then synthesize: total neutralized (blocked+sinkholed) vs resolved.

Step 3 — Call run_eicar_test for BR8. Show the full response including EICAR URL used and result. Then synthesize: was the threat blocked or allowed?

Step 4 — Call run_dem_probes_now for BR8. Show the trigger confirmation and any immediate results. Then synthesize: how many probes were triggered.

Step 5 — Call run_security_probe for BR8 with test_type="url" and target="https://malware.testpanw.com". Show the full response. Then synthesize: blocked or allowed?

Step 6 — Call run_security_probe for BR8 with test_type="dns" and target="test-malware.testpanw.com". Show the full response. Then synthesize: blocked, sinkholed, or resolved?

Step 7 — Call run_full_security_audit for BR8 (this takes 7-10 minutes — wait for completion). Show the complete audit results for all 3 phases. Then synthesize: overall security posture score and top recommendations.

---

After all 7 steps, give me a final security report:
| Phase | Score | Status |
|---|---|---|
| URL Filtering | X/Y blocked | ✅/⚠️/❌ |
| DNS Security | X/Y neutralized | ✅/⚠️/❌ |
| Threat Prevention | blocked/allowed | ✅/⚠️/❌ |
| **Overall** | | |
```

---

## PROMPT — Test Phase 3 (Multi-nœuds & rapport global)

```
Run a global fabric health check across all Stigix nodes.

⚠️ IMPORTANT RULES — follow exactly for EACH step:

After every tool call, show THREE things in this exact order:

**1. 📊 Full Output** — the complete data returned: tables, lists, all fields, all numbers. Do NOT truncate.

**2. 📌 Synthesis** — 1-3 sentences: what does this data mean? What is notable or unexpected?

**3. ✅ Validation line** (one line, always):
`[TOOL: tool_name | STATUS: OK or ERROR | NOTE: error message if any, or "none"]`

Rules:
- One step = one tool call = 3-part output. Never group steps.
- Always include the validation line, even when successful.
- If a tool returns an error, show the full error in the Full Output section.

---

Step 1 — Call generate_report with no filter (all nodes). Show the complete per-node status table. Then synthesize: how many nodes healthy vs unhealthy.

Step 2 — Call compare_nodes for BR8 and Hetzner. Show full comparison. Then synthesize: key differences.

Step 3 — Call get_public_ip for DC1. Show the WAN IP. Then synthesize: exit IP.

Step 4 — Call get_public_ip for Hetzner. Show the WAN IP. Then synthesize: exit IP.

Step 5 — Call get_node_status for DC1. Show all details. Then synthesize: health and version.

Step 6 — Call get_security_results_stats for DC1. Show full breakdown. Then synthesize: DC1 blocking rate vs BR8.

Step 7 — Call get_convergence_history for DC1. Show last 10 tests. Then synthesize: best path from DC1.

---

Final output: global fabric health table
| Node | Status | Version | Traffic | Security% | Best Convergence |
|---|---|---|---|---|---|
```

---

## PROMPT — Test Phase 4 (Config writes — ⚠️ sur BR8 seulement)

```
Test configuration changes on BR8. All changes will be reverted.

⚠️ IMPORTANT RULES — follow exactly for EACH step:

After every tool call, show THREE things in this exact order:

**1. 📊 Full Output** — the complete data returned: tables, lists, all fields, all numbers. Do NOT truncate.

**2. 📌 Synthesis** — 1-3 sentences: what does this data mean? What is notable or unexpected?

**3. ✅ Validation line** (one line, always):
`[TOOL: tool_name | STATUS: OK or ERROR | NOTE: error message if any, or "none"]`

Rules:
- One step = one tool call = 3-part output. Never group steps.
- Always include the validation line, even when successful.
- If a tool returns an error, show the full error in the Full Output section.

---

Step 1 — Call export_app_config for BR8. Show the full JSON config. Then synthesize: number of categories and total apps configured.

Step 2 — Call get_traffic_stats for BR8 (capture current client count as baseline). Then synthesize: current client count.

Step 3 — Call set_traffic_client_count for BR8 with count=2. Show the response. Then synthesize: was the change accepted?

Step 4 — Call get_traffic_stats for BR8 (verify change). Show updated stats. Then synthesize: confirm client count changed to 2.

Step 5 — Call set_traffic_client_count for BR8 with count=1 (restore). Show the response. Then synthesize: restored to original.

Step 6 — Call list_dem_probes for BR8 (capture current count as baseline). Then synthesize: current total probe count.

Step 7 — Call add_dem_probe for BR8 with name="Test-Probe-MCP", type="HTTP", target="https://stigix.io", interval=60. Show the response. Then synthesize: probe created successfully?

Step 8 — Call list_dem_probes for BR8 (verify addition). Show the new probe in the list. Then synthesize: probe "Test-Probe-MCP" found.

Step 9 — Call remove_dem_probe for BR8 for the probe named "Test-Probe-MCP". Show the response. Then synthesize: probe deleted.

Step 10 — Call list_dem_probes for BR8 (verify deletion). Then synthesize: confirm probe is gone, count back to baseline.

---

Final test report:
| Step | Action | Before | After | Reverted | Status |
|---|---|---|---|---|---|
```

---

## PROMPT — Speedtest (⚠️ génère du trafic réseau)

```
Run network performance tests between Stigix nodes.

⚠️ IMPORTANT RULES — follow exactly for EACH step:

After every tool call, show THREE things in this exact order:

**1. 📊 Full Output** — the complete data returned: tables, lists, all fields, all numbers. Do NOT truncate.

**2. 📌 Synthesis** — 1-3 sentences: what does this data mean? What is notable or unexpected?

**3. ✅ Validation line** (one line, always):
`[TOOL: tool_name | STATUS: OK or ERROR | NOTE: error message if any, or "none"]`

Rules:
- One step = one tool call = 3-part output. Never group steps.
- Always include the validation line, even when successful.
- If a tool returns an error, show the full error in the Full Output section.

---

Step 1 — Call run_test with source_id="BR8", target_id="DC1", profile="xfr", duration="30s". Show the response (test ID, status). Then synthesize: test started or error?

Step 2 — Wait 35 seconds then call get_test_status for the test ID from step 1. Show full status. Then synthesize: completed? throughput?

Step 3 — Call run_test with source_id="BR8", target_id="Hetzner", profile="xfr", duration="30s", bitrate="100M". Show the response. Then synthesize: test started or error?

Step 4 — Wait 35 seconds then call get_test_status for step 3 test ID. Show full status. Then synthesize: completed? throughput? Did it reach 100M?

Step 5 — Call list_speedtest_history for BR8. Show updated history including the 2 new tests. Then synthesize: compare throughput BR8→DC1 vs BR8→Hetzner.

---

Final network performance table:
| Route | Protocol | Duration | Throughput | Target Bitrate | Status |
|---|---|---|---|---|---|
```

---

## Tips

- **Sauvegarde** : à la fin de chaque phase, demande "save this complete output as markdown" — Claude génère un fichier `.md` que tu peux copier
- **Si un step échoue** : note le numéro et l'erreur exacte → je corrige le tool
- **Ordre recommandé** : Phase 1 → Phase 2 → Phase 3 → Phase 4 → Speedtest
