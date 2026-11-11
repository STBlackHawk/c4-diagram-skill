---
name: c4-diagram
description: Draw C4 model diagrams (System Context, Container, Deployment) of a software product from its code. Use when a user asks for a C4 diagram, a system context or container diagram, "what goes in and out of the system", "who uses the system", or wants to understand the system a repo builds. Two steps - discover a C4 model from the repos with a file:line source per fact, then render diagram-design HTML/SVG/PNG with the C4 rules and checklist built in.
---

# C4 Diagram

Draw C4 model diagrams of a software product. The input is one or more repos. The output is a C4 model file plus three diagrams: System Context, Container and Deployment.

Write all text for people in ASD-STE100 Simplified Technical English (skill `ste100`).

## When to use

- A user asks for a C4, system context, container or deployment diagram.
- A user asks what each user type puts into a system and gets out of it.
- A developer wants to understand the system a repo builds.

Do not use for Component or Code diagrams, Dynamic diagrams or System Landscape diagrams. C4 recommends those only in rare cases. Say so and stop at Container.

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

Resolve the brand profile first: the project marker `.c4-diagram` (`profile: <slug>`), else `--profile <slug>` or the model's `profile`, else `profiles/default.json`. Add a brand with a new `profiles/<slug>.json` (same keys as `default.json`). `profiles/amdahl.json` is an example of a brand profile.

Render:

```bash
python3 <skill-dir>/scripts/render_c4.py c4-model.json --out diagrams/ [--profile amdahl]
```

It writes `c4-context.html`, `c4-container.html` and `c4-deployment-<env>.html`, plus `c4-tables.md` (the per-role inputs and outputs table and the element tables in Markdown). Then check and export:

```bash
python3 <skill-dir>/scripts/c4_check.py c4-model.json diagrams/   # C4 checklist + geometry warnings
python3 <skill-dir>/scripts/self_check.py diagrams/c4-context.html   # diagram-design contract
python3 <skill-dir>/scripts/export_png.py diagrams/c4-context.html diagrams/c4-context.png   # needs: pip install playwright && playwright install chromium
```

Open the PNG and look at it. Fix every overlap by changing `layout` hints in the model (`col`, `row`, `zone`), never by editing the HTML.

## Notation (built into the renderer)

| Element | Treatment (diagram-design role) | Shows |
|---|---|---|
| System in scope | `focal` (accent border, accent tint) | name, `[Software system]`, description |
| Person, machine caller | `input` (muted fill) | name, `[Person]` or `[Machine caller]`, description |
| External system | `external` (faint fill, faint border) | name, `[External system]`, description |
| Container (application) | `backend` (white, ink border) | name, `[Container: technology]`, description |
| Container (data store) | `store` (ink wash, muted border) | name, `[Data store: technology]`, description |
| Deployment node | zone rect with an eyebrow | name, technology, instance counts |
| Relationship | one-direction arrow, verb label on a paper mask | label, technology on container level |

Lines: `link` (green) for HTTP and API calls, `muted` for internal calls, dashed for an async or not-configured path. At most 2 accent elements per diagram (the system in scope and one store or path).

Every diagram has: a title that names the type and the scope ("System Context diagram for Amdahl"), a legend strip at the bottom, and an accessible `<title>` and `<desc>`.

Budgets: System Context holds at most 8 people and 8 external systems, with at most 2 arrows per element (one in, one out). The diagram shows `main_in` and `main_out` only. The full `inputs` and `outputs` lists go into the table under the diagram. Container and Deployment diagrams follow the diagram-design budgets: at most 3 flat zones, 12 arrows, orthogonal connectors, labels on masks. Split a diagram that exceeds them.

## C4 checklist (run before output)

`scripts/c4_check.py` answers the C4 review checklist from the model and the rendered files. Each item must be yes:

- Title names the diagram type and the scope. Legend present.
- Every element has a name, a type and a description. Every container has a technology.
- Every arrow has a one-direction verb label. Container arrows name a technology.
- No two elements share a name. No acronym appears without a definition in `glossary`.
- The model has a `source` for every element and relationship, or `inferred: true`.

The full checklist text: `references/c4-rules.md`.

## Output

- `c4-model.json`: the editable model. Commit it next to the diagrams.
- `diagrams/c4-context.html`, `c4-container.html`, `c4-deployment-<env>.html`, and their `.png` and `.svg` exports.
- `diagrams/c4-tables.md`: Markdown tables to paste under the diagrams (inputs and outputs per role, elements, relationships).

## Keep it current

The model carries `sources`. A scheduled agent can re-run Step 1 on a diff of those files, update the model, and re-render. Pattern: keep `c4-model.json`, the diagrams and a `state.json` of last-seen commits in one repo; on each run, fetch the product repos, diff the watched paths, update the model, render, check, export, publish.
