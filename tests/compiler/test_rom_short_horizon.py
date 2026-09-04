"""A graph may declare a shorter horizon than the capability admits.

The ROM block loop takes its trip count from the capability's context bound.
For a released model that is right by coincidence: the graph is built for the
target it ships on, so the horizon and the bound are the same number.  A
*derived* graph is where the two part.  The DSpark draft stack, sliced out of
the speculative graph at a 1,024-token horizon and lowered against a
262,144-position capability, tripped its block loops 256 times and so promised
every symbolic-leading view 262,144 rows of a 1,024-row object.  Seventy-four
views were refused, none of them wrong about anything except how many rows the
loop had claimed on their behalf.

What this pins is the property, not the count: no view may be refused for
running off an object whose extent the *request* determines.  A view over a
tensor with a constant leading extent is a different question and is not
claimed here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from compiler.backends.rom.common import program as rom_program
from compiler.backends.rom.deepseek_v4_array import (
    build_deepseek_v4_array_rom_deployment,
    deepseek_v4_array_rom_capability,
)
from compiler.ir.v3.kernel_ir import KernelGraph, Symbolic
from runtime.abi3.verifier import verify_deployment

ROOT = Path(__file__).resolve().parents[2]
DRAFT = ROOT / "build" / "ir-v3" / "deepseek-v4-flash-0731-dspark-draft-b1024"


@pytest.fixture(scope="module")
def refusals_by_tensor() -> dict[str, list[str]]:
    """Lower the draft stack, keeping each view's tensor, and return refusals."""

    ir = DRAFT / "kernel_ir.v3.json"
    if not ir.exists():
        pytest.skip(
            f"{ir} is not built (tools/build_dspark_draft_graph.py "
            "--context-tokens 1024)"
        )
    graph = KernelGraph.read(ir)
    seen: dict[int, str] = {}
    original = rom_program.RomLowering._buffer_view

    def remember(self, tensor, *, dims, strides, **rest):
        view_id = original(self, tensor, dims=dims, strides=strides, **rest)
        seen.setdefault(view_id, tensor.tensor_id)
        return view_id

    capability = deepseek_v4_array_rom_capability()
    rom_program.RomLowering._buffer_view = remember
    try:
        deployment, _plan = build_deepseek_v4_array_rom_deployment(
            graph, capability=capability
        )
    finally:
        rom_program.RomLowering._buffer_view = original
    verification = verify_deployment(deployment, capability)

    import re

    pattern = re.compile(r"view (\d+): maximum element \d+ needs")
    refused: dict[str, list[str]] = {}
    for problem in verification.errors:
        match = pattern.match(str(problem))
        if match is None:
            continue
        tensor_id = seen.get(int(match.group(1)))
        if tensor_id is not None:
            refused.setdefault(tensor_id, []).append(str(problem))
    refused["__graph__"] = [graph]  # type: ignore[list-item]
    return refused


def test_no_request_sized_view_runs_off_its_object(refusals_by_tensor) -> None:
    graph: KernelGraph = refusals_by_tensor["__graph__"][0]  # type: ignore[index]
    tensors = {t.tensor_id: t for t in graph.tensors}
    offenders = []
    for tensor_id in refusals_by_tensor:
        if tensor_id == "__graph__":
            continue
        tensor = tensors.get(tensor_id)
        if tensor is None or not tensor.shape:
            continue
        if isinstance(tensor.shape[0], Symbolic):
            offenders.append((tensor_id, tensor.shape[0]))
    assert offenders == [], (
        "views over request-sized tensors were refused; the block loop is "
        f"claiming more rows than the graph's horizon declares: {offenders[:4]}"
    )


def test_the_derived_graph_really_declares_a_short_horizon(
    refusals_by_tensor,
) -> None:
    """Without this the first test would pass for the wrong reason."""

    graph: KernelGraph = refusals_by_tensor["__graph__"][0]  # type: ignore[index]
    horizon = int(graph.source.get("deployment_context_tokens") or 0)
    capability_bound = int(
        deepseek_v4_array_rom_capability().limits["max_context_positions"]
    )
    assert horizon, "the derived graph must declare the horizon it was built for"
    assert horizon < capability_bound, (
        f"horizon {horizon} is not shorter than the capability's "
        f"{capability_bound}; this graph cannot exercise the bound"
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "The draft stack does not lower cleanly yet, and the reason is not the "
        "horizon.  Nineteen views remain refused, every one of them over a "
        "tensor whose leading extent is the constant DSpark block of 5 -- "
        "'dspark.layerNN.expert_reduce.output' at [5, 4096], 'hc_ffn_post."
        "output' at [5, 4, 4096], 'routed_experts.output' at [30, 4096].  The "
        "block loop walks those as if the block axis were the token axis.  The "
        "same defect is in the HBM lane, where the static verifier admits the "
        "deployment and the device traps on it instead: the cluster-32 draft "
        "build (447 instructions) retires 35 and then reports 'EXPERT_SUM "
        "weight view 321 holds 20 weights for 4 contributions' -- 20 being 5 "
        "blocks times 4 contributions.  Settling it means settling what the "
        "DSpark block axis is, which is the A30 draft-window contract, so this "
        "records the defect rather than guessing at it.  Remove the marker when "
        "the draft stack admits."
    ),
)
def test_the_draft_stack_admits(refusals_by_tensor) -> None:
    refused = {k: v for k, v in refusals_by_tensor.items() if k != "__graph__"}
    assert refused == {}, f"{sum(len(v) for v in refused.values())} views refused"
