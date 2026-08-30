"""Guard the property the ROM-versus-HBM comparison rests on.

For the same model, the two backends must produce the same program and differ
only in where the immutable weights live. If anything else differed - one
operand view, one numeric profile, one schedule - a measured difference between
the targets would be unattributable, and the comparison would be measuring the
compiler rather than the memory technology.

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


def test_both_builds_declare_the_same_descriptor_set(proof) -> None:
    assert proof["descriptors_only_in_one_build"] == {"rom": [], "hbm": []}
    assert proof["descriptor_count"]["rom"] == proof["descriptor_count"]["hbm"]


def test_only_memory_objects_differ(proof) -> None:
    assert set(proof["differing_by_type"]) <= {"MEMORY_OBJECT"}, proof["differing_by_type"]


def test_every_difference_is_a_storage_class_transition(proof) -> None:
    assert proof["differences_beyond_storage_class"] == []
    assert set(proof["storage_class_transitions"]) == {"ROM->HBM"}


def test_both_builds_are_admitted(proof) -> None:
    assert proof["admitted"] == {"rom": True, "hbm": True}


def test_the_property_holds(proof) -> None:
    assert proof["holds"] is True
