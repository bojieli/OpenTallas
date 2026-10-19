#!/usr/bin/env python3
"""XDIE-S81-2 fixed-latency check (10-19): the bench verdict only bounds a landing from above (compiled deadline), so a
mutant that SHORTENS the fixed crossing latency (OT_S81_LAND_MUT_SEL: landing reads its slot one cycle early) passes it.
Checks every observed beat lands at least LFIX cycles after its issue and the global minimum equals LFIX.
LAND lines do not identify idle-stream boundaries; this check does not prove an exact first-beat latency
for every idle stream or equality between users.  Reads LAND lines
(LAND inst src dst k issue land deadline) of a run log (.gz ok); prints LFIX_PASS / LFIX_FAIL.
  python3 tools/xdie_s81_2/lfix_check.py <run.log[.gz]> --lfix 563"""
import argparse, gzip, collections

ap = argparse.ArgumentParser(); ap.add_argument("log"); ap.add_argument("--lfix", type=int, required=True)
a = ap.parse_args()
op = gzip.open if a.log.endswith(".gz") else open
lat = collections.Counter(); n = 0
with op(a.log, "rt") as f:
    for ln in f:
        if ln.startswith("LAND "):
            x = ln.split(); lat[int(x[6]) - int(x[5])] += 1; n += 1
mn = min(lat) if lat else None
early = sum(c for l, c in lat.items() if l < a.lfix)
ok = n > 0 and mn == a.lfix and early == 0
print(f"{'LFIX_PASS' if ok else 'LFIX_FAIL'} beats {n} min_latency {mn} lfix {a.lfix} early {early}")
