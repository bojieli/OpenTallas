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
import re
import sys
from pathlib import Path


def rows_of(p: Path):
    op = gzip.open if p.suffix == ".gz" else open
    with op(p, "rt", errors="replace") as f:
        for ln in f:
            if ln.startswith("LAND "):
                yield tuple(int(x) for x in ln.split()[1:])


def read_log(path):
    path = Path(path)
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', errors='replace') as stream:
        return stream.read()


def functional_status(golden, log):
    """Timing rows are evidence only after the independent payload/tag verdict passes."""
    errors = []
    passes = re.findall(r'^PASS xdie_s81:.*$', log, re.M)
    fails = re.findall(r'^FAIL xdie_s81:.*$', log, re.M)
    stats = re.findall(r'^XDIE_STATS (.*)$', log, re.M)
    if len(passes) != 1 or fails:
        errors.append('functional terminal verdict is not one PASS without FAIL')
    if len(stats) != 1:
        errors.append('expected exactly one XDIE_STATS')
    else:
        fields = dict(re.findall(r'(\w+) ([^ ]+)', stats[0]))
        expected = int(golden['beats'])
        for key in ('beats', 'landed'):
            if fields.get(key) != str(expected):
                errors.append(f'{key} != golden beats {expected}')
        for key in ('mismatches', 'late', 'extra', 'faults'):
            value = fields.get(key)
            if value is None or not re.fullmatch('0+', value):
                errors.append(f'{key} not zero')
        if fields.get('live') != '64/64':
            errors.append('not all 64 lanes live')
    return not errors, errors


def evaluate(g, log, win=2):
    functional_ok, functional_errors = functional_status(g, log)
    rows = [tuple(map(int, ln.split()[1:])) for ln in log.splitlines() if ln.startswith("LAND ")]
    early = [r for r in rows if r[6] and r[5] < r[6] - win]
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
    unassigned = 0
    for r in rows:
        cand = [i for (st, i) in starts.get(r[0], []) if st <= r[4]]
        if cand:
            by[cand[-1]].append(r)
        else:
            unassigned += 1

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
    coverage_ok = (len(rows) == int(g["beats"]) and not unassigned and
                   len({r[:5] for r in rows}) == len(rows))
    win_ok = bool(rows) and not early and not late
    inv_ok = bool(users) and all(inv.values()) and all(x["E_sched"] is not None for v in users.values() for x in v.values())
    out = dict(beats=len(rows), win=win, early=len(early), late=len(late), land_minus_deadline=dict(sorted(hist.items())),
               users=users, user_sched_equal_first=inv, win_pass=win_ok, inv_pass=inv_ok, dl_model=g.get("dl_model"), functional_pass=functional_ok, functional_errors=functional_errors,
               coverage_pass=coverage_ok, unassigned=unassigned,
               qualified=functional_ok and coverage_ok and win_ok and inv_ok)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("golden")
    ap.add_argument("run")
    ap.add_argument("--win", type=int, default=2)
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    g = json.loads((Path(a.golden) / "golden.json").read_text())
    out = evaluate(g, read_log(a.run), a.win)
    print(f"{'FUNCTIONAL_PASS' if out['functional_pass'] else 'FUNCTIONAL_FAIL'} {out['functional_errors']}")
    print(f"{'COVERAGE_PASS' if out['coverage_pass'] else 'COVERAGE_FAIL'} expected {g['beats']} observed {out['beats']} unassigned {out['unassigned']}")
    print(f"{'WIN_PASS' if out['win_pass'] else 'WIN_FAIL'} beats {out['beats']} early {out['early']} late {out['late']} "
          f"land-deadline {out['land_minus_deadline']}")
    print(f"{'INV_PASS' if out['inv_pass'] else 'INV_FAIL'} users {len(out['users'])} E_sched equal to user {next(iter(out['users']), None)}: "
          f"{sum(out['user_sched_equal_first'].values())}/{len(out['user_sched_equal_first'])}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1))
    sys.exit(0 if out["qualified"] else 1)


if __name__ == "__main__":
    main()
