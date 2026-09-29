# Contributing to Friday

Thank you for your interest in contributing to Friday Memory. We welcome bug reports, architectural improvements, new agent adapters, and documentation updates.

## Development Setup

### Prerequisites
- Python 3.11+
- Git

### Quick Start
```bash
git clone https://github.com/friday-memory/friday.git
cd friday

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install ruff pytest anyio
```

## Running Tests & Linters

Every PR must pass 100% green on all tests and lint checks before merging:

```bash
# 1. Run unit test suite
pytest tests/ -q

# 2. Run Ruff linter
ruff check .

# 3. Verify code formatting
ruff format --check .
```

## Contribution Workflow

1. **Fork the Repository**: Create your fork on GitHub.
2. **Create a Feature Branch**:
   ```bash
   git checkout -b feat/your-feature-name
   ```
3. **Write Tests**: Add test coverage under `tests/` for any new functionality or bug fixes.
4. **Data Privacy & Security Hygiene (Mandatory)**:
   - **Never commit** private IP addresses, internal test hostnames, API keys, staging URLs, or personal deployment credentials in commits or code diffs.
   - Always use mock interfaces (`httpx.MockTransport`), environment variable overrides, or sanitized dummy strings (`http://localhost:8000`).
5. **Commit Changes**: Use [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` New features or tools
   - `fix:` Bug fixes
   - `docs:` Documentation updates
   - `refactor:` Code restructuring without behavior changes
   - `perf:` Performance improvements
   - `chore:` Dependency or CI updates
6. **Open a Pull Request**: Submit your PR with a completed checklist from the PR template.

## Architectural Conventions

- **State Persistence**: Memory layers must remain modular:
  - Facts Ledger (Layer 2): Strict deterministic ground truths with project scoping and auto-supersede.
  - Semantic Retrieval (Layer 3): Vector embeddings via Mem0 / ChromaDB.
  - Knowledge Graph (Layer 4): Multi-hop relational entity relationships and blast-radius traversal (`get_blast_radius`).
- **Protocol Compliance**: Tool schemas must adhere strictly to the Model Context Protocol (MCP) standard.
- **Packaging Integrity**: Only official SDK and CLI files in `friday/` should be included in build distributions.

## Questions & Discussions

For technical discussions, feature proposals, and architectural questions, visit [GitHub Discussions](https://github.com/friday-memory/friday/discussions).
