# C4 rules used by this skill

Source: c4model.com (introduction, abstractions, diagrams, notation, checklist), read on 2026-11-11.

## Abstractions

- **Software system**: "the highest level of abstraction and describes something that delivers value to its users, whether they are human or not." A team builds and owns it.
- **Container**: an application or a data store, a runtime boundary that must run for the system to work. "Not Docker!" A JAR, DLL or module is not a container.
- **Component**: a grouping of related functionality behind an interface, inside a container. Not separately deployable. Out of scope for this skill.
- **Person**: actors, roles, personas or named individuals who use the system. This skill also uses a person box for a machine caller (an agent, a CI job, a partner app) and marks it `[Machine caller]`.
- **External system**: a software system outside your boundary that you do not own. A hosted store you configure and own is a container.

## Levels this skill draws

| Level | Scope | Shows | Audience |
|---|---|---|---|
| System Context | one software system | the system, its people, the external systems directly connected | everybody |
| Container | one software system | its containers, with technology, and how they talk | technical people in and around the team |
| Deployment | one or more systems in one environment | deployment nodes, container instances, counts | infrastructure and operations |

C4: "the system context and container diagrams are sufficient for most software development teams." Component and Code diagrams are optional and this skill does not draw them.

## Notation rules

- Every diagram has a title that names the type and the scope: "System Context diagram for My Software System".
- Every diagram has a key or legend.
- Every element shows its type (Person, Software System, Container, Component) and a short description "to provide an 'at a glance' view of key responsibilities."
- Every container shows its technology.
- "Every line should represent a unidirectional relationship."
- Every line has a label that matches its direction and intent. "Try to be as specific as possible with the label, ideally avoiding single words like, 'Uses'."
- Container-to-container lines show the technology or protocol.
- Lines show dependencies or data flow. Choose one per diagram set. This skill uses data flow.
- Colours are free, but consistent across the set. Think of black-and-white print and colour blindness, so shape and border style also carry meaning.
- Each diagram "can stand alone, and be (mostly) understood without a narrative."

## Review checklist

Each item is a yes or a no. `scripts/c4_check.py` answers the ones it can read from the model and the files.

General:
- Does the diagram have a title?
- Do you understand what the diagram type is?
- Do you understand what the diagram scope is?
- Does the diagram have a key or legend?

Elements:
- Does every element have a name?
- Do you understand the type of every element?
- Do you understand what every element does?
- Where applicable, do you understand the technology choices associated with every element?
- Do you understand the meaning of all acronyms and abbreviations used?
- Do you understand the meaning of all colours, shapes, icons, border styles and element sizes used?

Relationships:
- Does every arrow have a label describing the intent of that relationship?
- Does the description match the relationship direction?
- Where applicable, do you understand the technology choices associated with every relationship?
- Do you understand the meaning of all acronyms, colours, arrow heads and line styles used?
