# Aethel Technical Context Core (CONTEXT.md)

This is the compact technical index for the Aethel system. Keep it under 150 lines. Elaborate technical rules and schemas must be pushed to the Memory MCP Graph.

---

## 1. Project Directory Structure & Tech Stack

```text
├── .gitattributes         # Masking memory.json from git diffs (memory.json binary)
├── AETHEL.md              # AI Orchestrator & Development rules (Human-edited, canonical)
├── GEMINI.md / CLAUDE.md  # Redirect stubs pointing at AETHEL.md
├── aethel.toml            # Optional linter policy (ontology / structure / language / sync)
├── CONTEXT.md             # Technical context core (Under 150 lines, Human-edited)
├── CHANGELOG.md           # Project history (Human-edited)
├── memory.json            # AI Knowledge Graph (MCP-generated JSON Lines)
├── aethel/                # CLI package: cli.py, linter.py, config.py, templates/
│                          #   recipes discovered at runtime from templates/recipes/* (no hard-coded list)
└── prompt_linter.py       # Local CLI integrity linter (wrapper around aethel.linter)
```

* **Core Stack**: Python 3.11+ / Node.js 20+
* **Memory Layer**: Anthropic Memory MCP Server (`@modelcontextprotocol/server-memory`)
* **Serialization**: Newline-delimited JSON (JSON Lines) stored in `memory.json`.

---

## 2. Core Database Schema (DDL reference)

To prevent database and schema hallucinations, refer to this schema definition:

```sql
-- Knowledge Graph Schema Reference
-- Stored logically in memory.json as JSON Lines containing Entity and Relation records.

CREATE TABLE Entity (
    name VARCHAR(255) PRIMARY KEY,
    entityType VARCHAR(100) NOT NULL,
    observations TEXT[] NOT NULL
);

CREATE TABLE Relation (
    "from" VARCHAR(255) REFERENCES Entity(name) ON DELETE CASCADE,
    "to" VARCHAR(255) REFERENCES Entity(name) ON DELETE CASCADE,
    relationType VARCHAR(100) NOT NULL,
    PRIMARY KEY ("from", "to", relationType)
);
```

---

## 3. Top-10 Critical Coding Taboos (Reference Checklist)

1. **Anti-Vandalism**: No manual JSON edits to `memory.json`. Use MCP tools to alter the graph.
2. **Git Hygiene**: Keep `.gitattributes` configured so `memory.json` is treated as a binary file.
3. **FSM State Hygiene**: Check state preconditions and log transitions clearly.
4. **Clean Facades**: Isolate UI handlers from direct data/database mutations using Service layers.
5. **No Blind Clears**: Never clear state/cache without creating safety backups.
6. **Lint First**: Always run `python prompt_linter.py` before executing commits or wrapping up tasks.
7. **Strict Typings**: Ensure all typescript or python code uses strict typing; avoid `any` or `object`.
8. **No Silent Swallows**: Do not use empty `except:` or `catch(e) {}` blocks.
9. **Single H1 per Page**: Web layouts must strictly use exactly one `<h1>` header for SEO.
10. **TDD Workflow**: Write tests before coding new business logic/endpoints.

---

## 4. Obsidian RAG Navigation Map

For deep context exploration, navigate using the following semantic Obsidian note indices:
* `obsidian://open?vault=aethel&file=architectures%2Fmemory_mcp`: Schema and entity architecture diagrams.
* `obsidian://open?vault=aethel&file=workflows%2Froute_routing`: Decision routing models.
* `obsidian://open?vault=aethel&file=specs%2Flinter_spec`: Details on cycle-detection and rule checks.
