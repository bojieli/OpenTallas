"""The DFlash target adapter must use the two-reticle numerical boundary."""
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from tools import hdc_golden as G
from tools import qwen3_deployment_quality as Q
from tools.qwen3_o4_tp2_acceptance_adapter import bind_tp2_target
from tools.qwen3_dflash_int8_acceptance import W8DraftLinear


def test_tp2_column_split_and_row_partial_scale_order_match_golden():
    rng = np.random.default_rng(20260928)
    n, k, groups = 32, 32, 8
    x = G.to_bf16(rng.normal(0, 0.4, k).astype(np.float32))
    code = rng.integers(-120, 121, (n, k), dtype=np.int8)
    scales = (rng.uniform(0.003, 0.02, n).astype(np.float32)).astype(np.float32)
    scale = torch.tensor(scales).to(torch.bfloat16)
    W = {"q": torch.tensor(code.T.copy()), "s": scale[None, :]}
    model = SimpleNamespace(arith="contract", wfmt="w8", lm=W,
                            layers=[{"qkv": dict(W), "gu": dict(W),
                                     "o": dict(W), "down": dict(W)}])
    bind_tp2_target(model, groups)
    xt = torch.tensor(x)[None]
    col = model.mv(xt, model.lm)[0].numpy()
    sc = Q.split_for(n // 2, k, groups)
    col_ref = G.mul(G.matvec(code.astype(np.float32), x, sc), scale.float().numpy())
    np.testing.assert_array_equal(G.bits(col), G.bits(col_ref))
    row = model.mv(xt, model.layers[0]["o"])[0].numpy()
    sr = Q.split_for(n, k // 2, groups)
    a = G.matvec(code[:, :k // 2].astype(np.float32), x[:k // 2], sr)
    b = G.matvec(code[:, k // 2:].astype(np.float32), x[k // 2:], sr)
    row_ref = G.mul(G.add(a, b), scale.float().numpy())
    np.testing.assert_array_equal(G.bits(row), G.bits(row_ref))


def test_tp2_adapter_requires_deployed_w8_contract():
    W = {"q": torch.zeros((2, 2), dtype=torch.int8), "s": torch.ones((1, 2), dtype=torch.bfloat16)}
    model = SimpleNamespace(arith="gpu", wfmt="w8", lm=W, layers=[])
    try:
        bind_tp2_target(model)
    except ValueError as exc:
        assert "w8 contract" in str(exc)
    else:
        raise AssertionError("GPU arithmetic was accepted as TP-2 contract")


def test_drafter_row_parallel_int8_rounds_once_after_partial_fold():
    torch.manual_seed(17)
    lin = torch.nn.Linear(32, 32, bias=False).to(torch.bfloat16)
    w8 = W8DraftLinear(lin, groups=8, tp2_mode="row")
    x = torch.randn(1, 32).to(torch.bfloat16)
    got = w8(x)[0].float().numpy()
    q = w8.qT.t().numpy().astype(np.float32)
    xf = x[0].float().numpy()
    s = w8.sT[0].float().numpy()
    split = Q.split_for(32, 16, 8)
    p0 = G.matvec(q[:, :16], xf[:16], split)
    p1 = G.matvec(q[:, 16:], xf[16:], split)
    expect = torch.from_numpy(G.mul(G.add(p0, p1), s)).to(torch.bfloat16).float().numpy()
    np.testing.assert_array_equal(G.bits(got), G.bits(expect))


def test_released_separate_drafter_k_splits_and_fc_split():
    # The released drafter calls q/k/v separately; these are its numerical
    # splits, even though the timing inventory currently prices a fused qkv.
    assert Q.split_for(2048, 4096, 6144) == 4096       # q die slice
    assert Q.split_for(512, 4096, 6144) == 4096        # k or v die slice
    assert Q.split_for(2048, 20480, 6144) == 4096     # drafter fc die slice
    assert Q.split_for(3072, 4096, 6144) == 256       # target fused qkv
