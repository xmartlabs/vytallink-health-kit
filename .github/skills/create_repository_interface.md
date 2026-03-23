# Skill: create_repository_interface

## Purpose

Design repository interfaces that isolate persistence details from domain/application logic.

## Required Input

- Entity or aggregate name.
- Required operations (CRUD/query methods).
- Consistency and transactional constraints.

## Output Format

- Interface/protocol name and method signatures.
- Typed models involved in each operation.
- Adapter implementation guidance (infra side).
- Test strategy for contract behavior.

## Execution Rules

1. Keep domain independent from infrastructure implementations.
2. Use absolute imports and type hints.
3. Prefer minimal and explicit method contracts.
