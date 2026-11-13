#!/usr/bin/env python3
"""QC-S28-BIND (c): RESET TREES PAD, NEVER SHORTEN (reset_tree.wavefront_min_depth; OWNER reset rule, DIE-QC event rule).

For every soft partition type of PLAN, the wavefront reset tree depth on PLAN is compared with the published depth on
REF (the plan before the floorplan move, here s28a_bc = pre-HF-1c).  A type whose tree got SHALLOWER (HF-1c re-scaled
rows: hc 717.12, su 1399.68, ...) gets reset.wavefront_min_depth = REF depth, so its release cohort, its START-stage
raw_reset depths and its local-copy depths stay the published ones.  Row-variant types (T_h) use their base type T on
REF.  Types already at or deeper than REF are untouched (pad only).  Deterministic and idempotent; one EQ row per
changed type (reset release depth PLAN -> padded).

  reset_pad.py PLAN_IN REF PLAN_OUT REPORT.json [EQ.tsv] [--types RE]
Run from the event tree root (tools/die_plan on sys.path).
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "tools/die_plan")
import schema  # noqa: E402
import reset_tree as RT  # noqa: E402


def depths(path, raw, names):
    P = schema.Plan(raw, path)
    out = {}
    for tn in names:
        try:
            T = RT.for_type(P, tn)
            out[tn] = dict(depth=int(T["depth"]),
                           by_depth=dict(sorted(collections.Counter(int(r["depth"]) for r in T["relays"]).items())))
        except Exception as e:  # noqa: BLE001
            out[tn] = dict(error="%s: %s" % (type(e).__name__, e))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("ref")
    ap.add_argument("out")
    ap.add_argument("report")
    ap.add_argument("eq", nargs="?")
    ap.add_argument("--types", default=None)
    a = ap.parse_args()
    raw = json.loads(Path(a.plan).read_text())
    ref = json.loads(Path(a.ref).read_text())
    T, RTy = raw["partition_types"], ref["partition_types"]
    used = {p["type"] for p in raw["partitions"]}
    names = sorted(tn for tn in T if tn in used and not T[tn].get("hard")
                   and (a.types is None or re.search(a.types, tn)))
    refname = {tn: (tn if tn in RTy else tn[:-2] if tn.endswith("_h") and tn[:-2] in RTy else None) for tn in names}
    dn = depths(a.plan, json.loads(json.dumps(raw)), names)
    rnames = sorted({r for r in refname.values() if r})
    dr = depths(a.ref, ref, rnames)
    rows, eq = [], []
    for tn in names:
        r = refname[tn]
        row = dict(type=tn, ref_type=r, now=dn[tn], ref=dr.get(r) if r else None)
        if r is None or "error" in dn[tn] or "error" in (dr.get(r) or {}):
            row["action"] = "skip"
        elif dn[tn]["depth"] < dr[r]["depth"]:
            cur = (T[tn].get("reset") or {}).get("wavefront_min_depth")
            if cur is not None and cur >= dr[r]["depth"]:
                print(f"CONFLICT {tn}: wavefront_min_depth {cur} set but depth {dn[tn]['depth']} < {dr[r]['depth']}")
                sys.exit(3)
            T[tn].setdefault("reset", {})["wavefront_min_depth"] = dr[r]["depth"]
            row["action"] = "pad %d -> %d" % (dn[tn]["depth"], dr[r]["depth"])
            eq.append([tn, "reset.wavefront_min_depth", str(cur), str(dr[r]["depth"]),
                       "reset release depth %d -> %d (pad to published %s depth; HF-1c made the tree shallower)"
                       % (dn[tn]["depth"], dr[r]["depth"], r)])
        else:
            row["action"] = "keep"
        rows.append(row)
    if eq:
        chk = depths(a.out, json.loads(json.dumps(raw)), [e[0] for e in eq])
        for e in eq:
            got = chk[e[0]].get("depth")
            if got != int(e[3]):
                print(f"PAD FAILED {e[0]}: depth {got} != {e[3]}")
                sys.exit(4)
    Path(a.out).write_text(json.dumps(raw, indent=1) + "\n")
    Path(a.report).write_text(json.dumps(dict(plan=a.plan, ref=a.ref, rows=rows, eq=eq), indent=1) + "\n")
    if a.eq:
        with open(a.eq, "w") as f:
            f.write("type\tkey\tfrom\tto\tnote\n")
            for e in eq:
                f.write("\t".join(e) + "\n")
    c = collections.Counter(r["action"].split()[0] for r in rows)
    print("RESET_PAD", dict(c), "padded:", [e[0] + " " + e[4].split(" (")[0] for e in eq])


if __name__ == "__main__":
    main()
