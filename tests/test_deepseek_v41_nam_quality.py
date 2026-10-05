"""tools/deepseek_v41_nam_quality.py: the GPU engine of the norm-after-matvec variant (b_nam) is the golden's
opt-in HDC_V41_FUSE=nfold bit for bit, its unfolded form is the deployment contract (b) bit for bit, and the
committed record is consistent with the pre-registered rule and the stability rule.

GPU tests skip without CUDA/Triton or the reduced V4.1 vehicle (build/models/deepseek-v4.1-flash-reduced-v2,
or $OPENTALLAS_BUILD)."""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
RECORD = ROOT / "results/quality/deepseek_v41_flash_norm_after_matvec.json"

torch = pytest.importorskip("torch")
cuda = pytest.mark.skipif(not torch.cuda.is_available(), reason="needs a CUDA GPU")


def _reduced():
    build = Path(os.environ.get("OPENTALLAS_BUILD", ROOT / "build"))
    snap = build / "models/deepseek-v4.1-flash-reduced-v2"
    if not (snap / "model-00001-of-00001.safetensors").exists():
        pytest.skip("reduced V4.1 vehicle not built")
    import deepseek_v41_deployment_quality as Q
    if not (Q.SNAPSHOT / "inference/model.py").exists():
        pytest.skip("release inference code not in the Hugging Face cache")
    return snap


def _golden_logits(snap, toks, fuse):
    import hdc_golden_v41 as GV
    arith, old = GV.ARITH, set(GV.FUSE)
    try:
        GV.set_arith("chunk8")
        GV.set_fuse(fuse)
        m = GV.Model(checkpoint=snap / "model-00001-of-00001.safetensors")
        return np.stack(m.forward_positions(toks, 0, m.new_state()))
    finally:
        GV.set_arith(arith)
        GV.set_fuse(old)


@cuda
@pytest.mark.parametrize("fold,fuse", [(True, "nfold,osm"), (False, "osm")])
def test_engine_is_bit_exact_with_the_golden_on_the_reduced_vehicle(fold, fuse):
    """Every logit of every position of a 40-token sequence (compressed KV, index selection, both Engram
    layers, routing) equals hdc_golden_v41 under HDC_V41_ARITH=chunk8 and HDC_V41_FUSE=fuse."""
    snap = _reduced()
    import deepseek_v41_nam_quality as N
    toks = [0] + np.random.default_rng(1).integers(3, 4000, 39).tolist()
    lc, eng = N.model_logits(snap, [toks], fold)
    assert np.array_equal(lc[0].cpu().numpy(), _golden_logits(snap, toks, fuse))


@cuda
def test_fold_moves_the_fp8_rounding_and_nothing_else():
    """On one quantised linear: nfold differs from the contract only through the FP8 rounding of
    gamma*x vs gamma*x*rstd -- with an exactly representable power-of-two rstd the two are identical."""
    import deepseek_v41_deployment_quality as Q
    import deepseek_v41_nam_quality as N
    gen = torch.Generator().manual_seed(0)
    M, K, Nn = 9, 256, 48
    codes = torch.randint(0, 256, (Nn, K), dtype=torch.uint8, generator=gen)
    codes[(codes & 0x7F) == 0x7F] = 0
    sc = torch.full((Nn // 32 + 1, K // 32), 120, dtype=torch.uint8)
    qw = Q.QW.from_fp8(codes.view(torch.float8_e4m3fn).cuda(), sc.view(torch.float8_e8m0fnu).cuda()
                       if hasattr(torch, "float8_e8m0fnu") else sc.cuda())
    g = (torch.rand(K, generator=gen) + 0.5).cuda()
    x = (torch.randn(M, K, generator=gen) * 3).bfloat16().float().cuda()
    cfg = type("C", (), {"eps": Q.f32c(1e-6)})()
    e0, e1 = N.NamEngine.__new__(N.NamEngine), N.NamEngine.__new__(N.NamEngine)
    for e, f in ((e0, False), (e1, True)):
        Q.Engine.__init__(e, cfg, True)
        e.fold, e.instrument, e.stats, e.sites, e.pos, e.probe_n = f, False, N.Stats(), {}, None, 0
    # a row whose mean square makes rstd an exact power of two: x = 2^k * (+-1)
    x[0] = torch.where(x[0] >= 0, 4.0, -4.0)
    y0 = e0.linq(qw, e0.rmsnorm_fold(x, g, "t"))
    y1 = e1.linq(qw, e1.rmsnorm_fold(x, g, "t"))
    assert torch.equal(y0[0], y1[0])
    assert not torch.equal(y0[1:], y1[1:])                      # elsewhere the rounding moves
    rel = ((y0 - y1).norm(dim=-1) / y0.norm(dim=-1)).max().item()
    assert rel < 0.1


def test_record_is_consistent_with_its_rules():
    if not RECORD.exists():
        pytest.skip("no record")
    rec = json.loads(RECORD.read_text())
    import deepseek_v41_deployment_quality as Q
    assert rec["threshold"] == Q.THRESHOLD
    v = rec["verdict"]
    assert v["quality"]["acceptable"] == (v["quality"]["ppl_ok"] and v["quality"]["mmlu_ok"])
    s = v["stability"]
    assert s["pass"] == all(c["pass"] for c in s["criteria"].values())
    assert v["adopt"] == (v["quality"]["acceptable"] and s["pass"])
