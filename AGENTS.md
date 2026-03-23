# Codex UI Adapter

Use this repository-level structure as the canonical source of instructions.

## Level 1 — Governance

- `.github/architecture.md`
- `.github/standards.md`
- `.github/domain-boundaries.md`

## Level 2 — Operational Skills

- `.github/skills/create_use_case.md`
- `.github/skills/create_repository_interface.md`
- `.github/skills/create_mle_agent_package.md`
- `.github/skills/generate_e2e_tests.md`
- `.github/skills/generate_implementation_docs.md`
- `.github/skills/refactor_to_clean_architecture.md`
- `.github/skills/validate_module_structure.md`
- `.github/skills/generate_migration_plan.md`
- `.github/skills/execute_engineering_task.md`
- `.github/skills/plan_and_execute_feature.md`

Also load external synced skills from:

- `.github/skills-external/`

If overlap exists, prioritize `.github/skills/` over `.github/skills-external/`.

## Level 3 — Automation

- `.github/automation.md`

## Level 4 — Orchestration

- `.github/orchestration.md`

## Runtime Rules

- Use user language for interaction.
- Keep all code artifacts in English.
- Prefer Makefile and uv workflows.
