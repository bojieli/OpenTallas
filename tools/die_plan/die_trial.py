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
import collections
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
# DIE-QC-11 opt-in --clock-cell inv: clock inverter with the BUFx24 footprint (1.62 x 0.27 um, same legal sites), so an
# inverter tree cancels the rise/fall delay asymmetry stage by stage (measured on QC trial8 BUF-only: fall-rise 3.8 ps
# per stage TT, 652 ps at 165 stages = duty 1.28 -> the low phase vanishes)
CLK_INV = "CKINVDCx16_ASAP7_75t_R"
# --clock-cell inv2 (DIE-QC-11): every leg has an EVEN number of inverter stages (priced in leg_ps / snake chains), plus a
# 2-stage root, so every node and tap has true polarity by construction (no tap parity inverters, no parity skew)
EVEN_LEGS = False
FLOP = "DFFHQNx1_ASAP7_75t_R"
NDR_TRACKS = 5                       # clock wire 2W2S + a shield each side (hbm_arch clock_htree.py)
TAP_LOAD_FF = 3.0                    # partition tap buffer input (ASSUMED: BUFx24 A ~ 2-3 fF)
OCV = (0.03, 0.05)                   # flat clock OCV derates reported (ASSUMED; no project OCV table)
CORNER_LIB = {"SS": "SS", "TT": "TT", "FF": "FF"}
# M8 / M9 setRC (ASAP7 platform setRC.tcl, kohm / fF per um); clock NDR 2W2S: R / 2, C x 1.1 (ASSUMED)
WIRE_R = (8.44765e-3 + 8.89556e-3) / 2 / 2
WIRE_C = (1.03962e-1 + 9.28446e-2) / 2 * 1.1
# DIE-QC-3 opt-in --clock-rc 1x: the die clock is routed at 1x width (no NDR; HEAD/KV/QC recipe), so the model RC is the
# plain ASAP7 platform setRC M8/M9 mean (DIE-QC-2 measured routed ~334 ps/mm vs 199 ps/mm with the NDR model above)
WIRE_RC_1X = ((8.44765e-3 + 8.89556e-3) / 2, (1.03962e-1 + 9.28446e-2) / 2)


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
        if isinstance(d.get("lattice"), dict) and d["lattice"].get("cell_sites") is not None:
            for name, site in d["lattice"]["cell_sites"].items():
                out.append((tuple(site["xy_um"]), f"{tag}:cell:{name}"))
        elif isinstance(d.get("lattice"), dict):
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


def abstract_lef(P, tn, slots_only_pins=False, islands=None, module_name=None, landing_infra=False):
    """partition abstract (see module doc).  Returns (lef text, stats).  islands (CLOCK-128-R7, opt-in): type-frame
    island windows: no M1-M3 OBS and no ISLAND_PG_CUT PG stripe inside them."""
    t = P.types[tn]
    w, h = t["outline_um"]
    module_name = module_name or t["module"]
    top = P.layer_budget["partition_signal_max"]
    L = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {module_name}", "  CLASS BLOCK ;",
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
    if landing_infra:
        import landing_route
        for p in landing_route.scalar_pins(P, tn):
            x,y = p['xy_um']
            L += pin(p['name'], 'INPUT' if p['dir']=='in' else 'OUTPUT',
                     'CLOCK' if p['kind']=='clock' else 'SIGNAL',
                     [(p['layer'], x-.04, y-.216, x+.04, y+.216)])
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
    L += ["  END", f"END {module_name}", "END LIBRARY", ""]
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
        # Declared die channels are top-owned clock/reset placement space.
        # A strip recut can free the old clock sites outside all new partition
        # outlines. Keep those sites legal; core and PHY exclusions below still
        # apply, including wherever a channel rectangle crosses either one.
        self.parts.extend(tuple(ch["rect_um"]) for ch in P.die.get("channels", []) or []
                          if ch.get("rect_um"))
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
        # DIE-S81-16: bucket index of the partition rects (built on first use; a rect that contains q lies in q's bucket),
        # same boolean as the linear scan over every partition, which was ~70 % of the merge-mode DME runtime (snake_leg)
        pi = self.__dict__.get("_pidx")
        if pi is None or self.__dict__.get("_pidx_n") != len(self.parts):
            pi = {}
            for r in self.parts:
                for i in range(int(r[0] // self.b), int(r[2] // self.b) + 1):
                    for j in range(int(r[1] // self.b), int(r[3] // self.b) + 1):
                        pi.setdefault((i, j), []).append(r)
            self._pidx, self._pidx_n = pi, len(self.parts)
        return any(r[0] + m <= q[0] <= r[2] - m and r[1] + m <= q[1] <= r[3] - m
                   for r in pi.get((int(q[0] // self.b), int(q[1] // self.b)), ()))

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


def balance_legalize(nodes, site, radius_um=800.0, step=1.08, tol_um=2.0, select=None, extra_wire_w=0.1, skip_regions=None):
    """DIE-KV-3 (link_htree + --tree-site-slide/--tree-site-legal): legal sites for the region H-tree buffers that KEEP the
    tree balanced.  The feed-leg slide (sliding a branch node back along its incoming leg) lengthens one child leg and
    shortens the other when the split axis is collinear with that leg (KV sys_c: +800 um / 490 ps), so region H-tree nodes
    (rib nodes + region roots) are placed bottom-up as zero-skew (DME-style, Manhattan) merge points instead: a leaf sits
    on the legal site nearest its ideal point; a node's subtree wire S = leg + S(kid) (leaf: mean last-mile to its taps);
    a two-kid node takes the legal point nearest its ideal point on the locus |P-C1| + S1 = |P-C2| + S2 (scanned on
    rows/columns through the ideal point within radius_um).  Geometry only, no timing value, no pads/trims/detours.
    Returns stats (moved, merge points off-balance > tol_um and their worst imbalance).
    select (DIE-QC-3 opt-in, --slice-balance): node ids to process instead of the link_htree rib/region-root set; then
    every selected kid counts (also region roots), a non-merge node keeps its current legal site, and a fixed node on a
    plan spine column (spine == 'column') only moves ALONG its column, between its two kids (the column is legal); a merge
    point is the legal candidate (locus points + first legal point on each axis ray + current site) with the least
    imbalance_um + extra_wire_w x added wire (a locus point 600 um away behind a core is not worth 20 um of imbalance)."""
    if select is None:
        H = sorted((i for i, n in nodes.items() if n.get("rib") is not None or n.get("region_root") is not None), reverse=True)
        if skip_regions:    # DIE-QC-4 --region-dme-only: those region roots carry a DME tree instead (attach_region_dme)
            H = [i for i in H if nodes[i].get("region_root") not in skip_regions]
    else:
        H = sorted(select, reverse=True)
    Hs = set(H)
    S = {}
    st = dict(nodes=len(H), moved=0, unbalanced=0, worst_imbalance_um=0.0)
    md = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
    for i in H:
        nd = nodes[i]
        ideal = tuple(nd["req_xy"])
        kids = [k for k in nd["kids"] if k in Hs and (select is not None or nodes[k].get("region_root") is None)]
        colnode = (select is not None and nd.get("spine") == "column" and len(kids) == 2
                   and abs(nodes[kids[0]]["x"] - nd["x"]) < 1e-6 and abs(nodes[kids[1]]["x"] - nd["x"]) < 1e-6)
        if select is not None and nd.get("fixed") and not colnode:
            best = (nd["x"], nd["y"])
            S[i] = max([md(best, (nodes[k]["x"], nodes[k]["y"])) + S[k] for k in kids], default=0.0)
            continue
        if len(kids) == 2:
            (c1, c2) = [(nodes[k]["x"], nodes[k]["y"]) for k in kids]
            s1, s2 = S[kids[0]], S[kids[1]]
            dl = s2 - s1
            best = None
            if colnode:             # along the column only: y with |y-y1| + S1 = |y-y2| + S2 (clamped between the kids)
                ya, yb = c1[1], c2[1]
                y = (ya + yb + dl) / 2 if ya < yb else (ya + yb - dl) / 2
                y = min(max(y, min(ya, yb)), max(ya, yb))
                best = (nd["x"], y)
                if not site.legal(best):
                    best = (nd["x"], nd["y"])
            elif site.legal(ideal) and abs(md(ideal, c1) - md(ideal, c2) - dl) <= tol_um:
                best = ideal
            else:
                cand = []
                nst = int(radius_um / step)
                for k in range(-nst, nst + 1):
                    for ax in (0, 1):
                        o = 1 - ax          # scan coordinate o fixed, solve coordinate ax
                        q = [0.0, 0.0]
                        q[o] = ideal[o] + k * step
                        h = dl - (abs(q[o] - c1[o]) - abs(q[o] - c2[o]))
                        a, b = c1[ax], c2[ax]
                        if abs(a - b) < 1e-9:
                            continue
                        v = (h + a + b) / 2 if a < b else (a + b - h) / 2
                        if min(a, b) - 1e-9 <= v <= max(a, b) + 1e-9:
                            q[ax] = v
                            cand.append((md(q, ideal), round(q[0], 3), round(q[1], 3)))
                if select is None:
                    for _, x, y in sorted(cand):
                        if 0 <= x <= site.W and 0 <= y <= site.H and site.legal((x, y)):
                            best = (x, y)
                            break
                else:       # select mode: a far locus point costs wire (insertion, OCV); trade it against imbalance
                    pool = [(x, y) for _, x, y in sorted(cand)[:400]] + [(nd["x"], nd["y"])]
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):      # first legal point on each axis ray
                        for j in range(1, int(radius_um / step) + 1):
                            q = (round(ideal[0] + dx * j * step, 3), round(ideal[1] + dy * j * step, 3))
                            if site.legal(q):
                                pool.append(q)
                                break
                    span = md(c1, c2)

                    def cost(q):
                        return (abs(md(q, c1) + s1 - md(q, c2) - s2) + extra_wire_w * (md(q, c1) + md(q, c2) - span)
                                + 0.01 * md(q, ideal))
                    ok = [q for q in pool if 0 <= q[0] <= site.W and 0 <= q[1] <= site.H and site.legal(q)]
                    best = min(ok, key=cost) if ok else None
            if best is None:
                best = site.nearest(ideal) if select is None else (nd["x"], nd["y"])
            imb = abs(md(best, c1) + s1 - md(best, c2) - s2)
            if imb > tol_um:
                st["unbalanced"] += 1
                st["worst_imbalance_um"] = max(st["worst_imbalance_um"], round(imb, 1))
            nd["balance_imbalance_um"] = round(imb, 1)
            S[i] = max(md(best, c1) + s1, md(best, c2) + s2)
        else:
            best = site.nearest(ideal) if select is None else (nd["x"], nd["y"])
            if kids:
                S[i] = md(best, (nodes[kids[0]]["x"], nodes[kids[0]]["y"])) + S[kids[0]]
            else:
                tl = nd["taps"]
                S[i] = sum(md(best, t[2:4]) for t in tl) / len(tl) if tl else 0.0
        if md(best, ideal) > 1e-6:
            st["moved"] += 1
        nd["x"], nd["y"] = round_legal(site, best) if select is not None else (round(best[0], 3), round(best[1], 3))
    return st


# DIE-KV-2 10-27 (slid-root leg fix): a site-slid node can end up on the far side of a hard core from its kid (the slide
# keeps every root->node length, so it is chosen even when the kid leg then crosses the core).  On such a leg the straight
# repeaters snap to the core edges and leave a span of the core's length (KV G2 r3715: 800 um, 764 ps slew).  A leg whose
# straight path runs > rep_um through forbidden rects cannot meet the repeater spacing on that path, so it is routed on a
# LEGAL detour path (shortest Manhattan path over legal sites, bend penalty) and its repeaters are spaced evenly along that
# path.  Legs without such a stretch are unchanged (byte-identical).  Geometry only, no timing value.
# a leg is re-routed only when its straight placement would leave an unrepeated span > DETOUR_SPAN_X * rep_um and the
# straight leg runs > rep_um through forbidden rects (KV G2 c3500 rep 250: exactly 1 leg, r3715)
DETOUR_SPAN_X = 2.0


def leg_blocked_run(site, a, b, step=1.08):
    """longest contiguous stretch (um along the leg) of the straight leg a->b inside forbidden rects"""
    L = abs(b[0] - a[0]) + abs(b[1] - a[1])
    if L <= 0:
        return 0.0
    n = max(1, int(L / step))
    run = best = 0.0
    for k in range(n + 1):
        f = k / n
        if site.hits((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)):
            run += L / n
            best = max(best, run)
        else:
            run = 0.0
    return best


def legal_detour(site, a, b, step=5.4, margin=600.0, turn_um=20.0):
    """shortest Manhattan polyline a -> b whose grid points are legal sites (A*, bend penalty turn_um); None if none in
    the leg bbox + margin.  The endpoints themselves may be illegal (slide-fallback nodes)."""
    import heapq
    x0, y0 = max(0.0, min(a[0], b[0]) - margin), max(0.0, min(a[1], b[1]) - margin)
    x1, y1 = min(site.W, max(a[0], b[0]) + margin), min(site.H, max(a[1], b[1]) + margin)
    nx, ny = int((x1 - x0) / step) + 1, int((y1 - y0) / step) + 1

    def pt(i, j):
        return (round(x0 + i * step, 3), round(y0 + j * step, 3))

    def cell(q):
        return (min(nx - 1, max(0, int(round((q[0] - x0) / step)))), min(ny - 1, max(0, int(round((q[1] - y0) / step)))))
    s, g = cell(a), cell(b)
    ok = {}

    def legal(c):
        if c == s or c == g:
            return True
        if c not in ok:
            ok[c] = site.legal(pt(*c))
        return ok[c]

    def h(c):
        return (abs(c[0] - g[0]) + abs(c[1] - g[1])) * step
    best, prev = {(s, None): 0.0}, {}
    pq = [(h(s), 0.0, s, None)]
    end = None
    while pq:
        _, c0, c, d = heapq.heappop(pq)
        if c == g:
            end = (c, d)
            break
        if c0 > best.get((c, d), 1e30):
            continue
        for dv in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (c[0] + dv[0], c[1] + dv[1])
            if not (0 <= q[0] < nx and 0 <= q[1] < ny) or not legal(q):
                continue
            c1 = c0 + step + (turn_um if d is not None and d != dv else 0.0)
            if c1 < best.get((q, dv), 1e30):
                best[(q, dv)] = c1
                prev[(q, dv)] = (c, d)
                heapq.heappush(pq, (c1 + h(q), c1, q, dv))
    if end is None:
        return None
    st = [end]
    while st[-1] in prev:
        st.append(prev[st[-1]])
    path = [pt(*c) for c, _ in reversed(st)]
    # exact endpoints; a short jog joins each endpoint to its grid point (Manhattan: corner at (grid x, end y))
    path = [tuple(a), (path[0][0], a[1])] + path + [(path[-1][0], b[1]), tuple(b)]
    out = [path[0]]
    for k in range(1, len(path)):
        v = path[k]
        if abs(v[0] - out[-1][0]) < 1e-6 and abs(v[1] - out[-1][1]) < 1e-6:
            continue
        if len(out) >= 2:
            u, w = out[-2], out[-1]
            if (abs(u[0] - w[0]) < 1e-6 and abs(w[0] - v[0]) < 1e-6) or (abs(u[1] - w[1]) < 1e-6 and abs(w[1] - v[1]) < 1e-6):
                out[-1] = v
                continue
        out.append(v)
    return out


def polyline_points(poly, fracs):
    """(points at the given arc-length fractions of a Manhattan polyline, its length)"""
    seg = [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(poly, poly[1:])]
    tot = sum(seg)
    res = []
    for f in fracs:
        t, k = f * tot, 0
        while k < len(seg) - 1 and t > seg[k]:
            t -= seg[k]
            k += 1
        a, b = poly[k], poly[k + 1]
        u = t / seg[k] if seg[k] > 0 else 0.0
        res.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u))
    return res, tot


# DIE-QC-24 opt-in repeater leg rules (COORD 10-28 21:00; default off = byte-identical netlist/placement).
# Root cause (trial15, results/die_qc24_1028): a region-DME leg whose L route crosses an A0 hard core (+halo) on a blocked
# run shorter than route_um (480) is accepted as is; the evenly spaced repeater that lands inside the core is then moved by
# site.nearest() to the closest core EDGE in ANY direction -- 28 repeaters went 146.8 um sideways (462 x 1162-um core, the
# short way out is perpendicular to the leg), a 2 x 147-um wire spur the delay model never sees (+73 ps routed leg).
# REP_ON_LEG (--rep-on-leg): a blocked repeater slides ALONG its own planned leg polyline to the nearest legal point
# (between its upstream neighbour and the leg end), so the leg wire stays the planned wire; site.nearest only if the leg
# has no legal point left.  REP_OFF_LEG_MAX_UM (--rep-off-leg-max UM): guard -- the kit FAILS if any leg repeater is
# placed more than UM off its planned leg (Manhattan distance to the leg polyline / straight-leg bbox).
REP_ON_LEG = False
REP_OFF_LEG_MAX_UM = None


def poly_slide(site, poly, f, lo, step=0.54):
    """nearest legal point to arc fraction f ALONG the Manhattan polyline poly, searched on arc (lo, L - step]
    -> (x, y, arc) or None"""
    _, L = polyline_points(poly, [])
    if L <= 0:
        return None
    t0 = f * L
    n = int(L / step) + 1
    for s in range(0, n + 1):
        for t in ((t0 + s * step, t0 - s * step) if s else (t0,)):
            if lo < t <= L - step:
                q, _ = polyline_points(poly, [t / L])
                q = (round(q[0][0], 3), round(q[0][1], 3))
                if site.legal(q):
                    return q[0], q[1], t
    return None


def off_leg_um(c, poly):
    """Manhattan distance of point c to the leg polyline (a non-axis segment counts as its bbox: any L route in it)"""
    def d(a, b):
        cx = min(max(c[0], min(a[0], b[0])), max(a[0], b[0]))
        cy = min(max(c[1], min(a[1], b[1])), max(a[1], b[1]))
        return abs(c[0] - cx) + abs(c[1] - cy)
    return min(d(a, b) for a, b in zip(poly, poly[1:]))


def straight_leg_span(site, p, nd, nrep):
    """longest unrepeated span (um) of the default straight placement of a leg (repeaters snapped by site.nearest)"""
    ax = "x" if abs(nd["x"] - p["x"]) >= abs(nd["y"] - p["y"]) else "y"
    pts = [(p["x"], p["y"])] + [site.nearest((p["x"] + (nd["x"] - p["x"]) * (j + 1) / (nrep + 1),
                                              p["y"] + (nd["y"] - p["y"]) * (j + 1) / (nrep + 1)), ax)
                                for j in range(nrep)] + [(nd["x"], nd["y"])]
    return max(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(pts, pts[1:]))


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


def build_spine_fishbone(P, taps, col_um=60.0, merge_um=800.0, matched=False, station_max_taps=24):
    """LAND-HEAD-3 (opt-in --tree-form spine_fishbone, COORD 10-27 ruling A): LOW-INSERTION landed-form die clock in which
    every landed pair splits late.  Two levels, both straight M8/M9 legs, no padding/detour:
      (1) SPINE: a 1-D zero-skew (DME) binary tree along the vertical spine line x = clock.spine.root_um[0] that feeds one
          RIB ROOT per rib row; rib rows = the tap y of every partition that touches the spine line (spine/ctl/host rows).
          Adjacent rib roots are paired bottom-up; the merge point on the segment is the equal-length point, so every rib
          root sits at the same spine length by construction (an out-of-segment merge is clamped and reported).
      (2) RIBS: from each rib root a horizontal trunk E and W along the rib row; one trunk node per tap column (taps within
          col_um share it); a vertical stub to a leaf node per tap row.  Every tap belongs to its nearest rib row.
    A landed pair in the same rib then shares the trunk up to its own column (unshared = one column pitch + stubs) and a
    spine pair shares the spine down to its DME merge (insertion of the whole tree ~ spine half-span + longest rib)."""
    sx = (P.clock.get("spine", {}).get("root_um") or [P.W / 2, P.H / 2])[0]
    ry_root = (P.clock.get("spine", {}).get("root_um") or [P.W / 2, P.H / 2])[1]
    ribs = set()
    for n, p in P.parts.items():
        w = P.types[p["type"]]["outline_um"][0]
        if p["origin_um"][0] - 1e-3 <= sx <= p["origin_um"][0] + w + 1e-3:
            ribs.update(round(t[3], 3) for t in taps if t[0] == n)
    cnt = collections.Counter(round(t[3], 3) for t in taps)
    keep = []
    for r in sorted(ribs):                       # rows closer than merge_um (a PHY strip beside its station row) share
        if keep and r - keep[-1][-1] < merge_um:  # one rib: the row with the most taps carries it
            keep[-1].append(r)
        else:
            keep.append([r])
    ribs = sorted(max(g, key=lambda r: (cnt[r], -r)) for g in keep)
    by_rib = defaultdict(list)
    for t in taps:
        by_rib[min(ribs, key=lambda r: (abs(r - t[3]), r))].append(t)
    nodes = {}

    def mk(x, y, parent, level, **kw):
        i = len(nodes)
        nodes[i] = dict(id=i, x=round(x, 3), y=round(y, 3), parent=parent, level=level, kids=[], taps=[],
                        region=[0.0, 0.0, P.W, P.H], **kw)
        if parent is not None:
            nodes[parent]["kids"].append(i)
        return i
    # (1) spine DME (1-D): items (y, length below, structure)
    # LAND-HEAD-3 matched=True (12.13b phase-matched rib heads): (a) a rib with <= station_max_taps taps (a station row,
    # pitch ~1.4 mm, too long for a travelling rib) is a 1-D zero-skew DME along the row; (b) on a channel rib the spine
    # partition entry gets a detour leg equal to the column-0 trunk + mean stub, so it is in phase with o0/b0;
    # (c) the spine DME balances the rib HEAD lengths (the entries that cross between ribs), not just the rib roots.
    head_len, row_dme = {}, {}
    if matched:
        for r in ribs:
            tl = by_rib[r]
            if len(tl) <= station_max_taps:
                its = sorted(((t[2], abs(t[3] - r), ("tap", t)) for t in tl), key=lambda v: v[0])
                while len(its) > 1:
                    nx = []
                    for k2 in range(0, len(its) - 1, 2):
                        (xa, la_, sa), (xb, lb_, sb) = its[k2], its[k2 + 1]
                        D = xb - xa
                        xa2 = min(max((D + lb_ - la_) / 2, 0.0), D)
                        nx.append((xa + xa2, max(la_ + xa2, lb_ + D - xa2), ("m", xa + xa2, sa, sb)))
                    if len(its) % 2:
                        nx.append(its[-1])
                    its = nx
                row_dme[r] = its[0]
                head_len[r] = abs(its[0][0] - sx) + its[0][1]
            else:
                cx0 = min((abs(t[2] - sx) for t in tl if abs(t[2] - sx) > col_um), default=0.0)
                stubs = [abs(t[3] - r) for t in tl if abs(abs(t[2] - sx) - cx0) <= col_um]
                head_len[r] = cx0 + (sum(stubs) / len(stubs) if stubs else 0.0)
    items = [(r, head_len.get(r, 0.0), ("rib", r)) for r in ribs]
    clamp = 0.0
    while len(items) > 1:
        nxt = []
        for k in range(0, len(items) - 1, 2):
            (ya, la, sa), (yb, lb, sb) = items[k], items[k + 1]
            D = yb - ya
            xa = (D + lb - la) / 2
            da = db = 0.0
            if xa < 0 or xa > D:
                clamp = max(clamp, abs(min(xa, D - xa)))
                if matched:       # matched: balance by a detour leg on the shorter side (no clamp skew)
                    db, da = (la - lb - D, 0.0) if xa < 0 else (0.0, lb - la - D)
                xa = min(max(xa, 0.0), D)
            nxt.append((ya + xa, max(la + xa + da, lb + D - xa + db), ("m", ya + xa, sa, sb, da, db)))
        if len(items) % 2:
            nxt.append(items[-1])
        items = nxt
    top_y, top_len, top = items[0]
    root = mk(sx, ry_root, None, 0, spine=True)
    rib_root = {}

    def place(st, parent, level):
        if st[0] == "rib":
            i = parent if (abs(nodes[parent]["y"] - st[1]) < 1e-6 and abs(nodes[parent]["x"] - sx) < 1e-6) else \
                mk(sx, st[1], parent, level, spine=True)
            rib_root[st[1]] = i
            return
        _, y, sa, sb, da, db = st
        i = parent if abs(nodes[parent]["y"] - y) < 1e-6 else mk(sx, y, parent, level, spine=True)
        for ch, det in ((sa, da), (sb, db)):
            par = i
            if det > 1e-6:      # detour node beside the spine at the child's y: leg = |dy| + det/2, back det/2
                par = mk(sx + det / 2 if sx + det / 2 < P.W else sx - det / 2, ch[1], i, nodes[i]["level"] + 1,
                         spine=True, detour_um=round(det, 1))
            place(ch, par, nodes[par]["level"] + 1)
    place(top, root, 1)
    # (2) ribs
    for r in ribs:
        r0 = rib_root[r]
        if r in row_dme:          # matched station row: 1-D zero-skew DME hung below the rib root
            xr, _, st = row_dme[r]
            top = mk(xr, r, r0, nodes[r0]["level"] + 1, rib=r) if abs(xr - nodes[r0]["x"]) > 1e-6 else r0
            stk = [(st, top)]
            while stk:
                s2, par = stk.pop()
                if s2[0] == "tap":
                    t = s2[1]
                    lf = mk(t[2], t[3], par, nodes[par]["level"] + 1, rib=r)
                    nodes[lf]["taps"].append(t)
                else:
                    i = mk(s2[1], r, par, nodes[par]["level"] + 1, rib=r) if abs(s2[1] - nodes[par]["x"]) > 1e-6 else par
                    stk += [(s2[2], i), (s2[3], i)]
            continue
        for side in (-1, 1):
            tl = [t for t in by_rib[r] if (t[2] - sx) * side > 1e-6 or (side == 1 and abs(t[2] - sx) <= 1e-6)]
            tl.sort(key=lambda t: abs(t[2] - sx))
            cols = []
            for t in tl:
                if cols and abs(t[2] - cols[-1][0][2]) <= col_um:
                    cols[-1].append(t)
                else:
                    cols.append([t])
            prev = r0
            for c in cols:
                cx = sum(t[2] for t in c) / len(c)
                if abs(cx - sx) <= col_um and prev == r0 and matched and head_len.get(r, 0) > 2 * col_um:
                    h2 = head_len[r] / 2
                    q = mk(sx, r + h2 if r + h2 < P.H else r - h2, r0, nodes[r0]["level"] + 1, rib=r, detour_um=round(h2 * 2, 1))
                    tn = mk(sx, r, q, nodes[q]["level"] + 1, rib=r)
                    for t in c:
                        nodes[tn]["taps"].append(t)
                    continue
                if abs(cx - sx) <= col_um and prev == r0:
                    tn = r0
                else:
                    tn = mk(cx, r, prev, nodes[prev]["level"] + 1, rib=r)
                    prev = tn
                rows = defaultdict(list)
                for t in c:
                    rows[round(t[3], 1)].append(t)
                for yy, tt in sorted(rows.items()):
                    if abs(yy - r) <= col_um:
                        nodes[tn]["taps"] += tt
                    else:
                        lf = mk(nodes[tn]["x"], yy, tn, nodes[tn]["level"] + 1, rib=r)
                        nodes[lf]["taps"] += tt
    nodes[0]["spine_dme"] = dict(ribs=ribs, merge_len_um=round(top_len, 1), top_merge_y=round(top_y, 3),
                                 root_feed_um=round(abs(top_y - ry_root), 1), clamp_um=round(clamp, 1))
    return nodes


def _legal_on_line(site, q, along, tol=1.0):
    """legal clock site, or a sample sitting in the <0.5-um abutment sliver between two partitions with legal points
    tol um either side ALONG the line (a wire runs straight through an abutment edge)."""
    if site.legal(q):
        return True
    d = (tol, 0.0) if along == "x" else (0.0, tol)
    return site.why(q) == "outside" and site.legal((q[0] - d[0], q[1] - d[1])) and site.legal((q[0] + d[0], q[1] + d[1]))


def find_spine_column(site, box, step=2.16, dy=10.0):
    """x of the full-height legal column of `box` nearest its centre (QC-SLICECLK-3): every sample every dy um from
    y0+dy/2 to y1-dy/2 is a legal clock-tree site.  None if the region has no such column."""
    x0, y0, x1, y1 = box
    xc = (x0 + x1) / 2
    ys = [y0 + dy / 2 + i * dy for i in range(max(1, int((y1 - y0) / dy)))]
    n = int((x1 - x0) / 2 / step)
    for k in range(n + 1):
        for x in ((xc,) if k == 0 else (xc - k * step, xc + k * step)):
            if x0 + 1.0 <= x <= x1 - 1.0 and all(_legal_on_line(site, (x, y), "y") for y in ys):
                return round(x, 3)
    return None


def find_spine_row(site, xa, xb, y_want, dx=10.0, step=1.08, reach=3000.0):
    """y of the legal horizontal row over [xa, xb] nearest y_want (shared top spine along the slice band)."""
    xs = [xa + i * dx for i in range(int((xb - xa) / dx) + 1)] + [xb]
    for k in range(int(reach / step) + 1):
        for y in ((y_want,) if k == 0 else (y_want - k * step, y_want + k * step)):
            if 0 < y < site.H and all(_legal_on_line(site, (x, y), "x") for x in xs):
                return round(y, 3)
    return None


def build_slice_spine_tree(P, taps, regions, leaf_um=600.0, site=None, top_leaf_um=50.0, rows=None, region_dme=False,
                           dme_rep_um=None, dme_route_um=480.0, dme_delay_rep_um=None):
    """QC-SLICECLK-3 opt-in (--slice-spine, needs --region-trees): clock follows the slice band (METHODOLOGY 12.13b).
    - top: ONE shared horizontal spine at the legal row y_s nearest the common region centre; a 1-D equal-length
      bisection along it (full depth to top_leaf_um) reaches every region's spine column x_r at (x_r, y_s);
    - per region: a vertical leg on its full-height legal column to (x_r, yc), then every y-bisection level ON that
      column (no slide: siblings stay equal), until the strip height <= region width; then one equal horizontal leg to
      the strip centre (same length for every strip of the region) and a full-depth local bisection to leaf_um;
    - a region without a full-height legal column falls back to the stock equal-depth local tree from its bbox centre.
    rows (opt-in, qc_slice_clock_rows/1 of INFRA-FIRST-QC-R35): the plan's reserved geometry wins: column x = the
    region's top tap x (slices[].spine_x, HUB feed col), spine row = top.rows.T3_tap.y.
    Nodes on the spine / columns carry fixed=True (never slid); local nodes carry their split axis; the site pass (balanced_site) moves them where root->kid lengths change least.
    -> (nodes, info)"""
    W, H = P.W, P.H
    root = P.clock.get("spine", {}).get("root_um") or [W / 2, H / 2]
    nodes = {}

    def mk(x, y, parent, level, region, **kw):
        i = len(nodes)
        nodes[i] = dict(id=i, x=round(x, 3), y=round(y, 3), parent=parent, level=level, kids=[], taps=[],
                        region=[round(v, 3) for v in region], **kw)
        if parent is not None:
            nodes[parent]["kids"].append(i)
        return i

    def link(nid, x, y, region, **kw):
        """straight or L leg (corner node on the parent's row) from nid to (x, y)"""
        px, py, lv = nodes[nid]["x"], nodes[nid]["y"], nodes[nid]["level"] + 1
        if abs(px - x) > 1e-6 and abs(py - y) > 1e-6:
            nid = mk(x, py, nid, lv, region, corner=True, **kw)
        return mk(x, y, nid, lv, region, **kw)

    def local(nid, region, tlist):          # stock full-depth bisection (= build_htree.rec with full_depth)
        x0, y0, x1, y1 = region
        if max(x1 - x0, y1 - y0) <= leaf_um:
            nodes[nid]["taps"] = tlist
            return
        if x1 - x0 >= y1 - y0:
            xm = (x0 + x1) / 2
            halves = [((x0, y0, xm, y1), [t for t in tlist if t[2] < xm]), ((xm, y0, x1, y1), [t for t in tlist if t[2] >= xm])]
        else:
            ym = (y0 + y1) / 2
            halves = [((x0, y0, x1, ym), [t for t in tlist if t[3] < ym]), ((x0, ym, x1, y1), [t for t in tlist if t[3] >= ym])]
        nodes[nid]["split"] = "x" if x1 - x0 >= y1 - y0 else "y"
        for reg, tl in halves:
            if tl:
                c = link(nid, (reg[0] + reg[2]) / 2, (reg[1] + reg[3]) / 2, reg)
                local(c, reg, tl)

    rt = defaultdict(list)
    for t in taps:
        rt[regions[t[0]]].append(t)
    box = {}
    for rn, tl in rt.items():
        rs = [(P.parts[n]["origin_um"][0], P.parts[n]["origin_um"][1],
               P.parts[n]["origin_um"][0] + P.types[P.parts[n]["type"]]["outline_um"][0],
               P.parts[n]["origin_um"][1] + P.types[P.parts[n]["type"]]["outline_um"][1]) for n in {t[0] for t in tl}]
        box[rn] = (min(a[0] for a in rs), min(a[1] for a in rs), max(a[2] for a in rs), max(a[3] for a in rs))
    site = site or SiteMap(P)
    if rows:
        tapx = {t["region"]: t["x"] for t in rows["top"]["taps"]}
        col = {rn: tapx.get(rn) for rn in box}
    else:
        col = {rn: find_spine_column(site, b) for rn, b in sorted(box.items())}
    xcol = {rn: (col[rn] if col[rn] is not None else round((b[0] + b[2]) / 2, 3)) for rn, b in box.items()}
    ycs = sorted((b[1] + b[3]) / 2 for b in box.values())
    y_want = ycs[len(ycs) // 2]
    xa, xb = min(xcol.values()), max(xcol.values())
    y_s = rows["top"]["rows"]["T3_tap"]["y"] if rows else find_spine_row(site, xa, xb, y_want)
    if y_s is None:
        raise ValueError(f"no legal horizontal spine row over x {xa}-{xb} near y {y_want}")
    r = mk(root[0], root[1], None, 0, (0, 0, W, H), fixed=True)
    s0 = link(r, (xa + xb) / 2, y_s, (xa, y_s, xb, y_s), fixed=True, spine="top")

    def spine1d(nid, a, b, items):
        if b - a <= top_leaf_um:
            for rn, x in items:
                c = link(nid, x, y_s, box[rn], fixed=True, spine="top")
                nodes[c]["region_entry"] = rn
            return
        m = (a + b) / 2
        nodes[nid]["split"] = "x"
        for lo, hi in ((a, m), (m, b)):
            it = [(rn, x) for rn, x in items if (lo <= x < hi or (hi == b and x == b))]
            if it:
                c = link(nid, (lo + hi) / 2, y_s, (lo, y_s, hi, y_s), fixed=True, spine="top")
                spine1d(c, lo, hi, it)
    half = max(xb - xa, top_leaf_um) / 2 + 1e-3
    spine1d(s0, (xa + xb) / 2 - half, (xa + xb) / 2 + half, sorted((rn, x) for rn, x in xcol.items()))
    info = dict(spine_row_y_um=y_s, spine_x_um=[xa, xb], top_leaf_um=top_leaf_um, regions={},
                rows_source=(rows.get("lane"), rows.get("schema")) if rows else None)

    def column(nid, rn, y0, y1, tlist):
        b = box[rn]
        if y1 - y0 <= (b[2] - b[0]) + 1e-6:
            ysc = (y0 + y1) / 2
            s = nid
            if abs(nodes[nid]["x"] - (b[0] + b[2]) / 2) > 1e-6:
                s = link(nid, (b[0] + b[2]) / 2, ysc, (b[0], y0, b[2], y1), strip_root=rn)
            local(s, (b[0], y0, b[2], y1), tlist)
            return
        ym = (y0 + y1) / 2
        nodes[nid]["split"] = "y"
        for lo, hi, tl in ((y0, ym, [t for t in tlist if t[3] < ym]), (ym, y1, [t for t in tlist if t[3] >= ym])):
            if tl:
                c = link(nid, xcol[rn], (lo + hi) / 2, (b[0], lo, b[2], hi), fixed=True, spine="column")
                column(c, rn, lo, hi, tl)

    for e in [i for i, nd in list(nodes.items()) if nd.get("region_entry")]:
        rn = nodes[e]["region_entry"]
        b = box[rn]
        xc, yc = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if region_dme:             # DIE-QC-3 opt-in: legal-site DME region tree, fed straight from the spine entry
            dn, droot, dst = dme_region_tree(site, rt[rn], rep_um=dme_rep_um, delay_rep_um=dme_delay_rep_um)
            ids = {}

            def attach(j, parent, lv):
                d = dn[j]
                kw = dict(region_root=rn, dme_root=True) if j == droot else {}
                if d.get("part_root"):
                    kw["part_root"] = d["part_root"]
                i = mk(d["x"], d["y"], parent, lv, b, **kw)
                ids[j] = i
                pa, q = (nodes[parent]["x"], nodes[parent]["y"]), (d["x"], d["y"])
                if abs(pa[0] - q[0]) > 1e-6 and abs(pa[1] - q[1]) > 1e-6:     # L route through the channels
                    best = None
                    for cn in ((q[0], pa[1]), (pa[0], q[1])):
                        r = max(leg_blocked_run(site, pa, cn), leg_blocked_run(site, cn, q))
                        if best is None or r < best[0]:
                            best = (r, cn)
                    if best[0] <= dme_route_um and best[0] < leg_blocked_run(site, pa, q):
                        nodes[i]["route"] = [list(pa), list(best[1]), list(q)]
                nodes[i]["taps"] = list(d["taps"])
                for k in d["kids"]:
                    attach(k, i, lv + 1)
            attach(droot, e, nodes[e]["level"] + 1)
            info["regions"][rn] = dict(mode="dme", box=[round(v, 3) for v in b], dme=dst,
                                       dme_root_um=[dn[droot]["x"], dn[droot]["y"]], dme_S_um=round(dn[droot]["S"], 1))
            continue
        if col[rn] is None:        # fallback: stock local tree from the bbox centre
            c = link(e, xc, yc, b, region_root=rn)
            local(c, b, rt[rn])
            info["regions"][rn] = dict(mode="local", box=[round(v, 3) for v in b])
            continue
        c = link(e, xcol[rn], yc, b, fixed=True, spine="column", region_root=rn) if abs(yc - y_s) > 1e-6 else e
        nodes[c]["region_root"] = rn
        column(c, rn, b[1], b[3], rt[rn])
        info["regions"][rn] = dict(mode="spine_column", box=[round(v, 3) for v in b], column_x_um=xcol[rn],
                                   strip_leg_um=round(abs(xcol[rn] - xc), 3), feed_leg_um=round(abs(yc - y_s), 3))
    return nodes, info


DME_WORKERS = 1     # DIE-QC-20 opt-in --region-dme-workers: region DME trees computed in parallel (fork pool), attached in order
_DME_POOL_JOBS = None


def _dme_pool_job(k):
    site, tl, kw = _DME_POOL_JOBS[k]
    return dme_region_tree(site, tl, **kw)


def attach_region_dme(nodes, site, taps, regions, rep_um=None, delay_rep_um=None, route_um=480.0, only=None, early=None,
                      snake=None, early_mode="hang", merge_only=None):
    """DIE-QC-3 opt-in (--tree-form link_htree --region-dme): hang one legal-site DME tree (dme_region_tree) under every
    LEGALIZED feed-end node that carries region_root; legs that cross a core take the L corner through the channels
    (same rule as the slice-spine form).  Runs after the site pass, so nothing it places slides afterwards."""
    rt = defaultdict(list)
    for t in taps:
        rt[regions[t[0]]].append(t)
    st = {}
    jobs = []
    for e in [i for i, nd in list(nodes.items()) if nd.get("region_root") is not None]:
        rn = nodes[e]["region_root"]
        if not rt.get(rn) or (only is not None and rn not in only):   # DIE-QC-4 --region-dme-only: listed regions only
            continue
        sn = bool(snake) and (snake == "all" or rn in snake)    # DIE-QC-9 --region-dme-snake: listed regions (or all)
        # DIE-QC-19 opt-in --region-dme-early-merge-only: listed regions take early_mode 'merge' (A0-entry rooting: the
        # deep core sink is a DME sink with its declared early as sink delay, so the merge point sits at the core entry
        # and the shallow glue subtree joins there); every other region keeps early_mode
        em = "merge" if (merge_only and rn in merge_only) else early_mode
        jobs.append((e, rn, sn, dict(rep_um=rep_um, delay_rep_um=delay_rep_um, early=early,
                                     **({"snake": True} if sn else {}), **({"early_mode": em} if em != "hang" else {}))))
    # DIE-QC-20 opt-in DME_WORKERS > 1: dme_region_tree is a pure function of (site, region taps, options), so the region
    # trees are computed in a fork pool and attached below in the same order (same nodes / ids as the serial loop)
    global _DME_POOL_JOBS
    if DME_WORKERS > 1 and len(jobs) > 1:
        import multiprocessing as mp
        _DME_POOL_JOBS = [(site, rt[rn], kw) for _, rn, _, kw in jobs]
        try:
            with mp.get_context("fork").Pool(min(DME_WORKERS, len(jobs))) as pool:
                trees = pool.map(_dme_pool_job, range(len(jobs)), chunksize=1)
        finally:
            _DME_POOL_JOBS = None
    else:
        trees = None
    for jk, (e, rn, sn, kw) in enumerate(jobs):
        dn, droot, dst = trees[jk] if trees is not None else dme_region_tree(site, rt[rn], **kw)

        def attach(j, parent, snake_pts=None):
            d = dn[j]
            i = len(nodes)
            nodes[i] = dict(id=i, x=round(d["x"], 3), y=round(d["y"], 3), parent=parent, level=nodes[parent]["level"] + 1,
                            kids=[], taps=list(d["taps"]), region=list(nodes[e].get("region_box", nodes[e]["region"])),
                            dme=rn, **({"part_root": d["part_root"]} if d.get("part_root") else {}))
            nodes[i]["req_xy"] = [nodes[i]["x"], nodes[i]["y"]]
            nodes[parent]["kids"].append(i)
            pa, q = (nodes[parent]["x"], nodes[parent]["y"]), (nodes[i]["x"], nodes[i]["y"])
            if snake_pts:       # DIE-QC-9: elongated leg = explicit legal buffer chain (tree_netlist places it as is)
                nodes[i]["snake"] = [list(x) for x in snake_pts]
            elif abs(pa[0] - q[0]) > 1e-6 and abs(pa[1] - q[1]) > 1e-6:
                best = None
                for cn in ((q[0], pa[1]), (pa[0], q[1])):
                    r = max(leg_blocked_run(site, pa, cn), leg_blocked_run(site, cn, q))
                    if best is None or r < best[0]:
                        best = (r, cn)
                if best[0] <= route_um and best[0] < leg_blocked_run(site, pa, q):
                    nodes[i]["route"] = [list(pa), list(best[1]), list(q)]
            for k in d["kids"]:
                attach(k, i, (d.get("snakes") or {}).get(k))
        attach(droot, e)
        st[rn] = dict(merges=dst.get("merges"), imbalanced=dst.get("imbalanced"), spread=dst.get("spread_um"),
                      **({"early_taps": dst["early_taps"]} if dst.get("early_taps") else {}),
                      **({k: dst[k] for k in ("snakes", "snake_wire_um", "snake_buffers")} if sn else {}),
                      **({k: dst[k] for k in ("snake_max_leg_um", "snake_legs_over_cap", "snake_cap_rebuilt") if k in dst}
                         if sn else {}))
    return st


def _man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

# ------------------------------------------------------------------ DIE-QC-3 opt-in: legal-site DME region trees (bug ii)
def _split_cut(pts, mode="gap"):
    """binary cut of a point list -> (left idx, right idx).  mode 'gap': the cut at any coordinate gap (either axis,
    >= 1/4 of the points each side) with the least sum of the two bboxes' half-perimeters; 'median': equal halves on
    the axis with the least half-perimeter sum."""
    n = len(pts)
    best = None
    for ax in (0, 1):
        order = sorted(range(n), key=lambda i: (pts[i][ax], pts[i][1 - ax]))
        if mode == "median":
            ks = [(n + 1) // 2]
        else:
            lo_n = max(1, n // 4)
            ks = [k for k in range(lo_n, n - lo_n + 1) if 0 < k < n and pts[order[k - 1]][ax] != pts[order[k]][ax]]
        for k in ks:
            a, b = [pts[i] for i in order[:k]], [pts[i] for i in order[k:]]
            hp = sum(max(p[0] for p in g) - min(p[0] for p in g) + max(p[1] for p in g) - min(p[1] for p in g)
                     for g in (a, b))
            if best is None or hp < best[0] - 1e-9:
                best = (hp, order[:k], order[k:])
    if best is None:            # all points equal: split by count
        order = list(range(n))
        return order[:n // 2], order[n // 2:]
    return best[1], best[2]


def _leg_detours(site, a, b, rep_um):
    """True if tree_netlist would re-route the leg a -> b on a legal detour (its straight placement leaves a span >
    DETOUR_SPAN_X x rep_um and runs > rep_um through forbidden rects): the detour adds wire DME did not price."""
    L = _man(a, b)
    if L <= 2 * rep_um or not hasattr(site, "hits"):
        return False
    if leg_blocked_run(site, a, b) <= rep_um:
        return False
    nrep = max(0, int(math.ceil(L / rep_um)) - 1)
    return straight_leg_span(site, dict(x=a[0], y=a[1]), dict(x=b[0], y=b[1]), nrep) > DETOUR_SPAN_X * rep_um


def merge_point(site, c1, s1, c2, s2, radius_um=800.0, step=1.08, extra_wire_w=0.1, pool_n=400, rep_um=None):
    """DME merge on legal sites: the legal point q minimising |(|q-c1| + s1) - (|q-c2| + s2)| + extra_wire_w x (added
    wire over |c1-c2|) + 0.01 x |q - ideal|.  Candidates: the zero-skew locus scanned on rows/columns through the ideal
    point within radius_um (points outside the kids' bbox = elongated merge, standard DME detour wiring) + the first
    legal point on each axis ray from the ideal point.  ideal = the zero-skew point on the kids' shortest path (or the
    later kid when |s1 - s2| > |c1 - c2|).  -> (q, imbalance_um, extra_wire_um)"""
    md = _man
    D_ = md(c1, c2)
    dl = s2 - s1
    # ideal: on the shortest path c1 -> c2 at distance t from c1 with t + s1 = D - t + s2
    t = min(max((D_ + dl) / 2, 0.0), D_)
    dx, dy = c2[0] - c1[0], c2[1] - c1[1]
    if D_ > 0:
        fx = min(t, abs(dx))          # x first, then y (any monotone path: pick the L through the bbox centre side)
        ideal = (c1[0] + math.copysign(fx, dx), c1[1] + math.copysign(t - fx, dy))
    else:
        ideal = c1
    cand = []
    nst = int(radius_um / step)
    for k in range(-nst, nst + 1):
        for ax in (0, 1):
            o = 1 - ax
            q = [0.0, 0.0]
            q[o] = ideal[o] + k * step
            h = dl - (abs(q[o] - c1[o]) - abs(q[o] - c2[o]))
            a, b = c1[ax], c2[ax]
            if abs(a - b) < 1e-9:
                continue
            v = (h + a + b) / 2 if a < b else (a + b - h) / 2
            if min(a, b) - 1e-9 <= v <= max(a, b) + 1e-9:
                q[ax] = v
                cand.append((md(q, ideal), round(q[0], 3), round(q[1], 3)))
    pool = [(x, y) for _, x, y in sorted(cand)[:pool_n]] + [ideal, c1, c2]
    for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for j in range(1, nst + 1):
            q = (round(ideal[0] + ddx * j * step, 3), round(ideal[1] + ddy * j * step, 3))
            if 0 <= q[0] <= site.W and 0 <= q[1] <= site.H and site.legal(q):
                pool.append(q)
                break

    def cost(q):
        return (abs(md(q, c1) + s1 - md(q, c2) - s2) + extra_wire_w * (md(q, c1) + md(q, c2) - D_)
                + 0.01 * md(q, ideal))
    ok = [q for q in pool if 0 <= q[0] <= site.W and 0 <= q[1] <= site.H and site.legal(q)]
    if not ok:
        ok = [site.nearest(ideal)]
    q = min(ok, key=cost)
    return q, abs(md(q, c1) + s1 - md(q, c2) - s2), md(q, c1) + md(q, c2) - D_


def leg_len(site, a, b, rep_um):
    """routed length of the tree leg a -> b as tree_netlist builds it: Manhattan, or the legal-detour polyline when
    the straight placement would leave an unrepeatable span over a core (_leg_detours)."""
    if rep_um and _leg_detours(site, a, b, rep_um):
        poly = legal_detour(site, a, b)
        if poly is not None:
            return polyline_points(poly, [])[1]
    return _man(a, b)


def merge_point_routed(site, c1, s1, c2, s2, radius_um=800.0, step=1.08, extra_wire_w=0.1, rep_um=None, iters=3):
    """merge_point with the netlist's legal detours priced: a leg that tree_netlist will detour adds its extra length
    to that kid's depth and the zero-skew point is solved again (<= iters times).  -> (q, imbalance, extra, la, lb)"""
    e1 = e2 = 0.0
    for _ in range(iters):
        q, _, _ = merge_point(site, c1, s1 + e1, c2, s2 + e2, radius_um, step, extra_wire_w)
        la, lb = leg_len(site, q, c1, rep_um), leg_len(site, q, c2, rep_um)
        n1, n2 = la - _man(q, c1), lb - _man(q, c2)
        if abs(n1 - e1) < 1.0 and abs(n2 - e2) < 1.0:
            break
        e1, e2 = n1, n2
    return q, abs(la + s1 - lb - s2), la + lb - _man(c1, c2), la, lb


DME_MODES = ("gap", "median", "greedy")
# BUFx24 stage on a 1x M8/M9 leg, d = d0 + k1 L + k2 L^2 (ps, um): OpenSTA fit on 1x ladders (DIE-QC-3 cal1x, resid <= 4 ps)
STAGE_1X_TT = (20.8281, 0.013984, 0.00033554)
# DIE-QC-21 opt-in --region-dme-stage-cal FILE: a stage model calibrated on ROUTED legs of the actual clock cell replaces
# STAGE_1X_TT in the DME delay model (leg_ps / chain_ps / snake_leg / merge_point_delay), adds a per-extra-fanout term
# at every binary merge node (its cell drives two legs: QC trial13b inv2 +10.9 ps TT, unmodelled before, so branchy glue
# subtrees arrived later than modelled and merge-mode core taps came ~50 ps late), and prices the tap leg with the fitted
# wire coefficients.  Default None = the uncalibrated model (byte-identical trees).
DME_FANOUT_PS = 0.0
TAP_WIRE_CAL = None


def load_stage_cal(path):
    """--region-dme-stage-cal: JSON {"leg": [d0, k1, k2, kf], "tap": [k1, k2]} (TT ps; um) -> sets the DME model globals"""
    global STAGE_1X_TT, DME_FANOUT_PS, TAP_WIRE_CAL
    c = json.loads(Path(path).read_text())
    d0, k1, k2, kf = (float(x) for x in c["leg"])
    STAGE_1X_TT = (d0, k1, k2)
    DME_FANOUT_PS = kf
    TAP_WIRE_CAL = tuple(float(x) for x in c["tap"])
    return c


def leg_ps(L, rep_um):
    """delay of a buffered leg of length L (um): n = ceil(L / rep_um) equal stages (n - 1 repeaters + the child node
    buffer), as tree_netlist places them"""
    n = max(1, int(math.ceil(L / rep_um - 1e-9)))
    if EVEN_LEGS and n % 2:
        n += 1
    d0, k1, k2 = STAGE_1X_TT
    return n * d0 + k1 * L + k2 * L * L / n


def tap_wire_ps(d_um):
    """DIE-QC-9 (with --region-dme-snake): delay of the unbuffered tap leg from the leaf driver to a core pin d um away
    (often inside the core outline: QC vmr pins sit ~100 um in), wire part of STAGE_1X_TT only.  The DIE-QC-3/8 delay
    DME priced this leg as d (um read as ps): ~100 model ps too late for an in-core pin, so the tree delivered those pins
    ~150 ps TT early (trial6/7 measured).  Kept behind the opt-in so trial6 stays reproducible."""
    _, k1, k2 = STAGE_1X_TT
    if TAP_WIRE_CAL is not None:    # DIE-QC-21 --region-dme-stage-cal: fitted routed tap-leg wire
        k1, k2 = TAP_WIRE_CAL
    return k1 * d_um + k2 * d_um * d_um


def chain_ps(pts):
    """delay (model ps) of a leg whose buffers sit at pts[1:] (pts[0] = driver): one STAGE_1X_TT stage per consecutive
    pair, stage length = Manhattan between the two buffers (what the router connects).  leg_ps is the even-split case."""
    d0, k1, k2 = STAGE_1X_TT
    s = 0.0
    for a, b in zip(pts, pts[1:]):
        L = _man(a, b)
        s += d0 + k1 * L + k2 * L * L
    return s


def _snake_pts(pa, q, u, h, rep_um, shape="dogleg"):
    """elongated leg pa -> q, pushed h um outside the pa/q bounding box along axis direction u (adds 2h of wire):
    'dogleg' = one turning buffer w at the bbox mid-edge + h u (waypoints pa, w, q: >= 1 extra stage);
    'hairpin' = waypoints pa, pa + h u, q + h u, q (>= 2 extra stages).  Every waypoint is a buffer (the router
    joins buffers by Manhattan wire, so the turn must be a buffer) and each piece gets ceil(len / rep_um) equal stages."""
    if shape == "dogleg":
        m = [(pa[0] + q[0]) / 2, (pa[1] + q[1]) / 2]
        for ax in (0, 1):
            if u[ax]:
                m[ax] = (max(pa[ax], q[ax]) if u[ax] > 0 else min(pa[ax], q[ax])) + u[ax] * h
        w = [pa, tuple(m), q]
    else:
        w = [pa, (pa[0] + u[0] * h, pa[1] + u[1] * h), (q[0] + u[0] * h, q[1] + u[1] * h), q]
    pts = [pa]
    for a, b in zip(w, w[1:]):
        L = _man(a, b)
        if L < 1e-6:
            continue
        n = max(1, int(math.ceil(L / rep_um - 1e-9)))
        path = [a, (b[0], a[1]), b]
        p, _ = polyline_points(path, [j / n for j in range(1, n + 1)])
        pts += [tuple(x) for x in p]
    return pts


def snake_leg(site, pa, q, target_ps, rep_um, h_max=3000.0, step=1.08):
    """DIE-QC-9 opt-in (--region-dme-snake, COORD 10-28 ruling: standard zero-skew DME wire elongation, plan-computed,
    part of the tree): the buffer chain pa -> q whose chain_ps is closest to target_ps (> leg_ps of the plain leg).
    Shapes (_snake_pts) dogleg / hairpin x the 4 axis directions; h by bisection on the ideal chain, then a local
    scan with every buffer snapped to the nearest LEGAL site and the delay re-priced on the snapped chain (honest: the
    reported delay is that of the placed buffers).  Kept only if it beats the plain leg.  Ties: least snap distance,
    then least wire.  -> (repeater points [excluding pa and q], chain ps, added wire um over the plain leg) or None"""
    L0 = _man(pa, q)
    plain = leg_ps(L0, rep_um)
    best = None
    for shape in ("dogleg", "hairpin"):
        for u in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            lo, hi = 0.0, h_max
            if chain_ps(_snake_pts(pa, q, u, hi, rep_um, shape)) < target_ps:
                continue
            for _ in range(40):
                m = (lo + hi) / 2
                if chain_ps(_snake_pts(pa, q, u, m, rep_um, shape)) < target_ps:
                    lo = m
                else:
                    hi = m
            for k in range(-6, 7):
                h = max(0.0, hi + k * step)
                raw = _snake_pts(pa, q, u, h, rep_um, shape)
                if not all(0 <= x <= site.W and 0 <= y <= site.H for x, y in raw):
                    continue
                pts, snap = [pa], 0.0
                for x in raw[1:-1]:
                    y = x if site.legal(x) else site.nearest(x)
                    y = round_legal(site, y)
                    snap += _man(x, y)
                    pts.append(y)
                pts.append(q)
                if EVEN_LEGS and (len(pts) - 1) % 2:
                    continue            # inv2: odd stage count would flip polarity
                ps = chain_ps(pts)
                wire = sum(_man(a, b) for a, b in zip(pts, pts[1:]))
                key = (round(abs(ps - target_ps), 1), round(snap, 1), wire)
                if best is None or key < best[0]:
                    best = (key, pts[1:-1], ps, wire - L0)
    if best is None or abs(best[2] - target_ps) >= abs(plain - target_ps):
        return None
    return best[1], best[2], best[3]


def merge_point_delay(site, c1, s1, c2, s2, rep_um, radius_um=800.0, step=1.08, extra_ps_um=0.03):
    """delay-aware DME merge (opt-in --region-dme delay): s1/s2 are subtree delays (ps); candidates = the length-locus
    pool of merge_point (depths converted at the repeated-line ps/um) + every legal point on the kids' shortest L path;
    the legal point with the least |leg_ps(L1) + s1 - leg_ps(L2) - s2| + extra_ps_um x added wire wins (stage counts
    priced: a short leg still costs a whole stage).  -> (q, imbalance_ps, extra_um)"""
    md = _man
    a = leg_ps(rep_um, rep_um) / rep_um
    pool = []
    q0, _, _ = merge_point(site, c1, s1 / a, c2, s2 / a, radius_um, step, 0.1)
    pool.append(q0)
    D_ = md(c1, c2)
    for path in ([c1, (c2[0], c1[1]), c2], [c1, (c1[0], c2[1]), c2]):
        n = int(D_ / (4 * step)) + 1
        for j in range(n + 1):
            pt, _ = polyline_points(path, [j / n]) if D_ > 0 else ([c1], 0)
            q = (round(pt[0][0], 3), round(pt[0][1], 3))
            if 0 <= q[0] <= site.W and 0 <= q[1] <= site.H and site.legal(q):
                pool.append(q)
    for dx in (-2, -1, 1, 2):          # around the length solution
        for dy in (-2, -1, 1, 2):
            q = (round(q0[0] + dx * 4 * step, 3), round(q0[1] + dy * 4 * step, 3))
            if 0 <= q[0] <= site.W and 0 <= q[1] <= site.H and site.legal(q):
                pool.append(q)

    def cost(q):
        return (abs(leg_ps(md(q, c1), rep_um) + s1 - leg_ps(md(q, c2), rep_um) - s2)
                + extra_ps_um * (md(q, c1) + md(q, c2) - D_))
    q = min(pool, key=cost)
    return q, abs(leg_ps(md(q, c1), rep_um) + s1 - leg_ps(md(q, c2), rep_um) - s2), md(q, c1) + md(q, c2) - D_


DME_JOIN_BUDGET = 4096  # DIE-S81-16: join() calls per top-level merge before the bounded monotone join-down takes over
SNAKE_TOL_PS = 1.0      # DIE-QC-9 --region-dme-snake: a delay-mode merge imbalanced by more than this is elongated
# DIE-QC-23 opt-in --region-dme-snake-cap UM (COORD 10-28 19:26, structural long-snake fix; default None = byte-identical).
# In early-mode 'merge' regions with --region-dme-snake, a core tap's declared early is a deep DME sink; the stock build
# merges it with whatever glue taps the spatial cut puts beside it, so EVERY such low glue subtree gets its own snake
# (trial14: 1787 snake legs, 179 > 1.2 mm, up to 1.8 mm with 7 buffers; the 9 identical 1.8 mm replicas route -15..+41
# ps off the calibrated model, residual sd 9.6 ps < 400 um -> 19.0 ps > 1.6 mm).  Those snakes sit on glue-to-glue
# UNSHARED paths (glue intra hold).  With the cap set, the merge point moves up in every partition whose stock tree has
# a snake leg longer than the cap: the non-early (glue) taps are built into one tree first and each early core sink is
# then joined at the glue root (join(): it descends only where the depths meet), so the elongation lands on the glue
# root leg (shared by every glue tap) once per core; the rebuild is kept only if its longest snake leg is shorter.  The kept
# tree's snake legs longer than the cap are counted in the stats (snake_legs_over_cap; reported, never hidden).
DME_SNAKE_CAP_UM = None


def dme_region_tree(site, taps, radius_um=800.0, extra_wire_w=0.1, modes=DME_MODES, rep_um=None, delay_rep_um=None,
                    early=None, snake=False, early_mode="hang"):
    """DIE-QC-3 opt-in (--region-dme): a region clock tree built ON legal sites, so nothing slides after balancing.
    Embedding: bottom-up DME with Manhattan length as the delay proxy (repeated 1x line: delay ~ linear in length);
    every merge point is the legal zero-skew point from merge_point() (no slide, no snake; an elongated merge point is
    reported as extra wire); a pair too unequal in depth for a snake-free merge is joined by join() lower down.  A leaf is one tap: its driver sits at the tap (nearest legal point).
    Topology: per partition, each of `modes` is embedded and the one with the least root->tap length spread (then
    wire) is kept: 'gap' / 'median' = recursive _split_cut of the taps, 'greedy' = Edahiro-style matching (merge the
    pair with the least max(|c1-c2|, |S1-S2|), the wire a snake-free zero-skew merge needs).  Above the partitions:
    'gap' cuts over the partition roots.  Geometry only: no timing value.
    -> (tree nodes [dict(x, y, kids, taps, S, Smin, part_root)], root index, stats)"""
    out = []
    if early_mode not in ("hang", "merge"):
        raise ValueError(f"early_mode {early_mode!r}: hang | merge")
    # DIE-S81-14 opt-in early_mode='merge': an early core tap is an ordinary DME sink whose declared early (model ps) is a
    # sink delay, so the bottom-up zero-skew merges deliver it early by construction (binary merges, no upper-node hang
    # legs / star nodes; a pair with no zero-skew point is joined lower down or snaked like any other).  'hang' = DIE-QC-8.
    sink_early = early if (early and delay_rep_um and early_mode == "merge") else None

    def leaf(t):
        q = (t[2], t[3]) if site.legal((t[2], t[3])) else site.nearest((t[2], t[3]))
        q = round_legal(site, q)
        d = _man(q, (t[2], t[3]))
        sd = tap_wire_ps(d) if snake and delay_rep_um else d
        if sink_early:      # DIE-S81-14 --region-dme-early-mode merge: declared early = DME sink delay (zero-skew merge)
            sd += float(sink_early.get((t[0], t[1]), 0.0))
        out.append(dict(x=q[0], y=q[1], kids=[], taps=[t], S=sd, Smin=sd, W=d))
        return len(out) - 1

    def merge(a, b):
        A, B = out[a], out[b]
        rad = min(max(radius_um, _man((A["x"], A["y"]), (B["x"], B["y"])) / 2), 4000.0)
        if delay_rep_um:        # delay-aware: S / Smin are ps, legs priced by leg_ps (stage counts included)
            q, imb, ex = merge_point_delay(site, (A["x"], A["y"]), A["S"], (B["x"], B["y"]), B["S"], delay_rep_um, rad)
            q = round_legal(site, q)
            la, lb = _man(q, (A["x"], A["y"])), _man(q, (B["x"], B["y"]))
            da, db = leg_ps(la, delay_rep_um), leg_ps(lb, delay_rep_um)
            snakes, sw = {}, 0.0
            if snake and abs(da + A["S"] - db - B["S"]) > SNAKE_TOL_PS:
                # DIE-QC-9 opt-in: no zero-skew legal point -> elongate the fast kid's leg (plan-computed hairpin of
                # legal buffer sites, priced on the placed chain); the merge point itself is unchanged
                fast, Fx, slow_t = (a, A, db + B["S"]) if da + A["S"] < db + B["S"] else (b, B, da + A["S"])
                r = snake_leg(site, q, (Fx["x"], Fx["y"]), slow_t - Fx["S"], delay_rep_um)
                if r is not None:
                    pts, ps, sw = r
                    snakes[fast] = [list(x) for x in pts]
                    if fast == a:
                        da, la = ps, la + sw
                    else:
                        db, lb = ps, lb + sw
                    imb = abs(da + A["S"] - db - B["S"])
            fo = DME_FANOUT_PS      # DIE-QC-21 --region-dme-stage-cal: this node's cell drives two legs (one extra fanout)
            out.append(dict(x=q[0], y=q[1], kids=[a, b], taps=[], S=max(da + A["S"], db + B["S"]) + fo,
                            Smin=min(da + A["Smin"], db + B["Smin"]) + fo, W=la + lb + A["W"] + B["W"], imb=imb, ex=ex,
                            **({"snakes": snakes, "snake_um": sw} if snakes else {})))
            return len(out) - 1
        q, imb, ex, da, db = merge_point_routed(site, (A["x"], A["y"]), A["S"], (B["x"], B["y"]), B["S"], rad, 1.08,
                                                extra_wire_w, rep_um=rep_um)
        q2 = round_legal(site, q)
        if q2 != q:
            q = q2
            da, db = leg_len(site, q, (A["x"], A["y"]), rep_um), leg_len(site, q, (B["x"], B["y"]), rep_um)
        out.append(dict(x=q[0], y=q[1], kids=[a, b], taps=[], S=max(da + A["S"], db + B["S"]),
                        Smin=min(da + A["Smin"], db + B["Smin"]), W=da + db + A["W"] + B["W"], imb=imb, ex=ex))
        return len(out) - 1

    def reach_of(A, B):
        r = _man((A["x"], A["y"]), (B["x"], B["y"]))
        return leg_ps(r, delay_rep_um) - leg_ps(0.0, delay_rep_um) if delay_rep_um else r

    class _JoinBudget(Exception):
        pass

    jcalls, jfall = [0], []

    def join(a, b, depth=0):
        """merge a and b; when no snake-free zero-skew point exists (|S_a - S_b| > |a - b|), the shallow subtree is
        merged DOWN into the deep one instead (with the deep root's kid nearest to it, recursively), and the deep
        root is re-embedded over the result and its other kid: the depths meet where they match.
        DIE-S81-16: the re-embedding (join of the new node with the other kid) can descend into the node it has just
        built, so a pair whose depths never meet ping-pongs to the depth cap with 2 calls per level (2^25 worst case;
        go14 merge mode spent >2 h here).  Calls are counted per top-level join; one that needs more than
        DME_JOIN_BUDGET calls is discarded and redone by join_mono() (bounded, logged in stats join_fallbacks).  Any
        join that finishes within the budget is unchanged (same nodes, same ids: the whole output is byte-identical)."""
        if depth:
            jcalls[0] += 1
            if jcalls[0] > DME_JOIN_BUDGET:
                raise _JoinBudget
            return join_down(a, b, depth)
        jcalls[0] = 0
        n0 = len(out)
        try:
            return join_down(a, b, 0)
        except _JoinBudget:
            del out[n0:]            # orphans of the discarded attempt (never referenced by kept nodes)
            gap = abs(out[a]["S"] - out[b]["S"])
            r = join_mono(a, b)
            jfall.append((round(gap, 1), round(out[r].get("imb", 0.0), 1)))
            return r

    def join_down(a, b, depth):
        A, B = out[a], out[b]
        reach = reach_of(A, B)
        if abs(A["S"] - B["S"]) <= reach + 1e-6 or depth > 24:
            return merge(a, b)
        if A["S"] > B["S"]:
            a, b, A, B = b, a, B, A
        if not B["kids"]:
            return merge(a, b)
        k = min(B["kids"], key=lambda c: _man((A["x"], A["y"]), (out[c]["x"], out[c]["y"])))
        o = [c for c in B["kids"] if c != k][0]
        return join(join(a, k, depth + 1), o, depth + 1)

    def join_mono(a, b):
        """DIE-S81-16 bounded join-down (standard DME): the shallow subtree a descends into the deep one b only while
        the deep side's nearest kid is still at least as deep as a (strict progress: one level per call, never back
        into a node built on the way), merges where the depths meet, and the deep side is re-embedded by plain
        merges up the same path; any residual gap is the merge's own delay balance (the fast leg is snaked when
        --region-dme-snake is on, else it is reported as imbalance).  Calls <= depth of b."""
        A, B = out[a], out[b]
        if abs(A["S"] - B["S"]) <= reach_of(A, B) + 1e-6:
            return merge(a, b)
        if A["S"] > B["S"]:
            a, b, A, B = b, a, B, A
        if not B["kids"]:
            return merge(a, b)
        k = min(B["kids"], key=lambda c: _man((A["x"], A["y"]), (out[c]["x"], out[c]["y"])))
        if out[k]["S"] + reach_of(A, out[k]) + 1e-6 < A["S"]:
            return merge(a, b)          # the depths meet at b: merge here, the fast side takes the detour
        o = [c for c in B["kids"] if c != k][0]
        return merge(join_mono(a, k), o)

    def build(items, pos, mk_leaf, mode):
        if mode != "greedy":
            if len(items) == 1:
                return mk_leaf(items[0])
            l, r = _split_cut([pos(it) for it in items], mode)
            return join(build([items[i] for i in l], pos, mk_leaf, mode), build([items[i] for i in r], pos, mk_leaf, mode))
        live = [mk_leaf(it) for it in items]
        while len(live) > 1:
            best = None
            for a in range(len(live)):
                A = out[live[a]]
                for b in range(a + 1, len(live)):
                    B = out[live[b]]
                    c = max(_man((A["x"], A["y"]), (B["x"], B["y"])) * (0.33 if delay_rep_um else 1.0), abs(A["S"] - B["S"]))
                    if best is None or c < best[0] - 1e-9:
                        best = (c, a, b)
            _, a, b = best
            m = join(live[a], live[b])
            live = [x for k, x in enumerate(live) if k not in (a, b)] + [m]
        return live[0]
    byp = defaultdict(list)
    late = []           # DIE-QC-8 opt-in --region-dme-early: early core taps hang from an upper node (below)
    for t in taps:
        if early and delay_rep_um and early_mode == "hang" and early.get((t[0], t[1]), 0.0) > 0.0:
            late.append(t)
        else:
            byp[t[0]].append(t)
    if late and not byp:
        byp[late[0][0]] = late
        late = []
    def snake_legs(r_):
        legs, stack = [], [r_]
        while stack:
            d = out[stack.pop()]
            stack += d["kids"]
            for k_, pts in (d.get("snakes") or {}).items():
                ch = [(d["x"], d["y"])] + [tuple(x) for x in pts] + [(out[k_]["x"], out[k_]["y"])]
                legs.append(sum(_man(a, b) for a, b in zip(ch, ch[1:])))
        return legs

    def max_snake_leg(r_):
        return max(snake_legs(r_), default=0.0)

    cap_rebuilt = []
    proots, pick = [], defaultdict(int)
    for pn in sorted(byp):
        tl = sorted(byp[pn], key=lambda t: (t[2], t[3], t[1]))
        tries = [build(tl, lambda t: (t[2], t[3]), leaf, m) for m in modes]
        ear = ([t for t in tl if float(sink_early.get((t[0], t[1]), 0.0)) > 0.0]
               if (DME_SNAKE_CAP_UM is not None and snake and sink_early) else [])
        gl = [t for t in tl if t not in ear]
        if ear and gl and max(max_snake_leg(r_) for r_ in tries) > DME_SNAKE_CAP_UM + 1e-6:
            # DIE-QC-23 --region-dme-snake-cap: only a partition whose stock tree has a snake leg over the cap is rebuilt
            # glue tree first, early core sinks joined at its root; a rebuild is kept only if its longest snake leg is
            # shorter (trial15: applying it to every partition re-embedded glue trees that had no long snake: c_*_tf_00
            # routed glue spread 19.5 -> 136 ps)
            alt = []
            for m in modes:
                r_ = build(gl, lambda t: (t[2], t[3]), leaf, m)
                for t in sorted(ear, key=lambda t: (-float(sink_early[(t[0], t[1])]), t[1])):
                    r_ = join(r_, leaf(t))
                alt.append(r_)
            if max(max_snake_leg(r_) for r_ in alt) < max(max_snake_leg(r_) for r_ in tries):
                tries = alt
                cap_rebuilt.append(pn)
        k = min(range(len(tries)), key=lambda j: (round(out[tries[j]]["S"] - out[tries[j]]["Smin"], 1), out[tries[j]]["W"]))
        pick[modes[k]] += 1
        out[tries[k]]["part_root"] = pn
        proots.append(tries[k])
    root = build(proots, lambda i: (out[i]["x"], out[i]["y"]), lambda i: i, "gap")
    early_rows = []
    if late:
        # DIE-QC-8 opt-in (12.3 v5.0 macro insertion-delay balancing): a core tap with declared early e (model ps) is
        # delivered early BY CONSTRUCTION: it hangs from the kept-tree node j whose subtree delay S_j best matches
        # e + leg_ps(j -> tap) (arrival at j = S_root - S_j, so the tap arrives e before the other taps); no pads.
        # A shortfall (root not deep enough) is reported, never hidden.
        kept, stack = [], [root]
        while stack:
            i = stack.pop()
            kept.append(i)
            stack += out[i]["kids"]
        for t in sorted(late, key=lambda t: ((-early[(t[0], t[1])],) if snake else ()) + (t[0], t[1])):
            e = float(early[(t[0], t[1])])
            q = (t[2], t[3]) if site.legal((t[2], t[3])) else site.nearest((t[2], t[3]))
            q = round_legal(site, q)
            d = _man(q, (t[2], t[3]))
            dw = d
            if snake:       # DIE-QC-9: the tap leg in ps (see tap_wire_ps), not um
                d = tap_wire_ps(d)

            def miss(j):
                return out[j]["S"] - e - leg_ps(_man((out[j]["x"], out[j]["y"]), q), delay_rep_um) - d
            cand = [j for j in kept if out[j]["kids"]]
            if snake and cand and max(miss(j) for j in cand) < -SNAKE_TOL_PS:
                # DIE-QC-9: no node is deep enough for this early -> a new top node at the old root's site; the leg
                # down to the old root is elongated (in place: a dogleg out and back on legal sites) so the new
                # root is exactly deep enough; the early tap then hangs from it like any other
                rq = (out[root]["x"], out[root]["y"])
                need = e + leg_ps(_man(rq, q), delay_rep_um) + d - out[root]["S"]
                r = snake_leg(site, rq, rq, max(need, leg_ps(0.0, delay_rep_um)), delay_rep_um)
                if r is None:   # no elongated chain beats one plain stage (stage quantum): take the plain stage
                    r = ([], leg_ps(0.0, delay_rep_um), 0.0)
                if r is not None:
                    pts, ps, sw = r
                    out.append(dict(x=rq[0], y=rq[1], kids=[root], taps=[], S=out[root]["S"] + ps,
                                    Smin=out[root]["Smin"] + ps, W=out[root]["W"] + sw, imb=0.0, ex=0.0,
                                    snakes={root: [list(x) for x in pts]}, snake_um=sw,
                                    **({"part_root": out[root]["part_root"]} if out[root].get("part_root") else {})))
                    root = len(out) - 1
                    kept.append(root)
                    cand.append(root)
            if snake and any(miss(j) >= 0 for j in cand):
                # DIE-QC-9 --region-dme-snake: hang where the tap would be early by MORE than e, then elongate the
                # hang leg by the miss (a too-shallow node cannot be fixed by wire, so it is chosen only if nothing else)
                j = min((j for j in cand if miss(j) >= 0), key=lambda j: (round(miss(j), 3), j))
            else:
                j = min(cand, key=lambda j: (round(abs(miss(j)), 3), j), default=root)
            m0 = miss(j)
            out.append(dict(x=q[0], y=q[1], kids=[], taps=[t], S=d, Smin=d, W=dw))
            out[j]["kids"].append(len(out) - 1)
            row = dict(part=t[0], port=t[1], early_model_ps=round(e, 2), node_S_ps=round(out[j]["S"], 2),
                       leg_um=round(_man((out[j]["x"], out[j]["y"]), q), 1), miss_ps=round(m0, 2),
                       root_S_ps=round(out[root]["S"], 2))
            if snake and m0 > SNAKE_TOL_PS:
                jq = (out[j]["x"], out[j]["y"])
                r = snake_leg(site, jq, q, leg_ps(_man(jq, q), delay_rep_um) + m0, delay_rep_um)
                if r is not None:
                    pts, ps, sw = r
                    out[j].setdefault("snakes", {})[len(out) - 1] = [list(x) for x in pts]
                    out[j]["snake_um"] = out[j].get("snake_um", 0.0) + sw
                    row.update(snake_um=round(sw, 1), miss_ps=round(out[j]["S"] - e - ps - d, 2), miss_unsnaked_ps=round(m0, 2))
            early_rows.append(row)
    st = dict(merges=0, imbalanced=0, worst_imbalance_um=0.0, extra_wire_um=0.0, topology=dict(pick))
    if snake:
        st.update(snakes=0, snake_wire_um=0.0, snake_buffers=0)
    if sink_early:
        early_rows = [dict(part=t[0], port=t[1], early_model_ps=round(float(sink_early[(t[0], t[1])]), 2), mode="merge")
                      for t in taps if float(sink_early.get((t[0], t[1]), 0.0)) > 0.0]
    if early_rows:
        st["early_taps"] = early_rows
    stack = [root]
    while stack:                       # stats of the kept tree only
        d = out[stack.pop()]
        stack += d["kids"]
        if d.get("snakes") and snake:
            st["snakes"] += len(d["snakes"])
            st["snake_buffers"] += sum(len(v) for v in d["snakes"].values())
            st["snake_wire_um"] = round(st["snake_wire_um"] + d.get("snake_um", 0.0), 1)
        if d["kids"]:
            st["merges"] += 1
            st["extra_wire_um"] += d["ex"]
            if d["imb"] > 2.0:
                st["imbalanced"] += 1
                st["worst_imbalance_um"] = max(st["worst_imbalance_um"], round(d["imb"], 1))
    st["extra_wire_um"] = round(st["extra_wire_um"], 1)
    st["spread_um"] = round(out[root]["S"] - out[root]["Smin"], 1)
    if snake and DME_SNAKE_CAP_UM is not None:     # DIE-QC-23: kept-tree snake leg lengths vs the cap
        legs = snake_legs(root)
        st.update(snake_cap_um=float(DME_SNAKE_CAP_UM), snake_max_leg_um=round(max(legs, default=0.0), 1),
                  snake_legs_over_cap=sum(1 for x in legs if x > DME_SNAKE_CAP_UM + 1e-6),
                  snake_cap_rebuilt=len(cap_rebuilt))
    if jfall:       # DIE-S81-16: top-level joins redone by join_mono (only present when it happened)
        st["join_fallbacks"] = len(jfall)
        st["join_fallback_worst_gap_ps"] = max(g for g, _ in jfall)
        st["join_fallback_worst_imb"] = max(i for _, i in jfall)
    return out, root, st


def round_legal(site, q, nd=3):
    """q rounded to the nd-decimal output grid, staying legal (DIE-QC 10-27): balanced_site's refine walk stops ON
    a halo edge, and rounding 10620.7200000001 -> 10620.72 put 3 QC node buffers 1e-12 um inside a core halo
    (strict-inside test).  Try the 9 neighbours on the 10^-nd grid (nearest first); keep the plain rounding if the
    unrounded point was illegal too (that case is reported by site_legal, not hidden here)."""
    r = (round(q[0], nd), round(q[1], nd))
    if site.legal(r) or not site.legal(q):
        return r
    u = 10.0 ** -nd
    for dx, dy in sorted(((i, j) for i in (-1, 0, 1) for j in (-1, 0, 1)), key=lambda d: abs(d[0]) + abs(d[1])):
        c = (round(r[0] + dx * u, nd), round(r[1] + dy * u, nd))
        if site.legal(c):
            return c
    return r


def balanced_site(site, p, parent, kids, split=None, reach=1300.0, step=2.16, fine=0.54):
    """legal site for an illegal tree node that keeps root->descendant lengths as equal as possible (QC-SLICECLK-3).
    Candidates: the first legal point on each of the 4 axis rays from p (coarse walk, refined back toward p) + the
    nearest legal point.  Cost = worst |change of root->kid length| over the node's kids (taps for a leaf), i.e. the
    imbalance the move adds against the rest of the tree.  A branch node moved back along an incoming leg that is
    perpendicular to its split axis costs 0 (the old --tree-site-slide guarantee); a move ALONG the split axis costs
    2x its length between siblings and is chosen only when nothing cheaper is legal.  -> (point, cost_um) or (None, None)"""
    p = (float(p[0]), float(p[1]))
    if site.legal(p):
        return p, 0.0
    cands = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        k = 1
        while k * step <= reach:
            q = (p[0] + dx * k * step, p[1] + dy * k * step)
            if site.legal(q):
                j = 1
                while j * fine < step:          # refine back toward p
                    r = (q[0] - dx * j * fine, q[1] - dy * j * fine)
                    if not site.legal(r):
                        break
                    q = r
                    j += 1
                cands.append(q)        # unrounded: round_legal does the output grid (DIE-QC 10-27)
                break
            k += 1
    try:
        cands.append(site.nearest(p))
    except ValueError:
        pass
    if not cands:
        return None, None

    def cost(q):
        din = (_man(parent, q) - _man(parent, p)) if parent is not None else 0.0
        if not kids:
            return abs(din)
        return max(abs(din + _man(q, k) - _man(p, k)) for k in kids)
    best = min(cands, key=lambda q: (round(cost(q), 3), _man(p, q)))
    return best, round(cost(best), 3)


def path_lengths(nodes):
    """root -> node Manhattan length (um) of every node (for balance self-checks)."""
    L = {}
    for i in sorted(nodes):
        nd = nodes[i]
        if nd["parent"] is None:
            L[i] = 0.0
        else:
            p = nodes[nd["parent"]]
            L[i] = L[nd["parent"]] + abs(p["x"] - nd["x"]) + abs(p["y"] - nd["y"])
    return L


def build_link_fishbone(P, taps, regions, feed, col_um=60.0, local="fishbone", leaf_um=200.0, full=0.0, dme_only=None,
                        dme_feed_centroid=0.0, region_stub=0.0):
    """DIE-KV-2 (opt-in --tree-form link_fishbone --region-trees MAP --feed FEED, METHODOLOGY 12.13 clock follows data):
    the die clock is fed ALONG THE REGION LINKS, not by a die-wide balanced tree.
      (1) FEED: the region feed tree of tools/die_plan/locality.py (feed 'fish': max-bit spanning tree of the region
          crossing graph; FEED json = locality score()['feed'] = {root, parent{child: parent}, tap{'p->c': [x, y]}}).
          The feed runs from the parent region centre to the link's tap point and on to the child region centre in
          straight M8/M9 legs (L corners), so every feed edge is one crossing link: tree-edge crossings share the clock
          down to the parent centre.  No balancing, no pads: the nominal phase offset of each crossing is absorbed by the
          count-aligned ring (MESO-COUNT-1 ruling 20:35; per-crossing K from count_align_plan.py).
      (2) FISHBONE region tree: a trunk along the region's long axis through its centre; one trunk node per tap column
          (taps within col_um share it); a perpendicular stub to a leaf per tap row (leaf delay ~ Manhattan distance).
    Region names come from the map values; every tap's partition must be in the map and every region in the feed.
    local='htree' (DIE-KV-3, opt-in --tree-form link_htree; COORD 21:38 CROSS-DIE NOTE: balanced local tree inside each
    region): instead of (2), a BALANCED H-tree per region rooted at the region centre (= the feed end): full-depth
    bisection of the region bbox along its longer axis down to leaf_um (both halves of a split at the same depth, the child
    node at the child box centre, so every root->leaf path has the same leg lengths and repeater count by construction;
    empty halves pruned); taps hang from their leaf (leaf->tap last-mile leg <= leaf_um).  No trims, pads or detours.
    full=1 (opt-in): empty halves are NOT pruned (tapless leaves), so every branch node drives two equal legs and a sparse
    half loads its parent like a dense one (KV H200B: a 1-tap phy half ran 70-150 ps early against its 12-tap pc half).
    dme_feed_centroid=1 (DIE-QC-11 opt-in, --tree-opt dme_feed_centroid=1, with --region-dme-only): the feed of a DME
    region ends at the CENTROID of that region's taps instead of its partition bbox centre (the DME root hangs from the
    feed end; a region whose bbox is stretched by one far partition, e.g. QC c_W5_bf_01 + io_serdes_2, otherwise feeds
    ~0.7 mm past its cores and back).  Non-DME regions keep the bbox centre (their H-tree bisects the bbox).  Default 0:
    unchanged.
    region_stub=1 (DIE-QC-13 opt-in, --tree-opt region_stub=1; 12.16b(iv) reset release follows the clock): the feed end
    of every region that FEEDS other regions becomes a SHARED FEED NODE: the region's own tree (H-tree / DME / fishbone)
    hangs from a stub node at the same point (zero-length leg, one even inverter pair in inv2) instead of from the feed
    end itself.  The shared node then carries no region taps, so a reset-release start port leaves it as a retime flop
    on the clock fork (virtual st: node) instead of from a parent-region leaf ~440 ps below the fork (QC trial10: 60/871
    width start fails, all on slice-head parents).  Regions without feed children are unchanged.  Default 0: unchanged."""
    par = feed["parent"]
    tapxy = {tuple(k.split("->")): v for k, v in feed["tap"].items()}
    rt = defaultdict(list)
    for t in taps:
        rt[regions[t[0]]].append(t)
    box = {}
    for rn in set(regions.values()):
        rs = [(P.parts[n]["origin_um"][0], P.parts[n]["origin_um"][1],
               P.parts[n]["origin_um"][0] + P.types[P.parts[n]["type"]]["outline_um"][0],
               P.parts[n]["origin_um"][1] + P.types[P.parts[n]["type"]]["outline_um"][1])
              for n, r in regions.items() if r == rn and n in P.parts]
        if rs:
            box[rn] = (min(a[0] for a in rs), min(a[1] for a in rs), max(a[2] for a in rs), max(a[3] for a in rs))
    miss = sorted(set(box) - set(par))
    if miss:
        raise SystemExit(f"link_fishbone: regions not in the feed tree: {miss[:5]}")
    nodes = {}

    def mk(x, y, parent, level, reg, **kw):
        i = len(nodes)
        nodes[i] = dict(id=i, x=round(x, 3), y=round(y, 3), parent=parent, level=level, kids=[], taps=[],
                        region=list(reg), **kw)
        if parent is not None:
            nodes[parent]["kids"].append(i)
        return i

    def leg(a, x, y, reg, **kw):
        """straight legs a -> (x, y): horizontal first, then vertical (corner node when both change)"""
        ax, ay = nodes[a]["x"], nodes[a]["y"]
        if abs(ax - x) > 1e-6 and abs(ay - y) > 1e-6:
            a = mk(x, ay, a, nodes[a]["level"] + 1, reg, corner=True, **kw)
        if abs(nodes[a]["x"] - x) > 1e-6 or abs(nodes[a]["y"] - y) > 1e-6:
            a = mk(x, y, a, nodes[a]["level"] + 1, reg, **kw)
        return a
    cen = {r: ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for r, b in box.items()}
    if dme_feed_centroid and dme_only:
        for r in sorted(dme_only):
            if rt.get(r) and r in cen and r != feed["root"]:
                cen[r] = (sum(t[2] for t in rt[r]) / len(rt[r]), sum(t[3] for t in rt[r]) / len(rt[r]))
    root = feed["root"]
    rr = {root: mk(cen[root][0], cen[root][1], None, 0, box[root], region_root=root, feed=True)}
    order, kids = [root], defaultdict(list)
    for c, p_ in par.items():
        if p_ is not None:
            kids[p_].append(c)
    for x in order:
        for c in sorted(kids[x]):
            t = tapxy.get((x, c)) or [(cen[x][0] + cen[c][0]) / 2, (cen[x][1] + cen[c][1]) / 2]
            a = leg(rr[x], t[0], t[1], box[x], feed=True, feed_edge=f"{x}->{c}")
            a = leg(a, cen[c][0], cen[c][1], box[c], feed=True, feed_edge=f"{x}->{c}")
            nodes[a]["region_root"] = c
            rr[c] = a
            order.append(c)
    if region_stub:            # DIE-QC-13 opt-in: shared feed node; the region's own tree hangs from a stub below it
        for r in list(order):
            if kids.get(r):
                a = rr[r]
                nodes[a].pop("region_root", None)
                nodes[a]["shared_feed"] = r
                rr[r] = mk(nodes[a]["x"], nodes[a]["y"], a, nodes[a]["level"] + 1, box[r], region_root=r,
                           region_stub=True)
    if local == "none":        # DIE-QC-3 opt-in (link_htree + --region-dme): feed only; region trees attached later
        nodes[0]["link_feed"] = dict(root=root, regions=len(box), local="dme",
                                     feed_edges=sum(1 for v in par.values() if v is not None))
        for r in rr:
            nodes[rr[r]]["region_box"] = list(box[r])
        return nodes
    if local == "htree":
        def bisect(nid, reg, tl):
            x0, y0, x1, y1 = reg
            if max(x1 - x0, y1 - y0) <= leaf_um:
                nodes[nid]["taps"] += tl
                return
            if x1 - x0 >= y1 - y0:
                xm = (x0 + x1) / 2
                halves = [((x0, y0, xm, y1), [t for t in tl if t[2] < xm]), ((xm, y0, x1, y1), [t for t in tl if t[2] >= xm])]
            else:
                ym = (y0 + y1) / 2
                halves = [((x0, y0, x1, ym), [t for t in tl if t[3] < ym]), ((x0, ym, x1, y1), [t for t in tl if t[3] >= ym])]
            for rg, sub in halves:
                if sub or full:     # full (opt-in --tree-opt full=1): empty halves kept as tapless branches, so every
                    c = leg(nid, (rg[0] + rg[2]) / 2, (rg[1] + rg[3]) / 2, rg, rib=r)   # node drives 2 equal legs
                    bisect(c, rg, sub)
        for r, tl in rt.items():
            if dme_only and r in dme_only:   # DIE-QC-4 --region-dme-only: DME region tree attached after the site pass
                nodes[rr[r]]["region_box"] = list(box[r])
                continue
            bisect(rr[r], box[r], tl)
        nodes[0]["link_feed"] = dict(root=root, regions=len(box), local="htree", leaf_um=leaf_um,
                                     **({"dme_regions": sorted(dme_only)} if dme_only else {}),
                                     **({"full": True, "tapless_leaves": sum(1 for d in nodes.values() if d.get("rib") is not None
                                                                              and not d["kids"] and not d["taps"])}
                                        if full else {}),
                                     feed_edges=sum(1 for v in par.values() if v is not None),
                                     feed_wire_um=round(sum(abs(nodes[i]["x"] - nodes[n["parent"]]["x"]) +
                                                            abs(nodes[i]["y"] - nodes[n["parent"]]["y"])
                                                            for i, n in nodes.items() if n.get("feed") and
                                                            n["parent"] is not None), 1))
        return nodes
    # (2) fishbone per region
    for r, tl in rt.items():
        b, (cx, cy), r0 = box[r], cen[r], rr[r]
        horiz = (b[2] - b[0]) >= (b[3] - b[1])
        ax_of = (lambda t: t[2]) if horiz else (lambda t: t[3])
        ot_of = (lambda t: t[3]) if horiz else (lambda t: t[2])
        c_ax, c_ot = (cx, cy) if horiz else (cy, cx)
        xy = (lambda a_, o_: (a_, o_)) if horiz else (lambda a_, o_: (o_, a_))
        for side in (-1, 1):
            st = [t for t in tl if (ax_of(t) - c_ax) * side > 1e-6 or (side == 1 and abs(ax_of(t) - c_ax) <= 1e-6)]
            st.sort(key=lambda t: abs(ax_of(t) - c_ax))
            cols = []
            for t in st:
                if cols and abs(ax_of(t) - ax_of(cols[-1][0])) <= col_um:
                    cols[-1].append(t)
                else:
                    cols.append([t])
            prev = r0
            for c in cols:
                ca = sum(ax_of(t) for t in c) / len(c)
                if abs(ca - c_ax) <= col_um and prev == r0:
                    tn = r0
                else:
                    tn = mk(*xy(ca, c_ot), prev, nodes[prev]["level"] + 1, b, rib=r)
                    prev = tn
                rows = defaultdict(list)
                for t in c:
                    rows[round(ot_of(t), 1)].append(t)
                for oo, tt in sorted(rows.items()):
                    if abs(oo - c_ot) <= col_um:
                        nodes[tn]["taps"] += tt
                    else:
                        lf = mk(*xy(nodes[tn]["x" if horiz else "y"], oo), tn, nodes[tn]["level"] + 1, b, rib=r)
                        nodes[lf]["taps"] += tt
    nodes[0]["link_feed"] = dict(root=root, regions=len(box), feed_edges=sum(1 for v in par.values() if v is not None),
                                 feed_wire_um=round(sum(abs(nodes[i]["x"] - nodes[n["parent"]]["x"]) +
                                                        abs(nodes[i]["y"] - nodes[n["parent"]]["y"])
                                                        for i, n in nodes.items() if n.get("feed") and
                                                        n["parent"] is not None), 1))
    return nodes


def tree_netlist(nodes, taps, rep_um=450.0, site=None, tap_pad=None, tap_pad_sites=None, clock_cell="buf"):
    """buffered tree: a BUF at every node (branch / leaf driver), repeaters every rep_um along each leg.
    tap_pad (DIE-KV-5 opt-in --tap-pad, METHODOLOGY 12.8 plan-computed per-tap sizing): {tap port: n} puts n BUF cells in
    series between the tap's leaf net and the tap (insertion-delay balancing of a light, pruned branch); default None =
    byte-identical netlist.
    clock_cell='inv' (DIE-QC-11 opt-in --clock-cell inv): every node driver and leg repeater is CLK_INV (same footprint and
    sites), so the rise/fall asymmetry alternates sign stage by stage instead of accumulating; a tap whose root->tap
    inverter count is odd gets ONE CLK_INV at the tap (instance q<node>_<tap>, placed like a tap pad), so every tap sees the
    true clock polarity by construction.  nodes[i]['inv_parity'] = inverter count parity at the node output.
    Default 'buf': byte-identical netlist.
    -> (verilog, placements [(inst, x, y)], tap ports [(port, x, y)], node_buf {node id: inst}, path {tap port: [inst]})"""
    if clock_cell not in ("buf", "inv", "inv2"):
        raise ValueError(f"clock_cell {clock_cell!r}: buf, inv or inv2")
    even = clock_cell == "inv2"
    if even:
        clock_cell = "inv"
    CELL = CLK_INV if clock_cell == "inv" else BUF
    par_in = {}
    cells, place, wires = [], [], []
    node_buf, parent_of = {}, {}
    off_leg = []
    k = 0

    def net(i):
        return f"n{i}"
    # node buffers
    for i, nd in nodes.items():
        node_buf[i] = f"b{i}"
    for i, nd in sorted(nodes.items()):
        nrep = 0
        if nd["parent"] is None:
            src = "root"
            if even:            # inv2: 2-stage root (true polarity at the root node)
                cells.append(f"  {CLK_INV} b{i}_r (.A(root), .Y(nr{i}));")
                wires.append(f"nr{i}")
                q0 = (nd["x"] + 1.62, nd["y"])
                if site is not None and not site.legal(q0):
                    q0 = site.nearest(q0)
                place.append((f"b{i}_r", q0[0], q0[1]))
                src = f"nr{i}"
        else:
            p = nodes[nd["parent"]]
            L = abs(p["x"] - nd["x"]) + abs(p["y"] - nd["y"])
            nrep = max(0, int(math.ceil(L / rep_um)) - 1)
            poly = None
            if nd.get("snake"):     # DIE-QC-9 --region-dme-snake: plan-computed elongated leg, buffers at the given sites
                pts = [tuple(q) for q in nd["snake"]]
                nrep = len(pts)
                chain = [(p["x"], p["y"])] + pts + [(nd["x"], nd["y"])]
                poly = chain
                nd["detour"] = [[round(a, 3), round(b, 3)] for a, b in chain]
                nd["detour_um"] = round(sum(_man(a, b) for a, b in zip(chain, chain[1:])) - L, 1)
            elif nd.get("route") and site is not None and _man(nd["route"][0], (p["x"], p["y"])) < 1e-3 \
                    and _man(nd["route"][-1], (nd["x"], nd["y"])) < 1e-3:    # DIE-QC-3 --region-dme: the leg's L route
                poly = [tuple(q) for q in nd["route"]]
                _, Ld = polyline_points(poly, [])
                nrep = max(0, int(math.ceil(Ld / rep_um)) - 1)
                pts, _ = polyline_points(poly, [(j + 1) / (nrep + 1) for j in range(nrep)])
                nd["detour"] = [[round(a, 3), round(b, 3)] for a, b in poly]
                nd["detour_um"] = round(Ld - L, 1)
            elif site is not None and L > 2 * rep_um and leg_blocked_run(site, (p["x"], p["y"]), (nd["x"], nd["y"])) > rep_um \
                    and straight_leg_span(site, p, nd, nrep) > DETOUR_SPAN_X * rep_um:
                poly = legal_detour(site, (p["x"], p["y"]), (nd["x"], nd["y"]))
                if poly is not None:       # slid-root fix: repeaters evenly along the legal detour path
                    _, Ld = polyline_points(poly, [])
                    nrep = max(0, int(math.ceil(Ld / rep_um)) - 1)
                    pts, _ = polyline_points(poly, [(j + 1) / (nrep + 1) for j in range(nrep)])
                    nd["detour"] = [[round(a, 3), round(b, 3)] for a, b in poly]
                    nd["detour_um"] = round(Ld - L, 1)
            if even and (nrep + 1) % 2 and not nd.get("snake"):
                nrep += 1
                if poly is not None:
                    pts, _ = polyline_points(poly, [(j + 1) / (nrep + 1) for j in range(nrep)])
            if even and nd.get("snake") and (nrep + 1) % 2:
                raise ValueError(f"inv2: snake leg of node {i} has an odd stage count")
            src = f"{net(nd['parent'])}"
            prev_inst = node_buf[nd["parent"]]
            on_leg = REP_ON_LEG and poly is not None and not nd.get("snake")
            Lp = polyline_points(poly, [])[1] if on_leg else 0.0
            arc = 0.0
            for j in range(nrep):
                f = (j + 1) / (nrep + 1)
                x = p["x"] + (nd["x"] - p["x"]) * f
                y = p["y"] + (nd["y"] - p["y"]) * f
                inst = f"r{i}_{j}"
                if poly is not None:
                    x, y = pts[j]
                    if not site.legal((x, y)):
                        q = poly_slide(site, poly, f, arc) if on_leg else None
                        if q is not None:
                            x, y, arc = q
                        else:
                            x, y = site.nearest((x, y))
                    elif on_leg:
                        arc = max(arc, f * Lp)
                elif site is not None:
                    x, y = site.nearest((x, y), "x" if abs(nd["x"] - p["x"]) >= abs(nd["y"] - p["y"]) else "y")
                o = f"rn{i}_{j}"
                cells.append(f"  {CELL} {inst} (.A({src}), .Y({o}));")
                wires.append(o)
                place.append((inst, x, y))
                parent_of[inst] = prev_inst
                prev_inst = inst
                src = o
                if REP_OFF_LEG_MAX_UM is not None:
                    leg = poly if poly is not None else [(p["x"], p["y"]), (nd["x"], nd["y"])]
                    d = off_leg_um((x, y), leg)
                    if d > REP_OFF_LEG_MAX_UM:
                        off_leg.append((round(d, 1), inst, nd.get("dme")))
            parent_of[node_buf[i]] = prev_inst
        if clock_cell == "inv":
            pp = (1 if even else 0) if nd["parent"] is None else nodes[nd["parent"]]["inv_parity"]
            nd["inv_parity"] = (pp + (nrep if nd["parent"] is not None else 0) + 1) % 2
            if even and nd["inv_parity"]:
                raise ValueError(f"inv2: node {i} odd polarity (even legs violated)")
        cells.append(f"  {CELL} {node_buf[i]} (.A({src}), .Y({net(i)}));")
        wires.append(net(i))
        place.append((node_buf[i], nd["x"], nd["y"]))
    if off_leg:
        off_leg.sort(reverse=True)
        raise ValueError(f"--rep-off-leg-max {REP_OFF_LEG_MAX_UM:g}: {len(off_leg)} leg repeaters placed off their planned "
                         f"leg in {len({r for _, _, r in off_leg})} regions, worst {off_leg[:5]}")
    tap_ports = []
    for i, nd in sorted(nodes.items()):
        for (part, port, x, y) in nd["taps"]:
            tp = f"t_{sv(part)}__{port}"
            tap_ports.append((tp, x, y, part, port, i))
            src = net(i)
            prev_inst = node_buf[i]
            for j in range(int((tap_pad or {}).get(tp, 0))):
                inst, o = f"p{i}_{tp}_{j}", f"pn{i}_{tp}_{j}"
                cells.append(f"  {BUF} {inst} (.A({src}), .Y({o}));")
                wires.append(o)
                explicit = tp in (tap_pad_sites or {})
                if explicit:
                    rows = tap_pad_sites[tp]
                    if len(rows) != int((tap_pad or {}).get(tp, 0)):
                        raise ValueError(f"--tap-pad sites {tp}: count does not match pad buffers")
                    q = tuple(rows[j])
                    if len(q) != 2 or not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                                               and math.isfinite(v) for v in q):
                        raise ValueError(f"--tap-pad sites {tp}: finite x/y required")
                    if site is not None and not site.legal(q):
                        raise ValueError(f"--tap-pad sites {tp}: declared site {q} is not legal")
                else:
                    q = (nd["x"] + 0.54 * (j + 1), nd["y"])
                    if site is not None and not site.legal(q):
                        q = site.nearest(q)
                place.append((inst, q[0], q[1]))
                parent_of[inst] = prev_inst
                prev_inst = inst
                src = o
            if clock_cell == "inv" and nd["inv_parity"]:
                inst, o = f"q{i}_{tp}", f"qn{i}_{tp}"
                cells.append(f"  {CLK_INV} {inst} (.A({src}), .Y({o}));")
                wires.append(o)
                npad = int((tap_pad or {}).get(tp, 0))
                q = (nd["x"] + 0.54 * (npad + 1), nd["y"])
                if site is not None and not site.legal(q):
                    q = site.nearest(q)
                place.append((inst, q[0], q[1]))
                parent_of[inst] = prev_inst
                prev_inst = inst
                src = o
            cells.append(f"  assign {tp} = {src};")
    v = ["module ctree (root, " + ", ".join(t[0] for t in tap_ports) + ");", "  input root;"]
    v += [f"  output {t[0]};" for t in tap_ports]
    v += [f"  wire {w};" for w in wires]
    v += [c for c in cells if not c.lstrip().startswith("assign")]
    v += [c for c in cells if c.lstrip().startswith("assign")]
    v.append("endmodule")
    return "\n".join(v) + "\n", place, tap_ports, node_buf, parent_of


EDGES_HDR = "# OT_EDGES v1"   # FLOW-ONEMODEL-2: both-edge clock arrival readout (see clock_edge_readout)


def clock_parity(verilog):
    """{instance: inverter-count parity (0/1) at its Y}, {tap port: parity} of a clock tree netlist (ctree.v form: one
    '.A(net), .Y(net)' cell per line, 'assign tap = net', source port 'root')"""
    drv = {}
    for m in re.finditer(r"^\s+(\S+) (\S+) \(\.A\((\S+)\), \.Y\((\S+)\)\);", verilog, re.M):
        drv[m.group(4)] = (m.group(1), m.group(2), m.group(3))
    par = {"root": 0}

    def parity(net):
        st = []
        while net not in par:
            st.append(net)
            net = drv[net][2]
        v = par[net]
        for n in reversed(st):
            v = (v + ("INV" in drv[n][0])) % 2
            par[n] = v
        return v
    cells = {drv[n][1]: parity(n) for n in drv}
    taps = {m.group(1): parity(m.group(2)) for m in re.finditer(r"assign (\S+) = (\S+);", verilog)}
    return cells, taps


def clock_edge_readout(verilog, path, period="833.333", cells="b*", tap_slew=False, prefix=""):
    """FLOW-ONEMODEL-2 (COORD 10-28): Tcl lines writing the clock arrivals of BOTH source edges at every tap AND every
    clock cell, so every die proof carries measured fall arrivals by construction (no rise + T/2 anywhere).
    PATH gets: header EDGES_HDR; 'T port late early [slew]' = source RISING edge at the tap (period - slack_max_rise,
    slack_min_rise: output delay 0, the root is a data input at 0, so both transitions launch at t=0); 'F port late
    early [slew]' = source FALLING edge at the tap (sampling instant T/2 + F); 'N cell late early' / 'M cell late
    early' = source rise / fall edge at the cell output, POLARITY-RESOLVED: at an odd-inverter-parity output the
    source rise is the Y fall (clock_parity), so N and M stay true source edges in buf, inv and inv2 trees.  Taps must
    be true polarity (die_trial adds the parity inverter); an odd tap raises.  prefix: instance prefix in the routed
    design (combo/clock-only GRT 'ck_'; printed names drop it).  cells: the get_cells glob(s) of the readout."""
    cp, tp = clock_parity(verilog)
    odd_t = sorted(t for t, v in tp.items() if v)
    if odd_t:
        raise ValueError(f"clock_edge_readout: {len(odd_t)} tap(s) of inverted polarity, e.g. {odd_t[:3]}")
    odd = sorted(prefix + c for c, v in cp.items() if v)
    nm = f"[string range [get_full_name $i] {len(prefix)} end]" if prefix else "[get_full_name $i]"
    sl = " [get_property $p slew_max_{e}]" if tap_slew else ""
    return ["set ot_odd [dict create" + "".join(f" {c} 1" for c in odd) + "]",
            f"set fh [open {path} w]",
            f"puts $fh \"{EDGES_HDR} T/N=source rise F/M=source fall (late early), polarity-resolved\"",
            # arrival at a port = period - slack (output delay 0); at a cell output pin = its arrival property
            "foreach p [get_ports t_*] { set n [get_full_name $p]; "
            "set smx [get_property $p slack_max_rise]; set smn [get_property $p slack_min_rise]; "
            f"puts $fh \"T $n [expr {{{period} - $smx}}] [expr {{$smn}}]" + sl.format(e="rise") + "\" }",
            "foreach p [get_ports t_*] { "
            f"puts $fh \"F [get_full_name $p] [expr {{{period} - [get_property $p slack_max_fall]}}] "
            "[get_property $p slack_min_fall]" + sl.format(e="fall") + "\" }",
            f"foreach i [get_cells {cells}] {{ set q [get_pins [get_full_name $i]/Y]; "
            "if {[dict exists $ot_odd [get_full_name $i]]} { set e fall; set g rise } else { set e rise; set g fall }; "
            f"puts $fh \"N {nm} [get_property $q arrival_max_$e] [get_property $q arrival_min_$e]\"; "
            f"puts $fh \"M {nm} [get_property $q arrival_max_$g] [get_property $q arrival_min_$g]\" }}",
            "close $fh"]


def clock_kit(P, out, leaf_um, rep_um, full_depth=False, site_legal=False, site_slide=False, regions=None, tree_form="htree",
              tree_opts=None, slice_spine=False, spine_top_leaf_um=50.0, slice_rows=None, tap_pad=None, clock_rc="ndr",
              slice_balance=False, region_dme=False, region_dme_only=None, region_dme_early=None,
              region_dme_early_ff=None, region_dme_snake=None, clock_cell="buf", region_dme_early_mode="hang",
              cell_paths=False, region_dme_early_merge_only=None, rep_actual_max=None):
    global EVEN_LEGS
    EVEN_LEGS = clock_cell == "inv2"
    out = Path(out)
    if region_dme_early and region_dme != "delay":
        raise ValueError("--region-dme-early needs --region-dme delay")
    if region_dme_early_ff and not region_dme_early:
        raise ValueError("--region-dme-early-ff needs --region-dme-early")
    if region_dme_early_mode not in ("hang", "merge"):
        raise ValueError("--region-dme-early-mode: hang | merge")
    if region_dme_early_mode != "hang" and not region_dme_early:
        raise ValueError("--region-dme-early-mode merge needs --region-dme-early")
    if region_dme_early_merge_only and not region_dme_early:
        raise ValueError("--region-dme-early-merge-only needs --region-dme-early")
    if region_dme_snake and not (region_dme == "delay" and tree_form == "link_htree" and site_slide and not slice_spine):
        raise ValueError("--region-dme-snake needs --region-dme delay with --tree-form link_htree --tree-site-slide")
    if region_dme_only and not (region_dme and tree_form == "link_htree" and site_slide and not slice_spine):
        raise ValueError("--region-dme-only needs --region-dme with --tree-form link_htree --tree-site-slide")
    wire_r, wire_c = WIRE_RC_1X if clock_rc == "1x" else (WIRE_R, WIRE_C)
    if region_dme and not slice_spine and not (tree_form == "link_htree" and site_slide):
        raise ValueError("--region-dme needs --slice-spine or --tree-form link_htree --tree-site-slide")
    if slice_balance and not slice_spine:
        raise ValueError("--slice-balance needs --slice-spine")
    out.mkdir(parents=True, exist_ok=True)
    taps = clock_taps(P)
    dme_early = None
    if region_dme_early:    # DIE-QC-8 opt-in: declared core early (TT) in DME model ps = early / measured-over-model ratio
        dme_early = {}
        for n, p in P.parts.items():
            for port, _, _, tp in S.core_taps(P, p["type"]):
                e = S.core_tap_early_ps(P, tp, "TT")
                if e > 0:
                    dme_early[(n, port)] = e / float(region_dme_early)
                    if region_dme_early_ff:   # DIE-QC-9 opt-in: corner-averaged target (TT and FF in model ps)
                        dme_early[(n, port)] = 0.5 * (dme_early[(n, port)]
                                                      + S.core_tap_early_ps(P, tp, "FF") / float(region_dme_early_ff))
    if slice_spine and tree_form != "htree":
        raise ValueError("--slice-spine and --tree-form %s are exclusive opt-ins" % tree_form)
    site = None
    slid_fallback = 0
    spine_info = None
    balanced = None
    if slice_spine:         # QC-SLICECLK-3 opt-in: spine-column region trees + shared top spine, no slide along a split axis
        if not regions:
            raise ValueError("--slice-spine needs --region-trees")
        site = SiteMap(P)
        nodes, spine_info = build_slice_spine_tree(P, taps, regions, leaf_um, site, spine_top_leaf_um,
                                                    json.loads(Path(slice_rows).read_text()) if slice_rows else None,
                                                    region_dme=region_dme,
                                                    dme_rep_um=rep_um if region_dme == "priced" else None,
                                                    dme_delay_rep_um=rep_um if region_dme == "delay" else None)
        moves = []
        for i, nd in sorted(nodes.items()):
            nd["req_xy"] = [nd["x"], nd["y"]]
            if site.legal((nd["x"], nd["y"])):
                continue
            par = (nodes[nd["parent"]]["x"], nodes[nd["parent"]]["y"]) if nd["parent"] is not None else None
            kids = [(nodes[k]["x"], nodes[k]["y"]) for k in nd["kids"]] + [tuple(t[2:4]) for t in nd["taps"]]
            q, c = balanced_site(site, (nd["x"], nd["y"]), par, kids, nd.get("split"))
            if q is None:
                slid_fallback += 1
                q, c = site.nearest((nd["x"], nd["y"])), None
            moves.append(dict(node=i, fixed=bool(nd.get("fixed")), um=round(_man(q, (nd["x"], nd["y"])), 3),
                              imbalance_um=c))
            nd["x"], nd["y"] = round_legal(site, q)
        if slice_balance:   # DIE-QC-3 opt-in: re-balance the legalized region trees (DME merge on legal sites, bug ii)
            balanced = balance_legalize(nodes, site, select=[i for i, nd in nodes.items()
                                                             if nd["parent"] is not None and nd.get("spine") != "top"])
        L = path_lengths(nodes)
        reg_len = defaultdict(list)
        for i, nd in nodes.items():
            for t in nd["taps"]:
                reg_len[regions[t[0]]].append(L[i] + abs(t[2] - nd["x"]) + abs(t[3] - nd["y"]))
        for rn, v in reg_len.items():     # Manhattan root -> tap incl. the leaf->tap leg (balance self-check, um)
            spine_info["regions"].setdefault(rn, {})["root_to_tap_um"] = [round(min(v), 1), round(max(v), 1)]
        imb = [m["imbalance_um"] for m in moves if m["imbalance_um"] is not None]
        spine_info["moved"] = dict(nodes=len(moves), fixed_nodes=sum(m["fixed"] for m in moves),
                                   max_um=max([m["um"] for m in moves], default=0.0),
                                   sum_um=round(sum(m["um"] for m in moves), 1),
                                   zero_cost=sum(1 for v in imb if v <= 1e-6), max_imbalance_um=max(imb, default=0.0))
    elif tree_form in ("link_fishbone", "link_htree"):
        to = dict(tree_opts or {})
        if tree_form == "link_htree":
            to.update(local="none" if region_dme and not region_dme_only else "htree", leaf_um=leaf_um)
            if region_dme_only:
                to["dme_only"] = set(region_dme_only)
        nodes = build_link_fishbone(P, taps, regions, json.loads(Path(to.pop("feed")).read_text()), **to)
    else:
        nodes = (build_spine_fishbone(P, taps, **(tree_opts or {})) if tree_form == "spine_fishbone" else
                 build_htree(P, taps, leaf_um, full_depth, regions))
    if site_slide and not slice_spine:          # opt-in: slide each buffer back along its OWN incoming leg (equal length by construction)
        site = SiteMap(P)
        for nd in nodes.values():
            nd["req_xy"] = [nd["x"], nd["y"]]
        for nd in nodes.values():
            if tree_form == "link_htree" and (nd.get("rib") is not None or (nd.get("region_root") is not None and (
                    not region_dme or (region_dme_only and nd["region_root"] not in region_dme_only)))):
                continue        # region H-tree nodes: balance_legalize below
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
        if tree_form == "link_htree" and region_dme_only:   # DIE-QC-4 opt-in: H-tree regions balanced, listed regions DME
            balanced = balance_legalize(nodes, site, skip_regions=set(region_dme_only))
            balanced["region_dme"] = attach_region_dme(nodes, site, taps, regions,
                                                       rep_um=rep_um if region_dme == "priced" else None,
                                                       delay_rep_um=rep_um if region_dme == "delay" else None,
                                                       only=set(region_dme_only), early=dme_early,
                                                       **({"snake": region_dme_snake} if region_dme_snake else {}),
                                                       **({"early_mode": region_dme_early_mode}
                                                          if region_dme_early_mode != "hang" else {}),
                                                       **({"merge_only": set(region_dme_early_merge_only)}
                                                          if region_dme_early_merge_only else {}))
        elif tree_form == "link_htree" and region_dme:   # DIE-QC-3 opt-in: legal-site DME region trees, no re-slide
            balanced = dict(region_dme=attach_region_dme(nodes, site, taps, regions,
                                                         rep_um=rep_um if region_dme == "priced" else None,
                                                         delay_rep_um=rep_um if region_dme == "delay" else None,
                                                         early=dme_early,
                                                         **({"snake": region_dme_snake} if region_dme_snake else {}),
                                                         **({"early_mode": region_dme_early_mode}
                                                            if region_dme_early_mode != "hang" else {}),
                                                         **({"merge_only": set(region_dme_early_merge_only)}
                                                            if region_dme_early_merge_only else {})))
        elif tree_form == "link_htree":
            balanced = balance_legalize(nodes, site)
    elif site_legal and not slice_spine:          # opt-in: every buffer/repeater on a legal channel site; a one-entry leaf drives AT its entry
        site = SiteMap(P)
        for nd in nodes.values():
            nd["req_xy"] = [nd["x"], nd["y"]]
            if tree_form == "link_htree" and (nd.get("rib") is not None or nd.get("region_root") is not None):
                continue        # region H-tree nodes: balance_legalize below
            if len(nd["taps"]) == 1 and site.legal(nd["taps"][0][2:4]):
                q = nd["taps"][0][2:4]
            else:
                q = site.nearest((nd["x"], nd["y"]))
            nd["x"], nd["y"] = round(q[0], 3), round(q[1], 3)
        if tree_form == "link_htree":
            balanced = balance_legalize(nodes, site)
    # Optional explicit plan bays share the existing tap-pad JSON; ordinary
    # {tap_port: count} inputs retain their old placement path.
    pad_sites = dict((tap_pad or {}).get("sites", {}))
    if pad_sites:
        tap_pad = {k: v for k, v in tap_pad.items() if k != "sites"}
        unknown_sites = sorted(set(pad_sites) - set(tap_pad))
        if unknown_sites:
            raise ValueError(f"--tap-pad sites: no count for {unknown_sites[:5]}")
        for port, rows in pad_sites.items():
            if len(rows) != int(tap_pad[port]):
                raise ValueError(f"--tap-pad sites {port}: count does not match pad buffers")
    elif tap_pad and "sites" in tap_pad:
        tap_pad = {k: v for k, v in tap_pad.items() if k != "sites"}
    v, place, tap_ports, node_buf, parent_of = tree_netlist(nodes, taps, rep_um, site, tap_pad, pad_sites,
                                                            **({"clock_cell": clock_cell} if clock_cell != "buf" else {}))
    if tap_pad:
        unknown = sorted(set(tap_pad) - {t[0] for t in tap_ports})
        if unknown:
            raise ValueError(f"--tap-pad: not a tap port of this tree: {unknown[:5]}")
    (out / "ctree.v").write_text(v)
    segs = []
    for i, nd in nodes.items():
        if nd["parent"] is not None:
            p = nodes[nd["parent"]]
            if nd.get("detour"):         # slid-root fix: the leg runs on its legal detour path
                for (ax, ay), (bx, by) in zip(nd["detour"], nd["detour"][1:]):
                    segs.append((ax, ay, bx, by, nd["level"]))
            else:
                segs.append((p["x"], p["y"], nd["x"], nd["y"], nd["level"]))
    # leaf -> tap last-mile legs (L: horizontal on M8, then vertical on M9)
    leaf_legs = []
    pad_xy = {inst: (x, y) for inst, x, y in place} if tap_pad else {}
    for tp, x, y, part, port, i in tap_ports:
        nd = nodes[i]
        count = int((tap_pad or {}).get(tp, 0))
        prev = (nd["x"], nd["y"])
        for j in range(count):
            q = pad_xy[f"p{i}_{tp}_{j}"]
            leaf_legs.append((*prev, *q))
            prev = q
        leaf_legs.append((*prev, x, y))
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
    tcl += [f"set_wire_rc -signal -resistance {wire_r:.6e} -capacitance {wire_c:.6e}",
            f"set_wire_rc -clock -resistance {wire_r:.6e} -capacitance {wire_c:.6e}",
            "estimate_parasitics -placement",
            "create_clock -name vclk -period 833.333",
            f"set_driving_cell -lib_cell {BUF} -pin Y [get_ports root]",
            "set_input_delay 0 -clock vclk [get_ports root]",
            f"set_load {TAP_LOAD_FF} [all_outputs]",
            "set_output_delay 0 -clock vclk [all_outputs]",
            # FLOW-ONEMODEL-2: both source edges at every tap and clock cell (polarity-resolved, clock_edge_readout)
            *clock_edge_readout(v, "/work/clock/arr_$::env(CORNER).txt", period="833.333",
                                cells="{b* r* p*}" if any(int(x) > 0 for x in (tap_pad or {}).values()) else "b*",
                                tap_slew=any(int(x) > 0 for x in (tap_pad or {}).values())),
            "report_checks -path_delay max -group_path_count 1 -format full -fields {cap slew fanout}",
            "puts OT_DONE"]
    (out / "ctree.tcl").write_text("\n".join(tcl) + "\n")
    meta = dict(leaf_um=leaf_um, rep_um=rep_um, **({"full_depth": True} if full_depth else {}),
                **({"tree_form": tree_form, "spine_dme": nodes[0].get("spine_dme"),
                    **({"link_feed": nodes[0]["link_feed"]} if "link_feed" in nodes[0] else {})}
                   if tree_form != "htree" else {}),
                **({"region_trees": len({n.get("region_root") for n in nodes.values()} - {None})} if regions else {}), buffer=BUF, clock_cell=clock_cell, wire_r_kohm_um=wire_r, wire_c_ff_um=wire_c,
                **({"clock_rc": clock_rc} if clock_rc != "ndr" else {}),
                tap_load_ff=TAP_LOAD_FF, nodes=len(nodes), leaves=sum(1 for n in nodes.values() if n["taps"]),
                repeaters=sum(1 for i, *_ in place if i.startswith("r")), taps=len(tap_ports),
                wire_um=round(sum(abs(a - c) + abs(b - d) for a, b, c, d, _ in segs) +
                              sum(abs(a - c) + abs(b - d) for a, b, c, d in leaf_legs), 1),
                levels=max(n["level"] for n in nodes.values()))
    if tap_pad:
        meta["tap_pad"] = dict(taps=sum(1 for v in tap_pad.values() if v), cells=sum(int(v) for v in tap_pad.values()),
                               max_per_tap=max(int(v) for v in tap_pad.values()), cell=BUF)
    if spine_info is not None:
        meta["slice_spine"] = spine_info
        meta["region_trees"] = len(spine_info["regions"])
    if site is not None:
        bad = {}
        for inst, x, y in place:
            w = site.why((x, y))
            if w:
                bad[w] = bad.get(w, 0) + 1
        meta["site_legal"] = dict(mode="slice_spine" if slice_spine else "slide" if site_slide else "nearest", slide_fallbacks=slid_fallback,
                                  cells=len(place), illegal=bad, forbidden_rects=len(site.forb),
                                  moved_nodes=sum(1 for n in nodes.values() if [n["x"], n["y"]] != n["req_xy"]),
                                  **({"balance": balanced} if balanced is not None else {}))
        # slid-root fix report (new file; kit.json changes only when a leg is detoured): legal-detour legs and every leg
        # whose longest unrepeated span still exceeds rep_um
        xy = {inst: (x, y) for inst, x, y in place}
        spans = defaultdict(float)
        for inst, drv in parent_of.items():
            leg = int(inst[1:].split("_")[0])
            a, b = xy[inst], xy[drv]
            spans[leg] = max(spans[leg], abs(a[0] - b[0]) + abs(a[1] - b[1]))
        det = {i: n["detour_um"] for i, n in nodes.items() if n.get("detour")}
        over = sorted(((round(v, 1), i) for i, v in spans.items() if v > rep_um + 1e-6), reverse=True)
        (out / "leg_spans.json").write_text(json.dumps(dict(rep_um=rep_um, detoured_legs=det, legs_over_rep=len(over),
                                                            worst=[dict(node=i, span_um=v) for v, i in over[:20]])) + "\n")
        if det:
            meta["site_legal"]["detoured_legs"] = len(det)
            meta["site_legal"]["detour_added_um"] = round(sum(det.values()), 1)
    tree = dict(meta=meta, nodes={i: {k: v for k, v in n.items() if k != "taps"} | dict(ntaps=len(n["taps"]))
                                  for i, n in nodes.items()},
                taps=[dict(port=tp, part=part, tap=port, xy=[x, y], node=i) for tp, x, y, part, port, i in tap_ports],
                node_buf=node_buf, parent_of=parent_of, sites={inst: [round(x, 3), round(y, 3)] for inst, x, y in place})
    if cell_paths or any(int(v) > 0 for v in (tap_pad or {}).values()):
        # DIE-S81-15 --cell-paths (opt-in): the same physical paths without pads, so every leg repeater is a tree-path
        # node in trial_tap_arrivals (start-tree retime candidates at the EXISTING repeaters; netlist unchanged).
        # Physical paths include every repeater and final pad. The geometric
        # node id is retained for region membership, never substituted for the
        # actual padded tap driver during CPPR / depth accounting.
        def cell_path(cell):
            path = [cell]
            while cell in parent_of:
                cell = parent_of[cell]
                path.append(cell)
            return list(reversed(path))
        tree["node_stages"] = {cell: len(cell_path(cell)) for cell, *_ in place}
        for t in tree["taps"]:
            count = int((tap_pad or {}).get(t["port"], 0))
            t["driver"] = f"p{t['node']}_{t['port']}_{count - 1}" if count else node_buf[t["node"]]
            t["path"] = cell_path(t["driver"])
            t["stages_from_root"] = len(t["path"])
    if rep_actual_max is not None:
        from clock_reach import actual_reach
        reach = actual_reach(tree, rep_actual_max)
        # Keep the failed census even though no complete clock tree is published.
        with open(out / "actual_reach.json", "x") as fh:
            json.dump(reach, fh, indent=1)
        if reach["verdict"] != "PASS":
            raise ValueError(f"OT_CLOCK_ACTUAL_REACH {reach['over_count']} edges over {rep_actual_max} um; "
                             f"{len(reach['missing_sites'])} missing sites; see {out / 'actual_reach.json'}")
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


FT_LAYER_CLASS = {"M4": 0, "M5": 0, "M6": 1, "M7": 1}


def ft_layer_audit(P):
    """F1 (COORD 10-27 19:12, KV-PLAN-DELTA-8): one pin layer per FT bit end to end.  For every type ft slot, compare the
    layer class (M4/M5 lower, M6/M7 upper) of each bit's input-face pin with its output-face pin.  The die abstract
    writes the plan face pins unchanged (they are the hardened pins), so a class switch inside a partition is a plan
    property; this reports it (ft_station_probe derives station layers from the input face).  Returns
    dict(slot_bits, class_switch_bits, by_type{type: switches})."""
    tot = sw = 0
    by = {}
    for tn, t in sorted(P.types.items()):
        if not t.get("ft_slots"):
            continue
        if not any(p["type"] == tn for p in P.parts.values()):
            continue
        pins = defaultdict(dict)
        for bus, bit, ln, *_ in gen_phys.type_pins(P, tn):
            pins[bus][bit] = ln
        n = 0
        for sl in t["ft_slots"]:
            i, o = pins.get(sl["name"] + "_i", {}), pins.get(sl["name"] + "_o", {})
            for b in sorted(set(i) & set(o)):
                tot += 1
                if FT_LAYER_CLASS.get(i[b], -1) != FT_LAYER_CLASS.get(o[b], -2):
                    n += 1
        if n:
            by[tn] = n
        sw += n
    return dict(slot_bits=tot, class_switch_bits=sw, by_type=by)


def ft_nets(P):
    """[(inst, slot, nbits_connected, in_bits, out_bits)] and the die route netlist connections per instance."""
    rows = []
    for n, p in sorted(P.parts.items()):
        t = P.types[p["type"]]
        for s in t.get("ft_slots", []) or []:
            rows.append((n, s["name"], int(s["width"]), int(s.get("stations", 1))))
    return rows


def channel_ports(P):
    """INFRA-FIRST-QC-R21 (NUMBER-CHECK-QC-R20): partition<->partition ports that cross a planned die channel
    (P.channel_of(pid), die.channels[].ports).  Their two faces are NOT abutted (e.g. the 43.2-um QC centre clock
    channel), so they need die-top wires: [(pid, src part, src bus, dst part, dst bus, pin count)]."""
    out = []
    for pid, pr in sorted(P.ports.items()):
        if S.DIE_PART in (pr["src"]["part"], pr["dst"]["part"]) or not P.channel_of(pid):
            continue
        out.append((pid, pr["src"]["part"], pr["src"]["bus"], pr["dst"]["part"], pr["dst"]["bus"], S.port_pins_count(pr)))
    return out


def abutted_pin_check(P, type_pin_xy=None, tol=1e-3):
    """INFRA-FIRST-QC-R21: every bit of every ABUTTED partition<->partition port (no die channel) must land on the
    SAME die point and layer from both sides, using the TYPE pin tables (gen_phys.type_pins, taken from each type's
    first instance) transformed into each instance's die frame.  A miss = an abutted seam that only 'touches' in the
    plan arithmetic but not in the hardened pins.  Returns dict(ports, bits, bad_bits, bad_ports, examples)."""
    if type_pin_xy is None:
        type_pin_xy = {}
        for tn in P.types:
            if any(p["type"] == tn for p in P.parts.values()):
                type_pin_xy[tn] = {(bus, bit): (ln, x, y) for bus, bit, ln, x, y, _ in gen_phys.type_pins(P, tn)}
    ports = bits = 0
    bad, badp = [], set()
    for pid, pr in sorted(P.ports.items()):
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if S.DIE_PART in (a, b) or P.channel_of(pid):
            continue
        ports += 1
        ta, tb = type_pin_xy[P.parts[a]["type"]], type_pin_xy[P.parts[b]["type"]]
        for bit in range(S.port_pins_count(pr)):
            bits += 1
            pa, pb = ta.get((pr["src"]["bus"], bit)), tb.get((pr["dst"]["bus"], bit))
            if pa is None or pb is None:
                bad.append((pid, bit, "missing pin", pa, pb))
                badp.add(pid)
                continue
            xa, ya = P.to_die(a, pa[1:])
            xb, yb = P.to_die(b, pb[1:])
            if pa[0] != pb[0] or abs(xa - xb) > tol or abs(ya - yb) > tol:
                bad.append((pid, bit, f"{pa[0]}@({xa:.4f},{ya:.4f}) vs {pb[0]}@({xb:.4f},{yb:.4f})", None, None))
                badp.add(pid)
    return dict(ports=ports, bits=bits, bad_bits=len(bad), bad_ports=len(badp), examples=[list(e[:3]) for e in bad[:20]],
                verdict="PASS" if not bad else "FAIL")


def route_netlist(P, type_bits, channel_nets=True, landing_infra=False):
    """die route netlist: every instance's ft slots S_i[b] -> S_o[b] joined (one net per bit), arst_n on the reset
    spine.  type_bits {type: {bus: nbits}} from the plan pins.
    INFRA-FIRST-QC-R21 (NUMBER-CHECK-QC-R20): every partition<->partition port that crosses a planned die channel
    (channel_ports) joins its src bus pin to its dst bus pin per bit, so the die GRT routes the hop across the channel
    (before R21 these were counted as abutted and left out of the GRT netlist).  When an end of the port is an ft slot
    bus of that instance (the hop continues a feedthrough), the hop JOINS that ft net (one electrical net: S_i -> S_o
    -> across the channel -> receiver), never a second driver on the same pin; otherwise it is a new ch_<port> net.
    channel_nets=False = the pre-R21 netlist.  Returns (verilog, ft bits); route_netlist.channel = dict(ports, bits,
    new_net_bits, ft_joined_bits) of the channel hops."""
    landing = None
    if landing_infra:
        import landing_route
        landing = landing_route.network(P)
    provisional = landing['provisional'] if landing else []
    v = [f"module {sv(P.name)}_route ({', '.join(['rst_n']+provisional)});", "  input rst_n;"]
    if landing:
        v += [f'  input {name};' for name in landing['boundary_inputs']]
        v += [f'  output {name};' for name in landing['boundary_outputs']]
    if landing:
        v += [f'  wire {name};' for name in landing['wires']]
    insts, nft = [], 0
    smod = standin_module_names(P)
    width, ftw, slots = {}, {}, {}
    for n, p in sorted(P.parts.items()):
        tn = p["type"]
        sl = []
        for s_ in P.types[tn].get("ft_slots", []) or []:
            bi, bo = type_bits[tn].get(s_["name"] + "_i", 0), type_bits[tn].get(s_["name"] + "_o", 0)
            k = min(bi, bo)
            if k <= 0:
                continue
            w = f"ft_{sv(n)}__{sv(s_['name'])}"
            width[w] = k
            ftw[(n, s_["name"] + "_i")] = ftw[(n, s_["name"] + "_o")] = w
            sl.append((s_["name"], w, k))
        slots[n] = sl
    parent = {}

    def find(w):
        while parent.get(w, w) != w:
            w = parent[w]
        return w

    def union(x, y):
        x, y = find(x), find(y)
        if x == y:
            return
        # root preference: an ft wire (keeps the pre-R21 ft names), then the smaller name
        kx, ky = (not x.startswith("ft_"), x), (not y.startswith("ft_"), y)
        if ky < kx:
            x, y = y, x
        parent[y] = x
    extra = {}            # (inst, bus) -> wire, channel-port ends that are not ft slot buses
    nch = nchb = newb = joinb = 0
    for pid, a, ba, b, bb, k in (channel_ports(P) if channel_nets and getattr(P, "ports", None) else []):
        for part, bus in ((a, ba), (b, bb)):
            have = type_bits[P.parts[part]["type"]].get(bus, 0)
            if have != k:
                raise ValueError(f"route_netlist: channel port {pid}: {part}.{bus} has {have} pins, port needs {k} "
                                 "(bus shared by several ports: needs bit-slice connections)")
            if (part, bus) in extra:
                raise ValueError(f"route_netlist: {part}.{bus} is an end of two channel ports")
        w = f"ch_{sv(pid)}"
        width[w] = k
        ends = [ftw.get((a, ba)), ftw.get((b, bb))]
        for e in ends:
            if e is not None:
                if width[e] != k:
                    raise ValueError(f"route_netlist: channel port {pid} ({k} bits) joins ft net {e} ({width[e]} bits)")
                union(w, e)
        if ends[0] is None:
            extra[(a, ba)] = w
        if ends[1] is None:
            extra[(b, bb)] = w
        nch += 1
        nchb += k
        joinb += k if any(e is not None for e in ends) else 0
        newb += 0 if any(e is not None for e in ends) else k
    route_netlist.channel = dict(ports=nch, bits=nchb, new_net_bits=newb, ft_joined_bits=joinb)
    for w in sorted({find(x) for x in extra.values()}):
        if not w.startswith("ft_"):
            v.append(f"  wire [{width[w] - 1}:0] {w};")
    for n, p in sorted(P.parts.items()):
        tn = p["type"]
        conns = [".arst_n(rst_n)"] + [f".{bus}({find(w)})" for (pn, bus), w in sorted(extra.items()) if pn == n]
        if landing:
            conns += [f'.{pin}({wire})' for pin,wire in sorted(landing['bindings'].get(n,{}).items())]
        for sname, w, k in slots[n]:
            if find(w) == w:
                v.append(f"  wire [{k - 1}:0] {w};")
            conns.append(f".{sname}_i({find(w)})")
            conns.append(f".{sname}_o({find(w)})")
            nft += k
        insts.append(f"  {smod[tn]} {sv(n)} ({', '.join(conns)});")
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
    # KV-GRT-STALL 10-27: congestion-only die GRT, no timing-driven critical-net slack pass (see die_clock_mesh combo)
    t += ["global_route -congestion_iterations 50 -critical_nets_percentage 0 -allow_congestion -verbose "
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


def bump_contract(P):
    """One optional plan-owned source geometry for die and cropped PG emitters."""
    pg = P.die.get("pg", {}) if P is not None else {}
    c = dict(pg.get("bumps", {}))
    c.setdefault("pitch_um", 150.0)
    c.setdefault("pad_um", 0.0)
    for k in ("pitch_um", "pad_um", "edge_margin_um"):
        if k not in c:
            continue
        if isinstance(c[k], bool) or not isinstance(c[k], (int, float)) or not math.isfinite(c[k]) or c[k] < 0:
            raise ValueError("invalid PG bump " + k)
    if c["pitch_um"] <= 0 or c["pad_um"] >= c["pitch_um"]:
        raise ValueError("PG bump pitch must exceed its nonnegative pad width")
    if "edge_margin_um" in c and c["edge_margin_um"] < c["pad_um"] / 2:
        raise ValueError("PG edge margin must keep the complete pad inside the die")
    for fd in c.get("fields", []):
        _check_bump_field(fd, c)
    return c


def _check_bump_field(fd, base):
    """QC-PG-5 (OWNER 10-28 option c): an opt-in fine-pitch power-bump FIELD over a die region (e.g. the QC A0 array,
    75-um bumps / 37.5-um pads). rects_um = the field (union of rects); the field lattice is die-centred like the base
    lattice; every base bump closer than keep_um (Chebyshev) to a field bump is dropped."""
    for k in ("pitch_um", "pad_um", "keep_um"):
        v = fd.get(k)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError("invalid PG bump field " + k)
    if fd["pitch_um"] <= 0 or fd["pad_um"] >= fd["pitch_um"]:
        raise ValueError("PG bump field pitch must exceed its nonnegative pad width")
    if fd["keep_um"] < (fd["pad_um"] + base["pad_um"]) / 2:
        raise ValueError("PG bump field keep_um must separate a field pad from a base pad")
    rs = fd.get("rects_um")
    if not isinstance(rs, list) or not rs or any(not isinstance(r, list) or len(r) != 4 or not (r[0] < r[2] and r[1] < r[3])
                                                 for r in rs):
        raise ValueError("PG bump field needs nonempty rects_um [x0,y0,x1,y1]")


def bump_grid(P, io, pitch=None, size=60.0, pads=False):
    """C4 power bumps: a regular grid at `pitch` (alternating VDD / VSS by row+col parity) inside the die, minus the
    seal ring / corner keep-out channels and the die IO windows (signal bumps).  -> [(net, x, y)]
    Opt-in die.pg.bumps.fields (QC-PG-5): fine-pitch fields replace the base bumps near them; pads=True returns
    (net, x, y, pad_um) so bumps_tcl applies each bump's own pad.  No fields -> output byte-identical."""
    # between-only crossing channels (R16 delta: seam ports declared by partition pair) carry no rect of their own
    keep = [c["rect_um"] for c in P.die.get("channels", []) if "rect_um" in c] + [w["rect_um"] for w in io]
    out = []
    cfg = bump_contract(P)
    pitch = cfg["pitch_um"] if pitch is None else pitch
    if isinstance(pitch, bool) or not math.isfinite(pitch) or pitch <= cfg["pad_um"]:
        raise ValueError("PG bump pitch must exceed the pad width")
    if "edge_margin_um" in cfg:
        m = cfg["edge_margin_um"]
        nx, ny = int((P.W - 2*m) // pitch) + 1, int((P.H - 2*m) // pitch) + 1
        if min(nx, ny) < 1:
            raise ValueError("PG edge margin leaves no bump sites")
    else:
        nx, ny = int(P.W // pitch), int(P.H // pitch)
    x0 = (P.W - (nx - 1) * pitch) / 2
    y0 = (P.H - (ny - 1) * pitch) / 2
    for i in range(nx):
        for j in range(ny):
            x, y = x0 + i * pitch, y0 + j * pitch
            half = cfg["pad_um"] / 2
            if any((r[0] <= x <= r[2] and r[1] <= y <= r[3]) if half == 0 else
                   (x+half > r[0] and x-half < r[2] and y+half > r[1] and y-half < r[3]) for r in keep):
                continue
            out.append(("VDD" if (i + j) % 2 == 0 else "VSS", round(x, 3), round(y, 3)))
    if cfg.get("fields"):
        out = _field_bumps(P, cfg, out, keep, (x0, y0))
        return out if pads else [b[:3] for b in out]
    return [b + (cfg["pad_um"],) for b in out] if pads else out


def _field_bumps(P, cfg, base, keep, origin):
    """Base bumps (pad cfg pad_um) minus those within keep_um (Chebyshev) of a field bump, plus every field's bumps
    (lattice at the field pitch anchored on the base lattice origin, so a 75-um field lands on every 150-um base site;
    centre inside a field rect; complete pad inside the die and outside channels / IO windows)."""
    fine = []
    for fd in cfg["fields"]:
        p, half = fd["pitch_um"], fd["pad_um"] / 2
        x0, y0 = origin[0] % p, origin[1] % p
        x0, y0 = (x0 + p if x0 < half else x0), (y0 + p if y0 < half else y0)
        nx, ny = int((P.W - half - x0) // p) + 1, int((P.H - half - y0) // p) + 1
        for r in fd["rects_um"]:
            i0, i1 = max(0, math.ceil((r[0] - x0) / p - 1e-9)), min(nx - 1, math.floor((r[2] - x0) / p + 1e-9))
            j0, j1 = max(0, math.ceil((r[1] - y0) / p - 1e-9)), min(ny - 1, math.floor((r[3] - y0) / p + 1e-9))
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    x, y = x0 + i * p, y0 + j * p
                    if any(x+half > k[0] and x-half < k[2] and y+half > k[1] and y-half < k[3] for k in keep):
                        continue
                    fine.append(("VDD" if (i + j) % 2 == 0 else "VSS", round(x, 3), round(y, 3), fd["pad_um"], fd["keep_um"]))
    fine = sorted(set(fine), key=lambda b: (b[1], b[2]))
    cell = max(b[4] for b in fine) if fine else 1.0
    hsh = {}
    for b in fine:
        hsh.setdefault((int(b[1] // cell), int(b[2] // cell)), []).append(b)
    def near(x, y):
        ci, cj = int(x // cell), int(y // cell)
        return any(max(abs(x - b[1]), abs(y - b[2])) < b[4] for di in (-1, 0, 1) for dj in (-1, 0, 1)
                   for b in hsh.get((ci + di, cj + dj), ()))
    return [(n, x, y, cfg["pad_um"]) for n, x, y in base if not near(x, y)] + [b[:4] for b in fine]


def bumps_tcl(P, bumps, size=4.0, pad_um=None):
    """Attach each source to actual M9 metal of its own net after pdngen.

    Stripe origins depend on the floorplan core origin and pdngen net phase.
    Computing them from the plan offset produced isolated voltage-source pins.
    Optional die.pg.bumps.pad_um uses the qualified finite ideal pad overlap model
    from HEAD-5 (33ac225c10); a pad missing same-net metal fails, never substitutes a point source.
    """
    pad_um = bump_contract(P)["pad_um"] if pad_um is None else pad_um
    if isinstance(pad_um, bool) or not math.isfinite(pad_um) or pad_um < 0:
        raise ValueError("PG pad width must be finite and nonnegative")
    if any(len(b) > 3 for b in bumps):        # per-bump pads (die.pg.bumps.fields, bump_grid(pads=True))
        bp = [(b[0], b[1], b[2], b[3] if len(b) > 3 else pad_um) for b in bumps]
        if any(isinstance(b[3], bool) or not math.isfinite(b[3]) or b[3] <= 0 for b in bp):
            raise ValueError("per-bump PG pads must be finite and positive")
        return _pad_bumps_tcl([b[:3] for b in bp], pad_um, pads=[b[3] for b in bp])
    if pad_um > 0:
        return _pad_bumps_tcl(bumps, pad_um)
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


def _pad_bumps_tcl(bumps, pad_um, pads=None):
    """bumps_tcl with real bump pads (see bumps_tcl): one dbBTerm per bump, one dbBPin per pad x same-net M9 overlap."""
    t = ["set block [ord::get_db_block]",
         "foreach ot_auto_name {VDD VSS} { set ot_auto_bt [$block findBTerm $ot_auto_name]; "
         "if {$ot_auto_bt ne \"NULL\"} { if {[$ot_auto_bt getSigType] ni {POWER GROUND}} "
         "{ error \"refusing to remove non-PG boundary port $ot_auto_name\" }; "
         "odb::dbBTerm_destroy $ot_auto_bt } }",
         "set m9 [[ord::get_db_tech] findLayer M9]",
         "set bump_dbu [[ord::get_db_tech] getDbUnitsPerMicron]",
         "set bump_shapes {}",
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
         "}",
         "set pad_pins 0; set pad_fallback 0; set pad_area 0.0",
         f"set pad_half [expr {{round({pad_um:g}*$bump_dbu/2.0)}}]",
         "proc ot_pad {net k bx by {pum {}}} {",
         "  global block m9 bump_dbu bump_shapes pad_pins pad_fallback pad_area pad_half",
         "  if {$pum ne {}} { set pad_half [expr {round($pum*$bump_dbu/2.0)}] }",
         "  set bx [expr {round($bx*$bump_dbu)}]; set by [expr {round($by*$bump_dbu)}]",
         "  set px0 [expr {$bx-$pad_half}]; set px1 [expr {$bx+$pad_half}]; set py0 [expr {$by-$pad_half}]; set py1 [expr {$by+$pad_half}]",
         "  set hits {}; set best {}; set bd 1e30",
         "  foreach rect [dict get $bump_shapes $net] {",
         "    lassign $rect x0 y0 x1 y1",
         "    set ix0 [expr {max($x0,$px0)}]; set ix1 [expr {min($x1,$px1)}]; set iy0 [expr {max($y0,$py0)}]; set iy1 [expr {min($y1,$py1)}]",
         "    if {$ix1 > $ix0 && $iy1 > $iy0} { lappend hits [list $ix0 $iy0 $ix1 $iy1] }",
         "    set d [expr {abs(($x0+$x1)/2.0-$bx)}]; if {$d < $bd && $y0 <= $by && $by <= $y1} { set bd $d; set best $rect }",
         "  }",
         "  if {![llength $hits]} {",
         "    error \"OT_BUMPS pad misses actual same-net M9 metal: $net $k\"",
         "  }",
         "  set bt [odb::dbBTerm_create [$block findNet $net] ${net}_b$k]; $bt setIoType INOUT",
         "  $bt setSigType [expr {$net eq {VDD} ? {POWER} : {GROUND}}]",
         "  foreach h $hits { set bp [odb::dbBPin_create $bt]; odb::dbBox_create $bp $m9 {*}$h; $bp setPlacementStatus FIRM; incr pad_pins",
         "    lassign $h a b c d; set pad_area [expr {$pad_area + ($c-$a)*($d-$b)/double($bump_dbu*$bump_dbu)}] }",
         "}"]
    if pads is None:
        t += [f"ot_pad {net} {k} {x:g} {y:g}" for k, (net, x, y) in enumerate(bumps)]
    else:
        t += [f"ot_pad {net} {k} {x:g} {y:g} {p:g}" for k, ((net, x, y), p) in enumerate(zip(bumps, pads))]
    t.append(f'puts "OT_BUMPS pad_um {pad_um:g} bumps {len(bumps)} pad_pins $pad_pins pad_fallback $pad_fallback '
             f'm9_contact_um2 [format %.1f $pad_area]"' if pads is None else
             f'puts "OT_BUMPS mixed pads {" ".join(f"{p:g}:{pads.count(p)}" for p in sorted(set(pads)))} bumps {len(bumps)} '
             f'pad_pins $pad_pins pad_fallback $pad_fallback m9_contact_um2 [format %.1f $pad_area]"')
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
    # A sender-min/plan-demand input has no legacy receiver padding guarantee.
    # Leave its face flop bare: this is a pessimistic diagnostic, never a parent
    # hold proof. Fallback inputs and reset retain the legacy contract.
    parent_inputs = gen_phys.input_hold_min(P, tn)
    for bus, bit, ln, x, y, f in sorted(pins, key=lambda p: (p[0], p[1])):
        ck = ckn[near(x, y)]
        if dirs.get(bus) == "in" and hold_contract and bus not in parent_inputs:
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
    # Pin-register-free partition ports (STANDIN-PADPORT 10-27), carried like the KV hard-IP line side (bind.py
    # bump_pins: a die port with no timing arc of ours): off-die PHY pads (plan types[].pads, e.g. ot_s81hd_serdes
    # pma_*: PHY-side timing, die.io phy_macro bumps) and per-instance ID straps (types[].id_straps: tied at the die
    # top, kit SDC set_false_path -from).  Declared ports only: no face flop, no contract cell, so die STA sees the
    # connection (no 'port not found') and times nothing through it.  Never tied off or dropped here.
    free = [(gen_rtl.sv_id(pd["name"]), pd["dir"], pd["width"]) for pd in t.get("pads", []) or []] + \
        [(sp["name"], "in", sp["width"]) for sp in (t.get("id_straps", []) or []) + (t.get("count_straps", []) or [])]
    for n, d, w in free:
        ports.append(f"  {'input' if d == 'in' else 'output'} [{w - 1}:0] {n};")
    names = tapn + [n for n, _, _ in rin] + [n for n, _, _ in rout] + sorted(bits) + [n for n, _, _ in free]
    v = [f"module {t['module']} ({', '.join(names)});"] + ports + ckwires
    v += [f"  wire q{i};" for i in range(k) if f".QN(q{i})" in cells[i]]
    v += [f"  wire d{i};" for i in range(k) if f".Y(d{i})" in cells[i]]
    v += ckcells + cells + ["endmodule"]
    if parent_inputs:
        v.insert(0, "// OT_IO_HOLD NEEDS_PARENT: bare diagnostic inputs " + ",".join(sorted(parent_inputs)))
    return "\n".join(v) + "\n", k


def standin_module_names(P):
    """{type: stand-in module name}.  Plan types that share one RTL module (slice variants, e.g. QC slw_fw_v1/v2/v3)
    have different pins (buses, ft slots, rst_o / start_o sets), so ONE PARTS/<module> stand-in (last type written)
    left the other variants' die-top connections dangling ('port not found': 308 on QC plan 441d).  Each such type
    gets its own stand-in module <module>__<type>; types with a unique module keep the module name (closed views)."""
    from collections import Counter
    n = Counter(t["module"] for t in P.types.values())
    return {tn: (t["module"] if n[t["module"]] == 1 else f"{t['module']}__{tn}") for tn, t in P.types.items()}


def retarget_lef_macro(text, old, new):
    """Alias one closed LEF macro without changing pins, OBS or its plan RTL name."""
    if old == new:
        return text
    for keyword in ('MACRO', 'END'):
        pat = re.compile(r'^(\s*' + keyword + r'\s+)' + re.escape(old) + r'(\s*)$', re.M)
        text, count = pat.subn(lambda m: m.group(1) + new + m.group(2), text)
        if count != 1:
            raise ValueError(f'closed LEF: expected one {keyword} {old}, found {count}')
    return text


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
def logged_stages(stages):
    """Run all diagnostic stages, log each tool status, return the first failure.

    Dollar signs are escaped for run_sh's enclosing double-quoted Docker command.
    Logging and a later successful corner must never erase an earlier tool error.
    """
    parts = ["ot_stages_rc=0"]
    for command, log in stages:
        parts += [f"{command} > {log} 2>&1", "ot_stage_rc=\\$?",
                  f"echo EXIT \\$ot_stage_rc >> {log}",
                  "if [ \\$ot_stage_rc != 0 ] && [ \\$ot_stages_rc = 0 ]; then ot_stages_rc=\\$ot_stage_rc; fi"]
    parts.append("(exit \\$ot_stages_rc)")
    return "; ".join(parts)


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
              tree_form="htree", tree_opts=None, slice_spine=False, spine_top_leaf_um=50.0, slice_rows=None, tap_pad=None,
              clock_rc="ndr", slice_balance=False, region_dme=False, region_dme_only=None, region_dme_early=None,
              region_dme_early_ff=None, region_dme_snake=None, clock_cell="buf", region_dme_early_mode="hang",
              cell_paths=False, region_dme_early_merge_only=None, rep_actual_max=None, landing_infra=False):
    raw = S.load(plan_path)
    P = S.Plan(raw, Path(plan_path))   # plan-relative sidecars (core pins_file of the reset wavefront; as claude/die-proto-1025@bd51e6310)
    landing = None
    if landing_infra:
        import landing_route
        landing = landing_route.network(P)
    plan_dir = Path(plan_path).parent
    out = Path(out)
    for d in ("abstracts", "grt", "clock", "psm", "sta/parts"):
        (out / d).mkdir(parents=True, exist_ok=True)
    meta = dict(plan=str(plan_path), plan_sha256=S.sha256_file(plan_path) if hasattr(S, "sha256_file") else None,
                die=P.name, outline_um=[P.W, P.H], area_mm2=round(P.W * P.H * 1e-6, 2), parts=len(P.parts),
                types=len(P.types), ports=len(P.ports), lanes=len(raw.get("lanes", [])), image=IMAGE)
    import hashlib
    meta["plan_sha256"] = hashlib.sha256(Path(plan_path).read_bytes()).hexdigest()
    # Abstracts need one physical master per type, like the STA stand-ins.
    # Shared RTL names can have different outlines, pins and internal core OBS.
    smod = standin_module_names(P)
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
            txt = retarget_lef_macro(v.read_text(), t["module"], smod[tn])
            if landing_infra:
                expected = {p['name'] for p in t.get('clock',{}).get('landing_contract',{}).get('pins',[])}
                found = set(re.findall(r'^\s*PIN\s+(\S+)',txt,re.M))
                if expected-found:
                    raise ValueError(f'{tn}: closed view omits landing pins: {sorted(expected-found)[:8]}')
            (out / "abstracts" / f"{smod[tn]}.lef").write_text(txt)
            ab[tn] = dict(source="closed view", path=str(v))
        else:
            txt, st = abstract_lef(P, tn, islands=iw.get(tn), module_name=smod[tn], landing_infra=landing_infra)
            (out / "abstracts" / f"{smod[tn]}.lef").write_text(txt)
            ab[tn] = dict(source="plan abstract", **st)
        ab[tn]["physical_module"] = smod[tn]
        lefs.append(f"{smod[tn]}.lef")
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
                                           tree_form=tree_form, tree_opts=tree_opts, slice_spine=slice_spine,
                                           spine_top_leaf_um=spine_top_leaf_um, slice_rows=slice_rows, tap_pad=tap_pad,
                                           clock_rc=clock_rc, slice_balance=slice_balance, region_dme=region_dme,
                                           region_dme_only=region_dme_only, region_dme_early=region_dme_early,
                                           region_dme_early_ff=region_dme_early_ff, region_dme_snake=region_dme_snake,
                                           **({"rep_actual_max": rep_actual_max} if rep_actual_max is not None else {}),
                                           **({"clock_cell": clock_cell} if clock_cell != "buf" else {}),
                                           **({"region_dme_early_mode": region_dme_early_mode}
                                              if region_dme_early_mode != "hang" else {}),
                                           **({"cell_paths": True} if cell_paths else {}),
                                           **({"region_dme_early_merge_only": region_dme_early_merge_only}
                                              if region_dme_early_merge_only else {}))
    (out / "clock" / "make_tracks.tcl").write_text(gen_phys.make_tracks_tcl(P))
    meta["clock_tree"] = cm
    reserve = reserve_rects(segs, leaf_legs, P)
    # grt
    rv, nft = route_netlist(P, type_bits, landing_infra=landing_infra)
    if landing_infra:
        meta['landing_infra'] = dict(edges=landing['edges'], wires=len(landing['wires']),
            provisional_start_inputs=len(landing['boundary_inputs']),
            provisional_start_outputs=len(landing['boundary_outputs']),
            qualification='actual START provider and physical infra import required')
        (out/'grt'/'landing_provisional_nets.txt').write_text(''.join(name+'\n' for name in landing['provisional']))
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
    meta["grt"]["ft_layer_f1"] = ft_layer_audit(P)
    bl, br = band_region_adjust(P, dict(adjust).get("M4", 0.75))
    meta["grt"]["die_ft_bands"] = dict(layers=bl, band_rects=len(ft_band_rects(P)), share_strips=len(br),
                                       share_obstructions=len(band_share_obs(P, br)),
                                       transition_layers=list(TRANSITION_LAYERS), transition_keep=TRANSITION_KEEP)
    # INFRA-FIRST-QC-R21 (NUMBER-CHECK-QC-R20 kit bug): a port crossing a planned die channel is NOT abutted; it is a
    # die-top net in grt/route.v (route_netlist).  abutted_seam_bits now counts only the truly abutted ports.
    seam_bits = chan_bits = 0
    chan = 0
    for pid, pr in P.ports.items():
        if S.DIE_PART in (pr["src"]["part"], pr["dst"]["part"]):
            continue
        if P.channel_of(pid):
            chan += 1
            chan_bits += S.port_pins_count(pr)
        else:
            seam_bits += S.port_pins_count(pr)
    meta["grt"]["abutted_seam_bits"] = seam_bits
    meta["grt"]["channel_ports"] = chan
    meta["grt"]["channel_seam_bits"] = chan_bits
    meta["grt"]["channel_nets"] = dict(route_netlist.channel)
    meta["grt"]["abutted_pin_check"] = abutted_pin_check(P)
    if meta["grt"]["channel_nets"]["bits"] != chan_bits:
        raise SystemExit(f"die_trial kit: route.v channel nets {meta['grt']['channel_nets']} != {chan_bits} channel bits")
    grt = logged_stages([("/usr/bin/time -v openroad -no_init -threads 16 -exit /work/grt/grt.tcl",
                          "/work/grt/grt.log")])
    (out / "run_grt.sh").write_text(run_sh("grt", 256, 16, grt))
    # Run both sign-off corners even if one fails, preserving the first failure.
    ck = logged_stages([(f"CORNER={c} LIBDIR={PLAT}/lib/NLDM /usr/bin/time -v openroad -no_init -exit /work/clock/ctree.tcl",
                         f"/work/clock/ctree_{c}.log") for c in ("TT", "FF")])
    (out / "run_clock.sh").write_text(run_sh("clock", 32, 4, ck).replace("-v $D:/work", "-v $D:/work"))
    # psm
    power = part_power(P, plan_dir, density)
    pv = [f"module {sv(P.name)}_psm ();"] + [f"  {smod[p['type']]} {sv(n)} ();" for n, p in sorted(P.parts.items())] + ["endmodule"]
    (out / "psm" / "psm.v").write_text("\n".join(pv) + "\n")
    (out / "psm" / "pdn.tcl").write_text(psm_pdn_tcl(P))
    bumps = bump_grid(P, io, pads=bool(bump_contract(P).get("fields")))
    (out / "psm" / "bumps.tcl").write_text(bumps_tcl(P, bumps))
    (out / "psm" / "power.tcl").write_text("\n".join(f"set_pdnsim_inst_power -inst {sv(n)} -power {w:.6f}"
                                                     for n, w in sorted(power.items())) + "\n")
    (out / "psm" / "psm.tcl").write_text(psm_tcl(P, lefs, power, bumps))
    (out / "psm" / "power.json").write_text(json.dumps(dict(density_w_mm2=density, total_w=round(sum(power.values()), 3),
                                                            parts=power), indent=0) + "\n")
    meta["psm"] = dict(density_w_mm2=density, total_w=round(sum(power.values()), 2), bumps=len(bumps),
                       bumps_vdd=sum(1 for b in bumps if b[0] == "VDD"), bump_pitch_um=bump_contract(P)["pitch_um"],
                       **({"bump_contract": bump_contract(P)} if P.die.get("pg", {}).get("bumps") else {}),
                       io_windows=len(io), pg=P.die.get("pg", {}).get("grid"))
    (out / "run_psm.sh").write_text(run_sh("psm", 256, 16, "/usr/bin/time -v openroad -no_init -threads 16 -exit "
                                                         "/work/psm/psm.tcl > /work/psm/psm.log 2>&1"))
    # sta stand-ins
    nff = 0
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
    if gen_phys.io_hold_mode(P) != "legacy":
        meta["sta"]["io_hold"] = dict(mode=gen_phys.io_hold_mode(P), status="NEEDS_PARENT",
            basis="bare diagnostic input flops; real-view parent FF hold/CPPR required")
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
    plan_path = Path(kit["plan"] if Path(kit["plan"]).is_file() else a.plan)
    P = S.Plan(S.load(plan_path), plan_path)
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
    # Pin expansion is per type, not per instance or feedthrough slot.  QC
    # repeats a type's wide pin table many times; expanding it inside this
    # loop made the required visual review take minutes before its first PNG.
    ft_pins_by_type = {}
    for n, p in P.parts.items():
        tn = p["type"]
        if tn not in ft_pins_by_type:
            wanted = {s["name"] + suffix
                      for s in P.types[tn].get("ft_slots", []) or []
                      for suffix in ("_i", "_o")}
            by_name = collections.defaultdict(list)
            if wanted:
                for q in gen_phys.type_pins(P, tn):
                    if q[0] in wanted:
                        by_name[q[0]].append(q)
            ft_pins_by_type[tn] = by_name
        for s in P.types[p["type"]].get("ft_slots", []) or []:
            pins = (ft_pins_by_type[tn][s["name"] + "_i"]
                    + ft_pins_by_type[tn][s["name"] + "_o"])
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


def load_tap_pad(path):
    """Retain explicit sibling sites from the existing {pad: counts} CLI file."""
    raw = json.loads(Path(path).read_text())
    if "pad" in raw:
        return dict(raw["pad"], **({"sites": raw["sites"]} if "sites" in raw else {}))
    return raw


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
    k.add_argument("--feed", help="link_fishbone: region feed tree JSON (tools/die_plan/locality.py score()['feed'])")
    k.add_argument("--tree-form", choices=("htree", "spine_fishbone", "link_fishbone", "link_htree"), default="htree",
                   help="die clock topology: htree (default) or spine_fishbone (LAND-HEAD-3 opt-in: 1-D DME spine + per-row "
                        "fishbone ribs, low insertion so landed pairs split late); link_fishbone / link_htree (DIE-KV-2/3 opt-in: "
                        "region clocks fed along the locality feed tree --feed; fishbone or balanced H-tree (--leaf-um) inside "
                        "each --region-trees region)")
    k.add_argument("--tree-opt", action="append", default=[], metavar="K=V",
                   help="spine_fishbone options: matched=1 (phase-matched rib heads, station rows as 1-D DME; LAND-HEAD-3 model: worse), col_um, merge_um")
    k.add_argument("--region-trees", help="fallback regions.json (part_region): die reference tree to one root per "
                   "region + equal-depth local tree per region (FALLBACK-S81-2, opt-in)")
    k.add_argument("--slice-spine", action="store_true",
                   help="QC-SLICECLK-3 opt-in (needs --region-trees): one shared horizontal top spine + per-region "
                        "trees whose y levels sit on the region's full-height legal column, an equal leg per strip, "
                        "local bisection; illegal nodes move to the legal site that changes root->kid lengths least "
                        "(never a blind slide along a split axis)")
    k.add_argument("--spine-top-leaf-um", type=float, default=50.0,
                   help="top-spine 1-D bisection leaf (um): nominal top imbalance <= half of it")
    k.add_argument("--slice-rows", help="with --slice-spine: qc_slice_clock_rows/1 reservation (INFRA-FIRST-QC-R35): "
                   "column x and top spine row come from the plan reservation")
    k.add_argument("--rep-actual-max", type=float, default=None, metavar="UM",
                   help="opt-in: reject actual cell-to-cell and final-tap Manhattan hops over UM after legal snapping; "
                        "write actual_reach.json, default off; re-run clock_reach.py after any later clock overlay")
    k.add_argument("--clock-rc", default="ndr", choices=["ndr", "1x"],
                   help="die clock model wire RC: ndr = 2W2S assumption (R/2, Cx1.1; legacy default); 1x = ASAP7 M8/M9 "
                        "setRC as the die clock is routed (no NDR) (DIE-QC-3 opt-in)")
    k.add_argument("--slice-balance", action="store_true",
                   help="DIE-QC-3 opt-in (with --slice-spine): after the site pass, re-place the region-tree nodes as "
                        "zero-skew (Manhattan) merge points on legal sites (balance_legalize), column nodes along their column")
    k.add_argument("--region-dme", nargs="?", const=True, default=False, choices=[True, "priced", "delay"],
                   type=lambda v: v if v in ("priced", "delay") else v,
                   help="DIE-QC-3 opt-in (with --slice-spine): each region tree is a legal-site DME tree (per partition: "
                        "binary cuts of its taps; above: cuts of the partition roots), fed from the region's spine "
                        "entry; every merge point is chosen legal and zero-skew, so the site pass moves nothing; '--region-dme "
                        "priced' also prices the netlist's legal detours of legs over cores (merge_point_routed); '--region-dme delay' balances "
                        "stage-priced leg delay (leg_ps: a short leg still costs a stage) instead of length")
    k.add_argument("--region-dme-only", help="DIE-QC-4 opt-in (with --tree-form link_htree --tree-site-slide --region-dme): "
                   "comma list of regions that get the legal-site DME tree; every other region keeps the balanced "
                   "link_htree (balance_legalize).  Per-region fallback: DME only where the H-tree is worse")
    k.add_argument("--region-dme-early", type=float, default=None, metavar="RATIO",
                   help="DIE-QC-8 opt-in (with --region-dme delay; 12.3 v5.0 macro insertion-delay balancing): every early "
                        "core tap (clk_c<k>, early = core insertion - common latency, TT) in a DME region hangs from the "
                        "upper DME node whose subtree delay matches early/RATIO + its leg (RATIO = measured/model ps of "
                        "the routed clock, e.g. 1.548 from QC trial4), so it arrives early by construction; no pads. "
                        "Default: core taps are ordinary DME sinks")
    k.add_argument("--region-dme-early-ff", type=float, default=None, metavar="RATIO_FF",
                   help="DIE-QC-9 opt-in (with --region-dme-early): corner-averaged early hang target = mean of "
                        "early_TT/RATIO and early_FF/RATIO_FF (model ps), e.g. 1.293 from QC trial6 FF")
    k.add_argument("--cell-paths", action="store_true",
                   help="DIE-S81-15 opt-in: tree.json taps carry physical cell paths (driver/path/stages, as with "
                        "--tap-pad) so trial_tap_arrivals exports every leg repeater as a tree-path node; the start "
                        "tree (count_align_plan --start-retime-up) can then retime at the existing repeaters. "
                        "Netlist, placement and timing unchanged; default off = byte-identical tree.json")
    k.add_argument("--region-dme-early-mode", choices=("hang", "merge"), default="hang",
                   help="DIE-S81-14 opt-in (with --region-dme-early): 'merge' = the declared early (model ps) is a DME "
                        "sink delay, so bottom-up zero-skew merges deliver the core tap early (binary, no upper-node hang "
                        "legs / star nodes); default 'hang' = DIE-QC-8 hang from an upper node")
    k.add_argument("--region-dme-stage-cal", default=None, metavar="FILE",
                   help="DIE-QC-21 opt-in (with --region-dme delay): JSON {leg: [d0, k1, k2, kf], tap: [k1, k2]} stage model "
                        "fitted on routed legs of the clock cell (TT ps); replaces the BUFx24 1x-ladder STAGE_1X_TT in the "
                        "DME delay model and adds kf at every binary merge node (two-leg load). --region-dme-early RATIOs "
                        "are then measured/calibrated-model (about 1.0 TT). Default: uncalibrated model")
    k.add_argument("--region-dme-workers", type=int, default=1, metavar="N",
                   help="DIE-QC-20 opt-in: compute the region DME trees in N fork workers (same trees, attached in the "
                        "same order; default 1 = serial)")
    k.add_argument("--region-dme-early-merge-only", default=None, metavar="REGIONS",
                   help="DIE-QC-19 opt-in (with --region-dme-early): comma list of regions that use early mode 'merge' "
                        "(core sink delay = declared early, so the region tree is rooted at the core entry and the glue "
                        "joins there); other regions keep --region-dme-early-mode. Default: none")
    k.add_argument("--region-dme-snake", default=None, metavar="REGIONS",
                   help="DIE-QC-9 opt-in (with --region-dme delay, link_htree; COORD 10-28: standard zero-skew DME wire "
                        "elongation, plan-computed, part of the tree, not a residual ECO): comma list of DME regions "
                        "(or 'all') where a merge with no zero-skew legal point elongates the fast kid's leg as a "
                        "hairpin of legal buffer sites, and an over-early hung core tap gets its hang leg elongated. "
                        "Default: no elongation")
    k.add_argument("--region-dme-snake-cap", type=float, default=None, metavar="UM",
                   help="DIE-QC-23 opt-in (with --region-dme-snake and early mode 'merge'; COORD 10-28 structural long-snake "
                        "fix): per partition the glue taps are built into one DME tree first and each early core sink is "
                        "joined at its root (the merge point moves up, so one elongation on the shared glue root leg "
                        "replaces a snake on every low glue subtree); stats report snake legs longer than UM. "
                        "Default: off (byte-identical trees)")
    k.add_argument("--rep-on-leg", action="store_true",
                   help="DIE-QC-24 opt-in (COORD 10-28 21:00): a leg repeater whose evenly spaced point on a routed/detour "
                        "leg is not a legal site slides ALONG that leg to the nearest legal point (no sideways spur; trial15 "
                        "slid 28 repeaters 146.8 um off-leg to a core edge). Default off: site.nearest (byte-identical)")
    k.add_argument("--rep-off-leg-max", type=float, default=None, metavar="UM",
                   help="DIE-QC-24 opt-in guard (COORD 10-28 21:00): the kit FAILS if any leg repeater is placed more than "
                        "UM off its planned leg (e.g. 50). Default: no check")
    k.add_argument("--clock-cell", choices=("buf", "inv", "inv2"), default="buf",
                   help="DIE-QC-11 opt-in: 'inv' builds the die clock tree from CKINVDCx16 (BUFx24 footprint) so rise/fall "
                        "asymmetry cancels stage by stage (duty), with one parity inverter at odd-parity taps; 'inv2' = even inverter "
                        "stages per leg (priced in the DME delay model) + 2-stage root: true polarity everywhere by "
                        "construction, no tap parity inverters. Default buf")
    k.add_argument("--coarse-um", type=float, default=0.72)
    k.add_argument("--density", type=float, default=0.15, help="die power density W/mm2 for PDNSim")
    k.add_argument("--island-sites", nargs="+", help="CLOCK-128-R7 opt-in: die_tree_plan.json / ot_clock_sites/1 / "
                   "mesh.json (derived trunk sites): open plan-computed island windows (no M1-M3 OBS, M7 PG cut) in "
                   "every partition abstract, identical per type; island_windows.json lists them")
    k.add_argument("--island-margin-um", type=float, default=ISLAND_MARGIN_UM)
    k.add_argument("--landing-infra", action="store_true",
                   help="Opt-in scalar landing clock/control pins and real edge connectivity in the route target. "
                        "START boundary inputs remain explicitly provisional until actual infrastructure import.")
    k.add_argument("--tap-pad", help="DIE-KV-5 opt-in (12.8 plan-computed per-tap sizing): JSON {\"pad\": {tap port: n}} -> n "
                   "BUF cells in series on that tap's last leg (insertion-delay balancing of a light pruned branch)")
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
    e = sub.add_parser("readout", help="FLOW-ONEMODEL-2: print the both-edge clock arrival readout Tcl (T/F per tap, "
                                         "N/M per clock cell, polarity-resolved) for a ctree.v, to source in any clock-only "
                                         "or combo GRT script (writes the shared arr_<C>.txt format)")
    e.add_argument("ctree_v")
    e.add_argument("--path", default="/out/arr_$::env(CORNER).txt")
    e.add_argument("--period", default="833.333")
    e.add_argument("--cells", default="b*", help="get_cells glob, e.g. 'ck_*' or '{b* r* p*}'")
    e.add_argument("--prefix", default="", help="instance prefix in the routed design (e.g. ck_)")
    e.add_argument("--tap-slew", action="store_true")
    a = ap.parse_args(argv)
    global DME_WORKERS
    DME_WORKERS = max(1, int(getattr(a, "region_dme_workers", 1) or 1))
    if getattr(a, "region_dme_stage_cal", None):
        load_stage_cal(a.region_dme_stage_cal)
    global DME_SNAKE_CAP_UM
    if getattr(a, "region_dme_snake_cap", None) is not None:
        if not getattr(a, "region_dme_snake", None):
            raise SystemExit("--region-dme-snake-cap needs --region-dme-snake")
        DME_SNAKE_CAP_UM = float(a.region_dme_snake_cap)
    global REP_ON_LEG, REP_OFF_LEG_MAX_UM
    REP_ON_LEG = bool(getattr(a, "rep_on_leg", False))
    REP_OFF_LEG_MAX_UM = getattr(a, "rep_off_leg_max", None)
    if a.cmd == "readout":
        print("\n".join(clock_edge_readout(Path(a.ctree_v).read_text(), a.path, a.period, a.cells, a.tap_slew,
                                           a.prefix)))
        return 0
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
        summary = dict(types=len(tot), face_flops=sum(tot.values()), per_type_modules=shared,
                       clock_contract=not a.no_clock_contract)
        if gen_phys.io_hold_mode(P) != "legacy":
            summary["io_hold"] = dict(mode=gen_phys.io_hold_mode(P), status="NEEDS_PARENT",
                basis="bare diagnostic input flops; real-view parent FF hold/CPPR required")
            (Path(a.out) / "io_hold_standin.json").write_text(json.dumps(summary["io_hold"], indent=1) + "\n")
        print(json.dumps(summary, indent=1))
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
                      site_slide=a.tree_site_slide, regions=a.region_trees, landing_infra=a.landing_infra,
                      tree_form=a.tree_form,
                      tree_opts={**{k: float(v) for k, v in (o.split("=") for o in a.tree_opt)},
                                 **({"feed": a.feed} if a.tree_form in ("link_fishbone", "link_htree") else {})},
                      slice_spine=a.slice_spine, spine_top_leaf_um=a.spine_top_leaf_um, slice_rows=a.slice_rows,
                      tap_pad=load_tap_pad(a.tap_pad) if a.tap_pad else None,
                      clock_rc=a.clock_rc, slice_balance=a.slice_balance, region_dme=a.region_dme,
                      region_dme_only=[r for r in a.region_dme_only.split(",") if r] if a.region_dme_only else None,
                      region_dme_early=a.region_dme_early, region_dme_early_ff=a.region_dme_early_ff,
                      **({"rep_actual_max": a.rep_actual_max} if a.rep_actual_max is not None else {}),
                      **({"clock_cell": a.clock_cell} if a.clock_cell != "buf" else {}),
                      **({"region_dme_early_mode": a.region_dme_early_mode} if a.region_dme_early_mode != "hang" else {}),
                      **({"cell_paths": True} if a.cell_paths else {}),
                      **({"region_dme_early_merge_only": [r for r in a.region_dme_early_merge_only.split(",") if r]}
                         if a.region_dme_early_merge_only else {}),
                      region_dme_snake=(a.region_dme_snake if a.region_dme_snake == "all" else
                                        set(r for r in a.region_dme_snake.split(",") if r)) if a.region_dme_snake else None)
        print(json.dumps({k: m[k] for k in ("die", "parts", "types", "closed_views", "hard_cores", "clock_tree", "grt",
                                             "psm", "sta")}, indent=1))
    elif a.cmd == "report":
        res = cmd_report(a)
        print(json.dumps({k: v for k, v in res.items() if k != "kit"}, indent=1)[:6000])
    elif a.cmd == "render":
        d = Path(a.dir)
        kit = json.loads((d / "kit.json").read_text())
        plan_path = Path(a.plan or kit["plan"])
        P = S.Plan(S.load(plan_path), plan_path)
        print(json.dumps(render_all(d, P, a.plan or kit["plan"]), indent=1))
    elif a.cmd == "clock":
        d = Path(a.dir)
        kit = json.loads((d / "kit.json").read_text())
        plan_path = Path(a.plan or kit["plan"])
        P = S.Plan(S.load(plan_path), plan_path)
        print(json.dumps(clock_report(d, P), indent=1)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
