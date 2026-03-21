<critical>Note: This is a living document and will be updated as we refine our processes. Always refer back to this for the latest guidelines. Update whenever necessary.</critical>

<critical>**Development Workflow:** All changes go through a branch + PR — no direct commits to `main` unless explicitly instructed. See `.github/instructions/development-workflow.instructions.md`.</critical>

<critical>**PR and Issue linkage:** When creating a pull request from an issue, always mention the issue number in the PR description using `Fixes #N`, `Closes #N`, or `Resolves #N`. This is required for GitHub to auto-close the issue on merge.</critical>

<critical>**Before starting implementation:** Read ALL instruction files in `.github/instructions/` of this repository. Also read the organization-level instructions from the `Hexadian-Corporation/.github` repository (`.github/instructions/` directory). These contain essential rules for workflow, bug history, domain models, and GitHub procedures that you MUST follow.</critical>

<critical>**PR title:** The PR title MUST be identical to the originating issue title. Set the final PR title (remove the `[WIP]` prefix) before beginning implementation, not after.</critical>

<critical>**Async & Parallelization:** All code MUST be async-first. See `async-and-parallelization.instructions.md` for mandatory rules on asyncio.gather and parallelization patterns.</critical>

# Copilot Instructions — hhh-dataminer

## Project Context

**H³ (Hexadian Hauling Helper)** is a Star Citizen companion app for managing hauling contracts, owned by **Hexadian Corporation** (GitHub org: `Hexadian-Corporation`).

This service **mines game data from multiple external sources**, **merges** the results, and **orchestrates bulk imports** into the H³ backend services (maps, ships, commodities, contracts).

- **Repo:** `Hexadian-Corporation/hhh-dataminer`
- **Port:** 8008
- **Stack:** Python · FastAPI · httpx · opyoid (DI) · pydantic-settings

## Architecture — Hexagonal (Ports & Adapters)

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

**Key conventions:**
- Domain models are **pure Python dataclasses** — no Pydantic, no ORM
- DTOs at the API boundary are **Pydantic BaseModel** subclasses
- DI uses **opyoid** (`Module`, `Injector`, `SingletonScope`)
- External API calls use **httpx** (async-compatible HTTP client)
- Hexagonal architecture: DataSourcePort (outbound) fetches from external sources, MergeService merges multi-source data, ImportPort (outbound) pushes to HHH services
