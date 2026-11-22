#!/usr/bin/env python3
"""LANDING-BAND-CORE (FLOW-FLEET-R1 11-22, FABLE-CLOSURE-STRATEGY lever 7, COORD class item): G0 static check
`landing band ∩ core/macro footprint = 0` for every type.

Root cause it catches (S81 kv_leaf t5, J7 / candMISC5): the C1n regrid moved vp lane cores g_ln[4] / g_ln[0] (114.48 um square) onto the
N-face landing bands: ft0_i covered 100 %, ft1_i 52 %, monitor_0 88 %.  G0 passed; only a failed global place showed it.  Same class:
KV io_cor_v1 ("band too small or blocked"), KV pv CLAND.

Bands (type frame, clock.landing_contract):
  bands[<bus>]                    rect_um / rects_um   clock-landing ring bands (data rings, monitor_* reset/ready monitors)
  native_stage_groups.groups[]    rect_um (tag)        native stage landing bands (stage:*)
  group_rects_um[<name>]          rect                 explicit landing group rects
Footprints: placement_obstacles.placement_boxes(t) (hard cores, placed macros, probe blockages; no halo).  Touching edges is legal;
one finding per (type, band, core) with the covered share of the band.

OWN LANDING CORE (COORD 11-22, KV HGI: 106 hg/hgi bands '100 % covered' by their own landing core): a band's own landing core / landing
group cell IS the band's footprint and is never an overlap.  Own = named cl_<band> / u_cland_<band> (band name with non-word chars as _,
'#i' rect suffix dropped) or a box equal to the band rect within OWN_TOL_UM on every edge (track offsets: 0.012 um seen).  An own core
by name that still covers >= OWN_KEEP_SHARE of its band is on its band (QC cl_ cores sit 2.17 um off their band rect: grid, not a
defect); one that covers less has moved off it (the KV R6d class: core moved, band left behind) and is reported as 'own landing core
offset from its band'.

ERROR ON NEW, WARN ON INHERITED (COORD ruling 11-22: no new restrictive gate; KV D28 / S81 J8 must not fail on inherited overlaps):
  base = the plan of record the event starts from (check.py --band-base PLAN; publish_gate passes the die's live plan).  A finding whose
  (type stem, band kind, band, core) overlaps in the base by at least the same area (1e-3 um2 slack) is INHERITED -> WARN
  "[inherited]"; a new overlap, or one the event makes larger, -> ERROR "[new]" / "[larger]".  Type stem = name without __cl<hash> / __pv<hash>
  (events re-hash type names).  No base given -> every finding is a WARN "[no base]": new and inherited cannot be told apart.
  The G0 report summary lists the inherited findings (landing_band_core.inherited) for the owners' next event.
HARD RINGS (FIX-SYNC-KVHEAD 11-22, HARD-RING-BAND-1): a band whose ring is a signed hard child (hard_cores[] param_wrap, or band.hard_core)
is not a placement region (landing_place emits no ring group for it); it is skipped as a band.  The hard child's box stays an obstacle
for every soft band.  KV D28 hub_Ei/Eo/Wo: 17 "[new]" findings were all such dead hard-ring band rects.
Read-only, stdlib + the plan's own schema helpers.

  python3 tools/die_plan/landing_band_core.py PLAN_OR_TYPE.json [--base PLAN] [--types REGEX]   (exit 1 on any new/larger overlap)
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
CHECK = "landing_band_core"
EPS = 1e-6
OWN_TOL_UM = 0.5
OWN_KEEP_SHARE = 0.5


def _rect(r):
    try:
        r = [float(v) for v in r]
    except (TypeError, ValueError):
        return None
    return r if len(r) == 4 and r[2] > r[0] and r[3] > r[1] else None


def hard_ring_buses(t):
    """HARD-RING-BAND-1 (FIX-SYNC-KVHEAD 11-22): buses whose ring the type realises as a SIGNED hard child (hard_cores[] param_wrap
    on a count-aligned ring base at u_bound.u_cland_<bus>, clock_landings.hard_ring_params) or whose band names a hard_core.  Such a
    band emits no ring group (landing_place skips it), so its rect is not a placement region: the hard child's own box is its
    footprint, and that box is still checked against every SOFT band of the type."""
    from clock_landings import HARD_RING_BASES
    out = set()
    for hc in (t or {}).get("hard_cores") or []:
        pw = (hc or {}).get("param_wrap") or {}
        inst = ((hc or {}).get("physical_inst") or "").removeprefix("u_bound.")
        if isinstance(pw, dict) and pw.get("base") in HARD_RING_BASES and inst.startswith("u_cland_"):
            out.add(inst[len("u_cland_"):])
    return out


def band_rects(t):
    """-> [(kind, name, rect)] of type t's landing bands (bands realised as hard rings excluded: hard_ring_buses)"""
    lc = (((t or {}).get("clock") or {}).get("landing_contract") or {})
    out = []
    hard = hard_ring_buses(t)
    for bus, b in sorted((lc.get("bands") or {}).items()):
        if not isinstance(b, dict) or bus in hard or b.get("hard_core"):
            continue
        rs = b.get("rects_um") or ([b["rect_um"]] if b.get("rect_um") else [])
        for i, r in enumerate(rs):
            r = _rect(r)
            if r:
                out.append(("band", bus if len(rs) == 1 else f"{bus}#{i}", r))
    for i, g in enumerate(((lc.get("native_stage_groups") or {}).get("groups") or [])):
        r = _rect((g or {}).get("rect_um"))
        if r:
            out.append(("stage_band", str(g.get("tag") or f"group{i}"), r))
    for name, r in sorted((lc.get("group_rects_um") or {}).items()):
        r = _rect(r)
        if r:
            out.append(("group_band", name, r))
    seen, uniq = set(), []
    for k, n, r in out:
        key = (k, n, tuple(round(v, 4) for v in r))
        if key not in seen:
            seen.add(key)
            uniq.append((k, n, r))
    return uniq


def inter(a, b):
    w, h = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > EPS and h > EPS else 0.0


def _norm(name):
    return re.sub(r"\W", "_", str(name).split("#")[0])


def own_core(band, core):
    """True when CORE is the band's own landing core / landing group cell by name"""
    b = _norm(band)
    leaf = core.rsplit(".", 1)[-1]
    return leaf in (f"cl_{b}", f"u_cland_{b}", f"cl_{b.replace('stage_', '', 1)}") or core in (f"cl_{band}", f"u_cland_{band}")


def same_rect(a, b, tol=OWN_TOL_UM):
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def findings_type(tn, t, boxes=None):
    """-> [dict(type, kind, band, rect, core, core_rect, overlap_um2, share)]"""
    if boxes is None:
        from placement_obstacles import placement_boxes
        boxes = placement_boxes(t)
    out = []
    for kind, name, r in band_rects(t):
        area = (r[2] - r[0]) * (r[3] - r[1])
        for core, cb in sorted(boxes.items()):
            if same_rect(r, cb):
                continue                                   # the band's own landing core / group cell: its footprint, not an overlap
            a = inter(r, cb)
            if a > EPS:
                own = own_core(name, core)
                if own and a / area >= OWN_KEEP_SHARE:
                    continue                               # own landing core on its band (grid offset only)
                out.append(dict(type=tn, kind=kind, band=name, rect=r, core=core, core_rect=[float(v) for v in cb],
                                overlap_um2=round(a, 3), share=round(a / area, 3), own=own))
    return out


def fmt(r):
    return "[" + ",".join(f"{v:g}" for v in r) + "]"


def message(f):
    if f.get("own"):
        return (f"{f['type']}: landing {f['kind']} {f['band']} {fmt(f['rect'])}: its own landing core {f['core']} {fmt(f['core_rect'])} is "
                f"offset from the band ({f['overlap_um2']:g} um2, {100 * f['share']:.0f} % of the band shared): the core moved and left the band "
                f"behind (KV R6d class); move the band with its core")
    return (f"{f['type']}: landing {f['kind']} {f['band']} {fmt(f['rect'])} overlaps core {f['core']} {fmt(f['core_rect'])} "
            f"({f['overlap_um2']:g} um2, {100 * f['share']:.0f} % of the band): move the core or re-site the band before any kit "
            f"(a regrid onto a band fails global place)")


def stem(tn):
    return re.sub(r"__(cl|pv)[0-9a-f]{6,}", "", tn)


def key(f):
    return (stem(f["type"]), f["kind"], f["band"], f["core"])


def plan_findings(types, used=(), only=None, boxes_fn=None):
    out = []
    for tn in sorted(types):
        if (used and tn not in used) or (only and not re.search(only, tn)):
            continue
        t = types[tn]
        out += findings_type(tn, t, boxes_fn(t) if boxes_fn else None)
    return out


def base_index(base_raw, boxes_fn=None):
    """base plan raw dict (partition_types / partitions) -> {key: max overlap_um2}"""
    if not base_raw:
        return None
    types = base_raw.get("partition_types") or {}
    used = {p["type"] for p in base_raw.get("partitions", []) if isinstance(p, dict) and p.get("type")}
    idx = {}
    for f in plan_findings(types, used, boxes_fn=boxes_fn):
        idx[key(f)] = max(idx.get(key(f), 0.0), f["overlap_um2"])
    return idx


def classify(findings, idx, slack=1e-3):
    """-> [(status, finding, base_um2)]; status new | larger | inherited | nobase"""
    out = []
    for f in findings:
        if idx is None:
            out.append(("nobase", f, None))
            continue
        b = idx.get(key(f))
        out.append(("new" if b is None else ("larger" if f["overlap_um2"] > b + slack else "inherited"), f, b))
    return out


def check(P, R, types=None, boxes_fn=None, base=None):
    """G0: ERROR per new / larger (type, band, core) overlap vs the base plan of record, WARN per inherited one (or every one when no base
    is given), over the types used by a partition (all types when none is placed)"""
    used = {inst["type"] for inst in P.parts.values()} if getattr(P, "parts", None) else set()
    idx = base_index(base, boxes_fn) if isinstance(base, dict) and "partition_types" in base else base   # raw plan, or a ready index
    rows = classify(plan_findings(P.types, used, types, boxes_fn), idx)
    cnt = {"new": 0, "larger": 0, "inherited": 0, "nobase": 0}
    inherited = []
    for st, f, b in rows:
        cnt[st] += 1
        msg = message(f)
        if st == "new":
            R.err(CHECK, "[new] " + msg, type=f["type"])
        elif st == "larger":
            R.err(CHECK, f"[larger: base {b:g} um2] " + msg, type=f["type"])
        elif st == "inherited":
            R.warn(CHECK, f"[inherited: base {b:g} um2] " + msg, type=f["type"])
            inherited.append(msg)
        else:
            R.warn(CHECK, "[no base plan: new vs inherited unknown] " + msg, type=f["type"])
    return dict(findings=len(rows), errors=cnt["new"] + cnt["larger"], base=idx is not None, **cnt, inherited_list=inherited[:400])


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan", help="plan json (partition_types) or one type json")
    ap.add_argument("--types")
    ap.add_argument("--base", help="base plan of record: findings it already has (same or smaller) are inherited (WARN)")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    types = raw.get("partition_types") or {Path(a.plan).stem: raw}
    used = {p["type"] for p in raw.get("partitions", [])}
    idx = base_index(json.loads(Path(a.base).read_text())) if a.base else None
    rows = classify(plan_findings(types, used, a.types), idx)
    n = 0
    for st, f, b in rows:
        lvl = "ERROR" if st in ("new", "larger") else "WARN"
        n += lvl == "ERROR"
        print(f"{lvl} [{st}{'' if b is None else ' base %g um2' % b}] " + message(f))
    print(f"LANDING-BAND-CORE {'FAIL' if n else 'PASS'}: {n} new/larger, {len(rows) - n} inherited/unbased")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
