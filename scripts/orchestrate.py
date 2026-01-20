#!/usr/bin/env python3
"""
Beads Agent Orchestrator

Runs a loop that prioritizes tasks by hierarchy depth (deepest first):
1. Leaf tasks (depth >= 2, e.g., fb-ft0.1.1) - actual implementation work
2. Parent tasks (depth 1, e.g., fb-ft0.1) - auto-closed when children done
3. Epics (depth 0, e.g., fb-ft0) - auto-closed when children done

Hierarchy is determined by dot notation in task IDs:
- fb-ft0 (epic, depth 0)
- fb-ft0.1 (task, depth 1)
- fb-ft0.1.1 (subtask/leaf, depth 2)

For each iteration:
1. Fetches ready tasks and sorts by depth (deepest first)
2. For leaf tasks: runs the appropriate agent to do implementation work
3. For parent tasks/epics: auto-closes them (work already done in leaves)
4. Marks task complete and moves to the next one

Agent configurations are stored in .claude/agents/ as markdown files with
YAML frontmatter. Each agent can have its own:
- System prompt (markdown body)
- Tools (allowed/disallowed)
- Model selection
- Skills
- MCP servers (via project settings)
"""

import subprocess
import json
import sys
import os
import argparse
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum


# Default timeout for agent execution (30 minutes)
DEFAULT_AGENT_TIMEOUT_SECONDS = 1800


# Agent type to file mapping
# These correspond to files in .claude/agents/
AGENT_TYPE_TO_FILE = {
    "frontend": "dev-frontend",
    "backend": "dev-backend",
    "ai": "dev-ai",
    "sdet": "dev-sdet",
    "qa": "dev-qa",
    "general": "dev-general",
}

# Fallback prompts if agent files don't exist
FALLBACK_PROMPTS = {
    "frontend": "You are a Frontend Development Agent. Focus on UI components, client-side logic, and user experience.",
    "backend": "You are a Backend Development Agent. Focus on APIs, server logic, and database operations.",
    "ai": "You are an AI Specialization Agent. Focus on prompt engineering, LLM integration, and AI pipelines.",
    "sdet": "You are an SDET Agent. Focus on test infrastructure, E2E testing, and automation frameworks.",
    "qa": "You are a QA Validation Agent. Focus on test execution, acceptance criteria verification, and bug reporting.",
    "general": "You are a General Development Agent. Complete the assigned task following best practices.",
}


@dataclass
class BeadTask:
    """Represents a beads task/issue"""
    id: str
    title: str
    description: str
    labels: list[str]
    acceptance: str
    status: str
    task_type: str
    parent_id: Optional[str] = None

    @property
    def agent_type(self) -> str:
        """Determine agent type from labels"""
        for label in self.labels:
            if label.startswith("agent:"):
                agent = label.split(":")[1]
                if agent in AGENT_TYPE_TO_FILE:
                    return agent
        return "general"

    @property
    def agent_name(self) -> str:
        """Get the Claude Code agent name for this task"""
        return AGENT_TYPE_TO_FILE.get(self.agent_type, "dev-general")


def run_command(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            check=False
        )
        return result
    except Exception as e:
        print(f"Error running command {' '.join(cmd)}: {e}", file=sys.stderr)
        raise


def get_project_root() -> Path:
    """Find the project root (where .claude/ directory is)"""
    # Start from current directory and walk up
    current = Path.cwd()
    while current != current.parent:
        if (current / ".claude").is_dir():
            return current
        current = current.parent
    # Fallback to cwd
    return Path.cwd()


def get_agents_dir() -> Path:
    """Get the .claude/agents directory path"""
    return get_project_root() / ".claude" / "agents"


def agent_exists(agent_name: str) -> bool:
    """Check if an agent configuration file exists"""
    agents_dir = get_agents_dir()
    return (agents_dir / f"{agent_name}.md").exists()


def list_available_agents() -> list[str]:
    """List all available agent configurations"""
    agents_dir = get_agents_dir()
    if not agents_dir.exists():
        return []
    return [f.stem for f in agents_dir.glob("*.md")]


def get_ready_tasks(
    label_filter: Optional[str] = None,
    limit: int = 10,
) -> list[BeadTask]:
    """Fetch ready tasks from beads"""
    cmd = ["bd", "ready", "--json", "--limit", str(limit)]

    if label_filter:
        cmd.extend(["--label", label_filter])

    result = run_command(cmd)

    if result.returncode != 0:
        print(f"Error fetching ready tasks: {result.stderr}", file=sys.stderr)
        return []

    if not result.stdout.strip():
        return []

    try:
        data = json.loads(result.stdout)
        tasks = []

        # Handle both single object and array responses
        items = data if isinstance(data, list) else [data]

        for item in items:
            task = BeadTask(
                id=item.get("id", ""),
                title=item.get("title", ""),
                description=item.get("description", ""),
                labels=item.get("labels", []),
                acceptance=item.get("acceptance", ""),
                status=item.get("status", ""),
                task_type=item.get("issue_type", item.get("type", "task")),
                parent_id=item.get("parent"),  # Note: field is "parent", not "parent_id"
            )
            tasks.append(task)

        return tasks
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}", file=sys.stderr)
        print(f"Raw output: {result.stdout}", file=sys.stderr)
        return []


def get_in_progress_tasks(
    label_filter: Optional[str] = None,
    limit: int = 10,
) -> list[BeadTask]:
    """Fetch in-progress tasks from beads"""
    cmd = ["bd", "list", "--status", "in_progress", "--json", "--limit", str(limit)]

    if label_filter:
        cmd.extend(["--label", label_filter])

    result = run_command(cmd)

    if result.returncode != 0:
        print(f"Error fetching in-progress tasks: {result.stderr}", file=sys.stderr)
        return []

    if not result.stdout.strip():
        return []

    try:
        data = json.loads(result.stdout)
        tasks = []

        # Handle both single object and array responses
        items = data if isinstance(data, list) else [data]

        for item in items:
            task = BeadTask(
                id=item.get("id", ""),
                title=item.get("title", ""),
                description=item.get("description", ""),
                labels=item.get("labels", []),
                acceptance=item.get("acceptance", ""),
                status=item.get("status", ""),
                task_type=item.get("issue_type", item.get("type", "task")),
                parent_id=item.get("parent"),
            )
            tasks.append(task)

        return tasks
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}", file=sys.stderr)
        print(f"Raw output: {result.stdout}", file=sys.stderr)
        return []


def get_hierarchy_depth(task: BeadTask) -> int:
    """
    Determine hierarchy depth from task ID.

    IDs follow pattern: prefix-XXX.Y.Z where dots indicate depth.
    - fb-ft0 -> depth 0 (epic)
    - fb-ft0.1 -> depth 1 (task)
    - fb-ft0.1.1 -> depth 2 (subtask)
    """
    # Count dots after the prefix (e.g., "fb-ft0.1.2" has 2 dots = depth 2)
    task_id = task.id
    # Find the base ID part after prefix
    if "-" in task_id:
        suffix = task_id.split("-", 1)[1]
        return suffix.count(".")
    return 0


def is_leaf_task(task: BeadTask) -> bool:
    """
    Check if task is a leaf (no children / deepest level).

    Leaf tasks are where actual implementation work should happen.
    Non-leaf tasks (epics, parent tasks) should just be closed once children are done.
    """
    # Epics are never leaf tasks
    if task.task_type == "epic":
        return False

    # Tasks with depth >= 2 (e.g., fb-ft0.1.1) are leaf subtasks
    # Tasks with depth 1 that aren't epics could be leaf if no subtasks exist
    # For safety, treat depth >= 2 as definite leaves
    return get_hierarchy_depth(task) >= 2


def get_child_tasks(parent_id: str) -> list[BeadTask]:
    """
    Fetch direct child tasks of a given parent task.

    Uses bd list with --parent filter to find children.
    Includes --all to find closed children as well.
    """
    cmd = ["bd", "list", "--parent", parent_id, "--all", "--json", "--limit", "100"]

    result = run_command(cmd)

    if result.returncode != 0:
        print(f"Error fetching children of {parent_id}: {result.stderr}", file=sys.stderr)
        return []

    if not result.stdout.strip():
        return []

    try:
        data = json.loads(result.stdout)
        tasks = []

        items = data if isinstance(data, list) else [data]

        for item in items:
            task = BeadTask(
                id=item.get("id", ""),
                title=item.get("title", ""),
                description=item.get("description", ""),
                labels=item.get("labels", []),
                acceptance=item.get("acceptance", ""),
                status=item.get("status", ""),
                task_type=item.get("issue_type", item.get("type", "task")),
                parent_id=item.get("parent"),
            )
            tasks.append(task)

        return tasks
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}", file=sys.stderr)
        return []


def all_children_complete(parent_id: str) -> bool:
    """
    Check if all children of a task are complete (status = done or closed).

    Returns True if:
    - All children have status 'done' or 'closed', OR
    - The task has no children (leaf task)
    """
    children = get_child_tasks(parent_id)

    if not children:
        # No children means it's a leaf or has no subtasks
        return True

    for child in children:
        if child.status not in ("done", "closed"):
            return False

    return True


def get_next_prioritized_task(
    label_filter: Optional[str] = None,
    resume: bool = False,
) -> tuple[Optional[BeadTask], bool]:
    """
    Get the next task, prioritizing by hierarchy depth.

    When resume=True, in-progress tasks are checked first before ready tasks.

    Priority order (deepest first):
    1. Leaf subtasks (depth >= 2) - actual implementation work happens here
    2. Tasks (depth 1) - should be closeable once subtasks are done
    3. Epics (depth 0) - should be closeable once tasks are done

    For non-leaf in-progress tasks, we verify children are complete before
    returning them. If children aren't complete, we skip the non-leaf task
    so that children can be processed first.

    Returns (task, is_resumed) where is_resumed indicates if the task was in-progress.
    """
    # When resuming, first check for in-progress tasks
    if resume:
        in_progress = get_in_progress_tasks(label_filter=label_filter, limit=50)
        if in_progress:
            # Sort by depth descending (deepest/leaf tasks first), then by ID
            in_progress.sort(key=lambda t: (-get_hierarchy_depth(t), t.id))

            # Find a suitable task to resume
            for task in in_progress:
                if is_leaf_task(task):
                    # Leaf tasks can always be resumed for actual work
                    return task, True
                else:
                    # Non-leaf tasks: only return if all children are complete
                    # Otherwise, skip so children can be processed first
                    if all_children_complete(task.id):
                        return task, True
                    else:
                        print(f"  Skipping in-progress non-leaf task {task.id} (children not complete)")

    # Fall back to ready tasks
    tasks = get_ready_tasks(label_filter=label_filter, limit=50)

    if not tasks:
        return None, False

    # Sort by depth descending (deepest/leaf tasks first), then by ID for consistency
    tasks.sort(key=lambda t: (-get_hierarchy_depth(t), t.id))

    return tasks[0], False


def get_task_details(task_id: str) -> Optional[BeadTask]:
    """Get full details for a specific task"""
    result = run_command(["bd", "show", task_id, "--json"])

    if result.returncode != 0:
        print(f"Error fetching task {task_id}: {result.stderr}", file=sys.stderr)
        return None

    try:
        data = json.loads(result.stdout)
        # bd show returns an array even for single items
        item = data[0] if isinstance(data, list) else data
        return BeadTask(
            id=item.get("id", ""),
            title=item.get("title", ""),
            description=item.get("description", ""),
            labels=item.get("labels", []),
            acceptance=item.get("acceptance", ""),
            status=item.get("status", ""),
            task_type=item.get("issue_type", item.get("type", "task")),
            parent_id=item.get("parent_id"),
        )
    except json.JSONDecodeError as e:
        print(f"Error parsing task details: {e}", file=sys.stderr)
        return None


def claim_task(task_id: str) -> bool:
    """Atomically claim a task (set to in_progress and assign)"""
    result = run_command(["bd", "update", task_id, "--claim"])

    if result.returncode != 0:
        print(f"Failed to claim task {task_id}: {result.stderr}", file=sys.stderr)
        return False

    print(f"Claimed task: {task_id}")
    return True


def complete_task(task_id: str, session_id: Optional[str] = None) -> bool:
    """Mark a task as closed"""
    cmd = ["bd", "update", task_id, "--status", "closed"]

    if session_id:
        cmd.extend(["--session", session_id])

    result = run_command(cmd)

    if result.returncode != 0:
        print(f"Failed to complete task {task_id}: {result.stderr}", file=sys.stderr)
        return False

    print(f"Completed task: {task_id}")
    return True


def fail_task(task_id: str, reason: str) -> bool:
    """Mark a task as blocked/failed"""
    result = run_command([
        "bd", "update", task_id,
        "--status", "blocked",
        "--notes", f"Agent failed: {reason}"
    ])

    if result.returncode != 0:
        print(f"Failed to update task {task_id}: {result.stderr}", file=sys.stderr)
        return False

    print(f"Marked task as blocked: {task_id}")
    return True


def build_claude_prompt(task: BeadTask) -> str:
    """Build the prompt to send to Claude Code"""
    prompt_parts = [
        f"## Task: {task.title}",
        f"**Task ID:** {task.id}",
        "",
        "## Description",
        task.description or "(No description provided)",
        "",
    ]

    if task.acceptance:
        prompt_parts.extend([
            "## Acceptance Criteria",
            task.acceptance,
            "",
        ])

    prompt_parts.extend([
        "## Instructions",
        "1. Read the design document referenced in the description above",
        "2. Implement the requirements as specified",
        "3. Ensure all acceptance criteria are met",
        "4. Run relevant tests to verify your implementation",
        "",
        "## IMPORTANT: Progress Tracking",
        "",
        "You have a **30-minute timeout**. To ensure your work isn't lost if time runs out:",
        "",
        "**Record progress notes periodically** using the beads CLI:",
        "```bash",
        f"bd update {task.id} --notes \"Progress: <describe what you've completed and what remains>\"",
        "```",
        "",
        "**When to record progress:**",
        "- After completing each major step (reading design doc, writing tests, implementing code)",
        "- After every 5-10 minutes of work",
        "- Before starting any long-running operation (builds, test suites)",
        "- When you encounter blockers or make key decisions",
        "",
        "**What to include in progress notes:**",
        "- Files you've created or modified",
        "- Tests written and their status",
        "- Key implementation decisions made",
        "- What remains to be done",
        "- Any blockers or issues encountered",
        "",
        "This ensures that if a fresh agent picks up this task, it can continue from where you left off.",
        "",
        "Begin working on this task now.",
    ])

    return "\n".join(prompt_parts)


def run_agent(
    task: BeadTask,
    dry_run: bool = False,
    model_override: Optional[str] = None,
    timeout_seconds: int = DEFAULT_AGENT_TIMEOUT_SECONDS,
) -> tuple[bool, Optional[str], bool]:
    """
    Launch Claude Code with the appropriate agent configuration.

    Uses --agent flag if agent config exists, otherwise falls back to
    --append-system-prompt with built-in prompts.

    Args:
        task: The BeadTask to work on
        dry_run: If True, don't actually run the agent
        model_override: Override the model from agent config
        timeout_seconds: Maximum time to allow the agent to run (default: 30 min)

    Returns:
        (success, session_id, timed_out) - timed_out indicates if the agent was killed due to timeout
    """
    agent_type = task.agent_type
    agent_name = task.agent_name
    task_prompt = build_claude_prompt(task)

    # Check if agent config exists
    use_agent_file = agent_exists(agent_name)

    print(f"\n{'='*60}")
    print(f"Running {agent_type} agent on task: {task.id}")
    print(f"Title: {task.title}")
    print(f"Agent config: {agent_name}.md" if use_agent_file else f"Using fallback prompt")
    print(f"Timeout: {timeout_seconds // 60} minutes ({timeout_seconds} seconds)")
    print(f"{'='*60}\n")

    if dry_run:
        print("[DRY RUN] Would execute Claude Code with:")
        print(f"  Agent type: {agent_type}")
        print(f"  Agent name: {agent_name}")
        print(f"  Config file exists: {use_agent_file}")
        if model_override:
            print(f"  Model override: {model_override}")
        print(f"  Timeout: {timeout_seconds} seconds")
        print(f"  Task prompt length: {len(task_prompt)} chars")
        return True, None, False

    # Build Claude Code command
    cmd = [
        "claude",
        "--print",  # Non-interactive mode
        "--output-format", "json",
        "--dangerously-skip-permissions",  # Trust all tools
    ]

    if use_agent_file:
        # Use the agent configuration file
        cmd.extend(["--agent", agent_name])
    else:
        # Fall back to inline system prompt
        fallback_prompt = FALLBACK_PROMPTS.get(agent_type, FALLBACK_PROMPTS["general"])
        cmd.extend(["--append-system-prompt", fallback_prompt])

    # Model override (if specified, overrides agent config)
    if model_override:
        cmd.extend(["--model", model_override])

    # Add the task prompt
    cmd.append(task_prompt)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )

        if result.returncode != 0:
            print(f"Claude Code exited with error: {result.returncode}")
            print(f"Stderr: {result.stderr}")
            return False, None, False

        # Try to parse the JSON output for session ID
        session_id = None
        try:
            output = json.loads(result.stdout)
            session_id = output.get("session_id")

            # Print the result
            if "result" in output:
                print("\n--- Agent Output ---")
                print(output["result"])
                print("--- End Output ---\n")
        except json.JSONDecodeError:
            # If not JSON, just print the raw output
            print("\n--- Agent Output ---")
            print(result.stdout)
            print("--- End Output ---\n")

        return True, session_id, False

    except subprocess.TimeoutExpired:
        print(f"\n{'!'*60}")
        print(f"TIMEOUT: Agent exceeded {timeout_seconds // 60} minute limit")
        print(f"Task {task.id} will be marked for retry with progress notes")
        print(f"{'!'*60}\n")
        return False, None, True

    except Exception as e:
        print(f"Error running Claude Code: {e}", file=sys.stderr)
        return False, None, False


def orchestrate(
    max_iterations: Optional[int] = None,
    label_filter: Optional[str] = None,
    dry_run: bool = False,
    model_override: Optional[str] = None,
    auto_complete: bool = True,
    resume: bool = False,
    timeout_seconds: int = DEFAULT_AGENT_TIMEOUT_SECONDS,
) -> int:
    """
    Main orchestration loop with hierarchy depth prioritization.

    Prioritizes by depth (deepest first):
    1. Leaf tasks (depth >= 2) - agents do actual implementation work
    2. Parent tasks (depth 1) - auto-closed when ready (children done)
    3. Epics (depth 0) - auto-closed when ready (children done)

    When resume=True, in-progress tasks are processed first before ready tasks.

    Args:
        max_iterations: Maximum number of tasks to process (None = unlimited)
        label_filter: Only process tasks with this label
        dry_run: If True, don't actually run agents or update tasks
        model_override: Override the model specified in agent configs
        auto_complete: If True, automatically mark tasks as done on success
        resume: If True, pick up in-progress tasks before moving to ready tasks
        timeout_seconds: Maximum time for each agent execution (default: 30 min)

    Returns:
        Number of tasks processed
    """
    iteration = 0

    # Show available agents
    available_agents = list_available_agents()

    print("Starting Beads Agent Orchestrator")
    print(f"  Project root: {get_project_root()}")
    print(f"  Available agents: {', '.join(available_agents) if available_agents else '(none - using fallbacks)'}")
    print(f"  Label filter: {label_filter or '(none)'}")
    print(f"  Max iterations: {max_iterations or 'unlimited'}")
    print(f"  Model: {model_override}")
    print(f"  Timeout: {timeout_seconds // 60} minutes ({timeout_seconds} seconds)")
    print(f"  Dry run: {dry_run}")
    print(f"  Auto-complete: {auto_complete}")
    print(f"  Resume mode: {resume}")
    print()

    while True:
        # Check iteration limit
        if max_iterations is not None and iteration >= max_iterations:
            print(f"\nReached max iterations ({max_iterations})")
            break

        # Get next task with prioritization: subtasks -> tasks -> epics
        # When resuming, in-progress tasks are checked first
        if resume:
            print(f"\n[Iteration {iteration + 1}] Checking for in-progress tasks, then ready tasks...")
        else:
            print(f"\n[Iteration {iteration + 1}] Fetching ready tasks (priority: subtask > task > epic)...")

        task, is_resumed = get_next_prioritized_task(label_filter=label_filter, resume=resume)

        if not task:
            print("No tasks found. Orchestration complete.")
            break

        # Get full task details
        full_task = get_task_details(task.id)
        if full_task:
            task = full_task

        depth = get_hierarchy_depth(task)
        is_leaf = is_leaf_task(task)

        status_note = " (RESUMING)" if is_resumed else ""
        print(f"Found task: {task.id} - {task.title}{status_note}")
        print(f"  Type: {task.task_type}, Depth: {depth}, Leaf: {is_leaf}")
        print(f"  Labels: {', '.join(task.labels) or '(none)'}")
        print(f"  Agent: {task.agent_type} -> {task.agent_name}")

        # For non-leaf tasks (epics, parent tasks): work should already be done in subtasks
        # Just close them - children are verified complete by get_next_prioritized_task
        if not is_leaf:
            print(f"  -> Parent task detected (depth {depth}). Children should be complete.")
            print(f"     Closing without running agent (work done in leaf subtasks).")

            if not dry_run:
                # Only claim if not already in progress
                if not is_resumed:
                    if not claim_task(task.id):
                        print(f"Could not claim task {task.id}, skipping...")
                        iteration += 1
                        continue
                if auto_complete:
                    if not complete_task(task.id, session_id=None):
                        print(f"Failed to close parent task {task.id}, marking as blocked to prevent infinite loop")
                        fail_task(task.id, "Failed to mark task as done")
            else:
                print("[DRY RUN] Would claim and close parent task")

            iteration += 1
            continue

        # For leaf tasks: run the agent to do actual implementation work
        # Claim the task (skip if already in progress / resuming)
        if not dry_run:
            if is_resumed:
                print(f"  Resuming in-progress task (already claimed)")
            else:
                if not claim_task(task.id):
                    print(f"Could not claim task {task.id}, skipping...")
                    iteration += 1
                    continue
        else:
            print("[DRY RUN] Would claim task" if not is_resumed else "[DRY RUN] Would resume task")

        # Run the agent
        success, session_id, timed_out = run_agent(
            task,
            dry_run=dry_run,
            model_override=model_override,
            timeout_seconds=timeout_seconds,
        )

        # Update task status
        if not dry_run:
            if success and auto_complete:
                if not complete_task(task.id, session_id):
                    print(f"Failed to complete task {task.id}, marking as blocked to prevent infinite loop")
                    fail_task(task.id, "Failed to mark task as done after successful agent run")
            elif timed_out:
                # On timeout, leave task in_progress so it can be resumed
                # The agent should have recorded progress notes before timing out
                print(f"Task {task.id} timed out - leaving in_progress for retry")
                run_command([
                    "bd", "update", task.id,
                    "--notes", f"Agent timed out after {timeout_seconds // 60} minutes. Check progress notes for partial work."
                ])
            elif not success:
                fail_task(task.id, "Agent execution failed")
        else:
            print(f"[DRY RUN] Would {'complete' if success else 'timeout' if timed_out else 'fail'} task")

        iteration += 1

    print(f"\nOrchestration finished. Processed {iteration} tasks.")
    return iteration


def main():
    parser = argparse.ArgumentParser(
        description="Orchestrate Claude Code agents to work on beads tasks"
    )
    parser.add_argument(
        "-n", "--max-iterations",
        type=int,
        default=None,
        help="Maximum number of tasks to process (default: unlimited)"
    )
    parser.add_argument(
        "-l", "--label",
        type=str,
        default=None,
        help="Only process tasks with this label"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually run agents or update tasks"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="sonnet",
        help="Model for all agents (default: sonnet)"
    )
    parser.add_argument(
        "--no-auto-complete",
        action="store_true",
        help="Don't automatically mark tasks as done"
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Process only one task then exit"
    )
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="List available agent configurations and exit"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume in-progress tasks before processing ready tasks"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_AGENT_TIMEOUT_SECONDS,
        help=f"Timeout in seconds for each agent execution (default: {DEFAULT_AGENT_TIMEOUT_SECONDS} = 30 minutes)"
    )

    args = parser.parse_args()

    # List agents mode
    if args.list_agents:
        agents = list_available_agents()
        if agents:
            print("Available agent configurations:")
            for agent in sorted(agents):
                print(f"  - {agent}")
        else:
            print("No agent configurations found in .claude/agents/")
            print("Using fallback prompts for: " + ", ".join(AGENT_TYPE_TO_FILE.values()))
        return

    max_iterations = 1 if args.single or args.dry_run else args.max_iterations

    try:
        orchestrate(
            max_iterations=max_iterations,
            label_filter=args.label,
            dry_run=args.dry_run,
            model_override=args.model,
            auto_complete=not args.no_auto_complete,
            resume=args.resume,
            timeout_seconds=args.timeout,
        )
    except KeyboardInterrupt:
        print("\n\nOrchestration interrupted by user.")
        sys.exit(1)


if __name__ == "__main__":
    main()
