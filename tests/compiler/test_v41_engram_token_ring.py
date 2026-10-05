"""V4.1's Engram token ring holds the whole committed sequence, on every backend.

``main.compressed_token_ids`` declares ``committed_row: absolute_position``: the
compressed id of position ``p`` is row ``p`` of the ``token_ring`` state, and
``DMA.NGRAM_HASH`` reads the committed prefix ``[0, CONTEXT_LENGTH)`` -- its
output rows are the LAST ``span`` positions of the sequence it is given.

Measured before the fix (``results/abi3/deepseek_v41_state_read_results_were_unbound.json``,
``open``): HBM wrote the ring at rows ``[0, span)`` and the hash read ``[0, span)``,
so a decode step overwrote id 0 and hashed a one-token sequence -- device decode
at context 14 matched a prefill of the same 14 tokens through layer 0 and fell to
cosine 0.887 right after the layer-1 Engram.  The ROM lowering read the right
prefix but WROTE ``[0, CONTEXT_LENGTH)`` from a host window that holds only this
request's ids, so ring row 0 became the new token and rows 1.. kept stale ones.

Each test resolves the emitted views through ``runtime.sim.memory.ViewResolver``
at a prefill and at a decode step and checks the writer lands where the reader
looks.  They need the shipped V4.1 Kernel IR under ``build/`` and skip without it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CAP = REPO / "configs/hardware/abi3_capability"
CELLS = {
    "hbm_c512": (
        "compiler.backends.hbm_sram.lower",
        REPO / "build/ir-v3/deepseek-v4.1-flash-c512-amE10/kernel_ir.v3.json",
        CAP / "hbm_sram_cluster_n_comparator_8_e4096.json",
    ),
    "rom_wafer_c8192": (
        "compiler.backends.rom.deepseek_v41",
        REPO / "build/ir-v3/deepseek-v4.1-flash-c8192-amE10/kernel_ir.v3.json",
        CAP / "rom_deepseek_v41_wafer.json",
    ),
    "rom_array64_c8192": (
        "compiler.backends.rom.deepseek_v41_array",
        REPO / "build/ir-v3/deepseek-v4.1-flash-c8192-amE10/kernel_ir.v3.json",
        CAP / "rom_deepseek_v41_array_64.json",
    ),
}
NO_ID = 0xFFFFFFFF
RING = "main.compressed_token_ids.committed"


def _lower(cell: str):
    import importlib

    from compiler.ir.v3.kernel_ir import KernelGraph
    from runtime.abi3.capability import Capability
    from runtime.abi3.verifier import verify_deployment

    module, ir, cap = CELLS[cell]
    if not ir.exists():
        pytest.skip(f"{ir.relative_to(REPO)} is not built")
    graph = KernelGraph.read(ir)
    capability = Capability.from_dict(json.loads(cap.read_text()))
    deployment = importlib.import_module(module).lower_to_abi3(graph, capability)
    assert verify_deployment(deployment, capability).admitted
    return graph, deployment


def _operators(deployment, kernel_index: int) -> list[dict]:
    table = deployment.table
    found = []
    for i in range(len(table)):
        payload = dict(table[i].payload or {})
        if "output_view_0" not in payload:
            continue
        if int(payload.get("source_kernel_id", NO_ID)) == kernel_index:
            found.append(payload)
    return found


def _resolve(deployment, view_id: int, symbols: dict[int, int]):
    from runtime.sim.memory import ViewResolver

    payload = deployment.table[view_id].payload
    loops = {
        int(payload[f"term{slot}_index"]): 0
        for slot in range(int(payload["dynamic_term_count"]))
        if int(payload[f"term{slot}_kind"]) == 0
    }
    return ViewResolver(deployment, None).resolve(view_id, loops, symbols)


def _symbols(position_start: int, span: int) -> dict[int, int]:
    from runtime.abi3.descriptors import Symbol

    return {
        int(Symbol.SPAN_TOKENS): span,
        int(Symbol.POSITION_START): position_start,
        int(Symbol.POSITION_END): position_start + span,
        int(Symbol.CONTEXT_LENGTH): position_start + span,
    }


@pytest.mark.parametrize("cell", sorted(CELLS))
def test_ring_writes_after_the_history_and_the_hash_reads_all_of_it(cell) -> None:
    graph, deployment = _lower(cell)
    writer = next(k for k in graph.kernels if RING in k.outputs)
    readers = [k for k in graph.kernels if RING in k.inputs]
    assert str(writer.attributes.get("committed_row")) == "absolute_position"
    assert readers and all(k.kind == "NGRAM_HASH" for k in readers)
    (write,) = _operators(deployment, writer.index)
    reads = [op for k in readers for op in _operators(deployment, k.index)]
    assert reads  # the representative Engram layer's hashes

    for position_start, span in ((0, 12), (13, 1), (40, 3)):
        symbols = _symbols(position_start, span)
        ids = _resolve(deployment, write["input_view_0"], symbols)
        out = _resolve(deployment, write["output_view_0"], symbols)
        # The request's ids, one ring row each, from row POSITION_START on.
        assert ids.dims[0] == span, (cell, position_start, ids.dims)
        assert out.dims[0] == span, (cell, position_start, out.dims)
        row = out.strides[0]
        for op in reads:
            prefix = _resolve(deployment, op["input_view_0"], symbols)
            assert prefix.object_id == out.object_id
            # The hash is handed the whole committed prefix [0, context) ...
            assert prefix.dims[0] == position_start + span, (
                cell,
                position_start,
                prefix.dims,
            )
            # ... and the ids this step writes are its LAST ``span`` rows, which
            # is what the engine's output rows correspond to.
            assert out.element_offset == prefix.element_offset + position_start * row
            hashed = _resolve(deployment, op["output_view_0"], symbols)
            assert hashed.dims[0] == span
