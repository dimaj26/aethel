# Aethel Development Orchestrator & AI Protocol (GEMINI.md)

Welcome, AI Developer. This file is the official human-written orchestrator and rulebook. It defines your behavioral boundaries, decision routing, planning blueprints, and development standards.

---

## 1. Decision Routing Protocols

When a user issues a prompt, categorize the work into one of three routes:

### Route A: Immediate Execution
* **Criteria**: Simple bug fixes, style adjustments, single-file edits, comments, minor unit tests, or exploratory requests.
* **Protocol**: Implement directly. No plan is required. Explain what you did concisely.

### Route B: Plan-First Implementation (RNA-Blueprint)
* **Criteria**: New features, architectural changes, multi-file edits, database modifications, or complex refactorings.
* **Protocol**:
  1. Perform codebase research using search tools. Do NOT modify code yet.
  2. Create or update `implementation_plan.md` using the **RNA-Blueprint** format.
  3. Specify any open questions or design decisions.
  4. Halt and wait for user approval before modifying code.
  5. Upon approval, create `task.md` and begin execution.

### Route C: Docs Update (MCP-driven Knowledge Graph)
* **Criteria**: Any changes to database schemas, API surfaces, module structures, business logic, or code patterns.
* **Protocol**:
  * Do NOT edit `memory.json` manually (this risks syntax vandalism).
  * Use the Memory MCP Server tools (`create_entities`, `create_relations`, `add_observations`) to document new structures or update existing ones.
  * For human-readable release changes, append to [CHANGELOG.md](file:///c:/aethel/CHANGELOG.md).

---

## 2. RNA-Blueprint Plan Template
Every complex plan must be structured as follows:

```markdown
# [Feature/Goal Description]

## User Review Required
- Highlight critical design choices, breaking changes, or trade-offs.

## Proposed Changes
### [Component/Module Name]
- [MODIFY/NEW/DELETE] [filename](file:///path/to/file)
  - Detail exact API and logic changes.

## Verification Plan
### Automated Tests
- Command to run tests (e.g., `pytest`, `npm test`).
### Manual Verification
- Visual inspection checklist or console output matches.
```

---

## 3. Git Commit Protocol
* Commits must use imperative mood (e.g., `feat: add memory sync command`, NOT `added memory sync command`).
* Group commits by type prefix:
  * `feat:`: New features
  * `fix:`: Bug fixes
  * `docs:`: Documentation updates (such as updating CHANGELOG.md)
  * `test:`: Adding or refactoring tests
  * `refactor:`: Restructuring code without changing behavior
  * `chore:`: Updates to build tasks, dependencies, etc.

---

## 4. Top-10 Critical Coding Taboos (Hard Constraints)

1. **NO Manual Edits to `memory.json`**: Do not edit the database file manually. Always write/read via Memory MCP tools.
2. **Sync Code and memory.json**: When modifying files or adding modules, immediately update the memory knowledge graph to match.
3. **Database Facades Only**: Never query the raw database context from the UI or handler layers. Use service/domain facades.
4. **FSM State Hygiene**: Never transition state machines without validating pre-conditions and logging the transition event.
5. **No Placeholders in Prod**: Do not commit placeholders, dry-run mocks, or unhandled `TODO` comments to the main branch.
6. **No state.clear()**: Do not invoke global state clears without explicit backup and verification.
7. **Clean Git Attributes**: Do not remove `.gitattributes` or bypass binary masking of database files.
8. **Fail-Fast Error Handling**: Never catch exceptions silently. Always log with tracebacks and propagate where appropriate.
9. **Keep Context.md Under 150 Lines**: Do not dump technical details into `CONTEXT.md` that belong in the memory knowledge graph.
10. **Linter Compliance**: Do not ignore warnings from the `prompt_linter.py` script. Fix them before finishing.
