---
trigger: always_on
---

## 🤖 Antigravity Rules Adapter

Use this repository-level structure as the canonical source.

## Level 1 — Governance

- `.github/architecture.md`
- `.github/standards.md`
- `.github/domain-boundaries.md`

## Level 2 — Operational Skills

- `.github/skills/create_use_case.md`
- `.github/skills/create_repository_interface.md`
- `.github/skills/generate_e2e_tests.md`
- `.github/skills/generate_implementation_docs.md`
- `.github/skills/refactor_to_clean_architecture.md`
- `.github/skills/validate_module_structure.md`
- `.github/skills/generate_migration_plan.md`

External synced/vendor skills:

- `.github/skills-external/`

If overlap exists, prioritize `.github/skills/` over `.github/skills-external/`.

## Level 3 — Automation

- `.github/automation.md`

## Runtime Behavior

- Interact in the same language as the user.
- Keep code artifacts in English.
- Check `Makefile` before suggesting commands.
- Prefer `make install`, `make format`, `make fix`, `make lint`, and `make test`.
- When implementing and testing new changes, create or update docs in `docs/`.

## Imports Policy

- Import rules are centralized in `.github/standards.md`.
- Use absolute imports only.
