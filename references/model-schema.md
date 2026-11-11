# C4 model file (`c4-model.json`)

One JSON file holds the whole model. Every element has a `source` (`repo/path:line`) or `"inferred": true`. The full example is `examples/bookshop/c4-model.json`.

```json
{
  "system": {"name": "Bookshop", "description": "Online bookshop: customers browse, order and pay. Staff manage stock.", "source": "bookshop/README.md:1"},
  "profile": "default",
  "glossary": {"API": "application programming interface", "HTTPS": "HTTP over TLS"},
  "people": [
    {
      "id": "customer", "name": "Customer", "type": "person", "group": "Public",
      "description": "Browses the catalogue, orders books and pays",
      "inputs": ["searches", "orders", "payment details"],
      "outputs": ["search results", "order confirmations", "invoices (PDF)"],
      "main_in": "browses and orders on", "main_out": "gets confirmations from",
      "layout": {"gx": 0, "gy": 1.5},
      "source": "bookshop/web/src/routes.ts:12"
    }
  ],
  "external_systems": [
    {
      "id": "payments", "name": "Payment provider", "group": "Money",
      "description": "Card payments and refunds",
      "in_label": "creates charges on", "out_label": "posts payment events to",
      "layout": {"gx": 2, "gy": 0},
      "source": "bookshop/api/internal/payments/client.go:18"
    }
  ],
  "containers": [
    {
      "id": "api", "name": "API", "kind": "app", "technology": "Go 1.24, net/http",
      "description": "Orders, stock, payments", "zone": "cloud", "focal": true,
      "layout": {"gx": 2, "gy": 1.5}, "source": "bookshop/api/Dockerfile:1"
    },
    {
      "id": "postgres", "name": "Postgres", "kind": "store", "technology": "Postgres 16",
      "description": "Catalogue, orders, customers, job queue", "zone": "cloud",
      "layout": {"gx": 1, "gy": 2.5}, "source": "bookshop/api/migrations"
    }
  ],
  "zones": [
    {"id": "cloud", "name": "Cloud account · eu-west", "gx": 1, "gy": 1.5, "gw": 3, "gh": 2}
  ],
  "relationships": [
    {"from": "customer", "to": "web", "label": "orders on", "technology": "HTTPS", "style": "link", "source": "bookshop/web/src/routes.ts:12"},
    {"from": "api", "to": "postgres", "label": "reads and writes", "technology": "SQL", "style": "muted", "route": "vh", "source": "bookshop/api/internal/db/pool.go:9"}
  ],
  "deployment": {
    "environments": [
      {
        "id": "production", "name": "Production",
        "nodes": [
          {"id": "compute", "name": "Cloud account · eu-west", "technology": "containers", "gx": 0, "gy": 0, "gw": 3, "gh": 1},
          {"id": "data", "name": "Managed data", "technology": "", "gx": 0, "gy": 2, "gw": 3, "gh": 1}
        ],
        "instances": [
          {"container": "api", "count": 2, "size": "medium", "version": "v2.4.1", "layout": {"gx": 1, "gy": 0}},
          {"container": "postgres", "count": 1, "size": "db-s-2vcpu", "tag": "MANAGED", "layout": {"gx": 0, "gy": 2}}
        ],
        "relationships": [
          {"from": "api", "to": "postgres", "label": "reads and writes", "technology": "TLS:5432", "route": "vh"}
        ]
      }
    ]
  },
  "open_problems": ["The worker reads a queue table the migrations do not create."]
}
```

## Fields

| Field | Required | Notes |
|---|---|---|
| `system.name`, `system.description` | yes | The one software system in scope |
| `profile` | no | Brand profile slug. See "Brand profile" below |
| `glossary` | when an acronym appears | Each acronym used in a name, description or label |
| `people[]` | yes | `type` is `person` (human) or `machine` (agent, CI, other software that calls in). `group` names the band on the context diagram |
| `people[].inputs`, `outputs` | yes | Short noun phrases. They fill the table, not the diagram |
| `people[].main_in`, `main_out` | yes | Verb labels for the two arrows on the context diagram. Max 32 characters. Leave `main_out` empty when nothing flows back |
| `external_systems[]` | yes | Things you do not own. `in_label`: what the system sends to it. `out_label`: what it sends to the system. Either can be empty. Max 32 characters |
| `containers[]` | yes | `kind` is `app` or `store`. `technology` is required. `zone` is a zone id or null. `focal: true` on at most one |
| `zones[]` | no | Runtime or trust boundaries on the container diagram, in grid units |
| `layout` | yes for the container diagram | `gx`, `gy` in grid units. `gw`, `gh` span cells. People sit at low `gx`, external systems at high `gx` or `gy: 0` |
| `relationships[]` | yes | One direction. `label` is a verb phrase, max 20 characters. The renderer cuts a label that does not fit its segment and the checker fails, so keep labels short. `technology` is required when both ends are containers, same limits. `style`: `link` (HTTP, API, crosses a boundary), `muted` (internal), `accent` (the one headline path). `dashed: true` for async or not-configured. `route: "vh"` makes an off-axis arrow leave the source top or bottom first, then turn into the target side, when the default side-first elbow would pass behind a node (the renderer prints a WARN) |
| `containers[]` without `layout` | no | Appear in the tables only, not on the container diagram |
| `deployment.environments[]` | yes for the deployment diagram | One diagram per environment, at most 3 nodes each. `nodes` are deployment nodes (dashed zones) with `technology` as the eyebrow suffix. `instances` place container instances inside nodes |
| `instances[].count`, `size` | no | `count` over 1 draws a replica badge (`×3`). `size` sits at the right of the artifact chip, or in the description line when the chip is full |
| `instances[].artifact`, `version`, `tag` | no | The chip shows `artifact` (default: the container technology) and `version` (default: `size`). `tag` replaces the `APP` or `STORE` type tag, for example `MANAGED` or `POD` |
| `instances[].id` | no | Needed when one container has two instances in one environment (a stable and a beta sidecar) |
| `deployment...relationships[]` | no | `technology` names the protocol and port (`TLS:5432`). The renderer colours a path that crosses a node boundary `link` and one inside a node `muted` unless `style` is set |
| `open_problems[]` | no | Facts the code and docs disagree on, or that you could not verify |

## Grid

The container and deployment diagrams use a grid. One cell is 304 px wide and 128 px tall. A node is 168 by 88 px inside its cell, so the gap between adjacent columns is 136 px (room for a 20-character label) and between adjacent rows 40 px. A zone is a rect over `gw` by `gh` cells with a 36 px header. Steps of 0.25 (`gx: 4.25`, `gy: 1.5`) keep the 4 px grid; other fractions fail the check. Keep people in column 0, the system's zones in the middle columns, and external systems in the last column or the top row, so arrows run left to right or top to bottom.

## Brand profile

The renderer resolves the brand in this order and stops at the first hit:

1. A project marker next to the model: `.c4-diagram` or `.diagram-design` with one line `profile: <slug>`.
2. `--profile <slug>` on the command line.
3. `profile` in the model.
4. `default`.

For that slug it reads, and merges in this order:

- `<model dir>/profiles/<slug>.json`, else `<skill dir>/profiles/<slug>.json`: the keys of `profiles/default.json` (`paper`, `paper2`, `ink`, `muted`, `soft`, `accent`, `accent_tint`, `link`, `font_sans`, `font_mono`, `font_serif`, `font_link`, optional `dark`).
- `~/.diagram-design/profiles/<slug>.md`: a saved diagram-design profile. The renderer reads its semantic-role table (light and dark columns) and typography table, so a brand onboarded once in diagram-design works here without a second file.

Keep a private brand next to the model in `profiles/<slug>.json`, not in the skill.
