#!/usr/bin/env python3
"""QC-S28-BIND reset reach measure (QC-S28-TAPS definition): for every soft type, every landing_{reader,writer}_start
stage raw_reset and every landing_local_resets raw names a relay of the type's solved wavefront reset tree
(reset_tree.for_type); distance = Manhattan(stage / copy xy_um, relay xy).  Counts refs > LIMIT (405 um) and refs that
name no relay of the solved tree.
  reset_reach.py PLAN [PLAN ...] --json OUT [--limit 405]   (run from the tree root; plans in the plan folder)
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, "tools/die_plan")
import schema  # noqa: E402
import reset_tree as RT  # noqa: E402


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def measure(path, limit):
    raw = json.loads(Path(path).read_text())
    P = schema.Plan(raw, path)
    used = {p["type"] for p in raw["partitions"]}
    out = dict(plan=path, start_far=0, local_far=0, start_missing=0, local_missing=0, start_refs=0, local_refs=0,
               types={})
    for tn in sorted(used):
        t = raw["partition_types"][tn]
        if t.get("hard"):
            continue
        ck = t.get("clock") or {}
        refs = []
        for key in ("landing_reader_start", "landing_writer_start"):
            for bus, br in sorted(((ck.get(key) or {}).get("branches") or {}).items()):
                for i, st in enumerate(br.get("stages", []) if isinstance(br, dict) else []):
                    if isinstance(st.get("raw_reset"), str):
                        refs.append(("start", "%s.%s.%d" % (key, bus, i), st["raw_reset"], st.get("xy_um")))
        for i, lr in enumerate(ck.get("landing_local_resets") or []):
            if isinstance(lr.get("raw"), str):
                refs.append(("local", "landing_local_resets.%d" % i, lr["raw"], lr.get("xy_um")))
        if not refs:
            continue
        try:
            T = RT.for_type(P, tn)
        except Exception as e:  # noqa: BLE001
            out["types"][tn] = dict(error=str(e)[:200])
            continue
        by = {r["q"]: r for r in T["relays"]}
        rows = []
        for kind, tag, q, xy in refs:
            out[kind + "_refs"] += 1
            r = by.get(q)
            if r is None:
                out[kind + "_missing"] += 1
                rows.append([kind, tag, q, None, None])
                continue
            d = round(man(xy, r["xy"]), 1) if xy else None
            if d is not None and d > limit:
                out[kind + "_far"] += 1
            rows.append([kind, tag, q, int(r["depth"]), d])
        bad = [x for x in rows if x[4] is None or x[4] > limit]
        if bad:
            out["types"][tn] = dict(depth=int(T["depth"]), bad=bad)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plans", nargs="+")
    ap.add_argument("--json", required=True)
    ap.add_argument("--limit", type=float, default=405.0)
    a = ap.parse_args()
    res = [measure(p, a.limit) for p in a.plans]
    Path(a.json).write_text(json.dumps(res, indent=1) + "\n")
    for r in res:
        print("RESET_REACH", r["plan"], {k: v for k, v in r.items() if k not in ("plan", "types")},
              "types", len(r["types"]))


if __name__ == "__main__":
    main()
