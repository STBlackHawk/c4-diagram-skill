# Discovery: from code to a C4 model

Read code, not docs. When a doc and the code disagree, the code wins and the disagreement goes into `open_problems`.

## Questions to answer

### The software system

- What does the product deliver, and to whom? One sentence. Source: the root README or CLAUDE.md, confirmed by the route table.
- Which repos make it? Each repo that deploys something is part of the system. A repo that only holds docs or notebooks is not.

### People and machine callers

For each distinct caller type:

| Question | Where to look |
|---|---|
| Who signs in, and how? | auth middleware, session routes, OAuth routes, OTP senders |
| Which roles exist? | role tables, permission checks (`requireAdmin`, `platform_members`), admin route prefixes |
| Which machines call in? | API key middleware, MCP endpoints, webhook routes, CI workflows that call the API |
| What does each one send in? | request schemas on its routes, upload handlers, form parsers |
| What does each one get out? | response schemas, SSE streams, emails sent to that role, exports |

Write `inputs` and `outputs` as noun phrases ("draft messages", "graded rewrites"). Write `main_in` and `main_out` as verb phrases ("sends drafts to", "gets rewrites from").

### External systems

For each outbound URL, SDK or API key in the config module: name the vendor, what the system sends it, and what comes back. Group them (data sources, model providers, payments, email, observability). A store you configure and own is a container, not an external system.

### Containers

For each deploy spec component, Dockerfile, worker entry point, Cloud Run service or job, and data store:

| Field | Where to look |
|---|---|
| name | the deploy spec component name or the service name |
| kind | `app` for anything that runs code, `store` for databases, caches, buckets, queues |
| technology | the base image, the framework, the engine (`Node.js 22, Express`, `Python 3.11, FastAPI`, `Postgres 15`, `Valkey`) |
| description | what it serves or runs, in at most 2 short lines |
| zone | the runtime boundary: the cloud account, region and app it runs in |

### Relationships

For each container: what does it call, read or write? Sources: HTTP client calls with their base URLs, queue producers and consumers, database clients, pub/sub topics. One direction per arrow. Name the protocol (`HTTPS`, `Pub/Sub`, `BullMQ on Valkey`, `TLS`).

### Deployment

For each environment: the deploy trigger (branch, workflow), the hosting node (app platform, project, region), instance counts and sizes, the data store instance it uses. One deployment diagram per environment. Record how data moves between environments (copies, promotions) in `open_problems` or the tables, not on the diagram.

## Evidence

Each element and relationship carries `source: "repo/path:line"`. When you cannot find a fact in code, set `"inferred": true` and say why in `open_problems`. Never fill a gap from memory or from a vendor's marketing page.

## Size control

Before you draw, cut the model to what the reader needs:

- Merge callers that share every input and output.
- Merge external systems that play one role (six search vendors are one "Search and enrichment vendors" element with the names in its description).
- Keep at most 8 people and 8 external systems on the context diagram. Keep the rest in the tables.
