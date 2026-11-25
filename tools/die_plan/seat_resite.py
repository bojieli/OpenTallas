#!/usr/bin/env python3
"""seat_resite.py -- FP-CONVERGE-S81 11-25 (COORD FLOW-0930 S-08): PLAN-LEVEL first/last-register re-site for ADV-SEAT-ORIENT.

adv_seatgap.seat_orient flags an internal_stations chain whose first hop (launch pin from_um -> regs_um[0]) or last hop (regs_um[-1] -> capture
pin to_um) runs more than AGAINST_UM on the inside of the core face the pin sits on (the wire would cross the core).  This tool moves ONLY that
end register to the free side of the face: a lattice site (G = 4.32) outside every hard core (+HALO) and inside the outline (+INSET), with the pin
hop and the hop to the next element <= CAP (404 um), the register count unchanged, and the end no longer 'against'.  Chains with no legal site
are listed as skipped (never forced).  --flip-core lists cores whose pins are mostly against (a recommendation, no row).

  seat_resite.py rows PLAN --types @file|glob,glob --out ops.json      -> plan_ops.v1 ops + OPS.skipped.json + OPS.flip.json
  orient_lines(kit, plan=None, environ=None) -> WARN lines for kit_preflight (plan only; no kit seats needed): launch_gates.blocking() decides

The kit-seat orientation (ot_seat_o of relay seats) is relay_orient.py's job (S81-STAGE-SEAT wires it); this is the plan view of the same face rule
(adv_seatgap._face / _core_of), so both agree on 'pin face'.
"""
import argparse
import fnmatch
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adv_geom_static as G  # noqa: E402
import adv_seatgap as S  # noqa: E402

LAT = 4.32
HALO = 1.0
INSET = 8.0
CAP = 404.0
RINGS = 60


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _legal(p, rects, w, h):
    x, y = p
    if not (INSET <= x <= w - INSET and INSET <= y <= h - INSET):
        return False
    return not any(r[0] - HALO < x < r[2] + HALO and r[1] - HALO < y < r[3] + HALO for r in rects)


def _against(pin, nxt, n):
    return (nxt[0] - pin[0]) * n[0] + (nxt[1] - pin[1]) * n[1] < -S.AGAINST_UM


def _ring(around, ring):
    if ring == 0:
        return [(around[0], around[1])]
    pts = []
    for i in range(-ring, ring + 1):
        pts += [(around[0] + i * LAT, around[1] - ring * LAT), (around[0] + i * LAT, around[1] + ring * LAT),
                (around[0] - ring * LAT, around[1] + i * LAT), (around[0] + ring * LAT, around[1] + i * LAT)]
    return [(round(x, 3), round(y, 3)) for x, y in pts]


def fix_end(pin, n, old, nxt, rects, w, h, taken):
    """-> new register xy or None: legal lattice site on the free side of the face, hops <= CAP, minimal displacement from `old`;
    rings of pitch LAT around the point two lattice steps outside the pin; keep scanning 3 rings past the first legal one"""
    start = (pin[0] + n[0] * LAT * 2, pin[1] + n[1] * LAT * 2)
    best, first = None, None
    for ring in range(RINGS):
        if first is not None and ring > first + 3:
            break
        for p in _ring(start, ring):
            if p in taken or not _legal(p, rects, w, h):
                continue
            if (p[0] - pin[0]) * n[0] + (p[1] - pin[1]) * n[1] < -S.AGAINST_UM:
                continue
            if man(pin, p) > CAP or man(p, nxt) > CAP:
                continue
            first = ring if first is None else first
            d = man(p, old)
            if best is None or d < best[0]:
                best = (d, p)
    return None if best is None else [best[1][0], best[1][1]]


def type_fixes(tn, t):
    """-> (ops, skipped) for one type"""
    ops, skipped = [], []
    w, h = t.get("outline_um") or (0, 0)
    rects = G.hard_rects(t)
    taken = {tuple(round(float(c), 3) for c in r) for s in (t.get("internal_stations") or []) if isinstance(s, dict) for r in (s.get("regs_um") or [])
             if isinstance(r, (list, tuple)) and len(r) == 2}
    for i, s in enumerate(t.get("internal_stations") or []):
        if not isinstance(s, dict):
            continue
        fr, to = S._xy(s.get("from_um")), S._xy(s.get("to_um"))
        regs = [list(r) for r in (s.get("regs_um") or [])]
        pr = [S._xy(r) for r in regs]
        if not regs or any(p is None for p in pr) or fr is None or to is None:
            continue
        new = [list(r) for r in regs]
        changed = False
        for end, core_name, pin, nxt in (("launch", s.get("launch"), fr, pr[0]), ("capture", s.get("capture"), to, pr[-1])):
            r = S._core_of(core_name, rects) if core_name else None
            if r is None:
                continue
            n = S._face(pin, r)
            if n is None or not _against(pin, nxt, n):
                continue
            if any(k in s for k in ("bit_sites_um", "face_bit_sites_um", "bit_site_groups_um")):
                skipped.append((tn, i, end, "chain carries bit-site groups: not moved by this tool"))
                continue
            j = 0 if end == "launch" else len(regs) - 1
            other = (pr[1] if len(regs) > 1 else to) if end == "launch" else (pr[-2] if len(regs) > 1 else fr)
            if len(regs) == 1 and changed:
                skipped.append((tn, i, end, "single register against at both ends: needs a second register or a core flip"))
                continue
            p = fix_end(pin, n, pr[j], other, rects, w, h, taken)
            if p is None:
                skipped.append((tn, i, end, "no legal site <= %g um on the free side" % CAP))
                continue
            taken.add((round(p[0], 3), round(p[1], 3)))
            new[j] = p
            changed = True
        if changed:
            ops.append({"op": "replace", "path": f"/partition_types/{tn}/internal_stations/{i}/regs_um", "old": regs, "value": new})
    return ops, skipped


def flip_recommendations(t, min_share=0.5, min_hops=4):
    """cores whose pins' first/last hops are mostly against -> [(core, against, total)]"""
    rects = G.hard_rects(t)
    per = {}
    for s in t.get("internal_stations") or []:
        if not isinstance(s, dict):
            continue
        fr, to = S._xy(s.get("from_um")), S._xy(s.get("to_um"))
        regs = [p for p in (S._xy(r) for r in s.get("regs_um") or []) if p]
        for core_name, pin, nxt in ((s.get("launch"), fr, regs[0] if regs else to), (s.get("capture"), to, regs[-1] if regs else fr)):
            r = S._core_of(core_name, rects) if core_name else None
            if r is None or pin is None or nxt is None:
                continue
            n = S._face(pin, r)
            if n is None:
                continue
            a, tt = per.get(r[4], (0, 0))
            per[r[4]] = (a + (1 if _against(pin, nxt, n) else 0), tt + 1)
    return [(c, a, tt) for c, (a, tt) in sorted(per.items()) if tt >= min_hops and a / tt >= min_share]


def types_from(raw, spec):
    pt = raw.get("partition_types") or {}
    if spec.startswith("@"):
        names = set(Path(spec[1:]).read_text().split())
        return [n for n in pt if n in names]
    globs = [g for g in spec.split(",") if g]
    return [n for n in pt if any(fnmatch.fnmatchcase(n, g) for g in globs)]


def rows(plan, spec, out):
    raw = json.load(open(plan))
    ops, skipped, flips = [], [], {}
    for tn in types_from(raw, spec):
        o, sk = type_fixes(tn, raw["partition_types"][tn])
        ops += o
        skipped += sk
        f = flip_recommendations(raw["partition_types"][tn])
        if f:
            flips[tn] = f
    json.dump({"schema": "plan_ops.v1", "ops": ops}, open(out, "w"), indent=1)
    json.dump(skipped, open(out + ".skipped.json", "w"))
    json.dump(flips, open(out + ".flip.json", "w"))
    return len(ops), len(skipped), len(flips)


def orient_lines(kit, plan=None, environ=None):
    """WARN lines for kit_preflight: SEAT-ORIENT of the kit's type from the PLAN (no kit seats needed); report-only"""
    env = os.environ if environ is None else environ
    plan = plan or env.get("OT_LAUNCH_PLAN")
    tn = env.get("OT_KIT_TYPE") or Path(kit).name
    if not plan or not Path(plan).is_file():
        return ["SKIP SEAT-ORIENT-PREFLIGHT no plan (--plan / OT_LAUNCH_PLAN)"]
    t = (json.load(open(plan)).get("partition_types") or {}).get(tn)
    if t is None:
        return [f"SKIP SEAT-ORIENT-PREFLIGHT type {tn} not in plan"]
    a, tot, ex = S.seat_orient(t)
    if not a:
        return []
    return [f"WARN ADV-SEAT-ORIENT-PREFLIGHT {tn}: {a} of {tot} core-face hops against their pin face ({100 * a // max(tot, 1)}%): first/last register inside the pin's core face; "
            f"fix: seat_resite.py rows (plan) or relay_orient.py (kit seats); e.g. {', '.join(str(e[0]) + ':' + e[1] for e in ex[:3])}"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rows")
    r.add_argument("plan")
    r.add_argument("--types", required=True)
    r.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    n, sk, fl = rows(a.plan, a.types, a.out)
    print(f"seat_resite: ops {n} skipped {sk} flip-recommendations {fl} -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
