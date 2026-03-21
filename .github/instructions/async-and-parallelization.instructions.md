---
description: Mandatory rules for async parallelization of I/O-bound operations. Applies to all Python code in this service.
applyTo: "**/*.py"
---

<critical>Note: This is a living document and will be updated as we refine our processes. Always refer back to this for the latest guidelines. Update whenever necessary.</critical>

# Async & Parallelization Guidelines

This service already uses **httpx** (async-compatible) and **does not use MongoDB directly** — it pushes data to other H³ services via HTTP. All code MUST be async-first. Any synchronous I/O patterns found during development MUST be migrated to async immediately.

---

## 1. Stack Rules

### HTTP Clients: httpx.AsyncClient

```python
# ❌ WRONG — sync httpx
resp = httpx.get(url, timeout=10.0)

# ✅ CORRECT — async httpx
async with httpx.AsyncClient() as client:
    resp = await client.get(url, timeout=10.0)
```

- Prefer **session-scoped `AsyncClient`** (via DI) over creating one per request.
- Set explicit `timeout` on every HTTP call.

### FastAPI Endpoints

```python
# All endpoints MUST be async def
@router.post("/sync")
async def trigger_sync(service: SyncService = Depends(get_service)):
    return await service.sync_all()
```

---

## 2. Parallelization with `asyncio.gather()`

<critical>Whenever multiple independent I/O operations exist (HTTP calls to external sources, HTTP calls to H³ services), they MUST be parallelized using `asyncio.gather()`. Sequential `await` in a loop is a code-smell that should be flagged and refactored.</critical>

### Pattern: Sequential entity sync → parallel gather

```python
# ❌ WRONG — sequential entity syncs
results = []
for entity in EntityType:
    results.append(await self.sync_entity(entity))

# ✅ CORRECT — parallel entity syncs
results = await asyncio.gather(
    *[self.sync_entity(entity) for entity in EntityType]
)
```

### Pattern: Sequential source fetches → parallel gather

```python
# ❌ WRONG — sequential source fetches
merged = {}
for source in self._sources:
    for item in await source.fetch_locations():
        merged[item.id] = item

# ✅ CORRECT — parallel source fetches, then merge
source_results = await asyncio.gather(
    *[source.fetch_locations() for source in self._sources],
    return_exceptions=True,
)
merged = {}
for result in source_results:
    if not isinstance(result, Exception):
        for item in result:
            merged[item.id] = item
```

### Pattern: Multiple independent calls → gather

```python
# ❌ WRONG — sequential independent calls
locations = await source.fetch_locations()
ships = await source.fetch_ships()
commodities = await source.fetch_commodities()

# ✅ CORRECT — parallel independent calls
locations, ships, commodities = await asyncio.gather(
    source.fetch_locations(),
    source.fetch_ships(),
    source.fetch_commodities(),
)
```

### Error handling with gather

```python
results = await asyncio.gather(*tasks, return_exceptions=True)
successes = [r for r in results if not isinstance(r, Exception)]
failures = [r for r in results if isinstance(r, Exception)]
for err in failures:
    logger.error("Task failed: %s", err)
```

- Use `return_exceptions=True` when partial failures are acceptable (e.g., one source failing shouldn't block others).
- Without it, the first exception cancels all other tasks — use this when all-or-nothing semantics are needed.

### Rate limiting with Semaphore

When calling external APIs, limit concurrency to avoid rate limits or overwhelming the target:

```python
semaphore = asyncio.Semaphore(5)  # max 5 concurrent to external API

async def limited_fetch(source: DataSource, entity: EntityType):
    async with semaphore:
        return await source.fetch(entity)

results = await asyncio.gather(*[limited_fetch(s, e) for s, e in pairs])
```

---

## 3. Dependency-Aware Ordering

When entities have import dependencies (e.g., locations must exist before distances), use **phase-based parallelization**:

```python
# Phase 1: Independent entities (parallel)
locations, ships, commodities = await asyncio.gather(
    self._import.import_locations(merged_locations),
    self._import.import_ships(merged_ships),
    self._import.import_commodities(merged_commodities),
)

# Phase 2: Dependent entities (parallel among themselves, after Phase 1)
distances, contracts = await asyncio.gather(
    self._import.import_distances(merged_distances),
    self._import.import_contracts(merged_contracts),
)
```

---

## 4. Testing

- Use `pytest-asyncio>=0.25` with `@pytest.mark.asyncio`.
- Use `respx` for mocking httpx calls.

```python
import pytest
import respx

@pytest.mark.asyncio
async def test_sync_all(sync_service):
    with respx.mock:
        respx.get("https://api.example.com/data").respond(json=[...])
        results = await sync_service.sync_all()
        assert len(results) > 0
```

- When testing parallelized code, verify that the number of HTTP calls matches expectations (no N+1 queries).

---

## 5. What NOT to Do

- **Never** use `asyncio.run()` inside an async context — it creates a nested event loop.
- **Never** use `loop.run_until_complete()` in production code — it blocks the event loop.
- **Never** use `time.sleep()` in async code — use `await asyncio.sleep()`.
- **Never** use threading for I/O parallelism when asyncio is available — threads add overhead and complexity.
- **Never** use sync `httpx.get()`/`httpx.post()` — always use `AsyncClient`.
