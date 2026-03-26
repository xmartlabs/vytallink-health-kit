# Skill: generate_implementation_docs

## Purpose

Create or update implementation documentation in `docs/` whenever new code is implemented and tested.

## Required Input

- Feature or change summary.
- Files/modules changed.
- Tests executed and outcomes.
- Known limitations or follow-up tasks.

## Output Format

- Documentation file path under `docs/`.
- What changed.
- Why it changed.
- How it was validated (commands + results).
- Risks and next steps.

## Execution Rules

1. Always write docs in English.
2. Keep documentation concise and implementation-focused.
3. Include test evidence and validation commands.
4. Create `docs/` if missing.
5. Use `docs/implementation-template.md` as the default structure.
6. When documenting VytalLink-facing changes, include any request-volume, timeout, retry, caching, or backend-saturation considerations that operators should know.
