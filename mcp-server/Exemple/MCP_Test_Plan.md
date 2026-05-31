# 🧪 Stigix MCP — Plan de Validation Complet

> **Version** : v1.4.0-patch.128+  
> **Objectif** : Valider l'ensemble des 52+ tools MCP via Claude Desktop en conditions réelles.  
> **Format de notation** : ✅ Succès | ❌ Erreur | ⚠️ Réponse partielle

---

## 📖 Comment utiliser ce document

Copiez-collez chaque question exactement dans Claude Desktop.  
Après chaque réponse, notez ✅ (succès), ❌ (erreur), ou ⚠️ (réponse partielle).  
Pour le troubleshooting : demandez à Claude de dumper la requête et la réponse brute du tool MCP.

---

## 🛠️ Commande de Debug Universelle

Avant de commencer, si un tool échoue, posez cette question à Claude :

```
Peux-tu me montrer exactement quelle requête MCP tu as envoyé et quelle réponse brute tu as reçue ?
```

---

## SECTION 1 — Discovery & Inventaire (Base)

**Objectif** : Vérifier que Claude peut lister les endpoints disponibles. C'est le prérequis à tout.

### Test 1.1 — Lister tous les endpoints

```
Montre-moi tous les endpoints Stigix disponibles.
```

- **Tool attendu** : `list_endpoints()`
- **Résultat attendu** : Liste de nœuds fabric et/ou targets internet avec leurs IDs.
- **À noter** : Les IDs retournés sont ceux à utiliser dans tous les tests suivants.

---

### Test 1.2 — Filtrer par type Fabric

```
Liste uniquement les nœuds Fabric Stigix.
```

- **Tool attendu** : `list_endpoints(kind="fabric")`
- **Résultat attendu** : Sous-ensemble de la liste précédente avec uniquement les nœuds internes.

---

### Test 1.3 — Filtrer par type Internet

```
Liste uniquement les targets Internet Stigix.
```

- **Tool attendu** : `list_endpoints(kind="internet")`
- **Résultat attendu** : Sous-ensemble avec les cibles externes.

---

### Test 1.4 — Rapport global de la Fabric

```
Génère un rapport complet sur tous les nœuds Stigix de la fabric.
```

- **Tool attendu** : `generate_report()`
- **Résultat attendu** : Vue synthétique de tous les nœuds (health, version, traffic, DEM, sécurité, peers).

---

## SECTION 2 — Node Status (Diagnostics par Nœud)

**Objectif** : Valider les tools de status et diagnostic. Remplacer `<NODE_ID>` par un ID réel obtenu en Section 1.

### Test 2.1 — Status complet d'un nœud

```
Donne-moi le statut complet du nœud <NODE_ID>.
```

- **Tool attendu** : `get_node_status(agent_id="<NODE_ID>")`
- **Résultat attendu** : Health, version, traffic status, site info, état convergence.

---

### Test 2.2 — Dashboard complet de diagnostics

```
Montre-moi le dashboard de diagnostics complet du nœud <NODE_ID>.
```

- **Tool attendu** : `get_diagnostics(agent_id="<NODE_ID>")`
- **Résultat attendu** : CPU, bitrate, stats apps, voix, peers.

---

### Test 2.3 — IP publique / chemin WAN

```
Quelle est l'IP publique du nœud <NODE_ID> ? Par quelle route sort-il sur Internet ?
```

- **Tool attendu** : `get_public_ip(agent_id="<NODE_ID>")`
- **Résultat attendu** : IP WAN du nœud.

---

### Test 2.4 — Comparaison de deux nœuds

```
Compare les nœuds <NODE_ID_A> et <NODE_ID_B> côte-à-côte.
```

- **Tool attendu** : `compare_nodes(agent_id_a="<NODE_ID_A>", agent_id_b="<NODE_ID_B>")`
- **Résultat attendu** : Tableau comparatif health/version/traffic/DEM/security.

---

## SECTION 3 — Traffic Generation

**Objectif** : Valider les tools de contrôle du trafic applicatif.

### Test 3.1 — Stats de trafic live

```
Montre-moi les statistiques de génération de trafic en direct sur <NODE_ID>.
```

- **Tool attendu** : `get_traffic_stats(agent_id="<NODE_ID>")`
- **Résultat attendu** : Requêtes par app, taux d'erreur, clients actifs.

---

### Test 3.2 — Applications simulées

```
Quelles applications sont simulées sur le nœud <NODE_ID> ?
```

- **Tool attendu** : `list_apps(agent_id="<NODE_ID>")`
- **Résultat attendu** : Liste Teams, Zoom, Salesforce, etc.

---

### Test 3.3 — Score d'une application spécifique

```
Quel est le taux de succès de Teams sur le nœud <NODE_ID> ?
```

- **Tool attendu** : `get_app_score(agent_id="<NODE_ID>", app_name="teams")`
- **Résultat attendu** : Taux de succès %, status Healthy/Degraded/Critical.

---

### Test 3.4 — Logs de trafic

```
Montre-moi les 20 derniers logs de trafic du nœud <NODE_ID>.
```

- **Tool attendu** : `get_traffic_logs(agent_id="<NODE_ID>", limit=20)`
- **Résultat attendu** : Entrées de log récentes.

---

### Test 3.5 — Démarrer le trafic

```
Démarre la génération de trafic applicatif sur le nœud <NODE_ID>.
```

- **Tool attendu** : `set_traffic_status(source_id="<NODE_ID>", enabled=True)`
- **Résultat attendu** : Confirmation de démarrage.
- ⚠️ **Vérification** : Refaire le Test 3.1 pour confirmer que le trafic tourne.

---

### Test 3.6 — Ajuster la vitesse du trafic

```
Règle la vitesse de trafic sur le nœud <NODE_ID> à 0.5 secondes entre les requêtes.
```

- **Tool attendu** : `set_traffic_rate(agent_id="<NODE_ID>", rate=0.5)`
- **Résultat attendu** : Confirmation du changement.

---

### Test 3.7 — Augmenter le nombre de clients simulés

```
Passe le nœud <NODE_ID> à 5 clients parallèles.
```

- **Tool attendu** : `set_traffic_client_count(agent_id="<NODE_ID>", client_count=5)`
- **Résultat attendu** : Confirmation.

---

### Test 3.8 — Arrêter le trafic

```
Stoppe la génération de trafic applicatif sur le nœud <NODE_ID>.
```

- **Tool attendu** : `set_traffic_status(source_id="<NODE_ID>", enabled=False)`
- **Résultat attendu** : Confirmation d'arrêt.

---

### Test 3.9 — Export de config applicative

```
Exporte la configuration des applications du nœud <NODE_ID>.
```

- **Tool attendu** : `export_app_config(agent_id="<NODE_ID>")`
- **Résultat attendu** : Objet JSON de configuration.

---

## SECTION 4 — Digital Experience Monitoring (DEM)

**Objectif** : Valider tous les tools DEM/probes de connectivité.

### Test 4.1 — Résumé DEM global

```
Donne-moi le résumé DEM du nœud <NODE_ID>.
```

- **Tool attendu** : `get_dem_summary(agent_id="<NODE_ID>")`
- **Résultat attendu** : Score de santé global, statuts des probes individuels.

---

### Test 4.2 — Liste des probes DEM

```
Liste toutes les probes DEM configurées sur le nœud <NODE_ID>.
```

- **Tool attendu** : `list_dem_probes(agent_id="<NODE_ID>")`
- **Résultat attendu** : Nom, type (HTTP/PING/DNS/TCP/UDP), target, statut enabled.

---

### Test 4.3 — Stats historiques des probes

```
Montre-moi les statistiques historiques des probes DEM de <NODE_ID> sur la dernière heure.
```

- **Tool attendu** : `get_dem_probe_stats(agent_id="<NODE_ID>")`
- **Résultat attendu** : Score global, latence moyenne, fiabilité par probe.

---

### Test 4.4 — Détails d'une probe spécifique

```
Donne-moi les détails de performance de la probe "Google DNS" sur <NODE_ID>.
```

- **Tool attendu** : `get_probe_details(agent_id="<NODE_ID>", probe_name="Google DNS")`
- **Résultat attendu** : Score, latence totale, reachability.

---

### Test 4.5 — Déclencher les probes maintenant

```
Lance une exécution immédiate de toutes les probes DEM sur <NODE_ID>.
```

- **Tool attendu** : `run_dem_probes_now(agent_id="<NODE_ID>")`
- **Résultat attendu** : RTT, status, reachability pour chaque probe.
- ⚠️ **Note** : Peut prendre 30-60 secondes.

---

### Test 4.6 — Ajouter une nouvelle probe

```
Ajoute une probe PING vers 8.8.8.8 nommée "Google DNS Test" sur le nœud <NODE_ID>.
```

- **Tool attendu** : `add_dem_probe(agent_id="<NODE_ID>", name="Google DNS Test", target="8.8.8.8", probe_type="PING")`
- **Résultat attendu** : Confirmation d'ajout.
- ⚠️ **Vérification** : Refaire Test 4.2 pour confirmer que la probe apparaît.

---

### Test 4.7 — Supprimer une probe

```
Supprime la probe "Google DNS Test" du nœud <NODE_ID>.
```

- **Tool attendu** : `remove_dem_probe(agent_id="<NODE_ID>", probe_name="Google DNS Test")`
- **Résultat attendu** : Confirmation de suppression.
- ⚠️ **Vérification** : Refaire Test 4.2 pour confirmer la suppression.

---

## SECTION 5 — Fabric Targets (Peers)

**Objectif** : Valider la gestion des peers Fabric.

### Test 5.1 — Lister les fabric targets

```
Liste tous les peers Fabric configurés sur le nœud <NODE_ID>.
```

- **Tool attendu** : `list_fabric_targets(agent_id="<NODE_ID>")`
- **Résultat attendu** : Nom, host, capacités (xfr, voice, conv, security), statut enabled.

---

### Test 5.2 — Désactiver un fabric target

```
Désactive le fabric target "<TARGET_NAME>" sur le nœud <NODE_ID>.
```

- **Tool attendu** : `set_fabric_target_enabled(agent_id="<NODE_ID>", target_name_or_host="<TARGET_NAME>", enabled=False)`
- **Résultat attendu** : Confirmation.

---

### Test 5.3 — Réactiver un fabric target

```
Réactive le fabric target "<TARGET_NAME>" sur le nœud <NODE_ID>.
```

- **Tool attendu** : `set_fabric_target_enabled(agent_id="<NODE_ID>", target_name_or_host="<TARGET_NAME>", enabled=True)`
- **Résultat attendu** : Confirmation.

---

## SECTION 6 — Tests de Trafic (XFR / Speedtest / Convergence)

**Objectif** : Valider le lancement et le suivi des tests de performance.

### Test 6.1 — Historique speedtest

```
Montre-moi les 10 derniers speedtests du nœud <NODE_ID>.
```

- **Tool attendu** : `list_speedtest_history(agent_id="<NODE_ID>", limit=10)`
- **Résultat attendu** : Résultats historiques avec target, protocole, débit Mbps, RTT.

---

### Test 6.2 — Lancer un speedtest XFR simple

```
Lance un speedtest de 30 secondes entre <SOURCE_ID> et <TARGET_ID> en TCP.
```

- **Tool attendu** : `run_test(source_id="<SOURCE_ID>", target_id="<TARGET_ID>", profile="xfr", duration="30s", protocol="tcp")`
- **Résultat attendu** : Test ID et statut initial.

---

### Test 6.3 — Vérifier le statut d'un test

```
Donne-moi le statut du test <TEST_ID>.
```

- **Tool attendu** : `get_test_status(test_id="<TEST_ID>")`
- **Résultat attendu** : Status (running/completed/error), métriques.

---

### Test 6.4 — Speedtest avec débit limité

```
Lance un speedtest entre <SOURCE_ID> et <TARGET_ID> avec une limite à 100M bidirectionnel.
```

- **Tool attendu** : `run_test(source_id="<SOURCE_ID>", target_id="<TARGET_ID>", profile="xfr", bitrate="100M", direction="bidirectional")`
- **Résultat attendu** : Lancement du test.

---

### Test 6.5 — Stopper un test en cours

```
Arrête le test <TEST_ID>.
```

- **Tool attendu** : `stop_test(test_id="<TEST_ID>")`
- **Résultat attendu** : Confirmation d'arrêt + métriques finales.

---

### Test 6.6 — Test de convergence CONV

```
Lance un test de convergence entre <SOURCE_ID> et <TARGET_ID> avec 100 pps.
```

- **Tool attendu** : `run_test(source_id="<SOURCE_ID>", target_id="<TARGET_ID>", profile="conv", pps=100)`
- **Résultat attendu** : Test ID convergence + Claude annonce l'ID et **attend que l'utilisateur dise "stop"**.
- ⚠️ **Comportement attendu** : Claude NE doit PAS poller ni appeler `get_test_status` automatiquement.

---

### Test 6.7 — Historique de convergence

```
Montre-moi les 5 derniers tests de convergence du nœud <NODE_ID>.
```

- **Tool attendu** : `get_convergence_history(agent_id="<NODE_ID>", limit=5)`
- **Résultat attendu** : Résultats avec max blackout, verdict (PERFECT/GOOD/DEGRADED/BAD/CRITICAL).

---

## SECTION 7 — Sécurité

**Objectif** : Valider tous les tools de security testing.

### Test 7.1 — Config sécurité d'un nœud

```
Montre-moi la configuration de sécurité du nœud <NODE_ID>.
```

- **Tool attendu** : `get_security_config(agent_id="<NODE_ID>")`
- **Résultat attendu** : Modules activés, profil de test (DNS, URL, threat).

---

### Test 7.2 — Scorecard de sécurité (posture)

```
Quel est le score de sécurité actuel du nœud <NODE_ID> ?
```

- **Tool attendu** : `get_security_results_stats(agent_id="<NODE_ID>")`
- **Résultat attendu** : `posture_scores` (url_filter, dns_security, threat_prevention 0-100) + trend 24h.

---

### Test 7.3 — Derniers résultats de tests sécurité

```
Montre-moi les 10 derniers résultats de tests de sécurité du nœud <NODE_ID>.
```

- **Tool attendu** : `list_security_results(agent_id="<NODE_ID>", limit=10)`
- **Résultat attendu** : Résultats URL/DNS/Threat chronologiques.

---

### Test 7.4 — Options de test DNS (live du nœud)

```
Quels sont les targets DNS security disponibles sur le nœud <NODE_ID> ?
```

- **Tool attendu** : `get_security_test_options(agent_id="<NODE_ID>", probe_type="dns")`
- **Résultat attendu** : Liste des domaines de test configurés (malware, phishing, c2, etc.) issus du profil réel du nœud.
- ℹ️ **Note** : `get_security_test_options` est maintenant **dynamique** et requiert `agent_id`. Il remplace l'ancien outil statique.

---

### Test 7.5 — Options de test URL (live du nœud)

```
Quelles sont les catégories URL configurées sur le nœud <NODE_ID> ?
```

- **Tool attendu** : `get_security_test_options(agent_id="<NODE_ID>", probe_type="url")`
- **Résultat attendu** : Liste des catégories URL du profil réel du nœud (pas les URLs Palo Alto hardcodées).

---

### Test 7.6 — Options EICAR disponibles

```
Quelles sont les cibles EICAR disponibles sur le nœud <NODE_ID> ?
```

- **Tool attendu** : `get_security_test_options(agent_id="<NODE_ID>", probe_type="threat")`
- **Résultat attendu** : Liste des targets EICAR : fabric targets avec `capabilities.security=true` + cloud si configuré. Avec noms lisibles (ex: "Hetzner", "DC1").

---

### Test 7.7 — Test DNS individuel

```
Lance un test DNS security avec le domaine de malware sur le nœud <NODE_ID>.
```

**Workflow Claude attendu** :
1. `get_security_test_options(agent_id="<NODE_ID>", probe_type="dns")` → récupère les targets réels
2. `run_security_probe(agent_id="<NODE_ID>", probe_type="dns", target="<domain-malware-du-profil>")` → lance le test

- **Résultat attendu** : Blocked/Allowed + raison. Badge **MCP** visible dans le Security Log.

---

### Test 7.8 — Test URL filtering individuel

```
Teste le filtrage URL de la catégorie "Hacking" sur le nœud <NODE_ID>.
```

**Workflow Claude attendu** :
1. `get_security_test_options(agent_id="<NODE_ID>", probe_type="url")` → récupère l'URL exacte de la catégorie
2. `run_security_probe(agent_id="<NODE_ID>", probe_type="url", target="<url-du-profil>")` → teste

- **Résultat attendu** : Blocked/Allowed. Badge **MCP** visible dans le Security Log.

---

### Test 7.9 — Test EICAR vers une target spécifique

```
Lance un test EICAR de prévention des menaces vers la target Hetzner depuis le nœud <NODE_ID>.
```

**Workflow Claude attendu** :
1. `get_security_test_options(agent_id="<NODE_ID>", probe_type="threat")` → voit la liste (Hetzner, DC1, Cloud...)
2. Sélectionne la target "Hetzner"
3. `run_security_probe(agent_id="<NODE_ID>", probe_type="threat", target="http://<ip-hetzner>:8082/eicar.com.txt")`

- **Résultat attendu** : Blocked 🟢 (IPS actif) ou Allowed 🔴 (problème). Badge **MCP** visible.

---

### Test 7.10 — Batch DNS complet

```
Lance un audit DNS security complet sur le nœud <NODE_ID>.
```

- **Tool attendu** : `run_security_dns_batch(agent_id="<NODE_ID>")`
- **Résultat attendu** : Résumé (blocked/allowed/unknown) par domaine.
- ⚠️ **Note** : Peut prendre 3 minutes.

---

### Test 7.11 — Batch URL complet

```
Lance un audit URL filtering complet sur le nœud <NODE_ID>.
```

- **Tool attendu** : `run_security_url_batch(agent_id="<NODE_ID>")`
- **Résultat attendu** : Résumé par catégorie URL.
- ⚠️ **Note** : Peut prendre 3 minutes.

---

### Test 7.12 — Audit sécurité complet (les 3 phases)

```
Lance un audit de sécurité complet sur le nœud <NODE_ID> — URL, DNS, et EICAR.
```

- **Tool attendu** : `run_full_security_audit(agent_id="<NODE_ID>")`
- **Résultat attendu** : Résultats des 3 phases + résumé global.
- ⚠️ **Note** : Peut prendre 7-10 minutes.

---

## SECTION 8 — VyOS Network Chaos

**Objectif** : Valider les tools de manipulation réseau VyOS.  
⚠️ **Section délicate** — bien confirmer les actions avant exécution.

### Test 8.1 — Lister les routeurs VyOS

```
Liste les routeurs VyOS gérés par le nœud <NODE_ID>.
```

- **Tool attendu** : `list_vyos_routers(agent_id="<NODE_ID>")`
- **Résultat attendu** : Liste des routeurs avec leurs IDs.

---

### Test 8.2 — Lister les scénarios disponibles

```
Quels scénarios VyOS sont disponibles sur le nœud <NODE_ID> ?
```

- **Tool attendu** : `list_vyos_scenarios(agent_id="<NODE_ID>")`
- **Résultat attendu** : Liste des séquences (failover, etc.).

---

### Test 8.3 — Lister les interfaces chaos-eligible

```
Montre-moi les interfaces réseau disponibles pour le chaos engineering sur le nœud <NODE_ID>.
```

- **Tool attendu** : `get_vyos_interfaces(agent_id="<NODE_ID>")`
- **Résultat attendu** : Interfaces avec description, IP, statut up/down. Seulement les interfaces avec description sont retournées.

---

### Test 8.4 — État live d'un routeur VyOS

```
Quel est l'état actuel du routeur <ROUTER_ID> géré par le nœud <NODE_ID> ?
```

- **Tool attendu** : `get_vyos_router_state(agent_id="<NODE_ID>", router_id="<ROUTER_ID>")`
- **Résultat attendu** : Interfaces (up/down), QoS active, blocs IP actifs.

---

### Test 8.5 — Historique des changements VyOS

```
Montre-moi les 10 derniers changements VyOS effectués via le nœud <NODE_ID>.
```

- **Tool attendu** : `get_vyos_timeline(agent_id="<NODE_ID>", limit=10)`
- **Résultat attendu** : Historique des actions.

---

### Test 8.6 — Ajouter de la latence (flux NL → confirmation)

```
Ajoute 100ms de latence sur le lien MPLS de BR1 via le nœud <NODE_ID>.
```

**Workflow attendu de Claude** :
1. `get_vyos_interfaces(agent_id="<NODE_ID>")` → trouve l'interface MPLS de BR1
2. Présente : "J'ai trouvé eth1 (BR1-MPLS-197) sur vyosrouter. Voulez-vous appliquer 100ms ? (oui/non)"
3. Sur confirmation → `vyos_execute_action(agent_id, router_id, "set-impairment", interface="eth1", latency_ms=100)`

- ⚠️ **IMPORTANT** : Claude NE doit PAS appliquer l'action sans confirmation explicite.

---

### Test 8.7 — Ajouter perte de paquets

```
Ajoute 5% de perte de paquets sur l'interface WAN du routeur <ROUTER_ID> sur <NODE_ID>.
```

- **Workflow attendu** : Même flow NL → identification → confirmation → `set-impairment` avec `loss_pct=5`.

---

### Test 8.8 — Effacer le QoS sur une interface

```
Supprime le QoS sur eth1 du routeur <ROUTER_ID> géré par <NODE_ID>.
```

- **Tool attendu** : `vyos_execute_action(agent_id, router_id, "clear-qos", interface="eth1")`

---

### Test 8.9 — Reset global QoS

```
Efface tout le QoS actif sur le routeur <ROUTER_ID> géré par <NODE_ID>.
```

- **Tool attendu** : `vyos_bulk_reset(agent_id="<NODE_ID>", router_id="<ROUTER_ID>", scope="all-qos")`
- **Résultat attendu** : Liste des actions exécutées.

---

### Test 8.10 — Reset complet (full-reset)

```
Fais un reset complet du routeur <ROUTER_ID> — QoS, IP blocks, et interfaces down.
```

- **Tool attendu** : `vyos_bulk_reset(agent_id="<NODE_ID>", router_id="<ROUTER_ID>", scope="full-reset")`

---

### Test 8.11 — Bloquer une IP

```
Bloque le trafic vers 1.2.3.4 sur le routeur <ROUTER_ID> géré par <NODE_ID>.
```

- **Tool attendu** : `vyos_execute_action(agent_id, router_id, "deny-traffic", ip="1.2.3.4")`
- ⚠️ **IMPORTANT** : Claude doit demander confirmation avant d'exécuter.

---

### Test 8.12 — Débloquer une IP

```
Débloque le trafic vers 1.2.3.4 sur le routeur <ROUTER_ID> géré par <NODE_ID>.
```

- **Tool attendu** : `vyos_execute_action(agent_id, router_id, "allow-traffic", ip="1.2.3.4")`

---

### Test 8.13 — Exécuter un scénario VyOS

```
Lance le scénario "<SCENARIO_ID>" sur le nœud <NODE_ID>.
```

- **Tool attendu** : `run_vyos_scenario(agent_id="<NODE_ID>", scenario_id="<SCENARIO_ID>")`

---

### Test 8.14 — Activer/Désactiver un scénario cyclic

```
Désactive le scénario "<SCENARIO_ID>" qui tourne en boucle sur <NODE_ID>.
```

- **Tool attendu** : `set_vyos_scenario_status(agent_id="<NODE_ID>", scenario_id="<SCENARIO_ID>", enabled=False)`

---

## SECTION 9 — Voice Simulation

### Test 9.1 — Démarrer la simulation voix

```
Démarre la simulation voix sur le nœud <NODE_ID>.
```

- **Tool attendu** : `set_voice_status(source_id="<NODE_ID>", enabled=True)`
- **Résultat attendu** : Confirmation.
- ⚠️ **Note** : Le nœud doit être de type fabric.

---

### Test 9.2 — Arrêter la simulation voix

```
Arrête la simulation voix sur le nœud <NODE_ID>.
```

- **Tool attendu** : `set_voice_status(source_id="<NODE_ID>", enabled=False)`

---

## SECTION 10 — Tests Avancés & Edge Cases

### Test 10.1 — Node ID inexistant (test d'erreur)

```
Donne-moi le statut du nœud "NODE-QUI-NEXISTE-PAS".
```

- **Résultat attendu** : Erreur propre de Claude (pas un crash), message clair que le nœud n'existe pas.

---

### Test 10.2 — Résolution NL de site VyOS ambigu

```
Ajoute 200ms de latence sur le lien Internet de BR2 via <NODE_ID>.
```

**Workflow attendu de Claude** :
1. Appelle `get_vyos_interfaces`
2. Trouve PLUSIEURS liens Internet sur BR2 (ou ambiguïté)
3. Liste les candidats et demande à l'utilisateur de choisir
4. N'exécute PAS sans choix explicite

---

### Test 10.3 — Import de configuration applicative

```
Copie la configuration d'applications du nœud <NODE_ID_SOURCE> vers <NODE_ID_DEST>.
```

**Workflow attendu de Claude** :
1. `export_app_config(agent_id="<NODE_ID_SOURCE>")` → récupère la config JSON
2. Avertit que l'import écrase la config existante
3. Sur confirmation → `import_app_config(agent_id="<NODE_ID_DEST>", config=<JSON>)`

---

## 📊 Tableau de Suivi des Résultats

| # | Tool | Status | Note |
|---|------|--------|------|
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
| 6.6 | `run_test(conv)` — start/stop | ⬜ | Claude doit attendre "stop" |
| 6.7 | `get_convergence_history` | ⬜ | |
| 7.1 | `get_security_config` | ⬜ | |
| 7.2 | `get_security_results_stats` | ⬜ | |
| 7.3 | `list_security_results` | ⬜ | |
| 7.4 | `get_security_test_options(agent_id, dns)` | ⬜ | Dynamique — requiert agent_id |
| 7.5 | `get_security_test_options(agent_id, url)` | ⬜ | Dynamique — requiert agent_id |
| 7.6 | `get_security_test_options(agent_id, threat)` | ⬜ | Retourne targets fabric.security |
| 7.7 | `run_security_probe(dns)` + badge MCP | ⬜ | |
| 7.8 | `run_security_probe(url)` + badge MCP | ⬜ | |
| 7.9 | `run_security_probe(threat/eicar)` + badge MCP | ⬜ | |
| 7.10 | `run_security_dns_batch` | ⬜ | |
| 7.11 | `run_security_url_batch` | ⬜ | |
| 7.12 | `run_full_security_audit` | ⬜ | |
| 8.1 | `list_vyos_routers` | ⬜ | |
| 8.2 | `list_vyos_scenarios` | ⬜ | |
| 8.3 | `get_vyos_interfaces` | ⬜ | |
| 8.4 | `get_vyos_router_state` | ⬜ | |
| 8.5 | `get_vyos_timeline` | ⬜ | |
| 8.6 | `vyos_execute_action(set-impairment+latency)` | ⬜ | Confirmation obligatoire |
| 8.7 | `vyos_execute_action(set-impairment+loss)` | ⬜ | Confirmation obligatoire |
| 8.8 | `vyos_execute_action(clear-qos)` | ⬜ | |
| 8.9 | `vyos_bulk_reset(all-qos)` | ⬜ | |
| 8.10 | `vyos_bulk_reset(full-reset)` | ⬜ | |
| 8.11 | `vyos_execute_action(deny-traffic)` | ⬜ | Confirmation obligatoire |
| 8.12 | `vyos_execute_action(allow-traffic)` | ⬜ | |
| 8.13 | `run_vyos_scenario` | ⬜ | |
| 8.14 | `set_vyos_scenario_status` | ⬜ | |
| 9.1 | `set_voice_status(start)` | ⬜ | |
| 9.2 | `set_voice_status(stop)` | ⬜ | |
| 10.1 | Erreur node inexistant | ⬜ | |
| 10.2 | Ambiguïté VyOS NL | ⬜ | |
| 10.3 | `export_app_config` | ⬜ | |
| 10.4 | `import_app_config` | ⬜ | |
| 11.1 | `clone_node_config` (all scope) | ⬜ | |
| 11.2 | `clone_node_config` (scope partiel) | ⬜ | |
| 11.3 | `clone_node_config` (JWT mismatch) | ⬜ | Doit retourner error par composant |

---

## 📦 SECTION 11 — Clone Node Config (Multi-Déploiement)

**Objectif** : Valider le tool `clone_node_config` qui clone apps, probes DEM, security profile et VyOS scenarios d'un nœud source vers un nœud cible.

> ⚠️ Prérequis : JWT_SECRET identique sur les deux nœuds. Vérifier avec `docker exec stigix printenv JWT_SECRET` sur chaque nœud.

### Test 11.1 — Clone complet BR8 → BR5

```
Clone toute la configuration de BR8 vers BR5 : apps, probes DEM, security profile et scenarios VyOS.
```

- **Tool attendu** : `clone_node_config(source_id='<BR8_ID>', target_id='<BR5_ID>')`
- **Résultat attendu** : Rapport par composant avec `status: ok` pour chaque item.
- **Vérification** : Ouvrir l'UI de BR5 et vérifier que les apps / probes DEM correspondent à celles de BR8.

---

### Test 11.2 — Clone partiel (DEM probes uniquement)

```
Clone uniquement les probes DEM de BR8 vers BR5, sans toucher aux apps ni au security profile.
```

- **Tool attendu** : `clone_node_config(source_id='<BR8_ID>', target_id='<BR5_ID>', scope=['dem_probes'])`
- **Résultat attendu** : `components.dem_probes.status: ok`, les autres composants absents du rapport.

---

### Test 11.3 — Clone security profile uniquement

```
Copie le security profile de BR8 vers BR5.
```

- **Tool attendu** : `clone_node_config(..., scope=['security_profile'])`
- **Résultat attendu** : `components.security_profile.status: ok` avec `vendor`, `url_categories`, `dns_domains`.

---

### Test 11.4 — Clone avec nœud cible invalide

```
Clone la configuration de BR8 vers un nœud qui n'existe pas : "BR999".
```

- **Tool attendu** : `clone_node_config(source_id='<BR8_ID>', target_id='BR999')`
- **Résultat attendu** : `{"error": "Target node 'BR999' not found."}`

---

## 🔍 Questions de Debug Clé

Si un tool retourne une erreur, posez ces questions à Claude :

1. "Montre-moi la réponse brute JSON que tu as reçue du tool MCP."
2. "Quel était le paramètre exact que tu as passé au tool ?"
3. "Est-ce que le tool a retourné un champ `error` ou une exception Python ?"
4. "Peux-tu réessayer avec l'ID exact `<NODE_ID>` tel que retourné par `list_endpoints` ?"
5. "Y a-t-il un message dans les logs du container MCP ? (`docker logs stigix-mcp-server --tail 50`)"
6. "Est-ce que le JWT_SECRET est le même sur les deux nœuds ? (`docker exec stigix printenv JWT_SECRET`)"
