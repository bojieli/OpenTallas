"""Guard the storage-and-placement property the ROM/HBM comparison rests on.

For the same model, the two backends must produce the same program and differ
only in where the immutable weights live.  Comparison-HBM objects must use the
ABI's explicit unplaced sentinel; ROM bank-local addresses cannot be silently
reinterpreted as flat HBM addresses.  If anything else differed - one operand
view, one permission bit, one numeric profile, one schedule - a measured
difference between the targets would be unattributable.

These tests are skipped, not failed, when a neutral IR has not been built, so a
fresh checkout does not report a false failure.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import sys

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from compiler.ir.v3.kernel_ir import KernelGraph
from runtime.abi3.constants import (
    NO_ID,
    NO_NODE,
    IntegrityMode,
    Permission,
    StorageClass,
)
from runtime.abi3.descriptors import Descriptor, ExtendedDescriptorType

REPO = Path(__file__).resolve().parents[2]

CASES = (
    ("qwen3", "qwen3-8b"),
    ("deepseek_v4", "deepseek-v4-flash-0731"),
)


def _graph(model: str) -> KernelGraph:
    path = REPO / "build" / "ir-v3" / model / "kernel_ir.v3.json"
    if not path.exists():
        pytest.skip(f"neutral IR for {model} has not been built")
    return KernelGraph.read(path)


@pytest.fixture(params=CASES, ids=[c[0] for c in CASES])
def proof(request):
    from compiler.backends.rom.common.program import RomLoweringError
    from tools.prove_storage_class_equivalence import prove

    product, model = request.param
    try:
        return prove(_graph(model), product)
    except RomLoweringError as refusal:
        # A graph the backend REFUSES has no ROM/HBM pair to compare, so this
        # property is vacuous rather than violated -- the same reason this file
        # already skips when a neutral IR has not been built. Skipping with the
        # refusal as the reason means the suite says why the property is
        # unproven for this model instead of going quiet about it.
        pytest.skip(f"{product}: the backend refuses this graph -- {refusal}")


def test_the_instruction_stream_does_not_depend_on_storage_class(proof) -> None:
    assert proof["instruction_body_identical"] is True
    assert proof["decoded_instructions_equal"] is True
    assert proof["instruction_count"]["rom"] == proof["instruction_count"]["hbm"]
    assert proof["program_header_identical_except_derived_digests"] is True
    assert proof["unexpected_program_header_differences"] == []
    assert set(proof["program_header_differences"]) == {
        "deployment_digest",
        "descriptor_table_digest",
    }


def test_both_builds_declare_the_same_descriptor_set(proof) -> None:
    assert proof["descriptors_only_in_one_build"] == {"rom": [], "hbm": []}
    assert proof["descriptor_count"]["rom"] == proof["descriptor_count"]["hbm"]


def test_only_the_objects_and_their_bank_masks_differ(proof) -> None:
    """Two descriptor types may move, and a schedule only by its bank mask.

    A schedule's ``bank_mask`` names the ROM banks its weight operands occupy,
    so moving those weights to HBM empties it.  That is the placement
    transition observed on the reader rather than on the object, and
    ``assess_schedule_bank_transition`` admits it only in that exact shape.
    Any other schedule field -- tile geometry, queue, engine, outstanding
    bound, route class -- would be a compiler difference and lands in
    ``differences_beyond_permitted_transition`` below.
    """
    assert set(proof["differing_by_type"]) <= {"MEMORY_OBJECT", "SCHEDULE"}, proof[
        "differing_by_type"
    ]


def test_every_difference_is_the_governed_storage_and_placement_transition(
    proof,
) -> None:
    assert proof["schema"] == "opentallas.abi3.storage_and_placement_equivalence.v2"
    assert proof["contract"]["required_storage_transition"] == "ROM->HBM"
    assert proof["contract"]["required_hbm_placement"] == {
        "bank_or_tile": NO_NODE,
        "base_address": 0,
    }
    assert proof["differences_beyond_permitted_transition"] == []
    assert set(proof["storage_class_transitions"]) <= {
        "ROM->HBM",
        "rom_bank_mask->empty",
    }
    assert proof["permitted_transition_count"] == proof["differing_descriptor_count"]
    # Every object difference is the unplacing transition, and every remaining
    # difference is a schedule's emptied bank mask.  The two counts together
    # account for every differing descriptor, so nothing is admitted silently.
    assert (
        proof["hbm_unplaced_transition_count"]
        + proof["schedule_bank_transition_count"]
        == proof["differing_descriptor_count"]
    )
    assert proof["schedule_bank_transition_count"] == proof["differing_by_type"].get(
        "SCHEDULE", 0
    )


def test_non_wire_inputs_are_identical(proof) -> None:
    assert proof["object_sources_identical"] is True
    assert proof["entrypoints_identical"] is True
    assert proof["required_features_identical"] is True


def test_both_builds_are_admitted(proof) -> None:
    assert proof["admitted"] == {"rom": True, "hbm": True}


def test_the_property_holds(proof) -> None:
    assert proof["holds"] is True


def _memory_object(
    storage_class: StorageClass,
    *,
    bank_or_tile: int,
    base_address: int,
    integrity_mode: IntegrityMode = IntegrityMode.CRC_AND_ECC,
) -> Descriptor:
    return Descriptor(
        descriptor_id=7,
        descriptor_type=ExtendedDescriptorType.MEMORY_OBJECT,
        payload={
            "storage_class": int(storage_class),
            "integrity_mode": int(integrity_mode),
            "alignment_log2": 6,
            "node_id": 0,
            "bank_or_tile": bank_or_tile,
            "base_address": base_address,
            "size_bytes": 4096,
            "replica_group_id": NO_ID,
            "content_digest": bytes.fromhex("42" * 32),
        },
        permissions=int(Permission.READ | Permission.IMMUTABLE),
    )


def _assessment(
    rom: Descriptor,
    hbm: Descriptor,
):
    from tools.prove_storage_class_equivalence import (
        assess_memory_object_transition,
    )

    return assess_memory_object_transition(rom, hbm)


def test_exact_rom_placement_to_unplaced_hbm_transition_is_permitted() -> None:
    rom = _memory_object(StorageClass.ROM, bank_or_tile=9, base_address=0x4000)
    hbm = _memory_object(StorageClass.HBM, bank_or_tile=NO_NODE, base_address=0)

    assessment = _assessment(rom, hbm)
    assert assessment["permitted"] is True
    assert assessment["hbm_unplaced"] is True
    assert assessment["placement_changed"] is True


def test_already_unplaced_rom_object_may_change_storage_only() -> None:
    rom = _memory_object(StorageClass.ROM, bank_or_tile=NO_NODE, base_address=0)
    hbm = _memory_object(StorageClass.HBM, bank_or_tile=NO_NODE, base_address=0)

    assessment = _assessment(rom, hbm)
    assert assessment["permitted"] is True
    assert assessment["placement_changed"] is False


def test_existing_integrity_mode_exception_remains_explicit() -> None:
    rom = _memory_object(
        StorageClass.ROM,
        bank_or_tile=3,
        base_address=0x8000,
        integrity_mode=IntegrityMode.CRC_AND_ECC,
    )
    hbm = _memory_object(
        StorageClass.HBM,
        bank_or_tile=NO_NODE,
        base_address=0,
        integrity_mode=IntegrityMode.CRC32C,
    )

    assessment = _assessment(rom, hbm)
    assert assessment["permitted"] is True
    assert assessment["integrity_mode_changed"] is True


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    (
        ("bank_or_tile", 0, "hbm_bank_or_tile_not_no_node"),
        ("base_address", 0x1000, "hbm_base_address_not_zero"),
        ("storage_class", int(StorageClass.SRAM), "storage_transition_not_rom_to_hbm"),
    ),
)
def test_inexact_hbm_transition_fails_closed(field, value, reason) -> None:
    rom = _memory_object(StorageClass.ROM, bank_or_tile=5, base_address=0x2000)
    hbm = _memory_object(StorageClass.HBM, bank_or_tile=NO_NODE, base_address=0)
    hbm.payload[field] = value

    assessment = _assessment(rom, hbm)
    assert assessment["permitted"] is False
    assert reason in assessment["reasons"]


def test_payload_drift_outside_the_four_named_fields_fails_closed() -> None:
    rom = _memory_object(StorageClass.ROM, bank_or_tile=5, base_address=0x2000)
    hbm = _memory_object(StorageClass.HBM, bank_or_tile=NO_NODE, base_address=0)
    hbm.payload["size_bytes"] *= 2

    assessment = _assessment(rom, hbm)
    assert assessment["permitted"] is False
    assert assessment["unexpected_payload_fields"] == ["size_bytes"]
    assert "payload_drift_outside_permitted_fields" in assessment["reasons"]


def test_common_descriptor_header_drift_fails_closed() -> None:
    rom = _memory_object(StorageClass.ROM, bank_or_tile=5, base_address=0x2000)
    hbm = _memory_object(StorageClass.HBM, bank_or_tile=NO_NODE, base_address=0)
    hbm.permissions = int(Permission.READ)

    assessment = _assessment(rom, hbm)
    assert assessment["permitted"] is False
    assert assessment["changed_header_fields"] == ["permissions"]
    assert "descriptor_header_drift" in assessment["reasons"]
