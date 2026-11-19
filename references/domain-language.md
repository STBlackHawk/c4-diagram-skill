# Step 0: Agree the domain language

Before the agent reads the code for the C4 model, it agrees with the user on the words for the domain and the system. The result is `GLOSSARY.md`. Step 1 then names every person, external system, container and arrow with these words.

This step adapts the `domain-modeling` skill from [mattpocock/skills](https://github.com/mattpocock/skills) (MIT, see `LICENSE.mattpocock-skills`). That skill builds the *ubiquitous language* of Domain-Driven Design while you design. This skill applies the same discipline to a system that already exists, and then draws it.

## Why first

A diagram is a set of names on boxes and arrows. If the code says `workspace`, the UI says `team` and the sales deck says `account`, a diagram that picks one at random gives each reader a different system. Agree the words once, and the model, the diagrams and the tables use them everywhere.

## Find what exists

1. If `GLOSSARY-MAP.md` exists at the repo root, the repo has more than one bounded context. Read the map, then each `GLOSSARY.md` it names.
2. Else, if `GLOSSARY.md` (or `CONTEXT.md`, `UBIQUITOUS_LANGUAGE.md`, `docs/glossary.md`) exists, read it. Keep the file where it is.
3. Run the term miner on each repo:

   ```bash
   python3 <skill-dir>/scripts/term_candidates.py <repo> [<repo> ...] --top 40
   ```

   It lists the nouns that the code uses most in table names, type and class names, enums and route paths, each with a `path:line` source. It also lists pairs of words that may name the same thing (`workspace` and `business` both near `members`).

## Interview the user in rounds

Ask one round at a time. Number each question. Give your recommended answer, so that the user can reply "yes". Ask only the questions whose answers do not depend on an open question. Find facts yourself in the code. Ask the user only for decisions.

Round 1, the system and its users:

- What does the system deliver, and to whom, in one sentence?
- Which user types exist? Give each one a canonical name. Propose a name from the role tables and auth code, and show the code words you found.
- Which machine callers exist (agents, CI, partner software)?

Round 2, the core terms:

- For each candidate term that names a domain thing, give a definition of what it **is**, in one or two sentences.
- When the code, the UI and the docs use different words for one thing, pick one canonical term. Put the others under `_Avoid_`.
- When one word does two jobs ("account" means the customer in one file and the login in another), split it into two terms.

Round 3, the boundaries (only for a large system):

- Do the terms fall into separate bounded contexts (for example Ordering and Billing)? Which containers own each one?
- Where do two contexts share a term with different meanings?

Use concrete scenarios to test a boundary: "A customer cancels one book of three. Is that a cancellation of the order, or a return?" When the user states how something works, check the code. If the code disagrees, say so with the `path:line`, and ask which is right.

## Write the glossary at once

When the user settles a term, write it into `GLOSSARY.md` in the same turn. Do not collect terms for the end. Create the file when the first term is settled.

```md
# {System or context name}

{One or two sentences: what this system or context is, and why it exists.}

## Language

**Customer**:
A person who orders books from the shop.
_Avoid_: client, buyer, account

**Order**:
A request from a customer to buy one or more books at one price.
_Avoid_: purchase, basket
```

Rules:

- Define what a thing **is**, not what it does or how the code stores it. No table names, no file paths, no implementation details.
- Be opinionated. One canonical term per concept. Synonyms go under `_Avoid_`.
- Keep only terms of this domain. General programming words (timeout, request, cache) do not go in.
- Group terms under subheadings when clear clusters appear.
- For more than one bounded context, put a `GLOSSARY-MAP.md` at the root that lists each context, its `GLOSSARY.md` and how the contexts relate.

An agent-written glossary that the user did not read is worse than no glossary. Show each new term to the user before you write it.

## Decisions

Offer an architecture decision record (ADR) in `docs/adr/NNNN-slug.md` only when all three are true: the decision is hard to reverse, a reader would not expect it without context, and it was a real trade-off. Write it in one to three sentences: the context, the decision, the reason.

## Gate to Step 1

Stop and show the glossary. Start Step 1 only when the user says that the words are right. Then:

- Set `domain.glossary` in `c4-model.json` to the glossary path (or `domain.glossary_map` to `GLOSSARY-MAP.md`).
- Name each person, external system and container with a glossary term, or with a name built from glossary terms.
- Give each container its bounded `context` when the repo has more than one.
- When the code uses a word from `_Avoid_`, keep the canonical term in the model, and record the code word in `open_problems`.

`scripts/c4_check.py` fails a model that uses an `_Avoid_` word in a name, description or label, or a person whose name is not a glossary term.
