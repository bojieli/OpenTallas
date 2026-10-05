#!/usr/bin/env python3
"""Render the public OpenTallas visual gallery from checked repository evidence.

The output deliberately separates three visual classes:

* conceptual SVG diagrams, visibly labelled as concepts;
* plots calculated from the checked JSON/CSV simulation records; and
* layout views rendered from archived Magic/DEF physical geometry.

No conceptual image is presented as fabricated silicon, and no open-PDK local
slice is scaled into an N7/N4 product claim.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import warnings
from collections import defaultdict
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
# Some mixed distro/user Matplotlib installations cannot import the optional 3-D
# projection. This renderer uses only 2-D axes, so keep that unrelated warning
# out of otherwise clean regeneration logs.
warnings.filterwarnings("ignore", message="Unable to import Axes3D.*", category=UserWarning)
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle
from matplotlib.ticker import FuncFormatter, ScalarFormatter


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "assets"

BG = "#07111f"
PANEL = "#0f1d30"
PANEL_2 = "#14263d"
TEXT = "#edf5ff"
MUTED = "#9fb3ca"
GRID = "#263b55"
CYAN = "#35d4c7"
BLUE = "#5aa7ff"
PURPLE = "#ad8cff"
AMBER = "#f5c85b"
GREEN = "#62d6a4"
RED = "#ff7182"

FONT = "Inter,Segoe UI,Roboto,Helvetica,Arial,sans-serif"


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def svg_document(title: str, description: str, body: Iterable[str], *, width: int = 1600, height: int = 900) -> str:
    elements = "\n".join(body)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{escape(description)}</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#07111f"/><stop offset="1" stop-color="#0b1b2d"/></linearGradient>
    <linearGradient id="cyanGlow" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#35d4c7" stop-opacity=".28"/><stop offset="1" stop-color="#5aa7ff" stop-opacity=".08"/></linearGradient>
    <pattern id="microGrid" width="22" height="22" patternUnits="userSpaceOnUse"><path d="M22 0H0V22" fill="none" stroke="#29415d" stroke-width="1" opacity=".34"/></pattern>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="12" stdDeviation="14" flood-color="#000" flood-opacity=".25"/></filter>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#5aa7ff"/></marker>
    <marker id="arrowCyan" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#35d4c7"/></marker>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg)"/>
  {elements}
</svg>'''


def srect(x: float, y: float, width: float, height: float, *, fill: str = PANEL, stroke: str = GRID, radius: float = 18, stroke_width: float = 2, opacity: float = 1, extra: str = "") -> str:
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" fill="{fill}" fill-opacity="{opacity}" stroke="{stroke}" stroke-width="{stroke_width}" {extra}/>'


def stext(x: float, y: float, value: str, *, size: float = 24, fill: str = TEXT, weight: int = 400, anchor: str = "start", opacity: float = 1, extra: str = "") -> str:
    return f'<text x="{x}" y="{y}" fill="{fill}" fill-opacity="{opacity}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" {extra}>{escape(value)}</text>'


def smultiline(x: float, y: float, lines: Iterable[str], *, size: float = 22, fill: str = TEXT, weight: int = 400, anchor: str = "start", line_height: float = 1.35) -> str:
    spans = []
    for index, line in enumerate(lines):
        dy = 0 if index == 0 else size * line_height
        spans.append(f'<tspan x="{x}" dy="{dy}">{escape(line)}</tspan>')
    return f'<text x="{x}" y="{y}" fill="{fill}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">' + "".join(spans) + "</text>"


def sline(x1: float, y1: float, x2: float, y2: float, *, stroke: str = BLUE, width: float = 3, dash: str | None = None, marker: str | None = None, opacity: float = 1) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    marker_attr = f' marker-end="url(#{marker})"' if marker else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{width}" stroke-opacity="{opacity}" stroke-linecap="round"{dash_attr}{marker_attr}/>'


def pill(x: float, y: float, label: str, *, color: str, width: float) -> list[str]:
    return [
        srect(x, y, width, 38, fill=color, stroke=color, radius=19, opacity=.13, stroke_width=1),
        stext(x + width / 2, y + 26, label.upper(), size=15, fill=color, weight=700, anchor="middle", extra='letter-spacing="1.4"'),
    ]


def render_architecture_overview(output: Path) -> None:
    body: list[str] = []
    body += pill(70, 54, "conceptual architecture", color=AMBER, width=285)
    body.append(stext(70, 132, "OpenTallas: a fixed model becomes the machine", size=48, weight=750))
    body.append(stext(70, 177, "Autoregressive decode pipeline · immutable weights local to compute · mutable state kept in HBM", size=24, fill=MUTED))

    # Host command and stage pipeline.
    body.append(srect(70, 265, 190, 220, fill=PANEL_2, stroke=BLUE, extra='filter="url(#shadow)"'))
    body.append(stext(165, 310, "HOST / RUNTIME", size=18, fill=BLUE, weight=700, anchor="middle"))
    body.append(smultiline(165, 355, ["session", "token position", "context length", "image + epoch"], size=20, anchor="middle", fill=TEXT))
    body.append(sline(260, 375, 330, 375, marker="arrow"))

    stage_x = [330, 700, 1070]
    stage_titles = ["STAGE 0", "STAGE 1", "STAGE S−1"]
    stage_subtitles = ["early layers", "middle layers", "final layers"]
    for x, title, subtitle in zip(stage_x, stage_titles, stage_subtitles):
        body.append(srect(x, 235, 300, 490, fill=PANEL, stroke=CYAN, extra='filter="url(#shadow)"'))
        body.append(srect(x + 18, 255, 264, 190, fill="url(#microGrid)", stroke=GRID, radius=12, stroke_width=1))
        for row in range(4):
            for col in range(6):
                tile_x = x + 33 + col * 41
                tile_y = 272 + row * 40
                color = CYAN if (row + col) % 3 else PURPLE
                body.append(srect(tile_x, tile_y, 30, 28, fill=color, stroke=color, radius=5, opacity=.22, stroke_width=1))
        body.append(stext(x + 150, 478, title, size=25, fill=CYAN, weight=750, anchor="middle"))
        body.append(stext(x + 150, 507, subtitle, size=18, fill=MUTED, anchor="middle"))
        body.append(srect(x + 24, 535, 122, 70, fill="#172941", stroke=PURPLE, radius=10, stroke_width=1))
        body.append(stext(x + 85, 565, "MASK ROM", size=15, fill=PURPLE, weight=700, anchor="middle"))
        body.append(stext(x + 85, 588, "fixed weights", size=14, fill=MUTED, anchor="middle"))
        body.append(srect(x + 154, 535, 122, 70, fill="#172941", stroke=BLUE, radius=10, stroke_width=1))
        body.append(stext(x + 215, 565, "HBM", size=15, fill=BLUE, weight=700, anchor="middle"))
        body.append(stext(x + 215, 588, "KV + sessions", size=14, fill=MUTED, anchor="middle"))
        body.append(srect(x + 24, 620, 252, 78, fill="#0b1728", stroke=GREEN, radius=10, stroke_width=1))
        body.append(stext(x + 150, 652, "STATIC NoC + REDUCTION", size=15, fill=GREEN, weight=700, anchor="middle"))
        body.append(stext(x + 150, 678, "deterministic collective order", size=14, fill=MUTED, anchor="middle"))

    body.append(sline(630, 470, 690, 470, marker="arrowCyan", stroke=CYAN))
    body.append(sline(1000, 470, 1060, 470, marker="arrowCyan", stroke=CYAN))
    body.append(sline(1370, 375, 1510, 375, marker="arrow"))
    body.append(stext(1510, 344, "next", size=19, fill=BLUE, weight=700, anchor="end"))
    body.append(stext(1510, 370, "token", size=19, fill=BLUE, weight=700, anchor="end"))

    body.append(srect(70, 770, 1460, 76, fill="#0a1728", stroke=GRID, radius=14, stroke_width=1))
    body.append(stext(95, 805, "KEY TRADE", size=17, fill=AMBER, weight=750))
    body.append(stext(225, 805, "model flexibility is exchanged for dense, local, parallel weight reads", size=21, weight=600))
    body.append(stext(95, 832, "BOUNDARY", size=17, fill=RED, weight=750))
    body.append(stext(225, 832, "this is the intended organization—not a completed chip floorplan or fabricated die", size=19, fill=MUTED))
    write_text(output, svg_document("OpenTallas conceptual architecture", "A conceptual view of the OpenTallas multi-stage fixed-model inference architecture. Each stage combines mask ROM weights, compute tiles, a static network, and separate HBM for mutable KV state.", body))


def model_traffic_point() -> dict[str, float]:
    with (ROOT / "results/model-traffic/sweep.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["model"] == "DeepSeek-V4-Flash-0731" and int(row["context_tokens"]) == 200000 and int(row["batch_size"]) == 1:
                return {key: float(value) for key, value in row.items() if key not in {"model", "source_revision"}}
    raise RuntimeError("missing Flash 200K B=1 model-traffic point")


def render_why_rom(output: Path) -> None:
    point = model_traffic_point()
    weight_gb = point["active_weight_read_bytes_per_step"] / 1e9
    kv_mb = point["kv_read_bytes_per_user_token"] / 1e6
    ratio = point["weight_to_kv_read_ratio"]
    body: list[str] = []
    body += pill(70, 50, "checked traffic + architecture concept", color=AMBER, width=425)
    body.append(stext(70, 128, "Why put LLM weights in ROM?", size=50, weight=760))
    body.append(stext(70, 174, "At low batch, ordinary decode can move far more immutable weight data than mutable KV data.", size=24, fill=MUTED))

    # GPU panel.
    body.append(srect(70, 240, 690, 500, fill=PANEL, stroke=BLUE, extra='filter="url(#shadow)"'))
    body.append(stext(110, 292, "CONVENTIONAL GPU DEPLOYMENT", size=20, fill=BLUE, weight=750))
    body.append(srect(110, 340, 240, 270, fill="#172942", stroke=BLUE, radius=18))
    body.append(stext(230, 390, "SHARED HBM", size=23, fill=BLUE, weight=750, anchor="middle"))
    body.append(srect(140, 425, 180, 72, fill=PURPLE, stroke=PURPLE, radius=10, opacity=.18, stroke_width=1))
    body.append(stext(230, 456, "active weights", size=18, fill=PURPLE, weight=700, anchor="middle"))
    body.append(stext(230, 481, f"{weight_gb:.2f} GB / token step", size=16, fill=TEXT, anchor="middle"))
    body.append(srect(140, 518, 180, 62, fill=BLUE, stroke=BLUE, radius=10, opacity=.18, stroke_width=1))
    body.append(stext(230, 547, "KV read", size=18, fill=BLUE, weight=700, anchor="middle"))
    body.append(stext(230, 570, f"{kv_mb:.2f} MB / token", size=16, fill=TEXT, anchor="middle"))
    body.append(sline(350, 475, 485, 475, stroke=PURPLE, width=13, marker="arrow"))
    body.append(sline(350, 550, 485, 550, stroke=BLUE, width=4, marker="arrow"))
    body.append(srect(485, 390, 210, 175, fill="#0b1728", stroke=CYAN, radius=18))
    body.append(stext(590, 438, "TENSOR CORES", size=20, fill=CYAN, weight=750, anchor="middle"))
    body.append(stext(590, 475, "weights and KV", size=18, fill=MUTED, anchor="middle"))
    body.append(stext(590, 502, "compete for HBM", size=18, fill=MUTED, anchor="middle"))
    body.append(stext(590, 536, "every decode step", size=17, fill=TEXT, weight=650, anchor="middle"))
    body.append(stext(110, 687, "The checkpoint stays the same; its active matrices are read again for the next token.", size=18, fill=MUTED))

    # OpenTallas panel.
    body.append(srect(840, 240, 690, 500, fill=PANEL, stroke=CYAN, extra='filter="url(#shadow)"'))
    body.append(stext(880, 292, "OPENTALLAS HYPOTHESIS", size=20, fill=CYAN, weight=750))
    body.append(srect(880, 340, 230, 125, fill="#241d40", stroke=PURPLE, radius=18))
    body.append(stext(995, 383, "MASK ROM", size=23, fill=PURPLE, weight=750, anchor="middle"))
    body.append(stext(995, 415, "immutable weights", size=18, fill=TEXT, anchor="middle"))
    body.append(stext(995, 443, "distributed beside MACs", size=16, fill=MUTED, anchor="middle"))
    body.append(srect(880, 515, 230, 105, fill="#172942", stroke=BLUE, radius=18))
    body.append(stext(995, 556, "HBM", size=23, fill=BLUE, weight=750, anchor="middle"))
    body.append(stext(995, 587, "mutable KV + sessions", size=17, fill=TEXT, anchor="middle"))
    body.append(sline(1110, 402, 1240, 455, stroke=PURPLE, width=13, marker="arrowCyan"))
    body.append(sline(1110, 566, 1240, 510, stroke=BLUE, width=4, marker="arrowCyan"))
    body.append(srect(1240, 390, 235, 175, fill="#0b1728", stroke=CYAN, radius=18))
    body.append(stext(1358, 438, "LOCAL MACS", size=20, fill=CYAN, weight=750, anchor="middle"))
    body.append(stext(1358, 476, "parallel ROM reads", size=18, fill=TEXT, anchor="middle"))
    body.append(stext(1358, 505, "leave HBM for state", size=18, fill=MUTED, anchor="middle"))
    body.append(stext(1358, 536, "overlap where legal", size=17, fill=TEXT, weight=650, anchor="middle"))
    body.append(smultiline(880, 674, [
        "What disappears is HBM weight traffic—not computation, KV traffic,",
        "communication, or heat.",
    ], size=17, fill=MUTED, line_height=1.35))

    body.append(srect(390, 776, 820, 77, fill="url(#cyanGlow)", stroke=CYAN, radius=18, stroke_width=1))
    body.append(stext(800, 812, f"{ratio:.1f}× more active-weight bytes than KV-read bytes", size=27, fill=CYAN, weight=750, anchor="middle"))
    body.append(stext(800, 840, "DeepSeek-V4-Flash · 200K resident context · batch 1 · uniform-routing traffic screen", size=17, fill=MUTED, anchor="middle"))
    write_text(output, svg_document("Why OpenTallas places LLM weights in ROM", "A comparison of shared GPU HBM traffic and the OpenTallas split between immutable mask ROM weights and mutable HBM KV state, using the checked DeepSeek V4 Flash 200K batch-one traffic inventory.", body))


def render_conceptual_floorplan(output: Path) -> None:
    body: list[str] = []
    body += pill(70, 52, "logical floorplan—not placed and routed", color=AMBER, width=455)
    body.append(stext(70, 130, "One stage, from reticle fields down to a service tile", size=46, weight=750))
    body.append(stext(70, 174, "The hierarchy is frozen for software and RTL; physical sizes and shapes remain target-integration work.", size=23, fill=MUTED))

    # Stage boundary with HBM stacks.
    body.append(srect(85, 230, 830, 585, fill="#0a1728", stroke=CYAN, radius=30, stroke_width=3, extra='filter="url(#shadow)"'))
    body.append(stext(500, 270, "CONCEPTUAL LOGICAL STAGE", size=19, fill=CYAN, weight=750, anchor="middle"))
    grid_x, grid_y, cell = 205, 305, 61
    for row in range(8):
        for col in range(8):
            fill = "#17314c" if (row + col) % 2 else "#142a42"
            body.append(srect(grid_x + col * cell, grid_y + row * cell, 53, 53, fill=fill, stroke=GRID, radius=5, stroke_width=1))
            if (row, col) in {(1, 1), (3, 5), (6, 2)}:
                body.append(srect(grid_x + col * cell + 8, grid_y + row * cell + 8, 37, 37, fill=CYAN, stroke=CYAN, radius=4, opacity=.18, stroke_width=1))
    body.append(stext(450, 804, "8 × 8 logical reticle fields", size=18, fill=MUTED, anchor="middle"))
    for index in range(6):
        y = 335 + index * 72
        body.append(srect(105, y, 75, 48, fill=BLUE, stroke=BLUE, radius=8, opacity=.18, stroke_width=1))
        body.append(stext(142, y + 30, "HBM", size=14, fill=BLUE, weight=700, anchor="middle"))
        body.append(srect(820, y, 75, 48, fill=BLUE, stroke=BLUE, radius=8, opacity=.18, stroke_width=1))
        body.append(stext(857, y + 30, "HBM", size=14, fill=BLUE, weight=700, anchor="middle"))
    body.append(stext(500, 296, "perimeter memory beachfront", size=15, fill=BLUE, anchor="middle"))

    # Inset.
    body.append(sline(648, 446, 984, 342, stroke=CYAN, dash="10 8", width=2, marker="arrowCyan"))
    body.append(srect(985, 230, 545, 585, fill=PANEL, stroke=PURPLE, radius=25, stroke_width=2, extra='filter="url(#shadow)"'))
    body.append(stext(1025, 277, "SERVICE TILE", size=21, fill=PURPLE, weight=750))
    blocks = [
        (1025, 315, 220, 105, PURPLE, "WEIGHT + SCALE ROM", "fixed image shards"),
        (1265, 315, 225, 105, CYAN, "FORMAT + MAC LANES", "local dot products"),
        (1025, 445, 220, 105, BLUE, "ACTIVATION SRAM", "buffers + partial sums"),
        (1265, 445, 225, 105, GREEN, "STATIC SWITCH", "certified time slots"),
        (1025, 575, 220, 105, AMBER, "REPAIR + BIST", "quarantine + test"),
        (1265, 575, 225, 105, RED, "RAS + CONTROL", "CRC, poison, telemetry"),
    ]
    for x, y, w, h, color, title, subtitle in blocks:
        body.append(srect(x, y, w, h, fill=color, stroke=color, radius=13, opacity=.12, stroke_width=1))
        body.append(stext(x + w / 2, y + 42, title, size=16, fill=color, weight=750, anchor="middle"))
        body.append(stext(x + w / 2, y + 72, subtitle, size=15, fill=MUTED, anchor="middle"))
    body.append(srect(1025, 708, 465, 70, fill="#0a1728", stroke=GRID, radius=12, stroke_width=1))
    body.append(stext(1257, 738, "64 service tiles / reticle field", size=18, fill=TEXT, weight=650, anchor="middle"))
    body.append(stext(1257, 763, "4,096 logical tiles / stage in the public-reference contract", size=15, fill=MUTED, anchor="middle"))
    write_text(output, svg_document("OpenTallas conceptual stage floorplan", "A logical—not physical—stage floorplan showing 8 by 8 reticle fields, HBM at the perimeter, and the responsibilities inside one service tile.", body))


def render_evidence_ladder(output: Path) -> None:
    sim = read_json("results/rtl/simulation_campaign.json")
    formal = read_json("results/rtl/formal_campaign.json")
    static = read_json("results/rtl/static_campaign.json")
    coverage = read_json("results/rtl/coverage_campaign.json")
    fault = read_json("results/rtl/fault_campaign.json")
    sky = read_json("results/spice/sky130_physical/physical.json")
    sky_pvt = read_json("results/spice/sky130_extracted_pvt.json")
    sky_rc = read_json("results/spice/sky130_resistance/resistance.json")
    ihp = read_json("results/spice/ihp_sg13g2_physical/physical.json")
    ihp_pvt = read_json("results/spice/ihp_sg13g2_extracted_pvt.json")
    ihp_rc = read_json("results/spice/ihp_sg13g2_resistance/resistance.json")
    asap = read_json("results/asap7_physical/physical.json")
    rtl_ok = all(campaign["status"] == "pass" for campaign in (sim, formal, static, coverage, fault))
    local_ok = all(campaign["status"] == "pass" for campaign in (sky, sky_pvt, sky_rc, ihp, ihp_pvt, ihp_rc))
    steps = [
        ("1", "MODEL ACCOUNTING", "exact checkpoint bytes, operator shapes, KV traffic", GREEN, "DONE"),
        ("2", "ARCHITECTURE SIMULATION", "capacity, bandwidth, compute, NoC, pipeline, thermal envelopes", GREEN, "DONE"),
        ("3", "PUBLIC RTL", f"dual simulation, {len(formal['cases'])} formal harnesses, coverage, static checks, {fault['site_count']} directed fault sites", GREEN if rtl_ok else AMBER, "PASS" if rtl_ok else "OPEN"),
        ("4", "LOCAL ROM METHOD", "two open-PDK layouts, DRC/LVS/PEX, PVT and detailed-RC simulation", GREEN if local_ok else AMBER, "PASS" if local_ok else "OPEN"),
        ("5", "DIGITAL PHYSICAL PROXY", "one ASAP7 integer numeric block routed; campaign is 1/3 and noncanonical", AMBER, "PARTIAL"),
        ("6", "TARGET IMPLEMENTATION", "target formats, ROM macro, full stage, NoC, HBM/package, PI/thermal", RED, "OPEN"),
        ("7", "TEST SILICON", "manufacturing, yield, repair exhaustion, silicon correlation", RED, "NOT BUILT"),
    ]
    body: list[str] = []
    body += pill(70, 48, "evidence status", color=BLUE, width=190)
    body.append(stext(70, 124, "How far has OpenTallas actually progressed?", size=48, weight=750))
    body.append(stext(70, 168, "Green means repository evidence exists. Amber is partial. Red names work that still requires target technology or silicon.", size=22, fill=MUTED))
    y = 225
    for number, title, subtitle, color, status in steps:
        body.append(srect(70, y, 1460, 78, fill=PANEL, stroke=GRID, radius=14, stroke_width=1))
        body.append(f'<circle cx="113" cy="{y + 39}" r="24" fill="{color}" fill-opacity=".16" stroke="{color}" stroke-width="2"/>')
        body.append(stext(113, y + 47, number, size=20, fill=color, weight=750, anchor="middle"))
        body.append(stext(160, y + 32, title, size=18, fill=TEXT, weight=750))
        body.append(stext(160, y + 58, subtitle, size=17, fill=MUTED))
        body.append(srect(1350, y + 20, 145, 38, fill=color, stroke=color, radius=19, opacity=.13, stroke_width=1))
        body.append(stext(1422, y + 46, status, size=15, fill=color, weight=750, anchor="middle"))
        y += 91
    body.append(stext(70, 874, f"ASAP7 completed cases: {len(asap['completed_cases'])}/{len(asap['required_cases'])} · no full chip, wafer, target ROM macro, or fabricated OpenTallas silicon exists", size=17, fill=MUTED))
    write_text(output, svg_document("OpenTallas evidence ladder", "A seven-step evidence ladder showing completed model accounting, architecture simulation, public RTL and local open-PDK methods; partial digital physical work; and open target implementation and silicon stages.", body))


def setup_matplotlib() -> None:
    matplotlib.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.facecolor": PANEL,
            "axes.edgecolor": GRID,
            "axes.labelcolor": MUTED,
            "axes.titlecolor": TEXT,
            "figure.facecolor": BG,
            "savefig.facecolor": BG,
            "text.color": TEXT,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "grid.color": GRID,
            "grid.alpha": 0.55,
            "legend.facecolor": PANEL_2,
            "legend.edgecolor": GRID,
            "legend.labelcolor": TEXT,
            "svg.hashsalt": "opentallas-public-assets-v1",
        }
    )


def save_figure(fig: plt.Figure, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {"Creator": "OpenTallas tools/render_public_assets.py", "Date": None}
    fig.savefig(output, bbox_inches="tight", pad_inches=0.18, dpi=180, metadata=metadata)
    plt.close(fig)
    if output.suffix.lower() == ".svg":
        # Matplotlib emits spaces before newlines in multiline path data. Keep
        # generated text assets friendly to `git diff --check` without changing
        # any SVG geometry.
        svg = output.read_text(encoding="utf-8")
        output.write_text(re.sub(r"[ \t]+\n", "\n", svg), encoding="utf-8")


def central_comparisons(relative: str, architecture: str, model: str) -> list[dict]:
    data = read_json(relative)
    points = [
        row
        for row in data["comparisons"]
        if row["wafer_architecture"] == architecture
        and row["model"] == model
        and row["context_tokens"] == 200000
    ]
    return sorted(points, key=lambda row: row["batch_per_stage"])


def render_throughput_plot(output: Path) -> None:
    studies = [
        ("N7 architecture attribution", "results/iso-node/n7_architecture_attribution/analytical.json", "ROM-wafer-N7-HBM2e-central", "A100"),
        ("N4-class market study", "results/iso-node/leading_node_market/analytical.json", "ROM-wafer-N4-class-HBM3e-central", "B300"),
    ]
    models = [("DeepSeek V4 Flash", "DeepSeek-V4-Flash-0731"), ("DeepSeek V4 Pro", "DeepSeek-V4-Pro-0813")]
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    for col, (study_title, relative, architecture, gpu_label) in enumerate(studies):
        for row_index, (model_title, model_id) in enumerate(models):
            ax = axes[row_index, col]
            rows = central_comparisons(relative, architecture, model_id)
            batches = [row["batch_per_stage"] for row in rows]
            rom = [row["wafer_per_user_tokens_s"] for row in rows]
            gpu = [row["fastest_same_batch_gpu_per_user_tokens_s"] for row in rows]
            ax.plot(batches, rom, color=CYAN, marker="o", linewidth=2.8, markersize=7, label="ROM central envelope")
            ax.plot(batches, gpu, color=BLUE, marker="s", linewidth=2.3, markersize=6, label=f"fastest feasible {gpu_label} cluster")
            ax.set_xscale("log", base=2)
            ax.set_yscale("log")
            ax.set_xticks(batches, [str(value) for value in batches])
            ax.yaxis.set_major_formatter(ScalarFormatter())
            ax.grid(True, which="both", linestyle="--", linewidth=.7)
            ax.set_title(f"{study_title}\n{model_title} · 200K context", fontsize=14, fontweight="bold", loc="left")
            ax.set_xlabel("batch per stage")
            ax.set_ylabel("per-user tokens/s")
            ratio_1 = rows[0]["same_batch_per_user_speed_ratio"]
            ratio_last = rows[-1]["same_batch_per_user_speed_ratio"]
            ax.text(.97, .93, f"B=1  {ratio_1:.1f}×\nB={batches[-1]}  {ratio_last:.1f}×", transform=ax.transAxes, ha="right", va="top", color=AMBER, fontsize=10, fontweight="bold")
            if row_index == 0 and col == 0:
                ax.legend(loc="lower left", fontsize=9)
    fig.suptitle("Simulated decode throughput at 200K resident context", fontsize=22, fontweight="bold", color=TEXT)
    fig.text(.5, -.012, "Central deterministic hardware envelope; fastest feasible same-batch GPU candidate. These are analytical results, not measured silicon throughput.", ha="center", color=MUTED, fontsize=11)
    save_figure(fig, output)


def render_uncertainty_plot(output: Path) -> None:
    studies = [
        ("N7 vs A100", "results/iso-node/n7_architecture_attribution/analytical.json", "ROM-wafer-N7-HBM2e-central"),
        ("N4-class vs B300", "results/iso-node/leading_node_market/analytical.json", "ROM-wafer-N4-class-HBM3e-central"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), constrained_layout=True)
    for ax, (title, relative, central_arch) in zip(axes, studies):
        data = read_json(relative)
        bands = sorted(
            [row for row in data["uncertainty_bands"] if row["model"] == "DeepSeek-V4-Flash-0731" and row["context_tokens"] == 200000],
            key=lambda row: row["batch_per_stage"],
        )
        central = central_comparisons(relative, central_arch, "DeepSeek-V4-Flash-0731")
        batches = [row["batch_per_stage"] for row in bands]
        low = [row["rom_per_user_tokens_s_low"] for row in bands]
        high = [row["rom_per_user_tokens_s_high"] for row in bands]
        mid = [row["wafer_per_user_tokens_s"] for row in central]
        gpu = [row["fastest_same_batch_gpu_per_user_tokens_s"] for row in central]
        ax.fill_between(batches, low, high, color=CYAN, alpha=.18, label="conservative–aggressive envelope")
        ax.plot(batches, low, color=CYAN, alpha=.6, linewidth=1)
        ax.plot(batches, high, color=CYAN, alpha=.6, linewidth=1)
        ax.plot(batches, mid, color=CYAN, marker="o", linewidth=2.6, label="central envelope")
        ax.plot(batches, gpu, color=BLUE, marker="s", linewidth=2.2, label="fastest same-batch GPU")
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_xticks(batches, [str(value) for value in batches])
        ax.yaxis.set_major_formatter(ScalarFormatter())
        ax.grid(True, which="both", linestyle="--", linewidth=.7)
        ax.set_title(title, loc="left", fontsize=16, fontweight="bold")
        ax.set_xlabel("batch per stage")
        ax.set_ylabel("per-user tokens/s")
        ax.legend(loc="lower left", fontsize=9)
    fig.suptitle("The honest range is much wider than one headline number", fontsize=22, fontweight="bold")
    fig.text(.5, -.025, "DeepSeek V4 Flash · 200K context. Bands are deterministic hardware envelopes—not confidence intervals or measured error bars.", ha="center", color=MUTED, fontsize=11)
    save_figure(fig, output)


def render_spice_results(output: Path) -> None:
    sky = read_json("results/spice/sky130_extracted_pvt.json")
    ihp = read_json("results/spice/ihp_sg13g2_extracted_pvt.json")
    mismatch = read_json("results/spice/sky130_extracted_mismatch.json")
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), constrained_layout=True)
    corner_colors = {"ff": CYAN, "tt": BLUE, "ss": PURPLE}
    for ax, data, title in [(axes[0], sky, "SKY130A extracted PVT"), (axes[1], ihp, "IHP SG13G2 extracted PVT")]:
        for corner in ["ff", "tt", "ss"]:
            rows = [case for case in data["cases"] if case["process_corner"] == corner]
            if not rows:
                continue
            loads = [case["output_load_ff"] for case in rows]
            delays = [case["metrics"]["discharge_delay_ns"] * 1000 for case in rows]
            temps = [case["temperature_c"] for case in rows]
            sizes = [34 + (temperature + 40) / 3.8 for temperature in temps]
            ax.scatter(loads, delays, s=sizes, c=corner_colors[corner], alpha=.8, edgecolors=BG, linewidths=.4, label=corner.upper())
        ax.grid(True, linestyle="--", linewidth=.7)
        ax.set_title(title, loc="left", fontsize=14, fontweight="bold")
        ax.set_xlabel("declared output load (fF)")
        ax.set_ylabel("programmed discharge delay (ps)")
        ax.legend(title="corner", fontsize=8, title_fontsize=8)
        ax.text(.98, .05, f"{data['summary']['cases_passed']}/{data['summary']['cases_total']} pass", transform=ax.transAxes, ha="right", color=GREEN, fontweight="bold")
    delays = [sample["metrics"]["discharge_delay_ns"] * 1000 for sample in mismatch["samples"]]
    axes[2].hist(delays, bins=20, color=CYAN, alpha=.72, edgecolor=BG)
    dist = mismatch["summary"]["distributions"]["discharge_delay_ns"]
    for key, color in [("p05", PURPLE), ("p50", AMBER), ("p95", PURPLE)]:
        value = dist["quantiles"][key] * 1000
        axes[2].axvline(value, color=color, linewidth=2, linestyle="--" if key != "p50" else "-")
        axes[2].text(value, axes[2].get_ylim()[1] * .94, key, color=color, ha="center", va="top", fontsize=9, fontweight="bold")
    axes[2].grid(True, axis="y", linestyle="--", linewidth=.7)
    axes[2].set_title("SKY130A fixed-seed mismatch", loc="left", fontsize=14, fontweight="bold")
    axes[2].set_xlabel("programmed discharge delay (ps)")
    axes[2].set_ylabel("samples")
    axes[2].text(.98, .05, f"{mismatch['summary']['samples_passed']}/{mismatch['summary']['samples_total']} pass", transform=axes[2].transAxes, ha="right", color=GREEN, fontweight="bold")
    fig.suptitle("Circuit simulation of the actual extracted two-column test slices", fontsize=21, fontweight="bold")
    fig.text(.5, -.02, "Local open-PDK methodology evidence only. Marker size tracks temperature. These results do not scale to N7/N4, a compact array, yield, or whole-wafer throughput.", ha="center", color=MUTED, fontsize=10.5)
    save_figure(fig, output)


@dataclass
class MagUse:
    cell: str
    transform: tuple[int, int, int, int, int, int]


@dataclass
class MagCell:
    rects: dict[str, list[tuple[int, int, int, int]]] = field(default_factory=lambda: defaultdict(list))
    labels: list[tuple[str, int, int, int, int, str]] = field(default_factory=list)
    uses: list[MagUse] = field(default_factory=list)
    bbox: tuple[int, int, int, int] | None = None


def parse_mag(path: Path) -> MagCell:
    cell = MagCell()
    section = ""
    pending_use: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("<< ") and line.endswith(" >>"):
            section = line[3:-3]
            pending_use = None
            continue
        if line.startswith("use "):
            parts = line.split()
            pending_use = parts[1]
            continue
        if pending_use and line.startswith("transform "):
            values = tuple(int(value) for value in line.split()[1:7])
            cell.uses.append(MagUse(pending_use, values))
            pending_use = None
            continue
        if line.startswith("rect ") and section not in {"checkpaint", "comment", "properties", "labels", "end"}:
            values = tuple(int(value) for value in line.split()[1:5])
            cell.rects[section].append(values)
        elif line.startswith("rlabel "):
            parts = line.split(maxsplit=7)
            if len(parts) == 8:
                cell.labels.append((parts[1], int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5]), parts[7]))
        elif line.startswith("string FIXED_BBOX "):
            values = tuple(int(value) for value in line.split()[2:6])
            cell.bbox = values
    return cell


Transform = tuple[int, int, int, int, int, int]


def compose(parent: Transform, child: Transform) -> Transform:
    pa, pb, pc, pd, pe, pf = parent
    ca, cb, cc, cd, ce, cf = child
    return (
        pa * ca + pb * cd,
        pa * cb + pb * ce,
        pa * cc + pb * cf + pc,
        pd * ca + pe * cd,
        pd * cb + pe * ce,
        pd * cc + pe * cf + pf,
    )


def transform_point(transform: Transform, x: int, y: int) -> tuple[int, int]:
    a, b, c, d, e, f = transform
    return a * x + b * y + c, d * x + e * y + f


def mag_geometry(top: Path) -> tuple[dict[str, list[tuple[int, int, int, int]]], MagCell]:
    cache: dict[str, MagCell] = {}
    geometry: dict[str, list[tuple[int, int, int, int]]] = defaultdict(list)

    def load(name: str) -> MagCell:
        if name not in cache:
            cache[name] = parse_mag(top.parent / f"{name}.mag")
        return cache[name]

    def visit(name: str, transform: Transform) -> None:
        cell = load(name)
        for layer, rects in cell.rects.items():
            for x1, y1, x2, y2 in rects:
                corners = [transform_point(transform, x1, y1), transform_point(transform, x1, y2), transform_point(transform, x2, y1), transform_point(transform, x2, y2)]
                xs = [point[0] for point in corners]
                ys = [point[1] for point in corners]
                geometry[layer].append((min(xs), min(ys), max(xs), max(ys)))
        for use in cell.uses:
            visit(use.cell, compose(transform, use.transform))

    top_cell = parse_mag(top)
    cache[top.stem] = top_cell
    visit(top.stem, (1, 0, 0, 0, 1, 0))
    return geometry, top_cell


MAG_LAYER_STYLES: dict[str, tuple[str, float, int]] = {
    "pwell": ("#164a62", .24, 0),
    "nwell": ("#6d3f88", .25, 0),
    "nmos": ("#2eaf83", .55, 1),
    "pmos": ("#d8639b", .55, 1),
    "ndiff": ("#3fdd9d", .62, 2),
    "pdiff": ("#ff79b1", .62, 2),
    "psubdiff": ("#36b7a7", .5, 2),
    "nsubdiff": ("#c56fe0", .5, 2),
    "poly": ("#ff6f61", .75, 3),
    "locali": ("#d2dae5", .55, 4),
    "metal1": (CYAN, .72, 5),
    "metal2": (PURPLE, .68, 7),
    "metal3": (AMBER, .72, 9),
    "via1": ("#ffffff", .9, 8),
    "via2": ("#fff1a8", .95, 10),
    "viali": ("#e8eff9", .8, 6),
    "ndiffc": ("#b8ffe2", .85, 4),
    "pdiffc": ("#ffd2e5", .85, 4),
    "polycont": ("#ffe5ad", .85, 4),
    "psubdiffcont": ("#e8eff9", .85, 4),
    "nsubdiffcont": ("#e8eff9", .85, 4),
}


def render_mag_layout(
    top_relative: str,
    physical_relative: str,
    pvt_relative: str,
    output: Path,
    *,
    process_name: str,
    programmed_xy_um: tuple[float, float],
    absent_xy_um: tuple[float, float],
) -> None:
    top = ROOT / top_relative
    physical = read_json(physical_relative)
    pvt = read_json(pvt_relative)
    geometry, top_cell = mag_geometry(top)
    fig = plt.figure(figsize=(15.5, 7.4), constrained_layout=True)
    grid_spec = fig.add_gridspec(1, 2, width_ratios=[4.5, 1.35])
    ax = fig.add_subplot(grid_spec[0, 0])
    info = fig.add_subplot(grid_spec[0, 1])
    ax.set_facecolor("#050b14")
    scale = .005
    for layer, (color, alpha, zorder) in sorted(MAG_LAYER_STYLES.items(), key=lambda item: item[1][2]):
        rectangles = [Rectangle((x1 * scale, y1 * scale), (x2 - x1) * scale, (y2 - y1) * scale) for x1, y1, x2, y2 in geometry.get(layer, [])]
        if rectangles:
            collection = PatchCollection(rectangles, facecolor=color, edgecolor=color, linewidth=.16, alpha=alpha, zorder=zorder)
            ax.add_collection(collection)
    ax.axvspan(0, 14.5, color=CYAN, alpha=.025)
    ax.axvspan(18, 32.5, color=PURPLE, alpha=.025)
    ax.text(7.25, 11.08, "PROGRAMMED COLUMN", color=CYAN, fontsize=10, fontweight="bold", ha="center")
    ax.text(25.25, 11.08, "ABSENT-VIA COLUMN", color=PURPLE, fontsize=10, fontweight="bold", ha="center")
    ax.add_patch(Circle(programmed_xy_um, .48, fill=False, edgecolor=AMBER, linewidth=2.2, zorder=20))
    ax.annotate("programming via", programmed_xy_um, xytext=(programmed_xy_um[0] + 2.0, programmed_xy_um[1] - 1.2), color=AMBER, fontsize=9, arrowprops={"arrowstyle": "->", "color": AMBER, "lw": 1.5}, zorder=21)
    ax.add_patch(Circle(absent_xy_um, .48, fill=False, edgecolor=MUTED, linewidth=1.6, linestyle="--", zorder=20))
    ax.annotate("same site, via absent", absent_xy_um, xytext=(absent_xy_um[0] + 1.4, absent_xy_um[1] - 1.2), color=MUTED, fontsize=9, arrowprops={"arrowstyle": "->", "color": MUTED, "lw": 1.2}, zorder=21)
    for _, x1, y1, x2, y2, label in top_cell.labels:
        if label.startswith(("WL_", "EN_", "PRE_", "Q_", "VGND", "VPWR")):
            ax.text((x1 + x2) * scale / 2, (y1 + y2) * scale / 2, label.replace("_", " "), fontsize=5.8, color=TEXT, ha="center", va="center", zorder=25)
    ax.set_xlim(-.3, 32.8)
    ax.set_ylim(-.2, 11.7)
    ax.set_aspect("equal")
    ax.set_xlabel("µm")
    ax.set_ylabel("µm")
    ax.grid(False)
    ax.set_title(f"{process_name} archived Magic geometry", fontsize=18, fontweight="bold", loc="left", pad=14)
    for spine in ax.spines.values():
        spine.set_color(GRID)

    info.axis("off")
    layout = physical["metrics"]["layout"]
    parasitics = physical["metrics"]["parasitics"]
    topology = physical["metrics"]["topology"]
    lines = [
        ("ACTUAL LOCAL LAYOUT", AMBER, 12, "bold"),
        ("not a full ROM macro", MUTED, 10, "normal"),
        ("", TEXT, 10, "normal"),
        (f"{layout['bbox_um'][2]:.1f} × {layout['bbox_um'][3]:.1f} µm", TEXT, 15, "bold"),
        (f"{topology['device_count']} MOS · {topology['net_count']} nets", TEXT, 11, "normal"),
        (f"{layout['programming_via1']['present_column_count']} vs {layout['programming_via1']['absent_column_count']} via1", TEXT, 11, "normal"),
        ("", TEXT, 10, "normal"),
        ("DRC", MUTED, 10, "bold"),
        (f"{physical['verification']['drc']['errors']} errors", GREEN, 15, "bold"),
        ("LVS", MUTED, 10, "bold"),
        ("unique match", GREEN, 15, "bold"),
        ("PEX", MUTED, 10, "bold"),
        (f"{parasitics['total_extracted_capacitance_ff']:.2f} fF total C", GREEN, 14, "bold"),
        ("PVT / LOAD", MUTED, 10, "bold"),
        (f"{pvt['summary']['cases_passed']}/{pvt['summary']['cases_total']} pass", GREEN, 15, "bold"),
        ("", TEXT, 10, "normal"),
        ("Roomy two-column", MUTED, 10, "normal"),
        ("methodology slice.", MUTED, 10, "normal"),
        ("No density, target-node,", RED, 9.5, "normal"),
        ("yield, or product claim.", RED, 9.5, "normal"),
    ]
    y = .95
    for line, color, size, weight in lines:
        info.text(.06, y, line, transform=info.transAxes, color=color, fontsize=size, fontweight=weight, va="top")
        y -= .046 if line else .028
    legend_y = .08
    for index, (name, color) in enumerate([("M1", CYAN), ("M2", PURPLE), ("M3", AMBER), ("poly", "#ff6f61"), ("diffusion", GREEN)]):
        x = .06 + (index % 2) * .47
        yy = legend_y - (index // 2) * .045
        info.add_patch(Rectangle((x, yy), .06, .018, transform=info.transAxes, facecolor=color, edgecolor="none"))
        info.text(x + .08, yy + .009, name, transform=info.transAxes, color=MUTED, fontsize=8.5, va="center")
    save_figure(fig, output)


def parse_def(path: Path) -> tuple[tuple[float, float], list[tuple[str, str, float, float]], dict[str, list[tuple[tuple[float, float], tuple[float, float]]]], dict[str, list[tuple[tuple[float, float], tuple[float, float]]]]]:
    text = path.read_text(encoding="utf-8")
    die_match = re.search(r"DIEAREA\s+\(\s*0\s+0\s*\)\s+\(\s*(\d+)\s+(\d+)\s*\)", text)
    if not die_match:
        raise RuntimeError("DEF die area not found")
    die = (int(die_match.group(1)) / 1000, int(die_match.group(2)) / 1000)
    components: list[tuple[str, str, float, float]] = []
    routes: dict[str, list[tuple[tuple[float, float], tuple[float, float]]]] = defaultdict(list)
    special: dict[str, list[tuple[tuple[float, float], tuple[float, float]]]] = defaultdict(list)
    section = ""
    component_pattern = re.compile(r"^\s*-\s+(\S+)\s+(\S+).*\+\s+(?:PLACED|FIXED)\s+\(\s*(\d+)\s+(\d+)\s*\)")
    route_pattern = re.compile(r"(?:\+\s+ROUTED|\bNEW)\s+(M\d+)")
    coord_pattern = re.compile(r"\(\s*(-?\d+|\*)\s+(-?\d+|\*)\s*\)")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("COMPONENTS "):
            section = "components"
            continue
        if stripped.startswith("SPECIALNETS "):
            section = "special"
            continue
        if stripped.startswith("NETS "):
            section = "nets"
            continue
        if stripped.startswith("END "):
            section = ""
            continue
        if section == "components":
            match = component_pattern.match(line)
            if match:
                components.append((match.group(1), match.group(2), int(match.group(3)) / 1000, int(match.group(4)) / 1000))
        elif section in {"special", "nets"}:
            layer_match = route_pattern.search(line)
            if not layer_match:
                continue
            route_part = line.split("RECT", 1)[0]
            raw_coords = coord_pattern.findall(route_part)
            if len(raw_coords) < 2:
                continue
            coords: list[tuple[int, int]] = []
            for raw_x, raw_y in raw_coords:
                if not coords and (raw_x == "*" or raw_y == "*"):
                    break
                previous = coords[-1] if coords else (0, 0)
                x = previous[0] if raw_x == "*" else int(raw_x)
                y = previous[1] if raw_y == "*" else int(raw_y)
                coords.append((x, y))
            target = special if section == "special" else routes
            for first, second in zip(coords, coords[1:]):
                if first != second:
                    target[layer_match.group(1)].append(((first[0] / 1000, first[1] / 1000), (second[0] / 1000, second[1] / 1000)))
    return die, components, routes, special


def render_def_layout(output: Path) -> None:
    def_path = ROOT / "results/asap7_physical/numeric_e1_l16_tc/artifacts/6_final.def"
    physical = read_json("results/asap7_physical/physical.json")
    case = physical["cases"]["numeric_e1_l16_tc"]
    metrics = case["metrics"]
    die, components, routes, special = parse_def(def_path)
    fig = plt.figure(figsize=(14.5, 8.2), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=[4.25, 1.25])
    ax = fig.add_subplot(gs[0, 0])
    info = fig.add_subplot(gs[0, 1])
    ax.set_facecolor("#030914")
    layer_colors = {"M1": "#3672a8", "M2": "#3b95c5", "M3": CYAN, "M4": PURPLE, "M5": AMBER, "M6": RED, "M7": GREEN}
    for layer, segments in routes.items():
        if segments:
            ax.add_collection(LineCollection(segments, colors=layer_colors.get(layer, MUTED), linewidths=.12, alpha=.13, zorder=2))
    for layer, segments in special.items():
        if segments:
            ax.add_collection(LineCollection(segments, colors=layer_colors.get(layer, AMBER), linewidths=1.0 if layer in {"M5", "M6"} else .25, alpha=.35, zorder=3))
    categories: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for instance, master, x, y in components:
        name = f"{instance} {master}".upper()
        if any(token in name for token in ("FILLER", "DECAP", "TAPCELL")):
            category = "filler / decap"
        elif "DFF" in name or "SDF" in name:
            category = "register"
        elif "CLK" in name:
            category = "clock tree"
        else:
            category = "logic"
        categories[category].append((x, y))
    styles = {
        "filler / decap": ("#28405a", 1.0, .18),
        "logic": (BLUE, 1.2, .40),
        "register": (AMBER, 4.0, .85),
        "clock tree": (GREEN, 3.0, .75),
    }
    for category in ["filler / decap", "logic", "clock tree", "register"]:
        points = categories[category]
        if points:
            color, size, alpha = styles[category]
            ax.scatter([point[0] for point in points], [point[1] for point in points], s=size, c=color, alpha=alpha, linewidths=0, label=category, zorder=5)
    ax.add_patch(Rectangle((0, 0), die[0], die[1], fill=False, edgecolor=TEXT, linewidth=1.2, zorder=10))
    ax.set_xlim(-.5, die[0] + .5)
    ax.set_ylim(-.5, die[1] + .5)
    ax.set_aspect("equal")
    ax.set_xlabel("µm")
    ax.set_ylabel("µm")
    ax.set_title("Routed ASAP7 predictive digital proxy · ot_numeric_dot", fontsize=17, fontweight="bold", loc="left", pad=12)
    ax.legend(loc="upper left", fontsize=8, markerscale=3, ncol=2)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_color(GRID)

    info.axis("off")
    lines = [
        ("ACTUAL ROUTED DEF", AMBER, 12, "bold"),
        ("predictive research PDK", MUTED, 10, "normal"),
        ("", TEXT, 10, "normal"),
        ("signed integer DV block", TEXT, 13, "bold"),
        ("1 expert · 16 lanes", TEXT, 11, "normal"),
        (f"{die[0]:.2f} × {die[1]:.2f} µm die", TEXT, 11, "normal"),
        ("", TEXT, 10, "normal"),
        ("FMAX", MUTED, 10, "bold"),
        (f"{metrics['fmax_hz'] / 1e6:.1f} MHz", GREEN, 16, "bold"),
        ("SETUP / HOLD WNS", MUTED, 10, "bold"),
        (f"{metrics['setup_wns_ns']:.4f} / {metrics['hold_wns_ns']:.4f} ns", GREEN, 13, "bold"),
        ("ROUTING", MUTED, 10, "bold"),
        (f"{metrics['wirelength_um']:,.0f} µm wire", TEXT, 12, "bold"),
        (f"{int(metrics['vias']):,} vias", TEXT, 12, "bold"),
        ("DRC / ANTENNA", MUTED, 10, "bold"),
        (f"{int(metrics['drc_errors'])} / {int(metrics['antenna_violating_nets'])} violations", GREEN, 14, "bold"),
        ("", TEXT, 10, "normal"),
        ("Campaign status: 1/3", AMBER, 11, "bold"),
        ("noncanonical dirty-tree run", AMBER, 9.5, "normal"),
        ("No ROM/SRAM macro.", RED, 9.5, "normal"),
        ("No target numeric formats.", RED, 9.5, "normal"),
        ("Not a product floorplan.", RED, 9.5, "normal"),
    ]
    y = .96
    for line, color, size, weight in lines:
        info.text(.05, y, line, transform=info.transAxes, color=color, fontsize=size, fontweight=weight, va="top")
        y -= .045 if line else .026
    save_figure(fig, output)


def render_all(output_dir: Path) -> None:
    setup_matplotlib()
    output_dir.mkdir(parents=True, exist_ok=True)
    render_architecture_overview(output_dir / "architecture-overview.svg")
    render_why_rom(output_dir / "why-rom.svg")
    render_conceptual_floorplan(output_dir / "conceptual-stage-floorplan.svg")
    render_evidence_ladder(output_dir / "evidence-ladder.svg")
    render_throughput_plot(output_dir / "throughput-at-200k.svg")
    render_uncertainty_plot(output_dir / "uncertainty-at-200k.svg")
    render_spice_results(output_dir / "extracted-rom-simulations.svg")
    render_mag_layout(
        "results/spice/sky130_physical/artifacts/sky130_rom_slice.mag",
        "results/spice/sky130_physical/physical.json",
        "results/spice/sky130_extracted_pvt.json",
        output_dir / "sky130-rom-slice.png",
        process_name="SKY130A",
        programmed_xy_um=(2.57, 3.13),
        absent_xy_um=(20.57, 3.13),
    )
    render_mag_layout(
        "results/spice/ihp_sg13g2_physical/artifacts/ihp_sg13g2_rom_slice.mag",
        "results/spice/ihp_sg13g2_physical/physical.json",
        "results/spice/ihp_sg13g2_extracted_pvt.json",
        output_dir / "ihp-sg13g2-rom-slice.png",
        process_name="IHP SG13G2",
        programmed_xy_um=(1.50, 2.68),
        absent_xy_um=(19.50, 2.68),
    )
    render_def_layout(output_dir / "asap7-routed-numeric.png")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT, help="destination directory (default: docs/assets)")
    args = parser.parse_args()
    render_all(args.output_dir.resolve())
    print(f"rendered OpenTallas public assets in {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
