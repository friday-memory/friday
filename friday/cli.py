"""Friday Command Line Interface (CLI)."""

from __future__ import annotations

import argparse
import sys

from friday.rules import (
    generate_all_rules,
    generate_rule_file,
    get_supported_agents,
    register_custom_agent,
)


def _cmd_rules_list(args: argparse.Namespace) -> int:
    agents = get_supported_agents()
    print("\nSupported AI Coding Agent Environments:")
    print("-" * 75)
    print(f"{'KEY':<10} | {'TARGET AGENT':<26} | {'DEFAULT FILE':<28}")
    print("-" * 75)
    for key, target in agents.items():
        print(f"{key:<10} | {target.name:<26} | {target.default_filename:<28}")
    print("-" * 75)
    print("Run `friday rules generate --target <key>` or `friday rules generate --all`\n")
    return 0


def _cmd_rules_generate(args: argparse.Namespace) -> int:
    if args.all:
        print(f"Generating rule files for all supported agents in '{args.output_dir}'...")
        try:
            created = generate_all_rules(
                output_dir=args.output_dir,
                project_name=args.project,
                mcp_server=args.mcp,
                overwrite=args.force,
            )
            if not created:
                print("No files created (existing files found; use --force to overwrite).")
            else:
                for path in created:
                    print(f"  ✓ Created: {path}")
                print(f"\nSuccessfully generated {len(created)} rule files.")
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    if not args.target:
        print("Error: Specify --target <agent_key> or use --all to generate all formats.", file=sys.stderr)
        return 1

    try:
        path = generate_rule_file(
            key=args.target,
            output_path=args.output,
            project_name=args.project,
            mcp_server=args.mcp,
            overwrite=args.force,
        )
        print(f"✓ Generated rule file for '{args.target}' at: {path}")
        return 0
    except (FileExistsError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_rules_custom(args: argparse.Namespace) -> int:
    try:
        register_custom_agent(
            key=args.key,
            name=args.name,
            default_filename=args.file,
            description=args.desc or f"Custom rule for {args.name}",
        )
        path = generate_rule_file(
            key=args.key,
            output_path=args.output,
            project_name=args.project,
            mcp_server=args.mcp,
            overwrite=args.force,
        )
        print(f"✓ Custom agent '{args.name}' registered and rule file generated at: {path}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="friday",
        description="Friday CLI — Universal Persistent Memory & Agent Toolkit",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # `friday rules ...`
    rules_parser = subparsers.add_parser("rules", help="Manage and generate agent rule files")
    rules_sub = rules_parser.add_subparsers(dest="rules_action", help="Rule actions")

    # `friday rules list`
    list_p = rules_sub.add_parser("list", help="List all supported agent environments")
    list_p.set_defaults(func=_cmd_rules_list)

    # `friday rules generate`
    gen_p = rules_sub.add_parser("generate", help="Generate zero-amnesia rule files")
    gen_p.add_argument("--target", "-t", help="Agent target key (e.g. claude, cursor, gemini, copilot)")
    gen_p.add_argument("--all", "-a", action="store_true", help="Generate rules for all supported agents")
    gen_p.add_argument("--output", "-o", help="Custom output path for the rule file")
    gen_p.add_argument("--output-dir", default=".", help="Directory to output files when using --all (default: .)")
    gen_p.add_argument("--project", "-p", default="", help="Project name to include in header")
    gen_p.add_argument("--mcp", "-m", default="friday", help="MCP server name identifier (default: friday)")
    gen_p.add_argument("--force", "-f", action="store_true", help="Overwrite existing files")
    gen_p.set_defaults(func=_cmd_rules_generate)

    # `friday rules custom`
    cust_p = rules_sub.add_parser("custom", help="Generate rules for an arbitrary custom tool")
    cust_p.add_argument("--key", "-k", required=True, help="Unique identifier key (e.g. devin, mybot)")
    cust_p.add_argument("--name", "-n", required=True, help="Display name for the agent (e.g. 'Devin AI')")
    cust_p.add_argument("--file", required=True, help="Default rule filename (e.g. .devin/rules.md)")
    cust_p.add_argument("--desc", default="", help="Short description of the custom tool")
    cust_p.add_argument("--output", "-o", help="Custom output path")
    cust_p.add_argument("--project", "-p", default="", help="Project name")
    cust_p.add_argument("--mcp", "-m", default="friday", help="MCP server name")
    cust_p.add_argument("--force", "-f", action="store_true", help="Overwrite existing files")
    cust_p.set_defaults(func=_cmd_rules_custom)

    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
