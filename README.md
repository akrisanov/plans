# plans

A small, local-first control plane for agent-driven software work.

`plans` keeps implementation plans outside source repositories and gives them a simple lifecycle,
typed metadata, deterministic validation, and a machine-readable interface for execution tools.

It does not run coding agents itself. Execution is intentionally kept separate.

## Why

Coding agents are good at implementing scoped tasks, but the surrounding workflow still needs structure:

- what should be implemented;
- which repository owns the work;
- whether the task is ready for implementation;
- what state the work is currently in;
- what other plans it depends on;
- what was actually implemented and verified.

Keeping this state only in chat sessions, issue trackers, or individual repositories
makes it difficult to build a consistent workflow across multiple repositories and agent harnesses.

`plans` provides a small filesystem-based layer for that state.

## Architecture

The system is split into two responsibilities:

```text
plans
  planning / control plane
        │
        │ plan inspect --json
        ▼
execution layer
        │
        ▼
coding agent
        │
        ▼
target repository
```

`plans` owns:

- plan creation;
- typed metadata;
- validation and readiness;
- lifecycle transitions;
- machine-readable plan inspection.

The execution layer owns:

- repository checkout resolution;
- workspace preparation;
- harness selection;
- provider and model selection;
- agent invocation;
- process and session management.

This separation keeps plans independent from a particular agent, model, machine, or repository checkout layout.

## Lifecycle

Plans move through:

```text
drafts → next → open → done
   │       │      │
   └───────┴──────┴──→ discarded
```

| State       | Meaning                                                                               |
| ----------- | ------------------------------------------------------------------------------------- |
| `drafts`    | The plan is still being designed. Open questions and incomplete sections are allowed. |
| `next`      | The plan is implementation-ready and contains no unresolved design questions.         |
| `open`      | Implementation has started.                                                           |
| `done`      | Implementation is complete.                                                           |
| `discarded` | The plan was intentionally abandoned or discarded.                                    |

Readiness is intentionally separate from execution. Moving a plan to `next` means an implementation
agent should be able to start work without redesigning the task first.

## Storage

Plan state is stored separately from this repository.

Set:

```bash
export PLANS_HOME="$HOME/Projects/plans-data"
```

A typical layout is:

```text
$PLANS_HOME/
├── plans/
│   ├── drafts/
│   ├── next/
│   ├── open/
│   ├── done/
│   └── discarded/
├── coordinators/
└── repos.yaml
```

This repository contains the tooling and plan schema.

`PLANS_HOME` contains the actual planning state and can live in a separate private Git repository.

## Repository registry

Plans refer to repositories by logical name rather than filesystem path.

Repository checkouts are described in:

```text
$PLANS_HOME/repos.yaml
```

For example:

```yaml
repositories:
  plans:
    path: plans
    url: git@github.com:akrisanov/plans.git
    default_branch: main

  local-agent-stack:
    path: local-agent-stack
    url: git@github.com:akrisanov/local-agent-stack.git
    default_branch: main
```

`path` is relative to `REPOS_HOME`:

```bash
export REPOS_HOME="$HOME/Projects"
```

A plan can therefore refer simply to:

```yaml
repository: local-agent-stack
```

without knowing where that repository is checked out on the current machine.

Absolute checkout paths do not belong in plans or `repos.yaml`.

## Installation

The project requires Python 3.12+ and uses [uv](https://docs.astral.sh/uv/).

Clone the repository and install the development environment:

```bash
git clone https://github.com/akrisanov/plans.git
cd plans

uv sync
```

To make the `plan` command available globally while keeping it linked to the local checkout:

```bash
uv tool install --editable .
```

Verify the installation:

```bash
plan --help
```

## CLI

| Command                                   | Description                                                      |
| ----------------------------------------- | ---------------------------------------------------------------- |
| `plan add <id> --repository <repository>` | Create a new plan in `drafts`.                                   |
| `plan list`                               | List plans grouped by lifecycle state.                           |
| `plan show <id>`                          | Print the plan contents.                                         |
| `plan inspect <id>`                       | Show normalized metadata and current lifecycle state.            |
| `plan inspect <id> --json`                | Emit machine-readable plan information for execution tooling.    |
| `plan validate <id>`                      | Validate plan metadata and structure.                            |
| `plan ready <id>`                         | Check implementation readiness and move a valid draft to `next`. |
| `plan complete <id>`                      | Validate completion results and move an open plan to `done`.     |
| `plan transition <id> <state>`            | Perform a valid lifecycle transition (except `open` to `done`).  |
| `plan --help`                             | Show CLI help.                                                   |
| `plan <command> --help`                   | Show help for a specific command.                                |

### Machine-readable inspection

Execution tooling should use:

```bash
plan inspect <id> --json
```

Example:

```json
{
  "id": "add-feature",
  "state": "next",
  "status": "next",
  "repository": "my-repository",
  "created_at": "2026-09-19",
  "updated_at": "2026-09-19",
  "depends_on": [],
  "prs": [],
  "path": "plans/next/add-feature.md"
}
```

`state` represents the actual lifecycle location of the plan.

`status` comes from its metadata.

`path` is relative to `PLANS_HOME`.

The command intentionally does not expose machine-specific repository checkout paths.

## Readiness

A plan can move from `drafts` to `next` when its required implementation sections are complete and actionable.

The required readiness sections are:

- `Problem`
- `Goal`
- `Decisions`
- `Implementation`
- `Verification`
- `Done when`

Contextual and post-implementation sections may remain incomplete at this stage.

The canonical plan structure lives in the template shipped with the package rather than being duplicated in this README.

## Execution

`plans` deliberately does not invoke coding agents.

Execution tools consume its public interface, primarily:

```bash
plan inspect <id> --json
```

For example, [`local-agent-stack`](https://github.com/akrisanov/local-agent-stack) contains a runner that:

1. inspects the plan;
2. verifies that it is in `next`;
3. verifies that the selected plan is committed and unchanged in Git;
4. resolves the target repository through `repos.yaml` and `REPOS_HOME`;
5. performs the remaining deterministic preflight checks;
6. transitions the plan to `open`;
7. starts the selected agent harness in the target repository.

This preserves the exact implementation-ready plan used for execution in Git history.
The check belongs to the execution layer rather than plans itself.

Example:

```bash
cd ~/Projects/local-agent-stack

uv run scripts/run-plan add-feature --harness pi
```

The runner currently supports Pi.

Agent failure does not automatically complete or roll back a plan. Once implementation has started,
the plan remains `open` until its results are recorded and `plan complete <id>` succeeds. Completion
requires all `Done when` items to be checked, a commit value, verification results, and explicit
deviations (`None` is accepted). Direct `plan transition <id> done` is not supported.

## Development

Install dependencies:

```bash
uv sync
```

Run the test suite:

```bash
uv run pytest
```

Run linting and formatting checks:

```bash
uv run ruff check .
uv run ruff format --check .
```

Run type checking:

```bash
uv run ty check
```

## Design principles

### Plans describe work, not machines

Plans use logical repository names. They do not contain local checkout paths, agent executable paths,
or machine-specific configuration.

### Planning and execution are separate

`plans` decides what is ready to execute and tracks its lifecycle.
Execution tooling decides how and where an agent runs.

### Deterministic checks happen before agents

Anything that can be checked without an LLM should be checked before invoking one.

### Files are the source of truth

Plans are plain Markdown with typed YAML metadata.
They can be inspected, versioned, reviewed, and manipulated without a service or database.

### Agent harnesses are replaceable

The plan format is not tied to Pi, Codex, Goose, or any particular model provider.

## Status

The v1 core is feature-complete and is being stabilized through real usage.

```text
create
  ↓
draft
  ↓
ready
  ↓
next
  ↓
checkpoint
  ↓
run
  ↓
open
  ↓
agent
  ↓
review
  ↓
complete
  ↓
done
```

Plan creation, validation, readiness, inspection, lifecycle management, and completion
have been exercised end to end on real implementation work.

The implementation-ready next plan is preserved in Git before execution begins,
and the verified result is recorded separately when the plan is completed. This keeps
both the input to implementation and its final outcome recoverable from Git history.

The v1 public contracts are now being stabilized through continued dogfooding before
the v1.0.0 release.

---

MIT © 2026 Andrey Krisanov
