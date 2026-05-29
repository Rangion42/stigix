---
name: stigix-mcp-sync
description: >
  Audit and synchronize the Stigix MCP server tools with the stigix-cli.
  Use this whenever stigix-cli.py changes (new commands, bug fixes, new API parameters)
  to ensure Claude's MCP tools stay in sync. Also use when MCP tools have bugs that 
  were already fixed in the CLI.
---

# Stigix MCP Sync Skill

Use this skill whenever `Scripts/stigix-cli.py` is modified, or when a user reports that
an MCP tool behaves differently from the equivalent CLI command.

## When to Use

- After **any edit** to `Scripts/stigix-cli.py` (new commands, API fixes, new parameters)
- When a user reports a **bug** in an MCP tool that may have already been fixed in the CLI
- When asked "is the MCP server up to date?" or "can Claude do X?" after CLI changes
- Periodically as a health check if many CLI changes have accumulated

## Key Files

| File | Role |
|---|---|
| `Scripts/stigix-cli.py` | Source of truth for all available APIs |
| `mcp-server/src/server.py` | MCP tool registrations (`@mcp.tool()`) |
| `mcp-server/src/lib/orchestrator.py` | MCP business logic (HTTP calls) |
| `.agent/skills/stigix-mcp-sync/references/cli_to_mcp_map.md` | **Living registry** — CLI command → MCP tool mapping |

---

## Step-by-Step Process

### Step 1 — Identify What Changed in the CLI

```bash
# See recent commits touching the CLI
git log --oneline -20 -- Scripts/stigix-cli.py

# Diff the CLI since the last known MCP sync tag (adjust version as needed)
git diff v1.4.0-patch.100 -- Scripts/stigix-cli.py | head -200
```

Extract the key changes:
- New `api_get(...)` or `api_post(...)` calls → **new endpoints to expose**
- Changed payloads (new keys, renamed params) → **existing MCP tools to update**
- New CLI subcommands or flags → **new MCP tools or new parameters**
- Removed or deprecated calls → **MCP tools to mark as deprecated**

### Step 2 — Read the Current MCP Registry

Read the living registry file:
```
.agent/skills/stigix-mcp-sync/references/cli_to_mcp_map.md
```

This file documents every CLI command and whether it has a corresponding MCP tool.
Check:
- ❌ `NOT MAPPED` entries → candidates for new tools
- ⚠️ `PARTIAL` entries → tools that exist but have missing parameters or wrong payloads
- ✅ `MAPPED` entries → verify the payload still matches after the CLI diff

### Step 3 — Compare CLI APIs vs MCP Orchestrator

For each changed/new CLI `api_get` / `api_post` call, check if `orchestrator.py` has
a matching method using the **same endpoint and payload**.

```bash
# Find all HTTP calls in orchestrator
grep -n "client\.\(get\|post\|put\|delete\)" mcp-server/src/lib/orchestrator.py

# Find specific endpoint
grep -n "api/traffic/rate" mcp-server/src/lib/orchestrator.py
grep -n "api/traffic/rate" Scripts/stigix-cli.py
```

Compare:
- Is the **endpoint path** identical?
- Is the **request body/payload** identical (same JSON keys)?
- Are there **new optional parameters** in the CLI that should be added to the MCP tool?

### Step 4 — Implement Fixes

For each gap or drift found:

#### New tool needed (NOT MAPPED)
1. Add a new `async def method_name(...)` in `orchestrator.py` following the existing pattern
2. Add `@mcp.tool()` registration in `server.py` with a clear docstring
3. Validate with `python3 -c "import ast; ast.parse(open('src/server.py').read())"`

#### Payload drift (PARTIAL or wrong payload)
1. Update the orchestrator method to match the current CLI payload exactly
2. Add any missing parameters to the `@mcp.tool()` signature

#### Bug fix from CLI
1. Apply the same fix logic to the orchestrator method
2. Document what was fixed in the CHANGELOG

### Step 5 — Update the Registry

After implementing all changes, update the registry file:
`.agent/skills/stigix-mcp-sync/references/cli_to_mcp_map.md`

- Change `NOT MAPPED` → `MAPPED` for new tools
- Change `PARTIAL` → `MAPPED` for fixed tools
- Add new rows for new CLI commands discovered
- Update the "Last synced" header

### Step 6 — Deploy

Use the `stigix-deploy` skill to bump the version, commit, and push a tag.
The commit message should mention "MCP sync" and list what was added/fixed.

---

## Patterns to Follow

### Adding a new orchestrator method

```python
async def my_new_method(self, agent_id: str, param: str) -> Dict[str, Any]:
    """Brief description matching the CLI command purpose."""
    agent = await self.registry.get_endpoint(agent_id)
    if not agent:
        return {"error": f"Agent {agent_id} not found."}

    headers = {"Authorization": f"Bearer {self._generate_token()}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(  # or .post, .put, .delete
                f"{agent.api_base_url}/api/your/endpoint",
                headers=headers
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Failed to ... for {agent_id}: {e}")
            return {"error": str(e)}
```

### Adding a new @mcp.tool()

```python
@mcp.tool()
async def my_new_tool(agent_id: str, param: str) -> dict:
    """
    One-line summary of what this tool does.
    Include what Claude should know about when to use it.

    Args:
        agent_id: ID of the Stigix node.
        param: Description of the parameter and valid values.
    """
    return await orchestrator.my_new_method(agent_id, param)
```

### Authentication
Always use JWT Bearer: `{"Authorization": f"Bearer {self._generate_token()}"}`
Never use cookie-based auth (that's only for the CLI interactive session).

### Timeouts
- Standard reads: `timeout=10.0`
- Dashboard/heavy reads: `timeout=15.0`
- Batch security tests: `timeout=190.0` (180s test + 10s margin)
- Probe runs: `timeout=90.0`

---

## Quick Sanity Check

After any change, always run:
```bash
cd mcp-server
python3 -c "import ast; ast.parse(open('src/server.py').read()); print('OK')"
python3 -c "import ast; ast.parse(open('src/lib/orchestrator.py').read()); print('OK')"
```
