# Demo Architecture Blueprint

## Project: MyApp

### Tech Stack
- **Backend**: FastAPI (Python 3.11)
- **Database**: PostgreSQL 15 (primary) + Redis (cache)
- **AI Memory**: Friday (this project!)
- **Deployment**: Docker Compose → AWS EC2

### Key Components
1. **API Gateway** (`gateway/`) — FastAPI routes, auth middleware
2. **Memory Layer** — Mem0 (semantic) + ChromaDB (vector) + Neo4j (graph)
3. **Pipelines** — Auto-graph extraction, fact versioning
4. **Neural Studio** — Visual knowledge graph UI

### Architecture Decisions
- JWT for auth (not sessions) — stateless scaling
- Async everywhere — uvicorn + asyncio
- Background tasks for graph wiring (non-blocking UX)
