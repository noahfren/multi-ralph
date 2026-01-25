---
name: code-task-generator
description: This skill generates beads issues from rough descriptions, ideas, or PDD implementation plans. It automatically detects the input type and creates properly structured beads tasks with dependencies and hierarchies. For PDD plans, it processes implementation steps one at a time, creating an epic for each step with child tasks. Tasks are decomposed into agent-specific subtasks (frontend, backend, ai, sdet, qa) to enable parallel autonomous execution with proper validation gates.
type: anthropic-skill
version: "2.2"
---

# Code Task Generator (Beads Edition)

## Overview

This skill generates beads issues from rough descriptions, ideas, or PDD implementation plans. It automatically detects the input type and creates properly structured beads tasks with dependencies and hierarchies. For PDD plans, it processes implementation steps one at a time, creating an epic for each step with child tasks.

## Prerequisites

- Beads must be initialized in the repository (`bd init` has been run)
- The `bd` CLI must be available

## Agent Specialization

Tasks are broken into subtasks that can be assigned to specialized agents. Each subtask is labeled with an agent type to enable parallel autonomous execution.

### Agent Types

| Label | Agent | Responsibility |
|-------|-------|----------------|
| `agent:frontend` | Frontend Agent | UI components, client-side logic, styling, React/Vue/etc. |
| `agent:backend` | Backend Agent | APIs, server logic, database operations, business logic |
| `agent:ai` | AI Specialization Agent | Prompt engineering, LLM integration, AI pipelines |
| `agent:sdet` | SDET Agent | E2E test suite setup, test infrastructure, automation frameworks |
| `agent:qa` | QA Validation Agent | Test execution, validation, acceptance testing, bug verification |

### Subtask Decomposition Rules

**Rule 1: Every task MUST have implementation + validation**
- Every coding task requires a corresponding QA validation subtask
- The validation subtask depends on (is blocked by) the implementation subtask
- Validation ensures acceptance criteria are met before the task is considered complete

**Rule 2: Full-stack features require frontend + backend subtasks**
- If a task touches both UI and server-side code, split into separate subtasks
- Backend subtask typically comes first (API implementation)
- Frontend subtask depends on backend (consumes the API)
- Each gets its own QA validation subtask

**Rule 3: E2E test suites use SDET + QA**
- SDET agent sets up the test infrastructure and writes the tests
- QA agent validates the suite runs correctly and covers requirements
- SDET subtask blocks QA validation subtask

**Rule 4: AI-specific work uses the AI agent**
- Prompt engineering, prompt templates, LLM chain setup
- Model integration, embedding pipelines, RAG implementation
- AI agent subtasks still require QA validation

### Hierarchy Structure

```
Epic (Step N)
└── Task (Feature/Component)
    ├── Subtask: Backend implementation [agent:backend]
    │   └── Subtask: Backend validation [agent:qa] (blocked by backend impl)
    ├── Subtask: Frontend implementation [agent:frontend] (blocked by backend impl)
    │   └── Subtask: Frontend validation [agent:qa] (blocked by frontend impl)
    └── Subtask: Integration validation [agent:qa] (blocked by all impl subtasks)
```

### Subtask Creation

Subtasks are created with `--parent <task-id>` pointing to the parent task:

```bash
# Create implementation subtask
BACKEND_ID=$(bd create "Implement user API endpoints" \
  --type task \
  --parent <task-id> \
  --labels "agent:backend,complexity:medium" \
  --silent)

# Create validation subtask that depends on implementation
QA_ID=$(bd create "Validate user API endpoints" \
  --type task \
  --parent <task-id> \
  --labels "agent:qa" \
  --silent)

# QA is blocked by backend implementation
bd dep add $QA_ID $BACKEND_ID
```

## Parameters

- **input** (required): Task description, file path, or PDD plan path. Can be a simple sentence, paragraph, detailed explanation, or path to a PDD implementation plan.
- **step_number** (optional): For PDD plans only - specific step to process. If not provided, automatically determines the next uncompleted step from the checklist.
- **parent_epic** (optional): For description mode - an existing epic ID to add tasks under.

**Constraints for parameter acquisition:**
- You MUST ask for all required parameters upfront in a single prompt rather than one at a time
- You MUST support multiple input methods for input including:
  - Direct text input
  - File path containing the description or PDD plan
  - Directory path (will look for plan.md within it)
  - URL to internal documentation
- You MUST confirm successful acquisition of all parameters before proceeding

## Steps

### 1. Verify Beads Installation

Ensure beads is properly set up in the repository.

**Constraints:**
- You MUST run `bd info` to verify beads is initialized
- If beads is not initialized, You MUST inform the user and suggest running `bd init`
- You MUST NOT proceed if beads is not available

### 2. Detect Input Mode

Automatically determine whether input is a description or PDD plan.

**Constraints:**
- You MUST check if input is a file path that exists
- If file exists, You MUST read it and check for PDD plan structure (checklist, numbered steps)
- If file contains PDD checklist format, You MUST set mode to "pdd"
- If input is text or file without PDD structure, You MUST set mode to "description"
- You MUST inform user which mode was detected
- You MUST validate that PDD plans follow expected format with numbered steps

### 3. Analyze Input

Parse and understand the input content based on detected mode.

**Constraints:**
- For PDD mode: You MUST parse implementation plan and extract steps/checklist status
- For PDD mode: You MUST determine target step based on step_number parameter or first uncompleted step
- For description mode: You MUST identify the core functionality being requested
- You MUST extract any technical requirements, constraints, or preferences mentioned
- You MUST determine the appropriate complexity level (Low/Medium/High)
- You MUST identify the likely technology stack or domain area

### 4. Structure Requirements

Organize requirements and determine task breakdown based on mode.

**Constraints:**
- For PDD mode: You MUST extract target step's title, description, demo requirements, and constraints
- For PDD mode: You MUST preserve integration notes with previous steps
- For PDD mode: You MUST identify which specific research documents (if any) are directly relevant to each task
- For PDD mode: You MUST capture the design document path (typically `{project_dir}/design/detailed-design.md`) to include in all task descriptions
- For PDD mode: You MUST capture the requirements document path (typically `{project_dir}/idea-honing.md`) for reference
- For description mode: You MUST identify specific functional requirements from the description
- For description mode: You MUST ask the user if there is a related design document to reference
- You MUST infer reasonable technical constraints and dependencies
- You MUST create measurable acceptance criteria using Given-When-Then format
- You MUST prepare task breakdown plan for approval

### 5. Plan Tasks and Subtasks

Present task and subtask breakdown for user approval before generation.

**Constraints:**
- You MUST analyze content to identify logical tasks for implementation
- You MUST break each task into agent-specific subtasks following the decomposition rules:
  - Identify if task is frontend-only, backend-only, full-stack, AI-specific, or test infrastructure
  - Create appropriate implementation subtasks with agent labels
  - Create corresponding validation subtasks for each implementation subtask
- You MUST present a hierarchical view showing:
  - Tasks with their subtasks indented
  - Agent assignment for each subtask (e.g., `[agent:backend]`, `[agent:qa]`)
  - Dependencies between subtasks
- You MUST show proposed task sequence and dependencies
- You MUST ask user to approve the plan before proceeding
- You MUST allow user to request modifications to the task/subtask breakdown
- You MUST NOT proceed to create beads issues until user explicitly approves

**Example Plan Output:**
```
Task 1: Create User Authentication API
  ├── 1.1 Implement auth endpoints [agent:backend]
  ├── 1.2 Validate auth endpoints [agent:qa] (blocked by 1.1)
  └── 1.3 Integration test validation [agent:qa] (blocked by 1.1, 1.2)

Task 2: Build Login UI Component (blocked by Task 1)
  ├── 2.1 Implement login form [agent:frontend]
  ├── 2.2 Validate login form [agent:qa] (blocked by 2.1)
  └── 2.3 E2E login flow validation [agent:qa] (blocked by 2.1, 2.2)
```

### 6. Create Beads Issues

Create beads issues based on the approved plan, including tasks and their agent-specific subtasks.

**Constraints:**
- You MUST include a reference to the relevant design document in every task description
- For PDD mode: The design doc is typically at `{project_dir}/design/detailed-design.md`
- For description mode: If a design doc exists, include its path; if not, note that no design doc is available
- The design doc reference MUST be in the "Reference Documentation" section of the description so agents know where to look for context
- For PDD mode: You MUST create an epic for the step using:
  ```bash
  bd create "Step N: [Step Title]" --type epic --description "[Step overview and demo requirements]"
  ```
- For PDD mode: You MUST capture the epic ID from the output (e.g., `bd-abc123`)
- For PDD mode: You MUST create child tasks under the epic using `--parent <epic-id>`
- For description mode: You MUST create tasks (optionally under a provided parent_epic)
- You MUST use `--silent` flag and capture the task ID for each created task
- You MUST create subtasks under each task using `--parent <task-id>`
- You MUST label each subtask with the appropriate agent type:
  - `agent:frontend` for UI/client-side work
  - `agent:backend` for API/server-side work
  - `agent:ai` for prompt engineering, LLM integration
  - `agent:sdet` for E2E test infrastructure setup
  - `agent:qa` for validation and acceptance testing
- You MUST create dependencies between subtasks:
  - QA validation subtasks are blocked by their corresponding implementation subtasks
  - Frontend subtasks are blocked by backend subtasks they depend on
  - Integration validation is blocked by all component implementations
- You MUST use appropriate labels for metadata:
  - Agent assignment: `agent:frontend`, `agent:backend`, `agent:ai`, `agent:sdet`, `agent:qa`
  - Complexity: `complexity:low`, `complexity:medium`, or `complexity:high`
  - Required skills: `skill:<skill-name>` for each required skill
  - Domain labels as appropriate (e.g., `database`, `auth`, `api`)

**Task Creation Format:**
```bash
# Create a task with full details
bd create "[Task Title]" \
  --type task \
  --parent <epic-id> \
  --description "$(cat <<'EOF'
## Description
[Clear description of what needs to be implemented]

## Background
[Relevant context]

## Reference Documentation
**IMPORTANT: Always read the design doc before starting implementation.**
- Design Document: [absolute path to detailed design document, e.g., /path/to/project/design/detailed-design.md]
- Requirements: [path to idea-honing.md if available]
- Research: [paths to relevant research docs if available]

## Technical Requirements
1. [Requirement 1]
2. [Requirement 2]

## Implementation Approach
1. [Step 1]
2. [Step 2]
EOF
)" \
  --acceptance "$(cat <<'EOF'
1. [Criterion]: Given [precondition], When [action], Then [result]
2. [Criterion]: Given [precondition], When [action], Then [result]
EOF
)" \
  --labels "complexity:medium,skill:typescript,backend" \
  --silent
```

**Dependency Creation:**
```bash
# Task 2 depends on Task 1 (Task 1 blocks Task 2)
bd dep add <task-2-id> <task-1-id>
```

### 7. Report Results

Inform user about generated tasks and next steps.

**Constraints:**
- You MUST run `bd list --parent <epic-id> --pretty` to show the created task hierarchy
- You MUST provide the epic ID and all task IDs created
- For PDD mode: You MUST provide the step demo requirements for context
- For description mode: You MUST provide a brief summary of what was created
- You MUST suggest using `bd ready` to see which tasks are ready to work on
- You MUST suggest using `bd show <task-id>` to view full task details
- For PDD mode: You MUST mention running code-assist on each task in sequence
- For description mode: You MUST offer to create additional related tasks if the scope seems large

## Beads Task Structure

### Hierarchy Levels

1. **Epic** - Container for a PDD step or major feature
2. **Task** - Logical unit of work (feature, component, capability)
3. **Subtask** - Agent-assignable unit with specific specialization

### Issue Fields

Each issue created in beads will have:

- **Title**: Concise name describing the work
- **Type**: `epic`, `task`, or `task` (subtasks are tasks with a parent task)
- **Parent**: Parent ID for hierarchical organization
  - Tasks have epic as parent
  - Subtasks have task as parent
- **Description**: Full details including:
  - Description section
  - Background/context
  - **Reference Documentation** (CRITICAL: agents look here for context)
    - Design document path (e.g., `design/detailed-design.md`)
    - Requirements document path (e.g., `idea-honing.md`)
    - Relevant research documents
  - Technical requirements
  - Implementation approach
- **Acceptance Criteria**: Given-When-Then format criteria
- **Labels**: Metadata including:
  - Agent assignment: `agent:frontend`, `agent:backend`, `agent:ai`, `agent:sdet`, `agent:qa`
  - Complexity: `complexity:low`, `complexity:medium`, `complexity:high`
  - Skills: `skill:<skill-name>`
  - Domain: `database`, `api`, `auth`, etc.
- **Dependencies**: Blocking relationships between issues

### Agent Label Reference

| Label | Use For |
|-------|---------|
| `agent:frontend` | React/Vue/Angular components, CSS, client-side JS, UI logic |
| `agent:backend` | REST/GraphQL APIs, database queries, server logic, microservices |
| `agent:ai` | Prompt engineering, LLM chains, embeddings, RAG, model integration |
| `agent:sdet` | Test framework setup, E2E infrastructure, CI/CD test pipelines |
| `agent:qa` | Test execution, acceptance validation, bug verification, regression |

## Examples

### Example Input (Description Mode - Simple Backend Task)
```
input: "I need a function that validates email addresses and returns detailed error messages"
```

### Example Output (Description Mode - Simple Backend Task)
```
Detected mode: description

Is there a design document for this feature? (If yes, provide path)
User: "No, this is a standalone utility"

Created task: bd-a1b2c3 "Create Email Validator Function"
  Description includes:
    Reference Documentation:
    - Design: No design document (standalone utility)

Subtasks created:
  bd-a1b2c3
  ├── bd-d4e5f6 "Implement email validation logic" [agent:backend] (ready)
  └── bd-g7h8i9 "Validate email validator function" [agent:qa] (blocked by bd-d4e5f6)

View task hierarchy: bd list --parent bd-a1b2c3 --pretty
Start working: bd ready

Next steps:
1. Backend agent works on bd-d4e5f6
2. QA agent validates via bd-g7h8i9 once implementation is complete
```

### Example Input (Description Mode - Full Stack Feature)
```
input: "Build a user profile page that displays user info from the API and allows editing"
```

### Example Output (Description Mode - Full Stack Feature)
```
Detected mode: description

Is there a design document for this feature? (If yes, provide path)
User: "Yes, docs/design/user-profile-design.md"

Created epic: bd-xyz001 "User Profile Feature"

Task: bd-abc100 "User Profile Page"
  Description includes:
    Reference Documentation:
    - Design: /Users/dev/myproject/docs/design/user-profile-design.md
  Subtasks:
  ├── bd-abc101 "Implement profile API endpoints" [agent:backend] (ready)
  ├── bd-abc102 "Validate profile API" [agent:qa] (blocked by bd-abc101)
  ├── bd-abc103 "Build profile UI component" [agent:frontend] (blocked by bd-abc101)
  ├── bd-abc104 "Validate profile UI" [agent:qa] (blocked by bd-abc103)
  └── bd-abc105 "E2E profile flow validation" [agent:qa] (blocked by bd-abc102, bd-abc104)

View hierarchy: bd list --parent bd-xyz001 --pretty
Ready tasks: bd ready

Next steps:
1. Backend agent implements API (bd-abc101) - see design doc for API spec
2. QA validates API (bd-abc102), Frontend builds UI (bd-abc103) - can run in parallel
3. QA validates UI (bd-abc104)
4. QA runs E2E validation (bd-abc105)
```

### Example Input (Description Mode - AI Feature)
```
input: "Create a prompt template system for generating product descriptions using GPT-4"
```

### Example Output (Description Mode - AI Feature)
```
Detected mode: description

Created task: bd-ai001 "Prompt Template System for Product Descriptions"

Subtasks created:
  bd-ai001
  ├── bd-ai002 "Design and implement prompt templates" [agent:ai] (ready)
  ├── bd-ai003 "Implement template API endpoints" [agent:backend] (blocked by bd-ai002)
  ├── bd-ai004 "Validate prompt quality and outputs" [agent:qa] (blocked by bd-ai002)
  └── bd-ai005 "Validate API integration" [agent:qa] (blocked by bd-ai003)

Next steps:
1. AI agent designs prompt templates (bd-ai002)
2. Backend agent exposes API (bd-ai003), QA validates prompts (bd-ai004) - parallel
3. QA validates full integration (bd-ai005)
```

### Example Input (Description Mode - E2E Test Suite)
```
input: "Set up Playwright E2E test suite for the checkout flow"
```

### Example Output (Description Mode - E2E Test Suite)
```
Detected mode: description

Created task: bd-e2e001 "Checkout Flow E2E Test Suite"

Subtasks created:
  bd-e2e001
  ├── bd-e2e002 "Set up Playwright infrastructure" [agent:sdet] (ready)
  ├── bd-e2e003 "Implement checkout flow tests" [agent:sdet] (blocked by bd-e2e002)
  └── bd-e2e004 "Validate test suite execution" [agent:qa] (blocked by bd-e2e003)

Next steps:
1. SDET agent sets up Playwright (bd-e2e002)
2. SDET agent writes checkout tests (bd-e2e003)
3. QA agent validates suite runs correctly (bd-e2e004)
```

### Example Input (PDD Mode)
```
input: "planning/implementation/plan.md"
```

### Example Output (PDD Mode)
```
Detected mode: pdd

Processing Step 2: Create Data Models
Design document: planning/design/detailed-design.md

Created epic: bd-xyz789 "Step 2: Create Data Models"

Task: bd-t001 "Create core data models"
  Description includes:
    Reference Documentation:
    - Design: /Users/dev/myproject/planning/design/detailed-design.md
    - Requirements: /Users/dev/myproject/planning/idea-honing.md
  Subtasks:
  ├── bd-t001a "Implement data model classes" [agent:backend] (ready)
  └── bd-t001b "Validate data models" [agent:qa] (blocked by bd-t001a)

Task: bd-t002 "Implement validation logic" (blocked by bd-t001)
  ├── bd-t002a "Add validation rules" [agent:backend] (blocked by bd-t001)
  └── bd-t002b "Validate validation logic" [agent:qa] (blocked by bd-t002a)

Task: bd-t003 "Add serialization support" (blocked by bd-t002)
  ├── bd-t003a "Implement serializers" [agent:backend] (blocked by bd-t002)
  └── bd-t003b "Validate serialization" [agent:qa] (blocked by bd-t003a)

Task hierarchy: bd list --parent bd-xyz789 --pretty
Ready tasks: bd ready

Step demo: Working data models with validation that can create, validate,
and serialize/deserialize data objects

Next steps:
1. Run `bd ready` to see subtasks ready for agents
2. Backend agent starts with bd-t001a (design doc linked in task description)
3. QA agent validates each component as it completes
4. Run code-assist on each subtask in dependency order
```

## Troubleshooting

### Beads Not Initialized
If beads is not initialized in the repository:
- You SHOULD suggest running `bd init` to initialize beads
- You SHOULD provide the command: `bd init`

### Vague Description (Description Mode)
If the task description is too vague or unclear:
- You SHOULD ask clarifying questions about specific requirements
- You SHOULD suggest common patterns or approaches for the domain
- You SHOULD create a basic task and offer to refine it based on feedback

### Complex Description (Description Mode)
If the description suggests a very large or complex task:
- You SHOULD suggest creating an epic with multiple child tasks
- You SHOULD focus on the core functionality for the initial tasks
- You SHOULD offer to create additional related tasks

### Plan File Not Found (PDD Mode)
If the specified plan file doesn't exist:
- You SHOULD check if the path is a directory and look for plan.md within it
- You SHOULD suggest common locations where PDD plans might be stored
- You SHOULD validate the file path format and suggest corrections

### Invalid Plan Format (PDD Mode)
If the plan doesn't follow expected PDD format:
- You SHOULD identify what sections are missing or malformed
- You SHOULD suggest running the PDD skill to generate a proper plan
- You SHOULD attempt to extract what information is available

### No Uncompleted Steps (PDD Mode)
If all steps in the checklist are marked complete:
- You SHOULD inform the user that all steps appear to be complete
- You SHOULD run `bd list --type epic` to show existing step epics
- You SHOULD ask if they want to generate tasks for a specific step anyway

### Dependency Cycles
If creating dependencies would cause a cycle:
- You SHOULD use `bd dep cycles` to check for cycles
- You SHOULD restructure the task dependencies to avoid cycles
- You SHOULD inform the user about the dependency structure
