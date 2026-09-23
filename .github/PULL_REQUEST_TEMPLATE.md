## Description

Brief summary of the changes introduced in this pull request and the rationale behind them.

Fixes #(issue)

## Type of Change

- [ ] `fix`: Bug fix (non-breaking change which fixes an issue)
- [ ] `feat`: New feature (non-breaking change which adds functionality)
- [ ] `refactor`: Code refactoring or architectural cleanup
- [ ] `perf`: Performance improvement
- [ ] `docs`: Documentation updates or corrections
- [ ] `chore`: CI, dependency, or tooling updates

## Architecture Impact

- [ ] Updates MCP tool schema (`mcp/server.py`)
- [ ] Modifies database layer (SQLite / Neo4j / ChromaDB)
- [ ] Modifies Neural Studio visualizer (`studio/`)
- [ ] None (internal logic / tests only)

## Verification & Testing

Explain how the changes were verified:

```bash
# Example test run
make test
make lint
```

- [ ] Unit tests added / updated and passing green
- [ ] Smoke tested locally with FastAPI TestClient
- [ ] Verified live against Docker Compose stack (if applicable)
- [ ] No regression in token extraction or graph ingestion

## Checklist

- [ ] Code follows project style guidelines (`ruff check .`)
- [ ] All public methods and endpoints have clear docstrings
- [ ] Relevant documentation updated (README, API reference, or docs)
- [ ] Commit message follows Conventional Commits format
