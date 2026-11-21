"""KV-PLAN-R2 11-20 (EFAULT-STAGE): relay the eq inputs of the plan landing-check cell ot_dp_efault in hops <= reach.

ot_dp_efault (rtl/lib) samples the epoch outputs eq of its N in-boundary flops in ONE cycle: `fault <= fault | (armed &
~&eq)`, armed after AGE edges.  In KV kv3_hub_Wo (N = 26 landing ranks over a 1,279 x 1,676 um type) the worst eq path is
~2,700 um, placed WNS -1,040 ps on one endpoint.  The cell's own EQ_PIPE flops sit wherever the placer puts them; this form
puts D binder stations per eq bit on its Manhattan path at FIRM pre-GPL sites instead.

Opt-in asbuilt key (absent = byte-identical bind output):

    "efault_stage": {
        "types": ["kv3_hub_Wo"],            plan-cell types (regex, fullmatch; the bound type name matches too)
        "reach_um": 300,                    longest hop (source -> stage -> .. -> stage -> efault site)
        "cells": ["u_efault"],              optional: the ot_dp_efault cells to stage (default: every one in the type)
        "depth": 4,                         optional: minimum D (a computed need above it wins)
        "sites": "<json>" | {..}            optional: {type: {cell: {"at_um": [x, y], "src_um": {bus: [x, y]}}}}
        "avoid_macros": true                optional (default false): station sites off the type's placed macros and
                                            probe blockages (ft_seam_fix.macro_boxes; off_macro, 2 um gap), D grown
                                            until every ACTUAL hop src -> stages -> at is <= reach_um (D + 8 at most)
    }

Per staged cell, every eq bit i (an {"epoch": bus} entry; any other entry kind is an error) has a source point src_i (the
sites file src_um.<bus>, else the plan point of the in-boundary flop u_bin_<bus>: its relay_sites rows or the centre of
its clock-landing band, bind_pad_tail_split.src_xy) and the cell has a site `at` (sites at_um, else the L1 centre of the
sources).  Then

    h_i = ceil(|src_i - at|_1 / reach_um)        hops bit i needs
    D   = max(depth, max_i (h_i - 1))            stations per bit -- the SAME D on every bit

and every distinct eq source gets one ot_dp_dly_keep #(.W(1), .D(D)) u_efs<D>_<cell>_<i> (i = its first eq bit) whose
stage k (1..D) sits at k / (D + 1) of the x-first Manhattan path src_i -> at, so every hop is |src_i - at|_1 / (D + 1)
<= reach_um.  The cell is emitted with AGE + D (EQ_PIPE / EQ_PIPE_V must be absent or 0): the stations are reset-less but
flushed after D edges, and the armed check at edge AGE + D + 1 reads eq as sampled at edge AGE + 1, so the staged cell is
exactly the old check D cycles later (fault_D(k) = fault_0(k - D); same as the cell's own EQ_PIPE = D).  eq is a monitor
path: no lane latency changes.  D = 0 (every source within reach) leaves the cell as it was (recorded).

Receipt bind_efault_stage.json: types.<t>.<cell> = {depth, age_old, age_new, reach_um, at_um, max_hop_um, cells, flops,
chains: [{inst, bus, bits, src_um, dist_um}], sites: {<inst>.r[k] / <inst>.q: [x, y]}} -- sites in type_relay_sites key
form (plan partition_types[t].relay_sites, kit_istations rs_place_all: FIRM pre-GPL), like bind_intra_stations.json.

Fail closed: a key that matches no plan-cell type with an ot_dp_efault cell, a named cell that is not an ot_dp_efault cell
of a matched type, N != eq entries, a non-epoch eq entry, a non-integer AGE, EQ_PIPE / EQ_PIPE_V set, a source with no
point, reach_um not > 0, depth < 0, unknown keys.
"""
import json
import math
import re
from pathlib import Path

KEY = "efault_stage"
MODULE = "ot_dp_efault"
KEYS = {"types", "reach_um", "cells", "depth", "sites", "avoid_macros"}


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _xy(v, what):
    if not isinstance(v, (list, tuple)) or len(v) != 2 or not all(_num(a) for a in v):
        raise ValueError(f"asbuilt.{KEY}: {what} must be [x, y], got {v!r}")
    return (float(v[0]), float(v[1]))


def config(ab, base=None):
    """the checked option, or None when the key is absent"""
    c = (ab or {}).get(KEY)
    if c is None:
        return None
    if not isinstance(c, dict) or set(c) - KEYS or not isinstance(c.get("types"), list) or not c["types"] or \
            not all(isinstance(x, str) and x for x in c["types"]):
        raise ValueError(f"asbuilt.{KEY}: expected {{types: [regex..], reach_um, cells?, depth?, sites?}}")
    r = c.get("reach_um")
    if not _num(r) or r <= 0:
        raise ValueError(f"asbuilt.{KEY}: reach_um must be a number > 0")
    d = c.get("depth", 0)
    if not isinstance(d, int) or isinstance(d, bool) or d < 0:
        raise ValueError(f"asbuilt.{KEY}: depth must be an int >= 0")
    cells = c.get("cells")
    if cells is not None and (not isinstance(cells, list) or not cells or not all(isinstance(x, str) and x for x in cells)):
        raise ValueError(f"asbuilt.{KEY}: cells must be a non-empty list of plan cell names")
    am = c.get("avoid_macros", False)
    if not isinstance(am, bool):
        raise ValueError(f"asbuilt.{KEY}: avoid_macros must be true or false")
    sites = load_sites(c["sites"], base) if "sites" in c else {}
    return dict(types=[re.compile(x) for x in c["types"]], reach=float(r), depth=d,
                cells=None if cells is None else set(cells), sites=sites, avoid_macros=am)


def load_sites(v, base):
    if isinstance(v, dict):
        return v
    if not isinstance(v, str) or not v:
        raise ValueError(f"asbuilt.{KEY}.sites: expected a json path or an object")
    f = Path(v)
    if not f.is_absolute():
        f = Path(base or ".") / f
    try:
        d = json.loads(f.read_text())
    except (OSError, ValueError) as exc:
        raise ValueError(f"asbuilt.{KEY}.sites: cannot read {f}: {exc}") from exc
    if not isinstance(d, dict):
        raise ValueError(f"asbuilt.{KEY}.sites: {f} is not {{type: {{cell: {{at_um, src_um}}}}}}")
    return d


def selected(cfg, *names):
    return any(x.fullmatch(n) for x in cfg["types"] for n in names if n)


def staged_cells(cfg, cells):
    """the names of the ot_dp_efault cells of one plan-cell type to stage ({inst: cell}); ValueError when a named cell
    is missing or of another module"""
    eff = sorted(i for i, c in cells.items() if c.get("module") == MODULE)
    if cfg["cells"] is None:
        return eff
    bad = sorted(cfg["cells"] - set(eff))
    if bad:
        raise ValueError(f"{KEY}: cells {bad}: no {MODULE} cell of that name in the type")
    return sorted(cfg["cells"] & set(eff))


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def l1_centre(pts):
    """the point with the smallest largest Manhattan distance to pts"""
    u = [x + y for x, y in pts]
    v = [x - y for x, y in pts]
    uu, vv = (min(u) + max(u)) / 2.0, (min(v) + max(v)) / 2.0
    return ((uu + vv) / 2.0, (uu - vv) / 2.0)


def path_point(a, b, s):
    """the point at Manhattan run s from a on the x-first L path a -> (b.x, a.y) -> b"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    if s <= abs(dx):
        return (a[0] + math.copysign(s, dx), a[1])
    return (b[0], a[1] + math.copysign(min(s - abs(dx), abs(dy)), dy))


def need(dist, reach):
    """stations a run of `dist` needs so every hop is <= reach: ceil(dist / reach) - 1 (0 within reach)"""
    return max(0, int(math.ceil(dist / reach - 1e-9)) - 1)


def stage_sites(src, at, D):
    """D station sites on the x-first path src -> at, stage k (0-based) at (k + 1) / (D + 1) of the run"""
    L = md(src, at)
    return [[round(c, 3) for c in path_point(src, at, L * (k + 1) / (D + 1))] for k in range(D)]


def off_macro(boxes, xy, gap=2.0):
    """xy, or the nearest point gap um outside the box (x0, y0, x1, y1) whose interior holds it, 4 tries (the
    ft_seam_fix.off_macro rule, centre-only stations); None when it stays inside a box"""
    x, y = float(xy[0]), float(xy[1])
    for _ in range(4):
        hit = next((b for b in boxes if b[0] < x < b[2] and b[1] < y < b[3]), None)
        if hit is None:
            return [round(x, 3), round(y, 3)]
        x0, y0, x1, y1 = hit
        c = min(((x - x0 + gap, -1, 0), (x1 - x + gap, 1, 0), (y - y0 + gap, 0, -1), (y1 - y + gap, 0, 1)))
        x, y = x + c[1] * c[0], y + c[2] * c[0]
    return None


def chain_hop(src, regs, at):
    pts = [tuple(src)] + [tuple(r) for r in regs] + [tuple(at)]
    return max(md(a, b) for a, b in zip(pts, pts[1:]))


def plan_cell(cfg, tn, inst, cell, src_of, type_sites=None, boxes=None):
    """the staging of plan cell `inst` (an ot_dp_efault cell dict) of type tn: dict(depth, age_old, age_new, at_um,
    max_hop_um, chains [{bus, bits, src_um, dist_um, regs_um}]).  src_of(bus) -> (x, y) | None is the plan point of the
    in-boundary flop of the bus; type_sites the sites-file entry of the type ({cell: {at_um, src_um}}).  ValueError on
    anything ambiguous."""
    p = cell.get("params") or {}
    eq = (cell.get("conns") or {}).get("eq")
    if not isinstance(eq, list) or not eq:
        raise ValueError(f"{KEY} {tn}.{inst}: no eq conns")
    if not all(isinstance(e, dict) and set(e) == {"epoch"} and isinstance(e["epoch"], str) for e in eq):
        raise ValueError(f"{KEY} {tn}.{inst}: every eq entry must be {{\"epoch\": bus}} (one bit each)")
    try:
        n = int(p.get("N"))
    except (TypeError, ValueError):
        raise ValueError(f"{KEY} {tn}.{inst}: N {p.get('N')!r} is not an integer") from None
    if n != len(eq):
        raise ValueError(f"{KEY} {tn}.{inst}: N {n} != {len(eq)} eq entries")
    age = p.get("AGE")
    if isinstance(age, bool) or not (isinstance(age, int) or (isinstance(age, str) and re.fullmatch(r"\d+", age))):
        raise ValueError(f"{KEY} {tn}.{inst}: AGE {age!r} is not an integer literal")
    for k in ("EQ_PIPE", "EQ_PIPE_V"):
        v = p.get(k)
        if v is not None and not (v in (0, "0") or (isinstance(v, str) and re.fullmatch(r"\d+'h0+", v))):
            raise ValueError(f"{KEY} {tn}.{inst}: {k} {v!r} is set; stations and the cell's own eq pipe do not combine")
    row = (type_sites or {}).get(inst) or {}
    if not isinstance(row, dict) or set(row) - {"at_um", "src_um"}:
        raise ValueError(f"{KEY} {tn}.{inst}: sites row must be {{at_um?, src_um?}}")
    given = row.get("src_um") or {}
    if not isinstance(given, dict):
        raise ValueError(f"{KEY} {tn}.{inst}: sites src_um must be {{bus: [x, y]}}")
    unknown = sorted(set(given) - {e["epoch"] for e in eq})
    if unknown:
        raise ValueError(f"{KEY} {tn}.{inst}: sites src_um names buses not in its eq: {unknown[:4]}")
    chains, order = {}, []
    for i, e in enumerate(eq):
        b = e["epoch"]
        if b not in chains:
            xy = _xy(given[b], f"{tn}.{inst} src_um.{b}") if b in given else src_of(b)
            if xy is None:
                raise ValueError(f"{KEY} {tn}.{inst}: eq bus {b}: no source point (no sites src_um, no plan relay_sites "
                                 f"u_bin_{b}.q[*] and no clock-landing band)")
            chains[b] = dict(bus=b, bits=[], src_um=[round(float(xy[0]), 3), round(float(xy[1]), 3)])
            order.append(b)
        chains[b]["bits"].append(i)
    at = _xy(row["at_um"], f"{tn}.{inst} at_um") if "at_um" in row else \
        l1_centre([tuple(chains[b]["src_um"]) for b in order])
    at = (round(at[0], 3), round(at[1], 3))
    D = cfg["depth"]
    for b in order:
        c = chains[b]
        c["dist_um"] = round(md(c["src_um"], at), 3)
        D = max(D, need(c["dist_um"], cfg["reach"]))
    moved = None
    if boxes is not None and D:          # avoid_macros: off-macro sites, D grown until every actual hop <= reach
        for Dt in range(D, D + 9):
            regs = {b: [off_macro(boxes, s) for s in stage_sites(chains[b]["src_um"], at, Dt)] for b in order}
            if any(r is None for v in regs.values() for r in v):
                continue
            if max(chain_hop(chains[b]["src_um"], regs[b], at) for b in order) <= cfg["reach"] + 1e-6:
                break
        else:
            raise ValueError(f"{KEY} {tn}.{inst}: no off-macro station sites with every hop <= {cfg['reach']} um "
                             f"for depth {D}..{D + 8}")
        moved = sum(1 for b in order for r, s in zip(regs[b], stage_sites(chains[b]["src_um"], at, Dt))
                    if r != [round(c, 3) for c in s])
        D = Dt
        for b in order:
            chains[b]["regs_um"] = regs[b]
        hop = max(chain_hop(chains[b]["src_um"], chains[b]["regs_um"], at) for b in order)
    else:
        hop = 0.0
        for b in order:
            c = chains[b]
            c["regs_um"] = stage_sites(c["src_um"], at, D) if D else []
            hop = max(hop, c["dist_um"] / (D + 1))
    if hop > cfg["reach"] + 1e-6:          # cannot happen with the rule above: the guard keeps the law honest
        raise ValueError(f"{KEY} {tn}.{inst}: hop {hop:.1f} um > reach {cfg['reach']} um at depth {D}")
    age0 = int(age)
    out = dict(depth=D, age_old=age0, age_new=age0 + D, at_um=list(at), max_hop_um=round(hop, 3),
               reach_um=cfg["reach"], chains=[chains[b] for b in order])
    if boxes is not None:
        out["moved_off_macro"] = moved or 0
    return out


def site_rows(inst, regs):
    """type_relay_sites key form for the D-stage ot_dp_dly_keep `inst`: stage k at regs[k] (yosys names the last stage
    after the output port: <inst>.q, the others <inst>.r[k]); same form as bind_intra_stations.site_rows"""
    rows = {f"{inst}.r[{k}]": list(regs[k]) for k in range(len(regs) - 1)}
    rows[f"{inst}.q"] = list(regs[-1])
    return rows
