#!/usr/bin/env python3
"""post_place_review.py (STAGE-PLATEAU): post-placement review kit for a kit's 3_3_place_gp / 3_5_place_dp ODB.

    post_place_review.py --kit K --odb ODB --image IMG [--id ID] [--out DIR] [--npath 50] [--mem GB] [--dry-run]
        builds <kit>/review (fallback ~/.local/state/noprog/review/<id>), writes run.tcl + run.sh and launches
        `nice -n 10 ot-run --direct --threads 2 --mem N --dir DIR --no-spill -- bash DIR/run.sh` (same pattern as
        noprog_watchdog.smell_render).  run.sh runs tools/autopilot/post_place_review.tcl in the pinned ORFS image
        (kit mounted read-only), then `post_place_review.py --finish DIR` on the host python.
    post_place_review.py --finish DIR      post-process the tcl dumps into the review products.

Products in the review dir: paths_ideal.tsv / paths_ideal.txt (top-N setup paths, IDEAL clock, placement parasitics),
density.png, rudy.png (RUDY routing-demand estimate from the placed net bounding boxes), flight_lines.png (top-N paths
start -> via cells -> end on the layout), macro_pg_overlay.png (macro halos and pin faces versus PG straps), summary.json.
Pictures use PIL when importable, else SVG with the same name.  No headless GUI / save_image is used: the geometry is dumped
from the DB and drawn here.  Pure helpers (parse_paths, hpwl, rudy_grid, pg_overlaps, queue_row, ...) need no OpenROAD.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TCL_TOOLS = [HERE / "post_place_review.tcl", HERE.parent / "ref_tile" / "layout_dump.tcl", HERE.parent / "ref_tile" / "layout_review.tcl"]
VIS_QUEUE_HEADER = "t\ttype\tdie\tcheckpoint\trender\tstatus\towner\tkit\treview"
PIN_RE = re.compile(r"^\s*(?:-?\d+(?:\.\d+)?\s+)+([\^v])\s+(\S+)\s+\((\S+)\)")
SLACK_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s+slack\b")


# ------------------------------------------------------------------------------------------------ pure helpers
def queue_row(t, type_, die, checkpoint, host, rdir, status, owner, kit, log="LOG"):
    """one lanes/VIS-QUEUE.tsv line (no newline): t, type, die, checkpoint, host:dir, status, owner, kit, LOG.  The hub appends it."""
    cols = [str(int(t)), type_, die, checkpoint, f"{host}:{rdir}" if host else str(rdir), status, owner, str(kit), log]
    return "\t".join(str(c).replace("\t", " ").replace("\n", " ") for c in cols)


def parse_paths(text):
    """report_checks -format full text -> [{start,end,group,slack,pins:[(pin,edge,cell)]}]; pins are the DATA path only
    (launch clock pin ... endpoint pin), i.e. up to the first 'data arrival time'."""
    out, cur, in_data = [], None, False
    for ln in (text or "").splitlines():
        s = ln.strip()
        if s.startswith("Startpoint:"):
            cur = {"start": s.split()[1], "end": "", "group": "", "slack": None, "pins": []}
            out.append(cur)
            in_data = True
        elif cur is None:
            continue
        elif s.startswith("Endpoint:"):
            cur["end"] = s.split()[1]
        elif s.startswith("Path Group:"):
            cur["group"] = s.split(":", 1)[1].strip()
        elif "data arrival time" in s:
            in_data = False
        elif in_data:
            m = PIN_RE.match(ln)
            if m:
                cur["pins"].append((m.group(2), m.group(1), m.group(3)))
        if cur is not None and "slack" in s:
            m = SLACK_RE.search(s)
            if m:
                cur["slack"] = float(m.group(1))
    return out


def inst_of(pin):
    """'u1/u2/Y' -> 'u1/u2' ; a top-level port has no '/' -> ''"""
    return pin.rsplit("/", 1)[0] if "/" in pin else ""


def hpwl(points):
    """half-perimeter wirelength of [(x, y), ...] (um)"""
    pts = list(points)
    if len(pts) < 2:
        return 0.0
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (max(xs) - min(xs)) + (max(ys) - min(ys))


def read_pin_table(text):
    """pins.tsv -> {pin: (x, y, net, net_hpwl, fanout)}; keys also stored without backslash escapes"""
    tab = {}
    for ln in (text or "").splitlines()[1:]:
        f = ln.split("\t")
        if len(f) >= 6:
            row = (float(f[1]), float(f[2]), f[3], float(f[4]), int(float(f[5])))
            tab[f[0]] = row
            tab[f[0].replace("\\", "")] = row
    return tab


def path_rows(paths, pintab, top=50):
    """join parsed paths with the pin table -> rows sorted by slack (worst first), at most `top`:
    rank slack group start end sx sy ex ey n_cells manhattan_um path_wl_um (sum of the HPWL of the distinct nets the path crosses) nets"""
    rows = []
    for p in sorted((p for p in paths if p["slack"] is not None), key=lambda p: p["slack"])[:top]:
        pts, nets, cells = [], {}, []
        for pin, _e, _c in p["pins"]:
            r = pintab.get(pin) or pintab.get(pin.replace("\\", ""))
            if not r:
                continue
            pts.append((r[0], r[1]))
            if r[2] and r[2] != "-":
                nets[r[2]] = r[3]
            i = inst_of(pin)
            if i and (not cells or cells[-1] != i):
                cells.append(i)
        sx, sy = pts[0] if pts else (float("nan"),) * 2
        ex, ey = pts[-1] if pts else (float("nan"),) * 2
        rows.append({"rank": len(rows) + 1, "slack": p["slack"], "group": p["group"], "start": p["start"], "end": p["end"],
                     "sx": sx, "sy": sy, "ex": ex, "ey": ey, "n_cells": len(cells),
                     "manhattan_um": abs(ex - sx) + abs(ey - sy) if pts else float("nan"),
                     "path_wl_um": sum(nets.values()), "nets": len(nets), "pts": pts})
    return rows


PATH_COLS = ["rank", "slack", "group", "start", "end", "sx", "sy", "ex", "ey", "n_cells", "manhattan_um", "path_wl_um", "nets"]


def paths_tsv(rows):
    out = ["\t".join(PATH_COLS)]
    for r in rows:
        out.append("\t".join(f"{r[c]:.3f}" if isinstance(r[c], float) else str(r[c]) for c in PATH_COLS))
    return "\n".join(out) + "\n"


def rudy_grid(nets, die, nx, ny, min_dim=1.0):
    """RUDY (rectangular uniform wire density) estimate.  nets: [(x0, y0, x1, y1)] um; die: (x0, y0, x1, y1).
    Every net spreads (w + h) / (w * h) wire-um per um^2 over its bbox (w, h >= min_dim).  -> grid[j][i] in um of wire per um^2."""
    X0, Y0, X1, Y1 = die
    bw, bh = (X1 - X0) / nx, (Y1 - Y0) / ny
    g = [[0.0] * nx for _ in range(ny)]
    for (a, b, c, d) in nets:
        x0, x1 = min(a, c), max(a, c)
        y0, y1 = min(b, d), max(b, d)
        w, h = max(x1 - x0, min_dim), max(y1 - y0, min_dim)
        if x1 - x0 < w:
            x0 -= (w - (x1 - x0)) / 2; x1 = x0 + w
        if y1 - y0 < h:
            y0 -= (h - (y1 - y0)) / 2; y1 = y0 + h
        dens = (w + h) / (w * h)
        for j in range(max(0, int((y0 - Y0) / bh)), min(ny - 1, int((y1 - Y0) / bh)) + 1):
            oy = min(y1, Y0 + (j + 1) * bh) - max(y0, Y0 + j * bh)
            if oy <= 0:
                continue
            for i in range(max(0, int((x0 - X0) / bw)), min(nx - 1, int((x1 - X0) / bw)) + 1):
                ox = min(x1, X0 + (i + 1) * bw) - max(x0, X0 + i * bw)
                if ox > 0:
                    g[j][i] += dens * ox * oy / (bw * bh)
    return g


def read_nets(text):
    out = []
    for ln in (text or "").splitlines()[1:]:
        f = ln.split("\t")
        if len(f) >= 4:
            out.append((float(f[0]), float(f[1]), float(f[2]), float(f[3])))
    return out


def rects_overlap(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def read_macros(text, default_halo=0.0):
    """macros.tsv -> [{name, master, box, halo_box}]"""
    out = []
    for ln in (text or "").splitlines()[1:]:
        f = ln.split("\t")
        if len(f) < 10:
            continue
        x0, y0, x1, y1 = map(float, f[2:6])
        hl, hb, hr, ht = (float(v) or default_halo for v in f[6:10])
        out.append({"name": f[0], "master": f[1], "box": (x0, y0, x1, y1), "halo_box": (x0 - hl, y0 - hb, x1 + hr, y1 + ht)})
    return out


def read_macro_pins(text):
    return [(f[0], f[1], f[2], tuple(map(float, f[3:7]))) for f in (ln.split("\t") for ln in (text or "").splitlines()[1:]) if len(f) >= 7]


def pg_overlaps(straps, macros, mpins):
    """straps [(net, layer, x0, y0, x1, y1)] vs macros -> (hits, summary).  hit kinds: 'halo' (strap enters a macro's halo ring
    or the macro body without being its own PG connection is not judged here -> only the ring outside the body), 'pin' (strap
    rectangle overlaps a macro signal-pin rect on the same layer)."""
    hits = []
    pin_by_macro = {}
    for m, pin, layer, box in mpins:
        pin_by_macro.setdefault(m, []).append((pin, layer, box))
    for s in straps:
        sb = tuple(s[2:6])
        for m in macros:
            if not rects_overlap(sb, m["halo_box"]):
                continue
            if rects_overlap(sb, m["box"]):
                for pin, layer, box in pin_by_macro.get(m["name"], []):
                    if layer == s[1] and rects_overlap(sb, box):
                        hits.append({"kind": "pin", "macro": m["name"], "pin": pin, "net": s[0], "layer": s[1], "box": sb})
            else:
                hits.append({"kind": "halo", "macro": m["name"], "pin": "", "net": s[0], "layer": s[1], "box": sb})
    return hits, {"straps": len(straps), "macros": len(macros), "macro_pin_rects": len(mpins),
                  "halo_hits": sum(h["kind"] == "halo" for h in hits), "pin_hits": sum(h["kind"] == "pin" for h in hits)}


def heat_color(v):
    """0..1 -> (r, g, b) blue -> cyan -> green -> yellow -> red"""
    v = 0.0 if v != v else min(1.0, max(0.0, v))
    stops = [(0, (30, 40, 140)), (0.25, (30, 160, 220)), (0.5, (60, 190, 90)), (0.75, (240, 220, 40)), (1.0, (220, 30, 30))]
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if v <= b:
            t = (v - a) / (b - a)
            return tuple(int(ca[k] + t * (cb[k] - ca[k])) for k in range(3))
    return stops[-1][1]


def slack_color(rank, n):
    """worst path red, later paths towards blue"""
    return heat_color(1.0 - (rank - 1) / max(1, n - 1))


# ------------------------------------------------------------------------------------------------ drawing (PIL, else SVG)
class Canvas:
    def __init__(self, die, title, maxpx=1600):
        self.die = die
        W, H = die[2] - die[0], die[3] - die[1]
        self.s = maxpx / max(W, H, 1e-9)
        self.w, self.h = int(W * self.s) + 1, int(H * self.s) + 1
        self.title = title
        self.items = []
        self.pil = None
        try:
            from PIL import Image, ImageDraw
            self.pil = (Image.new("RGB", (self.w, self.h + 18), (255, 255, 255)), None)
            self.pil = (self.pil[0], ImageDraw.Draw(self.pil[0]))
        except Exception:
            self.pil = None

    def xy(self, x, y):
        return ((x - self.die[0]) * self.s, self.h - (y - self.die[1]) * self.s + 18)

    def rect(self, b, fill=None, outline=None, width=1):
        a, c = self.xy(b[0], b[3]), self.xy(b[2], b[1])
        self.items.append(("rect", a, c, fill, outline, width))
        if self.pil:
            self.pil[1].rectangle([a[0], a[1], max(a[0], c[0] - 1), max(a[1], c[1] - 1)], fill=fill, outline=outline, width=width)

    def line(self, pts, color, width=1):
        p = [self.xy(x, y) for x, y in pts]
        self.items.append(("line", p, color, width))
        if self.pil and len(p) > 1:
            self.pil[1].line(p, fill=color, width=width)

    def dot(self, x, y, color, r=3):
        a = self.xy(x, y)
        self.items.append(("dot", a, color, r))
        if self.pil:
            self.pil[1].ellipse([a[0] - r, a[1] - r, a[0] + r, a[1] + r], fill=color)

    def text(self, x, y, s, color=(0, 0, 0)):
        a = self.xy(x, y)
        self.items.append(("text", a, color, s))
        if self.pil:
            self.pil[1].text((a[0] + 3, a[1] - 5), s, fill=color)

    def cross(self, x, y, color, r=3):
        a = self.xy(x, y)
        self.items.append(("line", [(a[0] - r, a[1] - r), (a[0] + r, a[1] + r)], color, 1))
        self.items.append(("line", [(a[0] - r, a[1] + r), (a[0] + r, a[1] - r)], color, 1))
        if self.pil:
            self.pil[1].line([a[0] - r, a[1] - r, a[0] + r, a[1] + r], fill=color)
            self.pil[1].line([a[0] - r, a[1] + r, a[0] + r, a[1] - r], fill=color)

    def save(self, path_png):
        """-> path actually written (.png with PIL, else .svg)"""
        if self.pil:
            self.pil[1].text((4, 3), self.title[:200], fill=(0, 0, 0))
            self.pil[0].save(path_png)
            return path_png
        p = str(path_png)[:-4] + ".svg"
        col = lambda c: "none" if c is None else "rgb(%d,%d,%d)" % tuple(c)
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h + 18}"><rect width="100%" height="100%" fill="white"/>',
               f'<text x="4" y="13" font-size="12">{_esc(self.title[:200])}</text>']
        for it in self.items:
            if it[0] == "rect":
                _, a, c, fill, outline, width = it
                out.append(f'<rect x="{a[0]:.1f}" y="{a[1]:.1f}" width="{max(0.5, c[0] - a[0]):.1f}" height="{max(0.5, c[1] - a[1]):.1f}" fill="{col(fill)}" stroke="{col(outline)}" stroke-width="{width}"/>')
            elif it[0] == "line":
                out.append('<polyline fill="none" stroke="%s" stroke-width="%d" points="%s"/>' % (col(it[2]), it[3], " ".join(f"{x:.1f},{y:.1f}" for x, y in it[1])))
            elif it[0] == "text":
                out.append(f'<text x="{it[1][0] + 3:.1f}" y="{it[1][1]:.1f}" font-size="9" fill="{col(it[2])}">{_esc(it[3])}</text>')
            else:
                out.append(f'<circle cx="{it[1][0]:.1f}" cy="{it[1][1]:.1f}" r="{it[3]}" fill="{col(it[2])}"/>')
        out.append("</svg>")
        Path(p).write_text("\n".join(out))
        return p


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


def draw_grid(cv, die, grid, vmax, skip_none=True):
    ny, nx = len(grid), len(grid[0])
    bw, bh = (die[2] - die[0]) / nx, (die[3] - die[1]) / ny
    for j in range(ny):
        for i in range(nx):
            v = grid[j][i]
            if v is None:
                continue
            cv.rect((die[0] + i * bw, die[1] + j * bh, die[0] + (i + 1) * bw, die[1] + (j + 1) * bh), fill=heat_color(v / vmax if vmax else 0))


def draw_macros(cv, macros, fill=(150, 150, 150), outline=(60, 60, 60)):
    for m in macros:
        cv.rect(m["box"], fill=fill, outline=outline)


def percentile(vals, q):
    v = sorted(x for x in vals if x is not None)
    return v[min(len(v) - 1, int(q * len(v)))] if v else 0.0


# ------------------------------------------------------------------------------------------------ products
def _read(p):
    try:
        return Path(p).read_text(errors="replace")
    except OSError:
        return ""


def finish(rev, npath=50):
    """host half: tcl dumps -> products.  Returns summary dict (also written as summary.json)."""
    rev = Path(rev)
    summary = {"review_dir": str(rev), "files": [], "notes": []}
    lay = {}
    try:
        lay = json.loads(_read(rev / "layout.json"))
    except ValueError:
        summary["notes"].append("layout.json missing/unparseable: no pictures")
    die = tuple(lay.get("die") or ())
    halo = float(os.environ.get("PPR_HALO_UM", "0") or 0)  # DB halos are usually unset; PPR_HALO_UM gives a default ring width (um)
    macros = read_macros(_read(rev / "macros.tsv"), halo)
    ttl = lay.get("top") or ""
    # 1. paths
    raw = _read(rev / "paths_ideal_raw.txt")
    if raw:
        (rev / "paths_ideal.txt").write_text(raw)
        rows = path_rows(parse_paths(raw), read_pin_table(_read(rev / "pins.tsv")), npath)
        (rev / "paths_ideal.tsv").write_text(paths_tsv(rows))
        summary["files"] += ["paths_ideal.tsv", "paths_ideal.txt"]
        summary["paths"] = {"n": len(rows), "worst_slack_ps": rows[0]["slack"] if rows else None}
    else:
        rows = []
        summary["notes"].append("no path report: " + (_read(rev / "sta_error.txt").strip() or "STA did not run"))
    if len(die) != 4:
        (rev / "summary.json").write_text(json.dumps(summary, indent=1))
        return summary
    # 2. density + RUDY
    dens = lay.get("density") or {}
    nx, ny = int(dens.get("nx", 0) or 0), int(dens.get("ny", 0) or 0)
    if nx and ny:
        grid = [[(None if v is None else float(v)) for v in dens["grid"][j * nx:(j + 1) * nx]] for j in range(ny)]
        cv = Canvas(die, f"placement density (std-cell area / bin) {ttl}")
        draw_grid(cv, die, grid, 1.0)
        draw_macros(cv, macros)
        summary["files"].append(os.path.basename(cv.save(rev / "density.png")))
    nets = read_nets(_read(rev / "nets.tsv"))
    if nets:
        g = rudy_grid(nets, die, 64, 64)
        flat = [v for r in g for v in r]
        vmax = percentile(flat, 0.995) or 1.0
        cv = Canvas(die, f"RUDY routing demand estimate (placed net bboxes), max colour = p99.5 = {vmax:.3f} um/um2 {ttl}")
        draw_grid(cv, die, g, vmax)
        draw_macros(cv, macros, fill=None, outline=(255, 255, 255))
        summary["files"].append(os.path.basename(cv.save(rev / "rudy.png")))
        summary["rudy"] = {"nets": len(nets), "p99.5": round(vmax, 4), "max": round(max(flat), 4)}
    # 3. flight lines (every one of the top paths labelled with its slack in ps) + DRT violation markers when the kit has a detail-route report
    marks = []
    try:
        kit_dir = json.loads(_read(rev / "review.json") or "{}").get("kit", "")
        drc = find_drt_report(kit_dir) if kit_dir else ""
        if drc:
            marks = read_drt_marks(_read(drc))
            summary["drt_report"] = {"file": drc, "marks": len(marks)}
        else:
            summary["notes"].append("no 5_route_drc report in the kit yet: no DRT markers")
    except (OSError, ValueError):
        pass
    if rows:
        cv = Canvas(die, f"top {len(rows)} setup paths, ideal clock, placement RC (red = worst, label = slack ps)" + (f"; magenta x = {len(marks)} DRT violations" if marks else "") + f" {ttl}")
        draw_macros(cv, macros, fill=(225, 225, 225), outline=(170, 170, 170))
        for x, y, _l, _t in marks:
            cv.cross(x, y, (200, 0, 200), 2)
        for r in reversed(rows):
            col = slack_color(r["rank"], len(rows))
            if len(r["pts"]) > 1:
                cv.line(r["pts"], col, 1)
            if r["pts"]:
                cv.dot(r["sx"], r["sy"], (0, 140, 0), 3)
                cv.dot(r["ex"], r["ey"], (0, 0, 0), 3)
                cv.text(r["ex"], r["ey"], slack_label(r["slack"]), col)
        summary["files"].append(os.path.basename(cv.save(rev / "flight_lines.png")))
    elif marks:
        cv = Canvas(die, f"{len(marks)} DRT violations (magenta x); no path report {ttl}")
        draw_macros(cv, macros, fill=(225, 225, 225), outline=(170, 170, 170))
        for x, y, _l, _t in marks:
            cv.cross(x, y, (200, 0, 200), 2)
        summary["files"].append(os.path.basename(cv.save(rev / "drt_markers.png")))
    # 4. macro halo / pin vs PG strap overlay
    mpins = read_macro_pins(_read(rev / "macro_pins.tsv"))
    straps = [tuple([s[0], s[1]] + [float(v) for v in s[2:6]]) for s in lay.get("pg", [])]
    if macros:
        hits, st = pg_overlaps(straps, macros, mpins)
        cv = Canvas(die, f"macro halo (orange) / pin faces (cyan) vs top-layer PG straps (grey, red = overlap) {ttl}")
        for s in straps:
            cv.rect(tuple(s[2:6]), fill=(190, 190, 190))
        for m in macros:
            cv.rect(m["halo_box"], outline=(255, 140, 0))
            cv.rect(m["box"], fill=(235, 235, 235), outline=(60, 60, 60))
        for _m, _p, _l, b in mpins:
            cv.rect(b, fill=(0, 200, 220))
        for h in hits:
            cv.rect(h["box"], fill=(230, 0, 0) if h["kind"] == "pin" else (255, 90, 90))
        summary["files"].append(os.path.basename(cv.save(rev / "macro_pg_overlay.png")))
        summary["macro_pg"] = st
        if not any(m["halo_box"] != m["box"] for m in macros):
            summary["notes"].append("no macro halo in the DB and PPR_HALO_UM unset: halo overlap not judged")
        if not mpins:
            summary["notes"].append("macro pin rects not available from the DB: only halo overlaps judged")
    (rev / "summary.json").write_text(json.dumps(summary, indent=1))
    return summary


DRT_BBOX = re.compile(r"bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\) on Layer (\S+)")
DRT_TYPE = re.compile(r"^violation type:\s*(.+?)\s*$")


def read_drt_marks(text, limit=30000):
    """OpenROAD -output_drc report text -> [(x, y, layer, type)] (bbox centres, at most `limit`).  Pure."""
    out, cur = [], ""
    for ln in text.splitlines():
        m = DRT_TYPE.match(ln)
        if m:
            cur = m.group(1)
            continue
        b = DRT_BBOX.search(ln)
        if b and len(out) < limit:
            out.append(((float(b.group(1)) + float(b.group(3))) / 2, (float(b.group(2)) + float(b.group(4))) / 2, b.group(5), cur))
    return out


def find_drt_report(kit):
    """newest 5_route_drc.rpt* of the kit (run/reports/*/*/base or gen/*/run/reports/...), '' when none"""
    best = ("", 0.0)
    for g in ("run/reports/*/*/base/5_route_drc.rpt*", "gen/*/run/reports/*/*/base/5_route_drc.rpt*", "reports/*/*/base/5_route_drc.rpt*"):
        for p_ in glob.glob(os.path.join(kit, g)):
            try:
                mt = os.stat(p_).st_mtime
            except OSError:
                continue
            if mt > best[1]:
                best = (p_, mt)
    return best[0]


def slack_label(slack):
    return f"{slack:.0f}"


# ------------------------------------------------------------------------------------------------ launch
def tcl_wrapper(rel):
    """run.tcl: read the DB read-only from the /kit mount, then the review script"""
    return f"read_db /kit/{rel}\nset ::env(PPR_ODB) /kit/{rel}\nsource /rev/tools/post_place_review.tcl\n"


def run_script(kit, rel, rev, image, mem, rid, npath=50):
    q = shlex.quote
    return f"""#!/bin/bash
# post_place_review run script (generated): ORFS image does the OpenROAD half, host python3 the drawing half
set -uo pipefail
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
$DK run --rm --name ppr-{rid}-$$ --cpus 2 --memory {mem}g --memory-swap {mem}g -v {q(kit)}:/kit:ro -v {q(str(rev))}:/rev \\
  -e HUID=$(id -u) -e HGID=$(id -g) -e PPR_OUT=/rev -e PPR_NPATH={npath} -w /rev {q(image)} bash -lc \\
  "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /rev/run.tcl > /rev/tcl.log 2>&1; rc=\\$?; chown -R \\$HUID:\\$HGID /rev; exit \\$rc"
rc=$?
tail -3 {q(str(rev))}/tcl.log
python3 -I {q(str(rev))}/tools/post_place_review.py --finish {q(str(rev))} --npath {npath}
echo "PPR_DONE rc=$rc"
exit $rc
"""


PLACE_FALLBACK = ("3_5_place_dp.odb", "3_place.odb", "3_4_place_resized.odb", "3_3_place_gp.odb")


def resolve_odb(odb):
    """kit flows leave zero-byte intermediate DBs (hard-link/space saving): a 0-byte 3_3_place_gp.odb is replaced by the first
    non-empty placement DB beside it (3_5_place_dp, 3_place, 3_4_place_resized).  -> (path, note); path '' when none is readable."""
    def ok(p):
        try:
            return os.path.getsize(p) > 0
        except OSError:
            return False
    if ok(odb):
        return odb, ""
    d = os.path.dirname(odb)
    for n in PLACE_FALLBACK:
        c = os.path.join(d, n)
        if ok(c):
            return c, f"{os.path.basename(odb)} empty/missing, used {n}"
    return "", f"{os.path.basename(odb)} empty/missing and no fallback placement DB"


def pick_review_dir(kit, rid, out=None):
    cands = [out] if out else [os.path.join(kit, "review"), os.path.expanduser(f"~/.local/state/noprog/review/{rid}")]
    for c in cands:
        try:
            os.makedirs(os.path.join(c, "tools"), exist_ok=True)
            probe = os.path.join(c, ".w")
            Path(probe).write_text("")
            os.unlink(probe)
            return c
        except OSError:
            continue
    return ""


def mem_gb(odb):
    try:
        sz = os.path.getsize(odb)
    except OSError:
        sz = 0
    return min(256, int(max(16, 14 * sz / 2**30 + 8)) + 1)


def launch(kit, odb, image, rid="", out=None, npath=50, mem=None, dry=False, ot_run=None, popen=subprocess.Popen):
    """-> (status, review_dir).  Pure of hub files; the caller appends queue_row() to VIS-QUEUE."""
    kit = os.path.abspath(kit)
    odb = os.path.abspath(odb)
    rid = rid or re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(kit.rstrip("/")))[:40]
    if not odb.startswith(kit + "/"):
        return "odb-not-in-kit", ""
    odb, note = resolve_odb(odb)
    if not odb:
        return "no-odb", ""
    rev = pick_review_dir(kit, rid, out)
    if not rev:
        return "no-writable-dir", ""
    for t in TCL_TOOLS + [Path(__file__).resolve()]:
        if not t.is_file():
            return f"missing-tool-{t.name}", rev
        shutil.copyfile(t, os.path.join(rev, "tools", t.name))
    mem = mem or mem_gb(odb)
    rel = odb[len(kit) + 1:]
    Path(rev, "run.tcl").write_text(tcl_wrapper(rel))
    Path(rev, "run.sh").write_text(run_script(kit, rel, rev, image, mem, rid, npath))
    Path(rev, "review.json").write_text(json.dumps({"id": rid, "kit": kit, "odb": odb, "image": image, "mem_gb": mem, "npath": npath, "t": int(time.time()), "odb_note": note}))
    if dry:
        return "dry-run", rev
    ot_run = ot_run or shutil.which("ot-run") or os.path.expanduser("~/.local/bin/ot-run")
    argv = ["nice", "-n", "10", ot_run, "--direct", "--threads", "2", "--mem", str(mem), "--dir", rev, "--no-spill", "--", "bash", os.path.join(rev, "run.sh")]
    try:
        with open(os.path.join(rev, "ppr.log"), "w") as lg:
            popen(argv, stdout=lg, stderr=subprocess.STDOUT, start_new_session=True, stdin=subprocess.DEVNULL)
    except OSError as e:
        return f"launch-failed: {e}", rev
    return "rendering", rev


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kit")
    ap.add_argument("--odb")
    ap.add_argument("--image")
    ap.add_argument("--id", default="")
    ap.add_argument("--out")
    ap.add_argument("--npath", type=int, default=50)
    ap.add_argument("--mem", type=int)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--finish", metavar="DIR")
    ap.add_argument("--queue-row", nargs=4, metavar=("TYPE", "DIE", "CHECKPOINT", "OWNER"), help="also print the VIS-QUEUE row")
    a = ap.parse_args(argv)
    if a.finish:
        s = finish(a.finish, a.npath)
        print("PPR_FINISH", json.dumps(s))
        return 0
    if not (a.kit and a.odb and a.image):
        ap.error("--kit, --odb and --image are required")
    st, rev = launch(a.kit, a.odb, a.image, a.id, a.out, a.npath, a.mem, a.dry_run)
    print(f"PPR {st} {rev}")
    if a.queue_row:
        ty, die, cp, ow = a.queue_row
        print(queue_row(time.time(), ty, die, cp, os.uname().nodename, rev, st, ow, a.kit))
    return 0 if st in ("rendering", "dry-run") else 1


if __name__ == "__main__":
    sys.exit(main())
