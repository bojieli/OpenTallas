#!/usr/bin/env python3
"""region_guide.py -- die-agnostic SOFT region guides for AUTO-GEOM class D (COORD 11-02 23:0x, GEOM-111 class D).

Class D = "datapath spread inside one cloud": the AUTO-GEOM r2r rule (geom_rules.r2r_metrics, reach <= 405 um) fails
because same-bit launch/capture registers of one bus land at opposite ends of one large logic cloud (HBM
hnx_fused_lane a7: u_fcore.u_core.rd_q[i] -> up_d[i], 589 um x433).  This tool reads the kit's LAST AUTO-GEOM result
(geom_check.sh OUTDIR: geom.tsv dump + auto_geom.json), takes every capture over the reach limit with its worst launch
(the exact r2r census), joins the endpoints into bit slices (union-find over the failing pairs: one slice = the
registers one failing path set ties together), anchors each slice at the Manhattan minimax centre of its members'
last positions and groups the slices by the tile of a grid over the core (tiles at most (limit - margin) / 2 on a
side) that holds the anchor.  One region per non-empty tile: a SMALL box (member area / 0.30, >= 8 um, inside the
tile, off hard macros) at the mean anchor -- this OpenROAD GPL removes region area from the top-level placeable area,
so a whole-tile cover is infeasible (GPL-0301 'Utilization 289 %' measured on hnx_fused_lane).  Boxes are disjoint by
construction.  Broadcast registers (one register in > 16 failing pairs: reset / enable fan-out) are no bit slice and
are left to their own class fix (replication / reset relays); `plan` reports them.  The planner re-runs the exact r2r
census on the predicted placement (guided registers clamped into their box) up to --rounds times and adds new
failing pairs to the slices.

The kit hook (region_guide.tcl, sourced at the END of the PRE_GLOBAL_PLACE hook face_flops.tcl) turns each tile into
an INCLUSIVE odb dbRegion + dbGroup with the guided registers (the macro_reg_guide.tcl / r2a_fences.tcl form);
region_guide_release.tcl (end of the PRE_DETAIL_PLACE hook face_flops_release.tcl) destroys them, so the guide acts
on global placement only: DPL, repair, CTS and route are free.  This is a soft guide, not a fence and not a gate.

Never guided: hard macros / non-std cells, cells FIRM/LOCKED in the dump, and pin (face / IO) registers -- a register
reached from or reaching a top pin through buffers/inverters only (geom_rules pin_reg traversal depth).  A slice that
contains such a fixed register is placed in the tile of its fixed registers (the movable ones go to them).  At hook
time the Tcl again skips FIRM/LOCKED instances (face_flops.tcl pins face registers FIRM before GPL), non-core masters
and instances already in a group (another guide owns them).

Default OFF everywhere: the generators install it only when given --region-guide (gen_core_kit_hbm.py) or
--region-guide TYPE=JSON (gen.py phys), and `plan` writes a spec only when the AUTO-GEOM r2r rule FAILED (class D),
so kit_wave can pass the previous attempt's geom dir on every relaunch: a kit whose r2r passed gets no file.

    region_guide.py plan --geom-dir OUTDIR --out SPEC.json [--limit 405] [--margin 45] [--tile-um T] [--rounds 3]
        exit 0; SPEC.json written only on class D (prints REGION_GUIDE ... lines); exit 2 on unreadable input
    region_guide.py measure --geom-dir OUTDIR --spec SPEC.json
        r2r of the spec's guided pairs on a (new) dump: before/after evidence
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "autopilot"))
import geom_rules as G  # noqa: E402

SCHEMA = "opentallas.region_guide.v1"
LIMIT = G.R2R_MAX
MARGIN = 45.0
PIN_DEPTH = G.PINREG_DEPTH
BCAST_MAX = 16          # one register in more failing pairs than this = a broadcast, not a bit slice
BOX_DENSITY = 0.30       # guided register area / box area
BOX_MIN_SIDE = 8.0
BOX_HALO = 2.0           # um kept from hard macros
PIN_FANOUT = 8          # a pin register path is a bus bit, not a broadcast (reset/enable) tree
FIXED = {"FIRM", "LOCKED", "COVER"}
TCL_HOOK = HERE / "region_guide.tcl"
TCL_RELEASE = HERE / "region_guide_release.tcl"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def class_d(auto_geom):
    """auto_geom.json dict -> True when the r2r rule (or its count) FAILED: AUTO-GEOM class D"""
    return any(r.get("rule") in ("r2r", "r2r_count") and r.get("status") == "FAIL" for r in auto_geom.get("rules") or [])


def pin_registers(D, depth=PIN_DEPTH, fanout=PIN_FANOUT):
    """seq cells reached from (input side) or reaching (output side) a top signal pin through buffers/inverters only.
    Clock pins and broadcast nets (> fanout sinks: reset / enable trees) are not pin-register paths."""
    out = set()
    for p in D.pins:
        if p.get("sig") == "CLOCK" or G.CLOCK_PIN_RE.search(p["name"]):
            continue
        n0 = D.pin_net.get(p["k"])
        if n0 is None or len(D.nets[n0][2]) > fanout:
            continue
        front, seen = [n0], {n0}
        for _ in range(depth + 1):
            nf = []
            for n in front:
                sig, drv, sinks = D.nets[n]
                for r in ([drv] if drv else []) + list(sinks):
                    if r[0] != "i" or r[2]:
                        continue
                    k = D.kind(r[1])
                    if k == "S":
                        out.add(r[1])
                    elif k == "B":
                        for m in D.drives.get(r[1], []) + [x for x, clk in D.cell_in.get(r[1], []) if not clk]:
                            if m not in seen and len(D.nets[m][2]) <= fanout:
                                seen.add(m)
                                nf.append(m)
            front = nf
    return out


class UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def grid(core, tile):
    x0, y0, x1, y1 = core
    nx, ny = max(1, math.ceil((x1 - x0) / tile - 1e-9)), max(1, math.ceil((y1 - y0) / tile - 1e-9))
    return nx, ny, (x1 - x0) / nx, (y1 - y0) / ny


def tile_of(core, g, x, y):
    nx, ny, tw, th = g
    ix = min(nx - 1, max(0, int((x - core[0]) // tw)))
    iy = min(ny - 1, max(0, int((y - core[1]) // th)))
    return ix, iy


def tile_box(core, g, ix, iy):
    nx, ny, tw, th = g
    return (core[0] + ix * tw, core[1] + iy * th, core[0] + (ix + 1) * tw, core[1] + (iy + 1) * th)


def guide_box(tile, anchor, area, macros, density=None, min_side=None):
    """small INCLUSIVE box for one tile's guided registers: side sqrt(area / density) (>= min_side, <= tile), centred
    at the slices' anchor, inside the tile (so boxes of different tiles are disjoint), moved to the nearest macro-free
    spot of the tile when the anchor sits on a macro.  The box must stay small: this OpenROAD GPL removes every region
    from the top-level placeable area (a full-tile region cover made GPL-0301 'Utilization 289 %' on hnx_fused_lane)."""
    density = BOX_DENSITY if density is None else density
    min_side = BOX_MIN_SIDE if min_side is None else min_side
    tw, th = tile[2] - tile[0], tile[3] - tile[1]
    side = max(min_side, math.sqrt(max(area, 0.0) / density))
    w, h = min(side, tw), min(side, th)

    def at(cx, cy):
        cx = min(max(cx, tile[0] + w / 2), tile[2] - w / 2)
        cy = min(max(cy, tile[1] + h / 2), tile[3] - h / 2)
        return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

    def free(b):
        return not any(b[0] < m[2] and m[0] < b[2] and b[1] < m[3] and m[1] < b[3] for m in macros)

    best = at(*anchor)
    if free(best):
        return best
    step = max(min(w, h) / 2, 1.0)
    cands = [at(tile[0] + w / 2 + i * step, tile[1] + h / 2 + j * step)
             for i in range(int((tw - w) / step) + 2) for j in range(int((th - h) / step) + 2)]
    cands = [b for b in cands if free(b)]
    if not cands:
        return best
    return min(cands, key=lambda b: abs((b[0] + b[2]) / 2 - anchor[0]) + abs((b[1] + b[3]) / 2 - anchor[1]))


def clamp_cell(c, box):
    """cell tuple moved (same size) so its centre is inside box: the GPL-with-guide prediction"""
    w, h = c[4] - c[2], c[5] - c[3]
    x, y = G.ctr(c)
    x = min(max(x, box[0] + w / 2), box[2] - w / 2)
    y = min(max(y, box[1] + h / 2), box[3] - h / 2)
    return (c[0], c[1], x - w / 2, y - h / 2, x + w / 2, y + h / 2, c[6])


def plan(D, limit=LIMIT, margin=MARGIN, tile_um=None, rounds=3, bcast_max=None):
    """D = geom_rules.Design -> spec dict (regions [] when r2r already passes)"""
    if not 0 <= margin < limit:
        raise ValueError("margin must be in [0, limit)")
    tile = float(tile_um) if tile_um else (limit - margin) / 2.0
    if not 0 < tile * 2 <= limit:
        raise ValueError(f"tile {tile} um: two tile sides must stay within the {limit} um reach")
    bcast_max = BCAST_MAX if bcast_max is None else int(bcast_max)
    core = tuple(D.extra.get("core") or D.die)
    g = grid(core, tile)
    status = D.extra.get("status") or {}
    pinned = pin_registers(D)
    fixed = {cid for cid, c in D.cells.items()
             if c[0] != "S" or status.get(cid) in FIXED or cid in pinned}
    byname = {c[6]: cid for cid, c in D.cells.items()}
    orig = dict(D.cells)
    macros = [(c[2] - BOX_HALO, c[3] - BOX_HALO, c[4] + BOX_HALO, c[5] + BOX_HALO) for c in D.cells.values() if c[0] == "M"]
    pairs0 = []
    m0 = G.r2r_metrics(D, capture_pairs=pairs0, collect_above=limit)
    pair_log, assign, logged, bcast, uf, boxes = [], {}, set(), set(), UF(), {}
    work = D
    for rnd in range(max(1, rounds)):
        pairs = pairs0 if rnd == 0 else []
        if rnd:
            G.r2r_metrics(work, capture_pairs=pairs, collect_above=limit)
        new = 0
        for p in pairs:
            a, b = byname.get(p["launch"]), byname.get(p["capture"])
            if a is None or b is None or (a in fixed and b in fixed) or (a, b) in logged:
                continue
            logged.add((a, b))
            new += 1
            pair_log.append(dict(launch=p["launch"], capture=p["capture"], distance_um=p["distance_um"], round=rnd,
                                 ids=(a, b)))
        if not new:
            break
        # broadcast endpoints (one register in > bcast_max failing pairs: reset / enable fan-out, class R) are not a
        # bit slice; their pairs are left to the class fix that owns them
        cnt = Counter(e for q in pair_log for e in q["ids"])
        bcast = {e for e, n in cnt.items() if n > bcast_max}
        uf = UF()
        for q in pair_log:
            a, b = q["ids"]
            if a not in bcast and b not in bcast:
                uf.union(a, b)
        # slices -> tiles from the ORIGINAL placement (minimax anchor; fixed members never move)
        slices = {}
        for cid in list(uf.p):
            slices.setdefault(uf.find(cid), []).append(cid)
        assign, t_anchor = {}, {}
        for root, mem in slices.items():
            # anchor = Manhattan minimax centre of every member's last position (fixed ones exact, movable ones as the
            # proxy of their other neighbours): the slice's registers there are at most half the slice span away
            u = [sum(G.ctr(orig[m])) for m in mem]
            v = [G.ctr(orig[m])[0] - G.ctr(orig[m])[1] for m in mem]
            uc, vc = (min(u) + max(u)) / 2, (min(v) + max(v)) / 2
            x, y = (uc + vc) / 2, (uc - vc) / 2
            t = tile_of(core, g, x, y)
            mov = [m for m in mem if m not in fixed]
            if mov:
                t_anchor.setdefault(t, []).append((x, y))
            for m in mov:
                assign[m] = t
        boxes = {}
        for t, pts in t_anchor.items():
            area = sum((orig[m][4] - orig[m][2]) * (orig[m][5] - orig[m][3]) for m, tt in assign.items() if tt == t)
            boxes[t] = guide_box(tile_box(core, g, *t), (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)),
                                 area, macros)
        # prediction: guided cells clamped into their box; everything else where the last placement put it
        cells = dict(orig)
        for m, t in assign.items():
            cells[m] = clamp_cell(orig[m], boxes[t])
        work = _with_cells(D, cells)
    # per-pair census on the prediction: guided (both movable or anchored), broadcast (left to its class fix), fixed
    pc = {"guided": [], "broadcast": []}
    for q in pair_log:
        a, b = q["ids"]
        (ax, ay), (bx, by) = G.ctr(work.cells[a]), G.ctr(work.cells[b])
        pc["broadcast" if a in bcast or b in bcast else "guided"].append(abs(ax - bx) + abs(ay - by))
    census = {k: dict(pairs=len(v), predicted_max_um=round(max(v), 2) if v else None,
                      predicted_gt_limit=sum(1 for x in v if x > limit)) for k, v in pc.items()}
    regions = {}
    for m, t in assign.items():
        regions.setdefault(t, []).append(orig[m][6])
    m1 = G.r2r_metrics(work) if pair_log else m0
    out_regions = []
    for (ix, iy), insts in sorted(regions.items()):
        out_regions.append(dict(name=f"ot_rg_{ix}_{iy}", box_um=[round(v, 4) for v in boxes[(ix, iy)]],
                                insts=sorted(insts)))
    return dict(schema=SCHEMA, limit_um=limit, margin_um=margin, tile_um=round(tile, 4), grid=[g[0], g[1]],
                core_um=list(core), die_um=list(D.die), class_d=m0["r2r_captures_gt405"] > 0,
                fixed_skipped=sorted({orig[c][6] for c in uf.p if c in fixed}),
                broadcast_skipped=sorted(orig[c][6] for c in bcast), pair_census=census,
                pairs=[{k: v for k, v in q.items() if k != "ids"} for q in pair_log], regions=out_regions,
                before=dict(r2r_max=m0["r2r_max"], r2r_captures_gt405=m0["r2r_captures_gt405"], r2r_worst=m0["r2r_worst"]),
                predicted=dict(r2r_max=m1["r2r_max"], r2r_captures_gt405=m1["r2r_captures_gt405"],
                               r2r_worst=m1["r2r_worst"],
                               basis="guided registers clamped into their box, all other cells at the last placement"))


def _with_cells(D, cells):
    class V:
        pass
    v = V()
    v.__dict__.update(D.__dict__)
    v.cells = cells
    v.kind = lambda cid: cells[cid][0] if cid in cells else None
    return v


def measure(D, spec):
    """distance of the spec pairs on dump D (exact flop-centre Manhattan), split into guided / broadcast pairs, + the
    full r2r census"""
    byname = {c[6]: c for c in D.cells.values()}
    bc = set(spec.get("broadcast_skipped") or [])
    lim = spec.get("limit_um", LIMIT)
    d = {"guided": [], "broadcast": []}
    for p in spec.get("pairs") or []:
        a, b = byname.get(p["launch"]), byname.get(p["capture"])
        if a and b:
            (ax, ay), (bx, by) = G.ctr(a), G.ctr(b)
            d["broadcast" if p["launch"] in bc or p["capture"] in bc else "guided"].append(abs(ax - bx) + abs(ay - by))
    m = G.r2r_metrics(D)
    out = {k: dict(pairs=len(v), max_um=round(max(v), 2) if v else None, gt_limit=sum(1 for x in v if x > lim))
           for k, v in d.items()}
    return dict(pairs=len(spec.get("pairs") or []), **out,
                r2r_max=m["r2r_max"], r2r_captures_gt405=m["r2r_captures_gt405"], r2r_worst=m["r2r_worst"])


def _tsv_quote(s):
    if any(ch in s for ch in "\t\n\r"):
        raise ValueError(f"instance name with tab/newline: {s!r}")
    return s


def install(kd, spec, outline=None, src=None):
    """write the kit hook files (region_guide.tcl/.tsv/_release.tcl/.json) and source them at the end of the kit's
    face_flops.tcl (PRE_GLOBAL_PLACE) / face_flops_release.tcl (PRE_DETAIL_PLACE).  -> record dict for freeze/rec.
    outline (w, h): the kit outline; a spec measured on another outline is stale -> SystemExit."""
    kd = Path(kd)
    if spec.get("schema") != SCHEMA:
        raise SystemExit(f"region guide: schema {spec.get('schema')} != {SCHEMA}")
    if outline is not None:
        dw = spec["die_um"][2] - spec["die_um"][0]
        dh = spec["die_um"][3] - spec["die_um"][1]
        if abs(dw - float(outline[0])) > 0.01 or abs(dh - float(outline[1])) > 0.01:
            raise SystemExit(f"region guide: spec outline {dw:g}x{dh:g} != kit outline {outline[0]}x{outline[1]} (stale guide)")
    regs = spec.get("regions") or []
    if not regs:
        raise SystemExit("region guide: spec has no regions (r2r passed: nothing to guide; do not pass --region-guide)")
    for f in ("face_flops.tcl", "face_flops_release.tcl"):
        if not (kd / f).is_file():
            raise SystemExit(f"region guide: kit has no {f} (PRE_GLOBAL_PLACE / PRE_DETAIL_PLACE hook)")
    names, boxes = set(), []
    lines = []
    for r in regs:
        if r["name"] in names or not r["name"].startswith("ot_rg_"):
            raise SystemExit(f"region guide: bad/duplicate region name {r['name']}")
        names.add(r["name"])
        b = [float(v) for v in r["box_um"]]
        for o in boxes:
            if b[0] < o[2] - 1e-6 and o[0] < b[2] - 1e-6 and b[1] < o[3] - 1e-6 and o[1] < b[3] - 1e-6:
                raise SystemExit(f"region guide: region {r['name']} overlaps another")
        boxes.append(b)
        lines.append("\t".join(["R", r["name"]] + [f"{v:.4f}" for v in b]))
        lines += ["\t".join(["I", r["name"], _tsv_quote(i)]) for i in r["insts"]]
    (kd / "region_guide.tsv").write_text("\n".join(lines) + "\n")
    (kd / "region_guide.tcl").write_text(TCL_HOOK.read_text())
    (kd / "region_guide_release.tcl").write_text(TCL_RELEASE.read_text())
    (kd / "region_guide.json").write_text(json.dumps(dict(spec, src=src), indent=1) + "\n")
    for f, s in (("face_flops.tcl", "region_guide.tcl"), ("face_flops_release.tcl", "region_guide_release.tcl")):
        with open(kd / f, "a") as fh:
            fh.write(f"# FLOW-23 class D --region-guide (soft GPL guide, released before DPL)\n"
                     f"source [file join [file dirname [info script]] {s}]\n")
    return dict(regions=len(regs), insts=sum(len(r["insts"]) for r in regs), tile_um=spec.get("tile_um"),
                predicted=spec.get("predicted"), src=src)


def load_design(geom_dir):
    gd = Path(geom_dir)
    return G.Design(str(gd / "geom.tsv"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("plan")
    a.add_argument("--geom-dir", required=True, help="geom_check.sh OUTDIR of the kit's last AUTO-GEOM (geom.tsv, auto_geom.json)")
    a.add_argument("--out", required=True)
    a.add_argument("--limit", type=float, default=LIMIT)
    a.add_argument("--margin", type=float, default=MARGIN, help="tile side = (limit - margin) / 2 unless --tile-um")
    a.add_argument("--tile-um", type=float, default=None)
    a.add_argument("--rounds", type=int, default=3)
    a.add_argument("--bcast-max", type=int, default=BCAST_MAX)
    a.add_argument("--force", action="store_true", help="plan even when auto_geom.json shows no r2r FAIL")
    b = sub.add_parser("measure")
    b.add_argument("--geom-dir", required=True)
    b.add_argument("--spec", required=True)
    a_ = ap.parse_args(argv)
    gd = Path(a_.geom_dir)
    if a_.cmd == "measure":
        print("REGION_GUIDE_MEASURE " + json.dumps(measure(load_design(gd), json.loads(Path(a_.spec).read_text()))))
        return 0
    try:
        ag = json.loads((gd / "auto_geom.json").read_text())
    except (OSError, ValueError) as e:
        print(f"REGION_GUIDE_ERROR auto_geom.json unreadable: {e}")
        return 2
    if not a_.force and not class_d(ag):
        print(f"REGION_GUIDE none: AUTO-GEOM r2r did not FAIL in {gd} (not class D); no spec written")
        return 0
    if not (gd / "geom.tsv").is_file():
        print(f"REGION_GUIDE_ERROR {gd}/geom.tsv missing")
        return 2
    spec = plan(load_design(gd), a_.limit, a_.margin, a_.tile_um, a_.rounds, a_.bcast_max)
    spec["source"] = dict(geom_dir=str(gd.resolve()), geom_tsv_sha256=sha256(gd / "geom.tsv"),
                          auto_geom_line=ag.get("line", "")[:300])
    if not spec["regions"]:
        print(f"REGION_GUIDE none: no movable endpoint in the failing pairs ({len(spec['pairs'])} pairs); no spec written")
        return 0
    Path(a_.out).write_text(json.dumps(spec, indent=1) + "\n")
    print(f"REGION_GUIDE {len(spec['regions'])} regions {sum(len(r['insts']) for r in spec['regions'])} registers "
          f"tile {spec['tile_um']} um grid {spec['grid'][0]}x{spec['grid'][1]}; r2r before {spec['before']['r2r_max']} "
          f"x{spec['before']['r2r_captures_gt405']} -> predicted {spec['predicted']['r2r_max']} "
          f"x{spec['predicted']['r2r_captures_gt405']} -> {a_.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
