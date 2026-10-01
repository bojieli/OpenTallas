#!/usr/bin/env python3
"""Exact HC dot semantic witness, not a GPU timing or hardware qualification.

One software lane owns one contiguous eight-term chunk. Twelve separate
adjacent-pair passes preserve the golden padded tree. Global scratch/barriers
are explicit; no claim that these launches implement a Turing shared/RF design.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import hdc_golden_v41 as golden
from hdc_golden import add, mul, to_bf16

ROWS, K, THREADS, SMS = 24, 20480, 128, 32
CHUNKS, PAD = K // 8, 4096


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate(w, x):
    if w.shape != (ROWS, K) or x.shape != (K,):
        raise ValueError("normative HC shape is 24 x 20480")
    if w.dtype != np.float32 or x.dtype != np.float32:
        raise ValueError("F32 coefficients and F32 container for BF16 activation required")
    if not np.isfinite(w).all() or not np.isfinite(x).all():
        raise ValueError("finite fixture required")
    if not np.array_equal(x.view(np.uint32), to_bf16(x).view(np.uint32)):
        raise ValueError("activation must already be golden BF16-rounded")


def reference(w, x):
    validate(w, x)
    return golden.csum(mul(w, x[None, :]))


def contract():
    return {
        "modeled_sms": SMS, "modeled_fp32_lanes_per_sm": THREADS,
        "software_threads_per_block": THREADS, "warps_per_block": 4,
        "coefficient_bytes": ROWS * K * 4, "activation_bytes": K * 2,
        "activation_F32_container_bytes": K * 4,
        "chunk_programs": ROWS * PAD // THREADS,
        "valid_chunk_programs": ROWS * CHUNKS // THREADS,
        "padded_chunks_per_row": PAD, "tree_passes": 12,
        "global_scratch_bytes": ROWS * (PAD + PAD // 2) * 4,
        "logical_chunk_lane_live_F32": ["coefficient", "activation", "product", "accumulator"],
        "logical_chunk_lane_live_integer": ["chunk", "row", "element address"],
        "shared_memory_bytes_in_this_software_lowering": 0,
        "barrier": "same CUDA stream launch boundary between every tree pass",
        "RF_allocation_and_ports_qualified": False,
        "SM_schedule_latency_and_routes_qualified": False,
        "coefficient_staging": "F32 global memory; explicit loads, no resident/shared fit claim",
        "Turing_request": "Price four-warps/128-lanes chunk ownership on 32 SMs, actual RF allocation/ports, coefficient and activation load/coalescing cost, tree traffic/barriers and shared staging alternatives. No free overlap or dedicated HCP.",
        "full_token_rate": None, "hardware_adopted": False,
    }


def kernels():
    import triton
    import triton.language as tl

    @triton.jit
    def rn_mul(a, b):
        y = tl.inline_asm_elementwise("mul.rn.f32 $0, $1, $2;", "=f,f,f", [a, b], dtype=tl.float32, is_pure=True, pack=1)
        return tl.where(y == 0.0, 0.0, y)

    @triton.jit
    def rn_add(a, b):
        y = tl.inline_asm_elementwise("add.rn.f32 $0, $1, $2;", "=f,f,f", [a, b], dtype=tl.float32, is_pure=True, pack=1)
        return tl.where(y == 0.0, 0.0, y)

    @triton.jit
    def chunk(W, X, C, KK: tl.constexpr, PP: tl.constexpr, NN: tl.constexpr, BB: tl.constexpr):
        q = tl.program_id(0) * BB + tl.arange(0, BB)
        row, leaf = q // PP, q % PP
        active = (row < NN) & (leaf < KK // 8)
        acc = tl.full((BB,), 0.0, tl.float32)
        for j in tl.static_range(8):
            ix = leaf * 8 + j
            a = tl.load(W + row * KK + ix, active, other=0.0)
            b = tl.load(X + ix, active, other=0.0)
            acc = rn_add(acc, rn_mul(a, b))
        tl.store(C + q, acc, q < NN * PP)

    @triton.jit
    def pair(A, B, WIDTH: tl.constexpr, NN: tl.constexpr, BB: tl.constexpr):
        q = tl.program_id(0) * BB + tl.arange(0, BB)
        ix = (q // (WIDTH // 2)) * WIDTH + (q % (WIDTH // 2)) * 2
        mask = q < NN * (WIDTH // 2)
        a = tl.load(A + ix, mask, other=0.0)
        b = tl.load(A + ix + 1, mask, other=0.0)
        tl.store(B + q, rn_add(a, b), mask)
    return chunk, pair


def gpu(w, x):
    validate(w, x)
    import torch
    import triton
    chunk, pair = kernels()
    wg, xg = torch.from_numpy(w).cuda(), torch.from_numpy(x).cuda()
    a = torch.empty((ROWS * PAD,), device="cuda", dtype=torch.float32)
    b = torch.empty((ROWS * PAD // 2,), device="cuda", dtype=torch.float32)
    compiled = [chunk[(ROWS * PAD // THREADS,)](wg, xg, a, K, PAD, ROWS, THREADS, num_warps=4, enable_fp_fusion=False)]
    width = PAD
    while width > 1:
        compiled.append(pair[(triton.cdiv(ROWS * (width // 2), THREADS),)](a, b, width, ROWS, THREADS, num_warps=4, enable_fp_fusion=False))
        a, b = b, a
        width //= 2
    result = a[:ROWS].cpu().numpy()
    ptx = "\n".join(c.asm["ptx"] for c in compiled)
    if "fma.rn.f32" in ptx or "mma.sync" in ptx or "add.ftz" in ptx or "mul.ftz" in ptx:
        raise RuntimeError("PTX violates separate gradual-underflow F32 arithmetic")
    return result, ptx, [{"registers": c.n_regs, "shared_bytes": c.metadata.shared} for c in compiled]


def controls():
    rng = np.random.default_rng(190032)
    w = rng.normal(size=(ROWS, K)).astype(np.float32)
    x = to_bf16(rng.normal(size=K).astype(np.float32))
    yield "seeded_full_shape", w, x
    w = np.zeros((ROWS, K), np.float32)
    x = np.ones(K, np.float32)
    w[:, [0, 8, 16, 24]] = [2**25, 1, -(2**25), 1]
    yield "tree_order_cancellation", w, x
    w = np.zeros((ROWS, K), np.float32)
    x = np.ones(K, np.float32)
    x[1] = np.float32(1 - 2**-8)
    w[:, 1] = np.float32(1 + 2**-23)
    w[:, 0] = -mul(w[:, 1], x[1])
    yield "separate_product_FMA_witness", w, x
    w = np.zeros((ROWS, K), np.float32)
    x = np.ones(K, np.float32)
    w[:, 0] = np.nextafter(np.float32(0), np.float32(1))
    w[:, 1] = -0.0
    yield "gradual_underflow_signed_zero", w, x


def checkpoint_fixtures(snapshot):
    from safetensors import safe_open
    index_path = snapshot / "model.safetensors.index.json"
    index = json.loads(index_path.read_text())["weight_map"]
    for suffix in ["layers.0.hc_attn_fn", "layers.39.hc_ffn_fn"]:
        name = next(n for n in index if n.endswith(suffix))
        shard = snapshot / index[name]
        with safe_open(str(shard), framework="np") as f:
            w = f.get_tensor(name).copy()
        if w.dtype != np.float32:
            raise ValueError("checkpoint HC coefficients must actually be F32")
        rng = np.random.default_rng(190032)
        x = to_bf16(rng.normal(size=K).astype(np.float32))
        yield name, w, x, {"snapshot": str(snapshot), "shard": str(shard.resolve()), "index_sha256": sha(index_path.read_bytes()), "tensor": name, "tensor_sha256": sha(w.tobytes()), "activation_origin": "seeded synthetic BF16; not a measured model activation"}


def run(out, snapshot):
    import torch
    import triton
    out.mkdir(parents=True, exist_ok=False)
    repo = Path(__file__).resolve().parents[1]
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).strip():
        raise RuntimeError("run requires clean committed source checkout")
    records = []
    fixtures = [(n, w, x, {"origin": "synthetic control"}) for n, w, x in controls()]
    if snapshot:
        fixtures += list(checkpoint_fixtures(snapshot))
    for i, (name, w, x, provenance) in enumerate(fixtures):
        ref = reference(w, x)
        got, ptx, resources = gpu(w, x)
        diff = int(np.count_nonzero(ref.view(np.uint32) != got.view(np.uint32)))
        # Negative controls are evidence of sensitivity, not alternative criteria.
        bf16 = reference(to_bf16(w), x)
        products = mul(w, x[None, :]).reshape(ROWS, CHUNKS, 8)
        chunks = np.zeros((ROWS, CHUNKS), np.float32)
        for j in range(8):
            chunks = add(chunks, products[:, :, j])
        serial = np.zeros(ROWS, np.float32)
        for j in range(CHUNKS):
            serial = add(serial, chunks[:, j])
        fma_diff = None
        if name == "separate_product_FMA_witness":
            lib = ctypes.CDLL("libm.so.6")
            lib.fmaf.argtypes = [ctypes.c_float] * 3
            lib.fmaf.restype = ctypes.c_float
            fused = np.float32(lib.fmaf(float(w[0, 1]), float(x[1]), float(w[0, 0])))
            fma_diff = int(fused.view(np.uint32) != ref[0].view(np.uint32))
        np.savez_compressed(out / f"fixture_{i}.npz", coefficients=w, activation=x, golden=ref, gpu=got)
        (out / f"fixture_{i}.ptx").write_text(ptx)
        records.append({"name": name, "shape": list(w.shape), "provenance": provenance, "coefficient_sha256": sha(w.tobytes()), "activation_sha256": sha(x.tobytes()), "mismatched_F32_bits": diff, "BF16_coefficient_mutation_differences": int(np.count_nonzero(bf16.view(np.uint32) != ref.view(np.uint32))), "sequential_chunk_mutation_differences": int(np.count_nonzero(serial.view(np.uint32) != ref.view(np.uint32))), "FMA_mutation_difference": fma_diff, "compiled_resources_per_pass": resources})
    sensitivity = any(r["BF16_coefficient_mutation_differences"] for r in records) and any(r["sequential_chunk_mutation_differences"] for r in records) and any(r["FMA_mutation_difference"] for r in records)
    report = {"schema": "opentallas.w19.hc-simd-exact-software.v1", "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(), "source_pins": {str(p.relative_to(repo)): sha(p.read_bytes()) for p in [Path(__file__).resolve(), repo / "tools/hdc_golden.py", repo / "tools/hdc_golden_v41.py"]}, "device": torch.cuda.get_device_name(), "torch": torch.__version__, "triton": triton.__version__, "contract": contract(), "fixtures": records, "negative_controls_sensitive": sensitivity, "verdict": "PASS" if sensitivity and all(r["mismatched_F32_bits"] == 0 for r in records) else "FAIL", "scope": "HC full-F32 coefficient dot only; not full HC sigmoid/Sinkhorn or deployment HC activation attribution; Blackwell software witness, Turing analytical mapping remains unqualified", "artifacts": {p.name: sha(p.read_bytes()) for p in sorted(out.iterdir())}}
    (out / "proof.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"verdict": report["verdict"], "fixtures": len(records), "report": str(out / "proof.json")}))
    return report["verdict"] == "PASS"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--snapshot", type=Path)
    args = ap.parse_args()
    raise SystemExit(0 if run(args.out, args.snapshot) else 1)
