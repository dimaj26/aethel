# Aethel: AI Context & Memory Management System

Aethel is a lightweight, pragmatically designed context and prompt management boilerplate for AI agents in solo-developer projects. It separates human-authored rules (Markdown) from AI-maintained technical context (JSON Lines Graph via MCP).

---

## 1. File Structure

* **`.gitattributes`**: Configures Git to treat `memory.json` as a binary file (`memory.json binary`) to hide noisy JSON diffs.
* **`AETHEL.md`**: Canonical human-written orchestrator — decision routing, RNA-Blueprint plan templates, and critical coding taboos.
* **`GEMINI.md` / `CLAUDE.md`**: Redirect stubs that point the agent at `AETHEL.md`.
* **`aethel.toml`** *(optional)*: Linter policy — ontology (entity/relation types), required-header keywords, and language rules. Omit to use built-in defaults.
* **`CONTEXT.md`**: Compact technical summary (under 150 lines) referencing project layouts, DDL schemas, and key paths.
* **`memory.json`**: Newline-delimited JSON graph representing the AI agent's semantic knowledge database, managed via MCP.

---

## 2. MCP Integration & Setup

To enable your AI agent to read and write to `memory.json` dynamically, integrate the official Anthropic Memory MCP server.

### A. Claude Desktop
1. Locate the Claude Desktop configuration file:
   * **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   * **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Open or create the file and add the server definition under `mcpServers`:
   ```json
   {
     "mcpServers": {
       "aethel-memory": {
         "command": "npx",
         "args": [
           "-y",
           "@modelcontextprotocol/server-memory"
         ],
         "env": {
           "MEMORY_FILE_PATH": "c:/aethel/memory.json"
         }
       }
     }
   }
   ```
3. Restart Claude Desktop.

### B. Cursor IDE
1. Open Cursor and go to **Settings** -> **Features** -> **MCP**.
2. Click **+ Add New MCP Server**.
3. Fill in the fields:
   * **Name**: `aethel-memory`
   * **Type**: `command`
   * **Command**: `npx -y @modelcontextprotocol/server-memory`
4. **Environment Variables**:
   Since Cursor's UI does not natively support setting environment variables directly for commands, you must launch Cursor from a terminal session where the variable is set:
   * **PowerShell**:
     ```powershell
     $env:MEMORY_FILE_PATH="c:/aethel/memory.json"
     cursor .
     ```
   * **Command Prompt**:
     ```cmd
     set MEMORY_FILE_PATH=c:/aethel/memory.json
     cursor .
     ```

---

## 3. Git-Centric Rollback & Memory Safety

Because memory is persisted in `memory.json` directly inside the repository, AI memory state is tracked in sync with code branches.

* **Clean Diffs**: `.gitattributes` masks the text-based changes so your terminal commits aren't flooded with JSON diff lines.
* **Synchronous Rollbacks**: If you checkout an old commit or reset a branch, you restore the memory state of that exact timestamp:
  ```bash
  git checkout <commit_hash> memory.json
  # OR
  git restore memory.json
  ```
