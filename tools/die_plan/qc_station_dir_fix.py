#!/usr/bin/env python3
"""DIE-QC-97 11-11 STDIR: flip out-bus internal_station chains written face -> leaf (PLAN-ROUTE-1 station lint INVERTED,
COORD S7 class; same transform as DIE-KV-97 phyrev_1111 ccaf9e17d801).

kit_istations sites station k of an out-bus internal_station at regs_um[k] counted from the launch (leaf) end, unless
the entry is launched at the face ('face bus ...', KW-FIX-27).  27 QC entries (cbf/cbn_q0* y_o*, S face, launch
u_t*.n_y; sle/slw_hc* cw_n*, N face, launch u_pstn.cw_n*) list from_um ON the face edge and regs_um face first, so
the kit puts stage 0 next to the face and the chain zig-zags core -> face -> mid -> core -> face (placed kits: first
and last hops ~940-1010 um).

Signature (all must hold): conn bus:X with plan bus X dir 'out'; launch is not a face ('face' not in launch); capture
names the face ('face' in capture); from_um on the outline edge, to_um not; >= 2 regs and regs_um[0] closer to from_um
than regs_um[-1] (listed face first).
Fix: swap from_um / to_um, reverse regs_um.  Same stations, same sites, same stage count: cycles unchanged, EQ by
construction.  Idempotent (after the flip from_um is off the edge).  Entries with exact bank sites (bit_sites_um /
face_bit_sites_um) are reported and left alone.

The output is the input text with only the flipped entries re-serialised in place (byte-identical elsewhere).

usage: qc_station_dir_fix.py PLAN_IN PLAN_OUT [--types a,b] [--match RE] [--expect N] [--reach 405] [--no-schema]
exit 1 (output not written) when --expect does not match, a flipped chain has a hop over --reach, or the output has a
schema.validate error the input does not have.
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EDGE_TOL = 2.0


def on_edge(p, W, H, tol=EDGE_TOL):
    return min(p[0], p[1], W - p[0], H - p[1]) <= tol


def l1(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def hops(e):
    pts = [e["from_um"]] + list(e["regs_um"]) + [e["to_um"]]
    return [round(l1(pts[i], pts[i + 1]), 1) for i in range(len(pts) - 1)]


def inverted(t):
    """(index, entry) of the out-bus internal_stations written face -> leaf."""
    W, H = map(float, t.get("outline_um") or (0, 0))
    if not W or not H:
        return
    buses = {b.get("name"): b for b in t.get("buses") or []}
    for i, e in enumerate(t.get("internal_stations") or []):
        conn = str(e.get("conn", ""))
        b = buses.get(conn[4:]) if conn.startswith("bus:") else None
        regs = e.get("regs_um") or []
        if not b or b.get("dir") != "out" or len(regs) < 2 or not e.get("from_um") or not e.get("to_um"):
            continue
        L, C = str(e.get("launch", "")).lower(), str(e.get("capture", "")).lower()
        if "face" in L or "face" not in C:
            continue
        f, z = e["from_um"], e["to_um"]
        if not on_edge(f, W, H) or on_edge(z, W, H):
            continue
        if l1(regs[0], f) >= l1(regs[-1], f):
            continue
        yield i, e


def type_spans(text):
    """{type: (start, end)} text spans of the partition_types values (top-level key, any whitespace)."""
    dec = json.JSONDecoder()
    ws = re.compile(r"\s*")
    i = ws.match(text, 0).end()
    assert text[i] == "{"
    i += 1
    while True:
        i = ws.match(text, i).end()
        if text[i] == "}":
            raise SystemExit("qc_station_dir_fix: no partition_types")
        key, i = dec.raw_decode(text, i)
        i = ws.match(text, i).end()
        assert text[i] == ":"
        i = ws.match(text, i + 1).end()
        if key != "partition_types":
            _, i = dec.raw_decode(text, i)
            i = ws.match(text, i).end()
            assert text[i] in ",}"
            i += 1
            continue
        assert text[i] == "{"
        i += 1
        spans = {}
        while True:
            i = ws.match(text, i).end()
            if text[i] == "}":
                return spans
            tn, i = dec.raw_decode(text, i)
            i = ws.match(text, i).end()
            assert text[i] == ":"
            i = ws.match(text, i + 1).end()
            _, j = dec.raw_decode(text, i)
            spans[tn] = (i, j)
            i = ws.match(text, j).end()
            if text[i] == ",":
                i += 1


def apply(text, types=None, match=None):
    """-> (out_text, done, skipped); done = [(type, index, conn, regs, hops_before, hops_after)]."""
    plan = json.loads(text)
    orig = copy.deepcopy(plan)
    T = plan["partition_types"]
    done, skipped, edits = [], [], []
    for tn, t in T.items():
        if types and tn not in types:
            continue
        if match and not re.search(match, tn):
            continue
        for i, e in list(inverted(t)):
            if "bit_sites_um" in e or "face_bit_sites_um" in e:
                skipped.append((tn, i, e["conn"], "exact bank sites"))
                continue
            old = json.dumps(e, separators=(",", ":"))
            hb = hops(e)
            e["from_um"], e["to_um"] = e["to_um"], e["from_um"]
            e["regs_um"] = list(reversed(e["regs_um"]))
            edits.append((tn, old, json.dumps(e, separators=(",", ":"))))
            done.append((tn, i, e["conn"], len(e["regs_um"]), hb, hops(e)))
    # nothing but the flipped entries' from_um / to_um / regs_um order moves
    for k in plan:
        if k != "partition_types":
            assert plan[k] == orig[k], k
    flipped = {(d[0], d[1]) for d in done}
    for tn, t in T.items():
        o = orig["partition_types"][tn]
        assert {k: v for k, v in t.items() if k != "internal_stations"} == \
            {k: v for k, v in o.items() if k != "internal_stations"}, tn
        a, b = t.get("internal_stations") or [], o.get("internal_stations") or []
        assert len(a) == len(b), tn
        for i, (e, f) in enumerate(zip(a, b)):
            if (tn, i) not in flipped:
                assert e == f, (tn, i)
                continue
            assert {k: v for k, v in e.items() if k not in ("from_um", "to_um", "regs_um")} == \
                {k: v for k, v in f.items() if k not in ("from_um", "to_um", "regs_um")}
            assert e["regs_um"] == f["regs_um"][::-1] and e["from_um"] == f["to_um"] and e["to_um"] == f["from_um"]
    # in-place text edit inside each touched type's own span (clone types carry identical entries); the full
    # re-parse below proves nothing else moved
    spans = type_spans(text)
    pieces, last = [], 0
    by_type = {}
    for tn, old, new in edits:
        by_type.setdefault(tn, []).append((old, new))
    for tn in sorted(by_type, key=lambda k: spans[k][0]):
        a, b = spans[tn]
        seg = text[a:b]
        for old, new in by_type[tn]:
            if seg.count(old) != 1:
                raise SystemExit(f"qc_station_dir_fix: {tn}: entry text found {seg.count(old)}x in the type (plan not "
                                 f"in compact JSON?): {old[:120]}")
            seg = seg.replace(old, new)
        pieces += [text[last:a], seg]
        last = b
    out = "".join(pieces) + text[last:]
    assert json.loads(out) == plan
    return out, done, skipped


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan_in")
    ap.add_argument("plan_out")
    ap.add_argument("--types")
    ap.add_argument("--match")
    ap.add_argument("--expect", type=int, help="fail unless exactly N entries are flipped")
    ap.add_argument("--reach", type=float, default=405.0, help="max hop (um, Manhattan) on a flipped chain")
    ap.add_argument("--no-schema", action="store_true")
    a = ap.parse_args(argv)
    text = open(a.plan_in).read()
    out, done, skipped = apply(text, set(a.types.split(",")) if a.types else None, a.match)
    bad = 0
    for tn, i, conn, n, hb, ha in done:
        over = max(ha) > a.reach
        bad |= over
        print(f"FLIP\t{tn}\t{i}\t{conn}\tregs={n}\thops_after={ha}\tmax={max(ha)}{'  OVER' if over else ''}")
    for s in skipped:
        print("SKIP\t" + "\t".join(map(str, s)))
    if a.expect is not None and len(done) != a.expect:
        print(f"qc_station_dir_fix: flipped {len(done)} != --expect {a.expect}", file=sys.stderr)
        bad = 1
    if not a.no_schema:
        sys.path.insert(0, str(HERE))
        import schema as S
        e_in = S.validate(json.loads(text))
        errs = S.validate(json.loads(out))
        new = [e for e in errs if e not in set(e_in)]
        for e in new:
            print(f"SCHEMA ERROR (new) {e}")
        bad |= bool(new)
        print(f"schema: {len(errs)} errors on the output, {len(e_in)} on the input, {len(new)} new")
    if bad:
        print("qc_station_dir_fix: FAIL, output not written", file=sys.stderr)
        return 1
    Path(a.plan_out).write_text(out)
    print(f"qc_station_dir_fix: {len(done)} entries in {len({d[0] for d in done})} types -> {a.plan_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
