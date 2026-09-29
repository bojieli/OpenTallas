#!/usr/bin/env python3
"""RTL measurements that replace two free parameters of the GPU-organised HBM model.

    python3 tools/rtl_gpu_supply_barrier.py [--out results/rtl/gpu_supply_barrier.json]

supply   rtl/gpu/ot_gpu_bulk_copy.sv against a behavioural HBM share (rtl/test/tb_gpu_bulk_copy.sv): loaded
         latency LAT + jitter, at most one 128-B line a cycle, no faster than the SM's share of the die's
         sustained bandwidth.  Swept over outstanding reads; the model needs MAX_OUT x 128 B >= share x latency.
barrier  rtl/gpu/ot_gpu_barrier_node.sv as the 32-SM network (8 x 4 fan-in) with the registered wire stages the
         floorplan prices (results/floorplan/hbm_gpu/<model>_hbm_die.json barrier_network leaf/trunk cycles):
         last arrival -> every SM released, over 200 barriers with random skew.
"""
import argparse, hashlib, json, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_B = ["rtl/gpu/ot_gpu_bulk_copy.sv", "rtl/test/tb_gpu_bulk_copy.sv"]
SRC_R = ["rtl/gpu/ot_gpu_barrier_node.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/test/tb_gpu_barrier.sv"]


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def sim(src, top, params):
    d = tempfile.mkdtemp(prefix="gsb_")
    exe = Path(d) / "s.vvp"
    subprocess.run(["iverilog", "-g2012", "-o", str(exe), "-s", top] + [f"-P{top}.{k}={v}" for k, v in params.items()]
                   + [str(ROOT / s) for s in src], check=True)
    out = subprocess.run(["vvp", "-n", str(exe)], capture_output=True, text=True, check=True).stdout
    line = [l for l in out.splitlines() if l.startswith(("BULK", "BARRIER"))][-1]
    return {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", line)} | ({"timeout": True} if "TIMEOUT" in line else {})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    clock = 1.09864e9
    lat = round(500e-9 * clock)                      # the model's loaded latency, 500 ns
    share_ppm = round(3.6e12 / clock / 32 / 128 * 1e6)
    supply = []
    for mo in (7, 16, 64, 256, 440, 512):
        r = sim(SRC_B, "tb_gpu_bulk_copy", dict(MAX_OUT=mo, LAT=lat - 50, JIT=100, RATE_PPM=share_ppm, NLINES=20000))
        r["B_per_cycle"] = round(128 * r["window_lines"] / r["window_cycles"], 1)
        r["share_B_per_cycle"] = round(share_ppm / 1e6 * 128, 1)
        r["littles_law_B_per_cycle"] = round(min(share_ppm / 1e6, mo / lat) * 128, 1)
        supply.append(r)
        print("supply", mo, r["B_per_cycle"], r["littles_law_B_per_cycle"], r.get("bad"))
    barrier = []
    for model in ("qwen", "v41"):
        fp = json.loads((ROOT / f"results/floorplan/hbm_gpu/{model}_hbm_die.json").read_text())["barrier_network"]
        r = sim(SRC_R, "tb_gpu_barrier", dict(D_LEAF=fp["leaf_cycles"], D_TRUNK=fp["trunk_cycles"]))
        r.update(model=model, floorplan_leaf_um=fp["max_leaf_um"], floorplan_trunk_um=fp["max_trunk_um"])
        barrier.append(r)
        print("barrier", model, r)
    ok = all(s.get("bad", 1) == 0 and not s.get("timeout") for s in supply) and \
        all(b["early_release_errors"] == 0 and b["last_arrive_to_all_released_min"] == b["last_arrive_to_all_released_max"]
            for b in barrier)
    rec = dict(schema="opentallas.rtl.gpu_supply_barrier.v1", tool="tools/rtl_gpu_supply_barrier.py",
               status="pass" if ok else "fail", clock_hz=clock, loaded_latency_cycles=lat, supply=supply,
               barrier=barrier,
               source_sha256={s: sha(s) for s in sorted(set(SRC_B + SRC_R + ["tools/rtl_gpu_supply_barrier.py",
                   "results/floorplan/hbm_gpu/qwen_hbm_die.json", "results/floorplan/hbm_gpu/v41_hbm_die.json"]))})
    if a.out:
        Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")


if __name__ == "__main__":
    main()
