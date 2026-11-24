#!/usr/bin/env python3
"""Group violating endpoints of an OpenSTA `report_checks -format summary` file by
start class -> end class (BENCH-KEEP from QC-HC1-CLKENTRY / QC-SLECTL-RESYN sle_ctl census).

usage: sta_ep_census.py SUMFILE [TH_PS]   (TH default -42.0)
Pair with sta_ep_census.tcl (writes SUMFILE from a CTS/route DB) and sta_ep_census.sh (docker wrapper).
"""
import collections
import re
import sys


def cls(n):
    n = n.replace("\\", "")
    if not n.startswith("u_bound."):
        return "PORT:" + re.sub(r"\[.*", "", n)
    n = n[len("u_bound."):]
    first = re.split(r"[./]", n)[0]
    first = re.sub(r"_\d+$", "", first)          # drop bit/copy index
    first = re.sub(r"(\D)\d+$", r"\1#", first)   # u_pd7 -> u_pd# (after the _N index drop above: rrl_833 -> rrl)
    if first.startswith("u_u_rp"):
        m = re.match(r"u_u_rp\.(g_wgrp|u_rl|[a-z_]+)", n)
        first = "u_u_rp." + (m.group(1) if m else "?")
    return first


def parse(lines):
    rows = []
    for ln in lines:
        t = [x for x in ln.split() if not x.startswith("(")]
        if len(t) >= 3 and re.fullmatch(r"-?\d+\.\d+", t[-1]) and not ln.startswith(("Startpoint", "-")):
            rows.append((float(t[-1]), re.sub(r"/[A-Z]+$", "", t[0]), re.sub(r"/[A-Z]+$", "", t[1])))
    return rows


def census(rows, th=-42.0):
    neg = [r for r in rows if r[0] < 0]
    g = collections.defaultdict(list)
    for sl, s, e in neg:
        g[(cls(s), cls(e))].append(sl)
    out = [f"endpoints listed {len(rows)} violating {len(neg)} below {th}: {sum(1 for r in neg if r[0] < th)}",
           f"{'n':>5} {'<th':>4} {'worst':>8}  start_class -> end_class"]
    for (a, b), v in sorted(g.items(), key=lambda kv: min(kv[1])):
        out.append(f"{len(v):5d} {sum(1 for x in v if x < th):4d} {min(v):8.2f}  {a} -> {b}")
    return out


def main(argv):
    th = float(argv[2]) if len(argv) > 2 else -42.0
    with open(argv[1]) as f:
        print("\n".join(census(parse(f), th)))


if __name__ == "__main__":
    main(sys.argv)
