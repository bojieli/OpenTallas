"""Both V4.1 lanes lower the candidate pool's block ranking as a BLOCK ranking.

Layer 20's pool is ``BLOCK_MAX -> INDEX_TOPK (block select) -> CANDIDATE_MASK``,
and layers 21-39 read the plane.  The block select ranks candidate BLOCKS, so
its ``ROUTE.INDEX_TOPK`` must carry ``RANKS_BLOCKS`` above the mask mode: its
IDs index the plane's block axis and must not be rebased above the joined KV
rows, and the block holding the query's newest position is pinned.

The ROM lane set the bit when the pool landed; the HBM lane never did, so every
block ID it produced came back rebased by the context -- block 0 at P10 was
block 10 (positions 80-87 of a 512-wide plane) -- and the pool admitted nothing
a query could reach.  That was the first ROM/HBM prefill difference
(L24.ffn_norm rows 7-9, ``results/abi3/deepseek_v41_rom_join_context_engram.json``
``open``).  Every KV-ranking INDEX_TOPK must keep rebasing, so the bit is
checked in both directions.

Needs the shipped V4.1 Kernel IR under ``build/`` and skips without it.
"""

from __future__ import annotations

import importlib
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


@pytest.mark.parametrize("cell", sorted(CELLS))
def test_only_the_block_select_ranks_blocks(cell: str) -> None:
    from compiler.ir.v3.kernel_ir import KernelGraph
    from runtime.abi3.capability import Capability
    from runtime.abi3.constants import Major, Route
    from runtime.abi3.verifier import verify_deployment
    from runtime.sim.engines.route import RANKS_BLOCKS

    module, ir, cap = CELLS[cell]
    if not ir.exists():
        pytest.skip(f"{ir.relative_to(REPO)} is not built")
    graph = KernelGraph.read(ir)
    capability = Capability.from_dict(json.loads(cap.read_text()))
    deployment = importlib.import_module(module).lower_to_abi3(graph, capability)
    assert verify_deployment(deployment, capability).admitted

    block_kernels = {
        index
        for index, kernel in enumerate(graph.kernels)
        if kernel.kind == "INDEX_TOPK" and "block" in kernel.attributes
    }
    assert block_kernels, "the V4.1 graph declares no candidate-pool block select"
    ranks, rebases = {}, {}
    table = deployment.table
    for i in range(len(table)):
        payload = dict(table[i].payload or {})
        if (
            payload.get("engine_family") != int(Major.ROUTE)
            or payload.get("engine_sub") != int(Route.INDEX_TOPK)
        ):
            continue
        kernel = int(payload.get("source_kernel_id", NO_ID))
        mode = payload.get("aux_id_1", NO_ID)
        flagged = mode != NO_ID and bool(int(mode) & RANKS_BLOCKS)
        (ranks if kernel in block_kernels else rebases)[i] = flagged
    assert ranks and all(ranks.values()), (
        f"{cell}: block-select INDEX_TOPK operators without RANKS_BLOCKS: "
        f"{sorted(i for i, flagged in ranks.items() if not flagged)}"
    )
    assert rebases and not any(rebases.values()), (
        f"{cell}: KV-ranking INDEX_TOPK operators that stopped rebasing: "
        f"{sorted(i for i, flagged in rebases.items() if flagged)}"
    )


@pytest.mark.parametrize("cell", sorted(CELLS))
def test_every_separated_join_select_states_its_decode_rebase(cell: str) -> None:
    """V4.1's KV-ranking selects join behind a 128-row window in a separate CONCAT.

    ``ROUTE.INDEX_TOPK`` then has no window operand to measure, so the lowering
    states the window capacity above bit 16 of ``aux_id_1``; before it did, a
    decode selection was rebased by zero and attended window rows instead of the
    compressed rows (the HBM decode/prefill step at L02.ffn_norm, cosine 0.915).
    The block select must not carry it.
    """
    from compiler.ir.v3.kernel_ir import KernelGraph
    from runtime.abi3.capability import Capability
    from runtime.abi3.constants import Major, Route
    from runtime.sim.engines.route import DECODE_REBASE_SHIFT

    module, ir, cap = CELLS[cell]
    if not ir.exists():
        pytest.skip(f"{ir.relative_to(REPO)} is not built")
    graph = KernelGraph.read(ir)
    capability = Capability.from_dict(json.loads(cap.read_text()))
    deployment = importlib.import_module(module).lower_to_abi3(graph, capability)
    selects = {
        index: kernel
        for index, kernel in enumerate(graph.kernels)
        if kernel.kind == "INDEX_TOPK"
    }
    seen: dict[int, int] = {}
    table = deployment.table
    for i in range(len(table)):
        payload = dict(table[i].payload or {})
        if (
            payload.get("engine_family") != int(Major.ROUTE)
            or payload.get("engine_sub") != int(Route.INDEX_TOPK)
        ):
            continue
        kernel = int(payload.get("source_kernel_id", NO_ID))
        mode = int(payload.get("aux_id_1", NO_ID))
        seen[kernel] = 0 if mode == NO_ID else mode >> DECODE_REBASE_SHIFT
    blocks = {i for i, k in selects.items() if "block" in k.attributes}
    assert blocks and all(seen[i] == 0 for i in blocks)
    ranked = [i for i in selects if i not in blocks]
    # A banded lane issues one descriptor for several layers under the first
    # layer's kernel ID, so a kernel with no operator of its own is covered by
    # its band's.
    issued = [i for i in ranked if i in seen]
    wrong = {selects[i].kernel_id: seen[i] for i in issued if seen[i] != 128}
    assert issued and not wrong, wrong
