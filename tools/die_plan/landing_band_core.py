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
any positive-area intersection is an ERROR (check `landing_band_core`), one finding per (type, band, core) with the covered share of
the band.  Read-only, stdlib + the plan's own schema helpers.

  python3 tools/die_plan/landing_band_core.py PLAN_OR_TYPE.json [--types REGEX]     (exit 1 on any overlap)
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
CHECK = "landing_band_core"
EPS = 1e-6


def _rect(r):
    try:
        r = [float(v) for v in r]
    except (TypeError, ValueError):
        return None
    return r if len(r) == 4 and r[2] > r[0] and r[3] > r[1] else None


def band_rects(t):
    """-> [(kind, name, rect)] of type t's landing bands"""
    lc = (((t or {}).get("clock") or {}).get("landing_contract") or {})
    out = []
    for bus, b in sorted((lc.get("bands") or {}).items()):
        if not isinstance(b, dict):
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


def findings_type(tn, t, boxes=None):
    """-> [dict(type, kind, band, rect, core, core_rect, overlap_um2, share)]"""
    if boxes is None:
        from placement_obstacles import placement_boxes
        boxes = placement_boxes(t)
    out = []
    for kind, name, r in band_rects(t):
        area = (r[2] - r[0]) * (r[3] - r[1])
        for core, cb in sorted(boxes.items()):
            a = inter(r, cb)
            if a > EPS:
                out.append(dict(type=tn, kind=kind, band=name, rect=r, core=core, core_rect=[float(v) for v in cb],
                                overlap_um2=round(a, 3), share=round(a / area, 3)))
    return out


def fmt(r):
    return "[" + ",".join(f"{v:g}" for v in r) + "]"


def message(f):
    return (f"{f['type']}: landing {f['kind']} {f['band']} {fmt(f['rect'])} overlaps core {f['core']} {fmt(f['core_rect'])} "
            f"({f['overlap_um2']:g} um2, {100 * f['share']:.0f} % of the band): move the core or re-site the band before any kit "
            f"(a regrid onto a band fails global place)")


def check(P, R, types=None, boxes_fn=None):
    """G0: one ERROR per (type, band, core) overlap over the types used by a partition (all types when none is placed)"""
    used = {inst["type"] for inst in P.parts.values()} if getattr(P, "parts", None) else set()
    n, hit = 0, set()
    for tn in sorted(P.types):
        if (used and tn not in used) or (types and not re.search(types, tn)):
            continue
        t = P.types[tn]
        for f in findings_type(tn, t, boxes_fn(t) if boxes_fn else None):
            R.err(CHECK, message(f), type=tn)
            n += 1
            hit.add(tn)
    return dict(findings=n, types=len(hit))


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan", help="plan json (partition_types) or one type json")
    ap.add_argument("--types")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    types = raw.get("partition_types") or {Path(a.plan).stem: raw}
    used = {p["type"] for p in raw.get("partitions", [])}
    n = 0
    for tn in sorted(types):
        if (used and tn not in used) or (a.types and not re.search(a.types, tn)):
            continue
        for f in findings_type(tn, types[tn]):
            print("ERROR " + message(f))
            n += 1
    print(f"LANDING-BAND-CORE {'FAIL ' + str(n) + ' overlap(s)' if n else 'PASS'}")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
