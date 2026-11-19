"""Read GLOSSARY.md files in the domain-modeling format: **Term**: definition, then _Avoid_: a, b."""

import re
from dataclasses import dataclass, field
from pathlib import Path

TERM = re.compile(r"^\*\*(.+?)\*\*\s*:?\s*(.*)$")
AVOID = re.compile(r"^_Avoid_\s*:\s*(.+)$", re.I)
MAP_LINK = re.compile(r"\]\(([^)]+GLOSSARY\.md)\)")


@dataclass
class Glossary:
    terms: dict[str, str] = field(default_factory=dict)
    meaning: dict[str, str] = field(default_factory=dict)
    avoid: dict[str, str] = field(default_factory=dict)
    files: list[Path] = field(default_factory=list)


def read_file(path: Path, g: Glossary) -> None:
    g.files.append(path)
    term = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if m := TERM.match(line):
            term = m.group(1).strip().rstrip(":")
            g.terms[term.lower()] = term
            g.meaning[term] = m.group(2).strip()
        elif term and (m := AVOID.match(line)):
            for word in m.group(1).split(","):
                if word := word.strip().strip(".").lower():
                    g.avoid[word] = term
        elif term and line and not line.startswith("#") and not g.meaning[term]:
            g.meaning[term] = line
        elif line.startswith("#"):
            term = None


def load(base: Path, domain: dict) -> Glossary:
    """Load the glossary or the glossary map that the model's `domain` names, relative to the model dir."""
    g = Glossary()
    if path := domain.get("glossary_map"):
        map_path = base / path
        for link in MAP_LINK.findall(map_path.read_text()):
            read_file((map_path.parent / link).resolve(), g)
    if path := domain.get("glossary"):
        read_file(base / path, g)
    return g


def find_avoided(text: str, g: Glossary) -> list[tuple[str, str]]:
    """Return (avoided word, canonical term) pairs found in text, matched as whole words."""
    low = text.lower()
    return [(w, t) for w, t in g.avoid.items() if w not in g.terms and re.search(rf"(?<![\w-]){re.escape(w)}s?(?![\w-])", low)]
