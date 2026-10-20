#!/usr/bin/env python3
"""HBM-COLLFUSE2 (10-20): validate the census critical-path `bind` metadata (150304f7f) before any fusion is priced.

For every S2 schedule the census runs (DS AR + Qwen, every reprice job), this wrapper also runs the PRE-bind
timing.schedule body (the `def schedule` source of a reference timing.py, default commit 713c35b7d, compiled into the
LIVE timing module namespace so every runtime global the reprice jobs patch is shared) on the same records with the
same (measured) cost function, and checks
  1. start / end / disp of every executed record and total_cycles are IDENTICAL (bind is metadata only);
  2. sum(critical cycles of records) + sum(named gaps) == total_cycles of the segment, and the `unbound` gap is 0;
  3. every record on the walk is visited forward in time (no negative step).
Writes one JSON line per segment to <out>_bindval/<pid>.jsonl and a summary <out>_bindval/summary.json.

usage: PYTHONPATH=tools python3 -m hgi_sim.toksim_bind_validate_1020 REF_TIMING.py <census args...>
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from pathlib import Path


def _ref_schedule(ref_path, T):
    src = Path(ref_path).read_text()
    m = re.search(r"^def schedule\(.*?(?=^def )", src, re.S | re.M)
    if not m:
        raise SystemExit("no def schedule in " + ref_path)
    ns = dict(T.__dict__)
    exec(compile(m.group(0), ref_path + ":schedule", "exec"), ns)
    return ns["schedule"]


def main():
    ref = sys.argv[1]
    del sys.argv[1]
    from hgi_sim import timing as T
    from hgi_sim import toksim_hbm_census_1019 as C
    ref_sched = _ref_schedule(ref, T)
    if os.environ.get("CENSUS_ONLY"):
        C.ONLY = os.environ["CENSUS_ONLY"]
    argv = sys.argv[1:]
    out = Path(argv[argv.index("--out") + 1])
    vdir = out.parent / (out.stem + "_bindval")
    vdir.mkdir(parents=True, exist_ok=True)
    live = C.schedule

    def schedule(recs, pos, mode="S2", token=0, cost_fn=T.cost, wires=True):
        s = live(recs, pos, mode, token, cost_fn, wires)
        if C.CUR["job"] is None or mode != "S2":
            return s
        keep = (dict(C.LAST), dict(C.EXTRAP))

        def cf(r, dyn, L):                       # same cost as the live wrapper, no census logging
            c, g, how = cost_fn(r, dyn, L)
            mc = C.measured_cost(r, L, c) if C.MEAS else None
            return (mc if mc is not None else c), g, how
        s0 = ref_sched(recs, pos, mode, token, cf, wires)
        C.LAST.clear(); C.LAST.update(keep[0]); C.EXTRAP.clear(); C.EXTRAP.update(keep[1])
        n = len(s["ex"])
        dif = {k: sum(1 for a, b in zip(s[k], s0[k]) if a != b) for k in ("start", "end", "disp")}
        crit, gaps = C.crit_walk(s)
        tot = s["total_cycles"]
        acc = sum(crit.values()) + sum(gaps.values())
        rec = dict(job=C.CUR["job"], n=n, total=tot, total_ref=s0["total_cycles"], diff=dif,
                   same_len=len(s0["ex"]) == n, ex_same=[tuple(x[:2]) for x in s["ex"]] == [tuple(x[:2]) for x in s0["ex"]],
                   crit_sum=round(sum(crit.values()), 3), gaps={k: round(v, 3) for k, v in gaps.items()},
                   attributed=round(acc, 3), residual=round(tot - acc, 6),
                   neg_crit=sum(1 for v in crit.values() if v < -1e-9),
                   neg_detail=[dict(i=i, crit=round(v, 3), tag=recs[s["ex"][i][0]].tag, unit=recs[s["ex"][i][0]].unit,
                                    op=recs[s["ex"][i][0]].op, start=round(s["start"][i], 3), end=round(s["end"][i], 3),
                                    cost=str(s["costs"][i])[:80] if s.get("costs") is not None else None,
                                    bind=[list(b) if b else None for b in (s["bind"][i] or [])])
                               for i, v in crit.items() if v < -1e-9])
        with open(vdir / f"{os.getpid()}.jsonl", "a") as f:
            f.write(json.dumps(rec) + "\n")
        return s
    C.schedule = schedule
    C.T.schedule = schedule
    rc = C.main()
    rows = [json.loads(l) for p in glob.glob(str(vdir / "*.jsonl")) for l in open(p)]
    bad = [r for r in rows if any(r["diff"].values()) or r["total"] != r["total_ref"] or not r["same_len"]
           or not r["ex_same"] or abs(r["residual"]) > 1e-6 or r["gaps"].get("unbound", 0) > 1e-6 or r["neg_crit"]]
    per_job = {}
    for r in rows:
        j = per_job.setdefault(r["job"], dict(segments=0, total=0.0, crit=0.0, gaps={}))
        j["segments"] += 1
        j["total"] += r["total"]
        j["crit"] += r["crit_sum"]
        for k, v in r["gaps"].items():
            j["gaps"][k] = round(j["gaps"].get(k, 0.0) + v, 3)
    summ = dict(ref=ref, segments=len(rows), bad=len(bad), first_bad=bad[:5],
                verdict="PASS" if rows and not bad else "FAIL", per_job={k: dict(v, total=round(v["total"], 3), crit=round(v["crit"], 3)) for k, v in per_job.items()})
    (vdir / "summary.json").write_text(json.dumps(summ, indent=1) + "\n")
    print("BINDVAL", summ["verdict"], "segments", len(rows), "bad", len(bad))
    return rc if summ["verdict"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
