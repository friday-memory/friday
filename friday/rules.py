"""Friday Universal Agent Rule Adapter Engine.

Provides an extensible, multi-agent rule generator that equips any AI coding
agent (Claude Code, Cursor, Gemini, Copilot, Windsurf, Aider, Continue, or custom tools)
with a standardized Two-Way Zero-Amnesia Protocol via the Model Context Protocol (MCP).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class AgentTarget:
    """Specification for an AI coding agent instruction format."""

    key: str
    name: str
    default_filename: str
    description: str


# Canonical registry of supported agent environments
_REGISTRY: Dict[str, AgentTarget] = {
    "agents": AgentTarget(
        key="agents",
        name="Universal Agent Standard",
        default_filename="AGENTS.md",
        description="Standardized instruction file adopted by modern open-source agent runners (Cline, Roo, Codex)",
    ),
    "claude": AgentTarget(
        key="claude",
        name="Claude Code",
        default_filename="CLAUDE.md",
        description="Anthropic Claude Code CLI workspace instructions",
    ),
    "cursor": AgentTarget(
        key="cursor",
        name="Cursor IDE",
        default_filename=".cursorrules",
        description="Cursor AI editor workspace rules and directives",
    ),
    "gemini": AgentTarget(
        key="gemini",
        name="Google Gemini & Antigravity",
        default_filename="GEMINI.md",
        description="Google Gemini CLI and Antigravity IDE agent instructions",
    ),
    "copilot": AgentTarget(
        key="copilot",
        name="GitHub Copilot",
        default_filename=".github/copilot-instructions.md",
        description="GitHub Copilot workspace instructions and repository rules",
    ),
    "windsurf": AgentTarget(
        key="windsurf",
        name="Windsurf & Cascade",
        default_filename=".windsurfrules",
        description="Codeium Windsurf IDE and Cascade agent rules",
    ),
    "continue": AgentTarget(
        key="continue",
        name="Continue.dev",
        default_filename=".continue/rules.md",
        description="Continue.dev open-source AI extension instructions",
    ),
    "aider": AgentTarget(
        key="aider",
        name="Aider",
        default_filename="CONVENTIONS.md",
        description="Aider command-line coding assistant repository conventions",
    ),
}


def get_supported_agents() -> Dict[str, AgentTarget]:
    """Return a dictionary of all currently registered agent targets."""
    return dict(_REGISTRY)


def register_custom_agent(
    key: str,
    name: str,
    default_filename: str,
    description: str = "Custom agent instruction format",
) -> AgentTarget:
    """Register a custom agent target to make Friday rule generation extensible for any tool."""
    clean_key = key.strip().lower()
    target = AgentTarget(
        key=clean_key,
        name=name.strip(),
        default_filename=default_filename.strip(),
        description=description.strip(),
    )
    _REGISTRY[clean_key] = target
    return target


def render_rule(
    key: str,
    project_name: str = "",
    mcp_server: str = "friday",
    custom_instructions: str = "",
) -> str:
    """Render a clean, grounded, enterprise-grade Zero-Amnesia rule file for a given agent target."""
    clean_key = key.strip().lower()
    target = _REGISTRY.get(clean_key)
    if not target:
        supported = ", ".join(_REGISTRY.keys())
        raise ValueError(f"Unknown agent target '{key}'. Supported targets: {supported}")

    title_project = f" for {project_name}" if project_name else ""

    sections = [
        f"# AI Agent Core Directives — Persistent Memory Protocol{title_project}",
        "",
        f"> **ENVIRONMENT:** Configured for **{target.name}** interacting via the `{mcp_server}` Model Context Protocol (MCP) server.",
        "> **OBJECTIVE:** Enforce persistent state retention, eliminate session amnesia, and maintain verifiable project constraints across engineering sessions.",
        "",
        "---",
        "",
        "## 1. Two-Way Zero-Amnesia Protocol",
        "",
        "Every session must operate with bidirectional state validation through the Friday MCP server:",
        "",
        "### A. Pre-Task Read Gate (Turn Start — Ground-Truth Retrieval)",
        "- **Never guess** architecture decisions, database schemas, active endpoints, or past constraints from local context buffer alone.",
        f"- Before formulating a multi-step plan or executing code modifications, query the `{mcp_server}` server:",
        f"  - Use `{mcp_server}:get_context(query='<active task or component>')` to retrieve relevant architectural facts and constraints.",
        f"  - Use `{mcp_server}:memory_search(query='<technical topic>')` to surface prior implementation rationale and resolved trade-offs.",
        "",
        "### B. Post-Task Write Gate (Turn Finish — State Persistence)",
        f"- Whenever you complete a task, resolve a bug, introduce a schema change, or establish a new technical constraint, sync to `{mcp_server}` immediately.",
        "- Do not wait for the developer to request a memory update:",
        f"  - Record atomic, high-confidence constraints with `{mcp_server}:add_fact(content='...')`.",
        f"  - Record session summaries, rationale, and bug fixes with `{mcp_server}:add_memory(content='...')`.",
        "",
        "---",
        "",
        "## 2. Engineering & Quality Standards",
        "",
        "- **Deterministic Ground Truth**: Prefer structured facts and verified test outcomes over assumptions.",
        "- **Clean Code Hygiene**: Run test suites before considering tasks complete. Never leave unverified commits.",
        "- **Zero Promotional Fluff**: Maintain concise, precise, systems-engineering documentation. Avoid speculative hype, marketing jargon, or synthetic fluff.",
    ]

    if custom_instructions and custom_instructions.strip():
        sections.extend([
            "",
            "---",
            "",
            "## 3. Project-Specific Directives",
            "",
            custom_instructions.strip(),
        ])

    sections.append("")
    return "\n".join(sections)


def generate_rule_file(
    key: str,
    output_path: Optional[str | Path] = None,
    project_name: str = "",
    mcp_server: str = "friday",
    overwrite: bool = False,
    custom_instructions: str = "",
) -> Path:
    """Generate and write a specific agent rule file to disk."""
    clean_key = key.strip().lower()
    target = _REGISTRY.get(clean_key)
    if not target:
        supported = ", ".join(_REGISTRY.keys())
        raise ValueError(f"Unknown agent target '{key}'. Supported targets: {supported}")

    dest = Path(output_path) if output_path else Path(target.default_filename)

    if dest.exists() and not overwrite:
        raise FileExistsError(
            f"File '{dest}' already exists. Use overwrite=True (or --force in CLI) to overwrite."
        )

    # Ensure parent directory exists (e.g. .github/ or .continue/)
    if dest.parent and not dest.parent.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)

    content = render_rule(
        key=clean_key,
        project_name=project_name,
        mcp_server=mcp_server,
        custom_instructions=custom_instructions,
    )

    dest.write_text(content, encoding="utf-8")
    return dest


def generate_all_rules(
    output_dir: str | Path = ".",
    project_name: str = "",
    mcp_server: str = "friday",
    overwrite: bool = False,
    custom_instructions: str = "",
) -> List[Path]:
    """Generate rule files for all registered agent environments into the target directory."""
    base_dir = Path(output_dir)
    generated: List[Path] = []

    for key, target in _REGISTRY.items():
        dest = base_dir / target.default_filename
        if dest.exists() and not overwrite:
            continue
        created_path = generate_rule_file(
            key=key,
            output_path=dest,
            project_name=project_name,
            mcp_server=mcp_server,
            overwrite=overwrite,
            custom_instructions=custom_instructions,
        )
        generated.append(created_path)

    return generated
