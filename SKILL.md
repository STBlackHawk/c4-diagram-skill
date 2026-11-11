---
name: c4-diagram
description: Draw C4 model diagrams (System Context, Container, Deployment) of a software product from its code, in the diagram-design visual system. Use when a user asks for a C4 diagram, a system context or container diagram, "what goes in and out of the system", "who uses the system", or wants to understand the system a repo builds. Two steps - discover a C4 model from the repos with a file:line source per fact, then render diagram-design HTML/SVG/PNG with the C4 rules and the diagram-design connector rules checked by scripts.
---

# C4 Diagram

Draw C4 model diagrams of a software product. The input is one or more repos. The output is a C4 model file plus three diagrams: System Context, Container and Deployment.

C4 gives the content: element types, technology, one-direction verb labels, title and legend. The [diagram-design](https://github.com/cathrynlavery/diagram-design) system gives the look: node boxes with type tags, orthogonal connectors, labels on masks, zones, a legend strip, and the accessible SVG contract. The renderer applies both. The checker tests both.

Write all text for people in ASD-STE100 Simplified Technical English (skill `ste100`).

## When to use

- A user asks for a C4, system context, container or deployment diagram.
- A user asks what each user type puts into a system and gets out of it.
- A developer wants to understand the system a repo builds.

Do not use for Component or Code diagrams, Dynamic diagrams or System Landscape diagrams. C4 recommends those only in rare cases. Say so and stop at Container. For any other diagram type, use the diagram-design skill directly.

## Two steps

### Step 1: Discover

Read the code, not the docs. Write `c4-model.json` (schema: `references/model-schema.md`). Give each fact a `source` of the form `repo/path:line`. Mark a guess as `"inferred": true`.

Read, in this order, for each repo:

1. Deploy specs and infra: `.do/*.yaml`, `Dockerfile*`, `docker-compose*`, `deploy/`, `cloudbuild*`, `terraform/`, `k8s/`, `serverless*`, `Procfile`, `fly.toml`, `vercel.json`.
2. CI workflows: `.github/workflows/*.yml` (deploy triggers, branches, crons, environments).
3. Config: the one module that reads env vars (`config.*`, `settings.*`, `.env.example`). Each outbound URL or API key names an external system.
4. Entry points: the server bootstrap, route tables, worker and job entry points, queue names, schedulers.
5. Outbound clients: HTTP clients, SDK imports, message publishers, email senders.
6. Data: migrations, schema files, dataset and bucket names, pub/sub topics.
7. Auth: who can call what. Each distinct caller type is a person or a machine caller.

Full checklist and the questions to answer per element: `references/discovery.md`.

Rules of the model:

- A **person** is a human role or a machine caller that uses the system. Give each one `inputs` (what it sends in) and `outputs` (what it gets out), as short noun phrases, and one `main_in` and one `main_out` verb label for the diagram.
- A **software system** you own is the system in scope. A service you do not own or run is an **external system**. A hosted store you configure and own (a database, a bucket) is a **container**, not an external system.
- A **container** is an application or a data store that must run for the system to work. Docker images, JARs and packages are not containers.
- Every **relationship** is one direction and has a verb label ("sends drafts to", never "uses"). A container-to-container relationship names its technology or protocol.
- Put every fact you could not verify in `open_problems`.

Stop and show the model to the user before you draw, when the model has more than 8 people or 8 external systems, or when more than 3 facts are inferred. The user can cut or correct the model.

### Step 2: Draw

Resolve the brand profile first (order and sources: `references/model-schema.md`, "Brand profile"). The short version: a `.c4-diagram` or `.diagram-design` marker next to the model names a slug; the renderer reads `profiles/<slug>.json` next to the model or in the skill, and a saved diagram-design profile `~/.diagram-design/profiles/<slug>.md` when one exists. With no marker and no `--profile`, the output uses the diagram-design default skin. Keep a private brand next to the model, never in the skill.

Render, check, export:

```bash
python3 <skill-dir>/scripts/render_c4.py c4-model.json --out diagrams/ [--profile <slug>] [--dark]
python3 <skill-dir>/scripts/c4_check.py c4-model.json diagrams/
python3 <skill-dir>/scripts/export_png.py diagrams/c4-context.html diagrams/c4-context.png   # needs: pip install playwright && playwright install chromium
```

`render_c4.py` writes `c4-context.html`, `c4-container.html`, `c4-deployment-<env>.html`, `c4-tables.md` (the per-role inputs and outputs table and the element tables in Markdown) and `c4-geometry.json`. `--dark` adds a `-dark` variant of each diagram when the profile has dark tokens. Read every `WARN` line: a name wider than its box, a label that was cut, an arrow that passes behind a node.

`c4_check.py` is the gate. It runs the C4 checklist on the model, the geometry checks on `c4-geometry.json`, and then the vendored diagram-design checkers `self_check.py` (accessible SVG contract, single file, content inside the viewBox, text inside its box) and `verify_geometry.py` (the six connector rules) on every diagram. Fix every FAIL in the model, never in the HTML.

Open the PNG and look at it. Fix an overlap or a crowded row by changing `layout` hints in the model (`gx`, `gy`, `gw`, `route`).

## Notation (built into the renderer)

| C4 element | diagram-design treatment | Type tag | Shows |
|---|---|---|---|
| System in scope | `focal`: accent border, accent tint | `SOFTWARE SYSTEM` | name, description |
| Person | `input`: muted wash, soft border, user icon | `PERSON` | name, description |
| Machine caller | `input`, robot icon | `MACHINE` | name, description |
| External system | `external`: faint fill, faint border, cloud icon | `EXTERNAL` | name, description |
| Container (application) | `backend`: white, ink border | `CONTAINER` | name, technology (mono), description |
| Container (data store) | `store`: ink wash, muted border, database icon | `STORE` | name, technology, description |
| Deployment node | dashed zone with an eyebrow | | name · technology |
| Container instance | `backend` or `store` with an artifact chip and a replica badge | `APP`, `STORE`, or the instance `tag` | name, artifact + version chip, `×N`, description |
| Relationship | one-direction orthogonal arrow, verb label on a paper mask | | label, technology on container and deployment level |

Lines: `link` (HTTP, API, and any path that crosses a deployment node boundary), `muted` (internal calls), `accent` (the one headline path), dashed `5,4` for an async, replication or not-configured path. At most 2 accent elements per diagram: the focal container plus one accent path. The checker counts them.

Type: names in the sans face at 12px 600, technology and labels in the mono face, descriptions in the sans face at 9px, the page title in the serif face. Every coordinate and size sits on the 4px grid.

Every diagram has: a title that names the type and the scope ("System Context diagram for <system>"), a legend strip at the bottom, and an accessible `<title>` and `<desc>` with ids prefixed by the file slug.

Budgets: System Context holds at most 8 people and 8 external systems, with at most 2 arrows per element (one in, one out). The diagram shows `main_in` and `main_out` only, up to 32 characters each. The full `inputs` and `outputs` lists go into the table under the diagram. Container diagrams hold at most 3 flat zones, 12 arrows and labels of 20 characters. Deployment diagrams hold at most 3 nodes per environment. Split a diagram that exceeds them: one deployment diagram per environment, or an overview plus one container diagram per zone.

One deliberate deviation from diagram-design: arrow labels are C4 verb phrases up to 20 characters (32 on the context diagram), not the 14-character caps diagram-design prefers. The mask and the gap rules still hold.

## Diagram-design rules this skill keeps

From `cathrynlavery/diagram-design` (MIT). When the plugin is installed, its `references/type-architecture.md`, `type-deployment.md`, `primitives-core.md` and `style-guide.md` are the long form.

- Paint order: background, zones, arrows, labels, nodes, legend.
- Node box: opaque paper mask, styled box at `rx=6`, rectangular type tag at `rx=2` in the top-left corner, name in sans 600, technology in mono.
- Connector rules: orthogonal only with `r=8` elbows; a 6 to 10px gap between every label mask and its stroke; no stacked strokes; fanned ports 16px apart on a shared edge; no transit behind a non-endpoint box; a label mask never under a later node.
- Zones: `ink @ 0.02` fill, eyebrow on a paper mask in the `soft` role; deployment nodes dashed `4,4`.
- Legend: a horizontal strip under the diagram, never inside it.
- Accessible SVG: `role="img"`, `aria-labelledby`, `<title>` first, slug-prefixed ids.
- Page: `min-width` equals the viewBox width inside an `overflow-x: auto` wrapper, released in print.
- Colours and fonts by semantic role from a profile, never by hex in the code.

## C4 checklist (run before output)

`scripts/c4_check.py` answers the C4 review checklist from the model and the rendered files. Each item must be yes:

- Title names the diagram type and the scope. Legend present.
- Every element has a name, a type and a description. Every container has a technology.
- Every arrow has a one-direction verb label. Container and deployment arrows name a technology or protocol.
- No two elements share a name. No acronym appears without a definition in `glossary`.
- The model has a `source` for every element and relationship, or `inferred: true`.
- At most 2 accent elements. Labels within the length limits. Nodes on the 4px grid.

The full checklist text: `references/c4-rules.md`.

## Output

- `c4-model.json`: the editable model. Commit it next to the diagrams.
- `diagrams/c4-context.html`, `c4-container.html`, `c4-deployment-<env>.html`, optional `-dark` variants, and their `.png` and `.svg` exports.
- `diagrams/c4-tables.md`: Markdown tables to paste under the diagrams (inputs and outputs per role, elements, relationships).

## Keep it current

The model carries `sources`. A scheduled agent can re-run Step 1 on a diff of those files, update the model, and re-render. Pattern: keep `c4-model.json`, the diagrams and a `state.json` of last-seen commits in one repo; on each run, fetch the product repos, diff the watched paths, update the model, render, check, export, publish.
