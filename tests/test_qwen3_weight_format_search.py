"""Checks of tools/qwen3_weight_format_search.py (ROM-shippable Qwen3-8B weight
formats): format accounting, the compute-in-ROM capacity rule, the quantisers, and
that the folded rotations leave the (unquantised) model unchanged."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

torch = pytest.importorskip("torch")
W = pytest.importorskip("qwen3_weight_format_search")
Q = W.Q
REDUCED = Path("/home/ubuntu/OpenTallas/build/models/qwen3-reduced-v1")
CUDA = torch.cuda.is_available()


def test_bits_and_cells_per_weight():
    f = W.Fmt("int3+int6@0.125:g128")
    assert f.bits() == pytest.approx(3 + 3 * 0.125 + 17 / 128)
    # INT3 and INT6 take one and two <=4-bit select cells; scale + flag at full cell width
    assert W.cells_per_weight(f) == pytest.approx(0.875 + 0.25 + 17 / 128 / 4)
    assert W.cells_per_weight(W.Fmt("int4:g128")) == pytest.approx(1 + 16 / 128 / 4)
    assert W.cells_per_weight(W.Fmt("lm4:g32")) == pytest.approx(1 + 16 / 32 / 4)
    assert W.cells_per_weight(W.Fmt("int5:g128")) == pytest.approx(2 + 16 / 128 / 4)
    assert W.cells_per_weight(W.Fmt("int4+int8@0.1:g128")) == pytest.approx(1.1 + 17 / 128 / 4)


def test_rom_capacity_reproduces_the_design_point():
    """HC1's 3.5-bit mixture (7/6 cells a weight, no scales) at the repository's N6
    cell density is the 261.98 mm2 target ROM of tools/arch_budget_qwen3.py."""
    r = W.rom_capacity(W.Fmt("int4:g128"))
    assert W.QWEN3_PARAMS * 7 / 6 / r["cell_density_per_mm2"] == pytest.approx(261.98, abs=0.01)
    assert r["fits_reticle"] and r["target_rom_mm2"] < 261.98
    assert not W.rom_capacity(W.Fmt("int5:g128"))["fits_reticle"]
    # The single-reticle capacity columns in the measured quality record are
    # historical counterfactuals.  Keep them pinned after O4's two-reticle
    # budget replaces arch_budget_qwen3.RETICLE.
    rec = json.loads((ROOT / "results/quality/qwen3_8b_weight_format_search.json").read_text())
    old = rec["modes"]["e8_int8sym_perchannel_postscale_rtn_contract_fp8"]["rom"]
    now = W.rom_capacity(W.Fmt("int8:g0").for_k(4096), bits_measured=old["bits_per_weight"])
    for field in ("target_rom_mm2", "drafter_rom_mm2_same_format", "pool_target_drafter_lanecopies_mm2",
                  "left_after_roms_mm2", "design_point_lane_multiplier_m"):
        assert now[field] == pytest.approx(old[field]), field


def test_codebook_levels():
    e = W.Elem("lm4")
    lv = e.levels_np
    assert len(lv) == 16 and lv.max() == 127 and np.array_equal(lv, -lv[::-1])
    t = torch.linspace(-200, 200, 4001)
    q = e.q(t)
    best = e.levels[(t[:, None] - e.levels[None]).abs().argmin(1)]
    assert torch.equal((q - t).abs(), (best - t).abs())


def test_hadamard_blocks_orthonormal():
    x = torch.randn(3, 8192, dtype=torch.float64).float()
    y = Q.hadamard_blocks(Q.hadamard_blocks(x, 4096), 4096)
    assert torch.allclose(x, y, atol=1e-5)
    assert torch.allclose(x.norm(dim=-1), Q.hadamard_blocks(x, 4096).norm(dim=-1), rtol=1e-5)


@pytest.mark.skipif(not CUDA, reason="needs CUDA")
def test_gptq_with_identity_hessian_is_rtn():
    """With a diagonal Hessian GPTQ propagates no error, so (static groups, any
    sweep order) it must return round-to-nearest codes at the precomputed scales."""
    torch.manual_seed(0)
    Wm = torch.randn(64, 512, device="cuda")
    H = torch.diag(torch.rand(512, device="cuda") + 0.5)
    for spec in ("int4:g128", "lm4:g64", "int3+int6@0.25:g128"):
        f = W.Fmt(spec)
        uh = None
        if f.mixed:
            uh = torch.rand(64, 512 // f.g) < 0.25
        codes, scales = W.gptq(Wm, H, f, uh, actorder=True)
        wg = Wm.reshape(64, -1, f.g)
        colw = torch.diag(H).view(-1, f.g)
        s_lo, _ = W.rtn_scales(wg, f.lo, colw)
        s = s_lo[..., 0]
        if f.mixed:
            s_hi, _ = W.rtn_scales(wg, f.hi, colw)
            s = torch.where(uh.cuda(), s_hi[..., 0], s)
        assert torch.equal(scales.float().cuda(), s.to(torch.bfloat16).float())
        t = wg / s[..., None]
        ref = f.lo.q(t)
        if f.mixed:
            ref = torch.where(uh.cuda()[..., None], f.hi.q(t), ref)
        assert torch.equal(codes.cuda().float(), ref.reshape(64, 512))


@pytest.mark.skipif(not (CUDA and REDUCED.exists()), reason="needs CUDA and the reduced Qwen3 vehicle")
def test_folded_rotations_preserve_the_model():
    """res + vo + down rotations folded into BF16 matrices (and the online down
    Hadamard) reproduce the unrotated reduced model's logits up to BF16 rounding,
    in both the GPU and the contract arithmetic."""
    g = torch.Generator().manual_seed(0)
    calib = torch.randint(0, 4096, (4, 64), generator=g)
    toks = torch.randint(0, 4096, (48,), generator=g)

    def logits(wsrc, arith):
        m = Q.Qwen3(REDUCED, arith, "bf16", "bf16", wfile=wsrc)
        return m.logits(m.forward(toks.cuda(), m.new_cache(1, 48)))
    for rot in ("res+vo+down",):
        ws = W.build(REDUCED, W.Fmt("int8:g128"), rot=rot, quantise=False, calib=calib, log=lambda m: None)
        ws["fmt"] = "bf16"
        for arith in ("gpu", "contract"):
            a, b = logits(ws, arith), logits(None, arith)
            assert (a - b).abs().max().item() < 0.05 * b.abs().max().item()
            assert (a.argmax(-1) == b.argmax(-1)).float().mean().item() >= 0.9


@pytest.mark.skipif(not (CUDA and REDUCED.exists()), reason="needs CUDA and the reduced Qwen3 vehicle")
def test_quantised_build_runs_in_both_arithmetics():
    g = torch.Generator().manual_seed(1)
    calib = torch.randint(0, 4096, (4, 64), generator=g)
    ws = W.build(REDUCED, W.Fmt("int4+int8@0.25:g64"), rot="res+vo", alloc="fisher", scope="global",
                 calib=calib, fisher_calib=calib[:2], log=lambda m: None, embed_fmt="int4:g64")
    f = ws["meta"]["bits_per_weight_matrices"]
    assert 4 + 16 / 64 < f < 8
    toks = torch.randint(0, 4096, (16,), generator=g).cuda()
    outs = []
    for arith in ("gpu", "contract"):
        m = Q.Qwen3(REDUCED, arith, "bf16", "bf16", wfile=ws)
        outs.append(m.logits(m.forward(toks, m.new_cache(1, 16))))
        assert torch.isfinite(outs[-1]).all()
    assert (outs[0].argmax(-1) == outs[1].argmax(-1)).float().mean().item() > 0.8


def test_eight_bit_formats():
    """The 8-bit candidates: INT8 per output channel (g0 = the whole row), INT8 g128
    and FP8 E4M3 per channel; bits include the BF16 scale; E4M3 codes are the
    golden's to_fp8 values, held exactly in BF16."""
    f = W.Fmt("int8:g0").for_k(4096)
    assert f.g == 4096 and f.bits() == pytest.approx(8 + 16 / 4096) and f.code_dtype == torch.int8
    assert W.Fmt("int8:g128").bits() == pytest.approx(8.125)
    e = W.Fmt("fp8:g0").for_k(12288)
    assert e.code_dtype == torch.bfloat16 and e.bits() == pytest.approx(8 + 16 / 12288)
    t = torch.randn(100000) * 100
    assert torch.equal(e.lo.q(t), Q.to_fp8(t))
    assert torch.equal(e.lo.q(t).to(torch.bfloat16).float(), e.lo.q(t))
    torch.manual_seed(0)
    Wm = torch.randn(64, 4096) * torch.rand(64, 1)
    for spec in ("int8:g0", "int8:g128", "fp8:g0"):
        fk = W.Fmt(spec).for_k(4096)
        codes, scales = W.rtn(Wm, fk)
        assert codes.dtype == fk.code_dtype and scales.shape == (64, 4096 // fk.g)
        err = (W.dq(codes, scales, "cpu") - Wm).norm() / Wm.norm()
        assert err < (0.01 if spec.startswith("int8") else 0.03)
    # compute-in-ROM: an 8-bit element takes two <=4-bit select cells
    assert W.cells_per_weight(W.Fmt("int8:g128")) == pytest.approx(2 + 16 / 128 / 4)
    r = W.rom_capacity(W.Fmt("int8:g0"), None, 8 + 16 / 4096)
    assert r["cells_per_weight"] == pytest.approx(2 + 4 / 4096) and not r["fits_reticle"]


@pytest.mark.skipif(not CUDA, reason="needs CUDA")
def test_rtl_int8_contract_post_accumulation_scale():
    """Codex's RTL weight contract: symmetric signed INT8 codes (-127..127, no zero
    point), one BF16 scale per output channel applied ONCE to the FP32 dot product,
    y_n = s_n * sum_k q_nk x_k, the sum in the golden K-split order."""
    f = W.Fmt("int8s:g0").for_k(512)
    assert (f.lo.qmin, f.lo.qmax) == (-127, 127)
    torch.manual_seed(0)
    Wm = torch.randn(96, 512) * 3
    codes, scales = W.rtn(Wm, f)
    assert codes.abs().max().item() <= 127 and scales.shape == (96, 1)
    x = Q.to_bf16(torch.randn(5, 512)).cuda()
    Wd = {"q": codes.t().contiguous().cuda(), "s": scales.t().contiguous().cuda(), "N": 96, "post": True}

    class M:
        groups = Q.SPEC_GROUPS
    got = Q.Qwen3.mv(M(), x, Wd)
    S = Q.split_for(96, 512, Q.SPEC_GROUPS)
    ref = Q._chunk_tree_dot_ref(x, codes.cuda().float(), S) * scales.cuda().float().t()
    assert torch.equal(got, ref)
