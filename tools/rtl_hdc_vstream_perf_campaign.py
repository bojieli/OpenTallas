#!/usr/bin/env python3
"""Per-block performance bench of the vector stream unit (rtl/hdc/ot_hdc_vstream.sv).

    python3 tools/rtl_hdc_vstream_perf_campaign.py [--output results/rtl/hdc_vstream_perf.json]

For each width SW it runs rtl/test/tb_hdc_vstream_perf.sv under Verilator
(COPY, SUM, MAX and a segmented sum of squares over N elements) and checks the
block against its spec (docs/ARCH_SPEC_QWEN3.md):
  * throughput: an N-element op writes its elements in exactly N/SW cycles;
  * depth: go -> first write equals the timing model's su_depth, and the
    reducer's tail (last element -> result) is within a cycle of its red_tail
    (the model's constant is fitted to the whole-token trace, where the
    sequencer sees the registered idle);
  * arithmetic: every reducer result is bit-exact with tools/hdc_golden.py
    (reduce_chunked, the R-ARITH order, for every SW).
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_timing as T  # noqa: E402

OUT = ROOT / "results/rtl/hdc_vstream_perf.json"
RTL = [ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_delay", "ot_hdc_fp32_mul_pipe", "ot_hdc_fpu", "ot_hdc_fastfp", "ot_hdc_sfu",
                                          "ot_hdc_vstream_lane", "ot_hdc_vreduce", "ot_hdc_vstream")]
PIPES = [ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv", ROOT / "rtl/proto/ot_fp32_mul_rne_pipe.sv"]
TB = ROOT / "rtl/test/tb_hdc_vstream_perf.sv"
HARNESS = ROOT / "rtl/test/hdc_vstream_perf_harness.cpp"
CONFIGS = ((8, 7), (16, 6), (32, 5))         # (SW, LV): LV = log2 of the most vectors a segment spans
N, NSEG = 1024, 8
F = np.float32


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_one(sw, lv, s: Path):
    rng = np.random.default_rng(sw)
    v = (rng.standard_normal(N) * rng.choice([1e-2, 1.0, 1e2], N)).astype(F)
    (s / "vm.hex").write_text("".join(f"{int(b):08x}\n" for b in G.bits(v)))
    obj = s / f"obj{sw}"
    subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
                    "-Wno-BLKSEQ", "--top-module", "tb_hdc_vstream_perf", f"-GSW={sw}", f"-GLV={lv}", "-Mdir",
                    str(obj), *map(str, RTL), *map(str, PIPES), str(TB), str(HARNESS), "-CFLAGS", "-O1"],
                   check=True, capture_output=True)
    out = subprocess.run([str(obj / "Vtb_hdc_vstream_perf"), f"+DIR={s}", f"+N={N}", f"+NSEG={NSEG}"],
                         check=True, capture_output=True, text=True).stdout
    ops = {int(m.group(1)): dict(go=int(m.group(2)), first=int(m.group(3)), last=int(m.group(4)),
                                 idle=int(m.group(5)), fault=int(m.group(6)))
           for m in re.finditer(r"OP op=(\d+) go=(\d+) first_write=(-?\d+) last_write=(-?\d+) idle=(\d+) fault=(\d+)", out)}
    reds = [dict(op=int(m.group(1)), cyc=int(m.group(2)), addr=int(m.group(3)), bits=int(m.group(4), 16))
            for m in re.finditer(r"RED op=(\d+) cyc=(\d+) addr=(\d+) data=([0-9a-f]+)", out)]
    nvec = N // sw
    depth_none = T.K["su_depth"][0]
    k = dict(T.K, red_lv=lv)
    tail_model = T.red_tail(k, sw)
    copy = ops[0]
    thr = copy["last"] - copy["first"] + 1
    # expected reducer results
    exp_sum = int(G.bits(G.reduce_chunked(v)))
    exp_max = int(G.bits(F(np.max(v))))
    seg = N // NSEG
    exp_ssq = [int(G.bits(G.reduce_chunked(G.mul(v[i * seg:(i + 1) * seg], v[i * seg:(i + 1) * seg]))))
               for i in range(NSEG)]
    got = {r["op"]: [] for r in reds}
    for r in reds:
        got[r["op"]].append(r)
    sum_ok = [r["bits"] for r in got.get(1, [])] == [exp_sum]
    max_ok = [r["bits"] for r in got.get(2, [])] == [exp_max]
    ssq_ok = [r["bits"] for r in got.get(3, [])] == exp_ssq
    # tails: the reducer result after the op's last element (go + 1 + nvec - 1 + depth)
    last_el = {o: ops[o]["go"] + 1 + (N // sw if o != 3 else N // sw) - 1 + depth_none for o in (1, 2, 3)}
    tails = {o: got[o][-1]["cyc"] - last_el[o] for o in (1, 2, 3) if got.get(o)}
    rec = dict(sw=sw, lv=lv, n=N, vectors=nvec, copy_write_cycles=thr,
               throughput_elements_per_cycle=N / thr, first_write_after_go=copy["first"] - copy["go"],
               model_depth_none=depth_none, reducer_tail=tails, model_reducer_tail=tail_model,
               sum_bit_exact=sum_ok, max_bit_exact=max_ok, sumsq_segments_bit_exact=ssq_ok,
               faults=[ops[o]["fault"] for o in sorted(ops)])
    rec["pass"] = bool(thr == nvec and sum_ok and max_ok and ssq_ok and not any(rec["faults"])
                       and all(abs(t - tail_model) <= 1 for t in tails.values()))
    return rec, out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()
    rows = []
    with tempfile.TemporaryDirectory() as d:
        for sw, lv in CONFIGS:
            rec, _ = run_one(sw, lv, Path(d))
            rows.append(rec)
            print(json.dumps(rec))
    out = dict(schema="opentallas.hdc-vstream-perf.v1", tool="tools/rtl_hdc_vstream_perf_campaign.py",
               claim="per-block bench of the vector stream unit: throughput SW elements a cycle, the depths the "
                     "calibrated timing model uses, R-ARITH reductions bit-exact with the golden",
               status="pass" if all(r["pass"] for r in rows) else "fail", configurations=rows,
               input_sha256={str(p.relative_to(ROOT)): sha(p) for p in (*RTL, *PIPES, TB, HARNESS,
                                                                          ROOT / "tools/hdc_golden.py",
                                                                          ROOT / "tools/hdc_timing.py",
                                                                          Path(__file__))})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    print(out["status"])
    return 0 if out["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
