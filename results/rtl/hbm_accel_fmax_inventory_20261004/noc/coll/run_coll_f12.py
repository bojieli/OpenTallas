#!/usr/bin/env python3
"""Exactness + cycle delta of ot_gpu_coll_endpoint_f12 against ot_gpu_coll_endpoint on the unmodified collective bench
(rtl/test/gpu_sys/tb_gpu_coll.sv, stimulus and checker of tools/gpu_sys/run_coll.py).  For each seed the bench is
built twice -- as pinned (baseline endpoints) and with the two ENABLE=1 endpoints swapped for the successor (text
substitution into a generated copy) -- and both dumps are checked bit exact against numpy; the measured-latency
cases (both ranks idle, response always ready) give the clk_sm cycles from request handshake to coll_rsp_v.

    python3 run_coll_f12.py --out coll_f12.json --work DIR [--seeds 1,2,3] [--nt 160]     (run on a compute host)
"""
import argparse, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / "tools" / "gpu_sys"))
import run_coll as RC  # noqa: E402

BENCH0 = RC.BENCH
XREG = 0
NEW = [ROOT / "rtl/gpu_sys/ot_gpu_cdc_fifo_oh.sv", ROOT / "rtl/gpu_sys/ot_gpu_coll_mux_f12.sv", ROOT / "rtl/gpu_sys/ot_gpu_coll_endpoint_f12.sv"]


def run(variant, seed, nt, work):
    b = work / f"{variant}_s{seed}"
    b.mkdir(parents=True, exist_ok=True)
    tb = BENCH0.read_text()
    if variant == "f12":
        n = tb.count("ot_gpu_coll_endpoint #(.ENABLE(1)")
        assert n == 1, n
        tb = tb.replace("ot_gpu_coll_endpoint #(.ENABLE(1)", f"ot_gpu_coll_endpoint_f12 #(.XREG({XREG}), .ENABLE(1)")
    (b / "tb_gpu_coll.sv").write_text(tb)
    RC.BENCH = b / "tb_gpu_coll.sv"
    RC.RTL = RC.OURS + RC.REUSED + (NEW if variant == "f12" else [])
    cases = RC.make_cases(nt, seed)
    RC.write_stim(cases, b / "stim.hex")
    exe = RC.build(b, 4, 2)
    r = subprocess.run([str(exe), f"+stim={b / 'stim.hex'}", f"+out={b / 'out.txt'}", f"+verilator+seed+{seed}"],
                       cwd=b, capture_output=True, text=True)
    (b / "sim.log").write_text(r.stdout + r.stderr)
    res = RC.check(cases, (b / "out.txt").read_text() if (b / "out.txt").exists() else "")
    meas = [c for c in res["cases"] if c["measure"]]
    return dict(n_fail=res["n_fail"], n_cases=len(res["cases"]), done=res["done"],
                measure=[dict(mode=c["mode"], count=c["count"], latency_sm=c["latency_sm"]) for c in meas],
                bad=[c for c in res["cases"] if not c["pass_"]][:5])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--nt", type=int, default=160)
    ap.add_argument("--xreg", type=int, default=0)
    a = ap.parse_args()
    global XREG
    XREG = a.xreg
    rows, ok = [], True
    for s in map(int, a.seeds.split(",")):
        base, new = run("base", s, a.nt, a.work), run("f12", s, a.nt, a.work)
        delta = [[(n - b) if (n is not None and b is not None) else None for b, n in zip(mb["latency_sm"], mn["latency_sm"])]
                 for mb, mn in zip(base["measure"], new["measure"])]
        good = base["n_fail"] == 0 and new["n_fail"] == 0 and new["done"] is not None and new["done"][0] == 0
        ok &= good
        rows.append(dict(seed=s, baseline=base, f12=new, latency_delta_sm_cycles=delta, pass_=good))
        print(f"seed {s}: base fail {base['n_fail']}/{base['n_cases']} f12 fail {new['n_fail']}/{new['n_cases']} "
              f"faults {new['done']} delta {delta}")
    srcs = [*RC.OURS, *RC.REUSED, *NEW, ROOT / "rtl/test/gpu_sys/tb_gpu_coll.sv", ROOT / "tools/gpu_sys/run_coll.py"]
    a.out.write_text(json.dumps(dict(schema="opentallas.noc_fmax.coll_f12_exactness.v1", verdict="PASS" if ok else "FAIL",
                                     sources={str(p.relative_to(ROOT)): RC.sha(p) for p in srcs}, xreg=a.xreg, rows=rows),
                                indent=1) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
