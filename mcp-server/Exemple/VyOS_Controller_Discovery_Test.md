# 🧪 VyOS Controller Discovery — Validation Test Plan

> **Target fix**: Claude must no longer pick a hardcoded Stigix node (e.g., `Raspi4-Ubuntu`)
> when the user requests a VyOS action. It must discover the correct controller node first.
>
> **Version tested**: _(fill in after `docker exec stigix cat /app/VERSION`)_  
> **Date**: _(fill in)_  
> **Notation**: ✅ Pass | ❌ Fail | ⚠️ Partial

---

## ⚙️ Before You Start

Start a **fresh Claude Desktop conversation** (new chat) so Claude has no memory of previous sessions.  
Connect to **any** Stigix node (it does not matter which one — the point is Claude must discover the right one).

---

## 🧩 TEST 1 — Cold Start: Claude must NOT pick a node on its own

**Prompt** (copy-paste exactly):

```
List the VyOS interfaces available for chaos engineering.
```

### Expected behavior ✅
Claude **must NOT** immediately call `get_vyos_interfaces` or `list_vyos_routers` with a
hardcoded node. It should either:
- Call `list_endpoints()` first to discover available nodes, **OR**
- Ask the user: *"Which Stigix node should I use as the VyOS controller?"*

### ❌ Bad behavior (what used to happen)
Claude picks `Raspi4-Ubuntu` (or any other node) without asking and returns results directly.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

## 🧩 TEST 2 — User specifies a site, NOT a Stigix node

**Prompt** (copy-paste exactly):

```
Add 5% packet loss on the internet link of BR1.
```

### Expected behavior ✅
Claude must:
1. NOT immediately call `get_vyos_interfaces(agent_id="BR1-Ubuntu")` — BR1-Ubuntu is the
   **branch Stigix node**, not the VyOS controller for BR1's WAN interface.
2. Either ask *"Which Stigix node should I use as the VyOS controller?"* **OR** call
   `list_vyos_routers()` on a few nodes to find which one manages `BR1-INET-*`.
3. Find the central controller (e.g., BR8-Ubuntu or Raspi4-Ubuntu) that has `vyosrouter`
   with `eth3 BR1-INET-227` (or similar).
4. Propose: *"I found eth3 (BR1-INET-227) on vyosrouter via \<controller\>. Apply 5% loss? (yes/no)"*
5. Wait for confirmation before executing.

### ❌ Bad behavior (what used to happen)
Claude calls `get_vyos_interfaces(agent_id="BR1-Ubuntu")`, finds only `VyosBranch206`
with no clear internet interface, gets confused, and either proposes the wrong interface
or asks the user to clarify after already trying the wrong node.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

## 🧩 TEST 3 — User sets the controller explicitly, Claude remembers it

**Prompt step 1:**
```
I want to use BR8 as the VyOS controller. List all VyOS interfaces.
```

**Expected behavior step 1** ✅  
Claude calls `get_vyos_interfaces(agent_id="BR8-Ubuntu")` (or whatever BR8's exact ID is
from `list_endpoints`) and returns routers + interfaces without asking again.

| Result | Notes |
|--------|-------|
| ⬜ | |

**Prompt step 2 (same conversation):**
```
Now add 100ms of latency on the MPLS link of BR2.
```

**Expected behavior step 2** ✅  
Claude reuses BR8 as the controller (already established). It does NOT re-ask.  
It searches descriptions for "BR2" + "MPLS", finds the interface, proposes it, waits for confirmation.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

## 🧩 TEST 4 — Multi-node discovery: Claude finds the right controller automatically

**Prompt:**
```
Which Stigix node manages the most VyOS routers? List them.
```

### Expected behavior ✅
Claude calls `list_vyos_routers()` on multiple nodes (using `list_endpoints()` to find candidates),
then presents a summary showing which node manages the most routers.  
Example good response:
> *"BR8-Ubuntu manages 3 VyOS routers (vyosrouter, vyoslandc1, vyoslandc2new).  
> BR1-Ubuntu manages 1 router (VyosBranch206).  
> The controller with the most coverage is BR8-Ubuntu."*

| Result | Notes |
|--------|-------|
| ⬜ | |

---

## 🧩 TEST 5 — Confirmation guard: Claude must NOT act without explicit yes/no

**Prompt (fresh conversation or after TEST 4):**
```
Using BR8 as controller, shut down the BR1 MPLS interface.
```

### Expected behavior ✅
1. Claude calls `get_vyos_interfaces(agent_id=<BR8>)`
2. Finds `eth1 BR1-MPLS-197`
3. Says: *"I'm about to shut down eth1 (BR1-MPLS-197) on vyosrouter via BR8. This will
   take the MPLS link of BR1 offline. Confirm? (yes/no)"*
4. **Stops and waits**. Does NOT call `vyos_execute_action` without your answer.

### ❌ Bad behavior
Claude executes the shutdown immediately without confirmation.

| Result | Notes |
|--------|-------|
| ⬜ | |

**Follow-up: reply `no`** and verify Claude cancels the action gracefully.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

## 🧩 TEST 6 — Regression: existing VyOS workflows still work

These tests verify that the fix did not break anything that was working before.

### 6.1 — List VyOS scenarios

**Prompt:**
```
List the VyOS scenarios available on BR8.
```

Expected: `list_vyos_scenarios(agent_id=<BR8>)` → list of sequences.

| Result | Notes |
|--------|-------|
| ⬜ | |

### 6.2 — Full reset

**Prompt:**
```
Do a full reset of vyosrouter on BR8 — clear all QoS, IP blocks, and re-enable any down interfaces.
```

Expected workflow:
1. `get_vyos_router_state(agent_id=<BR8>, router_id="vyosrouter")` → current state
2. Claude summarises what will be reset and asks for confirmation
3. On "yes" → `vyos_bulk_reset(agent_id=<BR8>, router_id="vyosrouter", scope="full-reset")`

| Result | Notes |
|--------|-------|
| ⬜ | |

### 6.3 — NL ambiguity: multiple matches

**Prompt:**
```
Add latency on the internet link via BR8.
```

Expected: multiple interfaces match "internet" (BR1-INET, BR2-INET, DC1-INET…).
Claude **lists all candidates** and asks the user to choose — does NOT pick one arbitrarily.

| Result | Notes |
|--------|-------|
| ⬜ | |

---

## 📊 Results Summary

| Test | Description | Result | Notes |
|------|-------------|--------|-------|
| 1 | Cold start — no hardcoded node | ⬜ | |
| 2 | Site name ("BR1 internet") → correct controller | ⬜ | |
| 3a | User sets controller → Claude uses it | ⬜ | |
| 3b | Same conversation → Claude remembers controller | ⬜ | |
| 4 | Multi-node discovery → identifies best controller | ⬜ | |
| 5a | Confirmation guard — waits for yes/no | ⬜ | |
| 5b | Reply "no" — action cancelled | ⬜ | |
| 6.1 | Regression: list scenarios | ⬜ | |
| 6.2 | Regression: full reset workflow | ⬜ | |
| 6.3 | Regression: multi-match ambiguity | ⬜ | |

---

## 🔍 Debug Tips

If Claude calls the wrong node or acts without asking:

```
Can you show me exactly which MCP tool you called and what arguments you passed?
```

```
Why did you choose that specific Stigix node as the VyOS controller?
```

```
Show me the raw JSON response you received from list_vyos_routers.
```

Check MCP server logs on the Stigix node:
```bash
docker logs stigix-mcp-server --tail 50
# or check the history file:
docker exec stigix cat /app/logs/mcp-history.jsonl | tail -20
```

---

*Generated for fix: VyOS controller discovery — docstring improvements in `mcp-server/src/server.py`*
