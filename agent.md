# Workflow Orchestration

## Data and sourcing orientation

Before changing or querying sourced data, read `docs/AGENT_DATA_REFERENCE.md`.
Before changing collectors, read `docs/INGESTION_REFERENCE.md`. The former defines
safe table/feature interpretation and the latter documents sourcing side effects;
`schemas/*.json` is the complete observed-field inventory for dynamic provider
columns.

## Plan mode by default.
Enter plan mode for any non-trivial task (3+ steps or architectural decisions). If something goes sideways, stop and re-plan immediately — don't keep pushing. Use plan mode for verification steps, not just building. Write detailed specs upfront to reduce ambiguity.

## Subagent strategy.
Use subagents liberally to keep your main context window clean. Offload research, exploration, and parallel analysis. For complex problems, throw more compute at it. One task per subagent for focused execution.

## Self-improvement loop.
After any correction from the user, update tasks/lessons.md with the pattern. Write rules that prevent the same mistake twice. Ruthlessly iterate on these until the mistake rate drops. Review lessons at session start.

## Demand elegance (balanced).
For non-trivial changes, pause and ask "is there a more elegant way?" If a fix feels hacky: "Knowing everything I know now, implement the elegant solution." Skip this for simple, obvious fixes — don't over-engineer.

# Core Principles

## Simplicity first
Make every change as simple as possible. Minimal code impact.

## No laziness
Find root causes. No temporary fixes. Senior developer standards.

## Minimal blast radius
Only touch what's necessary. Don't introduce new bugs.
