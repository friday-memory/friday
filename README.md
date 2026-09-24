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
  <a href="https://github.com/friday-memory/friday/releases"><img src="https://img.shields.io/badge/release-v1.3.0-334155?style=flat" alt="Release"/></a>
  <a href="https://pypi.org/project/friday-memory/"><img src="https://img.shields.io/pypi/v/friday-memory?style=flat&color=334155&label=PyPI" alt="PyPI Package"/></a>
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
    <td align="center"><a href="#python-sdk-friday-memory"><b>Python SDK</b></a></td>
    <td align="center"><a href="#client-setup-mcp"><b>Client Setup (MCP)</b></a></td>
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


---

## Cognitive Core 2.0 (Biological Memory Architecture)

Friday incorporates biologically-inspired memory mechanics to ensure AI agents maintain pristine context without bloat, stale instruction interference, or communication misalignment:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                          FRIDAY COGNITIVE DYNAMICS ENGINE                              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│  🔥 Dynamic Memory Heat & Decay           🌙 The Dream Cycle (Nightly 03:00 UTC)      │
│  ┌───────────────────────────────────┐    ┌────────────────────────────────────────┐   │
│  │ Exponential Synaptic Decay        │    │ 1. Synaptic Pruning (Evaporates noise) │   │
│  │ • E(t) = E₀ · 2^(-Δt / T_half)    │───>│ 2. Episodic Synthesis (Distills gems)  │   │
│  │ • Recall Potentiation (+0.25)     │    │ 3. Neo4j Crystallization (Graph edges) │   │
│  │ • Soft Archive if E < 0.25        │    │ 4. Autonomous Backup to Git            │   │
│  └───────────────────────────────────┘    └────────────────────────────────────────┘   │
│                                                                                        │
│  🤍 Empathy & Cognitive State Tracking                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Multi-Dimensional User Calibration                                               │  │
│  │ • Interaction Modes: tactical_sprint | deep_architecture | casual_brainstorm      │  │
│  │ • Real-time Stress & Urgency Detection (0.0 to 1.0)                              │  │
│  │ • Dynamic Response Calibration: Brevity (high/med/low) & Tone Tuning             │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1. 🔥 Dynamic Memory Heat & Decay
Memories and verified facts are not static text—they have energy. Active, frequently recalled directives remain bright ($E > 1.0$). Irrelevant or outdated details experience exponential half-life decay ($T_{half} = 14\text{ days}$):
$$E(t) = E_0 \times 2^{-\frac{\Delta t}{T_{half}}}$$
When a memory is queried during coding, it receives a recall potentiation boost ($+0.25$), preventing stale knowledge from cluttering the agent prompt while preserving core architectural invariants.

### 2. 🌙 The Dream Cycle
Every night at 03:00 UTC (or on-demand), Friday enters the **Dream Cycle**:
- **Synaptic Pruning**: Identifies cold/stale facts and transitions them to archived storage.
- **Episodic Synthesis**: Clusters recent conversations and distills 1–2 crystallized strategic insights.
- **Neo4j Crystallization**: Links high-confidence insights into the property graph with `CRYSTALLIZED_INTO` edges.
- **Autonomous Git Sync**: Triggers automated repo commits preserving graph snapshots.

### 3. 🤍 Empathy & Cognitive State Tracking
Friday monitors the developer interaction context (urgent bug-fix sprint, late-night architecture exploration, or casual brainstorming). The engine dynamically adjusts agent response characteristics:
- **Brevity Calibration**: `high` (zero fluff, code-first) vs. `detailed` (system-wide breakdown).
- **Tone Calibration**: `sharp_tactical` (Kerry Condon MCU wit) vs. `structured_analytical`.
- Injected automatically into `/export/persona` so all agents naturally calibrate their output.

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

## Python SDK (`friday-memory`)

The official Python client for Friday is available on PyPI as [**`friday-memory`**](https://pypi.org/project/friday-memory/). Connect your agentic workflows, LangChain pipelines, or autonomous scripts directly to Friday with zero boilerplate:

```bash
pip install friday-memory
```

### Synchronous Client

```python
from friday import Friday

# Automatically resolves FRIDAY_URL and FRIDAY_API_KEY from environment
with Friday(api_key="your_secret_key", base_url="http://localhost:8000") as client:
    # 1. Health check
    status = client.health()
    print("Friday Status:", status["status"])

    # 2. Store architectural decision
    client.add_memory(
        "PostgreSQL 16 selected with pgvector for hybrid retrieval",
        project="backend-api",
    )

    # 3. Commit immutable ground-truth fact
    client.add_fact("Production database endpoint is db.internal.net:5432")

    # 4. Multi-layer search (L2 Facts + L3 ChromaDB + L4 Knowledge Graph)
    context = client.search("database connection configuration", project="backend-api")
    print(context["results"])

    # 5. Cognitive State & Dynamic Response Calibration
    state = client.get_cognitive_state()
    print("Active Mode:", state["current_mode"])  # tactical_sprint, deep_architecture, etc.

    # 6. Trigger Nightly Dream Cycle Consolidation (Consolidates & Prunes)
    dream_report = client.run_dream_cycle(half_life_days=14.0)
    print("Crystallized Insights:", dream_report["crystallized_insights"])

    # 7. Apply Synaptic Decay
    decay_report = client.apply_decay(half_life_days=14.0)
    print("Active Facts Remaining:", decay_report["active_facts_count"])
```

### Asynchronous Client (FastAPI / Agent Workers)

```python
import asyncio
from friday import AsyncFriday

async def main():
    async with AsyncFriday(api_key="your_secret_key") as client:
        # Commit context concurrently
        await client.add_memory("Redis cluster deployed for token bucket rate limiting")
        facts = await client.get_facts()
        print(f"Verified facts count: {len(facts)}")

asyncio.run(main())
```

### LangChain Integration (`FridayRetriever`)

```bash
pip install "friday-memory[langchain]"
```

```python
from friday.integrations.langchain import FridayRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

retriever = FridayRetriever(
    api_key="your_secret_key",
    base_url="http://localhost:8000",
    project="reeldm",
)

# Connect directly to LCEL chains
prompt = ChatPromptTemplate.from_template("""Answer using verified system memory:
{context}

Question: {question}""")

chain = {"context": retriever, "question": RunnablePassthrough()} | prompt | ChatOpenAI()
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
├── friday/                  # Official Python SDK (client, types, LangChain retriever)
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
| `GET` | `/state` | No | Retrieve active developer cognitive state & calibration. |
| `POST` | `/state/update` | Yes | Update mode, urgency, stress, and response calibration. |
| `POST` | `/dream/run` | Yes | Trigger biological Dream Cycle memory consolidation. |
| `POST` | `/decay/apply` | Yes | Apply exponential synaptic decay across facts ledger. |
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
