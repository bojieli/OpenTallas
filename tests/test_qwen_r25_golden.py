"""qwen_r25 golden (tools/qwen3_deployment_quality.py order="r25") against an independent numpy reference built
from tools/hdc_golden_v41.py (csum chunk8, IEEE div, silu) and tools/hdc_golden.py (exp): bit-exact."""
import sys
import types
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as V  # noqa: E402
import qwen3_deployment_quality as Q  # noqa: E402

F = np.float32
DEVS = ["cpu"] + (["cuda"] if torch.cuda.is_available() else [])


def bf16(a):
    return np.asarray(torch.from_numpy(np.asarray(a, dtype=F)).to(torch.bfloat16).to(torch.float32))


def ref_mv(x, w, tp):
    """x [T, K], w [N, K] -> [T, N]: per die csum of exact products, die partials ((p0+p1)+(p2+p3))."""
    T, K = x.shape
    Kd = K // tp
    parts = [V.csum(V.mul(w[None, :, d * Kd:(d + 1) * Kd], bf16(x)[:, None, d * Kd:(d + 1) * Kd]))
             for d in range(tp)]
    while len(parts) > 1:
        parts = [V.add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
    return parts[0]


@pytest.mark.parametrize("dev", DEVS)
@pytest.mark.parametrize("K,tp", [(64, 1), (96, 4), (40, 1), (4096, 1), (12288, 4)])
def test_csum_dot(dev, K, tp):
    rng = np.random.default_rng(K + tp)
    T, N = 3, 5
    x = (rng.standard_normal((T, K)) * 3).astype(F)
    w = rng.integers(-128, 128, size=(N, K)).astype(F)          # INT8 codes, exact in BF16
    got = Q.csum_dot_t(torch.from_numpy(bf16(x)).t().contiguous().to(dev),
                       torch.from_numpy(w.T.copy()).to(torch.int8).to(dev), tp).cpu().numpy()
    want = ref_mv(x, w, tp)
    assert np.array_equal(got.view(np.uint32), want.astype(F).view(np.uint32))


def test_silu_matches_v41():
    g = np.concatenate([np.linspace(-100, 100, 4001), [0.0, -0.0, 1e-30, -88.5, 88.5]]).astype(F)
    got = Q.silu_r25(torch.from_numpy(g)).numpy()
    want = V.div(g, V.add(G.exp(V.neg(g)), F(1.0)))
    assert np.array_equal(got.view(np.uint32), want.view(np.uint32))


@pytest.mark.parametrize("dev", DEVS)
def test_attend(dev):
    rng = np.random.default_rng(7)
    Bt, Gq, T, HD, P = 2, 3, 2, 16, 37
    q = bf16(rng.standard_normal((Bt, Gq, T, HD)) * 2)
    K = np.asarray(Q.to_fp8(torch.from_numpy(rng.standard_normal((Bt, P, HD)).astype(F) * 3)))
    Vv = np.asarray(Q.to_fp8(torch.from_numpy(rng.standard_normal((Bt, P, HD)).astype(F) * 3)))
    qpos = np.array([[P - 2, P - 1], [20, 21]])
    scale = F(1.0 / np.sqrt(HD))
    me = types.SimpleNamespace(HD=HD)
    got = Q.Qwen3._attend_r25(me, torch.from_numpy(q).to(dev), torch.from_numpy(K).to(dev), torch.from_numpy(Vv).to(dev),
                              P, T, torch.from_numpy(qpos).to(dev), torch.tensor(scale, device=dev)).cpu().numpy()
    for b in range(Bt):
        for h in range(Gq):
            for t in range(T):
                n = qpos[b, t] + 1
                sc = V.mul(V.csum(V.mul(q[b, h, t][None, :], K[b, :n])), scale)
                mx = sc.max()
                e = G.exp(V.add(sc, V.neg(mx)))
                Z = V.csum(e)
                p = bf16(e)
                pv = V.csum(V.mul(p[:, None], Vv[b, :n]), axis=0)
                want = V.div(pv, Z)
                assert np.array_equal(got[b, h, t].view(np.uint32), want.astype(F).view(np.uint32)), (b, h, t)
