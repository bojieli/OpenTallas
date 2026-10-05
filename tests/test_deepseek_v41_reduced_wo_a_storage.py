"""``wo_a`` is written in the release's STORAGE shape, and this checks the
convention against the release's own checkpoint.

WHY IT MATTERS. The vendor module declares ``wo_a`` as bf16 while every sibling
projection takes the default fp8, and says why beside the einsum that consumes
it: "wo_a is block-diagonal over groups ... convert.py dequantizes it to bf16;
an fp8 grouped GEMM would halve the memory." So bf16 is the RUNTIME shape. The
released CHECKPOINT stores fp8 with a 32x32-blocked E8M0 scale, which its own
shard header states. A fixture written from ``named_parameters()`` gets the
runtime shape and is missing 43 ``attn.wo_a.scale`` tensors that a front end
modelling storage expects.

WHAT CANNOT BE TESTED, and why. An exact byte round trip against the released
weight is not available: ``convert.py``'s dequantization casts to bf16, so
re-quantizing sees a block maximum that has itself been rounded. Where that
moves the maximum across a power-of-two boundary the chosen exponent differs by
one. The test below therefore checks the convention and bounds the disagreement
rather than asserting equality -- and bounding it is the point, because a
quantizer with the wrong convention disagrees by far more than one exponent,
which is exactly how the first version of this code was caught storing the
exponent where the scale's value belonged.
"""
from __future__ import annotations

import json
import pathlib

import pytest

torch = pytest.importorskip("torch")

from tools.build_deepseek_v41_reduced_model import _store_wo_a_quantized  # noqa: E402

RELEASED = pathlib.Path(
    "/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash"
)
WEIGHT = "layers.0.attn.wo_a.weight"
SCALE = "layers.0.attn.wo_a.scale"


def quantize(weight: "torch.Tensor") -> tuple["torch.Tensor", "torch.Tensor"]:
    out, _ = _store_wo_a_quantized({WEIGHT: weight}, {WEIGHT: "bfloat16"}, torch)
    return out[WEIGHT], out[SCALE]


def dequantize(weight: "torch.Tensor", scale: "torch.Tensor") -> "torch.Tensor":
    """``convert.py``'s own dequantization, in its own shape handling."""

    out_block = weight.size(0) // scale.size(0)
    in_block = weight.size(1) // scale.size(1)
    assert (out_block, in_block) == (32, 32)
    wide = (
        weight.unflatten(0, (-1, out_block)).unflatten(-1, (-1, in_block)).float()
        * scale[:, None, :, None].float()
    )
    return wide.flatten(2, 3).flatten(0, 1).bfloat16()


def test_the_formats_and_the_block_are_the_release_s() -> None:
    weight = (torch.randn(256, 256) * 0.02).bfloat16()
    stored, scale = quantize(weight)
    assert stored.dtype == torch.float8_e4m3fn
    assert scale.dtype == torch.float8_e8m0fnu
    assert tuple(scale.shape) == (256 // 32, 256 // 32)


def test_the_scale_stores_its_value_and_not_its_exponent() -> None:
    """2**0 is byte 0x7F, which is the builder's own stated convention."""

    weight = torch.zeros(32, 32).bfloat16()
    _, scale = quantize(weight)
    assert scale.view(torch.uint8).flatten()[0].item() == 0x7F
    assert scale.float().flatten()[0].item() == 1.0


def test_no_block_can_saturate_the_format() -> None:
    """The scale is chosen so every quotient lands inside e4m3's range."""

    torch.manual_seed(11)
    for magnitude in (1e-8, 1.0, 1e4):
        weight = (torch.randn(64, 64) * magnitude).bfloat16()
        stored, scale = quantize(weight)
        assert torch.isfinite(stored.float()).all(), magnitude
        back = dequantize(stored, scale)
        assert torch.isfinite(back.float()).all(), magnitude


def test_the_round_trip_sits_inside_e4m3_s_precision() -> None:
    """Mean relative error near 2**-5.5, which is what 3 mantissa bits give."""

    torch.manual_seed(7)
    weight = (torch.randn(256, 256) * 0.02).bfloat16()
    stored, scale = quantize(weight)
    back = dequantize(stored, scale)
    relative = (back.float() - weight.float()).abs() / weight.float().abs().clamp(
        min=1e-30
    )
    #: the MEAN, not the max: block scaling gives a small element inside a block
    #: with a large maximum only a few significant bits, which is inherent.
    assert relative.mean() < 0.05


@pytest.mark.skipif(not RELEASED.is_dir(), reason="released snapshot not cached")
def test_the_convention_agrees_with_the_released_checkpoint() -> None:
    """Re-quantizing the release's own dequantized wo_a lands within one exponent."""

    safetensors = pytest.importorskip("safetensors")
    from safetensors import safe_open

    snapshots = sorted((RELEASED / "snapshots").iterdir())
    snapshot = snapshots[0]
    index = json.loads((snapshot / "model.safetensors.index.json").read_text())
    shard = snapshot / index["weight_map"][WEIGHT]
    if not shard.is_file():
        pytest.skip("the shard holding wo_a is not cached")
    with safe_open(str(shard), framework="pt") as handle:
        released_weight = handle.get_tensor(WEIGHT)
        released_scale = handle.get_tensor(SCALE)
    assert released_weight.dtype == torch.float8_e4m3fn
    assert released_scale.dtype == torch.float8_e8m0fnu
    assert released_weight.size(0) // released_scale.size(0) == 32
    assert released_weight.size(1) // released_scale.size(1) == 32

    runtime = dequantize(released_weight, released_scale)
    _, scale = quantize(runtime)
    delta = scale.view(torch.uint8).int() - released_scale.view(torch.uint8).int()
    #: At most one exponent, and never upward -- a wrong convention misses by
    #: far more, and an upward miss would mean a quotient the format cannot hold.
    assert int(delta.max()) <= 0, int(delta.max())
    assert int(delta.min()) >= -1, int(delta.min())
