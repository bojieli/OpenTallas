#!/usr/bin/env python3
"""Collect the HA2 all-reduce campaign logs (tb_ha2_ar runs, see results/rtl/hbm_accel_ha2_ar_20261004/REPLAY.md).

    python3 tools/ha2_ar_campaign.py RUNSDIR --out measured.json

Per config and PHY setting: every seed's issue -> last-commit latency (earliest issue on any die to the last result
committed at the hub of the slowest die), mismatch/fault/credit-stall counts; worst over seeds is the figure of record.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

DONE = re.compile(r"HA2DONE seed=(\d+) lat_ns=([\d.]+) lat_cyc_1p2=([\d.]+) worst_die=(\d+) mismatches=(\d+) "
                  r"faults=(\d+) credit_stall_cycles=(\d+)")
PHY = re.compile(r"HA2PHY phy_l=(\d+) phy_g=(\d+) js=(\d+)")


def collect(runs: Path) -> dict:
    out = {}
    for f in sorted(runs.glob("*_s*.log")):
        m = re.match(r"(.+)_(central|phy\d+)_s(\d+)\.log$", f.name)
        if not m:
            continue
        cfg, setting, seed = m.group(1), m.group(2), int(m.group(3))
        txt = f.read_text(errors="replace")
        d = DONE.search(txt)
        p = PHY.search(txt)
        row = dict(seed=seed, complete=bool(d), timeout="HA2TIMEOUT" in txt)
        if d:
            row.update(lat_ns=float(d.group(2)), lat_cyc_1p2=float(d.group(3)), worst_die=int(d.group(4)),
                       mismatches=int(d.group(5)), faults=int(d.group(6)), credit_stall_cycles=int(d.group(7)))
        if p:
            row.update(phy_l=int(p.group(1)), phy_g=int(p.group(2)), js=int(p.group(3)))
        out.setdefault(cfg, {}).setdefault(setting, []).append(row)
    summ = {}
    for cfg, settings in out.items():
        for setting, rows in settings.items():
            rows.sort(key=lambda r: r["seed"])
            ok = [r for r in rows if r["complete"]]
            lat = [r["lat_ns"] for r in ok]
            key = cfg if setting == "central" else f"{cfg}_{setting}"
            summ[key] = dict(seeds=len(rows), complete=len(ok),
                             exact=all(r["mismatches"] == 0 for r in ok) and len(ok) == len(rows),
                             faults=sum(r["faults"] for r in ok),
                             credit_stall_cycles=sum(r["credit_stall_cycles"] for r in ok),
                             lat_ns_worst=max(lat) if lat else None, lat_ns_best=min(lat) if lat else None,
                             lat_cyc_1p2_worst=max(r["lat_cyc_1p2"] for r in ok) if ok else None,
                             phy=(ok[0].get("phy_l"), ok[0].get("phy_g"), ok[0].get("js")) if ok else None,
                             per_seed=rows)
    return summ


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", type=Path)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    s = collect(a.runs)
    if a.out:
        a.out.write_text(json.dumps(s, indent=1) + "\n")
    for k, v in s.items():
        print(k, {x: v[x] for x in ("seeds", "complete", "exact", "faults", "credit_stall_cycles", "lat_ns_worst",
                                     "lat_ns_best", "phy")})
