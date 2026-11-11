# C4 model file (`c4-model.json`)

One JSON file holds the whole model. Every element has a `source` (`repo/path:line`) or `"inferred": true`.

```json
{
  "system": {"name": "Amdahl", "description": "GTM context platform ...", "source": "amdahl-app/CLAUDE.md:5"},
  "profile": "amdahl",
  "glossary": {"MCP": "Model Context Protocol", "GTM": "go-to-market"},
  "people": [
    {
      "id": "rep", "name": "Sales rep", "type": "person", "group": "Customer roles",
      "description": "Writes outreach and asks questions in the console",
      "inputs": ["draft messages", "lead lists (CSV)", "search questions"],
      "outputs": ["graded rewrites", "search answers with citations"],
      "main_in": "sends drafts and questions to", "main_out": "gets rewrites and answers from",
      "layout": {"gx": 0, "gy": 1},
      "source": "amdahl-app/src/server/index.ts:464"
    }
  ],
  "external_systems": [
    {
      "id": "anthropic", "name": "Anthropic", "group": "Providers",
      "description": "Claude models for every model call",
      "in_label": "sends prompts to", "out_label": "returns completions to",
      "layout": {"gx": 6, "gy": 0},
      "source": "amdahl-app/src/shared/config.ts:39"
    }
  ],
  "containers": [
    {
      "id": "api", "name": "api", "kind": "app", "technology": "Node.js, Express",
      "description": "REST, MCP, OAuth, SSE", "zone": "do", "focal": true,
      "layout": {"gx": 1, "gy": 0}, "source": "amdahl-app/.do/app-prod.yaml:390"
    },
    {
      "id": "postgres", "name": "Supabase Postgres", "kind": "store", "technology": "Postgres 15",
      "description": "Tenants, runs, keys, optimizer tables", "zone": null,
      "layout": {"gx": 1, "gy": 3, "gw": 4}, "source": "amdahl-app/supabase/migrations"
    }
  ],
  "zones": [
    {"id": "do", "name": "DIGITALOCEAN NYC", "gx": 1, "gy": 0, "gw": 3, "gh": 2}
  ],
  "relationships": [
    {"from": "rep", "to": "api", "label": "HTTPS", "technology": "JSON over HTTPS", "style": "link", "source": "..."},
    {"from": "api", "to": "postgres", "label": "reads and writes", "technology": "service role", "style": "muted", "dashed": false, "source": "..."}
  ],
  "deployment": {
    "environments": [
      {
        "id": "production", "name": "Production",
        "nodes": [
          {"id": "do-prod", "name": "DigitalOcean App Platform, nyc", "technology": "amdahl-app-prod", "gx": 0, "gy": 0, "gw": 3, "gh": 2, "parent": null},
          {"id": "gcp", "name": "GCP project amdahl, us-central1", "technology": "Cloud Run", "gx": 3, "gy": 0, "gw": 3, "gh": 2}
        ],
        "instances": [
          {"container": "api", "node": "do-prod", "count": 1, "size": "professional-s", "layout": {"gx": 0, "gy": 0}}
        ],
        "relationships": [
          {"from": "api", "to": "postgres", "label": "reads and writes", "technology": "TLS", "style": "muted"}
        ]
      }
    ]
  },
  "open_problems": ["The dev market dataset is market_dev in the spec and market in the runbook."]
}
```

## Fields

| Field | Required | Notes |
|---|---|---|
| `system.name`, `system.description` | yes | The one software system in scope |
| `profile` | no | Brand profile slug. The project marker `.c4-diagram` wins |
| `glossary` | when an acronym appears | Each acronym used in a name, description or label |
| `people[]` | yes | `type` is `person` (human) or `machine` (agent, CI, other software that calls in). `group` names the band on the context diagram |
| `people[].inputs`, `outputs` | yes | Short noun phrases. They fill the table, not the diagram |
| `people[].main_in`, `main_out` | yes | Verb labels for the two arrows on the context diagram. Max 28 characters. Leave `main_out` empty when nothing flows back |
| `external_systems[]` | yes | Things you do not own. `in_label`: what the system sends to it. `out_label`: what it sends to the system. Either can be empty |
| `containers[]` | yes | `kind` is `app` or `store`. `technology` is required. `zone` is a zone id or null. `focal: true` on at most one |
| `zones[]` | no | Runtime or trust boundaries on the container diagram, in grid units |
| `layout` | yes for the container diagram | `gx`, `gy` in grid units (one cell is 216 by 112 px). `gw` spans cells. People sit at low `gx`, external systems at high `gx` |
| `relationships[]` | yes | One direction. `label` is a verb phrase. `technology` is required when both ends are containers. `style`: `link` (HTTP, API), `muted` (internal), `accent` (the one headline path). `dashed: true` for async or not-configured. `route: "vh"` makes an off-axis arrow leave the source top or bottom first, then turn into the target side, when the default side-first elbow would pass behind a node (the renderer prints a WARN) |
| `containers[]` without `layout` | no | Appear in the tables only, not on the container diagram |
| `deployment...instances[].id` | no | Needed when one container has two instances in one environment (a stable and a beta sidecar) |
| `deployment.environments[]` | yes for the deployment diagram | One diagram per environment. `nodes` are deployment nodes (grid rects, nestable with `parent`). `instances` place container instances inside nodes |
| `open_problems[]` | no | Facts the code and docs disagree on, or that you could not verify |

## Grid

The container and deployment diagrams use a grid. One cell is 216 px wide and 112 px tall. A node is 176 by 72 px inside its cell. A zone is a rect over `gw` by `gh` cells with a 36 px header. Keep people in column 0, the system's zones in the middle columns, and external systems in the last column, so arrows run left to right.
