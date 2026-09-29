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
- [ ] Modifies core gateway endpoints (`gateway/main.py`)
- [ ] Modifies Python SDK client or rules engine (`friday/`)
- [ ] Modifies Neural Studio visualizer (`studio/`)
- [ ] None (internal logic / tests only)

## Verification & Testing

Explain how the changes were verified:

```bash
# Verify test suite and code hygiene
pytest tests/ -q
ruff check .
ruff format --check .
```

- [ ] Unit tests added / updated and passing green (100%)
- [ ] Tested locally with FastAPI TestClient or MockTransport
- [ ] No regression in token extraction, graph ingestion, or fact resolution

## Security & Hygiene Checklist (Mandatory)

- [ ] **Data Hygiene**: Verified ZERO private testing hostnames, internal IPs, API keys, or staging credentials in commits.
- [ ] Code follows project style guidelines (`ruff check .` and `ruff format --check .`).
- [ ] All public methods and endpoints have clear docstrings.
- [ ] Commit message follows Conventional Commits format.
