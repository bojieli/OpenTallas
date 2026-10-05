#!/usr/bin/env python3
"""Rebuild the Qwen GPU comparison inputs without the old iso-area design.

The H200 row is a two-point latency fit to NVIDIA's concurrency-one NIM
Llama-3.1-8B measurements. The RTX rows come from this repository's measured
decode runs. The Qwen byte count and KV format come from the current O4 budget.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/arch/qwen_gpu_calibration.json"
GPU = ROOT / "results/gpu/qwen3_rtx_pro_6000_decode.json"
BUDGET = ROOT / "results/arch/qwen3_budget.json"

# NVIDIA NIM for LLMs performance, Llama-3.1-8B-Instruct, H200,
# concurrency 1, 1000 input / 1000 output tokens. The fixed term is scaled
# from Llama's 32 layers to Qwen3-8B's 36; this is a model, not an H200 run.
NIM_H200 = {"bf16_tok_s": 140.14, "fp8_tok_s": 234.95,
            "source": "https://docs.nvidia.com/nim/benchmarking/llm/1.0.0/performance.html"}
LLAMA_PARAMS_READ = 7_504_658_432
LLAMA_KV_BYTES = 2 * 32 * 8 * 128 * 1_500 * 2  # K,V; layers; KV heads; dim; mean context; BF16


def build() -> dict:
    gpu_raw = GPU.read_bytes()
    budget_raw = BUDGET.read_bytes()
    gpu = json.loads(gpu_raw)
    budget = json.loads(budget_raw)
    runs = gpu["runs"]
    workload = "reasoning_math500"
    def measured(run: str, field: str) -> float:
        return runs[run]["workloads"][workload][field]

    bf16, fp8 = NIM_H200["bf16_tok_s"], NIM_H200["fp8_tok_s"]
    slope = (1 / bf16 - 1 / fp8) / LLAMA_PARAMS_READ
    fixed_llama = 1 / fp8 - slope * (LLAMA_PARAMS_READ + LLAMA_KV_BYTES)
    fixed_qwen = fixed_llama * budget["shape"]["L"] / 32
    fp8_bytes = budget["hbm_comparator"]["8192"]["fp8"]["bytes_per_token"]
    kv_bytes = budget["requirements"]["kv_hbm"]["bytes_per_token"]
    weights_bytes = fp8_bytes - kv_bytes
    bf16_bytes = 2 * weights_bytes + kv_bytes
    def tok_s(byte_count: float) -> float:
        return 1 / (fixed_qwen + slope * byte_count)

    return {
        "schema": "opentallas.qwen-gpu-calibration.v1",
        "tool": "tools/qwen_gpu_calibration.py",
        "evidence_class": "model for H200; measured GPU for RTX PRO 6000",
        "inputs": {"results/gpu/qwen3_rtx_pro_6000_decode.json": hashlib.sha256(gpu_raw).hexdigest(),
                   "results/arch/qwen3_budget.json": hashlib.sha256(budget_raw).hexdigest()},
        "nim_h200": NIM_H200,
        "fit": {"llama_params_read": LLAMA_PARAMS_READ, "llama_bf16_kv_bytes_at_mean_context": LLAMA_KV_BYTES,
                "seconds_per_weight_byte": slope, "fixed_seconds_llama": fixed_llama,
                "fixed_seconds_qwen": fixed_qwen,
                "qwen_fp8_weight_bytes": weights_bytes, "qwen_fp8_kv_bytes_8k": kv_bytes,
                "rule": "t = fixed_seconds_qwen + seconds_per_weight_byte * (weight bytes + KV bytes); "
                        "NIM BF16/FP8 pair fits the slope, fixed time scales by 36/32 layers"},
        "contexts": {"8192": {"autoregressive": {
            "h200_bf16": {"tok_s": tok_s(bf16_bytes), "grade": "NIM-calibrated model"},
            "h200_fp8": {"tok_s": tok_s(fp8_bytes), "grade": "NIM-calibrated model"}}}},
        "local_gpu_rtx_pro_6000": {"source": str(GPU.relative_to(ROOT)), "workload": workload,
            "concurrency_1": {
                "bf16": {"ar_tok_s": measured("ar_bf16", "decode_tokens_per_s"),
                          "dflash_tok_s": measured("dflash_b16_bf16", "decode_tokens_per_s"),
                          "dflash_tau": measured("dflash_b16_bf16", "tau_mean")},
                "fp8": {"ar_tok_s": measured("ar_fp8", "decode_tokens_per_s"),
                         "dflash_tok_s": measured("dflash_b16_fp8", "decode_tokens_per_s"),
                         "dflash_tau": measured("dflash_b16_fp8", "tau_mean")}}}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raw = json.dumps(build(), indent=1, ensure_ascii=False) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text() != raw:
            print(f"{OUT.relative_to(ROOT)} is stale")
            return 1
        print(f"{OUT.relative_to(ROOT)} is current")
        return 0
    OUT.write_text(raw)
    print(OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
