---
description: Search FastAPI patterns, best practices, and implementation guides
---

# FastAPI Agents Skill

A searchable knowledge base for FastAPI development — covering routing, dependency injection, middleware, schemas, authentication, testing, performance, and error handling. Use this skill whenever working on FastAPI code in this project.

## Prerequisites

Check if Python is installed:

```bash
python3 --version || python --version
```

---

## How to Use This Skill

When working on FastAPI tasks (implementing routes, writing tests, adding middleware, handling auth, optimizing performance), search the relevant domain first.

### Step 1: Identify the Domain

| Domain | Use When |
|--------|----------|
| `routing` | Adding/modifying path operations, routers, path/query params |
| `dependencies` | Dependency injection, `Depends()`, lifespan events |
| `middleware` | CORS, logging, rate limiting, request/response middleware |
| `schemas` | Pydantic models, request/response schemas, validation |
| `auth` | OAuth2, JWT, API keys, security utilities |
| `testing` | Writing tests, TestClient, async tests, mocking |
| `performance` | Async patterns, background tasks, caching, WebSockets |
| `errors` | Exception handlers, HTTP exceptions, custom error responses |

### Step 2: Search

```bash
python3 .shared/fastapi-agents/scripts/search.py "<query>" --domain <domain> [-n <max_results>]
```

Leave out `--domain` to auto-detect from your query.

### Step 3: Apply Results

Synthesize the search results and implement accordingly.

---

## Example Searches

```bash
# How to structure routers
python3 .shared/fastapi-agents/scripts/search.py "router prefix tags include" --domain routing

# Dependency injection patterns
python3 .shared/fastapi-agents/scripts/search.py "depends database session" --domain dependencies

# Adding JWT auth
python3 .shared/fastapi-agents/scripts/search.py "JWT bearer token oauth2" --domain auth

# Writing async tests
python3 .shared/fastapi-agents/scripts/search.py "async test client pytest" --domain testing

# Handling validation errors
python3 .shared/fastapi-agents/scripts/search.py "request validation error handler" --domain errors

# Caching with Redis
python3 .shared/fastapi-agents/scripts/search.py "redis cache background task" --domain performance

# CORS middleware setup
python3 .shared/fastapi-agents/scripts/search.py "CORS allow origins middleware" --domain middleware

# Pydantic response models
python3 .shared/fastapi-agents/scripts/search.py "response model schema validator" --domain schemas
```

---

## Common FastAPI Rules

### Routing

| Rule | Do | Don't |
|------|----|-------|
| **Use APIRouter** | Split into routers per feature, include in `main.py` | Put all routes in `main.py` |
| **Response models** | Always set `response_model=` on endpoints | Return raw dicts |
| **Status codes** | Use `status_code=status.HTTP_201_CREATED` | Use raw integers |
| **Tags** | Add `tags=["resource"]` for OpenAPI grouping | Leave tags empty |

### Dependencies

| Rule | Do | Don't |
|------|----|-------|
| **Reuse sessions** | Yield dependencies for DB/Redis sessions | Open connections per request |
| **Lifespan** | Use `lifespan` context manager for startup/shutdown | Use deprecated `@app.on_event` |
| **Type hints** | Always annotate `Depends()` with the return type | Use untyped dependencies |

### Schemas

| Rule | Do | Don't |
|------|----|-------|
| **Separate schemas** | Use `Create`, `Update`, `Response` variants | Reuse one schema for everything |
| **Field validators** | Use `@field_validator` for custom validation | Validate in route handlers |
| **Config** | Use `model_config = ConfigDict(from_attributes=True)` | Use deprecated `class Config` |

### Testing

| Rule | Do | Don't |
|------|----|-------|
| **Override deps** | Use `app.dependency_overrides` for mocking | Hit real DB in tests |
| **Fixtures** | Create reusable `client` and `db` fixtures | Repeat setup code per test |
| **Async tests** | Use `pytest-asyncio` with `anyio` backend | Mix sync/async test patterns |

---

## Pre-Implementation Checklist

- [ ] Route has `response_model`, `status_code`, `summary`, and `tags`
- [ ] DB/cache access uses `Depends()` with yielding sessions
- [ ] Pydantic schemas validated with `model_config = ConfigDict(from_attributes=True)`
- [ ] Auth protected routes use security dependency
- [ ] Errors return structured JSON via exception handlers
- [ ] Tests override dependencies, don't hit real services
- [ ] Async endpoints use `async def`, CPU-bound work uses `run_in_executor`
