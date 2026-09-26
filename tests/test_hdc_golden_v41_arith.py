"""R-ARITH (docs/ARCH_SPEC_V41.md 4): csum is the chunked contract, geometry-independent, and legacy is untouched."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
V = pytest.importorskip("hdc_golden_v41")
G = pytest.importorskip("hdc_golden")
F = np.float32


def seq(t):
    acc = F(0)
    for x in t:
        acc = G.add(acc, F(x))
    return F(acc)


def tree(parts):
    parts = [F(p) for p in parts]
    while len(parts) & (len(parts) - 1):
        parts.append(F(0))
    while len(parts) > 1:
        parts = [G.add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
    return parts[0]


@pytest.mark.parametrize("n", [1, 5, 8, 9, 16, 20, 63, 64, 100, 640])
def test_csum_is_chunks_of_8_then_padded_tree(n):
    rng = np.random.default_rng(n)
    t = (rng.standard_normal(n) * np.exp2(rng.integers(-20, 20, n))).astype(F)
    want = tree([seq(t[i:i + 8]) for i in range(0, n, 8)])
    assert V.csum(t).tobytes() == F(want).tobytes()


def test_power_of_two_aligned_groups_reproduce_csum():
    """An engine that sums runs of 2^j chunks per group and combines the groups by the padded tree matches."""
    rng = np.random.default_rng(1)
    t = rng.standard_normal(160).astype(F)
    for block in (8, 16, 32, 64, 128):
        groups = [V.csum(t[i:i + block]) for i in range(0, len(t), block)]
        assert F(tree(groups)).tobytes() == V.csum(t).tobytes()


def test_csum_batched_axis():
    rng = np.random.default_rng(2)
    t = rng.standard_normal((3, 5, 37)).astype(F)
    out = V.csum(t)
    for i in range(3):
        for j in range(5):
            assert out[i, j] == V.csum(t[i, j])


def test_dots_q4_block_exact():
    V.set_arith("chunk8")
    try:
        rng = np.random.default_rng(3)
        a = np.stack([V.qdq_fp4_e8m0(x) for x in rng.standard_normal((4, 128)).astype(F)])
        b = np.stack([V.qdq_fp4_e8m0(x) for x in rng.standard_normal((6, 128)).astype(F)])
        got = V.dots_q4(a, b)
        for i in range(4):
            for j in range(6):
                blocks = [F(np.float64(a[i, k:k + 32]) @ np.float64(b[j, k:k + 32])) for k in range(0, 128, 32)]
                assert got[i, j] == V.csum(np.array(blocks, dtype=F))
    finally:
        V.set_arith("legacy")


def test_legacy_is_the_default():
    assert V.ARITH == "legacy"
