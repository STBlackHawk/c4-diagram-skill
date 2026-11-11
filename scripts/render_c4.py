#!/usr/bin/env python3
"""Render C4 System Context, Container and Deployment diagrams from c4-model.json.

The output follows the diagram-design system (cathrynlavery/diagram-design, MIT):
node box with a rectangular type tag, orthogonal connectors with fanned ports,
labels on paper masks, zones painted first, a legend strip, and the accessible SVG
contract. C4 supplies the content: element types, technology, verb labels.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parent.parent
DD_PROFILES = Path.home() / ".diagram-design" / "profiles"
PX, PY = 304, 128  # grid cell: quarter steps stay on the 4px grid, a 20-character label fits the 136px column gap
NW, NH = 168, 88  # node box
CTX_H = 72  # context column node
M, TOP = 40, 48  # page margins
CTX_W = 240  # context column width
SANS9, MONO9, MONO7 = 5.4, 5.6, 4.9  # px per character
LABEL_CH = 8 * 0.62 + 8 * 0.06  # 8px mono, tracked 0.06em
COLOR_KEYS = ("paper", "paper2", "ink", "muted", "soft", "accent", "accent_tint", "link")

ICONS = {  # Tabler Icons (MIT), via diagram-design primitive-icons.md
    "user": "M8 7a4 4 0 1 0 8 0a4 4 0 0 0 -8 0 M6 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2",
    "robot": "M6 6a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v4a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2l0 -4 M12 2v2 M9 12v9 M15 12v9 M5 16l4 -2 M15 14l4 2 M9 18h6 M10 8v.01 M14 8v.01",
    "database": "M4 6a8 3 0 1 0 16 0a8 3 0 1 0 -16 0 M4 6v6a8 3 0 0 0 16 0v-6 M4 12v6a8 3 0 0 0 16 0v-6",
    "cloud": "M6.657 18c-2.572 0 -4.657 -2.007 -4.657 -4.483c0 -2.475 2.085 -4.482 4.657 -4.482c.393 -1.762 1.794 -3.2 3.675 -3.773c1.88 -.572 3.956 -.193 5.444 1c1.488 1.19 2.162 3.007 1.77 4.769h.99c1.913 0 3.464 1.56 3.464 3.486c0 1.927 -1.551 3.487 -3.465 3.487h-11.878",
}


def r4(v: float) -> int:
    return int(math.ceil(v / 4) * 4)


def rgba(color: str, alpha: float) -> str:
    """A hex or rgba() colour at the given opacity."""
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", color.strip())
    if m:
        r, g, b = (int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r},{g},{b},{alpha})"
    m = re.fullmatch(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[\d.]+)?\)", color.strip())
    if m:
        return f"rgba({m.group(1)},{m.group(2)},{m.group(3)},{alpha})"
    return color


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


def clip(text: str, chars: int) -> str:
    return text if len(text) <= chars else text[: max(chars - 1, 1)].rstrip() + "…"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Canvas:
    """One diagram: zones, arrows and nodes in paint order, plus geometry for the checker."""

    def __init__(self, profile: dict[str, str], dark: bool = False) -> None:
        self.p = profile
        self.dark = dark
        ink, muted, accent = profile["ink"], profile["muted"], profile["accent"]
        backend_fill = profile["paper2"] if dark else "#ffffff"
        # kind -> (fill, stroke, tag stroke, tag text); style-guide.md "Node type -> treatment"
        self.treat = {
            "focal": (profile["accent_tint"], accent, rgba(accent, 0.5), accent),
            "backend": (backend_fill, ink, rgba(ink, 0.4), ink),
            "store": (rgba(ink, 0.05), muted, rgba(muted, 0.5), muted),
            "external": (rgba(ink, 0.03), rgba(ink, 0.3), rgba(ink, 0.22), profile["soft"]),
            "input": (rgba(muted, 0.1), profile["soft"], rgba(profile["soft"], 0.4), profile["soft"]),
        }
        self.zones: list[str] = []
        self.arrows: list[str] = []
        self.nodes: list[str] = []
        self.geometry: dict[str, list] = {"nodes": [], "labels": [], "segments": []}
        self.warnings: list[str] = []

    def text(self, x: float, y: float, s: str, size: float, fill: str, font: str, weight: int = 400, anchor: str = "middle", tracking: str = "") -> str:
        w = f' font-weight="{weight}"' if weight != 400 else ""
        t = f' letter-spacing="{tracking}"' if tracking else ""
        return f'<text x="{x:.0f}" y="{y:.0f}" fill="{fill}" font-size="{size}"{w} font-family="{self.p[font]}" text-anchor="{anchor}"{t}>{esc(s)}</text>'

    def icon(self, name: str, x: float, y: float, color: str) -> str:
        return f'<g transform="translate({x:.0f},{y:.0f}) scale(0.6667)" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="{ICONS[name]}"/></g>'

    @staticmethod
    def fit_chip(chip: tuple[str, str], desc: str, avail: float) -> tuple[str, str, str]:
        """Fit the artifact chip: shorten the name at its first comma, then move the version into the description."""
        left, right = chip
        for name in (left, left.split(",")[0].strip()):
            if len(name) * 7.2 + (len(right) * MONO9 + 8 if right else 0) <= avail:
                return name, right, desc
        if right:
            desc = " · ".join(t for t in (right, desc) if t)
        for name in (left, left.split(",")[0].strip()):
            if len(name) * 7.2 <= avail:
                return name, "", desc
        return clip(left, int(avail / 7.2)), "", desc

    def node(self, x: float, y: float, w: float, h: float, kind: str, name: str, tag: str, desc: str, nid: str = "", tech: str = "", icon: str = "", badge: str = "", chip: tuple[str, str] | None = None) -> None:
        p = self.p
        fill, stroke, tag_stroke, tag_text = self.treat[kind]
        cx = x + w / 2
        out = [
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{p["paper"]}"/>',
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1"/>',
        ]
        if tag:
            tw = r4(len(tag) * (MONO7 + 0.56) + 8)
            out.append(f'<rect x="{x + 8}" y="{y + 8}" width="{tw}" height="12" rx="2" fill="transparent" stroke="{tag_stroke}" stroke-width="0.8"/>')
            out.append(self.text(x + 8 + tw / 2, y + 17, tag.upper(), 7, tag_text, "font_mono", tracking="0.08em"))
        if badge:
            bw = r4(len(badge) * MONO9 + 8)
            out.append(f'<rect x="{x + w - 8 - bw}" y="{y + 8}" width="{bw}" height="12" rx="2" fill="transparent" stroke="{tag_stroke}" stroke-width="0.8"/>')
            out.append(self.text(x + w - 8 - bw / 2, y + 17, badge, 8, tag_text, "font_mono"))
        elif icon:
            out.append(self.icon(icon, x + w - 24, y + 6, p["soft"]))
        name_y = y + 36 if h >= 88 else y + 34
        if name:
            if len(name) * 7.2 > w - 16:
                self.warnings.append(f"name '{name}' is wider than its box, shorten it or widen the layout")
            out.append(self.text(cx, name_y, name, 12, p["ink"], "font_sans", 600))
        row = name_y + 14
        if chip:
            left, right, desc = self.fit_chip(chip, desc, w - 32)
            out.append(f'<rect x="{x + 8}" y="{y + 44}" width="{w - 16}" height="24" rx="4" fill="{rgba(p["ink"], 0.05)}" stroke="{p["muted"]}" stroke-width="0.8"/>')
            out.append(self.text(x + 16, y + 60, left, 12, p["ink"], "font_sans", anchor="start"))
            if right:
                out.append(self.text(x + w - 16, y + 60, right, 9, p["muted"], "font_mono", anchor="end"))
            row = y + 82
            if desc:
                out.append(self.text(cx, row, clip(desc, int((w - 16) / SANS9)), 9, p["muted"], "font_sans"))
        else:
            if tech:
                out.append(self.text(cx, row, clip(tech, int((w - 16) / MONO9)), 9, p["muted"], "font_mono"))
                row += 14
            for line in wrap(desc, int((w - 16) / SANS9), 2) if desc else []:
                out.append(self.text(cx, row, line, 9, p["muted"], "font_sans"))
                row += 12
        self.nodes.append("\n".join(out))
        self.geometry["nodes"].append({"id": nid or name, "x": x, "y": y, "w": w, "h": h})

    def zone(self, x: float, y: float, w: float, h: float, label: str, sub: str = "", dashed: bool = False) -> None:
        p = self.p
        text = label.upper() + (f"  ·  {sub.upper()}" if sub else "")
        lw = r4(len(text) * (MONO7 + 0.98) + 16)
        stroke = f'stroke="{rgba(p["ink"], 0.2)}" stroke-dasharray="4,4"' if dashed else f'stroke="{rgba(p["ink"], 0.1)}"'
        self.zones.append("\n".join([
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{rgba(p["ink"], 0.02)}" {stroke} stroke-width="0.8"/>',
            f'<rect x="{x + 12}" y="{y + 4}" width="{lw}" height="12" rx="2" fill="{p["paper"]}"/>',
            self.text(x + 12 + lw / 2, y + 13, text, 7, p["soft"], "font_mono", tracking="0.14em"),
        ]))

    def arrow(self, d: str, style: str = "muted", dashed: bool = False, points: list[tuple[float, float]] | None = None) -> None:
        stroke = self.p[style]
        marker = {"muted": "arrow", "accent": "arrow-accent", "link": "arrow-link"}[style]
        dash = ' stroke-dasharray="5,4"' if dashed else ""
        width = "1" if dashed else ("1.4" if style == "accent" else "1.2")
        self.arrows.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{width}"{dash} marker-end="url(#{marker})"/>')
        if points:
            self.geometry["segments"].append(points)

    def label(self, cx: float, cy: float, text: str, limit: int = 18, style: str = "muted") -> None:
        if len(text) > limit:
            self.warnings.append(f"label '{text}' is over {limit} characters and was cut")
        text = text[:limit]
        w = r4(len(text) * LABEL_CH + 8)
        x = cx - w / 2
        fill = self.p["link"] if style == "link" else (self.p["accent"] if style == "accent" else self.p["soft"])
        self.arrows.append("\n".join([
            f'<rect x="{x:.0f}" y="{cy - 6}" width="{w}" height="12" rx="2" fill="{self.p["paper"]}"/>',
            self.text(cx, cy + 3, text.upper(), 8, fill, "font_mono", tracking="0.06em"),
        ]))
        self.geometry["labels"].append({"text": text, "x": x, "y": cy - 6, "w": w, "h": 12})

    def legend(self, y: float, width: float, items: list[tuple[str, str]]) -> str:
        p = self.p
        out = [
            f'<line x1="{M}" y1="{y - 8}" x2="{width - M}" y2="{y - 8}" stroke="{rgba(p["ink"], 0.1)}" stroke-width="0.8"/>',
            self.text(M, y + 8, "LEGEND", 8, p["muted"], "font_mono", anchor="start", tracking="0.18em"),
        ]
        x = M + 72
        for kind, text in items:
            if kind in ("dashed", "link", "muted", "accent"):
                stroke = p["muted"] if kind == "dashed" else p[kind]
                marker = {"link": "arrow-link", "accent": "arrow-accent"}.get(kind, "arrow")
                dash = ' stroke-dasharray="5,4"' if kind == "dashed" else ""
                out.append(f'<line x1="{x}" y1="{y + 4}" x2="{x + 28}" y2="{y + 4}" stroke="{stroke}" stroke-width="1.2"{dash} marker-end="url(#{marker})"/>')
                tx = x + 36
            else:
                fill, stroke = self.treat[kind][:2]
                out.append(f'<rect x="{x}" y="{y - 1}" width="14" height="10" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
                tx = x + 20
            out.append(self.text(tx, y + 7, text, 8.5, p["muted"], "font_sans", anchor="start"))
            x = tx + r4(len(text) * 5.1) + 28
        return "\n".join(out)

    def page(self, slug: str, eyebrow: str, title: str, desc: str, width: int, height: int, legend: str) -> str:
        p = self.p
        body = "\n".join(self.zones + self.arrows + self.nodes + [legend])
        link = f'\n  <link href="{p["font_link"]}" rel="stylesheet">' if p.get("font_link") else ""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>{link}
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


def person_tag(p: dict[str, Any]) -> str:
    return "MACHINE" if p.get("type") == "machine" else "PERSON"


def person_icon(p: dict[str, Any]) -> str:
    return "robot" if p.get("type") == "machine" else "user"


def column(cv: Canvas, items: list[dict[str, Any]], x: float, kind: str) -> dict[str, float]:
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
            if kind == "input":
                cv.node(x, y, CTX_W, CTX_H, kind, it["name"], person_tag(it), it.get("description", ""), it["id"], icon=person_icon(it))
            else:
                cv.node(x, y, CTX_W, CTX_H, kind, it["name"], "EXTERNAL", it.get("description", ""), it["id"], icon="cloud")
            centers[it["id"]] = y + CTX_H / 2
            y += CTX_H + 24
        if g:
            cv.zone(x - 16, zy, CTX_W + 32, y - 24 + 16 - zy, g)
        y += 24
    return centers


def render_context(model: dict[str, Any], profile: dict[str, str], dark: bool) -> tuple[str, dict, list[str]]:
    cv = Canvas(profile, dark)
    W = 1400
    sys_x, sys_w = 520, 360
    left = column(cv, model["people"], M + 16, "input")
    right = column(cv, model["external_systems"], W - M - 16 - CTX_W, "external")
    ys = list(left.values()) + list(right.values())
    top, bottom = min(ys) - CTX_H / 2 - 8, max(ys) + CTX_H / 2 + 8
    s = model["system"]
    cv.node(sys_x, top, sys_w, bottom - top, "focal", "", "SOFTWARE SYSTEM", "", s["name"])
    cy = (top + bottom) / 2
    lines = wrap(s.get("description", ""), 56, 4)
    cv.nodes.append(cv.text(sys_x + sys_w / 2, cy - 8 - 6 * len(lines), s["name"], 16, profile["ink"], "font_sans", 600))
    for i, line in enumerate(lines):
        cv.nodes.append(cv.text(sys_x + sys_w / 2, cy + 12 - 6 * len(lines) + i * 12, line, 9, profile["muted"], "font_sans"))
    lx = M + 16 + CTX_W
    for p in model["people"]:
        c = left[p["id"]]
        has_out = bool(p.get("main_out"))
        yin = c - 10 if has_out else c
        cv.arrow(f"M{lx},{yin} H{sys_x}", "link", points=[(lx, yin), (sys_x, yin)])
        cv.label((lx + sys_x) / 2, yin - 14, p["main_in"], 32, "link")
        if has_out:
            cv.arrow(f"M{sys_x},{c + 10} H{lx}", "link", points=[(sys_x, c + 10), (lx, c + 10)])
            cv.label((lx + sys_x) / 2, c + 10 + 14, p["main_out"], 32, "link")
    rx = W - M - 16 - CTX_W
    for e in model["external_systems"]:
        c = right[e["id"]]
        both = bool(e.get("in_label")) and bool(e.get("out_label"))
        if e.get("in_label"):
            y1 = c - 10 if both else c
            cv.arrow(f"M{sys_x + sys_w},{y1} H{rx}", "link", points=[(sys_x + sys_w, y1), (rx, y1)])
            cv.label((sys_x + sys_w + rx) / 2, y1 - 14, e["in_label"], 32, "link")
        if e.get("out_label"):
            y2 = c + 10 if both else c
            cv.arrow(f"M{rx},{y2} H{sys_x + sys_w}", "link", points=[(rx, y2), (sys_x + sys_w, y2)])
            cv.label((sys_x + sys_w + rx) / 2, y2 + 14, e["out_label"], 32, "link")
    H = int(bottom + 56)
    legend = cv.legend(H + 8, W, [("input", "Person or machine caller"), ("focal", "System in scope"), ("external", "External system"), ("link", "Data flow, one direction")])
    title = f"System Context diagram for {s['name']}"
    html = cv.page("c4-context" + ("-dark" if dark else ""), "C4 · Level 1 · System Context", title, f"The {s['name']} system in the centre, the people and machine callers that use it on the left, and the external systems it exchanges data with on the right.", W, H + 32, legend)
    return html, cv.geometry, cv.warnings


class Grid:
    """Grid placement and orthogonal routing shared by the container and deployment diagrams."""

    def __init__(self, cv: Canvas) -> None:
        self.cv = cv
        self.rects: dict[str, tuple[float, float, float, float]] = {}
        self.zone_rects: dict[str, tuple[float, float, float, float]] = {}
        self.ports: dict[tuple[str, str], int] = {}
        self.port_total: dict[tuple[str, str], int] = {}

    @staticmethod
    def px(gx: float, gy: float) -> tuple[float, float]:
        return M + gx * PX, TOP + gy * PY

    def place(self, nid: str, layout: dict[str, Any], kind: str, name: str, tag: str, desc: str, tech: str = "", **kw: Any) -> None:
        x, y = self.px(layout["gx"], layout["gy"])
        w = layout.get("gw", 1) * PX - (PX - NW)
        h = layout.get("gh", 1) * PY - (PY - NH)
        self.cv.node(x, y, w, h, kind, name, tag, desc, nid, tech, **kw)
        self.rects[nid] = (x, y, w, h)

    def zone(self, z: dict[str, Any], sub: str = "", dashed: bool = False) -> None:
        x, y = self.px(z["gx"], z["gy"])
        rect = (x - 20, y - 36, z["gw"] * PX - (PX - NW) + 40, z["gh"] * PY - (PY - NH) + 52)
        self.zone_rects[z["id"]] = rect
        self.cv.zone(*rect, z["name"], sub, dashed)

    def zone_of(self, nid: str) -> str | None:
        x, y, w, h = self.rects[nid]
        cx, cy = x + w / 2, y + h / 2
        for zid, (zx, zy, zw, zh) in self.zone_rects.items():
            if zx <= cx <= zx + zw and zy <= cy <= zy + zh:
                return zid
        return None

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

    def route(self, r: dict[str, Any], default_style: str | None = None) -> None:
        a, b = r["from"], r["to"]
        if a not in self.rects or b not in self.rects:
            self.cv.warnings.append(f"relationship {a} -> {b} skipped: an end has no layout")
            return
        ax, ay, aw, ah = self.rects[a]
        bx, by, bw, bh = self.rects[b]
        style, dashed = r.get("style") or default_style or "muted", r.get("dashed", False)
        label = r.get("label", "")
        tech = r.get("technology", "") if r.get("level") != "context" else ""
        ka, kb = self.port_keys(r)
        kind = self.edge_side(a, b)
        skip = {a, b}
        if kind == "h":
            band = (max(ay, by) + min(ay + ah, by + bh)) / 2
            y = band + self.port(ka)
            self.port(kb)
            x1, x2 = (ax + aw, bx) if bx > ax else (ax, bx + bw)
            pts = [(x1, y), (x2, y)]
            self.cv.arrow(f"M{x1},{y} H{x2}", style, dashed, pts)
            lim = fit(abs(x2 - x1))
            self.cv.label((x1 + x2) / 2, y - 12, label, lim, style)
            if tech:
                self.cv.label((x1 + x2) / 2, y + 12, tech, lim)
        elif kind == "v":
            band = (max(ax, bx) + min(ax + aw, bx + bw)) / 2
            x = band + self.port(ka)
            self.port(kb)
            y1, y2 = (ay + ah, by) if by > ay else (ay, by + bh)
            pts = [(x, y1), (x, y2)]
            self.cv.arrow(f"M{x},{y1} V{y2}", style, dashed, pts)
            lw = r4(len(label[:20]) * LABEL_CH + 8)
            self.cv.label(x + 10 + lw / 2, (y1 + y2) / 2 - (7 if tech else 0), label, 20, style)
            if tech:
                tw = r4(len(tech[:20]) * LABEL_CH + 8)
                self.cv.label(x + 10 + tw / 2, (y1 + y2) / 2 + 7, tech)
        elif r.get("route") == "vh":
            x = ax + aw / 2 + self.port(ka)
            y = by + bh / 2 + self.port(kb)
            down, right = by > ay, bx > ax
            y1 = ay + ah if down else ay
            xe = bx if right else bx + bw
            sx, sy = (1 if right else -1), (1 if down else -1)
            d = f"M{x},{y1} V{y - 8 * sy} Q{x},{y} {x + 8 * sx},{y} H{xe}"
            pts = [(x, y1), (x, y), (xe, y)]
            self.cv.arrow(d, style, dashed, pts)
            lim = fit(abs(xe - x))
            self.cv.label((x + xe) / 2, y - 12, label, lim, style)
            if tech:
                self.cv.label((x + xe) / 2, y + 12, tech, lim)
        else:
            y = ay + ah / 2 + self.port(ka)
            x = bx + bw / 2 + self.port(kb)
            down, right = by > ay, bx > ax
            x1 = ax + aw if right else ax
            ye = by if down else by + bh
            sx, sy = (1 if right else -1), (1 if down else -1)
            d = f"M{x1},{y} H{x - 8 * sx} Q{x},{y} {x},{y + 8 * sy} V{ye}"
            pts = [(x1, y), (x, y), (x, ye)]
            self.cv.arrow(d, style, dashed, pts)
            lim = fit(abs(x - x1))
            self.cv.label((x1 + x) / 2, y - 12, label, lim, style)
            if tech:
                self.cv.label((x1 + x) / 2, y + 12, tech, lim)
        hit = self.transit(pts, skip)
        if hit:
            self.cv.warnings.append(f"{a} -> {b} passes behind {hit}; set route: vh or move a node")


def fit(segment: float, limit: int = 20) -> int:
    """How many label characters fit a horizontal segment with 8px clear of each node and 4px mask padding."""
    return max(1, min(limit, int((segment - 24) / LABEL_CH)))


def extent(cv: Canvas) -> tuple[int, int]:
    boxes = cv.geometry["nodes"] + cv.geometry["labels"]
    right = max(b["x"] + b["w"] for b in boxes)
    bottom = max(b["y"] + b["h"] for b in cv.geometry["nodes"])
    return r4(right + M), r4(bottom + 56)


def render_container(model: dict[str, Any], profile: dict[str, str], dark: bool) -> tuple[str, dict, list[str]]:
    cv = Canvas(profile, dark)
    g = Grid(cv)
    for z in model.get("zones", []):
        g.zone(z)
    for p in model["people"]:
        if "layout" in p:
            g.place(p["id"], p["layout"], "input", p["name"], person_tag(p), p.get("description", ""), icon=person_icon(p))
    for e in model["external_systems"]:
        if "layout" in e:
            g.place(e["id"], e["layout"], "external", e["name"], "EXTERNAL", e.get("description", ""), icon="cloud")
    for c in model["containers"]:
        if "layout" not in c:
            continue
        store = c.get("kind") == "store"
        kind = "focal" if c.get("focal") else ("store" if store else "backend")
        g.place(c["id"], c["layout"], kind, c["name"], "STORE" if store else "CONTAINER", c.get("description", ""), c.get("technology", ""), icon="database" if store else "")
    rels = [r for r in model["relationships"] if r.get("level", "container") == "container"]
    g.count_ports(rels)
    for r in rels:
        g.route(r)
    W, H = extent(cv)
    legend = cv.legend(H + 8, W, [("input", "Person or caller"), ("focal", "Focal container"), ("backend", "Container"), ("store", "Data store"), ("external", "External system"), ("link", "HTTP or API call"), ("muted", "Internal call"), ("dashed", "Async or not configured")])
    s = model["system"]
    title = f"Container diagram for {s['name']}"
    html = cv.page("c4-container" + ("-dark" if dark else ""), "C4 · Level 2 · Container", title, f"The containers inside {s['name']}, their technology, the people and external systems they connect to, and how they talk.", W, H + 32, legend)
    return html, cv.geometry, cv.warnings


def render_deployment(model: dict[str, Any], env: dict[str, Any], profile: dict[str, str], dark: bool) -> tuple[str, dict, list[str]]:
    cv = Canvas(profile, dark)
    g = Grid(cv)
    by_id = {c["id"]: c for c in model["containers"]}
    for n in env["nodes"]:
        g.zone(n, n.get("technology", ""), dashed=True)
    for inst in env["instances"]:
        c = by_id[inst["container"]]
        store = c.get("kind") == "store"
        count = inst.get("count") or 0
        tag = inst.get("tag") or ("STORE" if store else "APP")
        chip = (inst.get("artifact") or c.get("technology", ""), inst.get("version") or inst.get("size", ""))
        g.place(inst.get("id", c["id"]), inst["layout"], "store" if store else "backend", inst.get("name", c["name"]), tag, inst.get("description", ""), badge=f"×{count}" if count > 1 else "", chip=chip)
    rels = env.get("relationships", [])
    g.count_ports(rels)
    for r in rels:
        if r["from"] in g.rects and r["to"] in g.rects:
            cross = g.zone_of(r["from"]) != g.zone_of(r["to"])
            g.route(r, "link" if cross else "muted")
        else:
            g.route(r)
    W, H = extent(cv)
    legend = cv.legend(H + 8, W, [("backend", "Container instance"), ("store", "Data store instance"), ("link", "Crosses a node boundary"), ("muted", "Inside one node"), ("dashed", "Async or replication")])
    s = model["system"]
    title = f"Deployment diagram for {s['name']} · {env['name']}"
    html = cv.page(f"c4-deployment-{env['id']}" + ("-dark" if dark else ""), "C4 · Deployment", title, f"Where each container of {s['name']} runs in the {env['name']} environment, with instance counts and sizes.", W, H + 32, legend)
    return html, cv.geometry, cv.warnings


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


def read_marker(path: Path) -> str | None:
    if not path.exists():
        return None
    m = re.fullmatch(r"\s*profile:\s*([a-z0-9][a-z0-9-]{0,63})\s*", path.read_text())
    return m.group(1) if m else None


def family(cell: str, generic: str) -> str:
    name = re.sub(r"\s*\(.*?\)", "", cell).strip()
    return f"'{name}', {generic}"


def profile_from_style_guide(path: Path) -> dict[str, Any]:
    """Read the colour and font roles from a diagram-design style guide or saved profile."""
    text = path.read_text()
    keys = {"paper": "paper", "paper-2": "paper2", "ink": "ink", "muted": "muted", "soft": "soft", "accent": "accent", "accent-tint": "accent_tint", "link": "link"}
    light: dict[str, str] = {}
    dark: dict[str, str] = {}
    for role, key in keys.items():
        m = re.search(rf"^\|\s*`{re.escape(role)}`\s*\|[^|]*\|\s*`([^`]+)`[^|]*\|\s*`([^`]+)`", text, re.M)
        if not m:
            raise SystemExit(f"{path}: no row for role {role}")
        light[key], dark[key] = m.group(1).strip(), m.group(2).strip()
    fonts: dict[str, str] = {}
    for role, key, generic in (("title", "font_serif", "'Noto Serif', serif"), ("node-name", "font_sans", "system-ui, sans-serif"), ("sublabel", "font_mono", "ui-monospace, monospace")):
        m = re.search(rf"^\|\s*`{re.escape(role)}`\s*\|\s*([^|]+)\|", text, re.M)
        fonts[key] = family(m.group(1), generic) if m else {"font_serif": "'Instrument Serif', serif", "font_sans": "'Geist', system-ui, sans-serif", "font_mono": "'Geist Mono', ui-monospace, monospace"}[key]
    m = re.search(r"^Font source:\s*`?(\w+)`?", text, re.M)
    system_fonts = bool(m) and m.group(1) == "system"
    names = [fonts[k].split("'")[1] for k in ("font_serif", "font_sans", "font_mono")]
    link = "" if system_fonts else "https://fonts.googleapis.com/css2?" + "&".join(
        f"family={n.replace(' ', '+')}" + (":ital@0;1" if i == 0 else ":wght@400;500;600") for i, n in enumerate(names)) + "&display=swap"
    return {"name": path.stem, "source": str(path), **light, **fonts, "font_link": link, "dark": dark}


def load_profile(model: dict[str, Any], cli: str | None, model_path: Path) -> dict[str, Any]:
    """Resolve the brand: project marker, then --profile, then the model, then default."""
    slug = read_marker(model_path.parent / ".c4-diagram") or read_marker(model_path.parent / ".diagram-design") or cli or model.get("profile") or "default"
    local = model_path.parent / "profiles" / f"{slug}.json"  # a brand kept next to the model
    json_path = local if local.exists() else SKILL_DIR / "profiles" / f"{slug}.json"
    md_path = DD_PROFILES / f"{slug}.md"
    profile: dict[str, Any] = json.loads(json_path.read_text()) if json_path.exists() else {}
    if md_path.exists():
        md = profile_from_style_guide(md_path)
        if profile.get("font_link"):  # the JSON profile knows the real web font link
            md["font_link"], md["font_sans"], md["font_mono"], md["font_serif"] = (profile[k] for k in ("font_link", "font_sans", "font_mono", "font_serif"))
        profile = {**profile, **md}
    if not profile:
        raise SystemExit(f"profile not found: {json_path} or {md_path}")
    return profile


def variants(profile: dict[str, Any], want_dark: bool) -> list[tuple[bool, dict[str, str]]]:
    light = {k: v for k, v in profile.items() if k != "dark"}
    out = [(False, light)]
    if want_dark and profile.get("dark"):
        out.append((True, {**light, **profile["dark"]}))
    elif want_dark:
        print("WARN profile has no dark tokens, no dark variant written")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("model")
    ap.add_argument("--out", default="diagrams")
    ap.add_argument("--profile")
    ap.add_argument("--dark", action="store_true", help="also write *-dark.html when the profile has dark tokens")
    a = ap.parse_args()
    model_path = Path(a.model)
    model = json.loads(model_path.read_text())
    profile = load_profile(model, a.profile, model_path)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    geometry: dict[str, Any] = {}
    warnings: list[str] = []
    for dark, tokens in variants(profile, a.dark):
        suffix = "-dark" if dark else ""
        html, geo, warn = render_context(model, tokens, dark)
        (out / f"c4-context{suffix}.html").write_text(html)
        html, geo2, warn2 = render_container(model, tokens, dark)
        (out / f"c4-container{suffix}.html").write_text(html)
        if not dark:
            geometry["c4-context"], geometry["c4-container"] = geo, geo2
            warnings += warn + warn2
        for env in model.get("deployment", {}).get("environments", []):
            html, geo, warn = render_deployment(model, env, tokens, dark)
            (out / f"c4-deployment-{env['id']}{suffix}.html").write_text(html)
            if not dark:
                geometry[f"c4-deployment-{env['id']}"] = geo
                warnings += warn
    (out / "c4-tables.md").write_text(tables(model))
    geometry["warnings"] = list(dict.fromkeys(warnings))
    (out / "c4-geometry.json").write_text(json.dumps(geometry))
    for w in geometry["warnings"]:
        print("WARN", w)
    print(f"profile {profile['name']}; wrote", ", ".join(sorted(p.name for p in out.iterdir() if p.name.startswith("c4-"))))


if __name__ == "__main__":
    main()
