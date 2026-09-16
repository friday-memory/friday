# Contributing to Friday

Thank you for helping make AI coding agents smarter! 🧠

## Quick Start

```bash
git clone https://github.com/itskie/friday.git
cd friday
cp .env.example .env  # fill in your keys
pip install -r requirements.txt
python -m pytest tests/ -q  # all green? you're ready
```

## How to Contribute

1. **Fork** the repo
2. **Create** a feature branch: `git checkout -b feat/your-feature`
3. **Write** tests for your change
4. **Ensure** all tests pass: `python -m pytest tests/ -q`
5. **Commit** with a clear message: `git commit -m "feat: add X"`
6. **Open** a Pull Request

## Commit Convention

| Prefix | Use for |
|:---|:---|
| `feat:` | New features |
| `fix:` | Bug fixes |
| `docs:` | Documentation only |
| `refactor:` | Code cleanup (no behavior change) |
| `test:` | Adding tests |
| `chore:` | Build, CI, dependency updates |

## Code Style

- Python: follow PEP 8, type hints everywhere
- Keep functions small and focused
- Every public function needs a docstring

## Reporting Bugs

Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md).  
Include logs, OS, and steps to reproduce.

## Questions?

Open a [Discussion](https://github.com/itskie/friday/discussions) — we're friendly! 😊
