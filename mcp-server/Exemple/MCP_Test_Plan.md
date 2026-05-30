# Plan de Test MCP Stigix — Exhaustif
*v1.4.0-patch.105 — 47 outils disponibles*

> **Comment utiliser ce document**  
> Copie-colle chaque prompt dans Claude Desktop avec le MCP Stigix configuré.  
> Note le résultat (✅ OK / 🔴 Erreur / ⚠️ Partiel) dans la colonne statut.  
> Remplace `BR8` par le nom exact de ton nœud si différent.

---

## ✅ Déjà testés (session 29/05/2026)

| Tool | Prompt utilisé | Résultat |
|---|---|---|
| `list_endpoints` | List all available Stigix nodes | ✅ 10 nœuds |
| `get_node_status` | What is the status of node BR8? | ✅ READY |
| `get_traffic_stats` | Show me the traffic stats for BR8 | ✅ 170 req |
| `list_dem_probes` | List all DEM probes configured on BR8 | ✅ 55 probes |
| `list_fabric_targets` | List all fabric targets on BR8 | ✅ 10 targets |
| `list_apps` | What apps is BR8 simulating? | ✅ 17 catégories |
| `get_traffic_logs` | Show me the last 10 traffic logs from BR8 | ✅ |
| `get_security_results_stats` | What is the security score for BR8? | ✅ 2840 tests |
| `list_security_results` | Show me the last 10 security test results on BR8 | ✅ DNS batch |
| `get_convergence_history` | Show me the last convergence tests for BR8 | ✅ 10 tests |
| `run_eicar_test` | Run an EICAR threat prevention test on BR8 | 🔴 400 → ✅ fixé patch.105 |
| `run_full_security_audit` | Run the full security audit on BR8 | ✅ 24/94 bloqués |

---

## 🔵 Phase 1 — Discovery & Read (sans effet de bord)

### 1.1 Endpoints & Topology

```
List all Stigix nodes of type fabric only
```
→ `list_endpoints(kind="fabric")` — teste le filtre par type

```
What is the public IP of BR8?
```
→ `get_public_ip` — IP WAN du nœud

```
Compare BR8 and DC1 side by side
```
→ `compare_nodes` — diff health/traffic/security entre 2 nœuds

```
Generate a full report for all Stigix nodes
```
→ `generate_report` — rapport global fabric (tous les nœuds en parallèle)

---

### 1.2 Traffic & Apps

```
What is the current traffic status on DC1?
```
→ `get_node_status` sur un autre nœud que BR8

```
Show me the last 50 traffic logs from BR8
```
→ `get_traffic_logs` avec plus de lignes

```
Show me the speedtest history for BR8
```
→ `list_speedtest_history` — historique des XFR tests (**jamais testé**)

```
Export the application config from BR8 as JSON
```
→ `export_app_config` — dump JSON de la config apps (**jamais testé**)

---

### 1.3 DEM & Probes

```
Show me the DEM summary for BR8
```
→ `get_dem_summary` — vue globale santé DEM (**jamais testé**)

```
Show me the details of the probe "Cloudflare ICMP" on BR8
```
→ `get_probe_details` — détails d'une probe spécifique (**jamais testé**)

```
Show me the stats for the probe "Google Search" on BR8
```
→ `get_dem_probe_stats` — métriques historiques d'une probe (**jamais testé**)

---

### 1.4 Security (read-only)

```
What security tests are available on BR8?
```
→ `get_security_test_options` — liste des options de test dispo (**jamais testé**)

```
What are the available security test options on BR8 (dynamic)?
```
→ `get_security_test_options_dynamic` — version live depuis l'API (**jamais testé**)

```
Show me the security configuration of BR8
```
→ `get_security_config` — politique de sécurité active (**jamais testé**)

```
Show me the last 20 security results on BR8
```
→ `list_security_results(limit=20)` — plus de résultats

---

### 1.5 Diagnostics

```
Run diagnostics on BR8
```
→ `get_diagnostics` — check curl/DNS/scapy/connectivité (**jamais testé**)

```
What is the app quality score for BR8?
```
→ `get_app_score` — score qualité applicatif (**jamais testé**)

---

### 1.6 VyOS / Scenarios

```
List all VyOS routers managed by Stigix
```
→ `list_vyos_routers` — routeurs VyOS détectés (**jamais testé**)

```
List all available network scenarios for BR8
```
→ `list_vyos_scenarios` — scénarios dispo (WAN failover, QoS...) (**jamais testé**)

```
Show me the timeline of network events on BR8
```
→ `get_vyos_timeline` — historique changements réseau (**jamais testé**)

---

## 🟡 Phase 2 — Tests actifs (lecture avec déclenchement)

> Ces tests déclenchent des actions mais sont **non destructifs** (pas de modification de config).

### 2.1 Security probes

```
Run a URL security test on BR8 for "https://malware.testpanw.com"
```
→ `run_security_probe(agent_id="BR8", test_type="url", target="https://malware.testpanw.com")`

```
Run a DNS security test on BR8 for "test-malware.testpanw.com"
```
→ `run_security_probe(agent_id="BR8", test_type="dns", target="test-malware.testpanw.com")`

```
Run a threat prevention test on BR8 for "https://secure.eicar.org/eicar.com.txt"
```
→ `run_security_probe(agent_id="BR8", test_type="threat", target="https://secure.eicar.org/eicar.com.txt")` (**jamais testé**)

```
Run the full URL batch security test on BR8
```
→ `run_security_url_batch` — batch de ~70 URLs (**jamais testé seul**)

```
Run the full DNS batch security test on BR8
```
→ `run_security_dns_batch` — batch de ~24 domaines DNS (**jamais testé seul**)

```
Run an EICAR test on BR8
```
→ `run_eicar_test` — **à retester avec patch.105**

---

### 2.2 DEM probes

```
Force run all DEM probes on BR8 now
```
→ `run_dem_probes_now` — déclenche toutes les probes immédiatement (**jamais testé**)

---

### 2.3 Tests réseau (XFR / speedtest)

```
Run a speedtest from BR8 to DC1 for 30 seconds
```
→ `run_test(source_id="BR8", target_id="DC1", profile="xfr", duration="30s")` (**jamais testé**)

```
Run a speedtest from BR8 to Hetzner with 200Mbps bitrate
```
→ `run_test(..., bitrate="200M")`

```
Run a convergence test from BR8 to DC1
```
→ `run_test(..., profile="conv")` (**jamais testé**)

```
What is the status of the last test on BR8?
```
→ `get_test_status` (**jamais testé**)

```
Stop the current test on BR8
```
→ `stop_test` (**jamais testé**)

---

## 🟠 Phase 3 — Modifications de configuration

> ⚠️ Ces tests **modifient** la configuration. Teste sur BR8 ou un nœud non-prod.

### 3.1 Traffic generator

```
Stop traffic generation on BR8
```
→ `set_traffic_status(agent_id="BR8", enabled=False)` (**jamais testé**)

```
Start traffic generation on BR8
```
→ `set_traffic_status(agent_id="BR8", enabled=True)` — restaure

```
Set traffic interval on BR8 to 0.5 seconds
```
→ `set_traffic_rate(agent_id="BR8", interval=0.5)` (**jamais testé**)

```
Set traffic client count on BR8 to 2
```
→ `set_traffic_client_count(agent_id="BR8", count=2)` (**jamais testé**)

```
Set traffic client count on BR8 back to 1
```
→ restauration

---

### 3.2 Voice

```
Enable voice simulation on BR8
```
→ `set_voice_status(agent_id="BR8", enabled=True)` (**jamais testé**)

```
Disable voice simulation on BR8
```
→ `set_voice_status(agent_id="BR8", enabled=False)`

---

### 3.3 DEM probes (ajout/suppression)

> ⚠️ Faire sur un nœud de test, vérifier avant/après avec `list_dem_probes`

```
Add a new HTTP probe on BR8 targeting https://stigix.io with name "Stigix Website" every 60 seconds
```
→ `add_dem_probe` (**jamais testé**)

```
Remove the probe named "Stigix Website" from BR8
```
→ `remove_dem_probe` (**jamais testé**)

---

### 3.4 Fabric targets (ajout/suppression)

> ⚠️ Très impactant — modifier la topologie fabric

```
Add a new fabric target on BR8 pointing to 192.168.219.254 named "BR8-GW"
```
→ `add_fabric_target` (**jamais testé**)

```
Disable the fabric target "BR8-GW" on BR8
```
→ `set_fabric_target_enabled(enabled=False)` (**jamais testé**)

```
Remove the fabric target "BR8-GW" from BR8
```
→ `remove_fabric_target` (**jamais testé**)

---

### 3.5 App config (import/export)

```
Export the app config from BR8
```
→ `export_app_config` (backup avant import)

```
Import the app config to DC1 from BR8's config
```
→ `import_app_config` — copie config d'un nœud à l'autre (**jamais testé**)

---

### 3.6 VyOS scenarios

```
Run the scenario "wan-failover" on BR8
```
→ `run_vyos_scenario` (**jamais testé — risqué si VyOS pas configuré**)

```
Disable the scenario "wan-failover" on BR8
```
→ `set_vyos_scenario_status(enabled=False)` (**jamais testé**)

---

## 🔴 Phase 4 — Tests avancés (multi-nœuds)

### 4.1 Comparaisons multi-nœuds

```
Compare all pairs: BR8 vs DC1, BR8 vs Hetzner, DC1 vs Hetzner
```
→ 3x `compare_nodes` — différences de version, health, security

```
Generate a full report for BR8, DC1, and Hetzner only
```
→ `generate_report(agent_ids=["BR8", "DC1", "Hetzner"])`

---

### 4.2 Audit sécurité multi-nœuds

```
Run the full security audit on DC1
```
→ comparer les scores avec BR8

```
Run an EICAR test on Hetzner
```
→ tester sur un autre nœud (patch.105 corrigé)

---

### 4.3 Tests de charge

```
Run a speedtest from BR8 to DC1, and simultaneously from Raspi4 to Hetzner
```
→ 2x `run_test` en parallèle (Claude devrait lancer les 2 outils en parallèle)

---

## 📊 Grille de résultats

*Dernière mise à jour : 30/05/2026 — patch.105*

| # | Tool | Testé ? | Résultat | Notes |
|---|---|---|---|---|
| 1 | `list_endpoints` | ✅ | OK | 10 nœuds, 3 managed / 7 synthesized |
| 2 | `get_node_status` | ✅ | OK | BR8 READY, v1.4.0-patch.105, uptime 26238s |
| 3 | `get_traffic_stats` | ✅ | OK | 11 335 req, 60+ apps |
| 4 | `list_dem_probes` | ✅ | OK | 55 probes |
| 5 | `list_fabric_targets` | ✅ | OK | 10 targets |
| 6 | `list_apps` | ✅ | OK | 17 catégories |
| 7 | `get_traffic_logs` | ✅ | OK | |
| 8 | `get_security_results_stats` | ✅ | OK | 1 470 tests — 436 bloqués / 285 sinkholed |
| 9 | `list_security_results` | ✅ | OK | 20 DNS results — 17 sinkholed / 3 blocked |
| 10 | `get_convergence_history` | ✅ | OK | 7 PERFECT / 2 GOOD (Raspi4 ~5% loss) |
| 11 | `run_eicar_test` | ✅ | fixé | 400 patch.104 → OK patch.105 |
| 12 | `run_full_security_audit` | ✅ | OK | 24/94 bloqués |
| 13 | `get_public_ip` | ✅ | OK | 2.13.195.58 |
| 14 | `compare_nodes` | ✅ | OK | BR8 vs DC1 : patch 105 vs 37, 10 vs 9 peers |
| 15 | `generate_report` | ⬜ | | |
| 16 | `list_speedtest_history` | ✅ | OK | 50 tests — BR8→Hetzner 46.6 Mbps |
| 17 | `export_app_config` | ⬜ | | |
| 18 | `get_dem_summary` | ✅ | ⚠️ | globalHealth=0 — voir Limitations connues |
| 19 | `get_probe_details` | ⬜ | | Claude a utilisé get_dem_probe_stats à la place |
| 20 | `get_dem_probe_stats` | ✅ | OK | 73/100 — 13 HTTP endpoints, avg score 51 |
| 21 | `get_security_test_options` | ✅ | OK | 65 URL + 24 DNS + 7 C2 + 5 AI |
| 22 | `get_security_test_options_dynamic` | ⬜ | | |
| 23 | `get_security_config` | ✅ | OK | Threat Prevention disabled |
| 24 | `get_diagnostics` | ✅ | OK | RAM 33%, disk 51%, voice active (4 calls) |
| 25 | `get_app_score` | ✅ | OK | outlook: 648 req, 0 errors — 100% |
| 26 | `list_vyos_routers` | ⬜ | | |
| 27 | `list_vyos_scenarios` | ⬜ | | |
| 28 | `get_vyos_timeline` | ⬜ | | |
| 29 | `run_security_probe` (url) | ⬜ | | |
| 30 | `run_security_probe` (dns) | ⬜ | | |
| 31 | `run_security_probe` (threat) | ⬜ | | |
| 32 | `run_security_url_batch` | ⬜ | | |
| 33 | `run_security_dns_batch` | ⬜ | | |
| 34 | `run_dem_probes_now` | ⬜ | | |
| 35 | `run_test` (xfr) | ⬜ | | |
| 36 | `run_test` (conv) | ⬜ | | |
| 37 | `get_test_status` | ⬜ | | |
| 38 | `stop_test` | ⬜ | | |
| 39 | `set_traffic_status` | ⬜ | | ⚠️ Modifie config |
| 40 | `set_traffic_rate` | ⬜ | | ⚠️ Modifie config |
| 41 | `set_traffic_client_count` | ⬜ | | ⚠️ Modifie config |
| 42 | `set_voice_status` | ⬜ | | ⚠️ Modifie config |
| 43 | `add_dem_probe` | ⬜ | | ⚠️ Modifie config |
| 44 | `remove_dem_probe` | ⬜ | | ⚠️ Modifie config |
| 45 | `add_fabric_target` | ⬜ | | ⚠️ Modifie config |
| 46 | `remove_fabric_target` | ⬜ | | ⚠️ Modifie config |
| 47 | `set_fabric_target_enabled` | ⬜ | | ⚠️ Modifie config |
| 48 | `import_app_config` | ⬜ | | ⚠️ Écrase config |
| — | `run_vyos_scenario` | ⬜ | | 🔴 Risqué |
| — | `set_vyos_scenario_status` | ⬜ | | 🔴 Risqué |

---

## ⚠️ Limitations connues & comportements attendus

| Tool | Comportement | Explication |
|---|---|---|
| `get_dem_summary` | `globalHealth: 0` malgré probes actives | Cache `/api/admin/system/dashboard-data` pas encore agrégé. Utiliser `get_dem_probe_stats` pour le score live. |
| `run_eicar_test` | 400 sur patch.104 | Corrigé patch.105 — payload `endpoints[]` → `endpoint` (string) |
| Adressage nœuds | `BR8` vs `BR8-Ubuntu` | Utiliser le nom exact enregistré dans le registry (`BR8-Ubuntu`, pas `BR8`). |
| `get_probe_details` | Claude préfère `get_dem_probe_stats` | `get_probe_details` cherche dans `lastResults` — échoue si la probe n'a pas de résultat récent. |
| Threat Prevention | `enabled: false` par défaut | Aucun endpoint EICAR configuré localement. `run_eicar_test` fonctionne via le cloud Stigix. |
