# Active Architecture

This repository currently has one primary runtime path:

`main.py` -> FastAPI routers -> router dependencies -> service layer -> templates or API schemas

## Active Runtime Path

- `main.py`
  - owns app creation, lifespan wiring, middleware, exception handlers, router registration, shared `httpx.AsyncClient`, and cache provider initialization
- `routers/`
  - HTML routes for explorer pages
- `routers/api/`
  - JSON routes for API consumers
- `routers/dependencies.py`
  - request-scoped chain lookup
  - service construction
  - shared pagination/query parsing
  - common error mapping helpers
- `services/blockchain_service.py`
  - MultiChain RPC abstraction
  - retry logic
  - cached list/count helpers
  - shared windowed list helpers
  - shared newest-block and batched-transaction helpers
- `services/pagination_service.py`
  - canonical pagination calculations and context building
- `services/search_service.py`
  - shared entity search logic
- `schemas/responses.py`
  - JSON response contract boundary
- `templates/`
  - HTML rendering surface for page routes

## Compatibility Surface

The following compatibility behavior is intentionally still supported:

- legacy `/chain/...` HTML routes
- legacy `start`/`count` pagination inputs on API endpoints that now prefer `page`/`count`
- config/state compatibility dictionaries used by older code paths and tests

These are compatibility inputs, not the preferred internal architecture.

## Compatibility-Only Modules

These modules still exist in the repository but are not part of the primary FastAPI request path:

- `multichain.py`
  - legacy synchronous RPC wrapper
- `performance.py`
  - legacy/cache utility surface retained for compatibility and tests

Changes to the active runtime path should not add new dependencies on these modules.

## Current Refactor Direction

The active runtime path has been consolidated around shared helpers for:

- parsed pagination dependencies
- page-info derivation from query params
- paginated RPC window calls
- bounded fallback counts
- recent transaction windowing
- newest-first block paging
- batched transaction fetches
- API response-model mapping helpers

Future cleanup should prefer:

1. keeping `main.py` as the single entrypoint
2. adding behavior to services or shared dependencies before duplicating logic in routers
3. preserving compatibility inputs only when they protect existing URLs or clients
4. isolating or removing compatibility-only modules instead of extending them
