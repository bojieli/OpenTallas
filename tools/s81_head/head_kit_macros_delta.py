#!/usr/bin/env python3
"""DIE-HEAD-21 HK2 (COORD ruling 2026-10-28): HEAD kit plan plan_hk1 -> plan_hk2 with real SRAM macros.

    python3 tools/s81_head/head_kit_macros_delta.py PLAN_HK1.json CENSUS.json --main-plan MAIN_DIE_PLAN.json \
        --out PLAN_HK2.json [--report REPORT.json]
    python3 tools/s81_head/head_kit_macros_delta.py --census-from ENUM_DIR --census-out CENSUS.json

plan_hk1 (HEAD-KITS-1) lists the behavioural SRAM models (<m>.v) as sources of hd_serdes / hd_mesh / hd_ctl / hd_host,
so Yosys flattens the arrays (out of memory), and its hd_lep0N lacks the DIE-HEAD-10 LEP-C0 split.  This delta:
  (1) hd_lep0N <- main die_plan.json LEP-C0 form: u_core PAIR=1, the 45 parent SRAM contents, the 4 ot_s81hd_lep_pair
      hard_cores (pins_file re-pointed relative to the output plan), core_pg_connect, the moved reset.local_taps_um.
      Outline / module / sources must equal main's (else exit).
  (2) hd_serdes / hd_mesh / hd_ctl / hd_host: every behavioural SRAM source -> its <m>_bb.v blackbox; contents[] += one
      entry per SRAM instance of the census (Yosys hierarchy with the macros as blackboxes, flattened inst paths) with
      lef / lib / origin_um / outline_um / orient R0.  Placement is deterministic:
        * coll-lane SRAM sets (ot_s81hd_mesh_lane: 36 x 256x64 + 19 x 32x64, the same set as the LEP pair child) use
          the DIE-HEAD-9 child column block (6 columns, pitch 49.68; 8 big per column at 47.52, 32x64 at 21.6) next to
          the lane's coll face window (locality: the lane FIFO / replay buffer sit at their landing);
        * other SRAM (ctl x-store, serdes KP4 decoder) greedily nearest a per-type anchor (the consumer face).
      Every macro (grown by its keepout halo) stays off the landing bands, reserved clock sites, clock islands /
      tap, count-strap sites, landing pins, the type edge band, a PHY PG domain and the other macros
      (x channel 15.0 um at the M4 pin edges, y gap 4.0 um, lep child rule).  Reset local taps a macro blocks move to the
      nearest free 4.32-um site (LEP-C0 precedent).  A type whose SRAM cannot be placed is reported and left unchanged.
Outlines are never grown.  Grid: origins on 1.08 um (lep pack grid).
"""
import argparse
import copy
import json
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
G = 8.64                 # G0C hard-core origin lattice (die grid_um); sub-lattice shift = TRACK_OFF
TRACK_OFF = [0.108, 0.012]   # S81 SRAM hard-core track offset (M4 pins on the plan tracks)
TAP_GRID = 4.32
EDGE_UM = 17.28          # std-cell boundary band kept free of macros at every type edge
XGAP, YGAP = 15.0, 4.0   # macro-to-macro (lep child pack rule)
HALO = 8.64              # macro keepout around bands / reserved clock sites / islands
PT_HALO = 4.32           # around point sites (strap sites, landing pins, clock tap)
RESET_CLEAR = 4.32       # reset_tree.CLEAR_UM
FACE_BAND = 34.56        # boundary-flop strip in front of a bus window (lep child CH_COL_X0)
TAG = "DIE-HEAD-21 HK2"
LEP_TAG = "DIE-HEAD-10 LEP-C0"
SRAM_TYPES = ("hd_serdes", "hd_mesh", "hd_ctl", "hd_host")
BIG, SMALL = "ot_sram_1r1w2c_256x64_m1", "ot_sram_1r1w2c_32x64_m1"
COL_PITCH, BIG_PITCH, SMALL_PITCH = 51.84, 51.84, 25.92   # lep child pattern on the 8.64 lattice
BEHAV = re.compile(r"asap7_memory_macros[^/]*/([^/]+)/\1\.v$")
LANE_COLS = [("b", 8), ("b", 8), ("b", 8), ("b", 8), ("b", 4, "s", 9), ("s", 10)]

# per type: lane prefix -> (face window anchor, block placement); others -> anchor for the greedy fill.
#   lane block: ("W", y_lo, y_hi) block west edge at EDGE_UM+band, centred on the window span;
#               ("N"/"S", x_lo, x_hi) block centred on the window span, next to that face.
LANES = {
    "hd_mesh": {"u_core.u_la.": ("N", 160.0, 587.2), "u_core.u_lb.": ("W", 120.0, 547.2)},
    "hd_host": {"u_core.u_lane0.": ("W", 120.0, 547.2), "u_core.u_lane1.": ("S", 855.68, 1282.88)},
}
ANCHOR = {
    # x-store written from the W lepk_i0 window (y10-256), read to the S x_o window (x24-166): SW quadrant
    "hd_ctl": (180.0, 180.0),
    # KP4 decoder delay / output memories feed the S coll_o0 window (x1603-1809); logic strip below the PHY domain
    "hd_serdes": (1705.0, 60.0),
}


def snap(v, g=G):
    return round(round(v / g) * g, 3)


def lef_size(lef):
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", (ROOT / lef).read_text())
    return float(m.group(1)), float(m.group(2))


def macro_paths(mod, sources=()):
    """views of a macro; the directory the type's own behavioural source names wins (v1 and v2 both hold some)."""
    dirs = [s.rsplit("/", 2)[0] for s in sources if s.endswith(f"/{mod}/{mod}.v")]
    for d in dirs + ["physical/asap7_memory_macros_v2", "physical/asap7_memory_macros"]:
        p = ROOT / d / mod
        if (p / f"{mod}.lef").exists():
            return {"lef": f"{d}/{mod}/{mod}.lef", "lib": f"{d}/{mod}/{mod}_tt.lib", "bb": f"{d}/{mod}/{mod}_bb.v",
                    "v": f"{d}/{mod}/{mod}.v"}
    raise SystemExit(f"no macro view for {mod}")


# ------------------------------------------------------------------------------------------------ census (Yosys lists)
def census_from(enum_dir):
    """{type: [[inst, module], ...]} from ENUM/<type>.cells.<module>.txt (yosys `select -list t:<module>` after
    hierarchy + proc + flatten, sources with the <m>_bb.v blackboxes)."""
    out = {}
    for f in sorted(Path(enum_dir).glob("*.cells.*.txt")):
        tn, _, mod = f.name[:-4].split(".", 2)
        for ln in f.read_text().split():
            inst = ln.split("/", 1)[1]
            out.setdefault(tn, []).append([inst, mod])
    for tn in out:
        out[tn].sort()
    return out


# ------------------------------------------------------------------------------------------------ geometry helpers
def ov(a, b, gx=0.0, gy=None):
    gy = gx if gy is None else gy
    return not (a[2] + gx <= b[0] or b[2] + gx <= a[0] or a[3] + gy <= b[1] or b[3] + gy <= a[1])


def keepouts(plan, tn):
    """[(rect, label)] in the type frame a macro must not touch (rects already grown by their halo)."""
    t = plan["partition_types"][tn]
    ck = t.get("clock", {}) or {}
    ko = []

    def grow(r, h):
        return (r[0] - h, r[1] - h, r[2] + h, r[3] + h)
    for r in ck.get("reserved_sites_um", []) or []:
        ko.append((grow(r["rect_um"], HALO), f"reserved:{r.get('kind')}"))
    for r in ck.get("die_islands_um", []) or []:
        ko.append((grow(r, HALO), "clock_island"))
    lc = ck.get("landing_contract", {}) or {}
    for n, b in (lc.get("bands", {}) or {}).items():
        ko.append((grow(b["rect_um"], HALO), f"band:{n}"))
    pts = [("clock_tap", ck.get("tap_um"))] + [(f"edge_clock:{e['port']}", e["tap_um"]) for e in ck.get("edge_clocks", []) or []]
    pts += [(f"landing_pin:{p['name']}", p["xy_um"]) for p in lc.get("pins", []) or []]
    for s in t.get("count_straps", []) or []:
        pts += [(f"strap:{s['name']}", xy) for xy in s.get("sites_um", [])]
    for n, xy in pts:
        if xy:
            ko.append(((xy[0] - PT_HALO, xy[1] - PT_HALO, xy[0] + PT_HALO, xy[1] + PT_HALO), n))
    W, H = t["outline_um"]
    for b in t.get("buses", []) or []:          # boundary-flop strip in front of every bus window (lep child band)
        lo, hi = b["window_um"]
        r = {"S": (lo, 0, hi, FACE_BAND), "N": (lo, H - FACE_BAND, hi, H), "W": (0, lo, FACE_BAND, hi),
             "E": (W - FACE_BAND, lo, W, hi)}[b["face"]]
        ko.append((r, f"bus_face:{b['name']}"))
    for x0, y0, x1, y1 in ck.get("keepouts_um", []) or []:
        ko.append(((x0 - HALO, y0 - HALO, x1 + HALO, y1 + HALO), "clock_keepout"))
    # PHY PG domains (die.pg.domains) inside this type: a core-domain macro may not touch them
    W, H = t["outline_um"]
    for p in plan["partitions"]:
        if p["type"] != tn:
            continue
        ox, oy = p["origin_um"]
        for d in plan["die"].get("pg", {}).get("domains", []) or []:
            b = d["rect_um"]
            r = (max(ox, b[0]), max(oy, b[1]), min(ox + W, b[2]), min(oy + H, b[3]))
            if r[0] < r[2] - 1e-6 and r[1] < r[3] - 1e-6:
                rr = (r[0] - ox, r[1] - oy, r[2] - ox, r[3] - oy)
                if p.get("orient", "R0") == "MY":
                    rr = (W - rr[2], rr[1], W - rr[0], rr[3])
                ko.append((grow(rr, HALO), f"pg_domain:{d['name']}"))
        break                       # identical per instance (gen_phys.phy_pg_domains enforces it)
    return ko


def legal(rect, W, H, ko, placed):
    if rect[0] < EDGE_UM - 1e-6 or rect[1] < EDGE_UM - 1e-6 or rect[2] > W - EDGE_UM + 1e-6 or rect[3] > H - EDGE_UM + 1e-6:
        return "edge"
    for r, n in ko:
        if ov(rect, r):
            return n
    for r, n in placed:
        if ov(rect, r, XGAP, YGAP):
            return n
    return None


# ------------------------------------------------------------------------------------------------ placers
def lane_block(insts):
    """relative (inst, mod, dx, dy) of one mesh-lane SRAM set (DIE-HEAD-9 LEP pair child column pattern)."""
    big = sorted([i for i in insts if i[1] == BIG])
    small = sorted([i for i in insts if i[1] == SMALL])
    if (len(big), len(small)) != (36, 19) or len(insts) != 55:
        raise ValueError(f"lane SRAM set is {len(big)} big + {len(small)} small (+{len(insts) - len(big) - len(small)} other), "
                         "expected the 36 + 19 mesh-lane set")
    out, bi, si = [], 0, 0
    for c, spec in enumerate(LANE_COLS):
        y = 0.0
        for k in range(0, len(spec), 2):
            kind, n = spec[k], spec[k + 1]
            for _ in range(n):
                if kind == "b":
                    (inst, mod), bi, p = big[bi], bi + 1, BIG_PITCH
                else:
                    (inst, mod), si, p = small[si], si + 1, SMALL_PITCH
                out.append((inst, mod, snap(c * COL_PITCH), snap(y)))
                y += p
    return out


def block_bbox(rel, size):
    return (0.0, 0.0, max(dx + size[m][0] for _, m, dx, _ in rel), max(dy + size[m][1] for _, m, _, dy in rel))


def place_lane(rel, size, face, lo, hi, W, H, ko, placed):
    """slide the block along the face (start centred on the window span), first legal origin wins."""
    bw, bh = block_bbox(rel, size)[2:]
    cen = (lo + hi) / 2
    band_d = FACE_BAND                   # face-side clearance: boundary flops + landing band
    # candidates (slide along the face from the window centre, step away from the face) by cost |slide| + depth:
    # the block stays as close to its window as the keepouts allow
    cands = []
    for k in range(-150, 151):
        for depth in range(0, 20):
            off, d = k * G, depth * G
            if face == "W":
                x0, y0 = band_d + d, cen - bh / 2 + off
            elif face == "E":
                x0, y0 = W - band_d - bw - d, cen - bh / 2 + off
            elif face == "S":
                x0, y0 = cen - bw / 2 + off, band_d + d
            else:
                x0, y0 = cen - bw / 2 + off, H - band_d - bh - d
            cands.append((abs(off) + d, depth, k, snap(x0), snap(y0)))
    cands.sort()
    for _, _, _, x0, y0 in cands:
        if True:
            rects = [(inst, mod, snap(x0 + dx), snap(y0 + dy)) for inst, mod, dx, dy in rel]
            bad = None
            tmp = list(placed)
            for inst, mod, x, y in rects:
                r = (x, y, x + size[mod][0], y + size[mod][1])
                bad = legal(r, W, H, ko, tmp)
                if bad:
                    break
                tmp.append((r, inst))
            if not bad:
                return rects
    return None


def place_greedy(items, size, anchor, W, H, ko, placed, step=G):
    out = []
    nx, ny = int(W / step), int(H / step)
    for inst, mod in items:
        w, h = size[mod]
        best = None
        for i in range(nx):
            for j in range(ny):
                x, y = snap(i * step), snap(j * step)
                d = abs(x + w / 2 - anchor[0]) + abs(y + h / 2 - anchor[1])
                if best and d >= best[0]:
                    continue
                r = (x, y, x + w, y + h)
                if legal(r, W, H, ko, placed) is None:
                    best = (d, x, y)
        if not best:
            return None
        _, x, y = best
        placed.append(((x, y, x + w, y + h), inst))
        out.append((inst, mod, x, y))
    return out


def move_reset_taps(t, macros):
    """reset.local_taps_um a macro (grown by RESET_CLEAR) blocks -> nearest free 4.32 site; returns [(old, new)]."""
    taps = (t.get("reset", {}) or {}).get("local_taps_um")
    if not taps:
        return []
    W, H = t["outline_um"]
    boxes = [(r[0] - RESET_CLEAR, r[1] - RESET_CLEAR, r[2] + RESET_CLEAR, r[3] + RESET_CLEAR) for r in macros]

    def free(p):
        return all(not (b[0] < p[0] < b[2] and b[1] < p[1] < b[3]) for b in boxes) and \
            RESET_CLEAR <= p[0] <= W - RESET_CLEAR and RESET_CLEAR <= p[1] <= H - RESET_CLEAR
    moved, new = [], []
    for p in taps:
        if free(p):
            new.append(p)
            continue
        best = None
        for r in range(1, 200):
            for i in range(-r, r + 1):
                for j in (-r, r) if abs(i) != r else range(-r, r + 1):
                    q = [round(p[0] + i * TAP_GRID, 2), round(p[1] + j * TAP_GRID, 2)]
                    if free(q) and q not in new and q not in taps:
                        d = abs(i) + abs(j)
                        if best is None or d < best[0]:
                            best = (d, q)
            if best:
                break
        new.append(best[1])
        moved.append((p, best[1]))
    t["reset"]["local_taps_um"] = new
    return moved


def write_pins(mod, lef, out_dir):
    """<out_dir>/core_pins/<mod>.json (S81 SRAM pins_file form): largest non-M1 rect centre of every signal pin."""
    txt = (ROOT / lef).read_text()
    pins = []
    for name, body in re.findall(r"\n\s*PIN (\S+)(.*?)\n\s*END \1", txt, re.S):
        if re.search(r"USE\s+(POWER|GROUND)", body):
            continue
        best = None
        for L, x0, y0, x1, y1 in re.findall(r"LAYER (\S+) ;\s*RECT ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)", body):
            if L == "M1":
                continue
            a = (float(x1) - float(x0)) * (float(y1) - float(y0))
            if best is None or a > best[0]:
                best = (a, L, round((float(x0) + float(x1)) / 2, 4), round((float(y0) + float(y1)) / 2, 4))
        if best:
            pins.append({"name": name, "layer": best[1], "x": best[2], "y": best[3]})
    d = Path(out_dir) / "core_pins"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{mod}.json").write_text(json.dumps({"module": mod, "lef": lef, "source": f"{TAG}: LEF signal pins, largest "
                                               "non-M1 rect centres", "pins": pins}, indent=1) + "\n")
    return f"core_pins/{mod}.json", len(pins)


def hard_entry(inst, mod, lef, lib, x, y, size, out_dir, note):
    pf, _ = write_pins(mod, lef, out_dir)
    return {"inst": inst, "module": mod, "lef": lef, "lib": lib, "origin_um": [round(x, 2), round(y, 2)],
            "outline_um": list(size), "orient": "R0", "track_offset_um": list(TRACK_OFF), "pins_file": pf,
            "obs_max": "M4", "note": note}


# ------------------------------------------------------------------------------------------------ deltas
def lep_delta(plan, main, out_dir):
    t, m = plan["partition_types"]["hd_lep0N"], main["partition_types"]["hd_lep0N"]
    for k in ("outline_um", "module", "sources"):
        if t.get(k) != m.get(k):
            raise SystemExit(f"hd_lep0N {k} differs between plan_hk1 and main: reconcile first")
    core = next(c for c in t["contents"] if c["inst"] == "u_core")
    mcore = next(c for c in m["contents"] if c["inst"] == "u_core")
    if core["module"] != mcore["module"]:
        raise SystemExit("hd_lep0N u_core module differs from main")
    core.setdefault("params", {})["PAIR"] = mcore["params"]["PAIR"]
    t["contents"] = [c for c in t["contents"] if LEP_TAG not in c.get("note", "")] + \
        [copy.deepcopy(c) for c in m["contents"] if LEP_TAG in c.get("note", "")]
    t["hard_cores"] = copy.deepcopy(m["hard_cores"])
    main_dir = ROOT / "physical/die_plan/s81_head"
    for h in t["hard_cores"]:
        if h.get("pins_file"):
            h["pins_file"] = os.path.relpath(main_dir / h["pins_file"], out_dir)
    t["core_pg_connect"] = m.get("core_pg_connect", True)
    # main's LEP-C0 floorplan predates the one-entry clock (reserved die-clock sites / islands / landing bands of
    # plan_hk1): a copied SRAM that touches one moves to the nearest legal site; hard cores are only reported.
    W, H = t["outline_um"]
    ko = keepouts(plan, "hd_lep0N")
    hc = [((h["origin_um"][0] + h.get("track_offset_um", [0, 0])[0], h["origin_um"][1] + h.get("track_offset_um", [0, 0])[1],
            h["origin_um"][0] + h.get("track_offset_um", [0, 0])[0] + h["outline_um"][0],
            h["origin_um"][1] + h.get("track_offset_um", [0, 0])[1] + h["outline_um"][1]), h["inst"]) for h in t["hard_cores"]]
    sr = [c for c in t["contents"] if LEP_TAG in c.get("note", "")]
    rect = {c["inst"]: (c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
                        c["origin_um"][1] + c["outline_um"][1]) for c in sr}
    core_hits = [(n, k) for r, n in hc for k_r, k in ko if ov(r, k_r) and not k.startswith(("bus_face", "landing_pin",
                                                                                              "edge_clock"))]
    # hard cores (no view yet) that sit on a plan_hk1 landing band / reserved site: smallest shift on the G0C 8.64-um
    # hard-core lattice (x first: the one-entry landing bands sit between the coll face and the child's coll pins)
    core_moved = []
    soft = ("bus_face", "landing_pin", "edge_clock")
    for i, (r, n) in enumerate(hc):
        hits = [k for k_r, k in ko if ov(r, k_r) and not k.startswith(soft)]
        if not hits:
            continue
        h = next(x for x in t["hard_cores"] if x["inst"] == n)
        best = None
        for k in range(1, 40):
            for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
                q = (r[0] + dx * 8.64, r[1] + dy * 8.64, r[2] + dx * 8.64, r[3] + dy * 8.64)
                oth = [(o, m) for j, (o, m) in enumerate(hc) if j != i] + [(rect[c["inst"]], c["inst"]) for c in sr]
                if legal(q, W, H, [x for x in ko if not x[1].startswith(soft)], oth) is None:
                    best = (dx * 8.64, dy * 8.64)
                    break
            if best:
                break
        if not best:            # left where main has it; reported (the child has no view: kits do not place it)
            core_moved.append([n, sorted(set(hits)), list(h["origin_um"]), None])
            continue
        old_o = list(h["origin_um"])
        h["origin_um"] = [round(h["origin_um"][0] + best[0], 2), round(h["origin_um"][1] + best[1], 2)]
        h["note"] += f"; {TAG}: shifted {best} um off {sorted(set(hits))} (plan_hk1 one-entry landing/clock sites)"
        hc[i] = ((r[0] + best[0], r[1] + best[1], r[2] + best[0], r[3] + best[1]), n)
        core_moved.append([n, sorted(set(hits)), old_o, h["origin_um"]])
    moved = []
    for c in sr:
        others = [(rect[o["inst"]], o["inst"]) for o in sr if o is not c] + hc
        hit = next((k for k_r, k in ko if ov(rect[c["inst"]], k_r)), None)
        if not hit:
            continue
        w, h = c["outline_um"]
        got = place_greedy([(c["inst"], c["module"])], {c["module"]: (w, h)},
                           (c["origin_um"][0] + w / 2, c["origin_um"][1] + h / 2), W, H, ko, others, step=G)
        if not got:
            raise SystemExit(f"hd_lep0N {c['inst']} touches {hit} and has no legal site nearby")
        _, _, x, y = got[0]
        moved.append([c["inst"], hit, c["origin_um"], [x, y]])
        c["origin_um"] = [x, y]
        c["note"] += f"; {TAG}: moved off {hit}"
        rect[c["inst"]] = (x, y, x + w, y + h)
    # nested SRAM leaves are hard_cores (S81 form): gen_rtl instantiates every contents[] entry in the wrapper
    snapped = []
    t["contents"] = [c for c in t["contents"] if c not in sr]
    for c in sr:
        x, y = c["origin_um"]
        nx, ny = snap(x), snap(y)
        if (nx, ny) != (x, y):
            snapped.append([c["inst"], [x, y], [nx, ny]])
        t["hard_cores"].append(hard_entry(c["inst"], c["module"], c["lef"], c["lib"], nx, ny, c["outline_um"], out_dir,
                                          c["note"] + f"; {TAG}: nested SRAM as hard core on the 8.64 lattice"))
        rect[c["inst"]] = (nx, ny, nx + c["outline_um"][0], ny + c["outline_um"][1])
    rs = list(rect.items())
    clash = [(a, b) for i, (a, ra) in enumerate(rs) for b, rb in rs[i + 1:] if ov(ra, rb, 2.0)]
    clash += [(a, k) for a, ra in rs for k_r, k in ko if ov(ra, k_r)]
    t["reset"] = dict(t.get("reset", {}), local_taps_um=copy.deepcopy(m["reset"]["local_taps_um"]))
    taps_moved = move_reset_taps(t, [r for r, _ in hc] + list(rect.values()))
    return dict(pair=core["params"]["PAIR"], sram=len(sr), sram_moved=moved, core_keepout_hits=core_hits,
                cores_moved=core_moved, reset_taps_moved=taps_moved, sram_snapped=len(snapped),
                sram_snap_clashes=clash,
                hard_cores=len(t["hard_cores"]), core_pg_connect=t["core_pg_connect"],
                reset_taps_from_main=len(t["reset"]["local_taps_um"]))


def repoint_pins(plan, src_dir, out_dir):
    """hard-core pins_file that do not resolve from the source plan dir -> the repo copy (same basename) relative to
    out_dir.  Returns [(type, inst, old, new)]."""
    cores = ROOT / "physical/die_plan/s81_head/cores"
    ch = []
    for tn, t in plan["partition_types"].items():
        for h in t.get("hard_cores", []) or []:
            pf = h.get("pins_file")
            if not pf:
                continue
            if (Path(out_dir) / pf).exists():
                continue
            if (Path(src_dir) / pf).exists():
                new = os.path.relpath((Path(src_dir) / pf).resolve(), out_dir)
            elif (cores / Path(pf).name).exists():
                new = os.path.relpath(cores / Path(pf).name, out_dir)
            else:
                continue
            ch.append((tn, h["inst"], pf, new))
            h["pins_file"] = new
    return ch


def sram_delta(plan, tn, insts, out_dir):
    t = plan["partition_types"][tn]
    W, H = t["outline_um"]
    mods = sorted({m for _, m in insts})
    views = {m: macro_paths(m, t["sources"]) for m in mods}
    size = {m: lef_size(views[m]["lef"]) for m in mods}
    est = dict(n=len(insts), modules={m: sum(1 for _, x in insts if x == m) for m in mods},
               size_um={m: list(size[m]) for m in mods},
               macro_um2=round(sum(size[m][0] * size[m][1] for _, m in insts), 1),
               macro_with_channels_um2=round(sum((size[m][0] + XGAP) * (size[m][1] + YGAP) for _, m in insts), 1),
               outline_um2=round(W * H, 1))
    ko = keepouts(plan, tn)
    placed, res = [], []
    rest = list(insts)
    for pref, (face, lo, hi) in LANES.get(tn, {}).items():
        lane = [i for i in rest if i[0].startswith(pref)]
        rest = [i for i in rest if not i[0].startswith(pref)]
        got = place_lane(lane_block(lane), size, face, lo, hi, W, H, ko, placed)
        if not got:
            est.update(placed=False, why=f"lane {pref} block does not fit at face {face}")
            return est
        for inst, mod, x, y in got:
            placed.append(((x, y, x + size[mod][0], y + size[mod][1]), inst))
        res += got
    if rest:
        got = place_greedy(sorted(rest), size, ANCHOR[tn], W, H, ko, placed)
        if not got:
            est.update(placed=False, why="greedy fill found no legal site")
            return est
        res += got
    # sources: behavioural model -> blackbox
    # every listed behavioural model (also the ones the type lists but never instantiates) -> its blackbox
    vs = {s: s[:-2] + "_bb.v" for s in t["sources"] if BEHAV.search(s) and (ROOT / (s[:-2] + "_bb.v")).exists()}
    t["sources"] = [vs.get(s, s) for s in t["sources"]]
    left = [s for s in t["sources"] if BEHAV.search(s)]
    if left:
        raise SystemExit(f"type {tn}: behavioural SRAM source left: {left}")
    t["hard_cores"] = [h for h in t.get("hard_cores", []) or [] if TAG not in h.get("note", "")]
    for inst, mod, x, y in sorted(res):
        t["hard_cores"].append(hard_entry(inst, mod, views[mod]["lef"], views[mod]["lib"], x, y, size[mod], out_dir,
                                          f"{TAG}: SRAM macro (was a behavioural model)"))
    t["core_pg_connect"] = True     # PG-CORECONN-1: the kit PDN lands the macro PG pins (as hd_lep0N / hd_tile)
    moved = move_reset_taps(t, [r for r, _ in placed])
    bb = [min(r[0] for r, _ in placed), min(r[1] for r, _ in placed), max(r[2] for r, _ in placed),
          max(r[3] for r, _ in placed)]
    est.update(placed=True, bbox_um=[round(v, 3) for v in bb], reset_taps_moved=moved,
               sources_bb=sorted(vs.values()))
    return est


def render(plan, tn, rep, png):
    """type-frame view: outline, keepouts (bands / reserved clock sites / islands / PG domain / strap + pin points),
    bus windows on the faces, SRAM macros (HK2 new; LEP-C0 copied), lep_pair hard cores, reset taps (moved = red)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    t = plan["partition_types"][tn]
    W, H = t["outline_um"]
    fig, ax = plt.subplots(figsize=(14, 14 * H / W + 1.2) if W > H else (12, 12 * H / W))
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5, ec="k"))
    for r, n in keepouts(plan, tn):
        col = {"band": "#e8a33d", "reserved": "#7b3fbf", "clock_island": "#2a7de1", "pg_domain": "#bbbbbb"}.get(
            n.split(":")[0], "#d04040")
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=col, ec=col, alpha=0.35, lw=0.5))
    for b in t.get("buses", []):
        lo, hi = b["window_um"]
        f = b["face"]
        xy = {"N": ([lo, hi], [H, H]), "S": ([lo, hi], [0, 0]), "W": ([0, 0], [lo, hi]), "E": ([W, W], [lo, hi])}[f]
        ax.plot(*xy, lw=5, color="#1a9e5a", solid_capstyle="butt")
        ax.annotate(b["name"], (sum(xy[0]) / 2, sum(xy[1]) / 2), fontsize=7, color="#1a9e5a", ha="center")
    for c in t.get("contents", []):
        if "origin_um" not in c:
            continue
        new = TAG in c.get("note", "")
        x, y = c["origin_um"]
        w, h = c["outline_um"]
        ax.add_patch(Rectangle((x, y), w, h, fc="#4a90d9" if new else "#8fb8e8", ec="#123", lw=0.4))
    for h_ in t.get("hard_cores", []) or []:
        x, y = h_["origin_um"]
        dx, dy = h_.get("track_offset_um", [0, 0])
        w, h = h_["outline_um"]
        if h_.get("lef") and "sram" in h_["module"]:
            ax.add_patch(Rectangle((x + dx, y + dy), w, h, fc="#4a90d9" if "behavioural" in h_.get("note", "") else
                                   "#8fb8e8", ec="#123", lw=0.4))
            continue
        ax.add_patch(Rectangle((x + dx, y + dy), w, h, fill=False, ec="#c0392b", lw=1.2, ls="--"))
        ax.annotate(h_["inst"].split(".")[-2], (x + dx + w / 2, y + dy + h / 2), fontsize=8, ha="center")
    moved = {tuple(n) for _, n in (rep or {}).get("reset_taps_moved", [])}
    for p in (t.get("reset", {}) or {}).get("local_taps_um", []) or []:
        ax.plot(p[0], p[1], "x", color="red" if tuple(p) in moved else "#333", ms=6, mew=1.5)
    ck = t.get("clock", {})
    if ck.get("tap_um"):
        ax.plot(*ck["tap_um"], "*", color="#2a7de1", ms=12)
    n = sum(1 for c in t.get("hard_cores", []) or [] if "sram" in c["module"])
    ax.set_title(f"{tn} {W} x {H} um: {n} placed SRAM macros (dark = HK2 new, light = LEP-C0 copy), "
                 f"{len([c for c in t.get('hard_cores', []) or [] if 'sram' not in c['module']])} other hard cores (red dashed); orange bands, purple reserved clock, "
                 "blue islands/tap, grey PHY PG domain, x reset taps (red = moved), green bus windows", fontsize=8)
    ax.set_xlim(-20, W + 20)
    ax.set_ylim(-20, H + 20)
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(png, dpi=110)
    plt.close(fig)


def run(plan, census, main, out_dir, src_dir):
    rep = {"lep0N": lep_delta(plan, main, out_dir), "types": {}}
    for tn in SRAM_TYPES:
        rep["types"][tn] = sram_delta(plan, tn, [tuple(x) for x in census[tn]], out_dir)
    rep["pins_file_repointed"] = repoint_pins(plan, src_dir, out_dir)
    plan["note"] = (plan.get("note", "") + " | plan_hk2 (DIE-HEAD-21): SRAM macros in place of behavioural models "
                    "(serdes/mesh/ctl/host) + LEP-C0 lep_pair hard cores on hd_lep0N").strip(" |")
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan", nargs="?")
    ap.add_argument("census", nargs="?")
    ap.add_argument("--main-plan", default=str(ROOT / "physical/die_plan/s81_head/die_plan.json"))
    ap.add_argument("--out")
    ap.add_argument("--report")
    ap.add_argument("--png-dir", help="render each changed type's macro placement to PNG_DIR/<type>.png")
    ap.add_argument("--census-from")
    ap.add_argument("--census-out")
    a = ap.parse_args()
    if a.census_from:
        Path(a.census_out).write_text(json.dumps(census_from(a.census_from), indent=1) + "\n")
        return 0
    plan = json.loads(Path(a.plan).read_text())
    census = json.loads(Path(a.census).read_text())
    main_plan = json.loads(Path(a.main_plan).read_text())
    out = Path(a.out)
    rep = run(plan, census, main_plan, out.parent.resolve(), Path(a.plan).parent.resolve())
    out.write_text(json.dumps(plan, indent=1) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    if a.png_dir:
        Path(a.png_dir).mkdir(parents=True, exist_ok=True)
        for tn in ("hd_lep0N",) + SRAM_TYPES:
            render(plan, tn, rep["types"].get(tn) or rep["lep0N"], Path(a.png_dir) / f"{tn}.png")
    for tn, r in rep["types"].items():
        print(f"{tn}: {r['n']} SRAM {r['modules']} macro {r['macro_um2']} um2 (+ch {r['macro_with_channels_um2']}) / "
              f"outline {r['outline_um2']} -> placed {r['placed']} {r.get('bbox_um', r.get('why'))} "
              f"reset taps moved {len(r.get('reset_taps_moved', []))}")
    print(f"hd_lep0N: {rep['lep0N']}")
    print(f"pins_file repointed: {len(rep['pins_file_repointed'])}")
    return 0 if all(r["placed"] for r in rep["types"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
