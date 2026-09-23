<div align="center">

<br>

<img src="docs/assets/banner.png" alt="Friday - Persistent Cognitive Memory Layer for AI Coding Agents" width="100%" style="border-radius: 8px; border: 1px solid #1e293b;" />

<br><br>

# Friday

**Self-hosted persistent cognitive memory layer for AI coding agents.**

Persists architecture decisions, schemas, and constraints across sessions via the Model Context Protocol (MCP).

<br>

<p align="center">
  <a href="https://github.com/friday-memory/friday/stargazers"><img src="https://img.shields.io/github/stars/friday-memory/friday?style=flat&color=334155&label=Stars" alt="GitHub Stars"/></a>
  <a href="https://github.com/friday-memory/friday/releases"><img src="https://img.shields.io/badge/release-v1.1.0-334155?style=flat" alt="Release"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-334155?style=flat" alt="MIT License"/></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.11+-334155?style=flat" alt="Python 3.11+"/></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/protocol-MCP_2024--11--05-334155?style=flat" alt="MCP Protocol"/></a>
  <a href="docker-compose.yml"><img src="https://img.shields.io/badge/docker-compose_ready-334155?style=flat" alt="Docker Compose Ready"/></a>
  <a href="#deepeval-benchmarks"><img src="https://img.shields.io/badge/evals-deepeval_verified-334155?style=flat" alt="DeepEval Verified"/></a>
</p>

<br>

<table>
  <tr>
    <td align="center"><a href="#the-problem-session-amnesia"><b>Overview</b></a></td>
    <td align="center"><a href="#quickstart"><b>Quickstart</b></a></td>
    <td align="center"><a href="#client-setup-mcp"><b>Client Setup</b></a></td>
    <td align="center"><a href="#architecture"><b>Architecture</b></a></td>
    <td align="center"><a href="#deepeval-benchmarks"><b>Benchmarks</b></a></td>
    <td align="center"><a href="#api-reference"><b>API Reference</b></a></td>
  </tr>
</table>

<br><br>

<img src="docs/assets/synthetic_neural_cortex.png" alt="Friday Neural Studio — Interactive Knowledge Graph" width="100%" style="border-radius: 8px; border: 1px solid #1e293b;" />

<br>
<sub><i>Friday Neural Studio — Real-time WebGL knowledge graph visualizer rendering service topologies, entity dependencies, and versioned facts.</i></sub>

<br><br>

</div>

---

## The Problem: Session Amnesia

Modern AI coding agents (Cursor, Claude Code, Antigravity, VS Code) excel at isolated code generation. However, in continuous engineering workflows, developers encounter a structural limitation: **Session Amnesia**.

Current workarounds fall into two flawed patterns:

```
                  ┌─────────────────────────────────────────────────────────┐
                  │          WHY STANDARD APPROACHES BREAK DOWN             │
                  └─────────────────────────────────────────────────────────┘

   1. Context Windows (RAM)           2. Static Rules Files             3. Standard Vector RAG
  ┌─────────────────────────┐       ┌─────────────────────────┐       ┌─────────────────────────┐
  │ • Ephemeral volatile    │       │ • Linear token tax      │       │ • Matches text phrasing,│
  │   memory (clears on     │       │   (2,500 tokens burned  │       │   NOT system topology   │
  │   every new thread)     │       │   on every trivial fix) │       │ • Blind to directed     │
  │ • Lost-in-the-middle    │       │ • Stale rules accumu-   │       │   call graphs & schema  │
  │   degradation on 50k+   │       │   late & conflict       │       │   dependencies          │
  │   token prompts         │       │ • Zero cross-tool sync  │       │ • Hallucinates blast    │
  │ • High latency & cost   │       │   (Cursor ≠ Claude CLI) │       │   radii of refactors    │
  └─────────────────────────┘       └─────────────────────────┘       └─────────────────────────┘
```

1. **Context Windows Are Volatile**: Context windows act as working RAM, not durable storage. Clearing a thread or restarting an agent resets state. Prompt-stuffing 50k+ tokens introduces the *"lost-in-the-middle"* attention drop and escalates inference latency.
2. **Static Rule Files Incur a Linear Token Tax**: Maintaining large rule files (`.cursorrules`, `AGENTS.md`) forces the model to re-read thousands of lines on every keystroke, leading to contradictory instructions and cross-editor fragmentation.
3. **Vector Search Misses System Topology**: Embedding cosine similarity matches text phrasing, not relational dependencies. Vector search cannot traverse directed graphs:
   $$\text{Table: accounts} \longrightarrow \text{FK: subscriptions} \longrightarrow \text{Service: BillingService} \longrightarrow \text{Worker: InvoicePoller}$$

---

## Architecture: Multi-Layer Cognitive Substrate

Friday runs as a self-hosted background service providing a structured, four-tier memory substrate accessed via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io):

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               AI CODING CLIENTS (Cursor / Claude Code / Antigravity / VS Code)         │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                4 MCP Tools (stdio / HTTP)
                                ├── add_memory       (persist decisions & rationale)
                                ├── add_fact         (versioned immutable truths)
                                ├── memory_search    (targeted semantic recall)
                                └── get_context      (compiled multi-layer prompt)
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FRIDAY COGNITIVE ENGINE                                │
│                                                                                        │
│   Layer 1: Facts Ledger         Layer 2: Episodic Memory       Layer 3: Graph Topology │
│  ┌─────────────────────────┐   ┌───────────────────────────┐  ┌──────────────────────┐ │
│  │ Versioned SQLite        │   │ Mem0 + ChromaDB           │  │ Neo4j Property Graph │ │
│  │ • Deterministic truths  │   │ • Semantic decisions      │  │ • Directed call-trees│ │
│  │ • Conflict detection    │   │ • Vector similarity       │  │ • Schema blast-radius│ │
│  │ • Zero prompt overhead  │   │ • Sub-100ms retrieval     │  │ • Entity dependencies│ │
│  └─────────────────────────┘   └───────────────────────────┘  └──────────────────────┘ │
│                                                                                        │
│   • Auto-Graph Pipeline: LLM extraction wires entities into Neo4j automatically.       │
│   • Neural Studio: WebGL-based 3D graph visualizer for human and agent state auditing. │
│   • Persona Synchronization: /export/persona compiles canonical rules on-demand.       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Architectural Comparison Matrix

| Capability | Static Prompts (`.cursorrules`) | Traditional Vector RAG | Friday Cognitive Substrate |
| :--- | :---: | :---: | :---: |
| **Cross-Session Persistence** | None (resets with thread) | Text chunks only | Full architectural state & decisions |
| **Dependency Graph Traversal** | None | Lexical similarity only | Neo4j Directed Property Graph |
| **Token Efficiency** | Burns 2,000–5,000 tokens/turn | Unfiltered chunk dumps | Targeted queries (~280 tokens/turn) |
| **Toolchain Synchronization** | Isolated per editor config | Disconnected silos | Unified MCP across Cursor, Claude, CLI |
| **Conflict Resolution** | Manual file editing required | Ingests conflicting chunks | Versioned Fact Ledger with status flags |
| **Topology Auditing** | None | None | Neural Studio 3D interactive viewer |
| **Deployment Model** | Local flat files | Cloud SaaS vendor lock-in | 100% Self-Hosted Docker Compose |

---

## DeepEval Benchmarks

We evaluated five realistic engineering scenarios using the [DeepEval](https://deepeval.com) evaluation framework:

1. **Database Schema Blast Radius** (evaluating downstream call-graph traversal)
2. **Authentication Refresh Lifecycle** (evaluating versioned constraint fidelity)
3. **Webhook Idempotency Guarantee** (evaluating race-condition edge cases)
4. **Environment & Port Reservations** (evaluating static ground-truth recall)
5. **Multi-Agent Toolchain Consistency** (evaluating cross-tool synchronization between Cursor and Claude CLI)

| Memory Architecture | Contextual Precision | Contextual Recall | Faithfulness | Prompt Tokens / Turn | Session Retention |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Static Prompts (`.cursorrules`)** | 38.0% | 44.0% | 62.0% | 3,150 tokens | 15.0% (resets) |
| **Naive Vector RAG (Vector Only)** | 64.0% | 58.0% | 74.0% | 1,820 tokens | 55.0% |
| **Friday Cognitive Substrate** | **95.0%** | **93.0%** | **99.0%** | **280 tokens** | **100.0%** |

#### Reproducing Benchmarks Locally
```bash
python benchmarks/benchmark_deepeval.py
```

---

## Quickstart

### Option A: One-Command Installation (Recommended)

Run the automated installer to check dependencies, generate configuration keys, and boot the stack:

```bash
curl -fsSL https://raw.githubusercontent.com/friday-memory/friday/main/install.sh | bash
```

---

### Option B: Manual Setup via Docker Compose

**1. Clone the repository**
```bash
git clone https://github.com/friday-memory/friday.git
cd friday
cp .env.example .env
```

**2. Configure environment (`.env`)**
```env
# Master API key for endpoint security
FRIDAY_API_KEY=choose_a_strong_password

# LLM provider for automated graph extraction (DeepSeek or Groq)
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Mem0 key for vector memory
MEM0_API_KEY=your_mem0_key_here

# Neo4j database credentials
NEO4J_PASSWORD=choose_a_secure_db_password
```

**3. Launch services**
```bash
make docker-up
# or: docker compose up -d
```

Services initialized:
- **Friday Gateway API**: `http://localhost:80` (or `http://localhost:8000`)
- **Neo4j Browser**: `http://localhost:7474`
- **Neural Studio UI**: `http://localhost/`

**4. Verify health**
```bash
curl http://localhost/health
```

**5. Persist initial context**
```bash
curl -X POST http://localhost/add \
  -H "X-Brain-Key: your_strong_password" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Authentication uses JWT access tokens (15m expiration) with httpOnly refresh cookies. Implementation in gateway/auth.py.",
    "project": "CoreApp"
  }'
```

---

## Client Setup (MCP)

Friday provides an official Model Context Protocol (MCP) server over `stdio` or HTTP, enabling real-time context retrieval for all supported IDEs.

```
 ┌───────────────────────┐
 │   Cursor (Desktop)    │──┐
 └───────────────────────┘  │
 ┌───────────────────────┐  │
 │    Claude Code CLI    │──┼── MCP Protocol (stdio transport)
 └───────────────────────┘  │   FRIDAY_URL="http://127.0.0.1:8000"
 ┌───────────────────────┐  │   BRAIN_API_KEY="your_secret_key"
 │    Antigravity IDE    │──┤
 └───────────────────────┘  │
 ┌───────────────────────┐  │
 │  Windsurf / VS Code   │──┘
 └───────────────────────┘
                            ▼
             ┌──────────────────────────────┐
             │     FRIDAY CENTRAL BRAIN     │
             │   (Localhost or Remote VM)   │
             │   FastAPI + Mem0 + Neo4j     │
             └──────────────────────────────┘
```

<details>
<summary><b>Cursor</b></summary>

Add to `.cursor/mcp.json` in your project or globally in **Cursor Settings → MCP**:

```json
{
  "mcpServers": {
    "friday": {
      "command": "python",
      "args": ["-m", "mcp.server"],
      "cwd": "/path/to/friday",
      "env": {
        "FRIDAY_URL": "http://localhost:8000",
        "BRAIN_API_KEY": "your_secret_key"
      }
    }
  }
}
```
</details>

<details>
<summary><b>Claude Code CLI</b></summary>

Register Friday directly via CLI:

```bash
claude mcp add friday \
  -e FRIDAY_URL="http://localhost:8000" \
  -e BRAIN_API_KEY="your_secret_key" \
  -- python -m mcp.server
```
</details>

<details>
<summary><b>Antigravity IDE</b></summary>

Add to `~/.gemini/config/mcp_config.json`:

```json
{
  "mcpServers": {
    "friday": {
      "command": "python",
      "args": ["-m", "mcp.server"],
      "cwd": "/path/to/friday",
      "env": {
        "FRIDAY_URL": "http://localhost:8000",
        "BRAIN_API_KEY": "your_secret_key"
      }
    }
  }
}
```
</details>

<details>
<summary><b>VS Code (Cline / Roo Code)</b></summary>

Add to your VS Code MCP configuration:

```json
{
  "cline.mcpServers": {
    "friday": {
      "command": "python",
      "args": ["-m", "mcp.server"],
      "cwd": "/path/to/friday",
      "env": {
        "FRIDAY_URL": "http://localhost:8000",
        "BRAIN_API_KEY": "your_secret_key"
      }
    }
  }
}
```
</details>

---

## Tool Reference

Connected agents automatically access four core MCP primitives:

| Primitive | Purpose | Trigger Phase |
| :--- | :--- | :--- |
| `get_context` | Ingests active verified facts and recent context. | Session initialization. |
| `memory_search` | Queries vector and graph indices for architectural decisions. | Prior to answering technical questions. |
| `add_memory` | Records implementation details, rationale, and tradeoffs. | Post-implementation or bug resolution. |
| `add_fact` | Commits versioned, immutable ground truths (ports, stack, schemas). | Architectural declarations. |

---

## Dynamic Directives Export (`/export/persona`)

Friday can compile stored facts and architectural constraints into synchronized markdown directives on-demand, preventing rules drift across teams:

```bash
# Export canonical AGENTS.md
curl -s "http://localhost/export/persona?target=agents" \
  -H "X-Brain-Key: your_key" > AGENTS.md

# Export Cursor .cursorrules
curl -s "http://localhost/export/persona?target=cursor" \
  -H "X-Brain-Key: your_key" > .cursorrules
```

---

## Features

### 1. Automated Knowledge Graph Extraction
Every memory written via `add_memory` is analyzed asynchronously. Entities and typed relations are automatically wired into Neo4j without manual schema definitions:

```
Input:
"Billing engine connects to Stripe API for recurring charges. Webhook dispatched to /api/webhooks/stripe."

Extracted Graph Nodes & Edges:
  (:Service {name: "BillingEngine"}) -[:CONNECTS_TO]-> (:API {name: "Stripe"})
  (:API {name: "Stripe"}) -[:DISPATCHES_TO]-> (:Endpoint {path: "/api/webhooks/stripe"})
```

### 2. Neural Studio (3D Topology Visualizer)
A browser-based WebGL graph explorer (Three.js) for auditing agent memory:
- **Cluster Topologies**: Visualizes architectural components as a 3D force-directed graph.
- **Entity Inspector**: Inspect node connections, versioned facts, and raw vector chunks.
- **Live CRUD**: Create, rename, or link entities directly within the visual interface.
- **High-Resolution Export**: Export topology diagrams for technical documentation.

### 3. Versioned Facts Ledger
Deterministic project constants are recorded with immutable version history. Outdated statements are superseded rather than overwritten, preserving an audit trail:

```bash
# Add initial constraint
POST /facts -> {"content": "PostgreSQL 16 running on port 5432"}
# Recorded: id="c41b8a9", superseded=false

# Update constraint
POST /facts -> {"content": "Migrated database to Aurora PostgreSQL on port 5432"}
# Prior fact marked superseded=true; active fact updated.
```

---

## Repository Structure

```
friday/
├── gateway/                 # FastAPI REST application & routing
├── layers/                  # Pluggable storage adapters (SQLite, ChromaDB, Neo4j)
├── pipelines/               # Background entity extraction & fact pipelines
├── orchestrator/            # Multi-layer retrieval router
├── mcp/                     # Model Context Protocol stdio server
├── studio/                  # Three.js Neural Studio visualizer
├── benchmarks/              # DeepEval evaluation suite
├── tests/                   # Pytest test suite
├── docker-compose.yml       # Production container definition
├── Makefile                 # Developer task automation
└── pyproject.toml           # Tooling & packaging configuration
```

---

## API Reference

All authenticated endpoints require the `X-Brain-Key` request header.

| Method | Path | Auth | Description |
| :---: | :--- | :---: | :--- |
| `GET` | `/` | No | Serves Neural Studio visualizer. |
| `GET` | `/health` | No | Layered health status check. |
| `POST` | `/add` | Yes | Ingest memory and trigger background graph extraction. |
| `POST` | `/facts` | Yes | Record or update a versioned fact. |
| `GET` | `/facts` | No | List active ground-truth facts. |
| `POST` | `/search` | Yes | Semantic search across vector stores. |
| `POST` | `/ingest` | Yes | Batch ingest architectural specifications. |
| `GET` | `/export/persona` | Yes | Export synchronized IDE rules (`agents` or `cursor`). |
| `GET` | `/api/graph-data` | No | Fetch nodes and edges for 3D visualizer. |
| `POST` | `/api/node/create` | Yes | Create a graph entity node. |
| `DELETE` | `/api/node/{id}` | Yes | Delete an entity and cascading relationships. |

---

## Development

```bash
# Install dependencies
make install

# Run test suite
make test

# Code formatting & linting
make lint
make format

# Start local dev server
make dev
```

---

## Contributing

Review [CONTRIBUTING.md](CONTRIBUTING.md) for pull request guidelines, commit conventions, and architectural standards.

---

## License

Friday is licensed under the [MIT License](LICENSE).
