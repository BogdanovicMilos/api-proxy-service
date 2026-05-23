# API Proxy Service

Python service that acts as a generic reverse proxy to external sports APIs. It exposes a single `POST /proxy/execute` endpoint, routes by `operationType`, validates payload, invokes a provider adapter (OpenLiga), and returns a normalized response.

## Stack

- Python 3.12
- FastAPI + uvicorn
- httpx (async upstream calls)
- Pydantic v2

## Run (local)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Optional: copy example.env to .env and adjust knobs (see "Rate limiting and exponential backoff")
cp example.env .env

uvicorn application.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## Run (Docker Compose)

```bash
# .env is optional — defaults in application/config/settings.py apply if absent
cp example.env .env

docker compose up --build
```

The service binds on `localhost:8000`. To run detached: `docker compose up -d --build`. To stop: `docker compose down`.

Healthcheck: `GET /healthcheck` → `{"message": "Ok"}`

## Pre-commit hooks

Hook config lives in [.pre-commit-config.yaml](.pre-commit-config.yaml) (trailing whitespace, JSON/YAML/XML formatting, merge conflict / large file / private key detection, etc.). Install once per clone:

```bash
pip install -r requirements.dev.txt   # installs pre-commit
pre-commit install                    # wires it into .git/hooks/pre-commit
```

After that every `git commit` runs the hooks on staged files. To run them against the whole repo on demand:

```bash
pre-commit run --all-files
```

To bump pinned hook versions:

```bash
pre-commit autoupdate
```

## Endpoint

`POST /proxy/execute`

### Request

```json
{
  "operationType": "ListLeagues",
  "payload": { }
}
```

### Response

```json
{
  "requestId": "...",
  "operationType": "ListLeagues",
  "data": { /* normalized payload */ }
}
```

### Error

Returned for 4xx and 5xx outcomes:

```json
{
  "error": "human-readable message",
  "code": "unknown_operation | payload_validation_error | upstream_failed | internal_error",
  "details": ["..."],
  "requestId": "..."
}
```

## Supported operations

### 1. `ListLeagues`

Payload (empty):

```json
{ "operationType": "ListLeagues", "payload": {} }
```

Normalized item:

```json
{ "id": 4608, "name": "1. Fußball-Bundesliga 2023/2024", "shortcut": "bl1", "season": "2023", "sport": "Fußball" }
```

Example:

```bash
curl -s -X POST http://127.0.0.1:8000/proxy/execute \
  -H 'Content-Type: application/json' \
  -d '{"operationType":"ListLeagues","payload":{}}'
```

### 2. `GetLeagueMatches`

Payload:

| field | type | required |
| --- | --- | --- |
| `leagueShortcut` | string | yes |
| `season` | string | yes |

Returns a list of normalized matches (see GetMatch).

```bash
curl -s -X POST http://127.0.0.1:8000/proxy/execute \
  -H 'Content-Type: application/json' \
  -d '{"operationType":"GetLeagueMatches","payload":{"leagueShortcut":"bl1","season":"2023"}}'
```

### 3. `GetTeam`

OpenLiga has no direct `/team/{id}` endpoint, so we fetch the league/season roster and pick the requested team.

Payload:

| field | type | required |
| --- | --- | --- |
| `leagueShortcut` | string | yes |
| `season` | string | yes |
| `teamId` | int | yes |

Normalized:

```json
{ "id": 7, "name": "Borussia Dortmund", "shortName": "Dortmund", "iconUrl": "https://..." }
```

```bash
curl -s -X POST http://127.0.0.1:8000/proxy/execute \
  -H 'Content-Type: application/json' \
  -d '{"operationType":"GetTeam","payload":{"leagueShortcut":"bl1","season":"2023","teamId":7}}'
```

### 4. `GetMatch`

Payload:

| field | type | required |
| --- | --- | --- |
| `matchId` | int | yes |

Normalized:

```json
{
  "id": 66630,
  "kickoff": "2023-08-18T20:30:00",
  "isFinished": true,
  "leagueId": 4608,
  "leagueName": "1. Fußball-Bundesliga 2023/2024",
  "team1": { "id": 134, "name": "...", "shortName": "...", "iconUrl": "..." },
  "team2": { "id": 40,  "name": "...", "shortName": "...", "iconUrl": "..." },
  "finalScore": { "team1": 0, "team2": 4, "label": "Endergebnis" },
  "goals": [ { "id": ..., "scoreTeam1": 0, "scoreTeam2": 1, "minute": 32, "scorer": "...", "isPenalty": false, "isOwnGoal": false, "isOvertime": false } ]
}
```

```bash
curl -s -X POST http://127.0.0.1:8000/proxy/execute \
  -H 'Content-Type: application/json' \
  -d '{"operationType":"GetMatch","payload":{"matchId":65046}}'
```

## How the Decision Mapper works

The mapper lives in [application/proxy/mapper.py](application/proxy/decision_mapper.py). It is a small registry of `Operation` entries — one per supported `operationType`. Each entry bundles three things:

1. **`payload_model`** — a Pydantic model that validates `payload` and produces a typed object. Validation failures yield a 400 with field-level reasons.
2. **`call`** — an async function that translates the validated payload into a `SportsProvider` method invocation.
3. **`normalize`** — a pure function that maps the provider's raw response into a provider-agnostic shape.

`POST /proxy/execute` in [application/api/routers/proxy.py](application/api/routers/proxy.py) is the single entry point. It:

1. Parses the request body (`operationType` + `payload`).
2. Calls `resolve_operation(operationType)` → 400 if unknown.
3. Calls `validate_payload(op, payload)` → 400 with details if invalid.
4. Invokes `op.call(provider, validated)` against the configured provider.
5. Calls `op.normalize(result.data)` and returns the normalized response.

Adding a new operation = adding a new `Operation` entry to `_OPERATIONS`. No changes to the router.

## Adapter pattern

The interface is [application/providers/base.py](application/providers/base.py):

```python
class SportsProvider(Protocol):
    name: str
    async def list_leagues(self) -> ProviderResult: ...
    async def get_league_matches(self, league_shortcut: str, season: str) -> ProviderResult: ...
    async def get_team(self, league_shortcut: str, season: str, team_id: int) -> ProviderResult: ...
    async def get_match(self, match_id: int) -> ProviderResult: ...
```

`OpenLigaProvider` in [application/providers/openliga/provider.py](application/providers/openliga/provider.py) is the only adapter; it encapsulates the base URL `https://api.openligadb.de` and all path/parameter shapes. The proxy/decision code never references openligadb.

Shared HTTP — rate limiting, retries, audit logging of upstream calls — lives in [application/providers/http/](application/providers/_http/) and is reused by every adapter via `RateLimitedHttpClient`.

Provider selection is driven by the `SPORTS_PROVIDER` env var (see [application/providers/registry.py](application/providers/registry.py)). To add another provider:
  1. Create `application/providers/<name>/` with a `SportsProvider` subclass that uses `RateLimitedHttpClient`.
  2. Register it in `_PROVIDERS` in `registry.py`.
  3. Set `SPORTS_PROVIDER=<name>` in env to activate.

## Rate limiting and exponential backoff

Configured per-provider inside the adapter — all knobs are env vars consumed by [application/config/settings.py](application/config/settings.py):

| env var | default | meaning |
| --- | --- | --- |
| `SPORTS_PROVIDER` | `openliga` | which adapter to use |
| `OPENLIGA_BASE_URL` | `https://api.openligadb.de` | provider base URL |
| `OPENLIGA_TIMEOUT_SECONDS` | `10.0` | per-request HTTP timeout |
| `OPENLIGA_RATE_LIMIT_PER_SECOND` | `5.0` | token-bucket refill rate |
| `OPENLIGA_RATE_LIMIT_BURST` | `10` | token-bucket capacity |
| `OPENLIGA_MAX_RETRIES` | `3` | retry attempts on transient errors |
| `OPENLIGA_BACKOFF_BASE_SECONDS` | `0.2` | base delay; doubled each retry |
| `OPENLIGA_BACKOFF_MAX_SECONDS` | `5.0` | per-retry delay cap |
| `OPENLIGA_BACKOFF_JITTER_SECONDS` | `0.1` | uniform random jitter added each retry |
| `LOG_BODY_TRUNCATE_CHARS` | `512` | truncate request/response body previews |

- **Rate limiting** is an in-process async token bucket ([application/providers/http/rate_limit.py](application/providers/_http/rate_limit.py)). Every upstream call awaits `bucket.acquire()`.
- **Backoff** triggers on transient HTTP statuses (`408, 425, 429, 500, 502, 503, 504`) and transport errors (timeouts, connection errors). Delay = `min(MAX, BASE * 2^attempt) + uniform(0, JITTER)`. After `MAX_RETRIES` exhausted, the request fails with `502 upstream_failed`.

## Audit and logging layer

Implemented in [application/logging_layer/audit.py](application/logging_layer/audit.py). Logs are structured JSON lines on stdout. Every line carries `requestId`, `ts`, `level`, `event`, and event-specific fields.

Events emitted per request:

| event | when | key fields |
| --- | --- | --- |
| `request_in` | middleware, on inbound | method, path, headers (redacted), body_size, body_preview |
| `proxy_dispatch_start` | router, before resolve | operationType, payload_keys |
| `proxy_validation` | after schema check | outcome (pass/fail), reasons |
| `upstream_call` | per upstream attempt | provider, target_url, status_code, latency_ms, attempt |
| `upstream_error` | transport failure | provider, target_url, error, detail, attempt |
| `proxy_outcome` | end of dispatch | provider, target_url, upstream_status, upstream_latency_ms, total_ms, outcome |
| `request_out` | middleware, on outbound | status_code, body_size, body_preview, duration_ms |

Sensitive headers (`authorization`, `cookie`, `set-cookie`, `x-api-key`) are redacted. Bodies are truncated to `LOG_BODY_TRUNCATE_CHARS`.

### Sample log

```json
{"ts":"2026-05-22T20:33:03.188Z","level":"INFO","logger":"audit","requestId":"1846de40-742a-4faa-9af6-8bfe2b9407c9","msg":"upstream_call","event":"upstream_call","provider":"openliga","target_url":"https://api.openligadb.de/getavailableleagues","status_code":200,"latency_ms":384.09,"attempt":1}
{"ts":"2026-05-22T20:33:03.189Z","level":"INFO","logger":"audit","requestId":"1846de40-742a-4faa-9af6-8bfe2b9407c9","msg":"proxy_outcome","event":"proxy_outcome","operationType":"ListLeagues","provider":"openliga","target_url":"https://api.openligadb.de/getavailableleagues","upstream_status":200,"upstream_latency_ms":384.09,"total_ms":385.32,"outcome":"success"}
{"ts":"2026-05-22T20:33:03.191Z","level":"INFO","logger":"audit","requestId":"1846de40-742a-4faa-9af6-8bfe2b9407c9","msg":"request_out","event":"request_out","status_code":200,"body_size":76328,"body_preview":"{\"requestId\":\"1846de40...","duration_ms":446.56}
```

## Middleware

[application/api/middleware.py](application/api/middleware.py) installs `RequestLoggingMiddleware`:

- Generates a UUID `requestId` if neither `x-request-id` header nor body `requestId` is provided.
- Sets the per-request `request_id_ctx` ContextVar so every log line emitted during the request (router, adapter, retries) carries the same id.
- Emits `request_in` / `request_out` events with method, path, status, sizes, and truncated body previews.
- Redacts sensitive headers.
- Echoes `x-request-id` back as a response header.

## Error handling

| condition | HTTP | code |
| --- | --- | --- |
| Unknown `operationType` | 400 | `unknown_operation` |
| Invalid JSON body | 400 | `payload_validation_error` |
| Payload schema violation | 400 | `payload_validation_error` (with field-level details) |
| Upstream transient failure after retries | 502 | `upstream_failed` |
| Anything else | 500 | `internal_error` |

All errors share the same `ErrorPayload` shape.
