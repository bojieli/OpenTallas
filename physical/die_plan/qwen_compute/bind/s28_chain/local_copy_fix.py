#!/usr/bin/env python3
"""QC-S28-BIND (c): local reset copy depth law from the strict bind's own measurement (QC-S28-TAPS MEASURED_SHIFT rule,
made generic).  clock_landings.landing_local_resets: depth(raw) + 1 must equal the consumer's reset depth; the strict
bind reports the first mismatch of each type as
    EMIT T: T: landing_local_resets.NAME: consumer C reset R depth D != copy depth K (raw Q): release edge would move
For each such type the measured shift s = D - K is applied to EVERY local copy of the type whose raw has the failing
depth K - 1 (same cohort): raw -> the non-ported relay of depth K - 1 + s nearest the copy xy_um.  The anchor
(clock.reset_tree_anchor) is re-recorded.  Release edges do not move (that is what the law keeps); EQ row per copy.
  local_copy_fix.py PLAN_IN BIND_REPORT.json|LOG [...] --out PLAN_OUT --report R.json --eq EQ.tsv   (tree root, plan folder)
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "tools/die_plan")
import schema  # noqa: E402
import reset_tree as RT  # noqa: E402
import reset_anchor as RA  # noqa: E402

PAT = re.compile(r"EMIT (\S+): \S+: landing_local_resets\.(\w+): consumer (\S+) reset (\S+) depth (\d+) != copy depth (\d+)"
                 r" \(raw (\S+)\)")


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("logs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--eq", required=True)
    a = ap.parse_args()
    hits = {}
    for lg in a.logs:
        # bind_report.json "errors" holds every gap (the log prints only the first 30)
        txt = "\n".join(str(x) for x in json.loads(Path(lg).read_text())["errors"]) if lg.endswith(".json") \
            else Path(lg).read_text()
        for m in PAT.finditer(txt):
            tn, name, cons, rnet, D, K, q = m.groups()
            hits.setdefault(tn, dict(name=name, consumer=cons, reset=rnet, D=int(D), K=int(K), raw=q))
    raw = json.loads(Path(a.plan).read_text())
    P = schema.Plan(json.loads(json.dumps(raw)), a.plan)
    rows, eq = {}, []
    for tn, h in sorted(hits.items()):
        t = raw["partition_types"][tn]
        ck = t["clock"]
        T = RT.for_type(P, tn)
        port = RA.ported(T)
        by = {r["q"]: r for r in T["relays"]}
        cand = {}
        for r in T["relays"]:
            if RA.NAME.match(r["q"]) and r["q"] not in port:
                cand.setdefault(int(r["depth"]), []).append(r)
        s = h["D"] - h["K"]
        k0 = h["K"] - 1
        want = k0 + s
        if not cand.get(want):
            print(f"HELD {tn}: no non-ported relay of depth {want}")
            sys.exit(3)
        rows[tn] = dict(measured=h, shift=s, copies=[])
        for e in ck.get("landing_local_resets") or []:
            cur = by.get(e["raw"])
            if cur is None or int(cur["depth"]) != k0:
                continue
            b = min(cand[want], key=lambda r: (man(r["xy"], e["xy_um"]), r["q"]))
            rows[tn]["copies"].append(dict(name=e["name"], raw_before=e["raw"], raw_after=b["q"], depth=[k0, want],
                                           copy_to_relay_um=round(man(b["xy"], e["xy_um"]), 1)))
            eq.append([tn, "landing_local_resets.%s raw" % e["name"], "%s@%d" % (e["raw"], k0), "%s@%d" % (b["q"], want),
                       str(s), "copy depth %d -> %d = consumer reset depth %d (strict-bind measured); copy->relay %.1f um"
                       % (k0 + 1, want + 1, h["D"], man(b["xy"], e["xy_um"]))])
            e["raw"] = b["q"]
        if ck.get(RA.KEY):
            ck[RA.KEY] = RA.record(t, T, ".", float(ck[RA.KEY].get("tol_um", 405.0)))
    Path(a.out).write_text(json.dumps(raw, indent=1) + "\n")
    Path(a.report).write_text(json.dumps(rows, indent=1) + "\n")
    with open(a.eq, "w") as f:
        f.write("type\tkind\tbefore\tafter\treset_release_cycles\tnote\n")
        for x in eq:
            f.write("\t".join(x) + "\n")
    print("LOCAL_COPY_FIX types", len(rows), "copies", len(eq), {t: r["shift"] for t, r in rows.items()})


if __name__ == "__main__":
    main()
