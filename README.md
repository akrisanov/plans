# plans

A portable, harness-agnostic planning and coordination layer for agent-driven software work.

`plans` keeps durable planning state outside agent sessions.
Agents may come and go; plans, decisions, lifecycle state, and verification criteria remain in Git.

The project is intentionally independent of any specific model, agent harness, machine, or execution environment.

## Architecture

`plans` separates reusable tooling from user-specific planning data.

```text
plans                         plans-data
public tooling                private state
──────────────                ─────────────
scripts/plan          ──────> plans/
templates/                    coordinators/
AGENTS.md                     repos.yaml
README.md                     AGENTS.md
```

The `plans` repository contains the protocol, CLI, templates, and reusable agent instructions.

Actual plans and repository configuration live in a separate data repository or directory configured through `PLANS_HOME`.

This keeps the tooling reusable and shareable without exposing private work.

## Plan lifecycle

Plans move through a small deterministic state machine:

```text
drafts -> next -> open -> done
   |        |       |
   └────────┴───────┴──> discarded
```

The states mean:

- `drafts` — incomplete plans still being researched or designed
- `next` — plans ready for implementation
- `open` — work currently in progress
- `done` — completed work
- `discarded` — work intentionally abandoned

A draft may move to `next` only after it passes readiness validation.

## Principles

- Plans are durable state; agent sessions are disposable.
- Git is the source of truth.
- Planning state must survive switching models, harnesses, machines, or sessions.
- Plans should contain enough context for another agent to continue without the previous conversation.
- State transitions and structural validation should be deterministic.
- Agents should do reasoning; scripts should enforce invariants.
- Plans should reference repositories by logical name rather than absolute filesystem path.
- Generated dashboards or indexes must not become authoritative state.

## Setup

Clone the tooling repository:

```bash
git clone https://github.com/akrisanov/plans.git
```

Prepare a separate directory or repository for private planning data.

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

Point the CLI at it:

```bash
export PLANS_HOME="$HOME/Projects/plans-data"
```

The tooling does not require `PLANS_HOME` to live under `~/Projects`; that is only an example.

If `PLANS_HOME` is not set, the default is:

```text
~/.local/share/plans
```

## CLI

List plans:

```bash
./scripts/plan list
```

Show a plan:

```bash
./scripts/plan show <id>
```

Validate that a plan is ready for implementation:

```bash
./scripts/plan validate <id>
```

Move a plan through its lifecycle:

```bash
./scripts/plan transition <id> <state>
```

For example:

```bash
./scripts/plan transition improve-cache-layer next
./scripts/plan transition improve-cache-layer open
./scripts/plan transition improve-cache-layer done
```

Invalid lifecycle transitions are rejected.

Moving a plan from `drafts` to `next` automatically runs readiness validation.

## Plan format

Reusable plan structure is defined in:

```text
templates/plan.md
```

A plan uses YAML frontmatter for machine-readable state and Markdown for reasoning and implementation context.

Example:

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

Plans reference repositories by registry name:

```yaml
repository: backend
```

rather than machine-specific paths such as:

```text
/Users/alice/Projects/backend
```

## Repository registry

User-specific repository mappings belong in `PLANS_HOME/repos.yaml`, not in this repository.

Example:

```yaml
version: 1

repositories:
  backend:
    path: backend
    url: git@github.com:example/backend.git
    default_branch: main
```

How a repository is resolved into an actual workspace is intentionally outside the plan format.

This allows the same plan to be executed locally, on another workstation, in a container, or in a remote development environment.

## Agent harnesses

`plans` does not depend on a particular agent harness.

It is intended to work with systems such as:

- Codex
- Pi
- Goose
- other agent runtimes capable of reading and updating files

Harness-specific execution belongs outside the core planning protocol.

## Related project

My [local-agent-stack](https://github.com/akrisanov/local-agent-stack) is a reproducible local environment
for running and evaluating agent harnesses and models. It complements `plans` as an execution layer
while `plans` remains responsible for durable planning and coordination state.

## Inspiration

This project was inspired by Fatih Arslan's article [How I manage my agents](https://arslan.io/2026/09/11/how-i-manage-my-agents/).

The article describes a Git-backed workflow where plans move through `drafts`, `next`, `open`, `done`, and `discarded`,
while coordinators manage work performed by disposable agent sessions.

`plans` takes those ideas as a starting point and explores a portable implementation that is independent
of Cursor Projects or any other specific agent harness. The goal is to keep the planning protocol and durable
state reusable across local agents, cloud agents, different models, and different execution environments.

## Status

The project is early and intentionally small.

Current functionality includes:

- deterministic plan lifecycle transitions
- structural readiness validation
- separation of reusable tooling from private plan data

Planned next steps include deterministic plan creation and higher-level lifecycle conveniences.

## License

MIT © 2026 Andrey Krisanov
