#!/usr/bin/env python3
"""Trial die runs (early full-chip prototype) from a die_plan.json: every partition as an abstract, the die clock tree,
the die global route, die STA on budget stand-ins and die IR -- integration problems found long before G4.

    die_trial.py kit    PLAN.json --out DIR [--views VIEWDIR] [--leaf-um 600] [--rep-um 450] [--coarse-um 0.72]
    die_trial.py report DIR                       # parse grt / clock / psm / sta outputs -> DIR/trial.json
    die_trial.py clock  DIR                       # clock skew post-processing only (DIR/clock/*)

KIT (DIR/):
  abstracts/<module>.lef  partition abstract per TYPE: exact plan outline + every plan pin (buses, ft slots; the same
                          rectangles as the G3 kit io.tcl), interior clock-tap / reset pins on M7, the kit's M7 PG
                          stripes as VDD/VSS pins, OBS M1..M3 over the whole outline (partition logic) and OBS over every
                          planned hard core / ROM macro (type hard_cores[] origin/outline) up to the core view's top
                          layer (parsed from its LEF; M5 when no view).  A closed partition view in VIEWDIR/<type>/
                          <module>.lef replaces the abstract (none exist today for s81 / s81_head).
  grt/                    die global route of every die-level net on the abstracts: the ft slot crossings of every
                          partition instance (one net per bit, slot in pin -> out pin, the route the partition's
                          stations sit on), the reset spine (root -> every arst_n tap).  Capacity = the plan's budget:
                          M4..M7 at type ft_track_frac (default 0.25: the rest is the partition's own logic), M8 / M9
                          at layer_budget.cut_avail (0.6) of the PG-free tracks, die PG stripes and the die clock
                          H-tree (5 tracks per wire: 2W2S NDR + shields) as M8 / M9 obstructions.  M1-M3 get coarse
                          tracks (--coarse-um) so the GRT gcell stays die-sized; they are not routed.
  clock/                  die clock H-tree from the spine root to every partition clock tap (schema.tap_grid + core
                          taps): recursive bisection of the die (longer axis first), empty branches pruned, a branch
                          buffer at every node, repeaters every --rep-um along each leg, a leaf driver per leaf region
                          (<= --leaf-um) driving its taps.  ctree.v + place.tcl + ctree_<corner>.tcl: OpenROAD
                          estimate_parasitics -placement (M8/M9 RC, 2W NDR = R/2) and per-tap / per-node arrival at
                          SS / TT / FF.  `clock` then computes insertion and seam tap-to-tap skew with CPPR (common
                          path to the lowest common tree node removed) and a flat OCV derate on the uncommon path.
  psm/                    die PDN (die.pg.grid on M8 / M9 strapping the abstracts' M7 PG pins) + PDNSim with an
                          estimated per-partition power (set_pdnsim_inst_power) and C4 power bumps on a regular grid
                          outside the die IO windows (die_io.json).
  sta/                    budget stand-ins for die_sta.py (DIE-STA): PARTS/<module>/6_final.v per type = one face
                          flop per pin bit (in: pin -> D, out: QN -> pin; ft: in pin -> station 0, last station -> out
                          pin), each clocked from its nearest plan tap; die top = die_sta.py top (gen_rtl.die_top);
                          spine_<corner>.json = the clock tree's per-tap arrival as source latency offsets.

All runs are read-only diagnostics; nothing is written into the plan.  Heavy steps run in docker (openroad/orfs image)
through ot-run on a 1 TB host: DIR/run_<step>.sh.
"""
import argparse
import json
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import die_sta  # noqa: E402
import gen_rtl  # noqa: E402
import schema as S  # noqa: E402

IMAGE = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:latest")
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
TECH_LEF = f"{PLAT}/lef/asap7_tech_1x_201209.lef"
SC_LEF = f"{PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef"
ROOT = HERE.parent.parent
BUF = "BUFx24_ASAP7_75t_R"
FLOP = "DFFHQNx1_ASAP7_75t_R"
NDR_TRACKS = 5                       # clock wire 2W2S + a shield each side (hbm_arch clock_htree.py)
TAP_LOAD_FF = 3.0                    # partition tap buffer input (ASSUMED: BUFx24 A ~ 2-3 fF)
OCV = (0.03, 0.05)                   # flat clock OCV derates reported (ASSUMED; no project OCV table)
CORNER_LIB = {"SS": "SS", "TT": "TT", "FF": "FF"}
# M8 / M9 setRC (ASAP7 platform setRC.tcl, kohm / fF per um); clock NDR 2W2S: R / 2, C x 1.1 (ASSUMED)
WIRE_R = (8.44765e-3 + 8.89556e-3) / 2 / 2
WIRE_C = (1.03962e-1 + 9.28446e-2) / 2 * 1.1


def sv(s):
    return gen_rtl.sv_id(s)


# --------------------------------------------------------------------------------------------------------- abstracts
_LEF_TOP = {}


def lef_top_layer(path):
    """highest metal layer named in a LEF (pins + OBS); None if the file is missing."""
    p = (ROOT / path) if path and not Path(path).is_absolute() else Path(path or "")
    if not path or not p.is_file():
        return None
    if str(p) not in _LEF_TOP:
        top = 0
        for m in re.finditer(r"LAYER\s+M(\d+)\b", p.read_text(errors="replace")):
            top = max(top, int(m.group(1)))
        _LEF_TOP[str(p)] = f"M{top}" if top else None
    return _LEF_TOP[str(p)]


def core_obs(t):
    """[(x0, y0, x1, y1, top_layer, module, has_view)] of a type's planned hard cores (ROM macros, closed leaves)."""
    out = []
    for h in t.get("hard_cores", []) or []:
        if "origin_um" not in h or "outline_um" not in h:
            continue
        x0, y0 = h["origin_um"]
        w, hh = h["outline_um"]
        if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, hh = hh, w
        view_top = lef_top_layer(h.get("lef"))
        # A declared route ceiling remains an obstruction even when no routed
        # LEF exists. A lower parent/default/abstract may not free those layers.
        claimed = [L for L in (view_top, h.get("obs_max")) if L]
        top = max(claimed, key=lambda L: int(L[1:])) if claimed else "M5"
        out.append((x0, y0, x0 + w, y0 + hh, top, h.get("module", "?"), view_top is not None))
    return out


# ------------------------------------------------------------------------ CLOCK-128-R7: island windows (12.2a / 12.2a1)
# Opt-in (kit --island-sites).  A die clock cell (H-tree node / leg or trunk repeater) on a partition island site is a
# top-owned placement hole + M9->M1 stack (12.2a): the partition abstract must NOT carry solid M1-M3 OBS (nor its M7
# PG stripes) over it.  Windows are plan-computed from the declared site coordinates only (never from a placement):
# site centre +- (cell footprint / 2 + the plan-site snap + margin), snapped OUTWARD to the type's site/row grid,
# transformed into the TYPE frame and united over every instance of the type -> one abstract per type, the SAME
# windows in every instance (12.2a1 type identity).  A window over a planned hard core is NOT opened (the core's
# OBS stays): that site needs an in-core pushdown island (12.2a1), reported as island_in_core.
ISLAND_CELL_UM = (1.62, 0.27)     # BUFx24_ASAP7_75t_R footprint (die_clock_mesh BUF_W x ROW_Y)
ISLAND_SNAP_UM = 0.5              # die_clock_128.SITE_SNAP_UM: plan site -> placed cell
ISLAND_MARGIN_UM = 0.25           # pin stack pads (M2 0.019) + OBS spacing, rounded up
ISLAND_GRID_UM = (0.054, 0.27)    # site width / row height (ASAP7 7.5T)
ISLAND_PG_CUT = ("M7",)           # abstract PG pin layers cut at a window (the pin stack's M7 riser runs there)


def load_island_sites(paths):
    """[(xy, source)] die-frame island sites from: a die_tree_plan.json (lattice.nodes + lattice.gate.
    leg_repeater_sites), an ot_clock_sites/1 file (sites[] of kind partition), or a die_clock_mesh build mesh.json
    (meta.derived_trunk_sites: the root trunk repeaters the plan has not declared yet)."""
    out = []
    for p in paths:
        d = json.loads(Path(p).read_text())
        tag = Path(p).name
        if isinstance(d.get("lattice"), dict):
            for n in d["lattice"].get("nodes", []):
                out.append((tuple(n["xy_um"]), f"{tag}:node:{n.get('tag')}"))
            for k, r in enumerate(d["lattice"].get("gate", {}).get("leg_repeater_sites", [])):
                out.append((tuple(r["xy_um"]), f"{tag}:leg:{r.get('leg')}:{k}"))
        elif d.get("schema") == "ot_clock_sites/1":
            for s in d.get("sites", []):
                if s.get("kind", "partition") == "partition":
                    out.append((tuple(s["xy_um"]), f"{tag}:{s.get('name')}"))
        elif isinstance(d.get("meta"), dict) and "derived_trunk_sites" in d["meta"]:
            for s in d["meta"]["derived_trunk_sites"]:
                out.append((tuple(s["xy_um"]), f"{tag}:trunk:{s.get('cell')}"))
        else:
            raise SystemExit(f"die_trial kit --island-sites: {p}: not a die_tree_plan / ot_clock_sites/1 / mesh.json")
    return out


def _snap_out(v, g, up):
    k = v / g
    return round((math.ceil(k - 1e-6) if up else math.floor(k + 1e-6)) * g, 4)


def island_windows(P, sites, cell=ISLAND_CELL_UM, snap=ISLAND_SNAP_UM, margin=ISLAND_MARGIN_UM, grid=ISLAND_GRID_UM):
    """{type: [type-frame rect]} (union over instances, deduplicated) + per-site record list"""
    hx = cell[0] / 2 + snap + margin
    hy = cell[1] + snap + margin          # the cell row may lie above or below the site's row line
    rects = {n: P.rect(n) for n in P.parts}
    by_type, recs = defaultdict(set), []
    for (x, y), src in sites:
        w = (x - hx, y - hy, x + hx, y + hy)
        hit = []
        for n, r in rects.items():
            a, b, c, d = max(w[0], r[0]), max(w[1], r[1]), min(w[2], r[2]), min(w[3], r[3])
            if c <= a + 1e-9 or d <= b + 1e-9:
                continue
            tn = P.parts[n]["type"]
            tw, th = P.types[tn]["outline_um"]
            (u0, v0), (u1, v1) = P.to_type(n, (a, b)), P.to_type(n, (c, d))
            u0, u1 = sorted((u0, u1))
            v0, v1 = sorted((v0, v1))
            tr = (max(0.0, _snap_out(u0, grid[0], False)), max(0.0, _snap_out(v0, grid[1], False)),
                  min(tw, _snap_out(u1, grid[0], True)), min(th, _snap_out(v1, grid[1], True)))
            core = [m for (x0, y0, x1, y1, _, m, _) in core_obs(P.types[tn])
                    if x0 < tr[2] and x1 > tr[0] and y0 < tr[3] and y1 > tr[1]]
            hit.append(dict(part=n, type=tn, rect=list(tr), in_core=core))
            if not core:
                by_type[tn].add(tr)
        recs.append(dict(source=src, xy_um=[x, y], parts=hit))
    return {k: sorted(v) for k, v in by_type.items()}, recs


def rect_minus(W, H, holes):
    """[(x0, y0, x1, y1)] covering (0, 0, W, H) minus the union of holes: horizontal bands between hole edges,
    vertically merged where the free x-intervals repeat"""
    ys = sorted({0.0, float(H)} | {min(max(v, 0.0), H) for h in holes for v in (h[1], h[3])})
    bands = []
    for ya, yb in zip(ys, ys[1:]):
        if yb - ya < 1e-9:
            continue
        cov = sorted((h[0], h[2]) for h in holes if h[1] < yb - 1e-9 and h[3] > ya + 1e-9)
        free, cur = [], 0.0
        for a, b in cov:
            if a > cur + 1e-9:
                free.append((cur, min(a, W)))
            cur = max(cur, b)
        if cur < W - 1e-9:
            free.append((cur, float(W)))
        bands.append((ya, yb, tuple(free)))
    out, prev = [], None
    for ya, yb, fr in bands:
        if prev is not None and prev[2] == fr and abs(prev[1] - ya) < 1e-9:
            prev = (prev[0], yb, fr)
            continue
        if prev is not None:
            out += [(a, prev[0], b, prev[1]) for a, b in prev[2]]
        prev = (ya, yb, fr)
    if prev is not None:
        out += [(a, prev[0], b, prev[1]) for a, b in prev[2]]
    return out


def _cut_vertical(rect, holes):
    """split a vertical PG stripe rect (layer of preferred direction y) around the holes it crosses"""
    x0, y0, x1, y1 = rect
    cuts = sorted((h[1], h[3]) for h in holes if h[0] < x1 and h[2] > x0 and h[1] < y1 and h[3] > y0)
    out, cur = [], y0
    for a, b in cuts:
        if a > cur + 1e-9:
            out.append((x0, cur, x1, a))
        cur = max(cur, b)
    if cur < y1 - 1e-9:
        out.append((x0, cur, x1, y1))
    return out


def abstract_lef(P, tn, slots_only_pins=False, islands=None):
    """partition abstract (see module doc).  Returns (lef text, stats).  islands (CLOCK-128-R7, opt-in): type-frame
    island windows: no M1-M3 OBS and no ISLAND_PG_CUT PG stripe inside them."""
    t = P.types[tn]
    w, h = t["outline_um"]
    top = P.layer_budget["partition_signal_max"]
    L = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {t['module']}", "  CLASS BLOCK ;",
         "  ORIGIN 0 0 ;", f"  SIZE {w:.4f} BY {h:.4f} ;"]

    def pin(name, d, use, rects):
        out = [f"  PIN {name}", f"    DIRECTION {d} ;", f"    USE {use} ;", "    PORT"]
        for ln, x0, y0, x1, y1 in rects:
            out += [f"      LAYER {ln} ;", f"        RECT {x0:.4f} {y0:.4f} {x1:.4f} {y1:.4f} ;"]
        return out + ["    END", f"  END {name}"]
    dirs = {}
    for b in t.get("buses", []):
        dirs[b["name"]] = "INPUT" if b["dir"] == "in" else "OUTPUT"
    for sl in t.get("ft_slots", []):
        dirs[sl["name"] + "_i"], dirs[sl["name"] + "_o"] = "INPUT", "OUTPUT"
    npins = 0
    for bus, bit, ln, x, y, f in sorted(gen_phys.type_pins(P, tn), key=lambda p: (p[0], p[1])):
        lw = gen_phys.LAYER_W.get(ln, 0.04) / 2
        pl = gen_phys.PIN_LEN_UM
        r = {"E": (x - pl, y - lw, x, y + lw), "W": (x, y - lw, x + pl, y + lw),
             "N": (x - lw, y - pl, x + lw, y), "S": (x - lw, y, x + lw, y + pl)}[f]
        L += pin(f"{bus}[{bit}]", dirs.get(bus, "INPUT"), "SIGNAL", [(ln, *r)])
        npins += 1
    tw = gen_phys.LAYER_W.get(top, 0.032) / 2
    for name, x, y in gen_phys.tap_pins(P, tn):
        L += pin(name, "INPUT", "SIGNAL" if name == "arst_n" else "CLOCK",
                 [(top, x - tw, y - 2 * gen_phys.PIN_LEN_UM, x + tw, y + 2 * gen_phys.PIN_LEN_UM)])
    # PG: the kit's M7 stripes only (gen_phys.PDN: width 0.288, VSS one width + spacing 0.096 after VDD, pitch 8.64)
    for net, j in (("VDD", 0), ("VSS", 1)):
        rects = []
        c = 4.128 + j * (0.288 + 0.096)
        while c + 0.144 < w:
            rects.append(("M7", c - 0.144, 0.0, c + 0.144, h))
            c += 8.64
        if islands and "M7" in ISLAND_PG_CUT:
            rects = [("M7", *r) for _, *q in rects for r in _cut_vertical(tuple(q), islands)]
        L += pin(net, "INOUT", "POWER" if net == "VDD" else "GROUND", rects)
    cores = core_obs(t)
    if islands:
        free = rect_minus(w, h, islands)
        L += ["  OBS"]
        for i in (1, 2, 3):
            L.append(f"    LAYER M{i} ;")
            L += [f"      RECT {a:.4f} {b:.4f} {c:.4f} {d:.4f} ;" for a, b, c, d in free]
    else:
        L += ["  OBS"] + [f"    LAYER M{i} ;\n      RECT 0 0 {w:.4f} {h:.4f} ;" for i in (1, 2, 3)]
    by_layer = defaultdict(list)
    for x0, y0, x1, y1, tl, _, _ in cores:
        for i in range(4, min(int(tl[1:]), int(top[1:])) + 1):
            by_layer[i].append((x0, y0, x1, y1))
    for i in sorted(by_layer):
        L.append(f"    LAYER M{i} ;")
        L += [f"      RECT {a:.4f} {b:.4f} {c:.4f} {d:.4f} ;" for a, b, c, d in by_layer[i]]
    L += ["  END", f"END {t['module']}", "END LIBRARY", ""]
    st = dict(pins=npins, cores=len(cores), cores_with_view=sum(1 for c in cores if c[6]),
              core_area_um2=round(sum((c[2] - c[0]) * (c[3] - c[1]) for c in cores), 1),
              core_top_layers=sorted({c[4] for c in cores}))
    if islands:
        st["island_windows"] = len(islands)
    return "\n".join(L), st


# ------------------------------------------------------------------------------------------------------- clock tree
def clock_taps(P):
    """[(part, port, x_die, y_die)] every partition clock tap (R4 grid + early core taps), snapped as the kit."""
    out = []
    for n, p in sorted(P.parts.items()):
        tn = p["type"]
        for port, x, y in gen_phys.clock_pins(P, tn) + gen_phys.core_tap_pins(P, tn):
            X, Y = P.to_die(n, (x, y))
            out.append((n, port, round(X, 3), round(Y, 3)))
    return out



# ------------------------------------------------------------------------------------- tree cell site legality (opt-in)
class SiteMap:
    """Legal sites for die clock-tree cells (FALLBACK-HEAD 10-26, 12.2a1): inside a partition, never inside a planned
    hard-core outline (+halo) and never inside a reserved PHY power domain (die.pg.domains with VDDPHY).  Geometry only:
    moves a requested point to the nearest legal channel point; no timing value is used."""
    def __init__(self, P, halo=2.16, bucket=250.0):
        self.W, self.H, self.b = P.W, P.H, bucket
        self.parts = []
        self.forb = []
        for n, p in P.parts.items():
            t = P.types[p["type"]]
            w, h = t["outline_um"]
            ox, oy = p["origin_um"]
            self.parts.append((ox, oy, ox + w, oy + h))
            for x0, y0, x1, y1, *_ in core_obs(t):
                a, b = P.to_die(n, (x0, y0)), P.to_die(n, (x1, y1))
                self.forb.append((min(a[0], b[0]) - halo, min(a[1], b[1]) - halo,
                                  max(a[0], b[0]) + halo, max(a[1], b[1]) + halo, "core"))
        for d in P.die.get("pg", {}).get("domains", []) or []:
            if any("PHY" in str(v) for v in d.get("nets", [])) and d.get("rect_um"):
                x0, y0, x1, y1 = d["rect_um"]
                self.forb.append((x0 - halo, y0 - halo, x1 + halo, y1 + halo, "phy"))
        self.idx = {}
        for k, r in enumerate(self.forb):
            for i in range(int(r[0] // bucket), int(r[2] // bucket) + 1):
                for j in range(int(r[1] // bucket), int(r[3] // bucket) + 1):
                    self.idx.setdefault((i, j), []).append(k)

    def hits(self, q):
        return [self.forb[k] for k in self.idx.get((int(q[0] // self.b), int(q[1] // self.b)), ())
                if self.forb[k][0] < q[0] < self.forb[k][2] and self.forb[k][1] < q[1] < self.forb[k][3]]

    def in_part(self, q, m=0.5):
        return any(r[0] + m <= q[0] <= r[2] - m and r[1] + m <= q[1] <= r[3] - m for r in self.parts)

    def why(self, q):
        h = self.hits(q)
        return h[0][4] if h else (None if self.in_part(q) else "outside")

    def legal(self, q):
        return self.why(q) is None

    def nearest(self, p, axis=None):
        """nearest legal point; axis 'x'/'y' = prefer sliding along that leg axis (perpendicular moves cost 3x)."""
        p = (float(p[0]), float(p[1]))
        if self.legal(p):
            return p
        def cost(q):
            dx, dy = abs(q[0] - p[0]), abs(q[1] - p[1])
            return dx + dy + (2 * dy if axis == "x" else 2 * dx if axis == "y" else 0)
        e = 0.6
        front, seen, best = [p], set(), []
        for _ in range(6):
            nxt = []
            for q in front:
                cands = []
                for r in self.hits(q):
                    cands += [(r[0] - e, q[1]), (r[2] + e, q[1]), (q[0], r[1] - e), (q[0], r[3] + e)]
                if not self.hits(q) and not self.in_part(q):
                    for r in self.parts:
                        cands.append((min(max(q[0], r[0] + 1.0), r[2] - 1.0), min(max(q[1], r[1] + 1.0), r[3] - 1.0)))
                    cands.sort(key=lambda c: abs(c[0] - q[0]) + abs(c[1] - q[1]))
                    cands = cands[:3]
                for c in cands:
                    c = (round(min(max(c[0], 0.0), self.W), 3), round(min(max(c[1], 0.0), self.H), 3))
                    if c in seen:
                        continue
                    seen.add(c)
                    (best if self.legal(c) else nxt).append(c)
            if best:
                return min(best, key=cost)
            front = sorted(nxt, key=cost)[:40]
        raise ValueError(f"no legal clock-tree site near {p}")

    def slide(self, p, toward, step=0.54):
        """first legal point on the straight/L Manhattan leg from p back toward `toward` (the parent's ideal point):
        a buffer moved along its own incoming leg keeps every root->descendant Manhattan length unchanged."""
        p = (float(p[0]), float(p[1]))
        if self.legal(p):
            return p
        pts = [p, (toward[0], p[1]), (toward[0], toward[1])] if abs(p[1] - toward[1]) > 1e-6 and abs(p[0] - toward[0]) > 1e-6 \
            else [p, (toward[0], toward[1])]
        for a, b in zip(pts, pts[1:]):
            L = abs(b[0] - a[0]) + abs(b[1] - a[1])
            n = int(L / step)
            for k in range(1, n + 1):
                f = k / n
                q = (round(a[0] + (b[0] - a[0]) * f, 3), round(a[1] + (b[1] - a[1]) * f, 3))
                if self.legal(q):
                    return q
        return None


def build_htree(P, taps, leaf_um=600.0, full_depth=False, regions=None):
    """explicit H-tree: nodes {id: dict(x, y, parent, level, kids, taps)} rooted at the spine root.  Region bisection
    along the longer axis at the region midpoint; the child node sits at the child region centre (the leg runs along
    the split axis, so every node-to-node leg is a straight M8 (H) or M9 (V) run).  The first leg goes from the spine
    root to the first child centre (root need not be the centre).  Regions without taps are pruned.
    full_depth (opt-in, FALLBACK-HEAD 10-26): keep bisecting a single-tap region down to leaf_um, so every leaf sits at
    the same depth (equal-length H-tree by construction) and the leaf->tap leg is <= ~leaf_um (default unchanged)."""
    W, H = P.W, P.H
    root = P.clock.get("spine", {}).get("root_um") or [W / 2, H / 2]
    nodes = {}
    fd_now = [full_depth]

    def mk(x, y, parent, level, region):
        i = len(nodes)
        nodes[i] = dict(id=i, x=round(x, 3), y=round(y, 3), parent=parent, level=level, kids=[], taps=[],
                        region=[round(v, 3) for v in region])
        if parent is not None:
            nodes[parent]["kids"].append(i)
        return i

    def rec(nid, region, tlist):
        x0, y0, x1, y1 = region
        if max(x1 - x0, y1 - y0) <= leaf_um or (len(tlist) <= 1 and not fd_now[0]):
            nodes[nid]["taps"] = tlist
            return
        if x1 - x0 >= y1 - y0:
            xm = (x0 + x1) / 2
            halves = [((x0, y0, xm, y1), [t for t in tlist if t[2] < xm]), ((xm, y0, x1, y1), [t for t in tlist if t[2] >= xm])]
        else:
            ym = (y0 + y1) / 2
            halves = [((x0, y0, x1, ym), [t for t in tlist if t[3] < ym]), ((x0, ym, x1, y1), [t for t in tlist if t[3] >= ym])]
        for reg, tl in halves:
            if not tl:
                continue
            cx, cy = (reg[0] + reg[2]) / 2, (reg[1] + reg[3]) / 2
            px, py = nodes[nid]["x"], nodes[nid]["y"]
            # keep legs straight: move along the split axis only (the other coordinate is shared by construction,
            # except below the off-centre spine root, where an L-leg via a corner node is used)
            if abs(px - cx) > 1e-6 and abs(py - cy) > 1e-6:
                mid = mk(cx, py, nid, nodes[nid]["level"] + 1, reg)
                nodes[mid]["corner"] = True
                c = mk(cx, cy, mid, nodes[nid]["level"] + 1, reg)
            else:
                c = mk(cx, cy, nid, nodes[nid]["level"] + 1, reg)
            rec(c, reg, tl)
    r = mk(root[0], root[1], None, 0, (0, 0, W, H))
    if not regions:
        rec(r, (0.0, 0.0, W, H), list(taps))
        return nodes
    # FALLBACK-S81-2 10-26 (opt-in --region-trees): landed-region fallback clock.  A die reference tree (same
    # bisection) reaches one ROOT per clock region (region bbox centre); below it an equal-depth local tree
    # (full-depth bisection of the region bbox, leaf_um) feeds that region's partition entries.  Same-region pairs share
    # the region root; every cross-region port is a landed crossing (|d| <= P/2 window), so the reference tree needs no
    # balance.  No pads, trims or post-measurement values.
    rt = defaultdict(list)
    for t in taps:
        rt[regions[t[0]]].append(t)
    box = {}
    for rn, tl in rt.items():
        rs = [(P.parts[n]["origin_um"][0], P.parts[n]["origin_um"][1],
               P.parts[n]["origin_um"][0] + P.types[P.parts[n]["type"]]["outline_um"][0],
               P.parts[n]["origin_um"][1] + P.types[P.parts[n]["type"]]["outline_um"][1]) for n in {t[0] for t in tl}]
        box[rn] = (min(a[0] for a in rs), min(a[1] for a in rs), max(a[2] for a in rs), max(a[3] for a in rs))
    pseudo = [(rn, "__region_root__", (b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for rn, b in sorted(box.items())]
    rec(r, (0.0, 0.0, W, H), pseudo)
    for nid in [i for i, nd in nodes.items() if nd["taps"] and nd["taps"][0][1] == "__region_root__"]:
        ps, nodes[nid]["taps"] = nodes[nid]["taps"], []
        for rn, _, cx, cy in ps:
            px, py = nodes[nid]["x"], nodes[nid]["y"]
            lv = nodes[nid]["level"] + 1
            if abs(px - cx) > 1e-6 and abs(py - cy) > 1e-6:
                mid = mk(cx, py, nid, lv, box[rn])
                nodes[mid]["corner"] = True
                c = mk(cx, cy, mid, lv, box[rn])
            else:
                c = mk(cx, cy, nid, lv, box[rn])
            nodes[c]["region_root"] = rn
            fd_now[0] = True
            rec(c, box[rn], rt[rn])
            fd_now[0] = full_depth
    return nodes


def legal_repeater_chain(a, b, site, reach):
    """Shortest Manhattan-wire chain of legal repeater anchors, every hop <= reach.

    Siting a nominal repeater off a macro changes its two wire lengths. Recompute
    those actual legs before emitting the tree; this is reach repair, not clock
    delay balancing. Wires may cross a macro on the top metals, cells may not.
    """
    import heapq
    dist=lambda p,q:abs(p[0]-q[0])+abs(p[1]-q[1])
    if dist(a,b)<=reach+1e-6:return []
    pts={tuple(a),tuple(b)}
    n=math.ceil(dist(a,b)/(reach/2))
    for i in range(1,n):
        q=(a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n)
        for axis in (None,"x","y"):
            pts.add(tuple(site.nearest(q,axis)))
    lo=(min(a[0],b[0])-reach,min(a[1],b[1])-reach)
    hi=(max(a[0],b[0])+reach,max(a[1],b[1])+reach)
    ids=set()
    for ix in range(int(lo[0]//site.b),int(hi[0]//site.b)+1):
        for iy in range(int(lo[1]//site.b),int(hi[1]//site.b)+1):
            ids.update(site.idx.get((ix,iy),[]))
    for k in ids:
        x0,y0,x1,y1,*_=site.forb[k]
        x0-=.6;y0-=.6;x1+=.6;y1+=.6
        for p,q in [((x0,y0),(x1,y0)),((x0,y1),(x1,y1)),((x0,y0),(x0,y1)),((x1,y0),(x1,y1))]:
            m=max(1,math.ceil(dist(p,q)/(reach/2)))
            for i in range(m+1):
                v=(round(p[0]+(q[0]-p[0])*i/m,3),round(p[1]+(q[1]-p[1])*i/m,3))
                if lo[0]<=v[0]<=hi[0] and lo[1]<=v[1]<=hi[1] and site.legal(v):pts.add(v)
    pts=sorted(pts);src=pts.index(tuple(a));dst=pts.index(tuple(b))
    best={src:(0.,0)};prev={};heap=[(0.,0,src)]
    while heap:
        length,count,i=heapq.heappop(heap)
        if best[i]!=(length,count):continue
        if i==dst:
            path=[]
            while i!=src:path.append(pts[i]);i=prev[i]
            return list(reversed(path))[0:-1]
        for j,p in enumerate(pts):
            hop=dist(pts[i],p)
            if not 1e-6<hop<=reach+1e-6:continue
            score=(length+hop,count+1)
            if score<best.get(j,(math.inf,math.inf)):
                best[j]=score;prev[j]=i;heapq.heappush(heap,(*score,j))
    raise ValueError(f"no legal repeater corridor from {a} to {b} at {reach}um reach")


def tree_netlist(nodes, taps, rep_um=450.0, site=None, tap_rep_um=None):
    """buffered tree: a BUF at every node (branch / leaf driver), repeaters every rep_um along each leg.
    -> (verilog, placements [(inst, x, y)], tap ports [(port, x, y)], node_buf {node id: inst}, path {tap port: [inst]})"""
    cells, place, wires = [], [], []
    node_buf, parent_of = {}, {}
    k = 0

    def net(i):
        return f"n{i}"
    # node buffers
    for i, nd in nodes.items():
        node_buf[i] = f"b{i}"
    for i, nd in sorted(nodes.items()):
        if nd["parent"] is None:
            src = "root"
        else:
            p = nodes[nd["parent"]]
            L = abs(p["x"] - nd["x"]) + abs(p["y"] - nd["y"])
            nrep = max(0, int(math.ceil(L / rep_um)) - 1)
            src = f"{net(nd['parent'])}"
            prev_inst = node_buf[nd["parent"]]
            anchors=[]
            for j in range(nrep):
                f = (j + 1) / (nrep + 1)
                x = p["x"] + (nd["x"] - p["x"]) * f
                y = p["y"] + (nd["y"] - p["y"]) * f
                if site is not None:
                    x, y = site.nearest((x, y), "x" if abs(nd["x"] - p["x"]) >= abs(nd["y"] - p["y"]) else "y")
                anchors.append((x,y))
            if tap_rep_um is not None and site is not None:
                points=[(p["x"],p["y"])]+anchors+[(nd["x"],nd["y"])]
                if any(abs(a[0]-b[0])+abs(a[1]-b[1])>tap_rep_um+1e-6 for a,b in zip(points,points[1:])):
                    anchors=legal_repeater_chain(points[0],points[-1],site,tap_rep_um)
            for j,(x,y) in enumerate(anchors):
                inst = f"r{i}_{j}"
                o = f"rn{i}_{j}"
                cells.append(f"  {BUF} {inst} (.A({src}), .Y({o}));")
                wires.append(o)
                place.append((inst, x, y))
                parent_of[inst] = prev_inst
                prev_inst = inst
                src = o
            parent_of[node_buf[i]] = prev_inst
        cells.append(f"  {BUF} {node_buf[i]} (.A({src}), .Y({net(i)}));")
        wires.append(net(i))
        place.append((node_buf[i], nd["x"], nd["y"]))
    tap_ports = []
    for i, nd in sorted(nodes.items()):
        for ti, (part, port, x, y) in enumerate(nd["taps"]):
            tp = f"t_{sv(part)}__{port}"
            tap_ports.append((tp, x, y, part, port, i))
            src = net(i)
            if tap_rep_um is not None:
                if tap_rep_um <= 0:
                    raise ValueError("tap repeater reach must be positive")
                px, py = nd["x"], nd["y"]
                length = abs(x-px) + abs(y-py)
                count = max(0, math.ceil(length / tap_rep_um)-1)
                prev = node_buf[i]
                for j in range(count):
                    # Follow the actual M8-horizontal/M9-vertical L path.
                    d = length * (j+1)/(count+1)
                    dx = min(d, abs(x-nd["x"]))
                    dy = d-dx
                    qx = nd["x"] + math.copysign(dx, x-nd["x"])
                    qy = nd["y"] + math.copysign(dy, y-nd["y"])
                    if site is not None:
                        qx, qy = site.nearest((qx, qy))
                    hop = abs(qx-px)+abs(qy-py)
                    if hop > tap_rep_um + 1e-6:
                        raise ValueError(f"no legal tap-repeater sequence for {part}.{port}: hop {hop:.3f} > {tap_rep_um}")
                    inst, outnet = f"rtap{i}_{ti}_{j}", f"rtn{i}_{ti}_{j}"
                    cells.append(f"  {BUF} {inst} (.A({src}), .Y({outnet}));")
                    wires.append(outnet)
                    place.append((inst, qx, qy))
                    parent_of[inst] = prev
                    src, prev, px, py = outnet, inst, qx, qy
                hop = abs(x-px)+abs(y-py)
                if hop > tap_rep_um + 1e-6:
                    nearest = site.nearest((x,y)) if site is not None else (x,y)
                    gap = abs(x-nearest[0])+abs(y-nearest[1])
                    raise ValueError(f"no legal last tap hop for {part}.{port}: {hop:.3f} > {tap_rep_um}; "
                                     f"last_cell={(px,py)}, tap={(x,y)}, nearest_legal={nearest}, "
                                     f"nearest_tap_gap={gap:.3f}")
            cells.append(f"  assign {tp} = {src};")
    if len({name for name,*_ in place}) != len(place):
        raise ValueError("clock tree contains duplicate instance names")
    v = ["module ctree (root, " + ", ".join(t[0] for t in tap_ports) + ");", "  input root;"]
    v += [f"  output {t[0]};" for t in tap_ports]
    v += [f"  wire {w};" for w in wires]
    v += [c for c in cells if not c.lstrip().startswith("assign")]
    v += [c for c in cells if c.lstrip().startswith("assign")]
    v.append("endmodule")
    return "\n".join(v) + "\n", place, tap_ports, node_buf, parent_of


def clock_kit(P, out, leaf_um, rep_um, full_depth=False, site_legal=False, site_slide=False, regions=None,
              tap_rep_um=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    taps = clock_taps(P)
    nodes = build_htree(P, taps, leaf_um, full_depth, regions)
    site = None
    slid_fallback = 0
    if site_slide:          # opt-in: slide each buffer back along its OWN incoming leg (equal length by construction)
        site = SiteMap(P)
        for nd in nodes.values():
            nd["req_xy"] = [nd["x"], nd["y"]]
        for nd in nodes.values():
            if nd["parent"] is None:
                q = site.nearest((nd["x"], nd["y"]))
            else:
                par = nodes[nd["parent"]]["req_xy"]
                q = site.slide(nd["req_xy"], par)
                # one downstream path (single kid, or a leaf with one entry): sliding forward along that leg keeps the
                # length too; take the nearer of the two legal slides
                fwd = (nodes[nd["kids"][0]]["req_xy"] if len(nd["kids"]) == 1 and not nd["taps"] else
                       nd["taps"][0][2:4] if not nd["kids"] and len(nd["taps"]) == 1 else None)
                qf = site.slide(nd["req_xy"], fwd) if fwd is not None else None
                dist = lambda c: abs(c[0] - nd["req_xy"][0]) + abs(c[1] - nd["req_xy"][1])
                if qf is not None and (q is None or dist(qf) < dist(q)):
                    q = qf
                if q is None:
                    slid_fallback += 1
                    q = site.nearest(tuple(nd["req_xy"]))
            nd["x"], nd["y"] = round(q[0], 3), round(q[1], 3)
    elif site_legal:          # opt-in: every buffer/repeater on a legal channel site; a one-entry leaf drives AT its entry
        site = SiteMap(P)
        for nd in nodes.values():
            nd["req_xy"] = [nd["x"], nd["y"]]
            if len(nd["taps"]) == 1 and site.legal(nd["taps"][0][2:4]):
                q = nd["taps"][0][2:4]
            else:
                q = site.nearest((nd["x"], nd["y"]))
            nd["x"], nd["y"] = round(q[0], 3), round(q[1], 3)
    v, place, tap_ports, node_buf, parent_of = tree_netlist(nodes, taps, rep_um, site, tap_rep_um)
    (out / "ctree.v").write_text(v)
    segs = []
    for i, nd in nodes.items():
        if nd["parent"] is not None:
            p = nodes[nd["parent"]]
            segs.append((p["x"], p["y"], nd["x"], nd["y"], nd["level"]))
    # leaf -> tap last-mile legs (L: horizontal on M8, then vertical on M9)
    leaf_legs = []
    for tp, x, y, part, port, i in tap_ports:
        nd = nodes[i]
        leaf_legs.append((nd["x"], nd["y"], x, y))
    if tap_rep_um is not None:
        # In strict reach mode anchors may follow a legal channel around a
        # macro. Capacity reservations/rendering must cover the emitted wires,
        # not the pre-siting straight node legs.
        xy={name:(x,y) for name,x,y in place}
        segs=[]
        for child,parent in parent_of.items():
            if parent not in xy:continue
            a,b=xy[parent],xy[child]
            segs.append((*a,*b,0))
        leaf_legs=[];indices=defaultdict(int);last_driver={}
        for name in xy:
            if name.startswith("rtap"):
                ni,ti,j=map(int,name[4:].split("_"));key=(ni,ti)
                if key not in last_driver or j>last_driver[key][0]:last_driver[key]=(j,name)
        for tp,x,y,part,port,i in tap_ports:
            ti=indices[i];indices[i]+=1
            driver=last_driver[(i,ti)][1] if (i,ti) in last_driver else node_buf[i]
            leaf_legs.append((*xy[driver],x,y))
    tcl = [f"read_lef {TECH_LEF}", f"read_lef {SC_LEF}",
           "foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }",
           "read_verilog /work/clock/ctree.v", "link_design ctree",
           f"initialize_floorplan -die_area {{0 0 {gen_phys._um(P.W)} {gen_phys._um(P.H)}}} -core_area {{0 0 {gen_phys._um(P.W)} {gen_phys._um(P.H)}}} -site asap7sc7p5t",
           "source /work/clock/make_tracks.tcl"]
    sz9 = "{0.04 0.32}"
    root = nodes[0]
    tcl.append(f"place_pin -pin_name root -layer M9 -location {{{root['x']:.3f} {root['y']:.3f}}} -pin_size {sz9}")
    for tp, x, y, *_ in tap_ports:
        tcl.append(f"place_pin -pin_name {tp} -layer M9 -location {{{x:.3f} {y:.3f}}} -pin_size {sz9}")
    for inst, x, y in place:
        tcl.append(f"place_inst -name {inst} -location {{{max(0.0, x):.3f} {max(0.0, y):.3f}}} -status PLACED")
    tcl += [f"set_wire_rc -signal -resistance {WIRE_R:.6e} -capacitance {WIRE_C:.6e}",
            f"set_wire_rc -clock -resistance {WIRE_R:.6e} -capacitance {WIRE_C:.6e}",
            "estimate_parasitics -placement",
            "create_clock -name vclk -period 833.333",
            f"set_driving_cell -lib_cell {BUF} -pin Y [get_ports root]",
            "set_input_delay 0 -clock vclk [get_ports root]",
            f"set_load {TAP_LOAD_FF} [all_outputs]",
            "set_output_delay 0 -clock vclk [all_outputs]",
            "set fh [open /work/clock/arr_$::env(CORNER).txt w]",
            # arrival at a port = period - slack (output delay 0); at a buffer output pin = its arrival property
            "foreach p [get_ports t_*] { set n [get_full_name $p]; "
            "set smx [get_property $p slack_max_rise]; set smn [get_property $p slack_min_rise]; "
            "puts $fh \"T $n [expr {833.333 - $smx}] [expr {$smn}]\" }",
            "foreach i [get_cells b*] { set q [get_pins [get_full_name $i]/Y]; "
            "puts $fh \"N [get_full_name $i] [get_property $q arrival_max_rise] [get_property $q arrival_min_rise]\" }",
            "close $fh",
            "report_checks -path_delay max -group_path_count 1 -format full -fields {cap slew fanout}",
            "puts OT_DONE"]
    if tap_rep_um is not None:
        # Strict candidate models use the release clock exactly, including the
        # period-minus-slack arrival conversion. Legacy diagnostics unchanged.
        tcl=[line.replace("833.333","833.000") for line in tcl]
    (out / "ctree.tcl").write_text("\n".join(tcl) + "\n")
    meta = dict(leaf_um=leaf_um, rep_um=rep_um, **({"full_depth": True} if full_depth else {}),
                **({"tap_rep_um": tap_rep_um, "tap_repeaters": sum(i.startswith("rtap") for i, *_ in place)}
                   if tap_rep_um is not None else {}),
                **({"region_trees": len({n.get("region_root") for n in nodes.values()} - {None})} if regions else {}), buffer=BUF, wire_r_kohm_um=WIRE_R, wire_c_ff_um=WIRE_C,
                tap_load_ff=TAP_LOAD_FF, nodes=len(nodes), leaves=sum(1 for n in nodes.values() if n["taps"]),
                repeaters=sum(1 for i, *_ in place if i.startswith("r")), taps=len(tap_ports),
                wire_um=round(sum(abs(a - c) + abs(b - d) for a, b, c, d, _ in segs) +
                              sum(abs(a - c) + abs(b - d) for a, b, c, d in leaf_legs), 1),
                levels=max(n["level"] for n in nodes.values()))
    if site is not None:
        bad = {}
        for inst, x, y in place:
            w = site.why((x, y))
            if w:
                bad[w] = bad.get(w, 0) + 1
        meta["site_legal"] = dict(mode="slide" if site_slide else "nearest", slide_fallbacks=slid_fallback,
                                  cells=len(place), illegal=bad, forbidden_rects=len(site.forb),
                                  moved_nodes=sum(1 for n in nodes.values() if [n["x"], n["y"]] != n["req_xy"]))
    tree = dict(meta=meta, nodes={i: {k: v for k, v in n.items() if k != "taps"} | dict(ntaps=len(n["taps"]))
                                  for i, n in nodes.items()},
                taps=[dict(port=tp, part=part, tap=port, xy=[x, y], node=i) for tp, x, y, part, port, i in tap_ports],
                node_buf=node_buf, parent_of=parent_of, sites={inst: [round(x, 3), round(y, 3)] for inst, x, y in place})
    (out / "tree.json").write_text(json.dumps(tree) + "\n")
    return nodes, segs, leaf_legs, meta


def reserve_rects(segs, leaf_legs, P):
    """M8 (H) / M9 (V) reservation rectangles of the clock tree wires (NDR_TRACKS tracks wide)."""
    out = []
    for x0, y0, x1, y1, *_ in segs:
        out += _leg_rects(x0, y0, x1, y1, P)
    for x0, y0, x1, y1 in leaf_legs:
        out += _leg_rects(x0, y0, x1, y1, P)
    return out


def _leg_rects(x0, y0, x1, y1, P):
    h = NDR_TRACKS * P.layers["M8"]["pitch_um"] / 2
    v = NDR_TRACKS * P.layers["M9"]["pitch_um"] / 2
    r = []
    if abs(x1 - x0) > 1e-6:          # horizontal run on M8 at y0
        a, b = sorted((x0, x1))
        r.append(("M8", a, y0 - h, b, y0 + h))
    if abs(y1 - y0) > 1e-6:          # vertical run on M9 at x1
        a, b = sorted((y0, y1))
        r.append(("M9", x1 - v, a, x1 + v, b))
    return r


# --------------------------------------------------------------------------------------------------------- GRT kit
def coarse_tracks(P, coarse):
    lines = []
    for n in ("M1", "M2", "M3"):
        lines.append(f"make_tracks {n} -x_offset {coarse / 2:g} -x_pitch {coarse:g} -y_offset {coarse / 2:g} "
                     f"-y_pitch {coarse:g}")
    for n in ("M4", "M5", "M6", "M7", "M8", "M9"):
        L = P.layers[n]
        lines.append(f"make_tracks {n} -x_offset {L['offset_um']:g} -x_pitch {L['pitch_um']:g} "
                     f"-y_offset {L['offset_um']:g} -y_pitch {L['pitch_um']:g}")
    return "\n".join(lines) + "\n"


def pg_stripes(P):
    """[(layer, x0, y0, x1, y1)] of the die PG stripes (die.pg.grid)."""
    out = []
    for g in P.die.get("pg", {}).get("grid", []):
        L = P.layers.get(g["layer"])
        if not L:
            continue
        k = max(1, len(g.get("nets", ["VDD", "VSS"])))
        ext = P.H if L["dir"] == "V" else P.W
        span = P.W if L["dir"] == "V" else P.H
        pos = g["offset_um"]
        while pos < span:
            for j in range(k):
                c = pos + j * g["pitch_um"] / k
                if c + g["width_um"] / 2 > span:
                    continue
                a, b = c - g["width_um"] / 2, c + g["width_um"] / 2
                out.append((g["layer"],) + ((a, 0, b, ext) if L["dir"] == "V" else (0, a, ext, b)))
            pos += g["pitch_um"]
    return out


def ft_nets(P):
    """[(inst, slot, nbits_connected, in_bits, out_bits)] and the die route netlist connections per instance."""
    rows = []
    for n, p in sorted(P.parts.items()):
        t = P.types[p["type"]]
        for s in t.get("ft_slots", []) or []:
            rows.append((n, s["name"], int(s["width"]), int(s.get("stations", 1))))
    return rows


def route_netlist(P, type_bits):
    """die route netlist: every instance's ft slots S_i[b] -> S_o[b] joined (one net per bit), arst_n on the reset
    spine.  type_bits {type: {bus: nbits}} from the plan pins."""
    v = [f"module {sv(P.name)}_route (rst_n);", "  input rst_n;"]
    insts, nft = [], 0
    for n, p in sorted(P.parts.items()):
        tn = p["type"]
        t = P.types[tn]
        conns = [".arst_n(rst_n)"]
        for s in t.get("ft_slots", []) or []:
            bi, bo = type_bits[tn].get(s["name"] + "_i", 0), type_bits[tn].get(s["name"] + "_o", 0)
            k = min(bi, bo)
            if k <= 0:
                continue
            w = f"ft_{sv(n)}__{sv(s['name'])}"
            v.append(f"  wire [{k - 1}:0] {w};")
            conns.append(f".{s['name']}_i({w})")
            conns.append(f".{s['name']}_o({w})")
            nft += k
        insts.append(f"  {t['module']} {sv(n)} ({', '.join(conns)});")
    v += insts + ["endmodule"]
    return "\n".join(v) + "\n", nft


# ------------------------------------------------------------------------------ die_ft_bands GRT capacity model
# (DIE-FT-HBM 10-25 band stripes, DIE-FT 10-25 20:40 transition-layer fix; read against OpenROAD GlobalRouter.cpp
# 26Q3: applyObstructionAdjustment / extendObstructions / adjustTransitionLayers)
GCELL_UM = 10.8          # OpenROAD die gcell here (15 x M3 pitch 0.72; congestion.rpt bboxes, origin 0; floor(W/g) tiles)
OBS_EXT_UM = 0.072       # macro OBS extension = largest SPACINGTABLE value of M4-M6 (asap7 1x tech LEF; findLayerExtensions)
# OpenROAD halves ("fat via" transition, adjustTransitionLayers) the capacity of these layers in every gcell above a
# macro OBS on the layer below, from the capacity BEFORE the die obstructions: measured 10-25 on a 216x216 test die
# (block with OBS M4-M5: M6 -10.7 % of the die, layer adjustment 0.75 keeps 0.5 x 0.25 there).
TRANSITION_LAYERS = ("M5", "M6")
TRANSITION_KEEP = 0.5


def ft_band_rects(P):
    """die-frame rects of every type's die_ft_bands (DIE-FT-HBM 10-25): [(layer, x0, y0, x1, y1, die_share)].
    A band is a type-frame span (EW: y, NS: x) over the full type width/height where the listed layers belong to the
    die (die_share of their tracks, default 1.0) instead of the ft_track_frac share."""
    out = []
    for n, p in sorted(P.parts.items()):
        t = P.types[p["type"]]
        bands = t.get("die_ft_bands") or []
        if not bands:
            continue
        o = p.get("orient", "R0")
        if o not in ("R0", "MX", "MY", "R180"):
            raise ValueError(f"die_ft_bands on {n}: orient {o} not supported")
        w, h = t["outline_um"]
        ox, oy = p["origin_um"]
        for b in bands:
            lo, hi = b["span_um"]
            if b["dir"] == "EW":
                if o in ("MX", "R180"):
                    lo, hi = h - hi, h - lo
                r = (ox, oy + lo, ox + w, oy + hi)
            else:
                if o in ("MY", "R180"):
                    lo, hi = w - hi, w - lo
                r = (ox + lo, oy, ox + hi, oy + h)
            for L in b["layers"]:
                out.append((L, *r, float(b.get("die_share", 1.0))))
    return out


def die_core_rects(P, L, grow=0.0):
    """die-frame rects (grown by `grow` um) of every planned hard core whose abstract OBS covers layer L
    (abstract_lef: OBS on M4 .. min(core top, partition_signal_max))."""
    li = int(L[1:])
    top = int(P.layer_budget["partition_signal_max"][1:])
    out = []
    for n, p in P.parts.items():
        t = P.types[p["type"]]
        w, h = t["outline_um"]
        ox, oy = p["origin_um"]
        o = p.get("orient", "R0")
        for x0, y0, x1, y1, tl, _, _ in core_obs(t):
            if li < 4 or li > min(int(tl[1:]), top):
                continue
            if o in ("MY", "R180"):
                x0, x1 = w - x1, w - x0
            if o in ("MX", "R180"):
                y0, y1 = h - y1, h - y0
            out.append((ox + x0 - grow, oy + y0 - grow, ox + x1 + grow, oy + y1 + grow))
    return out


def _uncovered(W, H, rects):
    """rectangles covering [0,W]x[0,H] minus the union of rects (slab sweep, vertically merged)."""
    ys = sorted({0.0, H} | {min(max(r[1], 0.0), H) for r in rects} | {min(max(r[3], 0.0), H) for r in rects})
    open_ = {}
    out = []
    for ya, yb in zip(ys, ys[1:]):
        if yb - ya < 1e-6:
            continue
        cov = sorted((max(r[0], 0.0), min(r[2], W)) for r in rects if r[1] <= ya + 1e-6 and r[3] >= yb - 1e-6)
        free, x = [], 0.0
        for a, b in cov + [(W, W)]:
            if a > x + 1e-6:
                free.append((round(x, 3), round(a, 3)))
            x = max(x, b)
        nxt = {}
        for iv in free:
            nxt[iv] = open_.pop(iv, ya)
        for (a, b), y0 in open_.items():
            out.append((a, y0, b, ya))
        open_ = nxt
    for (a, b), y0 in open_.items():
        out.append((a, y0, b, H))
    return out


def _ngrid(L, g=GCELL_UM):
    """OpenROAD tile count along a die side: integer DBU floor (float 216 // 10.8 is 19.0, OpenROAD has 20)."""
    return max(1, int(round(L * 1000)) // int(round(g * 1000)))


def _gstrips(rects, vertical, W, H, g=GCELL_UM, eps=0.01):
    """region rects -> strips one gcell thick across the layer direction (rows for an H layer, columns for a V layer),
    snapped to the gcell grid with upper edges pulled in by eps, so every gcell has exactly one owner.  H strips stop
    before the last tile column and V strips before the last tile row (capacity 0 there, no routing edge).
    -> [(x0, y0, x1, y1, *extra)]"""
    nx, ny = _ngrid(W, g), _ngrid(H, g)
    imax = nx - (0 if vertical else 1)
    jmax = ny - (1 if vertical else 0)
    out = []
    for r in rects:
        i0, j0, i1, j1 = (int(round(v / g)) for v in r[:4])
        i1, j1 = min(i1, imax), min(j1, jmax)
        if i1 <= i0 or j1 <= j0:
            continue
        if vertical:
            out += [(round(i * g, 3), round(j0 * g, 3), round((i + 1) * g - eps, 3), round(j1 * g - eps, 3))
                    + tuple(r[4:]) for i in range(i0, i1)]
        else:
            out += [(round(i0 * g, 3), round(j * g, 3), round(i1 * g - eps, 3), round((j + 1) * g - eps, 3))
                    + tuple(r[4:]) for j in range(j0, j1)]
    return out


def band_region_adjust(P, share_adj):
    """the die_ft_bands share model as one-gcell strips: band layers get global layer adjustment 0; every die area
    outside a band of that layer keeps 1 - share_adj of its tracks (share_adj = the usual 1 - ft_track_frac) and a
    band with die_share < 1 keeps die_share.  Strips also cover planned hard cores: on the OBS layers of a core the
    capacity is 0 anyway (obstruction strips over macro OBS do not underflow, measured 10-25), and above it the share
    applies as everywhere else.  The 12-um core halo of cebbd80b8 is gone: it existed only for region adjustments
    (GRT-0114 underflow) and gave the die 100 % of M4/M5 in a ring around every core (HBM edge+band M4 +31 %).
    -> (band layers, [(layer, x0, y0, x1, y1, kept fraction)])"""
    rects = ft_band_rects(P)
    by = defaultdict(list)
    for L, x0, y0, x1, y1, ds in rects:
        by[L].append((x0, y0, x1, y1, ds))
    regs = []
    for L, rs in sorted(by.items()):
        vert = P.layers[L]["dir"] == "V"
        for x0, y0, x1, y1 in _gstrips(_uncovered(P.W, P.H, [r[:4] for r in rs]), vert, P.W, P.H):
            regs.append((L, x0, y0, x1, y1, round(1 - share_adj, 3)))
        for x0, y0, x1, y1, ds in rs:
            if ds < 1.0:
                for a in _gstrips([(x0, y0, x1, y1)], vert, P.W, P.H):
                    regs.append((L, *a, round(ds, 3)))
    return sorted(by), regs


def transition_intervals(P, L, g=GCELL_UM, ext=OBS_EXT_UM):
    """{strip index: [(lo, hi)]} gcell intervals where OpenROAD halves transition layer L (adjustTransitionLayers):
    every gcell from the first to the last-but-one tile of each macro OBS rect on the layer below (extended by the
    spacing in that layer's cross direction).  Strip index = gcell row for an H layer, column for a V layer; the
    interval runs along the layer direction.  Empty for non-transition layers."""
    if L not in TRANSITION_LAYERS:
        return {}
    below = f"M{int(L[1:]) - 1}"
    vb = P.layers[below]["dir"] == "V"
    nx, ny = _ngrid(P.W, g), _ngrid(P.H, g)
    by = defaultdict(list)
    for x0, y0, x1, y1 in die_core_rects(P, below, 0.0):
        if vb:
            x0, x1 = x0 - ext, x1 + ext
        else:
            y0, y1 = y0 - ext, y1 + ext
        fx, fy = int(max(x0, 0.0) // g), int(max(y0, 0.0) // g)
        lx, ly = min(int(x1 // g), nx - 1), min(int(y1 // g), ny - 1)
        if (fx, fy) == (lx, ly):
            continue
        if P.layers[L]["dir"] == "V":
            for i in range(fx, lx):
                by[i].append((fy, ly))
        else:
            for j in range(fy, ly):
                by[j].append((fx, lx))
    out = {}
    for k, ivs in by.items():
        m = []
        for lo, hi in sorted(ivs):
            if hi <= lo:
                continue
            if m and lo <= m[-1][1]:
                m[-1][1] = max(m[-1][1], hi)
            else:
                m.append([lo, hi])
        out[k] = [tuple(v) for v in m]
    return out


def band_share_obs(P, regs, g=GCELL_UM):
    """die_ft_bands share as OBSTRUCTION stripes: in every one-gcell strip from band_region_adjust (kept fraction a)
    obstruct the top f of each gcell row (H layer) or the right f of each gcell column (V layer), f = 1 - a.

    Transition layers (TRANSITION_LAYERS) over a macro OBS on the layer below: OpenROAD halves those gcells from the
    capacity before obstructions, so the two reductions ADD (strip 0.75 + halving 0.5 -> 0 tracks: the 10-25 HBM
    edge+band root interior, 8,806 zero-capacity gcells, 21 tracks in the layer-adjustment run of the same LEF).
    There f = (1 - TRANSITION_KEEP) * (1 - a), which keeps TRANSITION_KEEP * a: the same capacity a global layer
    adjustment gives (measured 10-25 on a 216x216 test die: M6 14,110 strips vs 14,259 layer adjustment 0.75; the
    uncompensated strips 12,490), so band and non-band kits share one capacity model.  -> [(layer, x0, y0, x1, y1)]"""
    trans = {L: transition_intervals(P, L, g) for L in sorted({r[0] for r in regs})}
    out = []
    for L, x0, y0, x1, y1, a in regs:
        if a >= 1.0:
            continue
        vert = P.layers[L]["dir"] == "V"
        k = int(round((x0 if vert else y0) / g))
        lo, hi = (int(round(v / g)) for v in ((y0, y1 + 0.01) if vert else (x0, x1 + 0.01)))
        f, fh = 1.0 - a, (1.0 - TRANSITION_KEEP) * (1.0 - a)
        segs, pos = [], lo
        for a0, a1 in trans[L].get(k, []):
            a0, a1 = max(a0, lo), min(a1, hi)
            if a1 <= a0:
                continue
            if a0 > pos:
                segs.append((pos, a0, f))
            segs.append((a0, a1, fh))
            pos = a1
        if pos < hi:
            segs.append((pos, hi, f))
        for s0, s1, ff in segs:
            c0, c1 = round((k + 1) * g - ff * g, 3), round((k + 1) * g, 3)
            if vert:
                out.append((L, c0, round(s0 * g, 3), c1, round(s1 * g, 3)))
            else:
                out.append((L, round(s0 * g, 3), c0, round(s1 * g, 3), c1))
    return out


PLACE_PROC = ("proc ot_place {n x y o} { set b [ord::get_db_block]; set i [$b findInst $n]; $i setOrient $o; "
              "set d [[$b getTech] getDbUnitsPerMicron]; set X [expr {round($x*$d)}]; set Y [expr {round($y*$d)}]; "
              "$i setLocation $X $Y; set bb [$i getBBox]; "
              "$i setLocation [expr {2*$X - [$bb xMin]}] [expr {2*$Y - [$bb yMin]}]; set bb [$i getBBox]; "
              "if {[$bb xMin] != $X || [$bb yMin] != $Y} { puts \"OT_PLACE_MISMATCH $n [$bb xMin] [$bb yMin]\" }; "
              "$i setPlacementStatus FIRM }")


def grt_tcl(P, out, coarse, lefs, reserve, adjust):
    W, H = P.W, P.H
    t = [f"# GENERATED by tools/die_plan/die_trial.py: die global route on abstracts, die {P.name}.",
         "set t0 [clock seconds]",
         f"read_lef {TECH_LEF}", f"read_lef {SC_LEF}"]
    t += [f"read_lef /work/abstracts/{x}" for x in lefs]
    t += [f"read_verilog /work/grt/route.v", f"link_design {sv(P.name)}_route",
          f"initialize_floorplan -die_area {{0 0 {gen_phys._um(W)} {gen_phys._um(H)}}} -core_area {{0 0 {gen_phys._um(W)} {gen_phys._um(H)}}} -site asap7sc7p5t",
          "source /work/grt/tracks.tcl", PLACE_PROC,
          "puts \"OT_T floorplan [expr {[clock seconds]-$t0}]\""]
    rp = {n: (x, y, L) for n, L, x, y in gen_phys.die_root_pins(P)}
    x, y, L = rp["rst_n"]
    t.append(f"place_pin -pin_name rst_n -layer {L} -location {{{x:.4f} {y:.4f}}} -pin_size {{0.32 0.04}}")
    for n, p in sorted(P.parts.items()):
        ox, oy = p["origin_um"]
        t.append(f"ot_place {sv(n)} {ox:g} {oy:g} {p.get('orient', 'R0')}")
    t.append("puts \"OT_T placed [expr {[clock seconds]-$t0}]\"")
    t.append("source /work/grt/obs.tcl")
    t.append("puts \"OT_T obs [expr {[clock seconds]-$t0}]\"")
    # METHODOLOGY 12.1c (owner 10-26): die-top signals on M4-M7 + leftover M8/M9 (PG stripes + clock NDR
    # reservations are obstructions); OT_DIE_SIGNAL_M47=1 = the 9.3-era legacy diagnostic only
    t.append("set_routing_layers -signal M4-M7" if os.environ.get("OT_DIE_SIGNAL_M47") == "1"
             else "set_routing_layers -signal M4-M9")
    band_layers, band_regs = band_region_adjust(P, dict(adjust).get("M4", 0.75))
    for L, a in adjust:
        t.append(f"set_global_routing_layer_adjustment {L} {0 if L in band_layers else a:g}")
    t += ["global_route -congestion_iterations 50 -allow_congestion -verbose "
          "-congestion_report_file /work/grt/congestion.rpt",
          "puts \"OT_T grt [expr {[clock seconds]-$t0}]\"",
          "if {[catch {grt::report_layer_wire_lengths} e]} { puts \"OT_NO_LAYER_WL $e\" }",
          "write_guides /work/grt/route.guide",
          "puts \"OT_T guides [expr {[clock seconds]-$t0}]\"",
          "puts OT_DONE"]
    obs = []
    for L, a, b, c, d in pg_stripes(P):
        obs.append(f"create_obstruction -region {{{a:.3f} {b:.3f} {c:.3f} {d:.3f}}} -layer {L}")
    for L, a, b, c, d in reserve:
        obs.append(f"create_obstruction -region {{{a:.3f} {b:.3f} {c:.3f} {d:.3f}}} -layer {L}")
    for L, a, b, c, d in band_share_obs(P, band_regs):   # die_ft_bands share stripes (band_share_obs)
        obs.append(f"create_obstruction -region {{{a:.3f} {b:.3f} {c:.3f} {d:.3f}}} -layer {L}")
    (Path(out) / "obs.tcl").write_text("\n".join(obs) + "\n")
    return "\n".join(t) + "\n"


# --------------------------------------------------------------------------------------------------------- PSM kit
def part_power(P, plan_dir, density_w_mm2):
    """{part: W}: uniform areal density (technology.json clock energy 8.5e-11 J/mm2/cycle at 1.2 GHz = 0.102 W/mm2
    ungated clock, + logic / leakage; the density is a parameter of the run: IR scales linearly)."""
    return {n: round(density_w_mm2 * P.types[p["type"]]["outline_um"][0] * P.types[p["type"]]["outline_um"][1] * 1e-6, 6)
            for n, p in P.parts.items()}


def io_windows(P, plan_dir):
    io = P.die.get("io")
    if not io:
        f = Path(plan_dir) / "die_io.json"
        io = json.loads(f.read_text()) if f.is_file() else []
    return io


def psm_tcl(P, lefs, power, bumps):
    W, H = P.W, P.H
    t = [f"# GENERATED by tools/die_plan/die_trial.py: die PDN + PDNSim on abstracts, die {P.name}.",
         "set t0 [clock seconds]", f"read_lef {TECH_LEF}", f"read_lef {SC_LEF}"]
    t += [f"read_lef /work/abstracts/{x}" for x in lefs]
    t += [f"foreach f [glob {PLAT}/lib/NLDM/*RVT_TT_nldm*.lib*] {{ read_liberty $f }}",
          "read_verilog /work/psm/psm.v", f"link_design {sv(P.name)}_psm",
          f"initialize_floorplan -die_area {{0 0 {gen_phys._um(W)} {gen_phys._um(H)}}} -core_area {{0 0 {gen_phys._um(W)} {gen_phys._um(H)}}} -site asap7sc7p5t",
          "source /work/grt/tracks.tcl", PLACE_PROC]
    for n, p in sorted(P.parts.items()):
        ox, oy = p["origin_um"]
        t.append(f"ot_place {sv(n)} {ox:g} {oy:g} {p.get('orient', 'R0')}")
    t += ["puts \"OT_T placed [expr {[clock seconds]-$t0}]\"", "source /work/psm/pdn.tcl", "pdngen",
          "puts \"OT_T pdngen [expr {[clock seconds]-$t0}]\"",
          "write_db /work/psm/pdn_grid.odb",
          "source /work/psm/bumps.tcl",
          "puts \"OT_T bumps [expr {[clock seconds]-$t0}]\"",
          "write_db /work/psm/pdn_bumps.odb",
          "source /work/psm/power.tcl",
          f"source {PLAT}/setRC.tcl",
          "set pg_failed 0",
          "foreach n {VDD VSS} { if {[catch {check_power_grid -net $n} e]} { incr pg_failed; puts \"OT_PG_CHECK_FAIL $n $e\" } "
          "else { puts \"OT_PG_CHECK_OK $n\" } }",
          "puts \"OT_T check [expr {[clock seconds]-$t0}]\"",
          "if {$pg_failed} { error \"power-grid connectivity failed\" }",
          "if {[catch {analyze_power_grid -net VDD -error_file /work/psm/psm_VDD.rpt "
          "-voltage_file /work/psm/ir_VDD.csv} e]} { puts \"OT_PSM_FAIL $e\"; error $e } else { puts OT_PSM_OK }",
          "puts \"OT_T psm [expr {[clock seconds]-$t0}]\"",
          "puts OT_DONE"]
    return "\n".join(t) + "\n"


def psm_pdn_tcl(P):
    """die-trial PDN from the plan's PG rows (ONE PDN RULE, COORD 10-26 13:13): explicit offset + parity from the die
    lattice (pg_regions.row_spec); a plan with die.pg.domains (PHY windows) builds its VDDPHY regions exactly as
    pg_regions.pdn_tcl (PG first = real view), so the die-trial kit, the assembly and the die_infra model agree."""
    import pg_regions
    die = dict(P.die, outline_um=[P.W, P.H])
    g = die.get("pg", {}).get("grid")
    lines = ["add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power",
             "add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground"]
    if die.get("pg", {}).get("domains"):
        phy = sorted({d["nets"][0] for d in die["pg"]["domains"]} - {"VDD"})
        lines += [f"add_global_connection -net {{{n}}} -inst_pattern {{.*}} -pin_pattern {{^{n}$}} -power" for n in phy]
        lines += [pg_regions.pdn_tcl(die).rstrip("\n")]
        dom = "Core"
    else:
        lines += ["global_connect", "set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}",
                  "define_pdn_grid -name {top} -voltage_domains {CORE}"]
        lines += pg_regions.core_stripes_tcl(die, "{top}")
        ls = [s["layer"] for s in g]
        for a, b in zip(ls, ls[1:]):
            lines.append(f"add_pdn_connect -grid {{top}} -layers {{{a} {b}}}")
        dom = "CORE"
    lines += [f"define_pdn_grid -name {{parts}} -voltage_domains {{{dom}}} -macro -orient {{R0 R180 MX MY}} "
              "-halo {0 0 0 0} -default", f"add_pdn_connect -grid {{parts}} -layers {{M7 {g[0]['layer']}}}"]
    return "\n".join(lines) + "\n"


def bump_grid(P, io, pitch=150.0, size=60.0):
    """C4 power bumps: a regular grid at `pitch` (alternating VDD / VSS by row+col parity) inside the die, minus the
    seal ring / corner keep-out channels and the die IO windows (signal bumps).  -> [(net, x, y)]"""
    keep = [c["rect_um"] for c in P.die.get("channels", [])] + [w["rect_um"] for w in io]
    out = []
    nx, ny = int(P.W // pitch), int(P.H // pitch)
    x0 = (P.W - (nx - 1) * pitch) / 2
    y0 = (P.H - (ny - 1) * pitch) / 2
    for i in range(nx):
        for j in range(ny):
            x, y = x0 + i * pitch, y0 + j * pitch
            if any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for r in keep):
                continue
            out.append(("VDD" if (i + j) % 2 == 0 else "VSS", round(x, 3), round(y, 3)))
    return out


def bumps_tcl(P, bumps, size=4.0):
    """Attach each source to actual M9 metal of its own net after pdngen.

    Stripe origins depend on the floorplan core origin and pdngen net phase.
    Computing them from the plan offset produced isolated voltage-source pins.
    """
    t = ["set block [ord::get_db_block]",
         # pdngen makes boundary PG ports; they are not the specified C4 sources.
         "foreach ot_auto_name {VDD VSS} { set ot_auto_bt [$block findBTerm $ot_auto_name]; "
         "if {$ot_auto_bt ne \"NULL\"} { if {[$ot_auto_bt getSigType] ni {POWER GROUND}} "
         "{ error \"refusing to remove non-PG boundary port $ot_auto_name\" }; "
         "odb::dbBTerm_destroy $ot_auto_bt } }",
         "set m9 [[ord::get_db_tech] findLayer M9]",
         "set bump_dbu [[ord::get_db_tech] getDbUnitsPerMicron]",
         "set bump_shapes {}", "set bump_x_cache {}",
         "foreach net_name {VDD VSS} {",
         "  set shapes {}",
         "  foreach wire [[$block findNet $net_name] getSWires] {",
         "    foreach shape [$wire getWires] {",
         "      if {[$shape isVia] || [$shape getTechLayer] ne $m9} continue",
         "      lappend shapes [list [$shape xMin] [$shape yMin] [$shape xMax] [$shape yMax]]",
         "    }",
         "  }",
         "  if {![llength $shapes]} { error \"no actual M9 metal for $net_name voltage sources\" }",
         "  dict set bump_shapes $net_name $shapes",
         "}"]
    for k, (net, x, y) in enumerate(bumps):
        t += [f"set bx [expr {{{x:g}*$bump_dbu}}]; set by [expr {{{y:g}*$bump_dbu}}]",
              f"set cache_key [list {net} $bx]",
              "if {![dict exists $bump_x_cache $cache_key]} {",
              "  set nearest {}; set x_distance 1e30",
              f"  foreach rect [dict get $bump_shapes {net}] {{",
              "    lassign $rect x0 y0 x1 y1",
              "    set dx [expr {abs(($x0+$x1)/2.0-$bx)}]",
              "    if {$dx < $x_distance} { set x_distance $dx; set nearest [list $rect] } elseif {$dx == $x_distance} { lappend nearest $rect }",
              "  }",
              "  dict set bump_x_cache $cache_key $nearest",
              "}",
              "set best {}; set best_distance 1e30",
              "foreach rect [dict get $bump_x_cache $cache_key] {",
              "  lassign $rect x0 y0 x1 y1",
              "  set cx [expr {($x0+$x1)/2.0}]",
              f"  set half [expr {{min({size:g}*$bump_dbu/2.0,($y1-$y0)/2.0)}}]",
              "  set cy [expr {max($y0+$half,min($y1-$half,$by))}]",
              "  set distance [expr {abs($cx-$bx)+abs($cy-$by)}]",
              "  if {$distance < $best_distance} {",
              "    set best_distance $distance",
              "    set best [list $x0 [expr {int($cy-$half)}] $x1 [expr {int($cy+$half)}]]",
              "  }",
              "}",
              f"set bt [odb::dbBTerm_create [$block findNet {net}] {net}_b{k}]; $bt setIoType INOUT; "
              f"$bt setSigType {'POWER' if net == 'VDD' else 'GROUND'}; set bp [odb::dbBPin_create $bt]",
              "odb::dbBox_create $bp $m9 {*}$best; $bp setPlacementStatus FIRM"]
    t.append(f'puts "OT_BUMPS actual_m9_sources {len(bumps)} cached_columns [dict size $bump_x_cache]"')
    return "\n".join(t) + "\n"


# --------------------------------------------------------------------------------------------------------- STA kit
def standin_netlist(P, tn, hold_contract=True, clock_contract=True):
    """budget stand-in of a partition type for die_sta.py: one face flop per pin bit next to its pin, clocked from the
    nearest plan clock tap (no internal logic: the partition's internal paths are its own G3 closure).  hold_contract:
    every input bit reaches its face flop through the boundary-hold contract cell (die_sta.bhold_cell(tol)): the port
    -> D minimum a signed kit guarantees under the signoff.py hold_ff overlay (input min -insertion_tol).
    clock_contract: every clock tap port drives ONE clock-latency contract cell (die_sta.clat_cell: input cap = the
    kit CTS root load the die tree is balanced against, constant delay = the type's bound TT / FF pin-register
    insertion, gen_phys.insertion_binding) and the face flops hang on its output, never on the port; face flops take
    the nearest TYPE tap (pin registers sit on the type grid taps), early core taps (clk_c<k>) drive only their
    contract cell at the core's insertion (the hard core's own tree).  Without it (legacy) every face flop's CLK
    loads the port directly and core taps clock face flops too."""
    t = P.types[tn]
    pins = gen_phys.type_pins(P, tn)
    bits = defaultdict(int)
    for bus, bit, *_ in pins:
        bits[bus] = max(bits[bus], bit + 1)
    ctaps = gen_phys.clock_pins(P, tn)
    cores = gen_phys.core_tap_pins(P, tn)
    taps = ctaps + cores
    tapn = [n for n, _, _ in taps]
    dirs = {b["name"]: b["dir"] for b in t.get("buses", [])}
    for sl in t.get("ft_slots", []) or []:
        dirs[sl["name"] + "_i"], dirs[sl["name"] + "_o"] = "in", "out"
    flop_taps = ctaps if clock_contract and ctaps else taps

    def near(x, y):
        return min(flop_taps, key=lambda q: abs(q[1] - x) + abs(q[2] - y))[0]
    # reset wavefront + START broadcast (OWNER DECISIONS 13/13c; reset_tree.py): the registered entries arst_n (u_rst_in)
    # and start_i, and the registered outs rst_o_<k> / start_o_<k>, are partition pins the die top wires parent ->
    # child.  Each gets ONE pin register at its own plan site on the nearest type tap, exactly like a data face flop,
    # so die STA times every wavefront / START hop (PATH-QC 10-25: without these ports die STA dropped 373 START nets
    # as 'port not found' and timed data seams only).  The partition-internal equal-depth relay tree is its own closure.
    tp = {n: (x, y) for n, x, y in gen_phys.tap_pins(P, tn)}
    rin = [(n,) + tuple(tp[n]) for n in ("arst_n", "start_i") if n in tp]
    rout = [tuple(r[:3]) for r in gen_phys.reset_out_pins(P, tn)]
    ports = [f"  input {n};" for n in tapn] + [f"  input {n};" for n, _, _ in rin] + \
        [f"  output {n};" for n, _, _ in rout]
    for b in sorted(bits):
        ports.append(f"  {'input' if dirs.get(b) == 'in' else 'output'} [{bits[b] - 1}:0] {b};")
    ckn, ckcells, ckwires = {n: n for n in tapn}, [], []
    if clock_contract:
        ib = gen_phys.insertion_binding(P, tn)
        cins = {r[0]: r[4] for r in gen_phys.core_tap_rows(P, tn)} if cores else {}
        for j, n in enumerate(tapn):
            if n in cins:
                tt = cins[n]
                lat = die_sta.clat_cell(tt, round(gen_phys.FF_TT_INSERTION_RATIO * tt, 1))
            else:
                lat = die_sta.clat_cell(ib["tt"], ib["ff"])
            ckn[n] = f"ck_{n}"
            ckwires.append(f"  wire ck_{n};")
            ckcells.append(f"  {lat} c{j} (.A({n}), .Y(ck_{n}));")
    cells = []
    k = 0
    bh = die_sta.bhold_cell(gen_phys.seam_hold(P)["seam_ps"])
    for bus, bit, ln, x, y, f in sorted(pins, key=lambda p: (p[0], p[1])):
        ck = ckn[near(x, y)]
        if dirs.get(bus) == "in" and hold_contract:
            cells.append(f"  {bh} h{k} (.A({bus}[{bit}]), .Y(d{k}));\n  {FLOP} f{k} (.CLK({ck}), .D(d{k}), .QN(q{k}));")
        elif dirs.get(bus) == "in":
            cells.append(f"  {FLOP} f{k} (.CLK({ck}), .D({bus}[{bit}]), .QN(q{k}));")
        else:
            cells.append(f"  {FLOP} f{k} (.CLK({ck}), .D(1'b0), .QN({bus}[{bit}]));")
        k += 1
    for n, x, y in rin:
        ck = ckn[near(x, y)]
        if hold_contract:
            cells.append(f"  {bh} h{k} (.A({n}), .Y(d{k}));\n  {FLOP} f{k} (.CLK({ck}), .D(d{k}), .QN(q{k}));")
        else:
            cells.append(f"  {FLOP} f{k} (.CLK({ck}), .D({n}), .QN(q{k}));")
        k += 1
    for n, x, y in rout:
        cells.append(f"  {FLOP} f{k} (.CLK({ckn[near(x, y)]}), .D(1'b0), .QN({n}));")
        k += 1
    names = tapn + [n for n, _, _ in rin] + [n for n, _, _ in rout] + sorted(bits)
    v = [f"module {t['module']} ({', '.join(names)});"] + ports + ckwires
    v += [f"  wire q{i};" for i in range(k) if f".QN(q{i})" in cells[i]]
    v += [f"  wire d{i};" for i in range(k) if f".Y(d{i})" in cells[i]]
    v += ckcells + cells + ["endmodule"]
    return "\n".join(v) + "\n", k


def standin_module_names(P):
    """{type: stand-in module name}.  Plan types that share one RTL module (slice variants, e.g. QC slw_fw_v1/v2/v3)
    have different pins (buses, ft slots, rst_o / start_o sets), so ONE PARTS/<module> stand-in (last type written)
    left the other variants' die-top connections dangling ('port not found': 308 on QC plan 441d).  Each such type
    gets its own stand-in module <module>__<type>; types with a unique module keep the module name (closed views)."""
    from collections import Counter
    n = Counter(t["module"] for t in P.types.values())
    return {tn: (t["module"] if n[t["module"]] == 1 else f"{t['module']}__{tn}") for tn, t in P.types.items()}


def retarget_shared_modules(P, top, smod):
    """die top text with every instance of a shared-module type re-pointed at its per-type stand-in module."""
    for name, p in P.parts.items():
        m, tn = P.types[p["type"]]["module"], p["type"]
        if smod[tn] == m:
            continue
        pat = re.compile(r"^(\s*)" + re.escape(m) + r"(\s+" + re.escape(gen_rtl.sv_id(name)) + r"\s*\()", re.M)
        top, k = pat.subn(lambda mm: mm.group(1) + smod[tn] + mm.group(2), top, count=1)
        if k != 1:
            raise ValueError(f"die top: instance {name} of {m} not found for stand-in retarget")
    return top


_STANDIN_IN = re.compile(r"^(\s*)(" + re.escape(FLOP) + r") f(\d+) \(\.CLK\(([^)]*)\), \.D\(([^)']+)\), \.QN\(q\3\)\);\s*$")


def standin_add_contract(text, tol_ps):
    """an existing bare stand-in netlist (standin_netlist without hold_contract) -> the contract form: every
    `FLOP fK (.CLK(c), .D(<port bit>), .QN(qK));` gets the OT_BHOLD cell between the port bit and D.  Returns
    (text, bits).  Refuses a netlist that is not a pure stand-in (any other cell type) or already has the cell."""
    bh = die_sta.bhold_cell(tol_ps)
    out, n, wires = [], 0, []
    for ln in text.splitlines():
        if "OT_BHOLD_" in ln:
            raise ValueError("stand-in already carries the boundary-hold contract")
        m = _STANDIN_IN.match(ln)
        if m:
            ind, cell, k, ck, d = m.groups()
            out += [f"{ind}{bh} h{k} (.A({d}), .Y(d{k}));", f"{ind}{cell} f{k} (.CLK({ck}), .D(d{k}), .QN(q{k}));"]
            wires.append(f"  wire d{k};")
            n += 1
            continue
        s = ln.strip()
        if s and not re.match(r"(module|input|output|wire|endmodule|\)|//)", s) and not s.startswith(FLOP):
            raise ValueError(f"not a budget stand-in netlist line: {s[:120]}")
        out.append(ln)
    if wires:
        i = next(j for j, ln in enumerate(out) if ln.strip().startswith(FLOP) or ln.strip().startswith(bh))
        out[i:i] = wires
    return "\n".join(out) + "\n", n


# ------------------------------------------------------------------------------------------------------------- kit
def run_sh(step, mem, cpus, cmd):
    return f"""#!/bin/bash
# GENERATED by tools/die_plan/die_trial.py: {step} (heavy: launch through ot-run --mem {mem} --threads {cpus})
D=$(cd $(dirname $0) && pwd)
IMAGE=${{OT_ORFS_IMAGE:-{IMAGE}}}
DK=docker; docker info >/dev/null 2>&1 || DK="sudo docker"
echo "image $IMAGE $($DK image inspect --format '{{{{.Id}}}}' $IMAGE) host $(hostname) start $(date -Is)" > $D/{step}.image.txt
$DK run --rm --name dtrial-{step}-$$ --cpus=${{CPUS:-{cpus}}} --memory=${{MEM:-{mem}}}g --memory-swap=${{MEM:-{mem}}}g -v $D:/work -w /work \\
  -e HUID=$(id -u) -e HGID=$(id -g) $IMAGE bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; {cmd}; rc=\\$?; chown -R \\$HUID:\\$HGID /work; exit \\$rc"
rc=$?
echo "end $(date -Is) exit $rc" >> $D/{step}.image.txt
exit $rc
"""


def write_kit(plan_path, out, views=None, leaf_um=600.0, rep_um=450.0, coarse=0.72, density=0.15, island_sites=None,
              island_margin=ISLAND_MARGIN_UM, full_depth=False, site_legal=False, site_slide=False, regions=None,
              tap_rep_um=None):
    raw = S.load(plan_path)
    P = S.Plan(raw, Path(plan_path))   # plan-relative sidecars (core pins_file of the reset wavefront; as claude/die-proto-1025@bd51e6310)
    plan_dir = Path(plan_path).parent
    out = Path(out)
    for d in ("abstracts", "grt", "clock", "psm", "sta/parts"):
        (out / d).mkdir(parents=True, exist_ok=True)
    meta = dict(plan=str(plan_path), plan_sha256=S.sha256_file(plan_path) if hasattr(S, "sha256_file") else None,
                die=P.name, outline_um=[P.W, P.H], area_mm2=round(P.W * P.H * 1e-6, 2), parts=len(P.parts),
                types=len(P.types), ports=len(P.ports), lanes=len(raw.get("lanes", [])), image=IMAGE)
    import hashlib
    meta["plan_sha256"] = hashlib.sha256(Path(plan_path).read_bytes()).hexdigest()
    # abstracts
    lefs, ab = [], {}
    type_bits = {}
    iw = {}
    if island_sites:     # CLOCK-128-R7 opt-in: plan-computed island windows (absent -> kit unchanged)
        sites = load_island_sites(island_sites)
        iw, irec = island_windows(P, sites, margin=island_margin)
        own = defaultdict(lambda: defaultdict(set))     # type -> instance -> windows holding one of ITS sites
        for r in irec:
            for h in r["parts"]:
                if not h["in_core"]:
                    own[h["type"]][h["part"]].add(tuple(h["rect"]))
        inst_n = defaultdict(int)
        for p_ in P.parts.values():
            inst_n[p_["type"]] += 1
        in_core = [dict(source=r["source"], xy_um=r["xy_um"], part=h["part"], cores=h["in_core"])
                   for r in irec for h in r["parts"] if h["in_core"]]
        meta_iw = dict(sources=[str(x) for x in island_sites], sites=len(sites), margin_um=island_margin,
                       cell_um=list(ISLAND_CELL_UM), snap_um=ISLAND_SNAP_UM, grid_um=list(ISLAND_GRID_UM),
                       pg_cut=list(ISLAND_PG_CUT), types=len(iw), windows=sum(len(v) for v in iw.values()),
                       instance_windows=sum(len(v) * inst_n[k] for k, v in iw.items()),
                       instance_windows_used=sum(len(x) for v in own.values() for x in v.values()),
                       island_in_core=len(in_core), island_in_core_list=in_core[:50],
                       sites_outside_partitions=sum(1 for r in irec if not r["parts"]))
        (out / "island_windows.json").write_text(json.dumps(dict(schema="ot_island_windows/1", meta=meta_iw,
                                                                 windows=iw, sites=irec), indent=1) + "\n")
    for tn, t in sorted(P.types.items()):
        v = Path(views) / tn / f"{t['module']}.lef" if views else None
        if v and v.is_file():
            (out / "abstracts" / v.name).write_text(v.read_text())
            ab[tn] = dict(source="closed view", path=str(v))
        else:
            txt, st = abstract_lef(P, tn, islands=iw.get(tn))
            (out / "abstracts" / f"{t['module']}.lef").write_text(txt)
            ab[tn] = dict(source="plan abstract", **st)
        lefs.append(f"{t['module']}.lef")
        bits = defaultdict(int)
        for bus, bit, *_ in gen_phys.type_pins(P, tn):
            bits[bus] = max(bits[bus], bit + 1)
        type_bits[tn] = dict(bits)
    meta["abstracts"] = ab
    if island_sites:
        meta["island_windows"] = meta_iw
    meta["closed_views"] = sum(1 for a in ab.values() if a["source"] == "closed view")
    meta["hard_cores"] = sum(len(P.types[p["type"]].get("hard_cores", []) or []) for p in P.parts.values())
    meta["hard_cores_with_view"] = sum(ab[p["type"]].get("cores_with_view", 0) for p in P.parts.values())
    # die IO
    io = io_windows(P, plan_dir)
    meta["die_io"] = [dict(name=w["name"], part=w.get("part"), iface=w.get("iface"), rect_um=w["rect_um"],
                           sites=w.get("sites"), signals=w.get("signals"), host=w.get("host", False)) for w in io]
    # clock
    nodes, segs, leaf_legs, cm = clock_kit(P, out / "clock", leaf_um, rep_um, full_depth, site_legal, site_slide,
                                            json.loads(Path(regions).read_text())["part_region"] if regions else None,
                                            tap_rep_um)
    (out / "clock" / "make_tracks.tcl").write_text(gen_phys.make_tracks_tcl(P))
    meta["clock_tree"] = cm
    reserve = reserve_rects(segs, leaf_legs, P)
    # grt
    rv, nft = route_netlist(P, type_bits)
    (out / "grt" / "route.v").write_text(rv)
    (out / "grt" / "tracks.tcl").write_text(coarse_tracks(P, coarse))
    ftf = sorted({t.get("ft_track_frac", 0.25) for t in P.types.values()})
    ca = P.layer_budget.get("cut_avail", {"M8": 0.6, "M9": 0.6})
    adjust = [(L, round(1 - ftf[0], 3)) for L in ("M4", "M5", "M6", "M7")] + \
             [(L, round(1 - ca.get(L, 0.6), 3)) for L in ("M8", "M9")]
    (out / "grt" / "grt.tcl").write_text(grt_tcl(P, out / "grt", coarse, lefs, reserve, adjust))
    meta["grt"] = dict(ft_bits=nft, ft_slot_instances=len(ft_nets(P)), reset_taps=len(P.parts),
                       adjust=dict(adjust), coarse_m123_um=coarse, clock_reserve_rects=len(reserve),
                       pg_stripes=len(pg_stripes(P)))
    bl, br = band_region_adjust(P, dict(adjust).get("M4", 0.75))
    meta["grt"]["die_ft_bands"] = dict(layers=bl, band_rects=len(ft_band_rects(P)), share_strips=len(br),
                                       share_obstructions=len(band_share_obs(P, br)),
                                       transition_layers=list(TRANSITION_LAYERS), transition_keep=TRANSITION_KEEP)
    seam_bits = 0
    chan = 0
    for pid, pr in P.ports.items():
        if S.DIE_PART in (pr["src"]["part"], pr["dst"]["part"]):
            continue
        seam_bits += S.port_pins_count(pr)
        chan += 1 if P.channel_of(pid) else 0
    meta["grt"]["abutted_seam_bits"] = seam_bits
    meta["grt"]["channel_ports"] = chan
    (out / "run_grt.sh").write_text(run_sh("grt", 256, 16, "/usr/bin/time -v openroad -no_init -threads 16 -exit "
                                                         "/work/grt/grt.tcl > /work/grt/grt.log 2>&1; echo EXIT \\$? >> /work/grt/grt.log"))
    # clock runs (3 corners)
    ck = "; ".join(f"CORNER={c} LIBDIR={PLAT}/lib/NLDM /usr/bin/time -v openroad -no_init -exit /work/clock/ctree.tcl "
                   f"> /work/clock/ctree_{c}.log 2>&1" for c in ("TT", "FF"))
    (out / "run_clock.sh").write_text(run_sh("clock", 32, 4, ck).replace("-v $D:/work", "-v $D:/work"))
    # psm
    power = part_power(P, plan_dir, density)
    pv = [f"module {sv(P.name)}_psm ();"] + [f"  {P.types[p['type']]['module']} {sv(n)} ();" for n, p in sorted(P.parts.items())] + ["endmodule"]
    (out / "psm" / "psm.v").write_text("\n".join(pv) + "\n")
    (out / "psm" / "pdn.tcl").write_text(psm_pdn_tcl(P))
    bumps = bump_grid(P, io)
    (out / "psm" / "bumps.tcl").write_text(bumps_tcl(P, bumps))
    (out / "psm" / "power.tcl").write_text("\n".join(f"set_pdnsim_inst_power -inst {sv(n)} -power {w:.6f}"
                                                     for n, w in sorted(power.items())) + "\n")
    (out / "psm" / "psm.tcl").write_text(psm_tcl(P, lefs, power, bumps))
    (out / "psm" / "power.json").write_text(json.dumps(dict(density_w_mm2=density, total_w=round(sum(power.values()), 3),
                                                            parts=power), indent=0) + "\n")
    meta["psm"] = dict(density_w_mm2=density, total_w=round(sum(power.values()), 2), bumps=len(bumps),
                       bumps_vdd=sum(1 for b in bumps if b[0] == "VDD"), bump_pitch_um=150.0,
                       io_windows=len(io), pg=P.die.get("pg", {}).get("grid"))
    (out / "run_psm.sh").write_text(run_sh("psm", 256, 16, "/usr/bin/time -v openroad -no_init -threads 16 -exit "
                                                         "/work/psm/psm.tcl > /work/psm/psm.log 2>&1"))
    # sta stand-ins
    nff = 0
    smod = standin_module_names(P)
    for tn, t in sorted(P.types.items()):
        d = out / "sta" / "parts" / smod[tn]
        d.mkdir(parents=True, exist_ok=True)
        v, k = standin_netlist(P, tn)
        if smod[tn] != t["module"]:
            v = v.replace(f"module {t['module']} (", f"module {smod[tn]} (", 1)
        (d / "6_final.v").write_text(v)
        nff += k * sum(1 for p in P.parts.values() if p["type"] == tn)
    v = retarget_shared_modules(P, gen_rtl.die_top(P, gen_rtl.bus_epochs(P), {}), smod)
    plain = "\n".join(re.sub(r"^endmodule\s*:.*$", "endmodule", ln) for ln in v.splitlines() if not ln.startswith("`"))
    (out / "sta" / "die_top.v").write_text(plain + "\n")
    meta["sta"] = dict(standin_flops=nff, seam_bits=seam_bits,
                       per_type_modules=sorted(tn for tn, m in smod.items() if m != P.types[tn]["module"]))
    for x in ("run_grt.sh", "run_clock.sh", "run_psm.sh"):
        os.chmod(out / x, 0o755)
    (out / "kit.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


# ---------------------------------------------------------------------------------------------------------- reports
def parse_time_v(text):
    r = {}
    m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", text)
    if m:
        r["peak_rss_gb"] = round(int(m.group(1)) / 1048576.0, 2)
    m = re.search(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): ([\d:.]+)", text)
    if m:
        s = 0.0
        for part in m.group(1).split(":"):
            s = s * 60 + float(part)
        r["wall_s"] = round(s, 1)
    return r


def grt_report(d, P):
    import g2
    log = (d / "grt" / "grt.log").read_text(errors="replace") if (d / "grt" / "grt.log").is_file() else ""
    r = g2.parse_grt(log)
    r.update(parse_time_v(log))
    r["marks_s"] = {k: int(v) for k, v in re.findall(r"OT_T (\w+) (\d+)", log)}
    m = re.findall(r"GRT-0\d+\]\s*.*?(\d+)\s*x\s*(\d+)", log)
    gc = re.findall(r"\[INFO GRT-0\d+\] (?:Number of )?(?:gcells|GCells)[^\n]*", log)
    r["grid_lines"] = gc[:4]
    # worst windows from the congestion report (KLayout marker DB): boxes + overflow text
    rpt = d / "grt" / "congestion.rpt"
    wins = []
    if rpt.is_file():
        txt = rpt.read_text(errors="replace")
        for m in re.finditer(r"box: \(([-\d.]+),([-\d.]+);([-\d.]+),([-\d.]+)\)(.*?)</", txt, re.S):
            wins.append((float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)), m.group(5)[:200]))
        r["congestion_items"] = len(wins)
        cnt = defaultdict(int)
        for x0, y0, x1, y1, _ in wins:
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            for n in P.parts:
                a, b, c, e = P.rect(n)
                if a <= cx < c and b <= cy < e:
                    cnt[n] += 1
                    break
        r["congestion_by_part"] = dict(sorted(cnt.items(), key=lambda kv: -kv[1])[:30])
        r["congestion_sample"] = [dict(box=w[:4], text=re.sub(r"\s+", " ", w[4]).strip()) for w in wins[:20]]
    r["exit"] = (re.findall(r"EXIT (\d+)", log) or [None])[-1]
    return r


def clock_report(d, P):
    tree = json.loads((d / "clock" / "tree.json").read_text())
    nodes = {int(k): v for k, v in tree["nodes"].items()}
    node_buf = {int(k): v for k, v in tree["node_buf"].items()}
    buf_node = {v: k for k, v in node_buf.items()}
    res = dict(meta=tree["meta"], corners={})
    taps = tree["taps"]
    tap_by = {(t["part"], t["tap"]): t for t in taps}
    part_taps = defaultdict(list)
    for t in taps:
        part_taps[t["part"]].append(t)

    def anc(i):
        out = []
        while i is not None:
            out.append(i)
            i = nodes[i]["parent"]
        return out
    # seam pairs: every abutted port -> the launch tap (src part) and capture tap (dst part) nearest the window centre
    pairs = []
    for pid, pr in P.ports.items():
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if S.DIE_PART in (a, b):
            continue
        pins = P.port_pins(pid)
        cs = [c for _, _, c in pins]
        cmid = (min(cs) + max(cs)) / 2
        ra = P.rect(a)
        f = pr["face"]
        if f in "EW":
            pt = ((ra[2] if f == "E" else ra[0]), cmid)
        else:
            pt = (cmid, (ra[3] if f == "N" else ra[1]))
        ta = min(part_taps[a], key=lambda t: abs(t["xy"][0] - pt[0]) + abs(t["xy"][1] - pt[1]))
        tb = min(part_taps[b], key=lambda t: abs(t["xy"][0] - pt[0]) + abs(t["xy"][1] - pt[1]))
        pairs.append((pid, ta, tb))
    for corner in ("SS", "TT", "FF"):
        f = d / "clock" / f"arr_{corner}.txt"
        if not f.is_file():
            continue
        tarr, narr = {}, {}
        for ln in f.read_text().splitlines():
            x = ln.split()
            if len(x) < 4:
                continue
            try:
                vmax, vmin = float(x[2]), float(x[3])
            except ValueError:
                continue
            if x[0] == "T":
                tarr[x[1]] = vmax          # max arrival (= period - slack_max)
            elif x[0] == "N":
                narr[buf_node.get(x[1])] = vmax
        if not tarr:
            continue
        ins = sorted(tarr.values())
        cr = dict(insertion_max_ps=round(ins[-1], 1), insertion_min_ps=round(ins[0], 1),
                  global_skew_ps=round(ins[-1] - ins[0], 1), taps=len(ins))
        # per-partition tap spread
        sp = []
        for n, tl in part_taps.items():
            v = [tarr[t["port"]] for t in tl if t["port"] in tarr]
            if v:
                sp.append(max(v) - min(v))
        cr["part_tap_spread_ps_max"] = round(max(sp), 1) if sp else None
        rows = []
        for pid, ta, tb in pairs:
            if ta["port"] not in tarr or tb["port"] not in tarr:
                continue
            A, B = anc(ta["node"]), anc(tb["node"])
            sb = set(B)
            lca = next(i for i in A if i in sb)
            la = narr.get(lca, 0.0)
            # node arrival is at the node buffer OUTPUT; taps below it
            ua, ub = tarr[ta["port"]] - la, tarr[tb["port"]] - la
            nom = tarr[tb["port"]] - tarr[ta["port"]]
            row = dict(port=pid, launch=f"{ta['part']}/{ta['tap']}", capture=f"{tb['part']}/{tb['tap']}",
                       nominal_ps=round(nom, 1), uncommon_launch_ps=round(ua, 1), uncommon_capture_ps=round(ub, 1),
                       lca_level=nodes[lca]["level"])
            for k in OCV:
                row[f"ocv{int(k * 100)}_ps"] = round(max(abs(ub * (1 - k) - ua * (1 + k)), abs(ub * (1 + k) - ua * (1 - k))), 1)
            rows.append(row)
        if rows:
            cr["seam_pairs"] = len(rows)
            cr["seam_nominal_abs_max_ps"] = max(abs(r["nominal_ps"]) for r in rows)
            for k in OCV:
                key = f"ocv{int(k * 100)}_ps"
                v = sorted(r[key] for r in rows)
                cr[f"seam_{key}_max"] = v[-1]
                cr[f"seam_{key}_p90"] = v[int(0.9 * (len(v) - 1))]
                cr[f"seam_{key}_over80"] = sum(1 for x in v if x > 80.0)
            cr["all_seams"] = rows
            cr["worst_seams"] = sorted(rows, key=lambda r: -r[f"ocv{int(OCV[-1] * 100)}_ps"])[:15]
            cr["worst_nominal"] = sorted(rows, key=lambda r: -abs(r["nominal_ps"]))[:10]
        log = d / "clock" / f"ctree_{corner}.log"
        if log.is_file():
            cr.update(parse_time_v(log.read_text(errors="replace")))
        res["corners"][corner] = cr
        # die_sta spine file: per tap offset = arrival - min arrival
        mn = ins[0]
        br = dict(model="trial-htree", corner=corner, parts={})
        for t in taps:
            if t["port"] in tarr:
                br["parts"].setdefault(t["part"], dict(taps={}))["taps"][t["tap"]] = dict(
                    offset_ps=round(tarr[t["port"]] - mn, 2), arrival_ps=round(tarr[t["port"]], 2))
        (d / "sta" / f"spine_{corner}.json").write_text(json.dumps(br) + "\n")
    return res


def psm_report(d):
    log = d / "psm" / "psm.log"
    r = {}
    if not log.is_file():
        return r
    txt = log.read_text(errors="replace")
    r.update(parse_time_v(txt))
    r["marks_s"] = {k: int(v) for k, v in re.findall(r"OT_T (\w+) (\d+)", txt)}
    for k, pat in (("worst_ir_drop_mv", r"Worstcase IR drop\s*:\s*([\d.e+-]+)\s*(\w*V)"),
                   ("avg_ir_drop_mv", r"Average IR drop\s*:\s*([\d.e+-]+)\s*(\w*V)"),
                   ("worst_voltage", r"Worstcase voltage\s*:\s*([\d.e+-]+)\s*(\w*V)"),
                   ("avg_voltage", r"Average voltage\s*:\s*([\d.e+-]+)\s*(\w*V)")):
        m = re.findall(pat, txt)
        if m:
            v, u = m[-1]
            f = dict(V=1.0, mV=1e-3, uV=1e-6).get(u, 1.0)
            r[k] = round(float(v) * f * (1e3 if k.endswith("_mv") else 1.0), 3)
    r["status"] = "OK" if "OT_PSM_OK" in txt else ("FAIL" if "OT_PSM_FAIL" in txt else "NOT RUN")
    r["pg_check"] = re.findall(r"OT_PG_CHECK_(OK|FAIL) (\w+)", txt)
    r["errors"] = sorted(set(re.findall(r"\[ERROR ([A-Z]+-\d+)\]", txt)))
    return r


def cmd_report(a):
    d = Path(a.dir)
    kit = json.loads((d / "kit.json").read_text())
    P = S.Plan(S.load(kit["plan"] if Path(kit["plan"]).is_file() else a.plan))
    res = dict(kit=kit)
    if (d / "grt" / "grt.log").is_file():
        res["grt"] = grt_report(d, P)
    if (d / "clock" / "tree.json").is_file():
        res["clock"] = clock_report(d, P)
    res["psm"] = psm_report(d)
    for c in ("SS", "FF", "TT"):
        f = d / "sta" / f"run_{c}" / "die_sta.json"
        if f.is_file():
            res.setdefault("sta", {})[c] = json.loads(f.read_text())
    (d / "trial.json").write_text(json.dumps(res, indent=1) + "\n")
    return res


# ---------------------------------------------------------------------------------------------------------- renders
def _part_patches(ax, P, alpha=0.25, edge="0.6", label=False):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    types = sorted(P.types)
    cmap = plt.get_cmap("tab20")
    col = {t: cmap(i % 20) for i, t in enumerate(types)}
    for n, p in P.parts.items():
        x0, y0, x1, y1 = P.rect(n)
        ax.add_patch(Rectangle((x0 / 1000, y0 / 1000), (x1 - x0) / 1000, (y1 - y0) / 1000, facecolor=col[p["type"]],
                               alpha=alpha, edgecolor=edge, lw=0.3))
        if label:
            ax.text((x0 + x1) / 2000, (y0 + y1) / 2000, n, fontsize=2.5, ha="center", va="center")


def core_rects_die(P):
    """[(layer_top, x0, y0, x1, y1)] every planned hard core in die coordinates."""
    out = []
    for n, p in P.parts.items():
        for x0, y0, x1, y1, tl, _, _ in core_obs(P.types[p["type"]]):
            a = P.to_die(n, (x0, y0))
            b = P.to_die(n, (x1, y1))
            out.append((tl, min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])))
    return out


def guide_maps(P, guide, win_um=27.0, adjust=None):
    """per-window routing utilisation from the GRT guides: demand (track x gcell) / capacity (tracks across a gcell
    x (1 - layer adjustment) minus planned hard-core OBS on M4.. and die PG on M8/M9).  -> {layer: 2D array}, meta"""
    import numpy as np
    dbu = 1000.0
    nx, ny = int(math.ceil(P.W / win_um)), int(math.ceil(P.H / win_um))
    dem = {L: np.zeros((ny, nx)) for L in ("M4", "M5", "M6", "M7", "M8", "M9")}
    gc = None
    nets = 0
    with open(guide) as f:
        for ln in f:
            x = ln.split()
            if len(x) == 5:
                L = x[4]
                if L not in dem:
                    continue
                x0, y0, x1, y1 = (int(v) / dbu for v in x[:4])
                if gc is None:
                    gc = min(x1 - x0, y1 - y0)
                hdir = P.layers[L]["dir"] == "H"
                if hdir:
                    a, b, c = x0, x1, (y0 + y1) / 2
                    if b - a <= gc * 1.01:
                        continue        # via-only box (pin access)
                    r = min(int(c / win_um), ny - 1)
                    i0, i1 = int(a / win_um), min(int((b - 1e-6) / win_um), nx - 1)
                    for i in range(i0, i1 + 1):
                        ov = min(b, (i + 1) * win_um) - max(a, i * win_um)
                        dem[L][r, i] += ov / gc
                else:
                    a, b, c = y0, y1, (x0 + x1) / 2
                    if b - a <= gc * 1.01:
                        continue
                    col = min(int(c / win_um), nx - 1)
                    i0, i1 = int(a / win_um), min(int((b - 1e-6) / win_um), ny - 1)
                    for i in range(i0, i1 + 1):
                        ov = min(b, (i + 1) * win_um) - max(a, i * win_um)
                        dem[L][i, col] += ov / gc
            elif len(x) == 1 and x[0] not in "()":
                nets += 1
    gc = gc or 2.7
    gpw = (win_um / gc) ** 2                       # gcells per window
    block = {L: np.zeros((ny, nx)) for L in dem}
    for tl, x0, y0, x1, y1 in core_rects_die(P):
        for L in dem:
            if int(L[1:]) > int(tl[1:]):
                continue
            i0, i1 = int(x0 / win_um), min(int(x1 / win_um), nx - 1)
            j0, j1 = int(y0 / win_um), min(int(y1 / win_um), ny - 1)
            for j in range(j0, j1 + 1):
                for i in range(i0, i1 + 1):
                    ov = max(0.0, min(x1, (i + 1) * win_um) - max(x0, i * win_um)) * \
                         max(0.0, min(y1, (j + 1) * win_um) - max(y0, j * win_um))
                    block[L][j, i] += ov / win_um ** 2
    util = {}
    pgf = 2 * 0.48 / 8.64
    for L in dem:
        tr = gc / P.layers[L]["pitch_um"] * (1 - (adjust or {}).get(L, 0.0))
        free = np.clip(1 - block[L], 0, 1) * (1 - (pgf if L in ("M8", "M9") else 0.0))
        cap = tr * gpw * free
        with np.errstate(divide="ignore", invalid="ignore"):
            # windows mostly covered by hard-core OBS (< 25 % free) are left out: their gcell-edge demand vs a
            # sliver of capacity is a window-quantisation artefact (GRT itself routes per gcell)
            u = np.where(free >= 0.25, dem[L] / np.maximum(cap, 1e-9), 0.0)
        util[L] = u
    return util, dict(win_um=win_um, gcell_um=gc, nets=nets, nx=nx, ny=ny)


def render_all(d, P, plan_path):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from matplotlib.collections import LineCollection
    d = Path(d)
    rd = d / "render"
    rd.mkdir(exist_ok=True)
    kit = json.loads((d / "kit.json").read_text())
    W, H = P.W / 1000, P.H / 1000
    figw = 16
    figh = figw * H / W + 1.2
    out = {}
    # (1) floorplan: types, hard cores, die IO windows, ft lane bundles (in-window -> out-window, width ~ bits)
    fig, ax = plt.subplots(figsize=(figw, figh), dpi=150)
    _part_patches(ax, P, label=True)
    for tl, x0, y0, x1, y1 in core_rects_die(P):
        ax.add_patch(Rectangle((x0 / 1000, y0 / 1000), (x1 - x0) / 1000, (y1 - y0) / 1000, facecolor="0.35",
                               edgecolor="none", alpha=0.6))
    for w in kit.get("die_io", []):
        x0, y0, x1, y1 = w["rect_um"]
        ax.add_patch(Rectangle((x0 / 1000, y0 / 1000), (x1 - x0) / 1000, (y1 - y0) / 1000, fill=False,
                               edgecolor="red" if w.get("host") else "magenta", lw=1.2, ls="--"))
        ax.text(x0 / 1000, y1 / 1000, w["name"].replace("io_", "").replace("_u_phy", ""), fontsize=4, color="m")
    segs, lw = [], []
    for n, p in P.parts.items():
        for s in P.types[p["type"]].get("ft_slots", []) or []:
            pins = [q for q in gen_phys.type_pins(P, p["type"]) if q[0] in (s["name"] + "_i", s["name"] + "_o")]
            if not pins:
                continue
            ins = [P.to_die(n, (q[3], q[4])) for q in pins if q[0].endswith("_i")]
            ous = [P.to_die(n, (q[3], q[4])) for q in pins if q[0].endswith("_o")]
            if ins and ous:
                a = (sum(v[0] for v in ins) / len(ins) / 1000, sum(v[1] for v in ins) / len(ins) / 1000)
                b = (sum(v[0] for v in ous) / len(ous) / 1000, sum(v[1] for v in ous) / len(ous) / 1000)
                segs.append([a, b])
                lw.append(0.3 + 2.5 * min(1.0, s["width"] / 2000))
    ax.add_collection(LineCollection(segs, linewidths=lw, colors="tab:blue", alpha=0.7))
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal")
    ax.set_title(f"{P.name} trial die: {len(P.parts)} partitions / {len(P.types)} types, hard cores (grey), "
                 f"die IO windows (magenta, red = host), ft slot bundles (blue, width ~ bits)  [mm]", fontsize=9)
    fig.tight_layout(); fig.savefig(rd / "floorplan_ft.png"); plt.close(fig)
    out["floorplan_ft"] = str(rd / "floorplan_ft.png")
    # (2) clock tree: legs by level, taps by SS arrival, seam pairs over 80 ps (3% OCV) in red
    tf = d / "clock" / "tree.json"
    if tf.is_file():
        tree = json.loads(tf.read_text())
        nodes = {int(k): v for k, v in tree["nodes"].items()}
        fig, ax = plt.subplots(figsize=(figw, figh), dpi=150)
        _part_patches(ax, P, alpha=0.12)
        segs, cols = [], []
        cm = plt.get_cmap("viridis")
        mx = max(n["level"] for n in nodes.values()) or 1
        for i, n in nodes.items():
            if n["parent"] is not None:
                p = nodes[n["parent"]]
                segs.append([(p["x"] / 1000, p["y"] / 1000), (n["x"] / 1000, n["y"] / 1000)])
                cols.append(cm(n["level"] / mx))
        ax.add_collection(LineCollection(segs, colors=cols, linewidths=0.8))
        arr = {}
        af = d / "clock" / "arr_SS.txt"
        if af.is_file():
            for ln in af.read_text().splitlines():
                x = ln.split()
                if x and x[0] == "T":
                    arr[x[1]] = float(x[2])
        xs = [t["xy"][0] / 1000 for t in tree["taps"]]
        ys = [t["xy"][1] / 1000 for t in tree["taps"]]
        cs = [arr.get(t["port"], float("nan")) for t in tree["taps"]]
        sc = ax.scatter(xs, ys, c=cs, s=3, cmap="plasma")
        fig.colorbar(sc, ax=ax, fraction=0.025, label="SS tap arrival (ps)")
        cr = None
        tj = d / "trial.json"
        if tj.is_file():
            cr = json.loads(tj.read_text()).get("clock", {}).get("corners", {}).get("SS")
        if cr is None:
            try:
                cr = clock_report(d, P)["corners"].get("SS")
            except Exception:
                cr = None
        tap_xy = {f"{t['part']}/{t['tap']}": t["xy"] for t in tree["taps"]}
        if cr:
            bad = [r for r in cr.get("all_seams", cr.get("worst_seams", [])) if r.get("ocv3_ps", 0) > 80]
            for r in bad:
                a, b = tap_xy[r["launch"]], tap_xy[r["capture"]]
                ax.plot([a[0] / 1000, b[0] / 1000], [a[1] / 1000, b[1] / 1000], color="red", lw=1.5)
        ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal")
        ax.set_title(f"{P.name} die clock H-tree ({tree['meta']['taps']} taps, {tree['meta']['repeaters']} repeaters, "
                     f"leaf {tree['meta']['leaf_um']:g} um); red = seam tap pairs > 80 ps skew at 3% OCV  [mm]", fontsize=9)
        fig.tight_layout(); fig.savefig(rd / "clock_tree.png"); plt.close(fig)
        out["clock_tree"] = str(rd / "clock_tree.png")
    # (3) congestion from the GRT guides
    gf = d / "grt" / "route.guide"
    if gf.is_file():
        adj = kit["grt"]["adjust"]
        util, gm = guide_maps(P, gf, adjust=adj)
        np.savez_compressed(rd / "congestion.npz", **util)
        fig, axs = plt.subplots(1, 2, figsize=(figw, figh / 2 + 0.6), dpi=150)
        for ax, Ls, name in ((axs[0], ("M4", "M5", "M6", "M7"), "M4-M7 (ft share 25%)"),
                             (axs[1], ("M8", "M9"), "M8/M9 (60% of PG-free)")):
            m = np.max(np.stack([util[L] for L in Ls]), axis=0)
            im = ax.imshow(m, origin="lower", extent=(0, W, 0, H), cmap="inferno", vmin=0, vmax=1.2)
            _part_patches(ax, P, alpha=0.0, edge="0.5")
            ax.set_title(f"{name}: max window utilisation (win {gm['win_um']:g} um), peak {m.max():.2f}", fontsize=8)
            fig.colorbar(im, ax=ax, fraction=0.03)
        fig.tight_layout(); fig.savefig(rd / "congestion.png"); plt.close(fig)
        out["congestion"] = str(rd / "congestion.png")
        stats = {}
        for L, u in util.items():
            flat = u[u > 0]
            j, i = np.unravel_index(np.argmax(u), u.shape)
            stats[L] = dict(peak=round(float(u.max()), 3), p99=round(float(np.percentile(flat, 99)), 3) if flat.size else 0,
                            windows_over_1=int((u > 1.0).sum()), windows_over_0p8=int((u > 0.8).sum()),
                            peak_xy_um=[round((i + 0.5) * gm["win_um"], 1), round((j + 0.5) * gm["win_um"], 1)],
                            peak_part=next((n for n in P.parts if P.rect(n)[0] <= (i + .5) * gm["win_um"] < P.rect(n)[2]
                                            and P.rect(n)[1] <= (j + .5) * gm["win_um"] < P.rect(n)[3]), None))
        # worst windows overall (any layer)
        allw = []
        for L, u in util.items():
            idx = np.argsort(u, axis=None)[-12:]
            for k in idx:
                j, i = np.unravel_index(k, u.shape)
                x, y = (i + 0.5) * gm["win_um"], (j + 0.5) * gm["win_um"]
                allw.append(dict(layer=L, util=round(float(u[j, i]), 3), xy_um=[round(x, 1), round(y, 1)],
                                 part=next((n for n in P.parts if P.rect(n)[0] <= x < P.rect(n)[2] and P.rect(n)[1] <= y < P.rect(n)[3]), None)))
        allw.sort(key=lambda r: -r["util"])
        (rd / "congestion.json").write_text(json.dumps(dict(meta=gm, layers=stats, worst=allw[:30]), indent=1) + "\n")
    # (4) IR map
    vf = d / "psm" / "ir_VDD.csv"
    if vf.is_file():
        xs, ys, vs = [], [], []
        for ln in vf.read_text().splitlines()[1:]:
            x = ln.replace(",", " ").split()
            try:
                xs.append(float(x[0])); ys.append(float(x[1])); vs.append(float(x[-1]))
            except (ValueError, IndexError):
                continue
        if vs:
            xs, ys, vs = np.array(xs), np.array(ys), np.array(vs)
            if xs.max() > P.W * 2:        # dbu
                xs, ys = xs / 1000.0, ys / 1000.0
            vdd = float(vs.max()) if vs.max() < 1.5 else 0.7
            nb = 400
            gx = np.clip((xs / P.W * nb).astype(int), 0, nb - 1)
            gy = np.clip((ys / P.H * int(nb * H / W)).astype(int), 0, int(nb * H / W) - 1)
            m = np.full((int(nb * H / W), nb), np.nan)
            drop = (0.7 - vs) * 1000.0
            for a, b, v in zip(gy, gx, drop):
                if np.isnan(m[a, b]) or v > m[a, b]:
                    m[a, b] = v
            fig, ax = plt.subplots(figsize=(figw, figh), dpi=150)
            im = ax.imshow(m, origin="lower", extent=(0, W, 0, H), cmap="magma_r")
            _part_patches(ax, P, alpha=0.0, edge="0.6")
            for w in kit.get("die_io", []):
                x0, y0, x1, y1 = w["rect_um"]
                ax.add_patch(Rectangle((x0 / 1000, y0 / 1000), (x1 - x0) / 1000, (y1 - y0) / 1000, fill=False,
                                       edgecolor="cyan", lw=1.0, ls="--"))
            fig.colorbar(im, ax=ax, fraction=0.025, label="VDD IR drop (mV)")
            ax.set_title(f"{P.name} VDD IR drop (PDNSim, {kit['psm']['density_w_mm2']} W/mm2 uniform = "
                         f"{kit['psm']['total_w']} W, C4 150 um bumps outside IO windows), worst {np.nanmax(m):.1f} mV",
                         fontsize=9)
            fig.tight_layout(); fig.savefig(rd / "ir_vdd.png"); plt.close(fig)
            out["ir"] = str(rd / "ir_vdd.png")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("kit")
    k.add_argument("plan")
    k.add_argument("--out", required=True)
    k.add_argument("--views")
    k.add_argument("--leaf-um", type=float, default=600.0)
    k.add_argument("--rep-um", type=float, default=450.0)
    k.add_argument("--htree-full-depth", action="store_true",
                   help="opt-in: bisect single-tap regions to --leaf-um (equal-depth leaves; FALLBACK-HEAD one-entry plans)")
    k.add_argument("--tree-site-legal", action="store_true",
                   help="opt-in: site every tree buffer/repeater in a partition, off hard cores and PHY domains (12.2a1)")
    k.add_argument("--tree-site-slide", action="store_true",
                   help="opt-in: like --tree-site-legal, but each buffer slides back along its own incoming leg "
                        "(root->entry Manhattan lengths unchanged = equal length kept by construction)")
    k.add_argument("--region-trees", help="fallback regions.json (part_region): die reference tree to one root per "
                   "region + equal-depth local tree per region (FALLBACK-S81-2, opt-in)")
    k.add_argument("--tap-rep-um", type=float, help="opt-in: repeat leaf-to-tap legs too, refusing any final legal-site hop above this reach")
    k.add_argument("--coarse-um", type=float, default=0.72)
    k.add_argument("--density", type=float, default=0.15, help="die power density W/mm2 for PDNSim")
    k.add_argument("--island-sites", nargs="+", help="CLOCK-128-R7 opt-in: die_tree_plan.json / ot_clock_sites/1 / "
                   "mesh.json (derived trunk sites): open plan-computed island windows (no M1-M3 OBS, M7 PG cut) in "
                   "every partition abstract, identical per type; island_windows.json lists them")
    k.add_argument("--island-margin-um", type=float, default=ISLAND_MARGIN_UM)
    r = sub.add_parser("report")
    r.add_argument("dir")
    r.add_argument("--plan")
    g = sub.add_parser("render")
    g.add_argument("dir")
    g.add_argument("--plan")
    c = sub.add_parser("clock")
    c.add_argument("dir")
    c.add_argument("--plan")
    h = sub.add_parser("standin-contract", help="copy a die_sta PARTS dir of bare stand-ins with the boundary-hold "
                                                "contract cell added (re-time an existing trial without a new kit)")
    h.add_argument("parts")
    h.add_argument("--out", required=True)
    h.add_argument("--tol-ps", type=float, default=float(S.DEFAULT_CLOCK["insertion_tol_ps"]))
    j = sub.add_parser("standins", help="write the die_sta PARTS stand-ins of every plan type (contract form: "
                                         "boundary-hold + clock-latency cells) without a full kit")
    j.add_argument("plan")
    j.add_argument("--out", required=True)
    j.add_argument("--no-clock-contract", action="store_true", help="legacy: face flops load the tap port directly")
    j.add_argument("--top", help="also write the matching die_top.v (shared-module types re-pointed to their stand-ins)")
    a = ap.parse_args(argv)
    if a.cmd == "standins":
        P = S.Plan(S.load(a.plan), Path(a.plan))
        smod = standin_module_names(P)
        tot = {}
        for tn, t in sorted(P.types.items()):
            d = Path(a.out) / smod[tn]
            d.mkdir(parents=True, exist_ok=True)
            v, k = standin_netlist(P, tn, clock_contract=not a.no_clock_contract)
            if smod[tn] != t["module"]:
                v = v.replace(f"module {t['module']} (", f"module {smod[tn]} (", 1)
            (d / "6_final.v").write_text(v)
            tot[smod[tn]] = k
        shared = sorted(tn for tn, m in smod.items() if m != P.types[tn]["module"])
        if a.top:   # per-type stand-in modules need the matching die top (instances re-pointed)
            v = retarget_shared_modules(P, gen_rtl.die_top(P, gen_rtl.bus_epochs(P), {}), smod)
            Path(a.top).write_text("\n".join(re.sub(r"^endmodule\s*:.*$", "endmodule", ln)
                                             for ln in v.splitlines() if not ln.startswith("`")) + "\n")
        elif shared:
            print(f"WARNING: {len(shared)} shared-module types got per-type stand-in modules; pass --top to write "
                  "the matching die_top.v (an old die top would instantiate the bare module name)", file=sys.stderr)
        print(json.dumps(dict(types=len(tot), face_flops=sum(tot.values()), per_type_modules=shared,
                              clock_contract=not a.no_clock_contract), indent=1))
        return 0
    if a.cmd == "standin-contract":
        tot = {}
        for v in sorted(Path(a.parts).glob("*/6_final.v")):
            t, n = standin_add_contract(v.read_text(), a.tol_ps)
            d = Path(a.out) / v.parent.name
            d.mkdir(parents=True, exist_ok=True)
            (d / "6_final.v").write_text(t)
            tot[v.parent.name] = n
        print(json.dumps(dict(cell=die_sta.bhold_cell(a.tol_ps), types=len(tot), input_bits=sum(tot.values())), indent=1))
        return 0
    if a.cmd == "kit":
        m = write_kit(a.plan, a.out, a.views, a.leaf_um, a.rep_um, a.coarse_um, a.density, a.island_sites,
                      a.island_margin_um, full_depth=a.htree_full_depth, site_legal=a.tree_site_legal,
                      site_slide=a.tree_site_slide, regions=a.region_trees, tap_rep_um=a.tap_rep_um)
        print(json.dumps({k: m[k] for k in ("die", "parts", "types", "closed_views", "hard_cores", "clock_tree", "grt",
                                             "psm", "sta")}, indent=1))
    elif a.cmd == "report":
        res = cmd_report(a)
        print(json.dumps({k: v for k, v in res.items() if k != "kit"}, indent=1)[:6000])
    elif a.cmd == "render":
        d = Path(a.dir)
        kit = json.loads((d / "kit.json").read_text())
        P = S.Plan(S.load(a.plan or kit["plan"]))
        print(json.dumps(render_all(d, P, a.plan or kit["plan"]), indent=1))
    elif a.cmd == "clock":
        d = Path(a.dir)
        kit = json.loads((d / "kit.json").read_text())
        P = S.Plan(S.load(a.plan or kit["plan"]))
        print(json.dumps(clock_report(d, P), indent=1)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
