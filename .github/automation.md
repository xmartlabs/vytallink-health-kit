# Automation Policy

This file defines Level 3 enforcement so quality does not depend on model behavior.

## Required Enforcement

- Strict lint and formatting checks.
- CI pipelines for lint/test/security.
- Structure validation checks.
- PR automation (status checks, optional bots).
- Documentation updates in `docs/` when `src/` or `tests/` change.
- Enforced quality sequence before tests: `make format` then `make fix`.

## Baseline Commands

- `make lint`
- `make format`
- `make fix`
- `make test`
- `make ci`

## Implementation Notes

- Keep enforcement deterministic and reproducible.
- Prefer failing fast in CI for boundary or quality violations.
- Keep local workflow aligned with CI (`make ci`).
