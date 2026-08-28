"""Canonical checkpoint tensor transformations for executable deployments."""

from .deepseek_v4 import (
    CANONICAL_PLAN_SCHEMA,
    CONVERT_SOURCE_SHA256,
    CanonicalTransformError,
    canonicalize_source_name,
    dequantize_fp8_e8m0_matrix_to_bf16,
    fp8_e8m0_to_bf16_code,
    slice_row_major_payload,
    validate_native_mxfp4_pair,
)
from .plan import build_official_canonical_plan

__all__ = [
    "CANONICAL_PLAN_SCHEMA",
    "CONVERT_SOURCE_SHA256",
    "CanonicalTransformError",
    "build_official_canonical_plan",
    "canonicalize_source_name",
    "dequantize_fp8_e8m0_matrix_to_bf16",
    "fp8_e8m0_to_bf16_code",
    "slice_row_major_payload",
    "validate_native_mxfp4_pair",
]
