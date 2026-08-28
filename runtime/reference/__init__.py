"""Independent target-semantic reference implementations."""

from .evaluator import ReferenceError, evaluate_reference
from .formats import (
    DecodedValue,
    NumericReferenceError,
    QuantizedActivationBlock,
    QuantizedBF16,
    QuantizedE4M3FN,
    binary32_bits_to_bf16_rne,
    decode_bf16,
    decode_e2m1,
    decode_e4m3fn,
    decode_e8m0,
    decode_mxfp4_block,
    decode_packed_e2m1,
    encode_e4m3fn_rne,
    quantize_bf16_activation_block,
)

__all__ = [
    "DecodedValue",
    "NumericReferenceError",
    "QuantizedActivationBlock",
    "QuantizedBF16",
    "QuantizedE4M3FN",
    "ReferenceError",
    "binary32_bits_to_bf16_rne",
    "decode_bf16",
    "decode_e2m1",
    "decode_e4m3fn",
    "decode_e8m0",
    "decode_mxfp4_block",
    "decode_packed_e2m1",
    "encode_e4m3fn_rne",
    "evaluate_reference",
    "quantize_bf16_activation_block",
]
