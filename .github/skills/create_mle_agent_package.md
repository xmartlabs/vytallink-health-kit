# Skill: create_mle_agent_package

## Purpose

Generate a reusable, pip-installable MLE agent package aligned with this repository governance, suitable for FastAPI, serverless runtimes, or chatbot adapters.

This skill produces a deterministic specification and file plan only. It must not generate full business implementation when the request scope is only package scaffolding/specification.

## Governance References (Mandatory)

- `.github/architecture.md`
- `.github/standards.md`
- `.github/domain-boundaries.md`
- `.github/automation.md`

## Required Input

- `agent_name` (string, snake_case package name).
- `prediction_type` (enum: `classification` | `regression` | `llm` | `hybrid`).
- `runtime_target` (enum: `fastapi` | `lambda` | `cloud_function` | `hybrid`).
- `include_chat_adapter` (boolean).
- `include_data_endpoint` (boolean).
- `include_healthcheck` (boolean).
- `llm_provider` (enum: `openai` | `google` | `ollama` | `lmstudio`).

## Output Format

- `package_name`: resolved from `agent_name`.
- `runtime_profile`: resolved from `runtime_target`.
- `artifact_tree`: deterministic ordered list of paths to create.
- `constraints_report`: pass/fail checklist for architecture and standards.
- `test_plan`: minimal deterministic unit test list.
- `runbook`: install/run/test commands.

### Required Artifact Tree

Always include (ordered):

- `src/{agent_name}/__init__.py`
- `src/{agent_name}/agent.py`
- `src/{agent_name}/config.py`
- `src/{agent_name}/observability.py`
- `src/{agent_name}/graph/__init__.py`
- `src/{agent_name}/graph/state.py`
- `src/{agent_name}/graph/nodes.py`
- `src/{agent_name}/graph/builder.py`
- `src/{agent_name}/model/__init__.py`
- `src/{agent_name}/model/llm.py`
- `src/{agent_name}/prompts/__init__.py`
- `src/{agent_name}/prompts/defaults.py`
- `src/{agent_name}/prompts/loader.py`
- `src/{agent_name}/tools/__init__.py`
- `tests/test_{agent_name}_config.py`
- `tests/test_{agent_name}_graph.py`
- `tests/test_{agent_name}_api.py` (only when `runtime_target` includes `fastapi`)
- `docs/{agent_name}-implementation.md`

Conditional artifacts:

- Add adapter module(s) under `src/{agent_name}/adapters/` only when requested by runtime flags.
- Add chat adapter module only when `include_chat_adapter=true`.
- Add data endpoint schema/router only when `include_data_endpoint=true` and runtime includes `fastapi`.
- Add healthcheck endpoint only when `include_healthcheck=true` and runtime includes `fastapi`.

## Architectural Constraints (Hard Rules)

1. Core (`graph`, `model`, `prompts`, `tools`, `agent`) must not depend on FastAPI or external transport SDKs.
2. Adapters may depend only on service/application entry points, never on infrastructure internals.
3. No business logic inside adapters (only translation, validation, orchestration wiring).
4. All imports must be absolute.
5. All public interfaces must have type hints.
6. If FastAPI is included, request/response schemas must use Pydantic.
7. Respect layer direction from `.github/architecture.md`:
   - domain/application independent from infrastructure.
   - infrastructure depends on contracts, not the opposite.

## Quality Guardrails

- Generate minimal unit tests for config loading, graph construction, and selected adapter wiring.
- Include English docstrings in all public modules and functions.
- Include structured logging hooks in service layer (`observability.py`, orchestration boundaries).
- Include one minimal usage snippet in docs showing package import and invocation path.
- Keep output deterministic: same input must yield same artifact tree and checklist.

## Execution Steps (Runbook)

1. Install locally:
   - `pip install -e .`
2. If FastAPI runtime is included, run locally:
   - `uvicorn api:app --reload`
3. Run tests with project workflow:
   - `make test`

## Determinism and Reproducibility Rules

- Sort generated artifact paths lexicographically within each section.
- Keep stable naming conventions from `agent_name` without random suffixes.
- Do not infer optional components unless explicitly enabled by input flags.
- Emit a fixed-order compliance checklist (architecture, boundaries, standards, automation).

## Failure Conditions (Must Fail)

Return `FAIL` and stop generation when any of the following is detected:

- Core module imports FastAPI, cloud runtime SDK, or adapter modules.
- Adapter includes business rules instead of transport translation/wiring.
- Relative imports are present.
- Missing type hints in public interfaces.
- FastAPI runtime selected but schemas are not Pydantic-based.
- Requested artifact tree violates repository boundaries (`src/`, `tests/`, `docs/`).
- Required governance checks are skipped.

## Compliance Checklist Template

- `architecture_governance`: PASS/FAIL
- `standards_governance`: PASS/FAIL
- `domain_boundaries_governance`: PASS/FAIL
- `automation_governance`: PASS/FAIL
- `determinism_reproducibility`: PASS/FAIL

## Execution Rules

1. Apply all governance files before proposing artifacts.
2. Generate only scoped outputs required by input flags.
3. Prefer minimal structure that satisfies architecture and testability.
4. Keep all code artifacts and technical docs in English.
5. Require a PASS checklist before declaring completion.
