# AI Agent Core Directives — Persistent Memory Protocol for Friday

> **ENVIRONMENT:** Configured for **Continue.dev** interacting via the `friday` Model Context Protocol (MCP) server.
> **OBJECTIVE:** Enforce persistent state retention, eliminate session amnesia, and maintain verifiable project constraints across engineering sessions.

---

## 1. Two-Way Zero-Amnesia Protocol

Every session must operate with bidirectional state validation through the Friday MCP server:

### A. Pre-Task Read Gate (Turn Start — Ground-Truth Retrieval)
- **Never guess** architecture decisions, database schemas, active endpoints, or past constraints from local context buffer alone.
- Before formulating a multi-step plan or executing code modifications, query the `friday` server:
  - Use `friday:get_context(query='<active task or component>')` to retrieve relevant architectural facts and constraints.
  - Use `friday:memory_search(query='<technical topic>')` to surface prior implementation rationale and resolved trade-offs.

### B. Post-Task Write Gate (Turn Finish — State Persistence)
- Whenever you complete a task, resolve a bug, introduce a schema change, or establish a new technical constraint, sync to `friday` immediately.
- Do not wait for the developer to request a memory update:
  - Record atomic, high-confidence constraints with `friday:add_fact(content='...')`.
  - Record session summaries, rationale, and bug fixes with `friday:add_memory(content='...')`.

---

## 2. Engineering & Quality Standards

- **Deterministic Ground Truth**: Prefer structured facts and verified test outcomes over assumptions.
- **Clean Code Hygiene**: Run test suites before considering tasks complete. Never leave unverified commits.
- **Zero Promotional Fluff**: Maintain concise, precise, systems-engineering documentation. Avoid speculative hype, marketing jargon, or synthetic fluff.
