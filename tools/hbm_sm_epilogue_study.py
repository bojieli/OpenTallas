#!/usr/bin/env python3
"""Model-level study (W13b, 2026-10-01; user decision AGENTS.md a4f314fb: HBM comparators borrow only what real
GPUs have): a Blackwell-TMEM-style accumulator memory plus register epilogues on the SM's column outputs.

    python3 tools/hbm_sm_epilogue_study.py [--out results/uarch/hbm_sm_epilogue_study.json]

Precedent: Blackwell (sm_100) keeps MMA accumulators in a per-SM tensor memory (TMEM, 256 KB = 128 lanes x 512
columns x 32 bit), read by tcgen05.ld into registers, where the epilogue (bias, residual, norm partials,
activation, quantise) runs on the CUDA cores before the store.  Here the SM's column results (one FP32 per
column per row, ot_gpu_tc_col / ot_gpu_bd_col) drain into an accumulator memory and through a per-column
register epilogue, so three on-path vector steps leave the token chain:
  * norm partials: sum of squares of the rows this SM produced (the global combine stays: 32 SM partials on a
    5-level FP32 add tree; across dies it rides the collective that already gathers the activations);
  * quantise: block-32 amax and E4M3 encode of the next op's activations (V4.1 FP8 / block-dot inputs);
  * residual: the residual (V4.1: mHC post combine) add on the output rows.
Not established: RTL, timing, the scheduling of a 32-row quantise block across SMs (assumed row-aligned).
Inputs are the unified model's (tools/uarch_model.py): unit areas, SM element, drains, the V4.1 HBM chain
(v41_hbm_chain) and the Qwen stream model (qwen_hbm_ops / stream_overlap).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import uarch_model as U  # noqa: E402

FADD_LAT, FMUL_LAT = 7, 7          # the SM's FP32 add / mul depth at 1.2 GHz SS (W11 keep-prefix, measured)
EPI_DEPTH = FMUL_LAT + FADD_LAT + 2   # square/scale, accumulate/add, amax + encode registers
COMBINE_CYCLES = 5 * FADD_LAT + 1  # 32 SM partials -> one sum (5 levels) + the result register
FUSED_V41 = (r"\.norm\.sumsq$", r"\.q_norm\.sumsq$", r"quant", r"\.hc_post$")
OUT = ROOT / "results/uarch/hbm_sm_epilogue_study.json"


def area(model):
    d = U.hbm_gpu_design(model)
    e, u = d["element"], U.GPU_UNIT_UM2
    cols = e["cols"]
    # TMEM sizing: the largest per-SM output slice of one op, every column, FP32, double-buffered so the next op's
    # columns write while the epilogue drains the previous one
    if model == "qwen":
        rows_sm = max(2 * 12288 // 2, 4096 // 2 * 3) / 32           # gate_up on the TP-2 die (12,288 rows) / 32 SMs
    else:
        _, b = U.arch_graph(1048576)
        g = b.g
        rows_sm = max(nd["sweep"]["macs"] / U.NODE_K[U.node_key(x)] / U.V41_HBM_DIES / 32
                      for x, nd in g.nodes.items() if nd["kind"] == "matvec" and U.node_key(x) in U.NODE_K
                      and U.node_key(x) != "hc.fn")
    tmem_kb = 2 * math.ceil(rows_sm) * cols * 4 / 1024
    macros = math.ceil(tmem_kb / 32)
    lane_um2 = (u["fp32_mul"] + u["fp32_add"] + 0.25 * u["fp32_add"] + 0.5 * u["fp32_add"]
                + (FMUL_LAT + FADD_LAT + 8) * 32 * u["dff"])
    logic_um2 = cols * lane_um2
    mm2 = logic_um2 / U.GPU_LOGIC_UTIL / 1e6 + macros * u["sram32k"] * U.GPU_MACRO_PACK / 1e6
    sm_mm2 = d["sm_area"]["total_mm2"]
    return dict(cols=cols, rows_per_sm_max=round(rows_sm, 1), tmem_kb_per_sm=round(tmem_kb, 1),
                tmem_macros_32kb=macros, blackwell_tmem_kb_per_sm=256,
                ports=dict(write_bits_per_clk=cols * 32, read_bits_per_clk=cols * 32,
                           macro="1R1W 256-bit (ot_sram_1r1w class); write = column drain, read = epilogue"),
                epilogue_lanes=cols, epilogue_lane_um2=round(lane_um2), epilogue_logic_um2=round(logic_um2),
                added_mm2_per_sm=round(mm2, 4), sm_mm2=sm_mm2, added_fraction_of_sm=round(mm2 / sm_mm2, 4),
                added_mm2_per_die=round(32 * mm2, 3), sm_per_die=d["sm_count"])


def v41_time():
    T0, parts, nb = U.v41_hbm_chain(True, 1)
    d = U.hbm_gpu_design("v41")
    clock = d["clock_hz"]
    _, b = U.arch_graph(1048576)
    g = b.g
    removed, n_fused, combine = 0.0, 0, 0.0
    by = {}
    for x in g.path(b.sink):
        nd = g.nodes[x]
        if nd["kind"] in ("matvec", "collective", "hop"):
            continue
        if any(re.search(p, x) for p in FUSED_V41):
            t = sum(g.contrib[x].values())
            removed += t
            n_fused += 1
            k = re.sub(r"^.*?\.(attn|ffn)\.", r"\1.", x)
            by[k] = by.get(k, 0.0) + t
            if x.endswith("sumsq"):
                combine += COMBINE_CYCLES / clock
    added = n_fused * EPI_DEPTH / clock
    saved = (removed - added - combine) * 1e6
    return dict(clock_hz=clock, baseline_us=round(T0, 2), baseline_tokens_s=round(1e6 / T0, 1),
                removed_on_path_us=round(removed * 1e6, 2), fused_nodes=n_fused,
                removed_by_kind_us={k: round(v * 1e6, 2) for k, v in sorted(by.items())},
                added_epilogue_depth_us=round(added * 1e6, 2), added_partial_combine_us=round(combine * 1e6, 2),
                with_epilogue_us=round(T0 - saved, 2), saved_us_per_token=round(saved, 2),
                with_epilogue_tokens_s=round(1e6 / (T0 - saved), 1),
                basis="v41_hbm_chain (group-slot, 1M, AR): on-path sumsq / quant / hc_post nodes removed; each "
                      f"fused producer's drain +{EPI_DEPTH} cycles; each sumsq keeps a {COMBINE_CYCLES}-cycle "
                      "on-die partial combine (the cross-die part rides the existing collective)")


def qwen_time():
    d = U.hbm_gpu_design("qwen")
    e, clock = d["element"], d["clock_hz"]
    bnd, drain = d["barrier"]["boundary_cycles"], d["drain_cycles"]
    n, staging = d["sm_count"], d["staging_kb_per_sm"] * 1024 * d["sm_count"]
    base = U.qwen_hbm_ops(e, bnd, drain)
    t0, _ = U.stream_overlap(base, d["hbm_Bpc"], n * e["ingest_Bpc"], staging)
    rec = json.loads((ROOT / "results/arch/qwen3_budget.json").read_text())
    st = {s["stage"]: s["exposed_latency"] + s["throughput"]
          for s in rec["dependency_chain"]["8192/spec_widths_reference_graph"]["stages"]}
    # per layer: qk_norm.sumsq fused into the qkv epilogue (heads are SM-local: no combine); the two
    # residual+sumsq steps fused into the o / down epilogues (+ the 32-SM combine)
    ops = []
    for i, (by, lat) in enumerate(base):
        j = i % 7 if i < 7 * 36 else -1
        if j == 1:
            lat = lat - st["qk_norm.sumsq"] + EPI_DEPTH
        elif j in (4, 6):
            lat = lat - st["residual+sumsq"] + EPI_DEPTH + COMBINE_CYCLES
        ops.append((by, lat))
    t1, _ = U.stream_overlap(ops, d["hbm_Bpc"], n * e["ingest_Bpc"], staging)
    chain0 = sum(l for _, l in base)
    chain1 = sum(l for _, l in ops)
    return dict(clock_hz=clock, baseline_cycles=round(t0), with_epilogue_cycles=round(t1),
                baseline_us=round(t0 / clock * 1e6, 2), with_epilogue_us=round(t1 / clock * 1e6, 2),
                saved_us_per_token=round((t0 - t1) / clock * 1e6, 3),
                dependent_latency_removed_us=round((chain0 - chain1) / clock * 1e6, 2),
                hbm_bound=True,
                basis="qwen_hbm_ops + stream_overlap (8K, AR): the token is HBM-bound (the bulk copy prefetches "
                      "through every boundary), so the removed dependent latency is hidden; it only shows where "
                      "the stream cannot cover it")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args(argv)
    srcs = ["tools/hbm_sm_epilogue_study.py", "tools/uarch_model.py", "results/arch/qwen3_budget.json"]
    rec = dict(schema="opentallas.uarch.hbm_sm_epilogue.v1", status="model-level (no RTL)",
               precedent="NVIDIA Blackwell sm_100 tensor memory (256 KB/SM) + register epilogue (tcgen05.ld)",
               epilogue_depth_cycles=EPI_DEPTH, partial_combine_cycles=COMBINE_CYCLES,
               area=dict(qwen=area("qwen"), v41=area("v41")),
               token=dict(v41=v41_time(), qwen=qwen_time()),
               source_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in srcs})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(area={k: dict(tmem_kb=v["tmem_kb_per_sm"], mm2_sm=v["added_mm2_per_sm"],
                                        frac=v["added_fraction_of_sm"], mm2_die=v["added_mm2_per_die"])
                                for k, v in rec["area"].items()},
                          v41={k: rec["token"]["v41"][k] for k in ("baseline_us", "saved_us_per_token",
                                                                   "with_epilogue_tokens_s", "removed_by_kind_us")},
                          qwen={k: rec["token"]["qwen"][k] for k in ("baseline_us", "saved_us_per_token",
                                                                    "dependent_latency_removed_us")}), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
