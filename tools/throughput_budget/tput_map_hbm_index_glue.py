#!/usr/bin/env python3
"""tput-map-1011 / F6: production-shape DENSE throughput runs of the four HBM native-index glue elements, on the closed
registered-boundary wrappers (physical/struct_close/regbound/*_rb.sv) with each element's COMMITTED exact golden bench
(physical/struct_close/regbound/bench.py cases) and its committed mutant.  The only changes to the golden benches are the
stimulus pacing (every throttle removed: sinks always ready, sources offer every cycle, provider latency fixed) and the
item count (production shape); every value check is unchanged.

    python3 tools/throughput_budget/tput_map_hbm_index_glue.py --work DIR --out DIR/summary.json      (from the repo root)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import types
from pathlib import Path

R = Path.cwd()
spec = importlib.util.spec_from_file_location("rb", R / "physical/struct_close/regbound/bench.py")
RB = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RB)


def sub(t, a, b):
    assert t.count(a) == 1, a
    return t.replace(a, b)


# ---- global order (adopted: STATIC_SCAN=1 FAST=2, gorderscan_fast2_a) --------------------------------------------------
def gorder_dense(n, lat):
    t = RB.gorder_fast2_tb(n)
    t = sub(t, "read_r=!pending&&!rsp_v&&(cycle%7!=0);", "read_r=!pending&&!rsp_v;")
    t = sub(t, "out_r=(cycle%5==0);", "out_r=1;")
    t = sub(t, "delay_count=2+(cycle%3);", f"delay_count={lat};")
    return t


# ---- candidate parse: NFL flits of 15 slots, sink always ready ---------------------------------------------------------
def parse_dense(nfl):
    t = RB.const("tools/hbm_index_native_credit_gate.py", "PARSE")
    t = sub(t, "while(got<60&&cyc<1000)", f"while(got<{15 * nfl}&&cyc<{nfl * 60 + 1000})")
    t = sub(t, "fv=sent<4;tr=cyc%5!=0;", f"fv=sent<{nfl};tr=1;")
    t = sub(t, "if(got!=60||sent!=4||!drained)", f"if(got!={15 * nfl}||sent!={nfl}||!drained)")
    t = sub(t, "PARSE_DONE tuples=60 cycles=%0d", f"PARSE_DONE tuples={15 * nfl} flits={nfl} cycles=%0d")
    return t


# ---- candidate format: one rank's list in 4 quarters, co offered every cycle a credit is held, TU sink always ready ----
def format_dense(quarters):
    def tbw(w):
        src = (R / "tools/hbm_index_native_format_gate.py").read_text()
        src = sub(src, "[2,16,342,1366]", repr(list(quarters)).replace(" ", ""))
        src = sub(src, "ready=(cyc%10==0);", "ready=1;")
        src = sub(src, "credits>0&&cyc%3!=0", "credits>0")
        m = types.ModuleType("fg")
        m.__file__ = str(R / "tools/hbm_index_native_format_gate.py")
        exec(compile(src, m.__file__, "exec"), m.__dict__)
        m.subprocess = types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(returncode=1), STDOUT=None)
        argv = sys.argv
        sys.argv = ["g", "--work", str(w)]
        try:
            m.main()
        finally:
            sys.argv = argv
        return (w / "tb.sv").read_text()
    return tbw


# ---- query credit: 2 frames x 128 query blocks, credit returned every cycle one is outstanding --------------------------
def query_dense():
    t = RB.const("tools/hbm_index_native_credit_gate.py", "QUERY")
    return sub(t, "qbr=outstanding!=0&&cyc%7==0;", "qbr=outstanding!=0;")


RUNS = []
for n in (512, 2048, 4096):
    for lat in (0, 3):
        RUNS.append((f"gorder_n{n}_l{lat}", "ot_hbm_index_global_order",
                     dict(RB.CASES["global_order"], tb=(lambda n=n, lat=lat: gorder_dense(n, lat)),
                          params=["-Ptb_hbm_index_global_order.SCAN_CASE=1"], ok=f"PASS_GLOBAL_ORDER ranks=96 tuples={n}")))
for n in (512, 2048):     # information: the non-scan merge (STATIC_SCAN=0, FAST=2; not the adopted closed variant)
    RUNS.append((f"gorderns_n{n}_l3", "ot_hbm_index_global_order",
                 dict(RB.CASES["global_order"], tb=(lambda n=n: gorder_dense(n, 3)), params=[],
                      ok=f"PASS_GLOBAL_ORDER ranks=96 tuples={n}")))
for nfl in (35, 92):     # 512 tuples (indexer list a rank) / 1380 slots (the 1366-candidate list a rank, model max 92 flits)
    RUNS.append((f"parse_f{nfl}", "ot_hbm_native_candidate_parse", dict(RB.CASES["cand_parse"], tb=(lambda nfl=nfl: parse_dense(nfl)))))
for name, q in (("format_q128x4", (128, 128, 128, 128)), ("format_q342x4", (342, 342, 342, 340)), ("format_gate_mix", (2, 16, 342, 1366))):
    RUNS.append((name, "ot_hbm_native_candidate_format", dict(RB.CASES["cand_format"], tb_w=format_dense(q))))
RUNS.append(("query_b128x2", "ot_hbm_native_index_query_credit", dict(RB.CASES["query_credit"], tb=query_dense)))

LINE = re.compile(r"(PASS_GLOBAL_ORDER|PARSE_DONE|FORMAT_DONE|QUERY_DONE)[^\n]*")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    res = {}
    for key, el, case in RUNS:
        if a.only and not re.search(a.only, key):
            continue
        RB.CASES[key] = case
        r = {}
        for mode in ("pos", "neg"):
            w = a.work / key / mode
            rc = RB.run(key, mode, w)
            log = (w / "run.log").read_text() if (w / "run.log").exists() else ""
            m = LINE.search(log)
            r[mode] = dict(rc=rc, line=m.group(0) if m else None, tail=log[-300:])
        r["element"] = el
        r["exact_pass"] = r["pos"]["rc"] == 0
        r["mutant_fail"] = r["neg"]["rc"] == 1
        res[key] = r
        print(key, r["exact_pass"], r["mutant_fail"], r["pos"]["line"], flush=True)
    a.out.write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
