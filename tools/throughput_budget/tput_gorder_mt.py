#!/usr/bin/env python3
"""tputx-gord 2026-10-11: exact benches + mutant + production-shape throughput bench of ot_hbm_index_global_order_mt
(the merge-tree successor of ot_hbm_index_global_order) on its registered-boundary wrapper
physical/struct_close/regbound/ot_hbm_index_global_order_mt_rb.sv (tools/struct_close/gen_regbound.py, global_order_mt.json).

Cases (all on the COMMITTED golden bench rtl/test/hbm_accel/tb_hbm_index_global_order.sv, instantiating the _mt module):
  golden_n12288     golden bench unchanged (single-outstanding throttled provider, throttled sink) + RTL mutant out_tuple^2
  mutrank / future  the bench's own negatives (+MUT_RANK, +FUTURE_ID) must fault (EXPECTED_BAD_IDENTITY_REJECT)
  sparse_*          rtl/test/hbm_accel/tb_hbm_index_global_order_sparse.sv: random sparse id set, random invalid slots,
                    empty ranks, pipelined provider, random sink stalls; + the same RTL mutant
  tput_n<N>_l<L>    production shape: the provider becomes an in-order PIPELINED read port (a read accepted every cycle,
                    each answered L cycles later -- the TU publication store is a pipelined storage port), sink always
                    ready; every value / count check of the golden bench unchanged; + the same RTL mutant
    python3 tools/throughput_budget/tput_gorder_mt.py --work DIR --out DIR/summary.json [--only REGEX]   (repo root)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path

R = Path.cwd()
spec = importlib.util.spec_from_file_location("rb", R / "physical/struct_close/regbound/bench.py")
RB = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RB)
WRAP = "physical/struct_close/regbound/ot_hbm_index_global_order_mt_rb.sv"
MUT = ("assign out_tuple=p_head[ROOT];", "assign out_tuple=p_head[ROOT]^34'd2;")


def sub(t, a, b):
    assert t.count(a) == 1, a
    return t.replace(a, b)


def golden(n):
    t = RB.sp_tb("gorder_tb", n)
    return sub(t, "ot_hbm_index_global_order #(.ENABLE(1),.STATIC_SCAN(SCAN_CASE)) dut(.*);",
               "ot_hbm_index_global_order_mt #(.ENABLE(1)) dut(.*);")


def pipelined(n, lat):
    t = golden(n)
    t = sub(t, "reg pending=0;", "reg pending=0;integer qh=0,qt=0;reg [6:0] qr[0:8191];reg [16:0] qo[0:8191];integer qdue[0:8191];")
    t = sub(t, "read_r=!pending&&!rsp_v&&(cycle%7!=0);", "read_r=1;")
    t = sub(t, "out_r=(cycle%5==0);", "out_r=1;")
    t = sub(t, "if(pending&&delay_count>0)delay_count=delay_count-1;", "")
    t = sub(t, "if(pending&&delay_count==0&&!rsp_v)begin",
            "if(qh!=qt&&cycle>=qdue[qh%8192]&&!rsp_v)begin p_rank=qr[qh%8192];p_ord=qo[qh%8192];qh=qh+1;")
    t = sub(t, "if(read_frame!==owner_frame||pending||rsp_v)$fatal", "if(read_frame!==owner_frame||qt-qh>=8192)$fatal")
    t = sub(t, "p_rank=read_rank;p_ord=read_ordinal;pending=1;delay_count=2+(cycle%3);",
            f"qr[qt%8192]=read_rank;qo[qt%8192]=read_ordinal;qdue[qt%8192]=cycle+{lat};qt=qt+1;")
    return t


BASE = dict(rtl=[WRAP], top="tb_hbm_index_global_order", neg_mut=MUT, neg_ok="")
RUNS = [("golden_n12288", dict(BASE, tb=lambda: golden(12288), ok="PASS_GLOBAL_ORDER ranks=96 tuples=12288"), ("pos", "neg")),
        ("mutrank", dict(BASE, tb=lambda: golden(512), pos_args=["+MUT_RANK"], ok="EXPECTED_BAD_IDENTITY_REJECT"), ("pos",)),
        ("future", dict(BASE, tb=lambda: golden(512), pos_args=["+FUTURE_ID"], ok="EXPECTED_BAD_IDENTITY_REJECT"), ("pos",))]
for n in (512, 2048, 4096):
    for lat in (3, 0):
        RUNS.append((f"tput_n{n}_l{lat}", dict(BASE, tb=(lambda n=n, lat=lat: pipelined(n, lat)),
                                               ok=f"PASS_GLOBAL_ORDER ranks=96 tuples={n}"), ("pos", "neg")))
SPARSE = "rtl/test/hbm_accel/tb_hbm_index_global_order_sparse.sv"
for n, lat, seed, stall in ((512, 3, 1, 0), (512, 3, 7, 3), (64, 3, 9, 2), (12288, 3, 11, 1)):
    P = "tb_hbm_index_global_order_sparse."
    RUNS.append((f"sparse_n{n}_l{lat}_s{seed}_st{stall}",
                 dict(BASE, tb=(lambda: (R / SPARSE).read_text()), top="tb_hbm_index_global_order_sparse",
                      params=[f"-P{P}N={n}", f"-P{P}LAT={lat}", f"-P{P}SEED={seed}", f"-P{P}STALL={stall}"],
                      ok=f"PASS_GLOBAL_ORDER_SPARSE n={n}"), ("pos", "neg")))
LINE = re.compile(r"(PASS_GLOBAL_ORDER\w*|EXPECTED_BAD_IDENTITY_REJECT)[^\n]*")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--case", default="", help="run one case (loop bench): exit 0 = PASS (pos); neg prints "
                                              "TPUT_GORDER_MT_MUTANT_DETECTED and exits 1 only on a value mismatch")
    ap.add_argument("--mode", default="pos", choices=("pos", "neg"))
    a = ap.parse_args()
    a.work = a.work.resolve()
    if a.case:
        case = {k: c for k, c, _ in RUNS}[a.case]
        RB.CASES[a.case] = case
        rc = RB.run(a.case, a.mode, a.work)
        if a.mode == "neg":
            log = (a.work / "run.log").read_text() if (a.work / "run.log").exists() else ""
            if rc == 1 and re.search(r"(canonical ID or exact score|sparse order) mismatch", log):
                print("TPUT_GORDER_MT_MUTANT_DETECTED", a.case)
                raise SystemExit(1)
            print("TPUT_GORDER_MT_MUTANT_ESCAPED_OR_ERROR", a.case)
            raise SystemExit(2)
        raise SystemExit(rc)
    res = {}
    for key, case, modes in RUNS:
        if a.only and not re.search(a.only, key):
            continue
        RB.CASES[key] = case
        r = {}
        for mode in modes:
            w = a.work / key / mode
            rc = RB.run(key, mode, w)
            log = (w / "run.log").read_text() if (w / "run.log").exists() else ""
            m = LINE.search(log)
            r[mode] = dict(rc=rc, line=m.group(0) if m else None)
        r["exact_pass"] = r["pos"]["rc"] == 0
        if "neg" in r:   # the mutant must be rejected by the bench's value check, not by a build / run error
            nlog = (a.work / key / "neg" / "run.log")
            r["mutant_fail"] = r["neg"]["rc"] == 1 and nlog.exists() and re.search(r"(canonical ID or exact score|sparse order) mismatch", nlog.read_text()) is not None
        res[key] = r
        print("TPUT_GORDER_MT", key, r["exact_pass"], r.get("mutant_fail"), r["pos"]["line"], flush=True)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
