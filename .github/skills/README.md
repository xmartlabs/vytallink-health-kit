# Skills Catalog

Operational skills must receive explicit input and return structured output.

## Skill Sources

- Internal curated skills: `.github/skills/`
- External synced skills: `.github/skills-external/`

Precedence rule:

- If a skill exists in both places, prefer `.github/skills/`.

## Available Skills

- `create_use_case`
- `create_repository_interface`
- `create_mle_agent_package`
- `generate_e2e_tests`
- `generate_implementation_docs`
- `refactor_to_clean_architecture`
- `validate_module_structure`
- `generate_migration_plan`
- `execute_engineering_task`
- `plan_and_execute_feature`

## Governance Dependency

All skills must comply with:

- `.github/architecture.md`
- `.github/standards.md`
- `.github/domain-boundaries.md`

For complex tasks, also comply with:

- `.github/orchestration.md`

Repository-specific caution:

- For VytalLink-facing features, demos, or notebooks, assume the upstream server may saturate under repeated or bursty requests.
- Prefer cached snapshots, bounded windows, request spacing, and explicit timeout/backoff settings over repeated refetch loops.
