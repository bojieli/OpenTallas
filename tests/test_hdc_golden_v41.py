import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402

F = np.float32
needs_checkpoint = pytest.mark.skipif(
    not G.CHECKPOINT.exists(), reason="build the reduced V4.1 v2 fixture (tools/build_deepseek_v41_reduced_model.py)")


def test_fp8_quantiser_scale_and_ties():
    x = np.full(32, 1.0, dtype=F)
    x[1], x[2] = 1.0625, 1.1875                        # ties on the E4M3 grid at scale 2^-8
    q, e = G.quant_fp8(x)
    assert e.tolist() == [-8]                          # ceil(log2(1 * fp32(1/448))) = -8
    assert q[0] == 256 and q[1] == 256 and q[2] == 320  # 272 -> 256 (even), 304 -> 320 (even)
    assert G.qdq_fp8(x)[1] == F(1.0)


def test_fp4_quantisers_round_to_nearest_even():
    x = np.array([0.25, 0.75, 2.5, 5.0, 5.5, -1.25, 0.1, 6.0] * 4, dtype=F)  # amax 6 -> scale 1
    got = G.qdq_fp4_e8m0(x)
    assert got[:8].tolist() == [0.0, 1.0, 2.0, 4.0, 6.0, -1.0, 0.0, 6.0]
    rng = np.random.default_rng(1)
    v = (rng.standard_normal(16 * 64) * np.exp2(rng.integers(-6, 6, 16 * 64))).astype(F)
    got = G.qdq_fp4_e4m3(v, 16).reshape(-1, 16)
    blocks = v.reshape(-1, 16).astype(np.float64)
    s = G._e4m3_round(np.maximum(np.abs(blocks).max(1), float(G.FP4_AMAX_FLOOR_E4M3)) / 6)
    ref = G._round_grid(np.clip(blocks / s[:, None], -6, 6), 0, 1) * s[:, None]
    assert np.array_equal(got.astype(np.float64), G.to_bf16(ref.astype(F)).astype(np.float64))


def test_softplus_and_sigmoid_accuracy():
    x = np.linspace(-30, 30, 6001).astype(F)
    ref = np.log1p(np.exp(x.astype(np.float64)))
    assert np.max(np.abs(G.softplus(x) / ref - 1)) < 6e-7
    s = 1 / (1 + np.exp(-x.astype(np.float64)))
    assert np.max(np.abs(G.sigmoid(x) / s - 1)) < 6e-7


def test_topk_breaks_ties_to_the_lower_index():
    assert G.topk_lowest_index([1.0, 3.0, 3.0, 2.0, 3.0], 2).tolist() == [1, 2]
    assert sorted(G.topk_lowest_index([0.0, -np.inf, -np.inf, 5.0], 3).tolist()) == [0, 1, 3]


def test_engram_tables_match_the_release_layout():
    import json
    c = json.loads(G.CONFIG.read_text())
    t = G.EngramTables(c, c["vocab_size"])             # asserts the compressed vocabulary size
    assert t.primes[0, 0, :3].tolist() == [7817, 7823, 7829]
    assert t.offsets[0, :3].tolist() == [0, 7817, 15640]
    assert int(t.multipliers[0, 0]) == 2232106896359385
    ids = t.hashes([0, 3563, 3745], 0)
    assert len(ids) == 24 and np.all(ids >= t.offsets[0]) and np.all(ids < t.offsets[0] + t.primes[0].reshape(-1))


@needs_checkpoint
def test_golden_reproduces_the_oracle_tokens_in_the_release_decode_order():
    prompt, expected = G.prompt_and_expected()
    model = G.Model(vendor_decode_from=len(prompt))
    tokens, rows = model.generate(prompt, 4)
    assert tokens == expected[:4]
    assert G.margin(rows[0]) > 0.1                     # the oracle's own first margin is 0.1727
