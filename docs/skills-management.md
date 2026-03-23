# Skills Management

This project supports two skill sources:

- Internal/governed skills: `.github/skills/`
- External ad-hoc skills (installed by CLI tools): `.agents/skills/` (fallback: `.agent/skills/`)

Default internal skills bundled by template:

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

## Sync external skills to governed layout

Use:

```bash
make sync-skills
```

Example external install before sync:

```bash
npx skills add https://github.com/wshobson/agents --skill langchain-architecture
```

What it does:

1. Detects external source in this order:
   - `.agents/skills/`
   - `.agent/skills/`
2. Copies each valid skill (`SKILL.md`) to:
   - `.github/skills-external/<skill-name>/SKILL.md`
3. Skips invalid folders without `SKILL.md`
4. Prunes stale folders from `.github/skills-external/` that no longer exist in source
5. Regenerates a governed `skills-lock.json` from synced skills (hash + timestamp)
6. Cleans installer artifacts after sync:
   - removes `.agents/`
   - removes `.agent/skills/`

## Safety behavior

- If no external source exists, command exits successfully (`0`) without failing CI.
- If source exists but has no skill folders, command exits successfully.
- If a skill folder is malformed, it is skipped and reported.
- `skills-lock.json` is always refreshed from `.github/skills-external/`.
- Cleanup step runs regardless of whether any skill was synced.

## Recommended workflow

1. Install/update external skills via your CLI tool (for example `npx skills ...`).
2. Run `make sync-skills`.
3. Keep your internal curated skills in `.github/skills/` and external vendor skills in `.github/skills-external/`.

## Purge external skills (reset template)

Use:

```bash
make purge-external-skills
```

What it does:

1. Removes all synced external skills from `.github/skills-external/`
2. Removes temporary installer folders (`.agents/`, `.agent/skills/`)
3. Removes governed lock metadata (`skills-lock.json`)
4. Recreates `.github/skills-external/` as an empty folder
