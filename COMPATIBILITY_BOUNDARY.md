# Compatibility Boundary

This repository still carries a compatibility surface, but it is not the primary runtime architecture.

## Compatibility Inputs Still Supported

- legacy HTML routes under `/chain/...`
- legacy `start`/`count` pagination inputs where API endpoints now prefer `page`/`count`
- compatibility-oriented config/state dictionaries used by older code paths and regression tests

## Active Runtime Boundary

The active runtime path is:

`main.py` -> `routers/` + `routers/api/` -> `routers/dependencies.py` -> `services/` -> `templates/` or `schemas/responses.py`

Changes inside the active runtime path should prefer:

1. shared router dependencies for query parsing and error mapping
2. service-layer helpers for RPC orchestration, retries, batching, and list/count behavior
3. schema-layer helpers for JSON contract normalization

## Enforcement

`tests/test_architecture_boundaries.py` verifies that the active runtime path does not import `multichain` or `performance`.
