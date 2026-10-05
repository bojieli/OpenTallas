import sys
from pathlib import Path
from dataclasses import replace
import ctypes
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import w19_hc_residual_proof as P


def random_carry():
    rng = np.random.default_rng(190034)
    return P.bind(P.G.to_bf16(rng.normal(size=(4, 5120)).astype(np.float32)), rng.normal(size=4).astype(np.float32),
                  rng.normal(size=4).astype(np.float32), rng.normal(size=(4, 4)).astype(np.float32), {"origin": "test synthetic"})


def test_full_shape_boundary_and_dependent_carry():
    c = random_carry()
    pre, y, post, a, b = P.consume(c)
    rp, rq, ra, rb = P.oracle(c.res, c.pre, y, c.post, c.comb)
    assert P.compare(a, ra) == 8
    assert P.compare(b, rb) == 37
    assert np.array_equal(pre.view(np.uint32), rp.view(np.uint32))
    assert np.array_equal(post.view(np.uint32), rq.view(np.uint32))
    assert P.array_sha(pre) == P.array_sha(y)
    P.check_carry(c)


@pytest.mark.parametrize("name", ["res", "pre", "post", "comb"])
def test_detect_changed_carry_or_cross_fixture_coefficients(name):
    c = random_carry()
    v = getattr(c, name).copy()
    v.reshape(-1)[0] += np.float32(1)
    with pytest.raises(ValueError, match="carry changed"):
        P.consume(replace(c, **{name: v}))


def test_producer_manifest_cannot_silently_change():
    c = random_carry()
    c.manifest["producer"] = {"origin": "wrong producer"}
    with pytest.raises(ValueError, match="provenance changed"):
        P.consume(c)


def test_tree_transpose_and_early_BF16_mutations_fail():
    _, c = next(P.controls())
    pre, _, _, _, _ = P.consume(c)
    assert np.all(pre == 1)
    products = P.G.mul(c.pre[:, None], c.res)
    tree = P.G.add(P.G.add(products[0], products[1]), P.G.add(products[2], products[3]))
    assert np.all(tree == 0)
    c = random_carry(); pre, y, post, _, _ = P.consume(c)
    wrong, _ = P.lower_post(y, c.res, c.post, c.comb.T.copy())
    assert np.any(wrong.view(np.uint32) != post.view(np.uint32))
    early, _ = P.lower_pre(c.res, P.G.to_bf16(c.pre))
    assert np.any(early.view(np.uint32) != pre.view(np.uint32))


def test_separate_product_FMA_control():
    _, c = list(P.controls())[1]
    pre, *_ = P.consume(c)
    assert np.all(pre.view(np.uint32) == 0)
    lib = ctypes.CDLL("libm.so.6"); lib.fmaf.argtypes = [ctypes.c_float] * 3; lib.fmaf.restype = ctypes.c_float
    fused = np.float32(lib.fmaf(float(c.pre[1]), float(c.res[1, 0]), float(c.pre[0])))
    assert fused != 0


def test_BF16_ties_signed_zero_and_underflow():
    bits = np.array([0x3F808000, 0x3F818000, 0xBF808000, 0xBF818000, 0x00008000, 0x00018000, 0x80000000], np.uint32)
    got = P.Instructions().bf16(bits.view(np.float32))
    assert np.array_equal(got.view(np.uint32), np.array([0x3F800000, 0x3F820000, 0xBF800000, 0xBF820000, 0, 0x00020000, 0x80000000], np.uint32))
    assert np.array_equal(got.view(np.uint32), P.G.to_bf16(bits.view(np.float32)).view(np.uint32))
    _, c = list(P.controls())[2]
    pre, y, post, *_ = P.consume(c)
    assert np.all(pre.view(np.uint32) == 0) and np.all(post.view(np.uint32) == 0)


def test_shape_and_BF16_validation():
    c = random_carry()
    with pytest.raises(ValueError):
        P.bind(c.res[:, :-1], c.pre, c.post, c.comb, {})
    v = c.res.copy(); v[0, 0] = np.float32(1.000001)
    with pytest.raises(ValueError):
        P.bind(v, c.pre, c.post, c.comb, {})


def test_oracle_restores_primitives_on_error():
    old = (P.V.add, P.V.mul, P.V.to_bf16)
    with pytest.raises(RuntimeError):
        with P.instrument(P.Instructions()):
            raise RuntimeError("injected")
    assert old == (P.V.add, P.V.mul, P.V.to_bf16)
