#!/usr/bin/env python3
"""Render C4 System Context, Container and Deployment diagrams from c4-model.json."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parent.parent
PX, PY = 272, 128  # grid cell
NW, NH = 168, 88  # node box
CTX_H = 72  # context column node
M, TOP = 40, 48  # page margins
CTX_W = 240  # context column width
CHAR8 = 4.9  # 8px mono
CHAR9 = 5.5  # 9px mono

TREAT = {
    "focal": ("{accent_tint}", "{accent}"),
    "backend": ("#ffffff", "{ink}"),
    "store": ("rgba(28,28,26,0.05)", "{muted}"),
    "external": ("rgba(28,28,26,0.03)", "rgba(28,28,26,0.30)"),
    "input": ("rgba(58,56,51,0.10)", "{soft}"),
}


def wrap(text: str, width: int, max_lines: int = 2) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: width - 1].rstrip() + "…"
    return lines


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Canvas:
    def __init__(self, profile: dict[str, str]) -> None:
        self.p = profile
        self.zones: list[str] = []
        self.arrows: list[str] = []
        self.nodes: list[str] = []
        self.geometry: dict[str, list] = {"nodes": [], "labels": [], "segments": []}

    def c(self, s: str) -> str:
        return s.format(**self.p)

    def node(self, x: float, y: float, w: float, h: float, kind: str, name: str, type_line: str, desc: str, nid: str = "", tech: str = "") -> None:
        fill, stroke = (self.c(v) for v in TREAT[kind])
        cx = x + w / 2
        chars = int((w - 16) / CHAR9)
        lines = wrap(desc, chars, 2) if desc else []
        out = [
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{self.p["paper"]}"/>',
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1"/>',
            f'<text x="{cx}" y="{y + 22}" fill="{self.p["ink"]}" font-size="12" font-weight="600" font-family="{self.p["font_sans"]}" text-anchor="middle">{esc(name)}</text>',
            f'<text x="{cx}" y="{y + 35}" fill="{self.p["soft"]}" font-size="8" font-family="{self.p["font_mono"]}" text-anchor="middle" letter-spacing="0.04em">{esc(type_line)}</text>',
        ]
        if tech:
            out.append(f'<text x="{cx}" y="{y + 47}" fill="{self.p["muted"]}" font-size="8" font-family="{self.p["font_mono"]}" text-anchor="middle">{esc(tech[:chars])}</text>')
        base = y + 62 if tech else y + 50
        for i, line in enumerate(lines):
            out.append(f'<text x="{cx}" y="{base + i * 12}" fill="{self.p["muted"]}" font-size="9" font-family="{self.p["font_mono"]}" text-anchor="middle">{esc(line)}</text>')
        self.nodes.append("\n".join(out))
        self.geometry["nodes"].append({"id": nid or name, "x": x, "y": y, "w": w, "h": h})

    def zone(self, x: float, y: float, w: float, h: float, label: str, sub: str = "") -> None:
        text = label.upper() + (f"  ·  {sub.upper()}" if sub else "")
        lw = int(len(text) * 5.2) + 16
        self.zones.append("\n".join([
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="rgba(28,28,26,0.02)" stroke="rgba(28,28,26,0.10)" stroke-width="0.8"/>',
            f'<rect x="{x + 12}" y="{y + 4}" width="{lw}" height="12" rx="2" fill="{self.p["paper"]}"/>',
            f'<text x="{x + 12 + lw / 2}" y="{y + 13}" fill="{self.p["soft"]}" font-size="7" font-family="{self.p["font_mono"]}" text-anchor="middle" letter-spacing="0.14em">{esc(text)}</text>',
        ]))

    def arrow(self, d: str, style: str = "muted", dashed: bool = False, points: list[tuple[float, float]] | None = None) -> None:
        stroke = self.p[style]
        marker = {"muted": "arrow", "accent": "arrow-accent", "link": "arrow-link"}[style]
        dash = ' stroke-dasharray="4,3"' if dashed else ""
        self.arrows.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{"1" if dashed else "1.2"}"{dash} marker-end="url(#{marker})"/>')
        if points:
            self.geometry["segments"].append(points)

    def label(self, cx: float, cy: float, text: str, limit: int = 20) -> None:
        text = text[:limit]
        w = int(len(text) * CHAR8) + 6
        x = cx - w / 2
        self.arrows.append("\n".join([
            f'<rect x="{x:.0f}" y="{cy - 6}" width="{w}" height="12" rx="2" fill="{self.p["paper"]}"/>',
            f'<text x="{cx:.0f}" y="{cy + 3}" fill="{self.p["soft"]}" font-size="8" font-family="{self.p["font_mono"]}" text-anchor="middle" letter-spacing="0.04em">{esc(text.upper())}</text>',
        ]))
        self.geometry["labels"].append({"text": text, "x": x, "y": cy - 6, "w": w, "h": 12})

    def legend(self, y: float, width: float, items: list[tuple[str, str]]) -> str:
        out = [
            f'<line x1="24" y1="{y - 8}" x2="{width - 24}" y2="{y - 8}" stroke="rgba(28,28,26,0.10)" stroke-width="0.8"/>',
            f'<text x="24" y="{y + 8}" fill="{self.p["muted"]}" font-size="8" font-family="{self.p["font_mono"]}" letter-spacing="0.14em">LEGEND</text>',
        ]
        x = 96
        for kind, text in items:
            if kind in ("dashed", "link", "muted", "accent"):
                stroke = self.p["muted"] if kind == "dashed" else self.p[kind]
                dash = ' stroke-dasharray="4,3"' if kind == "dashed" else ""
                out.append(f'<line x1="{x}" y1="{y + 4}" x2="{x + 24}" y2="{y + 4}" stroke="{stroke}" stroke-width="1.2"{dash} marker-end="url(#arrow)"/>')
            else:
                fill, stroke = (self.c(v) for v in TREAT[kind])
                out.append(f'<rect x="{x}" y="{y - 2}" width="24" height="12" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
            out.append(f'<text x="{x + 32}" y="{y + 8}" fill="{self.p["muted"]}" font-size="9" font-family="{self.p["font_mono"]}">{esc(text)}</text>')
            x += 48 + int(len(text) * 5.6)
        return "\n".join(out)

    def page(self, slug: str, eyebrow: str, title: str, desc: str, width: int, height: int, legend: str) -> str:
        p = self.p
        body = "\n".join(self.zones + self.arrows + self.nodes + [legend])
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <link href="{p["font_link"]}" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: {p["font_sans"]}; background: {p["paper"]}; color: {p["ink"]}; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 3rem 2rem; }}
    .frame {{ max-width: {width + 80}px; width: 100%; }}
    .diagram-container {{ width: 100%; overflow-x: auto; }}
    .eyebrow {{ font-family: {p["font_mono"]}; font-size: 0.66rem; font-weight: 500; letter-spacing: 0.18em; text-transform: uppercase; color: {p["muted"]}; margin-bottom: 0.5rem; }}
    h1 {{ font-family: {p["font_serif"]}; font-size: clamp(1.5rem, 2.4vw + 0.75rem, 2rem); font-weight: 400; letter-spacing: -0.02em; line-height: 1.15; margin-bottom: 1.5rem; }}
    svg {{ width: 100%; min-width: {width}px; display: block; }}
    @media print {{ .diagram-container {{ overflow-x: visible; }} svg {{ min-width: 0; }} }}
  </style>
</head>
<body>
  <div class="frame">
    <p class="eyebrow">{esc(eyebrow)}</p>
    <h1>{esc(title)}</h1>
    <div class="diagram-container">
      <svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{slug}-title {slug}-desc">
        <title id="{slug}-title">{esc(title)}</title>
        <desc id="{slug}-desc">{esc(desc)}</desc>
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{p["muted"]}"/></marker>
          <marker id="arrow-accent" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{p["accent"]}"/></marker>
          <marker id="arrow-link" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{p["link"]}"/></marker>
        </defs>
        <rect width="100%" height="100%" fill="{p["paper"]}"/>
{body}
      </svg>
    </div>
  </div>
</body>
</html>
"""


def person_type(p: dict[str, Any]) -> str:
    return "[Machine caller]" if p.get("type") == "machine" else "[Person]"


def column(cv: Canvas, items: list[dict[str, Any]], x: float, type_of, kind: str) -> dict[str, float]:
    """Stack grouped elements in one column. Returns id -> center y."""
    centers: dict[str, float] = {}
    y = TOP + 8
    groups: list[str] = []
    for it in items:
        if it.get("group", "") not in groups:
            groups.append(it.get("group", ""))
    for g in groups:
        members = [it for it in items if it.get("group", "") == g]
        zy = y
        y += 28 if g else 8
        for it in members:
            cv.node(x, y, CTX_W, CTX_H, kind, it["name"], type_of(it), it.get("description", ""), it["id"])
            centers[it["id"]] = y + CTX_H / 2
            y += CTX_H + 24
        if g:
            cv.zone(x - 16, zy, CTX_W + 32, y - 24 + 16 - zy, g)
        y += 24
    return centers


def render_context(model: dict[str, Any], profile: dict[str, str]) -> tuple[str, dict]:
    cv = Canvas(profile)
    W = 1400
    sys_x, sys_w = 520, 360
    left = column(cv, model["people"], M + 16, person_type, "input")
    right = column(cv, model["external_systems"], W - M - 16 - CTX_W, lambda _: "[External system]", "external")
    ys = list(left.values()) + list(right.values())
    top, bottom = min(ys) - CTX_H / 2 - 8, max(ys) + CTX_H / 2 + 8
    # system box
    s = model["system"]
    cv.node(sys_x, top, sys_w, bottom - top, "focal", "", "", "", s["name"])
    cy = (top + bottom) / 2
    lines = wrap(s.get("description", ""), 46, 4)
    cv.nodes.append(f'<text x="{sys_x + sys_w / 2}" y="{cy - 8 - 6 * len(lines)}" fill="{profile["ink"]}" font-size="16" font-weight="600" font-family="{profile["font_sans"]}" text-anchor="middle">{esc(s["name"])}</text>')
    cv.nodes.append(f'<text x="{sys_x + sys_w / 2}" y="{cy + 8 - 6 * len(lines)}" fill="{profile["soft"]}" font-size="8" font-family="{profile["font_mono"]}" text-anchor="middle" letter-spacing="0.04em">[SOFTWARE SYSTEM]</text>')
    for i, line in enumerate(lines):
        cv.nodes.append(f'<text x="{sys_x + sys_w / 2}" y="{cy + 26 - 6 * len(lines) + i * 12}" fill="{profile["muted"]}" font-size="9" font-family="{profile["font_mono"]}" text-anchor="middle">{esc(line)}</text>')
    # arrows: people
    lx = M + 16 + CTX_W
    for p in model["people"]:
        c = left[p["id"]]
        has_out = bool(p.get("main_out"))
        yin = c - 10 if has_out else c
        cv.arrow(f"M{lx},{yin} H{sys_x}", "link", points=[(lx, yin), (sys_x, yin)])
        cv.label((lx + sys_x) / 2, yin - 14, p["main_in"], 32)
        if has_out:
            cv.arrow(f"M{sys_x},{c + 10} H{lx}", "link", points=[(sys_x, c + 10), (lx, c + 10)])
            cv.label((lx + sys_x) / 2, c + 10 + 14, p["main_out"], 32)
    rx = W - M - 16 - CTX_W
    for e in model["external_systems"]:
        c = right[e["id"]]
        both = bool(e.get("in_label")) and bool(e.get("out_label"))
        if e.get("in_label"):
            y1 = c - 10 if both else c
            cv.arrow(f"M{sys_x + sys_w},{y1} H{rx}", "link", points=[(sys_x + sys_w, y1), (rx, y1)])
            cv.label((sys_x + sys_w + rx) / 2, y1 - 14, e["in_label"], 32)
        if e.get("out_label"):
            y2 = c + 10 if both else c
            cv.arrow(f"M{rx},{y2} H{sys_x + sys_w}", "link", points=[(rx, y2), (sys_x + sys_w, y2)])
            cv.label((sys_x + sys_w + rx) / 2, y2 + 14, e["out_label"], 32)
    H = int(bottom + 56)
    legend = cv.legend(H + 8, W, [("input", "person or machine caller"), ("focal", "system in scope"), ("external", "external system"), ("link", "data flow, one direction")])
    title = f"System Context diagram for {s['name']}"
    html = cv.page("c4-context", "C4 · Level 1 · System Context", title, f"The {s['name']} system in the centre, the people and machine callers that use it on the left, and the external systems it exchanges data with on the right.", W, H + 32, legend)
    return html, cv.geometry


class Grid:
    """Grid placement and orthogonal routing shared by the container and deployment diagrams."""

    def __init__(self, cv: Canvas) -> None:
        self.cv = cv
        self.rects: dict[str, tuple[float, float, float, float]] = {}
        self.ports: dict[tuple[str, str], int] = {}
        self.port_total: dict[tuple[str, str], int] = {}

    @staticmethod
    def px(gx: float, gy: float) -> tuple[float, float]:
        return M + gx * PX, TOP + gy * PY

    def place(self, nid: str, layout: dict[str, Any], kind: str, name: str, type_line: str, desc: str, tech: str = "") -> None:
        x, y = self.px(layout["gx"], layout["gy"])
        w = layout.get("gw", 1) * PX - (PX - NW)
        h = layout.get("gh", 1) * PY - (PY - NH)
        self.cv.node(x, y, w, h, kind, name, type_line, desc, nid, tech)
        self.rects[nid] = (x, y, w, h)

    def transit(self, points: list[tuple[float, float]], skip: set[str]) -> str | None:
        """Return the id of a node that a segment passes behind, or None."""
        for i in range(len(points) - 1):
            (x1, y1), (x2, y2) = points[i], points[i + 1]
            for nid, (x, y, w, h) in self.rects.items():
                if nid in skip:
                    continue
                if abs(y1 - y2) < 0.5 and y < y1 < y + h and min(x1, x2) < x + w and max(x1, x2) > x:
                    return nid
                if abs(x1 - x2) < 0.5 and x < x1 < x + w and min(y1, y2) < y + h and max(y1, y2) > y:
                    return nid
        return None

    def zone(self, z: dict[str, Any], sub: str = "") -> None:
        x, y = self.px(z["gx"], z["gy"])
        self.cv.zone(x - 20, y - 36, z["gw"] * PX - (PX - NW) + 40, z["gh"] * PY - (PY - NH) + 52, z["name"], sub)

    def edge_side(self, a: str, b: str) -> str:
        ax, ay, aw, ah = self.rects[a]
        bx, by, bw, bh = self.rects[b]
        if min(ay + ah, by + bh) - max(ay, by) >= 36:
            return "h"
        if min(ax + aw, bx + bw) - max(ax, bx) >= 48:
            return "v"
        return "elbow"

    def count_ports(self, rels: list[dict[str, Any]]) -> None:
        for r in rels:
            if r["from"] not in self.rects or r["to"] not in self.rects:
                continue
            for key in self.port_keys(r):
                self.port_total[key] = self.port_total.get(key, 0) + 1

    def port_keys(self, r: dict[str, Any]) -> list[tuple[str, str]]:
        a, b = r["from"], r["to"]
        ax, ay = self.rects[a][:2]
        bx, by = self.rects[b][:2]
        kind = self.edge_side(a, b)
        if kind == "h":
            return [(a, "right" if bx > ax else "left"), (b, "left" if bx > ax else "right")]
        if kind == "v":
            return [(a, "bottom" if by > ay else "top"), (b, "top" if by > ay else "bottom")]
        if r.get("route") == "vh":
            return [(a, "bottom" if by > ay else "top"), (b, "left" if bx > ax else "right")]
        return [(a, "right" if bx > ax else "left"), (b, "top" if by > ay else "bottom")]

    def port(self, key: tuple[str, str]) -> float:
        n = self.port_total.get(key, 1)
        k = self.ports.get(key, 0)
        self.ports[key] = k + 1
        return (k - (n - 1) / 2) * 16

    def route(self, r: dict[str, Any]) -> None:
        a, b = r["from"], r["to"]
        if a not in self.rects or b not in self.rects:
            return
        ax, ay, aw, ah = self.rects[a]
        bx, by, bw, bh = self.rects[b]
        style, dashed = r.get("style", "muted"), r.get("dashed", False)
        label = r.get("label", "")[:18]
        tech = (r.get("technology", "") if r.get("level") != "context" else "")[:18]
        ka, kb = self.port_keys(r)
        kind = self.edge_side(a, b)
        skip = {a, b}
        if kind == "h":
            # the shared y band of both boxes, then the port offset
            band = (max(ay, by) + min(ay + ah, by + bh)) / 2
            y = band + self.port(ka)
            self.port(kb)
            if bx > ax:
                x1, x2 = ax + aw, bx
            else:
                x1, x2 = ax, bx + bw
            pts = [(x1, y), (x2, y)]
            self.cv.arrow(f"M{x1},{y} H{x2}", style, dashed, pts)
            self.cv.label((x1 + x2) / 2, y - 12, label)
            if tech:
                self.cv.label((x1 + x2) / 2, y + 12, tech)
        elif kind == "v":
            band = (max(ax, bx) + min(ax + aw, bx + bw)) / 2
            x = band + self.port(ka)
            self.port(kb)
            if by > ay:
                y1, y2 = ay + ah, by
            else:
                y1, y2 = ay, by + bh
            pts = [(x, y1), (x, y2)]
            self.cv.arrow(f"M{x},{y1} V{y2}", style, dashed, pts)
            self.cv.label(x + 10 + len(label[:20]) * CHAR8 / 2, (y1 + y2) / 2 - (7 if tech else 0), label)
            if tech:
                self.cv.label(x + 10 + len(tech[:20]) * CHAR8 / 2, (y1 + y2) / 2 + 7, tech)
        elif r.get("route") == "vh":
            # leave the source top or bottom, run vertically, turn once into the target side
            x = ax + aw / 2 + self.port(ka)
            y = by + bh / 2 + self.port(kb)
            down = by > ay
            right = bx > ax
            y1 = ay + ah if down else ay
            xe = bx if right else bx + bw
            sx, sy = (1 if right else -1), (1 if down else -1)
            d = f"M{x},{y1} V{y - 8 * sy} Q{x},{y} {x + 8 * sx},{y} H{xe}"
            pts = [(x, y1), (x, y), (xe, y)]
            self.cv.arrow(d, style, dashed, pts)
            self.cv.label((x + xe) / 2, y - 12, label)
            if tech:
                self.cv.label((x + xe) / 2, y + 12, tech)
        else:
            y = ay + ah / 2 + self.port(ka)
            x = bx + bw / 2 + self.port(kb)
            down = by > ay
            right = bx > ax
            x1 = ax + aw if right else ax
            ye = by if down else by + bh
            sx, sy = (1 if right else -1), (1 if down else -1)
            d = f"M{x1},{y} H{x - 8 * sx} Q{x},{y} {x},{y + 8 * sy} V{ye}"
            pts = [(x1, y), (x, y), (x, ye)]
            self.cv.arrow(d, style, dashed, pts)
            self.cv.label((x1 + x) / 2, y - 12, label)
            if tech:
                self.cv.label((x1 + x) / 2, y + 12, tech)
        hit = self.transit(pts, skip)
        if hit:
            print(f"WARN {a} -> {b} passes behind {hit}; set route: vh or move a node")


def extent(cv: Canvas) -> tuple[int, int]:
    boxes = cv.geometry["nodes"] + cv.geometry["labels"]
    right = max(b["x"] + b["w"] for b in boxes)
    bottom = max(b["y"] + b["h"] for b in cv.geometry["nodes"])
    return int(right + M), int(bottom + 56)


def render_container(model: dict[str, Any], profile: dict[str, str]) -> tuple[str, dict]:
    cv = Canvas(profile)
    g = Grid(cv)
    for z in model.get("zones", []):
        g.zone(z)
    for p in model["people"]:
        if "layout" in p:
            g.place(p["id"], p["layout"], "input", p["name"], person_type(p), p.get("description", ""))
    for e in model["external_systems"]:
        if "layout" in e:
            g.place(e["id"], e["layout"], "external", e["name"], "[External system]", e.get("description", ""))
    for c in model["containers"]:
        if "layout" not in c:
            continue
        kind = "focal" if c.get("focal") else ("store" if c.get("kind") == "store" else "backend")
        tl = f"[{'Data store' if c.get('kind') == 'store' else 'Container'}]"
        g.place(c["id"], c["layout"], kind, c["name"], tl, c.get("description", ""), c.get("technology", ""))
    rels = [r for r in model["relationships"] if r.get("level", "container") == "container"]
    g.count_ports(rels)
    for r in rels:
        g.route(r)
    W, H = extent(cv)
    legend = cv.legend(H + 8, W, [("input", "person / caller"), ("focal", "focal container"), ("backend", "container"), ("store", "data store"), ("external", "external system"), ("link", "HTTP / API"), ("dashed", "async or not configured")])
    s = model["system"]
    title = f"Container diagram for {s['name']}"
    html = cv.page("c4-container", "C4 · Level 2 · Container", title, f"The containers inside {s['name']}, their technology, the people and external systems they connect to, and how they talk.", W, H + 32, legend)
    return html, cv.geometry


def render_deployment(model: dict[str, Any], env: dict[str, Any], profile: dict[str, str]) -> tuple[str, dict]:
    cv = Canvas(profile)
    g = Grid(cv)
    by_id = {c["id"]: c for c in model["containers"]}
    for n in env["nodes"]:
        g.zone(n, n.get("technology", ""))
    for inst in env["instances"]:
        c = by_id[inst["container"]]
        kind = "store" if c.get("kind") == "store" else "backend"
        count = f"×{inst['count']}" if inst.get("count") else ""
        size = inst.get("size", "")
        tl = f"[{'Data store' if c.get('kind') == 'store' else 'Container'} instance]"
        g.place(inst.get("id", c["id"]), inst["layout"], kind, inst.get("name", c["name"]), tl, inst.get("description", c.get("technology", "")), " · ".join(t for t in (count, size) if t))
    rels = env.get("relationships", [])
    g.count_ports(rels)
    for r in rels:
        g.route(r)
    W, H = extent(cv)
    legend = cv.legend(H + 8, W, [("backend", "container instance"), ("store", "data store instance"), ("link", "HTTP / API"), ("muted", "internal call")])
    s = model["system"]
    title = f"Deployment diagram for {s['name']} · {env['name']}"
    html = cv.page(f"c4-deployment-{env['id']}", "C4 · Deployment", title, f"Where each container of {s['name']} runs in the {env['name']} environment, with instance counts and sizes.", W, H + 32, legend)
    return html, cv.geometry


def tables(model: dict[str, Any]) -> str:
    out = ["## Inputs and outputs per user type", "", "| User type | Group | Sends in | Gets out |", "|---|---|---|---|"]
    for p in model["people"]:
        out.append(f"| {p['name']} ({'machine' if p.get('type') == 'machine' else 'person'}) | {p.get('group', '')} | {', '.join(p.get('inputs', []))} | {', '.join(p.get('outputs', []))} |")
    out += ["", "## External systems", "", "| External system | Group | The system sends | The system receives |", "|---|---|---|---|"]
    for e in model["external_systems"]:
        out.append(f"| {e['name']} | {e.get('group', '')} | {e.get('in_label', '')} | {e.get('out_label', '')} |")
    out += ["", "## Containers", "", "| Container | Kind | Technology | Does |", "|---|---|---|---|"]
    for c in model["containers"]:
        out.append(f"| {c['name']} | {c.get('kind', 'app')} | {c.get('technology', '')} | {c.get('description', '')} |")
    out += ["", "## Relationships", "", "| From | To | Label | Technology |", "|---|---|---|---|"]
    for r in model["relationships"]:
        out.append(f"| {r['from']} | {r['to']} | {r.get('label', '')} | {r.get('technology', '')} |")
    if model.get("glossary"):
        out += ["", "## Glossary", ""]
        out += [f"- {k}: {v}" for k, v in model["glossary"].items()]
    return "\n".join(out) + "\n"


def load_profile(model: dict[str, Any], cli: str | None, model_path: Path) -> dict[str, str]:
    slug = cli or model.get("profile") or "default"
    marker = model_path.parent / ".c4-diagram"
    if marker.exists():
        m = re.fullmatch(r"\s*profile:\s*([a-z0-9][a-z0-9-]{0,63})\s*", marker.read_text())
        if m:
            slug = m.group(1)
    path = SKILL_DIR / "profiles" / f"{slug}.json"
    if not path.exists():
        raise SystemExit(f"profile not found: {path}")
    return json.loads(path.read_text())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("model")
    ap.add_argument("--out", default="diagrams")
    ap.add_argument("--profile")
    a = ap.parse_args()
    model_path = Path(a.model)
    model = json.loads(model_path.read_text())
    profile = load_profile(model, a.profile, model_path)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    geometry: dict[str, dict] = {}
    html, geometry["c4-context"] = render_context(model, profile)
    (out / "c4-context.html").write_text(html)
    html, geometry["c4-container"] = render_container(model, profile)
    (out / "c4-container.html").write_text(html)
    for env in model.get("deployment", {}).get("environments", []):
        html, geometry[f"c4-deployment-{env['id']}"] = render_deployment(model, env, profile)
        (out / f"c4-deployment-{env['id']}.html").write_text(html)
    (out / "c4-tables.md").write_text(tables(model))
    (out / "c4-geometry.json").write_text(json.dumps(geometry))
    print("wrote", ", ".join(sorted(p.name for p in out.iterdir() if p.name.startswith("c4-"))))


if __name__ == "__main__":
    main()
