"""ABI 3.0 feature requirements are derived from operations, not products."""

from __future__ import annotations

from compiler.backends.hbm_sram.capability import single_chip_capability
from compiler.backends.rom.deepseek_v4 import (
    CAPABILITY_FEATURES as DEEPSEEK_ROM_CAPABILITY_FEATURES,
    PROGRAM_FEATURES as DEEPSEEK_ROM_PROGRAM_FEATURES,
)
from compiler.backends.rom.qwen3 import (
    CAPABILITY_FEATURES as QWEN_ROM_CAPABILITY_FEATURES,
    PROGRAM_FEATURES as QWEN_ROM_PROGRAM_FEATURES,
)
from runtime.abi3.builder import DeploymentBuilder
from runtime.abi3.constants import Feature, IntegrityMode
from runtime.abi3.descriptors import CollectiveOp


def _builder() -> DeploymentBuilder:
    return DeploymentBuilder(
        target_id="feature-requirement-probe",
        model_id="feature-requirement-probe",
        backend="test",
        capability=single_chip_capability(),
    )


def test_rom_programs_do_not_blanket_require_compatibility_features() -> None:
    assert Feature.TRANSACTIONAL_STATE not in QWEN_ROM_PROGRAM_FEATURES
    assert Feature.INTEGRITY_RETRY not in QWEN_ROM_PROGRAM_FEATURES
    assert Feature.TRANSACTIONAL_STATE not in DEEPSEEK_ROM_PROGRAM_FEATURES
    assert Feature.INTEGRITY_RETRY not in DEEPSEEK_ROM_PROGRAM_FEATURES

    # Removing a program requirement does not remove compatibility support
    # from the hardware capability or change its published identity.
    assert Feature.TRANSACTIONAL_STATE in QWEN_ROM_CAPABILITY_FEATURES
    assert Feature.INTEGRITY_RETRY in QWEN_ROM_CAPABILITY_FEATURES
    assert Feature.TRANSACTIONAL_STATE in DEEPSEEK_ROM_CAPABILITY_FEATURES
    assert Feature.INTEGRITY_RETRY in DEEPSEEK_ROM_CAPABILITY_FEATURES


def test_integrity_or_replay_on_a_communication_descriptor_requires_bit_10() -> None:
    builder = _builder()
    builder.communication(
        collective_op=CollectiveOp.BROADCAST,
        local_object_id=1,
        integrity_mode=IntegrityMode.CRC32C,
        retry_bound=3,
    )

    assert int(Feature.INTEGRITY_RETRY) in builder.features


def test_unprotected_nonreplayed_communication_does_not_require_bit_10() -> None:
    builder = _builder()
    builder.communication(
        collective_op=CollectiveOp.BROADCAST,
        local_object_id=1,
        integrity_mode=IntegrityMode.NONE,
        retry_bound=0,
    )

    assert int(Feature.INTEGRITY_RETRY) not in builder.features
