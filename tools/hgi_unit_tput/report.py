#!/usr/bin/env python3
"""Unit throughput bench log -> report.json in the hgi-e2e report schema (hgi-1010/g), so hgi_sim.e2e_calibration's
service() / ratios() read it: per record {unit, op (HGI.D_OPS index), disp, ret, cost, real}.  Every record is
dispatched at cycle 0 (all are queued in the CP's unit queue at the start), so the per-record service is
ret - max(0, previous ret) = the unit's back-to-back service time.

    python3 tools/hgi_unit_tput/report.py --unit FUSED --log m0.log [--mutant-log m1.log ...] --meta JSON --out report.json
Bench log lines:  TPUT k op <op> ... issue <c> ret <c> (cost <c> | cost_milli <c x 1000>)   and   EXACT k mismatch <m>
"""
import argparse
import json
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import hbm_generic_iface as HGI  # noqa: E402

PASS = re.compile(r"PASS HGI_\w+_TPUT|HGI_\w+_TPUT PASS")


def parse(text):
    recs, exact = {}, {}
    for ln in text.splitlines():
        m = re.match(r"TPUT (\d+) op (\d+)(.*?) issue (\d+) ret (-?\d+) (cost|cost_milli) (\d+)", ln)
        if m:
            c = int(m.group(7)) / (1000 if m.group(6) == "cost_milli" else 1)
            recs[int(m.group(1))] = dict(op=int(m.group(2)), issue=int(m.group(4)), ret=int(m.group(5)), cost=c)
        m = re.match(r"EXACT (\d+) mismatch (\d+)", ln)
        if m:
            exact[int(m.group(1))] = int(m.group(2))
    return recs, exact


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unit", required=True)
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--mutant-log", type=Path, nargs="*", default=[])
    ap.add_argument("--tags", type=Path, help="one tag a line, record order")
    ap.add_argument("--meta", help="JSON object merged into the report (source commit, bench, shapes, scaling)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    text = a.log.read_text()
    recs, exact = parse(text)
    tags = a.tags.read_text().splitlines() if a.tags else []
    ok = bool(PASS.search(text))
    rows, prev, busy, cost = [], 0, 0, 0.0
    for k in sorted(recs):
        r = recs[k]
        st = max(0, prev)
        rows.append(dict(k=k, unit=a.unit, op=r["op"], tag=tags[k] if k < len(tags) else HGI.D_OPS[a.unit][r["op"]],
                         real=1, disp=0, issue=r["issue"], ret=r["ret"], service=r["ret"] - st, cost=r["cost"],
                         ratio=round((r["ret"] - st) / r["cost"], 3), mismatch=exact.get(k, -1)))
        busy += r["ret"] - st
        cost += r["cost"]
        prev = r["ret"]
    per_op = {}
    for x in rows:
        o = per_op.setdefault(f"{a.unit}.{HGI.D_OPS[a.unit][x['op']]}", dict(records=0, rtl_service=0, sim_cost=0.0))
        o["records"] += 1
        o["rtl_service"] += x["service"]
        o["sim_cost"] += x["cost"]
    for o in per_op.values():
        o["ratio"] = round(o["rtl_service"] / o["sim_cost"], 3)
        o["sim_cost"] = round(o["sim_cost"], 3)
    muts = {}
    for p in a.mutant_log:
        t = p.read_text()
        muts[p.name] = dict(pass_=bool(PASS.search(t)), expected="FAIL",
                            tail=[ln for ln in t.splitlines() if "FATAL" in ln or "FAIL" in ln or "MISMATCH" in ln][:3])
    gate = ok and all(x["mismatch"] == 0 for x in rows) and all(not m["pass_"] for m in muts.values())
    rep = dict(schema="opentallas.hgi_unit_tput.v1 (hgi-e2e report.json compatible)", pass_=gate,
               summary=dict(cycles=prev, records=len(rows), exact_records=sum(x["mismatch"] == 0 for x in rows)),
               per_unit={a.unit: dict(records=len(rows), real=len(rows), exact=sum(x["mismatch"] == 0 for x in rows),
                                      rtl_busy=busy, sim_cost=round(cost, 3))},
               per_op=per_op, records=rows, mutants=muts)
    if a.meta:
        rep.update(json.loads(a.meta))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(pass_=gate, per_op=per_op)))


if __name__ == "__main__":
    main()
