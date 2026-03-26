# Skill: plan_and_execute_feature

## Purpose

Deliver a feature through explicit orchestration phases with architecture-safe execution.

## Required Input

- Feature request.
- Business outcome.
- Affected modules and boundaries.
- Non-functional requirements (performance, security, observability).
- Test expectations.

## Output Format

- Phase report (1 to 5).
- Approved implementation plan.
- Selected skills map.
- Code/test/doc change summary.
- Validation checklist with pass/fail evidence.

## Phases

### Phase 1 - Planning

- Clarify scope, assumptions, and acceptance criteria.
- Build a step-by-step implementation plan.
- If the feature touches VytalLink data access, notebooks, chat loops, or observability demos, explicitly assess backend saturation risk and how the design limits repeated requests.

### Phase 2 - Architecture Validation

- Validate intended changes against:
  - `.github/architecture.md`
  - `.github/domain-boundaries.md`
- Adjust plan to preserve dependency direction and module placement.

### Phase 3 - Skill Selection

- Select internal operational skills needed for execution.
- Define invocation order and dependencies between skills.

### Phase 4 - Execution

- Implement changes following selected skills and plan order.
- Keep modifications scoped and documented.

### Phase 5 - Validation

- Validate against `.github/automation.md` and `.github/orchestration.md`.
- Review diffs, run required checks, and produce final summary.

## Execution Rules

1. Internal skills have precedence over external synced skills.
2. No direct implementation without completing Phase 1 and Phase 2.
3. Include tests and `docs/` updates when behavior changes.
4. Report open risks and deferred items explicitly.
5. For VytalLink-facing work, prefer plans that reuse fetched data, space outbound requests, and document timeout/backoff controls.
