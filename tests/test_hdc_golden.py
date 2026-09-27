import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402

needs_checkpoint = pytest.mark.skipif(
    not G.CHECKPOINT.exists(), reason="build the reduced checkpoint: tools/build_qwen3_reduced_model.py")


def test_special_functions_are_within_three_ulp():
    x = np.linspace(-87, 88, 20001).astype(np.float32)
    assert np.max(np.abs(G.exp(x) / np.exp(x.astype(np.float64)) - 1)) < 3.6e-7
    d = np.exp(np.random.default_rng(0).uniform(-40, 40, 5000)).astype(np.float32)
    assert np.max(np.abs(G.reciprocal(d) * d.astype(np.float64) - 1)) < 3.6e-7
    assert max(abs(float(G.rsqrt(v)) * np.sqrt(float(v)) - 1) for v in d[:500]) < 3.6e-7


def test_bf16_rounding_is_nearest_even():
    assert G.to_bf16(np.float32(1.0 + 2 ** -8)) == np.float32(1.0)            # tie -> even
    assert G.to_bf16(np.float32(1.0 + 3 * 2 ** -8)) == np.float32(1.0 + 2 ** -6)


@needs_checkpoint
def test_golden_reproduces_the_torch_oracle_tokens():
    model = G.Model()
    prompt, expected = G.prompt_and_expected()
    cache = [[] for _ in range(model.layers)]
    for pos, tok in enumerate(prompt[:-1]):
        model.decode_token(tok, pos, cache)
    tok, out = prompt[-1], []
    for i in range(3):
        tok = int(np.argmax(model.decode_token(tok, len(prompt) - 1 + i, cache)))
        out.append(tok)
    assert out == expected


def test_fp8_kv_rounding_is_e4m3_nearest_even_saturating():
    f = lambda v: float(G.to_fp8(np.float32(v)))                               # noqa: E731
    assert f(1.0 + 2 ** -4) == 1.0 and f(1.0 + 3 * 2 ** -4) == 1.0 + 2 ** -2     # tie -> even
    assert f(448.0) == 448.0 and f(1e9) == 448.0 and f(-500.0) == -448.0         # saturating
    assert f(2 ** -9) == 2 ** -9 and f(2 ** -10) == 0.0 and f(1.5 * 2 ** -9) == 2 ** -8  # subnormals
    assert np.signbit(G.to_fp8(np.float32(-2 ** -12))) == False                  # noqa: E712  canonical +0
    x = np.random.default_rng(0).standard_normal(4096).astype(np.float32)
    assert np.array_equal(G.to_bf16(G.to_fp8(x)), G.to_fp8(x))                  # every E4M3 value is a BF16 value
