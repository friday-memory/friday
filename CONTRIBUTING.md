# Contributing to Friday

Thank you for your interest in contributing to Friday. We welcome bug reports, architectural improvements, new integrations, and documentation updates.

## Development Setup

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- Git

### Quick Start
```bash
git clone https://github.com/friday-memory/friday.git
cd friday
cp .env.example .env

# Install dependencies
make install
# or: pip install -r requirements.txt

# Run test suite
make test
# or: python -m pytest tests/ -v
```

## Contribution Workflow

1. **Fork the Repository**: Create your fork on GitHub.
2. **Create a Feature Branch**:
   ```bash
   git checkout -b feat/your-feature-name
   ```
3. **Write Tests**: Add test coverage under `tests/` for any new functionality or bug fixes.
4. **Verify Standards**:
   ```bash
   make test
   make lint
   ```
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
  - Facts Ledger: Strict deterministic ground truths.
  - Episodic Memory: Semantic vector embeddings.
  - Graph Topology: Relational entity relationships.
- **Protocol Compliance**: Tool schemas must adhere strictly to the Model Context Protocol (MCP) standard.
- **Performance**: Operations in the hot path of MCP tool execution should maintain sub-100ms response latencies where possible.

## Questions & Discussions

For technical discussions, feature proposals, and architectural questions, visit [GitHub Discussions](https://github.com/friday-memory/friday/discussions).
