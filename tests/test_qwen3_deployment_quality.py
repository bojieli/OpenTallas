"""Checks of tools/qwen3_deployment_quality.py, the full-model quality emulation
of the Qwen3-8B deployment arithmetic.

The load-bearing check is the last one: the GPU contract forward (Triton
chunk + pairwise-tree kernel, eager FP32 golden primitives, batched prefill)
reproduces the numpy golden (tools/hdc_golden.py at 45762e32, sequential
decode steps) bit-exactly in every logit of the reduced Qwen3 vehicle.
"""
import importlib.util
import json
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


# -- the O4 INT8 per-channel contract (w8; docs/ARCH_QWEN3_O4_RTL_SPEC.md section 3.1, gap G14) ----------------
O4_ROWS = 192                     # rows a matrix in the spec's check (tools/qwen3_o4_rtl_gaps.numerics)
O4_FULL_N = {"qkv(q)": 3072, "o": 4096, "gate_up(gate)": 12288, "down": 4096, "lm_head": 75968}


def _bf16_rne(x):
    """float32 -> the nearest BF16 (ties to even), as float32."""
    u = np.ascontiguousarray(x, dtype=np.float32).view(np.uint32).astype(np.uint64)
    u = (u + 0x7FFF + ((u >> 16) & 1)) & 0xFFFF0000
    return u.astype(np.uint32).view(np.float32)


def contract_reference(x, codes, s, S):
    """An independent numpy statement of C2 + C3, written from the contract text: bf16(x_k) x q_nk exactly in FP32;
    S contiguous chunks of K/S, each summed sequentially from +0 in FP32 RNE; the chunk sums added by the pairwise
    tree ((c0 + c1) + (c2 + c3)) + ...; then y_n = fl32(T_n x s_n), canonical +0.  y stays FP32."""
    xb = _bf16_rne(x)
    p = codes.astype(np.float32) * xb[None, :]
    assert np.array_equal(p.astype(np.float64), codes.astype(np.float64) * xb.astype(np.float64)[None, :])
    M = x.shape[0] // S
    acc = np.zeros((codes.shape[0], S), np.float32)
    for j in range(M):                      # element j of every chunk c (index c * M + j)
        acc = (acc + p[:, j::M]).astype(np.float32)
    while acc.shape[1] > 1:
        acc = (acc[:, 0::2] + acc[:, 1::2]).astype(np.float32)
    return (acc[:, 0] * s.astype(np.float32)).astype(np.float32) + np.float32(0.0)


def _w8_rows(real):
    import qwen3_o4_rtl_gaps as O
    if real:
        src = O._load_real(O4_ROWS, 0)
        if src is None:
            pytest.skip("the Qwen3-8B HF snapshot is not on disk")
        return O, src
    return O, O._synthetic(24, 0)


def _check_w8_rows(O, mats, xs, devices):
    """The harness's w8 path (quantize_w8, int8_mv_t) against the contract reference, and the spec's finding that the
    old scale-inside-the-product order differs: (rows, outputs differing from the reference, old-order differing)."""
    rows = diff = old = 0
    for key, w in mats.items():
        K = w.shape[1]
        x = xs[K]
        S = O.G.split_for(O4_FULL_N[key], K, O.GROUPS_DIE)
        codes, scales, bits = Q.quantize_w8(torch.from_numpy(np.ascontiguousarray(w, dtype=np.float32)))
        codes_np = codes.numpy()
        s_np = scales[:, 0].to(torch.float32).numpy()
        # the harness quantiser gives the spec's rows (the gaps tool's _rtn_mse): same codes and BF16 scales
        q_o4, s_o4 = O.quantize_rows(w, Q)
        assert np.array_equal(codes_np, q_o4) and np.array_equal(s_np, s_o4)
        assert codes.dtype == torch.int8 and int(codes.min()) >= -128 and int(codes.max()) <= 127
        assert np.array_equal(_bf16_rne(s_np), s_np) and bits == 8 + 16 / K
        ref = contract_reference(x, codes_np, s_np, S)
        # the reference is also the golden's matvec of the codes followed by one multiply (tools/qwen3_o4_rtl_gaps)
        assert np.array_equal(ref.view(np.uint32), O._bits(O.contract_mv(x, codes_np, s_np, S)[0]))
        for dev in devices:
            got = Q.int8_mv_t(torch.from_numpy(x)[None].to(dev), codes.t().contiguous().to(dev),
                              scales.t().contiguous().to(dev), S)[0].cpu().numpy()
            assert got.dtype == np.float32
            diff += int((got.view(np.uint32) != ref.view(np.uint32)).sum())
        old += int((O._bits(O.harness_per_mac(Q, x, codes_np, s_np, S)) != O._bits(ref)).sum())
        rows += w.shape[0]
    return rows, diff, old


def test_w8_contract_bit_exact_synthetic():
    O, (mats, xs, _) = _w8_rows(False)
    rows, diff, old = _check_w8_rows(O, mats, xs, ["cpu"] + (["cuda"] if CUDA else []))
    assert rows == 5 * 24 and diff == 0 and old > 0


def test_w8_contract_bit_exact_on_the_spec_960_rows():
    """The spec's comparison (section 3.2): 192 real Qwen3-8B rows of layer 0's q and gate (norm-folded), o and down
    (one die's K slice) and the lm_head, each die's K-split at 6,144 groups.  The old per-product order differs from
    the contract in 720 of the 960 outputs; the w8 mode differs in none, on the CPU and (when present) the GPU."""
    O, (mats, xs, _) = _w8_rows(True)
    rows, diff, old = _check_w8_rows(O, mats, xs, ["cpu"] + (["cuda"] if CUDA else []))
    rec = json.loads(O.OUT.read_text())["numerics"]
    assert rows == 960 == rec["rows_checked"]
    assert old == rec["harness_order_rows_differing"] == 720
    assert diff == 0


def test_w8_model_plumbing():
    """Qwen3._w / mv / embed_rows in the contract arithmetic: K-major codes and [1, N] scales, the post-sum scale
    (the norm fold's 1/rms follows it in the forward, C4), and the embedding row code x scale exactly (C5)."""
    m = object.__new__(Q.Qwen3)
    m.arith, m.wfmt, m.wfile, m.bits, m.groups, m.device = "contract", "w8", None, {}, 6144, torch.device("cpu")
    rng = np.random.default_rng(3)
    w = torch.from_numpy(rng.standard_normal((40, 512)).astype(np.float32) * 0.03).to(torch.bfloat16)
    W = m._w(w, "o", "0.o")
    assert W["post"] and tuple(W["q"].shape) == (512, 40) and tuple(W["s"].shape) == (1, 40)
    x = rng.standard_normal((3, 512)).astype(np.float32)
    got = m.mv(torch.from_numpy(x), W).numpy()
    codes, scales, _ = Q.quantize_w8(w)
    S = Q.split_for(40, 512, 6144)
    for t in range(3):
        ref = contract_reference(x[t], codes.numpy(), scales[:, 0].float().numpy(), S)
        assert np.array_equal(got[t].view(np.uint32), ref.view(np.uint32))
    emb = torch.from_numpy(rng.standard_normal((50, 64)).astype(np.float32) * 0.02).to(torch.bfloat16)
    m.embed_q, m.embed_s, _ = Q.quantize_w8(emb)
    toks = torch.tensor([[3, 49, 0]])
    e = m.embed_rows(toks).numpy()
    e64 = m.embed_q[toks].double().numpy() * m.embed_s[toks].double().numpy()
    assert np.array_equal(e.astype(np.float64), e64)
    assert {"b_w8", "g_contract_w8", "e_full_w8"} <= set(Q.MODES) and Q.MODES["e_full_w8"] == ("contract", "w8", "fp8")
