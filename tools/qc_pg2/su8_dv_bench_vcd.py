#!/usr/bin/env python3
"""QC-PG-2 (10-27): measured SU8 activity on the real QC slice workload = dv_bench2 golden benches on the BOUND s8 die
slice row (DV2_S8DIE=1, FACE 3, tools/qwen_tokfunc/s8die_srcs.py S8_FLAGS), Verilator --trace limited to the su8 sources
(su8_trace.vlt), VCD per simulation, toggle rates per bit via tools/pg_activity/vcd_activity.py (clock = su8 ck), then
the VCD is deleted.  Each bench keeps its own golden check (bench PASS printed by dv_bench2).
  su8_dv_bench_vcd.py WORK BENCH [BENCH ...]"""
import os, sys, subprocess, json, glob, re
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
os.environ["DV2_S8DIE"] = "1"
sys.path.insert(0, str(ROOT / "rtl/test/qwen_dv")); sys.path.insert(0, str(ROOT / "tools/qwen_tokfunc"))
import s8die_srcs as S8
import dv_bench2 as D
work = Path(sys.argv[1]).resolve(); benches = sys.argv[2:]
D.HERE = HERE                                   # main2.cpp -> tools/qc_pg2/main2.cpp (traced driver)
orig = D.run_sim2
def run_traced(name, ev, wk, mut, ncyc, n=2):
    out = orig(name, ev, wk, mut, ncyc, n)
    vcd = Path(wk) / f"{name}.log.vcd"
    od = work / "act" / f"{Path(wk).name}_{name}_{len(list((work / 'act').glob('*')))}"; od.mkdir(parents=True, exist_ok=True)
    sc = subprocess.run([sys.executable, str(ROOT / "tools/pg_activity/vcd_activity.py"), str(vcd), str(od), "--list-scopes", "u_su8$"],
                        capture_output=True, text=True).stdout.split()
    roots = [f"--root=s{i}={s}" for i, s in enumerate(sc)]
    r = subprocess.run([sys.executable, str(ROOT / "tools/pg_activity/vcd_activity.py"), str(vcd), str(od), "--clk", sc[0] + ".ck"] + roots,
                       capture_output=True, text=True)
    (od / "scopes.txt").write_text("\n".join(sc) + "\n" + r.stdout + r.stderr)
    vcd.unlink()
    return out
D.run_sim2 = run_traced
(work / "act").mkdir(parents=True, exist_ok=True)
sys.argv = ["dv_bench2", *benches, "--work", str(work / "bench"), "--vflags",
            " ".join(S8.S8_FLAGS + ["--trace", str(HERE / "su8_trace.vlt")])]
D.main()
