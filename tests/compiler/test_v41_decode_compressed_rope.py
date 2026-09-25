"""A V4.1 decode step rotates a completed compression group at its FIRST position.

The released ``Attention._compress_kv`` / ``Indexer.forward`` rotate the latent a
decode step completes with ``freqs_cis[start_pos + 1 - ratio]``: the group stands
for its first token.  Both lanes already select that row for V4 through
``floor_div_indices_v1`` and a ratio-strided coefficient table -- but only for a
GATHER marked ``compressed``, which is the V4 exporter's spelling.  The V4.1
exporter states only ``position_stride``, so on layers 2, 8 and 14 (ratio 2) the
decode path read the plain position ``p``: every compressed KV row and index key
a decode step completed was rotated one position late.  Measured on the reduced
V4.1 HBM cell: after the decode rebase fix, L02.ffn_norm decode/prefill cosine
0.999989 with the newest compressed row differing by up to 1.81.

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


def test_either_exporter_spelling_is_a_compressed_rope_gather() -> None:
    from types import SimpleNamespace

    from compiler.ir.v3.lowering import compressed_rope_gather

    def kernel(kind: str, **attributes: object) -> SimpleNamespace:
        return SimpleNamespace(kind=kind, attributes=attributes)

    assert compressed_rope_gather(kernel("GATHER", compressed=True, position_stride=4))
    assert compressed_rope_gather(kernel("GATHER", position_stride=2))
    assert not compressed_rope_gather(kernel("GATHER", position_stride=1))
    assert not compressed_rope_gather(kernel("GATHER"))
    assert not compressed_rope_gather(kernel("ROPE", position_stride=2))


@pytest.mark.parametrize("cell", sorted(CELLS))
def test_decode_rotates_the_group_at_its_first_position(cell: str) -> None:
    from compiler.ir.v3.kernel_ir import KernelGraph
    from runtime.abi3.capability import Capability

    module, ir, cap = CELLS[cell]
    if not ir.exists():
        pytest.skip(f"{ir.relative_to(REPO)} is not built")
    graph = KernelGraph.read(ir)
    capability = Capability.from_dict(json.loads(cap.read_text()))
    deployment = importlib.import_module(module).lower_to_abi3(graph, capability)
    gathers = {
        index: kernel
        for index, kernel in enumerate(graph.kernels)
        if kernel.kind == "GATHER"
        and int(kernel.attributes.get("position_stride", 1) or 1) > 1
    }
    assert gathers, "the V4.1 graph declares no pooled rotary gather"
    table = deployment.table
    found: dict[int, bool] = {}
    for i in range(len(table)):
        payload = dict(table[i].payload or {})
        kernel = int(payload.get("source_kernel_id", NO_ID))
        if kernel not in gathers or "input_view_0" not in payload:
            continue
        ratio = int(gathers[kernel].attributes["position_stride"])
        index = dict(table[payload["input_view_0"]].payload)
        source = deployment.objects[int(table[payload["input_view_0"]].primary_object_id)]
        coefficients = dict(table[payload["input_view_1"]].payload)
        width = int(coefficients["dim1"])
        decode_form = (
            getattr(source, "generator", None) == "floor_div_indices_v1"
            and int(dict(source.parameters)["divisor"]) == ratio
            and int(index["dim0"]) == 1
            and int(coefficients["stride0"]) == ratio * width
        )
        found[kernel] = found.get(kernel, False) or decode_form
    assert found, f"{cell}: no operator issues a pooled rotary gather"
    missing = sorted(gathers[k].kernel_id for k, ok in found.items() if not ok)
    assert not missing, f"{cell}: decode reads the plain position for {missing}"
