"""Checks of tools/qwen3_deployment_quality.py, the full-model quality emulation
of the Qwen3-8B deployment arithmetic.

The load-bearing check is the last one: the GPU contract forward (Triton
chunk + pairwise-tree kernel, eager FP32 golden primitives, batched prefill)
reproduces the numpy golden (tools/hdc_golden.py at 45762e32, sequential
decode steps) bit-exactly in every logit of the reduced Qwen3 vehicle.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

torch = pytest.importorskip("torch")
Q = pytest.importorskip("qwen3_deployment_quality")

GOLDEN_COMMIT = "45762e32"          # vector-core golden (FP8 KV, norm fold) + reciprocal saturation
GOLDEN_BLOB = "657d916762bc39c68124388f1dd74d302c8bf059"   # blob hash of that tools/hdc_golden.py
REDUCED = Path("/home/ubuntu/OpenTallas/build/models/qwen3-reduced-v1")
CUDA = torch.cuda.is_available()


def golden_module(tmp_path):
    try:
        src = subprocess.run(["git", "show", f"{GOLDEN_COMMIT}:tools/hdc_golden.py"], cwd=ROOT,
                             capture_output=True, check=True, text=True).stdout
    except Exception:
        pytest.skip(f"golden {GOLDEN_COMMIT} not in this clone")
    import hashlib
    blob = src.encode()
    assert hashlib.sha1(b"blob %d\0" % len(blob) + blob).hexdigest() == GOLDEN_BLOB
    p = tmp_path / "hdc_golden_fp8kv.py"
    p.write_text(src)
    spec = importlib.util.spec_from_file_location("hdc_golden_fp8kv", p)
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    return g


def test_split_for_matches_golden_and_spec_chunks():
    sys.path.insert(0, str(ROOT / "tools"))
    import hdc_golden
    shapes = {"qkv": (6144, 4096, 8), "o": (4096, 4096, 16), "gate_up": (24576, 4096, 32),
              "down": (4096, 12288, 48), "lm_head": (151936, 4096, 2)}
    for n, k, chunk in shapes.values():
        s = Q.split_for(n, k, Q.SPEC_GROUPS)
        assert s == hdc_golden.split_for(n, k, Q.SPEC_GROUPS)
        assert k // s == chunk
    assert Q.attn_splits(128, Q.SPEC_GROUPS) == (128, 1024)


def test_to_fp8_matches_golden(tmp_path):
    g = golden_module(tmp_path)
    rng = np.random.default_rng(0)
    x = np.concatenate([rng.standard_normal(200000) * s for s in (1e-4, 1e-2, 1, 30, 300, 1e4)]).astype(np.float32)
    x = np.concatenate([x, np.float32([0.0, -0.0, 448.0, 464.0, 470.0, -500.0, 2.0 ** -9, 2.0 ** -10, 3 * 2.0 ** -11])])
    ref = g.to_fp8(x)
    got = Q.to_fp8(torch.from_numpy(x)).numpy()
    assert np.array_equal(ref.view(np.uint32), got.view(np.uint32))


@pytest.mark.parametrize("S", [1, 2, 8, 64])
def test_chunk_tree_dot_matches_golden_matvec(tmp_path, S):
    g = golden_module(tmp_path)
    rng = np.random.default_rng(S)
    K, N, T = 128, 40, 3
    w = g.to_bf16(rng.standard_normal((N, K)).astype(np.float32))
    x = g.to_bf16(rng.standard_normal((T, K)).astype(np.float32))
    dev = "cuda" if CUDA else "cpu"
    got = Q.chunk_tree_dot(torch.from_numpy(x).to(dev), torch.from_numpy(w).to(dev).to(torch.bfloat16), S).cpu().numpy()
    for t in range(T):
        ref = g.matvec(w, x[t], S)
        assert np.array_equal(ref.view(np.uint32), got[t].view(np.uint32))
    # interleaved split (the attention products)
    idx, M = Q.interleave_perm(K, S, dev)
    xp = Q.gather_pad(torch.from_numpy(x).to(dev), idx, K, 1)
    wp = Q.gather_pad(torch.from_numpy(w).to(dev), idx, K, 1)
    got = Q.chunk_tree_dot(xp, wp, S).cpu().numpy()
    for t in range(T):
        ref = g.matvec_il(w, x[t], S)
        assert np.array_equal(ref.view(np.uint32), got[t].view(np.uint32))


def test_quantizer_bits_and_codes():
    torch.manual_seed(0)
    w = (torch.randn(256, 1024) * 0.02).to(torch.bfloat16)
    for fmt, bits in (("q35", 3.5), ("w4", 4.125), ("w3", 3.125)):
        codes, scales, b = Q.quantize(w, fmt)
        assert abs(b - bits) < 1e-3
        lo, hi, _, g = Q.QFORMATS[fmt]
        assert int(codes.min()) >= -(2 ** (hi - 1)) and int(codes.max()) <= 2 ** (hi - 1) - 1
        err = (Q.dequant(codes, scales) - w.float()).pow(2).mean().item()
        assert err < w.float().pow(2).mean().item() * 0.1


@pytest.mark.skipif(not CUDA or not REDUCED.exists(), reason="needs CUDA and the reduced Qwen3 checkpoint")
@pytest.mark.parametrize("groups,kv", [(4, "fp8"), (64, "bf16"), (8192, "fp8")])
def test_contract_forward_bit_exact_vs_golden_reduced(tmp_path, groups, kv):
    g = golden_module(tmp_path)
    g.CHECKPOINT = REDUCED / "model-00001-of-00001.safetensors"
    g.CONFIG = ROOT / "compiler/models/qwen3-reduced-v1/config.json"
    g.KV_FMT = kv
    gm = g.Model(groups)
    m = Q.Qwen3(REDUCED, "contract", "bf16", kv, groups=groups)
    toks = [91, 17, 300, 1200, 5, 77, 3000, 12, 4000, 1, 2, 3, 999, 1500]
    cache = [[] for _ in range(gm.layers)]
    ref = [gm.decode_token(t, p, cache) for p, t in enumerate(toks)]
    m.prefill_chunk = 4                                      # blocked prefill on a growing cache
    c = m.new_cache(1, 32)
    h = torch.cat([m.forward(torch.tensor(toks[:6], device="cuda"), c),     # batched prefill
                   m.forward(torch.tensor(toks[6:7], device="cuda"), c),    # one decode step
                   m.forward(torch.tensor(toks[7:], device="cuda"), c)])    # prefill on a cache
    lg = m.logits(h).cpu().numpy()
    for p in range(len(toks)):
        assert np.array_equal(lg[p].view(np.uint32), ref[p].view(np.uint32)), f"position {p}"


@pytest.mark.skipif(not CUDA or not REDUCED.exists(), reason="needs CUDA and the reduced Qwen3 checkpoint")
def test_batched_decode_equals_single_sequence(tmp_path):
    """Sequences of different lengths decoded together give each sequence's own bits."""
    m = Q.Qwen3(REDUCED, "contract", "bf16", "fp8", groups=64)
    prompts = [torch.tensor([91, 17, 300, 1200, 5]), torch.tensor([91, 4000, 2]), torch.tensor([7] * 11)]
    both = Q.greedy_batch(m, prompts, 6, batched=True)
    alone = Q.greedy_batch(m, prompts, 6, batched=False)
    for a, b in zip(both, alone):
        assert a["tokens"] == b["tokens"]
        assert a["margins"] == b["margins"]


def test_gptq_beats_rtn_on_correlated_inputs():
    """GPTQ codes keep the format (ranges, bits) and cut the output error below RTN's."""
    torch.manual_seed(1)
    N, K, T = 64, 256, 2048
    w = (torch.randn(N, K) * 0.02).to(torch.bfloat16)
    mix = torch.randn(K, K) / K ** 0.5 + torch.eye(K)
    x = torch.randn(T, K) @ mix
    H = 2 * x.t() @ x / T
    for fmt in ("q35", "w3"):
        codes, scales, bits = Q._gptq_matrix(w, H, fmt)
        lo, hi, _, _ = Q.QFORMATS[fmt]
        assert abs(bits - Q.quantize(w, fmt)[2]) < 1e-3
        assert int(codes.min()) >= -(2 ** (hi - 1)) and int(codes.max()) <= 2 ** (hi - 1) - 1
        e_gptq = (x @ (Q.dequant(codes, scales) - w.float()).t()).pow(2).mean()
        c2, s2, _ = Q.quantize(w, fmt)
        e_rtn = (x @ (Q.dequant(c2, s2) - w.float()).t()).pow(2).mean()
        assert e_gptq < 0.8 * e_rtn


def test_reciprocal_saturation_matches_golden(tmp_path):
    """RECIP_SAT equals the golden's saturated reciprocal and SiLU at the extremes."""
    g = golden_module(tmp_path)
    d = np.float32([1.0, 3.0, 1.6e38, 1.6158e38, 1.6159e38, 1.7e38, 3.4e38, 2.0 ** -120])
    got = Q.reciprocal_g(torch.from_numpy(d)).numpy()
    assert np.array_equal(g.reciprocal(d).view(np.uint32), got.view(np.uint32))
    x = np.float32([-200.0, -90.0, -88.0, -87.98, -87.9, -10.0, 0.0, 3.0, 90.0])
    got = Q.silu_g(torch.from_numpy(x)).numpy()
    ref = g.silu(x)
    assert np.isfinite(got).all() and np.array_equal(ref.view(np.uint32), got.view(np.uint32))
