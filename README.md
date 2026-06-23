# Aethel: AI Context & Knowledge Management System

Aethel is a lightweight, provider-agnostic context and prompt management boilerplate for AI
agents in solo-developer projects. It separates human-authored rules (Markdown) from an
AI-maintained Markdown knowledge layer — a curated index plus a tree of atomic topic files —
with no server or external runtime dependency.

---

## 1. File Structure

* **`AETHEL.md`**: Canonical human-written orchestrator — decision routing, RNA-Blueprint plan templates, and critical coding taboos.
* **`AGENTS.md`**: Universal cross-agent entry point. Read natively by most coding agents; it redirects to `AETHEL.md`.
* **`GEMINI.md` / `CLAUDE.md`**: Thin redirect stubs (for tools that look for those names) pointing at `AGENTS.md` / `AETHEL.md`.
* **`CONTEXT.md`**: An [`llms.txt`](https://llmstxt.org/)-style index — an H1, a one-line summary, then H2 sections of annotated **inline** links into the knowledge tree. Curated, not exhaustive; kept under 150 lines.
* **`knowledge/`**: Atomic topic files (one layer / subsystem / bounded context each, `name` + `description` frontmatter). Detail lives here, not in the index. Design decisions are append-only ADRs under `knowledge/decisions/NNNN-*.md`.
* **`aethel.toml`** *(optional)*: Linter policy — required-header keywords, language rules, spec-sync, and `[knowledge]` index/orphan settings. Omit to use built-in defaults.

---

## 2. The Markdown Knowledge Architecture

Structured knowledge is plain Markdown — there is nothing to install or wire up:

* The **index** (`CONTEXT.md`) maps the project. Each entry is one inline link to a topic file
  with a one-line note.
* Each **topic file** under `knowledge/` is a single unit-of-change and unit-of-retrieval.
* **Decisions** are recorded as numbered ADRs under `knowledge/decisions/`.

The linter (`aethel lint` → `check_knowledge_index`) keeps the index honest: a relative inline
link that does not resolve on disk is an **error**; a `knowledge/*.md` file not reachable from
the index is an **orphan warning**. External (`http(s)`/`mailto`) links and `#anchors` are
ignored. Use inline links only — reference-style links and autolinks are intentionally not
parsed. Severities are configurable in `aethel.toml` under `[knowledge]`.

> Earlier versions stored structured knowledge in a Memory MCP server / `memory.json` graph.
> That layer has been retired in favour of this provider-agnostic Markdown architecture; see
> [knowledge/decisions/0001-retire-memory-graph.md](knowledge/decisions/0001-retire-memory-graph.md).

---

## 3. CLI

```bash
aethel init [path]            # scaffold a workspace (AGENTS.md, AETHEL.md, CONTEXT.md, knowledge/, ...)
aethel init --recipe python   # also deploy a stack-specific linter recipe
aethel update [path]          # refresh the managed core block non-destructively
aethel eject [path]           # mark the managed core block as sanctioned divergence
aethel eject [path] --undo    # remove the eject stamp, restoring managed updates
aethel lint [path]            # validate plan/checklist + knowledge-index integrity + hygiene
```

`aethel init` also installs a Git pre-commit hook that runs the linter, including the spec-sync
drift guard (code staged without a spec update is flagged — Route C). Escape hatch for an
intentionally spec-irrelevant commit: `AETHEL_SKIP_SYNC=1 git commit ...`.
