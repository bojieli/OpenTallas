"""A STATE_READ result is the state it re-presents, on both backends.

V4.1 declares 72 STATE_READ results ``role: activation`` -- every non-owning
layer's ``compressed_view.valid``, every shared-index ``indexer.reuse.selection``
and every ``pool_read.admission``.  Both backends keyed the state binding on the
tensor's role, so each became an activation buffer: the reused selection was an
object NOTHING writes (layer 3 read 512 zeros per query instead of layer 2's
published indices) and the compressed-KV views read whatever activation last
occupied their arena slot.  Nothing traps: the views are in bounds and the
objects legal.  Measured and recorded in
``results/abi3/deepseek_v41_state_read_results_were_unbound.json``.

These tests need the shipped V4.1 Kernel IR under ``build/`` and skip without it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HBM_IR = REPO / "build/ir-v3/deepseek-v4.1-flash-c512-amE10/kernel_ir.v3.json"
ROM_IR = REPO / "build/ir-v3/deepseek-v4.1-flash-c8192-amE10/kernel_ir.v3.json"
HBM_CAP = (
    REPO / "configs/hardware/abi3_capability/hbm_sram_cluster_n_comparator_8_e4096.json"
)
ROM_CAP = REPO / "configs/hardware/abi3_capability/rom_deepseek_v41_wafer.json"
NO_ID = 0xFFFFFFFF


def _capability(path: Path):
    from runtime.abi3.capability import Capability

    return Capability.from_dict(json.loads(path.read_text()))


def _graph(path: Path):
    if not path.exists():
        pytest.skip(f"{path.relative_to(REPO)} is not built")
    from compiler.ir.v3.kernel_ir import KernelGraph

    return KernelGraph.read(path)


def _unwritten_zero_objects_read(deployment) -> dict[int, set[int]]:
    """Zero-initialised objects an operator reads and no operator writes."""
    table = deployment.table
    zero = {
        int(object_id)
        for object_id, source in deployment.objects.items()
        if source.kind == "zero"
    }
    views = {
        i: int(table[i].primary_object_id)
        for i in range(len(table))
        if table[i].type_name == "TENSOR_VIEW"
    }
    written: set[int] = set()
    read: dict[int, set[int]] = {}
    for i in range(len(table)):
        payload = dict(table[i].payload or {})
        if "output_view_0" not in payload:
            continue
        for slot in range(2):
            view = payload.get(f"output_view_{slot}", NO_ID)
            if view in views:
                written.add(views[view])
        for slot in range(4):
            view = payload.get(f"input_view_{slot}", NO_ID)
            if view in views:
                read.setdefault(views[view], set()).add(
                    int(payload.get("source_kernel_id", NO_ID))
                )
    return {
        obj: kernels
        for obj, kernels in read.items()
        if obj in zero and obj not in written
    }


def test_hbm_binds_every_state_read_result_to_its_source_state() -> None:
    from compiler.backends.hbm_sram.plan import build_plan

    graph = _graph(HBM_IR)
    plan = build_plan(graph, _capability(HBM_CAP))
    reads = [k for k in graph.kernels if k.kind == "STATE_READ"]
    assert reads
    for kernel in reads:
        source = plan.state_of_tensor.get(kernel.inputs[0])
        result = plan.state_of_tensor.get(kernel.outputs[0])
        assert source is not None, kernel.kernel_id
        assert result is not None and list(result)[:2] == list(source)[:2], (
            f"{kernel.kernel_id}: result bound to {result}, source to {source}"
        )


def test_hbm_reused_state_is_read_where_it_was_written() -> None:
    from compiler.backends.hbm_sram.lower import lower_to_abi3
    from runtime.abi3.verifier import verify_deployment

    capability = _capability(HBM_CAP)
    deployment = lower_to_abi3(_graph(HBM_IR), capability)
    assert verify_deployment(deployment, capability).admitted
    assert _unwritten_zero_objects_read(deployment) == {}


def test_rom_reused_selection_is_read_where_it_was_written() -> None:
    from compiler.backends.rom.deepseek_v41 import lower_to_abi3
    from runtime.abi3.verifier import verify_deployment

    capability = _capability(ROM_CAP)
    deployment = lower_to_abi3(_graph(ROM_IR), capability)
    assert verify_deployment(deployment, capability).admitted
    graph = _graph(ROM_IR)
    reuse_joins = {
        k.index
        for k in graph.kernels
        if k.kernel_id.endswith("indexer.reuse.index_join")
    }
    assert reuse_joins
    unwritten = _unwritten_zero_objects_read(deployment)
    assert not any(kernels & reuse_joins for kernels in unwritten.values()), unwritten


def test_rom_array_reused_selection_is_read_where_it_was_written() -> None:
    """The array caps a scratch plane to one query block, so the selection is a
    buffer there -- and the reusing layers must read the producer's buffer."""
    from compiler.backends.rom.deepseek_v41_array import lower_to_abi3
    from runtime.abi3.verifier import verify_deployment

    capability = _capability(
        REPO / "configs/hardware/abi3_capability/rom_deepseek_v41_array_64.json"
    )
    graph = _graph(ROM_IR)
    deployment = lower_to_abi3(graph, capability)
    assert verify_deployment(deployment, capability).admitted
    readers = {
        k.index
        for k in graph.kernels
        if k.kernel_id.endswith("indexer.reuse.index_join")
        or any(name.endswith("pool_read.admission") for name in k.inputs)
    }
    assert readers
    unwritten = _unwritten_zero_objects_read(deployment)
    assert not any(kernels & readers for kernels in unwritten.values()), unwritten
