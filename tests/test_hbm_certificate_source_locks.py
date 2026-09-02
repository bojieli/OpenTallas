"""The HBM certificate must invalidate on every correctness-layer change."""

from __future__ import annotations

import hashlib
from pathlib import Path

from tools.check_hbm_deployments import CERTIFICATE_SOURCE_PATHS


REPO = Path(__file__).resolve().parents[1]


def test_certificate_locks_admission_decode_ir_and_backend_sources() -> None:
    required = {
        "compiler/backends/hbm_sram/check.py",
        "compiler/backends/hbm_sram/lower.py",
        "compiler/backends/hbm_sram/plan.py",
        "compiler/backends/numeric_contracts.py",
        "compiler/ir/v3/kernel_ir.py",
        "compiler/ir/v3/lowering.py",
        "compiler/ir/v3/numeric.py",
        "runtime/abi3/builder.py",
        "runtime/abi3/capability.py",
        "runtime/abi3/constants.py",
        "runtime/abi3/crc.py",
        "runtime/abi3/deployment.py",
        "runtime/abi3/descriptors.py",
        "runtime/abi3/layout.py",
        "runtime/abi3/records.py",
        "runtime/abi3/verifier.py",
        "tools/check_hbm_deployments.py",
    }
    assert required <= set(CERTIFICATE_SOURCE_PATHS.values())
    assert len(CERTIFICATE_SOURCE_PATHS) == len(set(CERTIFICATE_SOURCE_PATHS.values()))
    for relative in CERTIFICATE_SOURCE_PATHS.values():
        source = REPO / relative
        assert source.is_file(), relative
        assert len(hashlib.sha256(source.read_bytes()).hexdigest()) == 64
