#!/usr/bin/env python3
"""Answer the C4 review checklist from c4-model.json, check the rendered geometry, and run the diagram-design checkers."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VAGUE = {"uses", "use", "calls", "call", "talks to", "connects to", ""}
MAX_LABEL, MAX_CONTEXT_LABEL, MAX_ACCENT = 20, 32, 2


def overlaps(a: dict, b: dict, pad: float = 0) -> bool:
    return not (a["x"] + a["w"] + pad <= b["x"] or b["x"] + b["w"] + pad <= a["x"] or a["y"] + a["h"] + pad <= b["y"] or b["y"] + b["h"] + pad <= a["y"])


def segment_hits(seg: list, node: dict) -> bool:
    (x1, y1), (x2, y2) = seg
    if abs(y1 - y2) < 0.5:
        lo, hi = sorted((x1, x2))
        return node["y"] < y1 < node["y"] + node["h"] and lo < node["x"] + node["w"] and hi > node["x"]
    if abs(x1 - x2) < 0.5:
        lo, hi = sorted((y1, y2))
        return node["x"] < x1 < node["x"] + node["w"] and lo < node["y"] + node["h"] and hi > node["y"]
    return False


def check_model(model: dict) -> list[str]:
    problems: list[str] = []
    names: dict[str, str] = {}
    acronyms: set[str] = set()
    glossary = {k.upper() for k in model.get("glossary", {})}

    def check_elem(kind: str, e: dict, need_tech: bool = False) -> None:
        for f in ("id", "name", "description"):
            if not e.get(f):
                problems.append(f"{kind} {e.get('id') or e.get('name')}: missing {f}")
        if need_tech and not e.get("technology"):
            problems.append(f"{kind} {e.get('id')}: missing technology")
        if not e.get("source") and not e.get("inferred"):
            problems.append(f"{kind} {e.get('id')}: no source and not marked inferred")
        if e.get("name") in names:
            problems.append(f"{kind} {e.get('id')}: duplicate name '{e['name']}' (also {names[e['name']]})")
        names[e.get("name", "")] = e.get("id", "")
        for text in (e.get("name", ""), e.get("description", "")):
            acronyms.update(re.findall(r"\b[A-Z]{2,}\b", text))

    for p in model["people"]:
        check_elem("person", p)
        for key in ("main_in", "main_out"):
            if len(p.get(key, "")) > MAX_CONTEXT_LABEL:
                problems.append(f"person {p['id']}: {key} over {MAX_CONTEXT_LABEL} characters")
        if not p.get("main_in"):
            problems.append(f"person {p['id']}: main_in missing")
        if not p.get("inputs") or not p.get("outputs"):
            problems.append(f"person {p['id']}: inputs or outputs list is empty")
    for e in model["external_systems"]:
        check_elem("external system", e)
        if not e.get("in_label") and not e.get("out_label"):
            problems.append(f"external system {e['id']}: no in_label and no out_label")
        for key in ("in_label", "out_label"):
            if len(e.get(key, "")) > MAX_CONTEXT_LABEL:
                problems.append(f"external system {e['id']}: {key} over {MAX_CONTEXT_LABEL} characters")
    for c in model["containers"]:
        check_elem("container", c, need_tech=True)
    focal = [c["id"] for c in model["containers"] if c.get("focal")]
    ids = {x["id"] for x in model["people"] + model["external_systems"] + model["containers"]}
    containers = {c["id"] for c in model["containers"]}
    accent_rels = 0
    for r in model["relationships"]:
        if r["from"] not in ids or r["to"] not in ids:
            problems.append(f"relationship {r['from']} -> {r['to']}: unknown end")
        if r.get("label", "").strip().lower() in VAGUE:
            problems.append(f"relationship {r['from']} -> {r['to']}: label is vague or empty")
        for key in ("label", "technology"):
            if len(r.get(key, "")) > MAX_LABEL:
                problems.append(f"relationship {r['from']} -> {r['to']}: {key} over {MAX_LABEL} characters")
        if r["from"] in containers and r["to"] in containers and not r.get("technology"):
            problems.append(f"relationship {r['from']} -> {r['to']}: container to container without technology")
        if not r.get("source") and not r.get("inferred"):
            problems.append(f"relationship {r['from']} -> {r['to']}: no source and not marked inferred")
        if r.get("style") == "accent":
            accent_rels += 1
        acronyms.update(re.findall(r"\b[A-Z]{2,}\b", r.get("label", "")))
    if len(focal) + accent_rels > MAX_ACCENT:
        problems.append(f"container diagram has {len(focal)} focal containers and {accent_rels} accent arrows, max {MAX_ACCENT} accent elements")
    for acr in sorted(acronyms - glossary):
        problems.append(f"acronym {acr} is not in glossary")
    if len(model["people"]) > 8:
        problems.append(f"context diagram has {len(model['people'])} people, max 8")
    if len(model["external_systems"]) > 8:
        problems.append(f"context diagram has {len(model['external_systems'])} external systems, max 8")
    for env in model.get("deployment", {}).get("environments", []):
        if len(env.get("nodes", [])) > 3:
            problems.append(f"deployment {env['id']} has {len(env['nodes'])} nodes, max 3 (split by environment)")
        for r in env.get("relationships", []):
            if not r.get("technology"):
                problems.append(f"deployment {env['id']}: {r['from']} -> {r['to']} has no protocol or port")
    return problems


def check_geometry(out: Path) -> list[str]:
    problems: list[str] = []
    geo_path = out / "c4-geometry.json"
    if not geo_path.exists():
        return problems
    geometry = json.loads(geo_path.read_text())
    problems += [f"renderer: {w}" for w in geometry.pop("warnings", [])]
    for name, geo in geometry.items():
        for lab in geo["labels"]:
            for n in geo["nodes"]:
                if overlaps(lab, n):
                    problems.append(f"{name}: label '{lab['text']}' overlaps node {n['id']}")
        for i, a in enumerate(geo["labels"]):
            for b in geo["labels"][i + 1:]:
                if overlaps(a, b):
                    problems.append(f"{name}: labels '{a['text']}' and '{b['text']}' overlap")
        for pts in geo["segments"]:
            for j in range(len(pts) - 1):
                for n in geo["nodes"]:
                    if segment_hits([pts[j], pts[j + 1]], n) and j not in (0, len(pts) - 2):
                        problems.append(f"{name}: an arrow passes behind {n['id']}")
        for n in geo["nodes"]:
            if n["w"] < 80:
                problems.append(f"{name}: node {n['id']} narrower than 80px")
            if any(v % 4 for v in (n["x"], n["y"], n["w"], n["h"])):
                problems.append(f"{name}: node {n['id']} is off the 4px grid")
    return problems


def run_checker(script: str, files: list[Path]) -> list[str]:
    path = HERE / script
    if not path.exists() or not files:
        return []
    res = subprocess.run([sys.executable, str(path), *map(str, files)], capture_output=True, text=True)
    if res.returncode == 0:
        return []
    lines = [ln for ln in (res.stdout + res.stderr).splitlines() if ln.strip()]
    return [f"{script}: {ln.strip()}" for ln in lines if not ln.startswith("OK")]


def main() -> None:
    model = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("diagrams")
    problems = check_model(model) + check_geometry(out)
    htmls = sorted(out.glob("c4-*.html"))
    for html in htmls:
        text = html.read_text()
        if "LEGEND" not in text:
            problems.append(f"{html.name}: no legend")
        if not re.search(r"<h1>(System Context|Container|Deployment) diagram for ", text):
            problems.append(f"{html.name}: title does not name type and scope")
    problems += run_checker("self_check.py", htmls)
    problems += run_checker("verify_geometry.py", htmls)
    if problems:
        print("\n".join(f"FAIL {p}" for p in problems))
        sys.exit(1)
    print(f"OK: C4 checklist, geometry, self_check and verify_geometry passed for {len(model['people'])} people, {len(model['external_systems'])} external systems, {len(model['containers'])} containers, {len(htmls)} diagrams")


if __name__ == "__main__":
    main()
