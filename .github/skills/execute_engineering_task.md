# Skill: execute_engineering_task

## Purpose

Execute engineering work through governed orchestration instead of ad-hoc generation.

## Required Input

- Task objective.
- Scope constraints (files/modules in and out of scope).
- Acceptance criteria.
- Risk or compliance constraints.
- Optional preferred skills.

## Output Format

- Task summary.
- Implementation plan (ordered steps).
- Selected operational skills and rationale.
- Execution log by step.
- Validation results against automation and governance.
- Final change summary with touched files.

## Execution Phases

1. Read governance
   - `.github/architecture.md`
   - `.github/standards.md`
   - `.github/domain-boundaries.md`
2. Generate implementation plan.
3. Identify required operational skills from `.github/skills/`.
4. Execute selected skills in dependency order.
5. Validate against `.github/automation.md` and `.github/orchestration.md`.
6. Produce a structured summary of changes and residual risks.

## Execution Rules

1. Follow governance files before planning or coding.
2. Prefer minimal file churn and strict scope boundaries.
3. Keep all code artifacts in English.
4. Update `docs/` when implementation or tests change.
5. Escalate blockers with explicit assumptions and next actions.
