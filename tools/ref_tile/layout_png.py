#!/usr/bin/env python3
"""layout_png.py -- dependency-free PNG layout pictures for tiles, clusters and dies (OWNER RULE 20:45 PT 2026-10-15).

Element owners must LOOK at the layout (Read tool on the PNG) before submitting and after every verdict.  This module
draws, with nothing but the python standard library (the fleet hosts and the ORFS image have no matplotlib):

  floorplan.png    die outline, hard macros / hardened children (filled, named), PG straps of the top PG layer, pins
                   coloured by bus (bus = name without its [index]), clock entry pins as large red markers, the 20 um
                   channel rule visualised (macro-to-macro / macro-to-edge gaps < 20 um hatched in orange)
  density.png      post-place std-cell density heatmap (blue 0 -> red >= 1.0), macros in grey
  congestion.png   global-route congestion hotspots (gcells over capacity, red by overflow) over the floorplan
  die_floorplan.png / die_buses.png   die level: block outlines + names; every inter-block bus drawn as a line whose
                   thickness scales with log2(bit width), coloured by relay stage count (green 0 .. red >= 6)

Inputs are JSON dumps: tools/ref_tile/layout_dump.tcl (OpenROAD, any .odb) or a die plan
({"die": [x0, y0, x1, y1], "blocks": [[name, x0, y0, x1, y1], ...], "buses": [[from, to, bits, stages], ...]}).

    python3 tools/ref_tile/layout_png.py DUMP.json OUTDIR [--congestion RPT] [--title T]
    python3 tools/ref_tile/layout_png.py --die PLAN.json OUTDIR [--title T]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
import zlib
from pathlib import Path

# ------------------------------------------------------------------------------------------------ 5x7 bitmap font
_F = {
    "0": "01110 10001 10011 10101 11001 10001 01110", "1": "00100 01100 00100 00100 00100 00100 01110",
    "2": "01110 10001 00001 00010 00100 01000 11111", "3": "11110 00001 00001 01110 00001 00001 11110",
    "4": "00010 00110 01010 10010 11111 00010 00010", "5": "11111 10000 11110 00001 00001 10001 01110",
    "6": "00110 01000 10000 11110 10001 10001 01110", "7": "11111 00001 00010 00100 01000 01000 01000",
    "8": "01110 10001 10001 01110 10001 10001 01110", "9": "01110 10001 10001 01111 00001 00010 01100",
    "A": "01110 10001 10001 11111 10001 10001 10001", "B": "11110 10001 10001 11110 10001 10001 11110",
    "C": "01110 10001 10000 10000 10000 10001 01110", "D": "11100 10010 10001 10001 10001 10010 11100",
    "E": "11111 10000 10000 11110 10000 10000 11111", "F": "11111 10000 10000 11110 10000 10000 10000",
    "G": "01110 10001 10000 10111 10001 10001 01111", "H": "10001 10001 10001 11111 10001 10001 10001",
    "I": "01110 00100 00100 00100 00100 00100 01110", "J": "00111 00010 00010 00010 00010 10010 01100",
    "K": "10001 10010 10100 11000 10100 10010 10001", "L": "10000 10000 10000 10000 10000 10000 11111",
    "M": "10001 11011 10101 10101 10001 10001 10001", "N": "10001 10001 11001 10101 10011 10001 10001",
    "O": "01110 10001 10001 10001 10001 10001 01110", "P": "11110 10001 10001 11110 10000 10000 10000",
    "Q": "01110 10001 10001 10001 10101 10010 01101", "R": "11110 10001 10001 11110 10100 10010 10001",
    "S": "01111 10000 10000 01110 00001 00001 11110", "T": "11111 00100 00100 00100 00100 00100 00100",
    "U": "10001 10001 10001 10001 10001 10001 01110", "V": "10001 10001 10001 10001 10001 01010 00100",
    "W": "10001 10001 10001 10101 10101 10101 01010", "X": "10001 10001 01010 00100 01010 10001 10001",
    "Y": "10001 10001 01010 00100 00100 00100 00100", "Z": "11111 00001 00010 00100 01000 10000 11111",
    "_": "00000 00000 00000 00000 00000 00000 11111", "-": "00000 00000 00000 11111 00000 00000 00000",
    ".": "00000 00000 00000 00000 00000 01100 01100", "/": "00001 00010 00010 00100 01000 01000 10000",
    ":": "00000 01100 01100 00000 01100 01100 00000", "%": "11001 11010 00010 00100 01000 01011 10011",
    "[": "01110 01000 01000 01000 01000 01000 01110", "]": "01110 00010 00010 00010 00010 00010 01110",
    " ": "00000 00000 00000 00000 00000 00000 00000", "=": "00000 00000 11111 00000 11111 00000 00000",
    "+": "00000 00100 00100 11111 00100 00100 00000", "x": "00000 00000 10001 01010 00100 01010 10001",
    "(": "00010 00100 01000 01000 01000 00100 00010", ")": "01000 00100 00010 00010 00010 00100 01000",
    ",": "00000 00000 00000 00000 00110 00100 01000", ">": "01000 00100 00010 00001 00010 00100 01000",
}
FONT = {k: [int(r, 2) for r in v.split()] for k, v in _F.items()}


class Canvas:
    def __init__(self, w, h, bg=(255, 255, 255)):
        self.w, self.h = int(w), int(h)
        self.px = bytearray(bytes(bg) * (self.w * self.h))

    def _set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = 3 * (y * self.w + x)
            self.px[i:i + 3] = bytes(c)

    def fill(self, x0, y0, x1, y1, c):
        x0, x1 = max(0, int(min(x0, x1))), min(self.w, int(math.ceil(max(x0, x1))))
        y0, y1 = max(0, int(min(y0, y1))), min(self.h, int(math.ceil(max(y0, y1))))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for y in range(y0, y1):
            i = 3 * (y * self.w + x0)
            self.px[i:i + len(row)] = row

    def box(self, x0, y0, x1, y1, c, t=1):
        self.fill(x0, y0, x1, y0 + t, c); self.fill(x0, y1 - t, x1, y1, c)
        self.fill(x0, y0, x0 + t, y1, c); self.fill(x1 - t, y0, x1, y1, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        n = int(max(abs(x1 - x0), abs(y1 - y0), 1))
        r = max(0.5, t / 2)
        for k in range(n + 1):
            x, y = x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n
            self.fill(x - r, y - r, x + r, y + r, c)

    def text(self, x, y, s, c=(0, 0, 0), scale=1):
        for ch in str(s):
            g = FONT.get(ch) or FONT.get(ch.upper()) or FONT[" "]
            for ry, bits in enumerate(g):
                for rx in range(5):
                    if bits >> (4 - rx) & 1:
                        self.fill(x + rx * scale, y + ry * scale, x + (rx + 1) * scale, y + (ry + 1) * scale, c)
            x += 6 * scale

    def save(self, path):
        raw = b"".join(b"\x00" + bytes(self.px[3 * y * self.w:3 * (y + 1) * self.w]) for y in range(self.h))
        def chunk(t, d):
            return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0))
                               + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
        return str(path)


# ------------------------------------------------------------------------------------------------ helpers
def bus_of(pin):
    return re.sub(r"\[\d+\]$", "", re.sub(r"\\", "", pin))


def color_of(key):
    h = zlib.crc32(key.encode()) & 0xFFFFFF
    r, g, b = (h >> 16) & 255, (h >> 8) & 255, h & 255
    m = max(r, g, b) or 1
    return tuple(min(230, int(40 + 190 * v / m)) for v in (r, g, b))


def ramp(v):
    """0 -> blue, 0.5 -> green, 1 -> red, > 1 -> dark red"""
    v = max(0.0, float(v))
    if v >= 1.0:
        return (min(255, int(200 + 55 / v)), 0, 0) if v > 1.0 else (230, 0, 0)
    if v < 0.5:
        k = v / 0.5
        return (0, int(80 + 150 * k), int(230 - 150 * k))
    k = (v - 0.5) / 0.5
    return (int(230 * k), int(230 - 180 * k), 30)


def stage_color(n):
    n = max(0, int(n or 0))
    return [(30, 160, 60), (90, 180, 40), (170, 190, 30), (230, 170, 20), (240, 120, 20), (230, 70, 20)][min(n, 5)] \
        if n < 6 else (200, 0, 0)


class View:
    """um -> pixel, y up, margin for the title / legend"""
    def __init__(self, die, max_px=1400, top=40, side=12):
        self.x0, self.y0, x1, y1 = die
        self.W, self.H = max(1e-6, x1 - self.x0), max(1e-6, y1 - self.y0)
        self.s = (max_px - 2 * side) / max(self.W, self.H)
        self.side, self.top = side, top
        self.cw, self.ch = int(self.W * self.s + 2 * side), int(self.H * self.s + top + side)

    def x(self, v):
        return self.side + (v - self.x0) * self.s

    def y(self, v):
        return self.top + (self.H - (v - self.y0)) * self.s

    def rect(self, r):
        return self.x(r[0]), self.y(r[3]), self.x(r[2]), self.y(r[1])


def _gaps(blocks, die, limit=20.0):
    """macro-macro and macro-edge gaps narrower than limit (um): [(x0, y0, x1, y1)] rectangles of the sliver"""
    out = []
    X0, Y0, X1, Y1 = die
    for i, a in enumerate(blocks):
        ax0, ay0, ax1, ay1 = a
        for e, (g0, g1) in (("w", (X0, ax0)), ("e", (ax1, X1))):
            if 0 < g1 - g0 < limit:
                out.append((g0, ay0, g1, ay1))
        for e, (g0, g1) in (("s", (Y0, ay0)), ("n", (ay1, Y1))):
            if 0 < g1 - g0 < limit:
                out.append((ax0, g0, ax1, g1))
        for b in blocks[i + 1:]:
            bx0, by0, bx1, by1 = b
            if min(ay1, by1) > max(ay0, by0):               # side by side in x
                g0, g1 = (ax1, bx0) if ax1 <= bx0 else (bx1, ax0)
                if 0 < g1 - g0 < limit:
                    out.append((g0, max(ay0, by0), g1, min(ay1, by1)))
            if min(ax1, bx1) > max(ax0, bx0):               # stacked in y
                g0, g1 = (ay1, by0) if ay1 <= by0 else (by1, ay0)
                if 0 < g1 - g0 < limit:
                    out.append((max(ax0, bx0), g0, min(ax1, bx1), g1))
    return out


# ------------------------------------------------------------------------------------------------ tile / cluster
def render_floorplan(d, out, title=""):
    v = View(d["die"])
    c = Canvas(v.cw, v.ch)
    c.box(*v.rect(d["die"]), (0, 0, 0), 2)
    blocks = [b for b in d.get("blocks", [])]
    for g in _gaps([b[2:6] for b in blocks], d["die"]):
        c.fill(*v.rect(g), (255, 200, 120))
    for net, layer, *r in d.get("pg", []):
        c.fill(*v.rect(r), (210, 210, 250) if net.upper().startswith("VDD") else (250, 215, 215))
    for name, master, *r in blocks:
        x0, y0, x1, y1 = v.rect(r)
        c.fill(x0, y0, x1, y1, (150, 150, 165))
        c.box(x0, y0, x1, y1, (40, 40, 60), 2)
        lab = (master or name)[:max(1, int((x1 - x0) / 6) - 1)]
        if x1 - x0 > 30 and y1 - y0 > 10:
            c.text(x0 + 3, y0 + 3, lab, (255, 255, 255))
    clocks = set(d.get("clocks", []))
    buses = {}
    for name, layer, *r in d.get("pins", []):
        b = bus_of(name)
        buses.setdefault(b, 0)
        buses[b] += 1
        x0, y0, x1, y1 = v.rect(r)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if b in clocks or name in clocks:
            c.fill(cx - 7, cy - 7, cx + 7, cy + 7, (230, 0, 0))
            c.box(cx - 9, cy - 9, cx + 9, cy + 9, (0, 0, 0), 2)
        else:
            c.fill(cx - 2, cy - 2, cx + 2, cy + 2, color_of(b))
    st = d.get("stats", {})
    c.text(6, 6, (title or d.get("top", ""))[:110], (0, 0, 0), 2)
    c.text(6, 24, f"{d['die'][2] - d['die'][0]:.1f}x{d['die'][3] - d['die'][1]:.1f} um  blocks {len(blocks)}  pins "
                  f"{sum(buses.values())}  buses {len(buses)}  fill {st.get('fill', '?')}  clock=red  <20um gap=orange",
           (60, 60, 60))
    legend = {b: color_of(b) for b in sorted(buses)}
    return c.save(out), legend


def render_grid(d, key, out, title, scale_note):
    g = d.get(key)
    if not g:
        return None
    v = View(d["die"])
    c = Canvas(v.cw, v.ch)
    nx, ny, vals = g["nx"], g["ny"], g["grid"]
    X0, Y0, X1, Y1 = d["die"]
    bw, bh = (X1 - X0) / nx, (Y1 - Y0) / ny
    for j in range(ny):
        for i in range(nx):
            val = vals[j * nx + i]
            if val is None:
                continue
            c.fill(*v.rect((X0 + i * bw, Y0 + j * bh, X0 + (i + 1) * bw, Y0 + (j + 1) * bh)), ramp(val))
    for name, master, *r in d.get("blocks", []):
        x0, y0, x1, y1 = v.rect(r)
        c.fill(x0, y0, x1, y1, (120, 120, 120))
        c.box(x0, y0, x1, y1, (0, 0, 0), 1)
    c.box(*v.rect(d["die"]), (0, 0, 0), 2)
    c.text(6, 6, title[:110], (0, 0, 0), 2)
    c.text(6, 24, scale_note, (60, 60, 60))
    return c.save(out)


def congestion_grid(d, rpt_text, n=64):
    """bin GRT congestion markers ('bbox = (x0, y0) - (x1, y1)' + 'H/V overflow') into an n x n overflow grid"""
    X0, Y0, X1, Y1 = d["die"]
    nx = ny = n
    grid = [0.0] * (nx * ny)
    hits = 0
    for m in re.finditer(r"\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)\s*-\s*\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)", rpt_text):
        x0, y0, x1, y1 = map(float, m.groups())
        i = min(nx - 1, max(0, int(((x0 + x1) / 2 - X0) / max(1e-9, X1 - X0) * nx)))
        j = min(ny - 1, max(0, int(((y0 + y1) / 2 - Y0) / max(1e-9, Y1 - Y0) * ny)))
        grid[j * nx + i] += 1.0
        hits += 1
    mx = max(grid) or 1.0
    return {"nx": nx, "ny": ny, "grid": [0.25 + 0.75 * v / mx if v else 0.0 for v in grid], "markers": hits}


def render_tile(dump, outdir, rpt=None, title=""):
    d = json.loads(Path(dump).read_text()) if not isinstance(dump, dict) else dump
    outdir = Path(outdir)
    out = {}
    out["floorplan"], legend = render_floorplan(d, outdir / "floorplan.png", title)
    if d.get("density"):
        out["density"] = render_grid(d, "density", outdir / "density.png", f"{title} post-place density",
                                     "std-cell area / bin area: blue 0, green 0.5, red 1.0+ ; grey = macros")
    if rpt:
        t = Path(rpt).read_text(errors="replace") if Path(rpt).exists() else ""
        d["congestion"] = congestion_grid(d, t)
        out["congestion"] = render_grid(d, "congestion", outdir / "congestion.png", f"{title} GRT congestion",
                                        f"{d['congestion']['markers']} congested gcells (red = most); none = clean")
    (outdir / "legend.json").write_text(json.dumps({"bus_colors": {k: "#%02x%02x%02x" % v for k, v in legend.items()},
                                                     "images": out}, indent=1) + "\n")
    return out


# ------------------------------------------------------------------------------------------------ die
def render_die(plan, outdir, title=""):
    p = json.loads(Path(plan).read_text()) if not isinstance(plan, dict) else plan
    outdir = Path(outdir)
    v = View(p["die"], max_px=1800, top=48)
    centers = {}
    imgs = {}
    for kind in ("floorplan", "buses"):
        c = Canvas(v.cw, v.ch)
        c.box(*v.rect(p["die"]), (0, 0, 0), 3)
        for b in p["blocks"]:
            name, r = b[0], b[1:5]
            x0, y0, x1, y1 = v.rect(r)
            centers[name] = ((x0 + x1) / 2, (y0 + y1) / 2)
            c.fill(x0, y0, x1, y1, (225, 228, 238) if kind == "buses" else color_of(name.split("/")[0].rstrip("0123456789_")))
            c.box(x0, y0, x1, y1, (40, 40, 60), 1)
            if kind == "floorplan" and x1 - x0 > 24 and y1 - y0 > 9:
                c.text(x0 + 2, y0 + 2, name[:max(1, int((x1 - x0) / 6) - 1)], (0, 0, 0))
        if kind == "buses":
            for f, t, bits, stages in p.get("buses", []):
                if f in centers and t in centers:
                    w = max(1, int(round(math.log2(max(1, int(bits))))))
                    c.line(*centers[f], *centers[t], stage_color(stages), w)
            c.text(6, 26, "bus line width = log2(bits); colour = relay stages: green 0 .. yellow 2 .. orange 4 .. red 6+",
                   (60, 60, 60))
        else:
            c.text(6, 26, f"{len(p['blocks'])} blocks  {p['die'][2] - p['die'][0]:.0f}x{p['die'][3] - p['die'][1]:.0f} um",
                   (60, 60, 60))
        c.text(6, 6, f"{title} {kind}"[:140], (0, 0, 0), 2)
        imgs[kind] = c.save(outdir / f"die_{kind}.png")
    if p.get("congestion"):
        imgs["congestion"] = render_grid({"die": p["die"], "blocks": [], "congestion": p["congestion"]}, "congestion",
                                         outdir / "die_congestion.png", f"{title} GRT congestion", "overflow per bin")
    return imgs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dump", nargs="?")
    ap.add_argument("outdir")
    ap.add_argument("--congestion")
    ap.add_argument("--die", help="die plan JSON (blocks + buses) instead of a tile dump")
    ap.add_argument("--title", default="")
    a = ap.parse_args(argv)
    imgs = render_die(a.die, a.outdir, a.title) if a.die else render_tile(a.dump, a.outdir, a.congestion, a.title)
    for k, p in imgs.items():
        if p:
            print(f"OT_LAYOUT_PNG {k} {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
