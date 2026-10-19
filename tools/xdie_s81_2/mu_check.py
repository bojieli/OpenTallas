#!/usr/bin/env python3
"""XDIE-S81-MU (10-19): two-sided landing window + per-user crossing invariance for a tb_xdie_s81_2 run.

    python3 tools/xdie_s81_2/mu_check.py <golden dir> <run.log[.gz]> [--win 2] [--json out.json]

Golden = gen_golden.py --dl-model fluid (phase-free compiler crossing model).  Checks:
  WIN   every landed beat lies in [deadline - WIN, deadline] (the bench checks only the upper bound; an early-landing
        mutant such as OT_S81_LAND_MUT_SEL lands 2 cycles before the window floor and fails here)
  INV   per user, the COMPILED crossing span of every collective (E_sched = last deadline - first issue; AR = RS + AG)
        is identical for every user and equal to the first user's: the static schedule is the same for every user
        whatever the lane slot phase.  E_meas (last landing - first issue) is reported beside it; the difference is
        the phase slack (0..WIN), never a schedule input.
Prints WIN_PASS / WIN_FAIL and INV_PASS / INV_FAIL lines; exit 0 only if both pass.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import sys
from pathlib import Path


def rows_of(p: Path):
    op = gzip.open if p.suffix == ".gz" else open
    with op(p, "rt", errors="replace") as f:
        for ln in f:
            if ln.startswith("LAND "):
                yield tuple(int(x) for x in ln.split()[1:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("golden")
    ap.add_argument("run")
    ap.add_argument("--win", type=int, default=2)
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    g = json.loads((Path(a.golden) / "golden.json").read_text())
    rows = list(rows_of(Path(a.run)))
    early = [r for r in rows if r[6] and r[5] < r[6] - a.win]
    late = [r for r in rows if r[6] and r[5] > r[6]]
    hist = collections.Counter(r[5] - r[6] for r in rows if r[6])
    # the LAND inst field is 8 bits (beat [1095:1088]) and wraps beyond 256 instances: a row belongs to the instance with
    # the same inst mod 256 and the latest start <= its issue cycle
    starts = collections.defaultdict(list)
    for ins in g["instances"]:
        starts[ins["inst"] & 0xFF].append((ins["start"], ins["inst"]))
        if ins["kind"] == "AR":
            starts[ins["inst_ag"] & 0xFF].append((ins["ag_start"], ins["inst_ag"]))
    for v in starts.values():
        v.sort()
    by = collections.defaultdict(list)
    for r in rows:
        cand = [i for (st, i) in starts.get(r[0], []) if st <= r[4]]
        if cand:
            by[cand[-1]].append(r)

    def span(inst, key):  # key 6 = deadline, 5 = landing
        v = by.get(inst, [])
        if not v:
            return None, None
        return min(x[4] for x in v), max(x[key] for x in v)

    users = collections.OrderedDict()
    for ins in g["instances"]:
        u = ins.get("user")
        if u is None:
            u = "su"
        ents = [ins["inst"]] + ([ins["inst_ag"]] if ins["kind"] == "AR" else [])
        es = em = 0
        ok = True
        for i in ents:
            f0, ld = span(i, 6)
            _, ll = span(i, 5)
            if f0 is None:
                ok = False
                break
            es += ld - f0
            em += ll - f0
        uu = users.setdefault(str(u), {})
        nm = ins["name"] if ins.get("rep", 0) == 0 or u != "su" else f"{ins['name']}#r{ins['rep']}"
        uu[nm] = dict(E_sched=es if ok else None, E_meas=em if ok else None)
    first = next(iter(users.values()), {})
    inv = {u: all(v.get(n, {}).get("E_sched") == first[n]["E_sched"] for n in first if n in v) for u, v in users.items()}
    win_ok = bool(rows) and not early and not late
    inv_ok = bool(users) and all(inv.values()) and all(x["E_sched"] is not None for v in users.values() for x in v.values())
    out = dict(beats=len(rows), win=a.win, early=len(early), late=len(late), land_minus_deadline=dict(sorted(hist.items())),
               users=users, user_sched_equal_first=inv, win_pass=win_ok, inv_pass=inv_ok, dl_model=g.get("dl_model"))
    print(f"{'WIN_PASS' if win_ok else 'WIN_FAIL'} beats {len(rows)} early {len(early)} late {len(late)} "
          f"land-deadline {dict(sorted(hist.items()))}")
    print(f"{'INV_PASS' if inv_ok else 'INV_FAIL'} users {len(users)} E_sched equal to user {next(iter(users), None)}: "
          f"{sum(inv.values())}/{len(inv)}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1))
    sys.exit(0 if (win_ok and inv_ok) else 1)


if __name__ == "__main__":
    main()
