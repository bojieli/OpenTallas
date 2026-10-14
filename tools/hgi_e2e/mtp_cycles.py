#!/usr/bin/env python3
"""Measured cycles of the DS MTP e2e job (tb_hgi_e2e -GMTP=2, vehicle ds_mtp_spec) against the MTP.VERIFY price.

The bench prints one `E2E KCPL <n> cyc <c>` line per completed kernel launch (c = cycles since the doorbell).  The
simulator's launches.json (ds_mtp_kernels sim --out) names every launch in the same order (kind, L', token, pos) with
its S2 price-model cycles.  This tool pairs the two and reports

  * per kind: launches, measured cycles (sum, per launch), simulator cycles, ratio;
  * the L0 verify: every L0 column = swapin + embed + L0 body + swapout around a `layer` launch with L' = 0; the five
    verify columns of the first step (the prefill column is reported apart) against the price
    (results/rtl/tput_map_1011/mtp_verify/record.json price.cycles, 63,800; limit 1.10x);
  * the whole job, doorbell -> last completion.

A launch's measured cycles = its KCPL time minus the previous launch's (the controller issues launches back to back:
launch overhead of the controller is inside the number, as it is on the die).

    python3 tools/hgi_e2e/mtp_cycles.py RUN_LOG LAUNCHES_JSON [--price 63800] [--out report.json]

With the bench run under E2E_RECLOG=1 the log also carries one `E2E REC <k> <tag> unit <u> disp <c> ret <c> real <0|1>
s2 <disp> <end>` line per retired record: the report then adds, per unit, the records' measured residence (retire -
dispatch) against the simulator's (S2 end - S2 dispatch) and the ten slowest records by ratio (real units only; a
stub retires after its S2 cost by construction).  A run cut short is reported on the part it reached.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

LIMIT = 1.10


def kcpl(run_log):
    out = []
    for ln in Path(run_log).read_text(errors="replace").splitlines():
        m = re.match(r"E2E KCPL (\d+) cyc (\d+) token (\d+) status (\d+)", ln)
        if m:
            n, c, tok, st = map(int, m.groups())
            assert n == len(out), f"KCPL lines out of order at {n}"
            out.append(dict(cyc=c, token=tok, status=st))
    return out


UNITS = ["CTL", "SM", "SU", "SFU", "FUSED", "ATT", "COLL", "ARGMAX", "DMA", "IDX", "HC", "SIMT"]


def records(run_log):
    """the E2E REC lines: per unit measured residence vs the simulator's, and the slowest real records"""
    rec = []
    for ln in Path(run_log).read_text(errors="replace").splitlines():
        m = re.match(r"E2E REC (\d+) (\S+) unit (\d+) disp (-?\d+) ret (-?\d+) real (\d) s2 ([\d.]+) ([\d.]+)", ln)
        if m:
            k, tag, u, d, r, real, sd, se = m.groups()
            rec.append(dict(k=int(k), tag=tag, unit=UNITS[int(u)], measured=int(r) - int(d), sim=round(float(se) - float(sd), 1),
                            real=int(real)))
    if not rec:
        return None
    by = {}
    for x in rec:
        d = by.setdefault(x["unit"] + ("" if x["real"] else " (stub)"), dict(records=0, measured=0, sim=0.0))
        d["records"] += 1
        d["measured"] += x["measured"]
        d["sim"] += x["sim"]
    for d in by.values():
        d["sim"] = round(d["sim"], 1)
        d["ratio"] = round(d["measured"] / d["sim"], 3) if d["sim"] else None
    slow = sorted((x for x in rec if x["real"] and x["sim"] > 0), key=lambda x: -(x["measured"] / x["sim"]))[:10]
    return dict(retired=len(rec), by_unit=by, slowest=slow)


def report(run_log, launches, price):
    k = kcpl(run_log)
    L = json.loads(Path(launches).read_text())
    n = min(len(k), len(L))
    per, prev = [], 0
    for i in range(n):
        per.append(dict(i=i, kind=L[i]["kind"], Lp=L[i]["Lp"], token=L[i]["token"], pos=L[i]["pos"],
                        measured=k[i]["cyc"] - prev, sim=L[i]["s2_cycles"], status=k[i]["status"]))
        prev = k[i]["cyc"]
    kinds = {}
    for x in per:
        d = kinds.setdefault(x["kind"], dict(launches=0, measured=0, sim=0.0, worst=0))
        d["launches"] += 1
        d["measured"] += x["measured"]
        d["sim"] += x["sim"]
        d["worst"] = max(d["worst"], x["measured"])
    for d in kinds.values():
        d["measured_per_launch"] = round(d["measured"] / d["launches"], 1)
        d["sim_per_launch"] = round(d["sim"] / d["launches"], 1)
        d["ratio_vs_sim"] = round(d["measured"] / d["sim"], 3) if d["sim"] else None
        d["sim"] = round(d["sim"], 1)
    cols = []
    for i, x in enumerate(per):
        if x["kind"] == "layer" and x["Lp"] == 0:
            grp = per[max(i - 2, 0):i + 2]
            if [g["kind"] for g in grp] != ["swapin", "embed", "layer", "swapout"]:
                cols.append(dict(layer_launch=i, pos=x["pos"], complete=False, kinds=[g["kind"] for g in grp]))
                continue
            cols.append(dict(layer_launch=i, pos=x["pos"], complete=True,
                             measured={g["kind"]: g["measured"] for g in grp}, measured_total=sum(g["measured"] for g in grp),
                             sim_total=round(sum(g["sim"] for g in grp), 1)))
    full = [c for c in cols if c["complete"]]
    # the job is prefill p0 (one L0 column) then the verify step's columns: the price is five verify columns
    verify = full[1:6]
    v = None
    if len(verify) == 5:
        tot = sum(c["measured_total"] for c in verify)
        v = dict(columns=5, measured_cycles=tot, price_cycles=price, limit_cycles=round(price * LIMIT), ratio=round(tot / price, 4),
                 within_limit=bool(tot <= price * LIMIT), sim_cycles=round(sum(c["sim_total"] for c in verify), 1),
                 per_column_mean={kk: round(sum(c["measured"][kk] for c in verify) / 5, 1)
                                  for kk in ("swapin", "embed", "layer", "swapout")})
    return dict(schema="opentallas.hgi_e2e.mtp_cycles.v1", run_log=str(run_log), launches_json=str(launches),
                kcpl=len(k), launches=len(L), paired=n, complete=bool(len(k) == len(L)),
                bad_status=[x["i"] for x in per if x["status"]][:16],
                job_cycles=k[-1]["cyc"] if k else None, sim_job_cycles=round(sum(x["s2_cycles"] for x in L), 1),
                job_ratio_vs_sim=round(k[-1]["cyc"] / sum(x["s2_cycles"] for x in L[:n]), 3) if k else None,
                by_kind=kinds, l0_columns=cols, l0_verify=v, records=records(run_log))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_log")
    ap.add_argument("launches")
    ap.add_argument("--price", type=float, default=63800.0)
    ap.add_argument("--out")
    a = ap.parse_args()
    r = report(a.run_log, a.launches, a.price)
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1) + "\n")
    print(f"paired {r['paired']} of {r['launches']} launches (KCPL {r['kcpl']}); job {r['job_cycles']} cycles, simulator "
          f"{r['sim_job_cycles']} ({r['job_ratio_vs_sim']}x on the paired part)")
    for kk, d in sorted(r["by_kind"].items(), key=lambda kv: -kv[1]["measured"]):
        print(f"  {kk:8s} {d['launches']:4d} launches  measured {d['measured']:9d} ({d['measured_per_launch']:9.1f} each, worst "
              f"{d['worst']})  sim {d['sim']:10.1f} ({d['sim_per_launch']:8.1f})  ratio {d['ratio_vs_sim']}")
    if r["records"]:
        print(f"records retired {r['records']['retired']}; residence (retire - dispatch) by unit, measured vs simulator:")
        for u, d in sorted(r["records"]["by_unit"].items(), key=lambda kv: -kv[1]["measured"]):
            print(f"  {u:14s} {d['records']:5d} records  measured {d['measured']:9d}  sim {d['sim']:10.1f}  ratio {d['ratio']}")
        for x in r["records"]["slowest"][:5]:
            print(f"  slow: k {x['k']} {x['tag'][:40]} {x['unit']} measured {x['measured']} sim {x['sim']}")
    v = r["l0_verify"]
    if v:
        print(f"L0 verify, 5 columns: measured {v['measured_cycles']} vs price {v['price_cycles']:.0f} = {v['ratio']} "
              f"(limit {v['limit_cycles']}: {'WITHIN' if v['within_limit'] else 'OVER'}); per column {v['per_column_mean']}")
    else:
        print("L0 verify: fewer than five complete verify columns in the run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
