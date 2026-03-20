> **© 2026 Hexadian Corporation** — Licensed under [PolyForm Noncommercial 1.0.0 (Modified)](./LICENSE). No commercial use, no public deployment, no plagiarism. See [LICENSE](./LICENSE) for full terms.

# hhh-dataminer

Game data mining and import orchestration service for **H³ – Hexadian Hauling Helper**.

## Domain

Mines Star Citizen game data (locations, distances, ships, commodities, contracts) from **multiple external sources**, automatically **merges** the results, and orchestrates bulk imports into the H³ backend services.

## Stack

- Python 3.11+ / FastAPI
- Hexagonal architecture (Ports & Adapters)
- opyoid (dependency injection)
- httpx (HTTP client for data sources + HHH service calls)
- pydantic-settings

## Prerequisites

- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
```

## Run

```bash
uv run uvicorn src.main:app --reload --port 8008
```

## Test

```bash
uv run pytest
```

## Lint

```bash
uv run ruff check .
```

## Format

```bash
uv run ruff format .
```

## Run in Docker (full stack)

From the monorepo root (`hexadian-hauling-helper`):

```bash
uv run hhh up
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HHH_DATAMINER_PORT` | `8008` | Service port |
| `HHH_DATAMINER_MAPS_SERVICE_URL` | `http://localhost:8003` | Maps service URL |
| `HHH_DATAMINER_SHIPS_SERVICE_URL` | `http://localhost:8002` | Ships service URL |
| `HHH_DATAMINER_COMMODITIES_SERVICE_URL` | `http://localhost:8007` | Commodities service URL |
| `HHH_DATAMINER_CONTRACTS_SERVICE_URL` | `http://localhost:8001` | Contracts service URL |
| `HEXADIAN_AUTH_JWT_SECRET` | `change-me-in-production` | Shared secret for JWT signature verification |

## API

All endpoints require a valid JWT Bearer token with the appropriate permission.

| Method | Endpoint | Permission | Description |
|---|---|---|---|
| `POST` | `/sync` | `hhh:data:sync` | Full sync — fetch all entities from data source and import |
| `POST` | `/sync/{entity}` | `hhh:data:sync` | Sync a single entity type (locations, distances, ships, commodities, contracts) |
| `GET` | `/health` | **Public** | Health check |

## Architecture

```
src/
├── main.py                          # FastAPI app factory + uvicorn
├── domain/
│   └── models/                      # Data transfer models
├── application/
│   ├── ports/
│   │   ├── data_source_port.py      # ABC: fetch game data from external source
│   │   └── import_port.py           # ABC: push data to HHH services
│   └── services/
│       └── sync_service.py          # Orchestration: fetch → transform → import
└── infrastructure/
    ├── config/
    │   ├── settings.py              # pydantic-settings (env prefix: HHH_DATAMINER_)
    │   └── dependencies.py          # opyoid DI Module
    └── adapters/
        ├── inbound/api/             # FastAPI router, DTOs
        └── outbound/
            ├── sources/             # Data source adapters (one per source, each implements DataSourcePort)
            └── hhh/                 # HHH services HTTP client (ImportPort)
```
