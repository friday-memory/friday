"""Tests for the Friday Universal Agent Rule Adapter Engine & CLI."""

import io
import sys
from pathlib import Path
import pytest

from friday.rules import (
    AgentTarget,
    generate_all_rules,
    generate_rule_file,
    get_supported_agents,
    register_custom_agent,
    render_rule,
)
from friday.cli import main


def test_get_supported_agents():
    agents = get_supported_agents()
    expected_keys = {"agents", "claude", "cursor", "gemini", "copilot", "windsurf", "continue", "aider"}
    assert expected_keys.issubset(set(agents.keys()))
    assert isinstance(agents["claude"], AgentTarget)
    assert agents["claude"].default_filename == "CLAUDE.md"
    assert agents["cursor"].default_filename == ".cursorrules"
    assert agents["gemini"].default_filename == "GEMINI.md"


def test_render_rule_contains_core_protocol():
    content = render_rule("claude", project_name="TestProject", mcp_server="friday")
    assert "Two-Way Zero-Amnesia Protocol" in content
    assert "Pre-Task Read Gate" in content
    assert "Post-Task Write Gate" in content
    assert "friday:get_context" in content
    assert "friday:add_memory" in content
    assert "TestProject" in content
    assert "Zero Promotional Fluff" in content


def test_render_rule_with_custom_instructions():
    content = render_rule("cursor", custom_instructions="Custom Rule: Always use pytest.")
    assert "Project-Specific Directives" in content
    assert "Custom Rule: Always use pytest." in content


def test_render_rule_unknown_target():
    with pytest.raises(ValueError, match="Unknown agent target 'nonexistent'"):
        render_rule("nonexistent")


def test_generate_rule_file(tmp_path):
    dest = tmp_path / "CLAUDE.md"
    path = generate_rule_file("claude", output_path=dest, project_name="App")
    assert path.exists()
    assert "Claude Code" in path.read_text(encoding="utf-8")

    # Trying to overwrite without flag should raise FileExistsError
    with pytest.raises(FileExistsError):
        generate_rule_file("claude", output_path=dest)

    # Overwrite flag works
    generate_rule_file("claude", output_path=dest, overwrite=True)
    assert dest.exists()


def test_generate_all_rules(tmp_path):
    created = generate_all_rules(output_dir=tmp_path)
    assert len(created) >= 8
    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / ".cursorrules").exists()
    assert (tmp_path / "GEMINI.md").exists()
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".github" / "copilot-instructions.md").exists()
    assert (tmp_path / ".windsurfrules").exists()
    assert (tmp_path / ".continue" / "rules.md").exists()
    assert (tmp_path / "CONVENTIONS.md").exists()


def test_register_custom_agent(tmp_path):
    register_custom_agent(
        key="custom_bot",
        name="Custom Bot 9000",
        default_filename="CUSTOM_BOT.md",
        description="A specialized in-house agent",
    )
    dest = tmp_path / "CUSTOM_BOT.md"
    path = generate_rule_file("custom_bot", output_path=dest)
    assert path.exists()
    assert "Custom Bot 9000" in path.read_text(encoding="utf-8")


def test_cli_rules_list(capsys):
    ret = main(["rules", "list"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Supported AI Coding Agent Environments:" in captured.out
    assert "claude" in captured.out
    assert "cursor" in captured.out
    assert "gemini" in captured.out


def test_cli_rules_generate(tmp_path):
    out_file = tmp_path / "CLAUDE.md"
    ret = main(["rules", "generate", "--target", "claude", "--output", str(out_file)])
    assert ret == 0
    assert out_file.exists()


def test_cli_rules_generate_all(tmp_path):
    ret = main(["rules", "generate", "--all", "--output-dir", str(tmp_path)])
    assert ret == 0
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".cursorrules").exists()


def test_cli_rules_custom(tmp_path):
    out_file = tmp_path / ".custom" / "instructions.txt"
    ret = main([
        "rules",
        "custom",
        "--key", "myagent",
        "--name", "My Special Agent",
        "--file", ".custom/instructions.txt",
        "--output", str(out_file),
    ])
    assert ret == 0
    assert out_file.exists()
    assert "My Special Agent" in out_file.read_text(encoding="utf-8")
