#!/usr/bin/env python3
"""raw_origin_sync.py -- take the origin reset node the BIND emits for each landing_raw_branches consumer (KV-SINKBINS 11-25).

After a tap re-solve the plan names the old origin reset node (rst_n_t1) in the final stage `original` of landing_raw_branches
while the bind picks the consumer default itself (clock_landings count_origin / START raw) and refuses with
  `<type>: <role> reset phase/equation differs: <emitted> != <planned>`  (landing_raw_branches.RawBranches.validate).
retap and landing_remap cannot predict that node (no new node at the old site; the bind takes the first count-aligned raw), so this
tool reads the bind's own answer from bind_report.json and writes it into the plan:

  raw_origin_sync.py PLAN BIND_REPORT.json OUT [--report R.json] [--types a,b]

For each such error of a selected type every landing_raw_branches branch of that type whose last stage original is the planned node
gets the emitted node (all branches of a type end on the same reset node; the next role would fail identically).  Errors that
match no branch are returned unfixed (exit 1).  Run bind -> sync -> bind until no sync is needed."""
import argparse
import json
import re
import sys

ERR = re.compile(r"^EMIT (\S+?): (?:\S+: )?(\S+) reset phase/equation differs: (\w+) != (\w+)\s*$")


def parse_errors(errors):
    """[(type, role, emitted, planned)] of the phase/equation errors in a bind report errors list."""
    out = []
    for e in errors or []:
        m = ERR.match(str(e).strip())
        if m:
            out.append((m.group(1), m.group(2), m.group(3), m.group(4)))
    return out


def sync(plan, errors, types=None):
    """rewrite plan (in place) -> {type: {"changed": n, "pairs": [[planned, emitted]], "unfixed": [...]}}"""
    rep = {}
    for tn, role, emitted, planned in parse_errors(errors):
        if types and tn not in types:
            continue
        t = plan["partition_types"].get(tn)
        r = rep.setdefault(tn, dict(changed=0, pairs=[], unfixed=[]))
        if t is None:
            r["unfixed"].append(f"{role}: type not in plan")
            continue
        n = 0
        for b in (t.get("clock") or {}).get("landing_raw_branches") or []:
            st = b.get("stages") or []
            if st and st[-1].get("original") == planned:
                st[-1]["original"] = emitted
                n += 1
        if n == 0:
            r["unfixed"].append(f"{role}: no branch ends on {planned}")
        if [planned, emitted] not in r["pairs"]:
            r["pairs"].append([planned, emitted])
        r["changed"] += n
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan"); ap.add_argument("bind_report"); ap.add_argument("out")
    ap.add_argument("--report"); ap.add_argument("--types", default="")
    a = ap.parse_args(argv)
    plan = json.load(open(a.plan))
    errs = json.load(open(a.bind_report)).get("errors") or []
    rep = sync(plan, errs, set(filter(None, a.types.split(","))) or None)
    json.dump(plan, open(a.out, "w"), indent=1)
    open(a.out, "a").write("\n")
    if a.report:
        json.dump(rep, open(a.report, "w"), indent=1)
    unfixed = {t: v["unfixed"] for t, v in rep.items() if v["unfixed"]}
    print("RAW_ORIGIN_SYNC types", len(rep), "branches", sum(v["changed"] for v in rep.values()), "unfixed", unfixed)
    return 1 if unfixed else 0


if __name__ == "__main__":
    sys.exit(main())
