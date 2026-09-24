"""The ROM lowering of V4.1's attention KV join, resolved the way the runtime does.

Measured on the shipped V4.1 ROM cells (see
``results/abi3/deepseek_v41_state_read_results_were_unbound.json``, ``open``):
the ratio-1 PREFILL join (layers 20-39) was emitted one token per iteration,
writing ``[current r, compressed r]`` at rows ``2r, 2r + 1`` -- the two segments
interleaved -- while ``ATTENTION.SPARSE``'s indices address every current row
first and compressed row ``j`` at ``span + j``.

The test resolves the emitted views through ``runtime.sim.memory.ViewResolver``
-- the resolver the engines use -- at a concrete request, so it checks what the
engine is handed rather than how the lowering spelled it.  It needs the shipped
V4.1 Kernel IR under ``build/`` and skip without it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ROM_IR = REPO / "build/ir-v3/deepseek-v4.1-flash-c8192-amE10/kernel_ir.v3.json"
CAPS = {
    "wafer": REPO / "configs/hardware/abi3_capability/rom_deepseek_v41_wafer.json",
    "array64": REPO / "configs/hardware/abi3_capability/rom_deepseek_v41_array_64.json",
}
NO_ID = 0xFFFFFFFF


@pytest.fixture(scope="module")
def graph():
    if not ROM_IR.exists():
        pytest.skip(f"{ROM_IR.relative_to(REPO)} is not built")
    from compiler.ir.v3.kernel_ir import KernelGraph

    return KernelGraph.read(ROM_IR)


_DEPLOYMENTS: dict[str, object] = {}


def _deployment(graph, target: str):
    if target not in _DEPLOYMENTS:
        from runtime.abi3.capability import Capability
        from runtime.abi3.verifier import verify_deployment

        capability = Capability.from_dict(json.loads(CAPS[target].read_text()))
        if target == "wafer":
            from compiler.backends.rom.deepseek_v41 import lower_to_abi3
        else:
            from compiler.backends.rom.deepseek_v41_array import lower_to_abi3
        deployment = lower_to_abi3(graph, capability)
        assert verify_deployment(deployment, capability).admitted
        _DEPLOYMENTS[target] = deployment
    return _DEPLOYMENTS[target]


def _join_operators(deployment, kernel_index: int) -> dict[str, dict]:
    """The prefill (reads the current rows, slot 0) and decode (reads the
    window, slot 1) operators of one KV join."""
    table = deployment.table
    found: dict[str, dict] = {}
    for i in range(len(table)):
        payload = dict(table[i].payload or {})
        if "output_view_0" not in payload:
            continue
        if int(payload.get("source_kernel_id", NO_ID)) != kernel_index:
            continue
        if payload.get("input_view_0", NO_ID) != NO_ID:
            found.setdefault("prefill", payload)
        elif payload.get("input_view_1", NO_ID) != NO_ID:
            found.setdefault("decode", payload)
    return found


def _resolve(deployment, view_id: int, symbols: dict[int, int]):
    """Resolve at iteration 0 of every loop the view names (each join loop
    runs once at these requests), with no layer offset."""
    from runtime.sim.memory import ViewResolver

    resolver = ViewResolver(deployment, None)
    payload = deployment.table[view_id].payload
    loops = {
        int(payload[f"term{slot}_index"]): 0
        for slot in range(int(payload["dynamic_term_count"]))
        if int(payload[f"term{slot}_kind"]) == 0
    }
    return resolver.resolve(view_id, loops, symbols)


def _ratio1_joins(graph) -> list[int]:
    tensors = {t.tensor_id: t for t in graph.tensors}
    joins = []
    for kernel in graph.kernels:
        if kernel.kind != "CONCAT" or "phase_inputs" not in kernel.attributes:
            continue
        leading = tensors[kernel.outputs[0]].shape[0]
        if getattr(leading, "symbol", None) == "span_tokens" and int(
            getattr(leading, "multiplier", 1)
        ) == 2:
            joins.append(kernel.index)
    return joins


@pytest.mark.parametrize("target", ["wafer", "array64"])
def test_ratio1_prefill_join_lays_its_segments_end_to_end(graph, target) -> None:
    from runtime.abi3.descriptors import Symbol

    joins = _ratio1_joins(graph)
    assert len(joins) == 20  # layers 20-39
    deployment = _deployment(graph, target)
    span = 10
    symbols = {
        int(Symbol.SPAN_TOKENS): span,
        int(Symbol.POSITION_START): 0,
        int(Symbol.CONTEXT_LENGTH): span,
    }
    emitted = 0
    for kernel_index in joins:
        # Layers the program runs in a layer loop share their representative's
        # operators; the representative is the one that carries them.
        operators = _join_operators(deployment, kernel_index)
        if not operators:
            continue
        emitted += 1
        prefill = operators["prefill"]
        current = _resolve(deployment, prefill["input_view_0"], symbols)
        compressed = _resolve(deployment, prefill["input_view_2"], symbols)
        out = _resolve(deployment, prefill["output_view_0"], symbols)
        # ONE operator covers the whole span: GROUPED_CONCAT then writes every
        # current row, then every compressed row, which is the order the
        # attention indices address.  The per-token form presented (1, 512),
        # (1, 512) -> (2, 512) and interleaved them.
        assert current.dims == (span, 512), (kernel_index, current.dims)
        assert compressed.dims == (span, 512), (kernel_index, compressed.dims)
        assert out.dims == (2 * span, 512), (kernel_index, out.dims)
        # ...and the block starts at row 0 of the fused plane.
        assert out.element_offset == deployment.table[
            prefill["output_view_0"]
        ].payload["element_offset"]
    assert emitted >= 1
