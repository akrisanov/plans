# plans

`plans` keeps plans for agent-driven software work in Git.

Plans are Markdown files with typed YAML metadata.
The CLI creates plans, validates them, and moves them through a defined lifecycle.

Agent sessions are temporary.
Plans, decisions, implementation steps, and verification criteria remain available after a session ends.

The project does not depend on a specific model, agent harness, machine, or execution environment.

## Architecture

`plans` separates reusable tooling from private planning data.

```text
plans                         plans-data
public tooling                private state
──────────────                ─────────────
src/plans/            ──────> plans/
  cli.py                       coordinators/
  lifecycle.py                 repos.yaml
  models.py                    AGENTS.md
  storage.py
  validation.py
  templates/
AGENTS.md
README.md
```

The `plans` repository contains the Python package, CLI, plan template, and reusable agent instructions.

Actual plans and repository configuration live in a separate directory or Git repository configured through `PLANS_HOME`.

The separation allows the tooling to remain public while plans and repository configuration remain private.

## Plan lifecycle

Plans move through the following states:

```text
drafts -> next -> open -> done
   |        |       |
   └────────┴───────┴──> discarded
```

The states have the following meanings:

- `drafts` contains plans that are still being researched or written.
- `next` contains plans that are ready for implementation.
- `open` contains work that is in progress.
- `done` contains completed work.
- `discarded` contains work that was intentionally abandoned.

A draft can move to `next` only after it passes readiness validation.

Invalid state transitions are rejected by the CLI.

## Principles

Plans are durable state, while agent sessions are temporary. Git is the source of truth for plan data.

A plan should contain enough context for another agent to continue the work without access to the previous conversation.
State transitions and structural validation are handled by deterministic code rather than by an agent.

Plans refer to repositories by logical name instead of absolute filesystem paths.
The same plan can therefore be used on different machines and with different execution environments.

The core planning format does not depend on Codex, Pi, Goose, or another specific agent harness.

## Requirements

`plans` requires Python 3.12 or later.

The project uses `uv` for package and dependency management.

## Installation

Clone the repository:

```bash
git clone https://github.com/akrisanov/plans.git
cd plans
```

Install the project:

```bash
uv sync
```

The `plan` command can then be run with:

```bash
uv run plan
```

You can also install the package so that `plan` is available directly in your environment.

## Planning data

Prepare a separate directory or Git repository for planning data.

For example:

```text
plans-data/
├── plans/
│   ├── drafts/
│   ├── next/
│   ├── open/
│   ├── done/
│   └── discarded/
├── coordinators/
├── AGENTS.md
└── repos.yaml
```

Set `PLANS_HOME` to the location of the data:

```bash
export PLANS_HOME="$HOME/Projects/plans-data"
```

The directory does not need to be under `~/Projects`. The path above is only an example.

If `PLANS_HOME` is not set, the default location is:

```text
~/.local/share/plans
```

## CLI

Create a draft:

```bash
uv run plan add improve-cache-layer --repository backend
```

The command creates:

```text
$PLANS_HOME/plans/drafts/improve-cache-layer.md
```

Plan IDs use lowercase kebab-case.

List plans:

```bash
uv run plan list
```

Show a plan:

```bash
uv run plan show improve-cache-layer
```

Validate that a plan is ready for implementation:

```bash
uv run plan validate improve-cache-layer
```

Validate a draft and move it to `next`:

```bash
uv run plan ready improve-cache-layer
```

Move a plan through its lifecycle:

```bash
uv run plan transition improve-cache-layer open
uv run plan transition improve-cache-layer done
```

The CLI rejects invalid transitions.

Moving a plan from `drafts` to `next` runs readiness validation automatically.
The `ready` command provides the same validated transition for drafts.

## Plan format

The plan template is stored in:

```text
src/plans/templates/plan.md
```

Each plan contains YAML frontmatter followed by Markdown sections.

For example:

```yaml
---
id: improve-cache-layer
status: draft
repository: backend

created_at: 2026-09-13
updated_at: 2026-09-13

depends_on: []
prs: []
---
```

The metadata is parsed with PyYAML and validated with Pydantic.

The current metadata schema includes:

- `id`
- `status`
- `repository`
- `created_at`
- `updated_at`
- `depends_on`
- `prs`

Unknown metadata fields are rejected.

The Markdown body records the problem, decisions, implementation steps, verification steps, completion criteria, and results.

A draft must contain meaningful content in the sections required for readiness before it can move to `next`.

## Repository registry

Plans refer to repositories by logical name:

```yaml
repository: backend
```

Machine-specific paths should not be stored in plans.

Repository mappings belong in:

```text
$PLANS_HOME/repos.yaml
```

For example:

```yaml
version: 1

repositories:
  backend:
    path: backend
    url: git@github.com:example/backend.git
    default_branch: main
```

The plan format does not define where a repository must exist on disk.
Repository resolution can therefore be implemented separately for local machines, containers, or remote environments.

## Agent harnesses

`plans` does not execute coding agents itself.

The planning format is intended to work with Codex, Pi, Goose, and other agent runtimes that can read and update files.

Execution code that depends on a specific harness belongs outside the core planning protocol.

## Related projects

[local-agent-stack](https://github.com/akrisanov/local-agent-stack) is my reproducible environment
for running and evaluating local agent harnesses and models.

`plans` stores planning state. `local-agent-stack` handles execution.
The two projects are separate so that planning data does not depend on a particular agent runtime.

## Inspiration

The project was inspired by Fatih Arslan's article [How I manage my agents](https://arslan.io/2026/09/11/how-i-manage-my-agents/).

`plans` uses the same basic idea and implements it independently.
The project keeps the planning format separate from any specific agent harness or local machine setup.

## Status

The current version supports plan creation, typed metadata, readiness validation, lifecycle transitions,
and separate private planning data.

## License

MIT © 2026 Andrey Krisanov
