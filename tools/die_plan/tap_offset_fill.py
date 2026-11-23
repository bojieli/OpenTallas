#!/usr/bin/env python3
"""TAPOFF-FILL (TAP-GRID-R5 11-23, COORD class ruling; KV ledger x10, S81 rc33): every tap appended to a type that carries a
plan clock.tap_offset.per_port_ps row (R-CLOCK-7) gets its offset row in the SAME step.

A port missing from a listed type's row is charged the window [-W, 0] by gen_phys.tap_offset_lines (W = the type's offset
span), so an appended tap silently times at the widest window: KV D29 r5 had 9 pv types with 1,440 added tap ports and no
row (SOFTFLOP / V3TAPS appends), S81 rc33 PINREG-TAPS appends 490 pin-face taps.  The offset of a tap is its measured routed
arrival minus the partition's median glue tap (die_sta_related --kit-offset-out); a new tap has no measurement yet, so it
takes the row of its NEAREST listed glue tap (L1, current tap sites: an added tap splits a neighbour's sinks and is fed by the
same die branch -- FABLE-UNC-QC tapoff_rows.py rule), or {TT 0, FF 0, tol = the table's smallest tol} (0 = the table's own
median-glue reference) when the type has no listed glue tap left.  Core ports (clk_c*) are never written.  The rows are an
estimate until the next die_sta_related re-measure, which overwrites them.

  python3 tap_offset_fill.py check PLAN            -> one MISSING line per type, exit 1 when any (PRE: FAIL TAPOFF-MISSING)
  python3 tap_offset_fill.py fill PLAN OUT [--types a,b] [--rows ROWS.json]
Library: missing(raw, P=None, types=None) -> {type: [port]};  fill(raw, P=None, types=None) -> {type: {port: row}} (writes raw)."""
import argparse
import json
import sys
from pathlib import Path


def _table(raw):
    return (((raw.get("clock") or {}).get("tap_offset") or {}).get("per_port_ps")) or {}


def _plan(raw, P):
    if P is not None:
        return P
    import schema
    return schema.Plan(raw, None)


def _glue(P, tn):
    import schema
    return [(n, float(x), float(y)) for n, x, y in schema.tap_grid(P, tn) if not str(n).startswith("clk_c")]


def missing(raw, P=None, types=None):
    """{type: [tap port without a row]} over the types that HAVE a row (a type without one keeps the window form)."""
    tab = _table(raw)
    if not tab:
        return {}
    P = _plan(raw, P)
    out = {}
    for tn in sorted(tab):
        if (types and tn not in types) or tn not in raw.get("partition_types", {}):
            continue
        miss = [n for n, _x, _y in _glue(P, tn) if n not in tab[tn]]
        if miss:
            out[tn] = miss
    return out


def fill(raw, P=None, types=None):
    """write a row for every missing port (see module doc); -> {type: {port: row}} written."""
    tab = _table(raw)
    if not tab:
        return {}
    P = _plan(raw, P)
    done = {}
    for tn in sorted(tab):
        if (types and tn not in types) or tn not in raw.get("partition_types", {}):
            continue
        rows = tab[tn]
        sites = _glue(P, tn)
        xy = {n: (x, y) for n, x, y in sites}
        live = [n for n in rows if n in xy and not n.startswith("clk_c")]
        tol = min((float(v["tol"]) for v in rows.values()), default=0.0)
        new = {}
        for n, x, y in sites:
            if n in rows:
                continue
            if live:
                src = min(live, key=lambda q: (abs(xy[q][0] - x) + abs(xy[q][1] - y), q))
                r = rows[src]
                new[n] = {"TT": float(r["TT"]), "FF": float(r["FF"]), "tol": float(r["tol"]), "from": src}
            else:
                new[n] = {"TT": 0.0, "FF": 0.0, "tol": tol, "from": None}
        for n, r in new.items():
            rows[n] = {k: r[k] for k in ("TT", "FF", "tol")}
        if new:
            done[tn] = new
    return done


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("check", "fill"))
    ap.add_argument("plan")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--types", default="")
    ap.add_argument("--rows", help="fill: also write the rows written ({type: {port: row + from}}) here")
    ap.add_argument("--tools", help="tools/die_plan of the tree (default: next to this file)")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(Path(a.tools).resolve() if a.tools else Path(__file__).resolve().parent))
    raw = json.loads(Path(a.plan).read_text())
    types = set(x for x in a.types.split(",") if x) or None
    if a.cmd == "check":
        m = missing(raw, types=types)
        for tn, ps in m.items():
            print(f"TAPOFF MISSING {tn}: {len(ps)} tap port(s) with no clock.tap_offset row: {', '.join(ps[:6])}"
                  f"{' ...' if len(ps) > 6 else ''}")
        print(f"TAPOFF CHECK {'FAIL' if m else 'PASS'} types {len(m)} ports {sum(len(v) for v in m.values())}")
        return 1 if m else 0
    if not a.out:
        ap.error("fill needs OUT")
    done = fill(raw, types=types)
    Path(a.out).write_text(json.dumps(raw) + "\n")
    if a.rows:
        Path(a.rows).write_text(json.dumps(done, indent=1) + "\n")
    print(f"TAPOFF FILL types {len(done)} ports {sum(len(v) for v in done.values())} -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
