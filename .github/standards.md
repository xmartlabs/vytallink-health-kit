# Engineering Standards

This document defines coding and operational standards across tools.

## Language Policy

- User interaction language follows user language.
- Code artifacts are always in English:
  - identifiers
  - docstrings
  - comments
  - generated technical docs

## Python and Environment

- Use Python for generated implementation by default.
- Use `uv` workflows via Makefile commands.
- Do not recommend direct `pip` usage for project dependencies.

## Command Policy

Before suggesting project commands, inspect and prioritize `Makefile` targets.

Primary commands:

- `make install`
- `make add PKG=<package>`
- `make format`
- `make lint`
- `make test`

## Code Quality

- Enforce type hints whenever practical.
- Prefer `Pydantic` for structured validation/configuration.
- Use Ruff for linting/formatting workflows.
- Run security checks through project lint pipeline.

## Imports

- Use absolute imports only.
- Avoid relative imports (`from .x import y`, `from ..x import y`).

## Prompt Design

For complex LLM prompts, prefer structured XML-like sections:

- `<thinking>`
- `<context>`
- `<instructions>`

## Validation Checklist

Before finalizing generated work:

1. Code artifacts are in English.
2. Relevant quality checks ran (`make lint` and/or targeted tests).
3. Data flow respects raw vs processed boundaries.
4. Implementation changes include/update documentation under `docs/`.
