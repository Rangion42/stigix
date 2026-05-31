---
name: stigix-lang
description: >
  Language policy for the Stigix repository. Use this skill whenever writing
  or editing any file that will be committed to the GitHub repository
  (docs/, mcp-server/Exemple/, README, CHANGELOG, code comments, docstrings,
  tool descriptions, etc.). Conversation with the user may remain in French,
  but all repo-facing content must be in English.
---

# Stigix Language Policy

## Rule

**All content committed to the Stigix GitHub repository MUST be written in English.**

This applies to:
- Documentation files (`docs/*.md`, `*.md` at repo root)
- MCP example files (`mcp-server/Exemple/*.md`)
- Code comments and docstrings (`server.py`, `orchestrator.py`, `server.ts`, etc.)
- MCP tool descriptions and parameter docs
- Git commit messages
- Skill and workflow files (`.agent/`)
- README, CHANGELOG, VERSION notes

**Exception:** Conversation with the user may remain in French. Only the files written to disk must be in English.

## Why

The Stigix repository is public and internationally oriented. Non-English content in repo files creates friction for contributors and users who do not speak French.

## Checklist Before Writing Any Repo File

1. ✅ Is the target path inside the Git repo (`/Users/jsuzanne/Github/stigix/`)?
   → Write in **English**.
2. ✅ Is this a scratch/artifact file outside the repo?
   → Language is flexible.
3. ✅ Is this a response in the chat?
   → French is fine.

## Translation Guidance

When translating existing French content to English:
- Keep technical terms as-is (node IDs, API paths, JSON keys)
- Preserve all markdown formatting, code blocks, tables, and alert syntax
- Keep the same document structure and section headings
- Do NOT translate node/endpoint IDs (e.g., `BR8-Ubuntu`, `ubuntubr5`, `DC1`)
- Do NOT translate JSON field names or API parameters
- Translate UI labels faithfully (e.g., "Ouvrir l'UI" → "Open the UI")
