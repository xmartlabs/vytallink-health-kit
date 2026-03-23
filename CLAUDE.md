# Claude Code Adapter

Use the following 4-level structure as the single source of truth for all AI-assisted work in this repository.

## Level 1 — Governance

Always read and apply these files before generating code or plans:

- `.github/architecture.md`
- `.github/standards.md`
- `.github/domain-boundaries.md`

## Level 2 — Operational Skills

Skills are stored in:

- `.github/skills/` (internal curated)
- `.github/skills-external/` (synced external/vendor)

Prefer internal curated skills when both define overlapping capabilities.

Core internal skills (specs in `.github/skills/`):

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

Each skill must:

- receive explicit input,
- produce structured output,
- comply with governance files.

## Level 3 — Automation

Prefer system-enforced quality over model-only behavior:

- Automation policy: `.github/automation.md`

Quality gate sequence:

- `make format`
- `make fix`
- `make lint`
- `make test`

## Level 4 — Orchestration

Use explicit orchestration for complex tasks:

- Orchestration policy: `.github/orchestration.md`

Rules:

- Plan first, then execute.
- Complete each phase before moving to the next.
- Review diffs before finalizing.
- Validate results against automation requirements.
- Do not perform large-scale generation without invoking a relevant skill first.

## Runtime Rules

- Interact in the same language as the user.
- Keep all code artifacts in English (identifiers, docstrings, comments, docs).
- Check `Makefile` before suggesting commands. Prefer `make` targets.
- Prefer `uv` workflows for Python environment management.
- When implementing or testing changes, create or update documentation in `docs/`.
- Use absolute imports only.
