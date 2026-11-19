#!/usr/bin/env python3
"""List candidate domain terms from code: table, type, class and enum names and route paths, with a source per term."""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__", "vendor", ".next", "coverage", "target"}
EXTS = {".sql", ".ts", ".tsx", ".js", ".py", ".go", ".java", ".kt", ".cs", ".rb", ".rs", ".prisma", ".graphql", ".proto"}
PATTERNS = {
    "table": re.compile(r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:[\w\"]+\.)?\"?(\w+)", re.I),
    "type": re.compile(r"\b(?:interface|type|class|enum|struct|record|model|message)\s+([A-Z]\w+)"),
    "go type": re.compile(r"\btype\s+([A-Z]\w+)\s+struct"),
    "route": re.compile(r"""['"`](/(?:api/)?[a-z][\w\-/:{}]*)['"`]"""),
}
# Words every codebase uses. They are not domain terms.
GENERIC = set(
    """id ids data info item items config configs setting settings option options param params props state type types base abstract
    impl default error errors exception request requests response responses handler handlers service services client clients util utils
    helper helpers manager factory provider providers schema schemas model models dto input output result results context value values
    list map key keys name names test tests mock mocks api v1 v2 v3 app main index get set create update delete new old internal public
    private status meta metadata payload body query args event events log logs job jobs queue task tasks worker http json url uri file files
    path entry record records row rows table tables view views page pages component components hook hooks route routes router store
    cache token tokens session sessions auth user users admin health ping by for of the and to from with at in on is""".split()
)


def words(identifier: str) -> list[str]:
    parts = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", identifier).replace("_", " ").replace("-", " ").replace("/", " ")
    out = []
    for w in parts.lower().split():
        if w.startswith((":", "{", "$", "[")):
            continue
        w = re.sub(r"[^a-z0-9]", "", w)
        if w.isdigit() or len(w) < 3:
            continue
        w = re.sub(r"(ies)$", "y", w) if w.endswith("ies") else re.sub(r"(?<!s)s$", "", w)
        if w not in GENERIC:
            out.append(w)
    return out


def scan(roots: list[Path]) -> dict[str, dict]:
    found: dict[str, dict] = defaultdict(lambda: {"count": 0, "kinds": set(), "source": "", "with": defaultdict(int)})
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in EXTS or any(p in SKIP_DIRS or p.startswith(".") for p in path.relative_to(root).parts):
                continue
            if re.search(r"(\.test\.|\.spec\.|_test\.|/tests?/|/__tests__/)", str(path)):
                continue
            try:
                lines = path.read_text(errors="ignore").splitlines()
            except OSError:
                continue
            for n, line in enumerate(lines, 1):
                for kind, rx in PATTERNS.items():
                    for ident in rx.findall(line):
                        ws = words(ident)
                        for w in ws:
                            f = found[w]
                            f["count"] += 1
                            f["kinds"].add(kind)
                            f["source"] = f["source"] or f"{root.name}/{path.relative_to(root)}:{n}"
                            for other in ws:
                                if other != w:
                                    f["with"][other] += 1
    return found


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repos", nargs="+", type=Path)
    ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args()
    found = scan(a.repos)
    top = sorted(found.items(), key=lambda kv: (-len(kv[1]["kinds"]), -kv[1]["count"]))[: a.top]
    print("| Term | Uses | Found in | First source | Often with |")
    print("|---|---|---|---|---|")
    for w, f in top:
        near = ", ".join(o for o, _ in sorted(f["with"].items(), key=lambda kv: -kv[1])[:3])
        print(f"| {w} | {f['count']} | {', '.join(sorted(f['kinds']))} | `{f['source']}` | {near} |")
    names = [w for w, _ in top]
    pairs = []
    for i, a_ in enumerate(names):
        for b in names[i + 1 :]:
            shared = set(found[a_]["with"]) & set(found[b]["with"])
            if len(shared) >= 3 and b not in found[a_]["with"]:
                pairs.append((a_, b, sorted(shared)[:3]))
    if pairs:
        print("\nWords that may name one thing (they appear with the same words, never together). Ask the user:\n")
        for a_, b, shared in pairs[:10]:
            print(f"- `{a_}` and `{b}` (both with {', '.join(shared)})")


if __name__ == "__main__":
    main()
