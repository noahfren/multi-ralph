# Multi-Ralph: Agent Orchestration Framework

A standalone multi-agent orchestration framework for autonomous development workflows using Claude Code and Beads issue tracking.

## Overview

Multi-Ralph coordinates specialized AI agents to work through development tasks in a structured, hierarchical manner. It integrates with [Beads](https://github.com/beads-dev/beads) (bd) for issue tracking and uses Claude Code's agent configuration system to assign tasks to specialized development agents.

## Features

- **Hierarchical Task Processing**: Prioritizes tasks by depth (leaf subtasks → parent tasks → epics)
- **Specialized Agents**: Pre-configured agents for frontend, backend, AI, SDET, and QA work
- **Automatic Task Routing**: Routes tasks to appropriate agents based on labels
- **Dependency Awareness**: Respects task dependencies and only processes ready tasks
- **Resume Capability**: Can resume in-progress tasks after interruption

## Prerequisites

1. **Claude Code CLI**: Install the Claude CLI (`claude` command)
2. **Beads (bd)**: Install the Beads issue tracker CLI
   ```bash
   # Initialize beads in your project
   bd init
   ```

## Installation

Copy this package to your project or use it standalone:

```bash
# Clone or copy to your development directory
cp -r multi-ralph ~/dev/multi-ralph

# Or symlink the orchestration script
ln -s ~/dev/multi-ralph/scripts/orchestrate.py ~/bin/orchestrate
```

## Directory Structure

```
multi-ralph/
├── scripts/
│   └── orchestrate.py      # Main orchestration script
├── .claude/
│   ├── agents/             # Agent configuration files
│   │   ├── dev-ai.md       # AI/ML specialist agent
│   │   ├── dev-backend.md  # Backend developer agent
│   │   ├── dev-frontend.md # Frontend developer agent
│   │   ├── dev-general.md  # General-purpose agent
│   │   ├── dev-qa.md       # QA validation agent
│   │   └── dev-sdet.md     # Test automation agent
│   └── skills/
│       ├── code-assist/    # TDD implementation skill
│       │   └── SKILL.md
│       └── code-task-generator/  # Task breakdown skill
│           └── SKILL.md
└── README.md
```

## Usage

### Basic Usage

```bash
# Run the orchestrator
python scripts/orchestrate.py

# Process a single task
python scripts/orchestrate.py --single

# Dry run (see what would happen)
python scripts/orchestrate.py --dry-run

# Resume in-progress tasks first
python scripts/orchestrate.py --resume
```

### Options

| Flag | Description |
|------|-------------|
| `-n, --max-iterations` | Maximum number of tasks to process |
| `-l, --label` | Only process tasks with this label |
| `--dry-run` | Don't run agents or update tasks |
| `--model` | Override model for all agents (default: sonnet) |
| `--no-auto-complete` | Don't auto-mark tasks as done |
| `--single` | Process only one task then exit |
| `--list-agents` | List available agent configurations |
| `--resume` | Resume in-progress tasks before ready tasks |

### Examples

```bash
# Process only backend tasks
python scripts/orchestrate.py --label agent:backend

# Use Opus model for all agents
python scripts/orchestrate.py --model opus

# Process 5 tasks maximum
python scripts/orchestrate.py -n 5

# List available agents
python scripts/orchestrate.py --list-agents
```

## Agent Configuration

Agents are configured in `.claude/agents/` as Markdown files with YAML frontmatter:

```markdown
---
name: dev-backend
description: Backend development agent
tools: [Read, Edit, Write, Bash, Grep, Glob]
model: sonnet
skills: [code-assist]
---

# Backend Development Agent

You are a specialized backend development agent...
```

### Agent Types

| Agent | Label | Specialization |
|-------|-------|----------------|
| `dev-frontend` | `agent:frontend` | UI components, React/Vue, CSS |
| `dev-backend` | `agent:backend` | APIs, databases, server logic |
| `dev-ai` | `agent:ai` | Prompts, LLM integration, RAG |
| `dev-sdet` | `agent:sdet` | E2E tests, test infrastructure |
| `dev-qa` | `agent:qa` | Validation, acceptance testing |
| `dev-general` | (fallback) | General development tasks |

## Task Hierarchy

Tasks are organized in a three-level hierarchy:

1. **Epic** (depth 0): Container for a feature or implementation step
2. **Task** (depth 1): Logical unit of work
3. **Subtask** (depth 2+): Agent-assignable work items

The orchestrator processes tasks deepest-first, ensuring leaf subtasks are completed before their parents are auto-closed.

## Creating Tasks

Use the `code-task-generator` skill to create properly structured tasks:

```bash
# In Claude Code, invoke the skill
> Use the code-task-generator skill to create tasks for: "Build a user authentication system"
```

Or manually with beads:

```bash
# Create an epic
bd create "User Authentication" --type epic

# Create a task under the epic
bd create "Login API" --parent fb-auth0 --labels "agent:backend"

# Create a QA validation subtask
bd create "Validate Login API" --parent fb-auth0.1 --labels "agent:qa"

# Set dependency
bd dep add fb-auth0.1.2 fb-auth0.1.1
```

## Integration with Your Project

1. Copy the `.claude/` directory to your project root
2. Copy the orchestration script to your project's `scripts/` directory
3. Initialize beads in your project: `bd init`
4. Create tasks using the skill or manually
5. Run the orchestrator: `python scripts/orchestrate.py`

## Workflow

1. **Task Generation**: Use `code-task-generator` to break features into agent-assignable subtasks
2. **Orchestration**: Run `orchestrate.py` to process tasks automatically
3. **Agent Execution**: Each agent reads its task, implements the work, and closes the task
4. **Validation**: QA agents validate implementation work
5. **Completion**: Parent tasks auto-close when all children are complete

## Customization

### Adding New Agent Types

1. Create a new agent file in `.claude/agents/`:
   ```bash
   touch .claude/agents/dev-devops.md
   ```

2. Add the YAML frontmatter and system prompt

3. Update `AGENT_TYPE_TO_FILE` in `orchestrate.py`:
   ```python
   AGENT_TYPE_TO_FILE = {
       ...
       "devops": "dev-devops",
   }
   ```

### Modifying Agent Behavior

Edit the agent's markdown file to change:
- `tools`: Available tools for the agent
- `model`: Which model to use (sonnet, opus, etc.)
- `skills`: Skills the agent can use
- System prompt (markdown body)

## Troubleshooting

### No agents found
Ensure `.claude/agents/` exists and contains `.md` files. The orchestrator will fall back to built-in prompts if agent files are missing.

### Tasks not being processed
- Check `bd ready` to see available tasks
- Verify task labels match agent types
- Check for blocking dependencies with `bd show <task-id>`

### Agent execution fails
- Verify Claude CLI is installed and authenticated
- Check model availability
- Review agent configuration syntax

## License

MIT
