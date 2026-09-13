# Agent Instructions

This repository contains reusable tooling and protocol for planning and coordinating agent-driven software work.

Actual planning state lives outside this repository under `PLANS_HOME`.

The system is intentionally independent of any specific agent harness, model, machine, or execution environment.

## Principles

1. Plans are durable state. Agent sessions are disposable.
2. Git-backed plan data is the source of truth for planning state.
3. A plan must contain enough context for another agent to continue the work without access to the previous conversation.
4. Do not rely on absolute local filesystem paths.
5. Do not store user-specific plans, repository registries, secrets, credentials, tokens, kubeconfigs,
   `.env` files, or private keys in this repository.
6. Do not make lifecycle transitions by manually moving plan files. Use repository tooling when available.
7. Prefer deterministic scripts for state changes and structural validation. Use agents for reasoning.
8. Keep plans implementation-oriented and concise. Record decisions and their rationale, not conversation transcripts.
9. Keep the core protocol harness-agnostic.

## Repository boundaries

This repository contains reusable components such as:

```text
scripts/
templates/
AGENTS.md
README.md
```

User-specific planning data lives under `PLANS_HOME`, for example:

```text
$PLANS_HOME/
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

Do not add real user plans or private repository configuration to this repository.

Reusable plan structure is defined in:

```text
templates/plan.md
```

## Data root

The CLI resolves planning data through `PLANS_HOME`.

Do not assume that plan data lives inside this repository.

Do not assume that `PLANS_HOME` is under `~/Projects` or any other particular filesystem location.

If a task requires reading or modifying actual planning state, operate on the configured data root
rather than creating local state inside the tooling repository.

## Plan lifecycle

The normal lifecycle is:

```text
drafts -> next -> open -> done
```

A plan may also move to `discarded` from an active pre-completion state.

A plan may move to `next` only when:

- the problem is understood;
- relevant repository context has been inspected;
- important design decisions have been made;
- implementation steps are clear;
- verification criteria are defined;
- an implementation agent should not need to ask design questions before starting.

Do not reopen completed plans by moving them back to `open`. Create a new plan and reference the previous one instead.

## Working with repositories

User-specific repositories are registered in:

```text
$PLANS_HOME/repos.yaml
```

Do not assume that projects live under `~/Projects` or any other absolute path.

The runtime or harness is responsible for resolving a repository registry entry to an available workspace.

A plan should reference a repository by its registry name:

```text
repository: local-agent-stack
```

rather than by an absolute filesystem path.

Repository-local instructions such as another project's `AGENTS.md` still apply when executing work in that repository.

## Editing plans

Preserve YAML frontmatter.

When adding context:

- prefer facts verified from the target repository;
- distinguish observations from decisions;
- record unresolved questions explicitly;
- update `updated_at` when making meaningful changes.

Do not add harness-specific instructions to plans unless the task itself genuinely depends on a particular harness.

A plan in `next` should represent an implementation-ready decision, not an unfinished design discussion.

## Implementation

When executing a plan:

- read the entire plan;
- inspect the target repository before changing code;
- follow repository-local instructions;
- implement only the scope described by the plan;
- run the verification described in the plan;
- record deviations or new decisions in the plan;
- keep implementation commits in the target repository, not in the planning tooling repository.

A worker must not silently redesign a plan marked as `next`.

If implementation reveals a significant missing design decision, stop implementation and return the work
to planning rather than inventing a materially different design.

## Completion

A plan is complete only when its `Done when` criteria are satisfied.

Before moving a plan to `done`, record available implementation results such as:

- branch;
- commits;
- pull requests;
- verification performed;
- relevant follow-up work.

Generated indexes or dashboards must never become the authoritative source of plan state.

## Changes to this repository

Changes here should improve the reusable planning system rather than encode one user's workflow or environment.

Prefer:

- portable behavior;
- deterministic operations;
- dependency-light tooling;
- explicit invariants;
- backwards-compatible plan formats where practical.

Avoid adding assumptions about a particular harness, local directory layout, or private infrastructure.
