"""tools/deepseek_v41_deployment_quality.py: the GPU emulation of the V4.1 deployment contract is the
golden's arithmetic bit for bit, and the committed record is consistent with its pre-registered rule.

GPU tests skip without CUDA/Triton; the whole-model comparison needs the reduced vehicle's checkpoint
(build/models/deepseek-v4.1-flash-reduced-v2, or $OPENTALLAS_BUILD) and the release's inference code in
the Hugging Face cache (for the vendor path and the Engram hash).
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
RECORD = ROOT / "results/quality/deepseek_v41_flash_deployment_arithmetic.json"

torch = pytest.importorskip("torch")
cuda = pytest.mark.skipif(not torch.cuda.is_available(), reason="needs a CUDA GPU")


def _mods():
    import deepseek_v41_deployment_quality as Q
    import hdc_golden as G
    import hdc_golden_v41 as GV
    return Q, G, GV


def _e4m3(shape, gen):
    b = torch.randint(0, 256, shape, dtype=torch.uint8, generator=gen)
    v = b.view(torch.float8_e4m3fn).float()
    v[torch.isnan(v)] = 0
    return v


@cuda
def test_block_dot_kernel_is_exact_and_chunked():
    """FP8 x FP8 and FP8 x FP4 block dots over the full E4M3 range, exact then rounded once, scaled,
    blocks by the chunk-8 tree: equal to the float64 dot and hdc_golden_v41.csum -- with the weight
    given as code values, as raw E4M3 bytes, and as packed E2M1 bytes."""
    Q, G, GV = _mods()
    gen = torch.Generator().manual_seed(0)
    M, N, K = 37, 70, 32 * 21
    x = _e4m3((M, K), gen)
    xe = torch.randint(-20, 5, (M, K // 32), dtype=torch.int32, generator=gen)
    we = torch.randint(-15, -2, (N, K // 32), dtype=torch.int32, generator=gen)
    w8b = torch.randint(0, 256, (N, K), dtype=torch.uint8, generator=gen)
    w8b[(w8b & 0x7F) == 0x7F] = 0                       # no NaN codes
    w4b = torch.randint(0, 256, (N, K // 2), dtype=torch.uint8, generator=gen)
    cases = [(w8b.view(torch.float8_e4m3fn).float(), Q.QW(w8b.t().contiguous().cuda(), we.t().contiguous().cuda(), N, K, 1)),
             (Q.fp4_values(w4b), Q.QW(w4b.t().contiguous().cuda(), we.t().contiguous().cuda(), N, K, 2))]
    cases.append((cases[0][0], Q.QW.from_values(cases[0][0].cuda(), we.cuda())))
    for w, qw in cases:
        assert torch.equal(qw.values_T().cpu(), w.t())
        got = Q.tree_t(Q.qdot_chunks(x.cuda(), xe.cuda(), qw)).cpu().numpy()
        blk = torch.einsum("mbk,nbk->mnb", x.double().view(M, -1, 32), w.double().view(N, -1, 32)).float()
        blk = np.ldexp(blk.numpy(), (xe[:, None, :] + we[None, :, :]).numpy())
        assert np.array_equal(got, GV.csum(blk, axis=-1))
    # the golden's E2M1 decoding (low nibble first) is the same table
    ref = GV.E2M1[np.stack([w4b.numpy() & 15, w4b.numpy() >> 4], -1).reshape(N, K)]
    assert np.array_equal(Q.fp4_values(w4b).numpy(), ref)


@cuda
@pytest.mark.parametrize("T,N,K,exact", [(5, 7, 5120, True), (64, 130, 512, True), (3, 24, 640, False),
                                          (70, 33, 100, True)])
def test_csum_kernel_matches_golden_csum(T, N, K, exact):
    Q, G, GV = _mods()
    gen = torch.Generator().manual_seed(T + N + K)
    x = torch.randn(T, K, generator=gen).bfloat16().float()
    w = torch.randn(N, K, generator=gen)
    if exact:
        w = w.bfloat16().float()
    got = Q.csum_mm(x.cuda(), w.cuda(), exact=exact)[0].cpu().numpy()
    assert np.array_equal(got, GV.csum(GV.mul(w.numpy()[None], x.numpy()[:, None]), axis=-1))


@cuda
def test_special_functions_and_quantisers_match_golden():
    Q, G, GV = _mods()
    gen = torch.Generator().manual_seed(1)
    v = torch.randn(100000, generator=gen) * 30
    d = v.cuda()
    assert np.array_equal(Q.exp_g(d).cpu().numpy(), G.exp(v.numpy()))
    assert np.array_equal(Q.rsqrt_g(d.abs() + 1e-3).cpu().numpy(), G.rsqrt(v.abs().numpy() + np.float32(1e-3)))
    assert np.array_equal(Q.softplus_g(d).cpu().numpy(), GV.softplus(v.numpy()))
    assert np.array_equal(Q.sigmoid_g(d).cpu().numpy(), GV.sigmoid(v.numpy()))
    assert np.array_equal(Q.silu_g(d).cpu().numpy(), GV.silu(v.numpy()))
    x = (torch.randn(64, 256, generator=gen) * torch.exp(torch.randn(64, 256, generator=gen) * 3)).bfloat16().float()
    flat = x.numpy().reshape(-1)
    assert np.array_equal(Q.qdq_fp8(x.cuda()).cpu().numpy().reshape(-1), GV.qdq_fp8(flat))
    assert np.array_equal(Q.qdq_fp4_e8m0(x.cuda()).cpu().numpy().reshape(-1), GV.qdq_fp4_e8m0(flat))
    assert np.array_equal(Q.qdq_fp4_e4m3(x.cuda(), 16).cpu().numpy().reshape(-1), GV.qdq_fp4_e4m3(flat, 16))
    # the deployed KV formats dequantise to BF16-exact values: storing codes + scales is value-identical
    for f in (Q.qdq_fp8(x.cuda()), Q.qdq_fp4_e8m0(x.cuda()), Q.qdq_fp4_e4m3(x.cuda(), 16)):
        assert torch.equal(Q.to_bf16(f), f)


def _reduced():
    build = Path(os.environ.get("OPENTALLAS_BUILD", ROOT / "build"))
    snap = build / "models/deepseek-v4.1-flash-reduced-v2"
    if not (snap / "model-00001-of-00001.safetensors").exists():
        pytest.skip("reduced V4.1 vehicle not built")
    Q, _, _ = _mods()
    if not (Q.SNAPSHOT / "inference/model.py").exists():
        pytest.skip("release inference code not in the Hugging Face cache")
    return snap


@cuda
def test_contract_engine_is_bit_exact_with_the_golden_on_the_reduced_vehicle():
    """Every logit of every position of a 40-token sequence (compressed KV, index selection, the
    online-softmax blocks, both Engram layers, 40 layers of routing) equals hdc_golden_v41 under
    HDC_V41_ARITH=chunk8, HDC_V41_FUSE=osm."""
    snap = _reduced()
    Q, _, GV = _mods()
    rng = np.random.default_rng(1)
    toks = [0] + rng.integers(3, 4000, 39).tolist()
    lc, _ = Q.model_logits(snap, [toks], "contract")
    arith, fuse = GV.ARITH, set(GV.FUSE)
    try:
        GV.set_arith("chunk8")
        GV.set_fuse("osm")
        m = GV.Model(checkpoint=snap / "model-00001-of-00001.safetensors")
        gl = np.stack(m.forward_positions(toks, 0, m.new_state()))
    finally:
        GV.set_arith(arith)
        GV.set_fuse(fuse)
    assert np.array_equal(lc[0].cpu().numpy(), gl)


@cuda
def test_three_arithmetics_agree_layer_by_layer_on_the_reduced_vehicle():
    """vendor (a), contract (b) and the torch re-implementation (a2) compute the same layer: fed the
    vendor's own input at each of the first 16 layers (teacher-forced), their outputs agree to about
    one BF16 ulp and almost every token routes to the same experts.  (Free-running comparisons on
    the reduced vehicle are meaningless: its random router picks 6 of 12 experts at near-ties.)"""
    snap = _reduced()
    Q, _, _ = _mods()
    dev = torch.device("cuda")
    cfg, ck, tok = Q.Cfg(snap), Q.Checkpoint(snap), Q.tokenizer_for(snap)
    T, B = 40, 1
    toks = [0] + np.random.default_rng(3).integers(3, cfg.vocab - 1, T - 1).tolist()
    vend = Q.Vendor(snap, B, T)
    hashes = torch.stack(vend.hashes(tok, [toks]))
    h = ck.get("embed.weight").to(dev)[torch.tensor([toks], device=dev)][:, :, None, :].repeat(1, 1, cfg.hc, 1)
    pre = torch.zeros(B, T, cfg.hc, device=dev)
    pre[..., 0] = 1
    engs = {k: Q.Engine(cfg, k == "contract") for k in ("contract", "torch")}
    sts = {k: Q.new_state(cfg, B, T, dev) for k in engs}
    sh, flips, tokens = {}, {k: 0 for k in engs}, 0
    for L in range(16):
        blk = vend.block(L, ck)
        W, ex = Q.contract_weights(cfg, blk, ck, L, dev)
        er = Q.engram_rows(ck, cfg, L, hashes[:, :, cfg.engram_layers.index(L), :], dev) \
            if L in cfg.engram_layers else None
        tra = {}
        ha, pa = vend.run(blk, h, pre, sh, er, tra)
        for k, e in engs.items():
            tr = {}
            hk, _ = e.layer(L, W, ex, h.reshape(B * T, cfg.hc, -1).float(), pre.reshape(B * T, cfg.hc), sts[k],
                            B, T, er.reshape(B * T, -1).float() if er is not None else None, tr)
            f = (torch.sort(tr["router"], -1).values != torch.sort(tra["router"].reshape(B * T, -1), -1).values)
            same = ~f.any(-1)
            flips[k] += int((~same).sum())
            d = (hk.reshape(B * T, -1) - ha.reshape(B * T, -1).float())[same]
            rel = (d.norm() / ha.reshape(B * T, -1).float()[same].norm()).item()
            assert rel < 0.02, (L, k, rel)       # tokens that route alike agree to BF16 rounding
        tokens += B * T
        h, pre = ha, pa
    for k in engs:
        assert flips[k] <= 0.05 * tokens, (k, flips[k], tokens)


def test_record_is_consistent_with_its_preregistered_rule():
    if not RECORD.exists():
        pytest.skip("no record")
    rec = json.loads(RECORD.read_text())
    Q, _, _ = _mods()
    assert rec["threshold"] == Q.THRESHOLD
    s = rec["summary"]["modes"]
    b = s["b"]
    ok_ppl = b["wikitext2"]["rel_delta_ppl"] <= rec["threshold"]["ppl_rel_max"]
    ok_mmlu = ("mmlu" not in b) or (-b["mmlu"]["delta_pt"] <= rec["threshold"]["mmlu_drop_max_pt"])
    assert rec["verdict"]["acceptable"] == (ok_ppl and ok_mmlu)
    for m, d in s.items():
        w = d["wikitext2"]
        lo, hi = w["rel_delta_ppl_ci95"]
        assert lo - 1e-12 <= w["rel_delta_ppl"] <= hi + 1e-12 or m == "a"
    assert s["a"]["wikitext2"]["top1_agree_vs_ref"] == 1.0
    assert len(rec["layers"]) == 40
