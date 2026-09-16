# IDE & Agent Setup — Ready-Made MCP Configs

Friday acts as a **central persistent memory** across all your AI coding tools.  
Whether running locally or on a remote cloud server (AWS EC2 / VPS), connect all your tools to the same `FRIDAY_URL`.

---

## Quick Setup (2 steps)

**Step 1:** Start Friday
```bash
docker compose up -d
```

**Step 2:** Copy the config for your tool:

### ⚡ Antigravity IDE  
Copy `antigravity.json` → `~/.gemini/config/mcp_config.json`

### 🤖 Claude Code (CLI)
Connect via CLI:
```bash
claude mcp add friday -e FRIDAY_URL="http://localhost:8000" -e BRAIN_API_KEY="your_key" -- python -m mcp.server
```
Or copy `claude_code.json` into `~/.claude.json`.

### 🖱️ Cursor
Copy `cursor.json` → `.cursor/mcp.json` (or Cursor Settings → MCP → Add Server)

### 💻 VS Code (Cline / Roo Code)
Copy `vscode.json` → VS Code `settings.json`

### 🖥️ Claude Desktop
Copy `claude_desktop.json` → `~/Library/Application Support/Claude/claude_desktop_config.json`

### 📟 Codex & Autonomous Agents
Use the direct HTTP REST API:
```bash
curl -X POST http://<your-server-ip>:8000/add \
  -H "X-Brain-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{"content": "Architecture decision", "project": "MyApp"}'
```

---
*Note: If running on a remote cloud server/EC2, replace `http://localhost:8000` with `http://<your-server-ip>:8000`.*
