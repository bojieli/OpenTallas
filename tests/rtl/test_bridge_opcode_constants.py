"""The issue bridge's opcode constants must equal the ABI's own.

``ot_a3_engine_issue_bridge.sv`` decides what a token may execute by comparing
the issued family and sub against ``localparam`` values written by hand. A wrong
value does not fail loudly: the comparison simply never matches, so the operator
keeps taking ``TRAP_CAPABILITY`` and every predicate, port mux, count leg and
instantiation behind it is dead code that lints clean and passes every campaign
that does not issue that operator.

That happened: REDUCTION.EXPERT_SUM was wired with a sub of 0x05 against the
ABI's 0x01, and nothing in the RTL or the campaigns could have said so. This
test is the check that would have.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from runtime.abi3.constants import (
    Attention,
    Dma,
    Major,
    Reduction,
    Route,
    Selection,
    Tensor,
    Vector,
)

BRIDGE = Path(__file__).resolve().parents[2] / "rtl/abi3/ot_a3_engine_issue_bridge.sv"

#: The families whose sub-opcode enums the bridge names, keyed by the prefix its
#: localparams use.
SUB_ENUMS = {
    "DMA": Dma,
    "TENSOR": Tensor,
    "VECTOR": Vector,
    "ATTENTION": Attention,
    "ROUTE": Route,
    "REDUCTION": Reduction,
    "SELECTION": Selection,
}

LOCALPARAM = re.compile(r"localparam \[7:0\]\s+(\w+)\s*=\s*8'h([0-9a-fA-F]+);")


def _declared() -> dict[str, int]:
    return {
        match.group(1): int(match.group(2), 16)
        for match in LOCALPARAM.finditer(BRIDGE.read_text())
    }


def _expected() -> dict[str, int]:
    expected = {f"FAMILY_{family.name}": int(family) for family in Major}
    for prefix, enum in SUB_ENUMS.items():
        for member in enum:
            expected[f"{prefix}_{member.name}"] = int(member)
    return expected


def test_every_named_opcode_matches_the_abi() -> None:
    declared = _declared()
    expected = _expected()
    checked = {
        name: value for name, value in declared.items() if name in expected
    }
    assert checked, "no opcode localparams found; has the bridge been renamed?"
    wrong = {
        name: (value, expected[name])
        for name, value in checked.items()
        if value != expected[name]
    }
    assert not wrong, "\n".join(
        f"{name}: bridge {got:#04x}, runtime.abi3.constants {want:#04x}"
        for name, (got, want) in sorted(wrong.items())
    )


@pytest.mark.parametrize(
    "name",
    [
        # Every operator the bridge is meant to admit. A missing constant means
        # the wiring for it cannot be reached, which is the failure this file
        # exists for.
        "FAMILY_ROUTE",
        "FAMILY_REDUCTION",
        "ROUTE_WEIGHT_NORMALIZE",
        "ROUTE_WINDOW_INDEX",
        "ROUTE_BIASED_TOPK",
        "REDUCTION_EXPERT_SUM",
    ],
)
def test_the_wired_operators_are_named(name: str) -> None:
    assert name in _declared(), f"{name} is not declared in the bridge"
