"""The attention softmax scale, derived from the head width.

This lives in its own module rather than beside the numeric contracts because it
is not a contract: it is one arithmetic identity, ``1/sqrt(head_dim)``, that both
the Qwen frontend (which writes the attribute) and the ROM backend (which checks
it) need to agree on.

It exists at all because the two used to disagree. The frontend emitted
``scale_bf16_code`` as the literal 0x3DB5 beside a ``scale_denominator_sqrt``
taken from ``head_dim``, so the pair agreed only at Qwen3-8B's head width of 128.
Any other model was handed the 8B softmax scale, and nothing downstream could
detect it: the value is finite, positive and plausible.
"""

from __future__ import annotations

import math
import struct

from runtime.reference.formats import binary32_bits_to_bf16_rne


def attention_scale_bf16_code(head_dim: int) -> int:
    """``1/sqrt(head_dim)`` as a BF16 code, rounded to nearest even.

    The attention softmax scale is a function of the head width and nothing
    else. Rounding goes through the repository's own binary32-to-BF16 RNE
    reference so the code here and the code the engines check against are
    produced by one rule; at ``head_dim`` 128 it yields 0x3DB5, the value this
    was previously written as a literal.
    """
    if head_dim <= 0:
        raise ValueError(f"head_dim must be positive, got {head_dim}")
    bits = struct.unpack("<I", struct.pack("<f", 1.0 / math.sqrt(head_dim)))[0]
    return int(binary32_bits_to_bf16_rne(bits).code)
