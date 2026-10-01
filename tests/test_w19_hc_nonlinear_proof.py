import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import w19_hc_nonlinear_proof as P


def fixture():
    rng = np.random.default_rng(190033)
    w = rng.normal(size=(24, 20480)).astype(np.float32)
    x = P.G.to_bf16(rng.normal(size=(4, 5120)).astype(np.float32))
    return w, x, np.array([0.01, 0.1, 1], np.float32), rng.normal(size=24).astype(np.float32), {
        "hc_mult": 4, "hc_sinkhorn_iters": 20, "rms_norm_eps": 1e-20, "hc_eps": 1e-6}


def test_full_shape_all_boundaries_match_original_method():
    args = fixture()
    out, trace = P.lower(*args)
    ref, expected = P.oracle(*args)
    P.compare(trace, expected)
    assert sum(n == "sinkhorn.cols" for n, _ in trace) == 20
    assert sum(n == "sinkhorn.rows" for n, _ in trace) == 19
    for a, b in zip(out, ref):
        assert np.array_equal(a.view(np.uint32), b.view(np.uint32))


def test_released_config_is_nested_and_shape_bound():
    raw = {"hidden_size": 5120, "hc_mult": 4, "hc_sinkhorn_iters": 20, "rms_norm_eps": 1e-20, "hc_eps": 1e-6}
    assert P.release_config({"text_config": raw}) is raw
    assert P.release_config(raw) is raw
    with pytest.raises(ValueError):
        P.release_config({"text_config": dict(raw, hidden_size=640)})


def test_oracle_restores_global_state_even_on_failure():
    old = (P.G.add, P.V.add, P.V.ARITH, sys.gettrace())
    with pytest.raises(RuntimeError):
        with P.instrument_original(P.Instructions(), np.zeros(24, np.float32)):
            raise RuntimeError("injected oracle failure")
    assert old == (P.G.add, P.V.add, P.V.ARITH, sys.gettrace())


@pytest.mark.parametrize("special,values", [
    ("rsqrt", [1e-20, 0.25, 1, 2, 1e20]),
    ("exp", [-100, -87, -0.0, 0, 0.5, 88, 100]),
    ("sigmoid", [-100, -1, -0.0, 0, 1, 100])])
def test_special_functions_exact(special, values):
    x = np.array(values, np.float32)
    got = getattr(P.Instructions(), special)(x)
    ref = getattr(P.V, special)(x)
    assert np.array_equal(got.view(np.uint32), ref.view(np.uint32))


def test_boundary_oracle_detects_rounding_and_missing_iteration():
    _, trace = P.lower(*fixture())
    bad = [(n, v.copy()) for n, v in trace]
    bad[10][1].reshape(-1).view(np.uint32)[0] ^= np.uint32(1)
    with pytest.raises(AssertionError, match="boundary"):
        P.compare(bad, trace)
    with pytest.raises(AssertionError, match="count"):
        P.compare(trace[:-1], trace)


def test_forbid_changed_normative_contract():
    args = list(fixture())
    args[-1]["hc_sinkhorn_iters"] = 19
    with pytest.raises(ValueError):
        P.lower(*args)


def test_separate_instructions_and_canonical_zero():
    I = P.Instructions()
    tiny = np.nextafter(np.float32(0), np.float32(1))
    assert I.mul(tiny, np.float32(1)).view(np.uint32) == 1
    assert I.mul(np.float32(-0), np.float32(1)).view(np.uint32) == 0
    a, b = np.float32(1 + 2**-23), np.float32(1 - 2**-8)
    rounded = I.mul(a, b)
    assert I.add(-rounded, I.mul(a, b)).view(np.uint32) == 0


def test_native_transcendental_shortcuts_are_detectable():
    I = P.Instructions()
    v = np.array([0.125, 0.3, 2, 10, 1e-20], np.float32)
    native_rsqrt = np.float32(1) / np.sqrt(v)
    assert np.any(I.rsqrt(v).view(np.uint32) != native_rsqrt.view(np.uint32))
    x = np.array([-100, -1.3, 0.125, 1.9, 100], np.float32)
    with np.errstate(over="ignore"):
        native_exp = np.exp(x)
    assert np.any(I.exp(x).view(np.uint32) != native_exp.view(np.uint32))


def test_realistic_reciprocal_and_sinkhorn_order_mutations_fail(monkeypatch):
    args = fixture()
    _, expected = P.oracle(*args)
    original = P.Instructions.div
    def approximate_div(self, a, b):
        result = np.asarray(a, np.float32) * (np.float32(1) / np.asarray(b, np.float32))
        return self.boundary("div", self.z(result))
    monkeypatch.setattr(P.Instructions, "div", approximate_div)
    _, changed = P.lower(*args)
    with pytest.raises(AssertionError, match="boundary"):
        P.compare(changed, expected)
    monkeypatch.setattr(P.Instructions, "div", original)
    _, trace = P.lower(*args)
    cols = [i for i, (n, _) in enumerate(trace) if n == "sinkhorn.cols"]
    # Dropping the twentieth column iteration fails even if final shape matches.
    with pytest.raises(AssertionError, match="count"):
        P.compare(trace[:cols[-2] + 1], expected)
