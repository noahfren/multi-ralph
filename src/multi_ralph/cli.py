#!/usr/bin/env python3
"""Multi-Ralph CLI - Agent orchestration for autonomous development workflows."""

import argparse
import shutil
import sys
from pathlib import Path

from . import __version__


def get_package_claude_dir() -> Path:
    """Get the path to the .claude directory bundled with the package."""
    # The .claude directory is bundled inside the package as _data/.claude
    package_dir = Path(__file__).parent
    claude_dir = package_dir / "_data" / ".claude"
    
    # Fallback for development: check repo root
    if not claude_dir.exists():
        repo_root = package_dir.parent.parent
        claude_dir = repo_root / ".claude"
    
    return claude_dir


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize a project with multi-ralph Claude configuration files."""
    target_dir = Path(args.target).resolve()
    
    if not target_dir.exists():
        print(f"Error: Target directory does not exist: {target_dir}", file=sys.stderr)
        return 1
    
    target_claude_dir = target_dir / ".claude"
    source_claude_dir = get_package_claude_dir()
    
    if not source_claude_dir.exists():
        print(f"Error: Could not find .claude directory in package at {source_claude_dir}", file=sys.stderr)
        return 1
    
    # Check if .claude already exists
    if target_claude_dir.exists():
        if args.force:
            print(f"Removing existing .claude directory at {target_claude_dir}")
            shutil.rmtree(target_claude_dir)
        elif args.merge:
            print(f"Merging into existing .claude directory at {target_claude_dir}")
        else:
            print(f"Error: .claude directory already exists at {target_claude_dir}", file=sys.stderr)
            print("Use --force to overwrite or --merge to add missing files", file=sys.stderr)
            return 1
    
    # Copy the .claude directory
    if args.merge and target_claude_dir.exists():
        _merge_directories(source_claude_dir, target_claude_dir, args.verbose)
    else:
        if args.verbose:
            print(f"Copying {source_claude_dir} -> {target_claude_dir}")
        shutil.copytree(source_claude_dir, target_claude_dir)
    
    print(f"✓ Initialized multi-ralph in {target_dir}")
    print()
    print("Created files:")
    _print_tree(target_claude_dir, prefix="  ")
    print()
    print("Next steps:")
    print("  1. Review and customize agent configurations in .claude/agents/")
    print("  2. Initialize beads in your project: bd init")
    print("  3. Create tasks using: ralph orchestrate --list-agents")
    
    return 0


def _merge_directories(source: Path, target: Path, verbose: bool = False) -> None:
    """Merge source directory into target, only copying missing files."""
    for src_path in source.rglob("*"):
        if src_path.is_file():
            rel_path = src_path.relative_to(source)
            dst_path = target / rel_path
            
            if not dst_path.exists():
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                if verbose:
                    print(f"  Adding: {rel_path}")
                shutil.copy2(src_path, dst_path)
            elif verbose:
                print(f"  Skipping (exists): {rel_path}")


def _print_tree(directory: Path, prefix: str = "") -> None:
    """Print a directory tree."""
    paths = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name))
    
    for i, path in enumerate(paths):
        is_last = i == len(paths) - 1
        connector = "└── " if is_last else "├── "
        
        print(f"{prefix}{connector}{path.name}")
        
        if path.is_dir():
            extension = "    " if is_last else "│   "
            _print_tree(path, prefix + extension)


def cmd_orchestrate(args: argparse.Namespace) -> int:
    """Run the agent orchestrator."""
    # Import here to avoid circular imports and speed up CLI startup
    from .orchestrate import main as orchestrate_main
    
    # Build sys.argv for the orchestrator
    sys.argv = ["multi-ralph orchestrate"] + args.orchestrate_args
    orchestrate_main()
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    """Print version information."""
    print(f"multi-ralph {__version__}")
    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="multi-ralph",
        description="Multi-agent orchestration framework for autonomous development workflows",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # init command
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize a project with multi-ralph Claude configuration files",
        description="Copy .claude/agents and .claude/skills to a target project directory",
    )
    init_parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Target project directory (default: current directory)",
    )
    init_parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite existing .claude directory",
    )
    init_parser.add_argument(
        "-m", "--merge",
        action="store_true",
        help="Merge with existing .claude directory (only add missing files)",
    )
    init_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output",
    )
    init_parser.set_defaults(func=cmd_init)
    
    # orchestrate command
    orch_parser = subparsers.add_parser(
        "orchestrate",
        help="Run the agent orchestrator",
        description="Orchestrate Claude Code agents to work on beads tasks",
    )
    orch_parser.add_argument(
        "orchestrate_args",
        nargs="*",
        help="Arguments to pass to the orchestrator",
    )
    orch_parser.set_defaults(func=cmd_orchestrate)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
