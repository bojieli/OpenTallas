"""AM-E9: one SCHEDULE emission rule, both backends.

``docs/CHIP_ARCHITECTURE_DESIGN.md`` section 3.8 / 7.2 / 10.1 (AM-E9): the two
lowerings of one graph must carry identical SCHEDULE fields wherever the
operator is the same.  AM-E9 v2 closes the last exception: ``bank_mask`` is one
activation-buffer placement over the scratchpad both vehicles declare, not a
per-store value, because ``runtime.cycle.model.MemorySystem.schedule`` charges
the field to the SRAM class on both sides.  These tests pin the rule itself,
the values it produces for the Qwen shapes, and -- the property the comparison
protocol rests on -- that the ROM and HBM backends emit the same tiled fields,
and now the same banks, for the same neutral kernel.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compiler.backends.hbm_sram.capability import (
    cluster32_capability,
    single_chip_capability,
)
from compiler.backends.hbm_sram.lower import lower_to_abi3 as hbm_lower
from compiler.backends.rom.common.check import check_rom_schedule
from compiler.backends.rom.qwen3 import (
    build_qwen3_rom_deployment,
    qwen3_rom_capability,
)
from compiler.backends.schedule_rule import (
    COLUMN_LANE_FAMILIES,
    E9_OUTSTANDING,
    E9_QUEUES,
    E9_TILE_COLS,
    E9_TILE_DEPTH,
    ENGINE_STAGING_REGIONS,
    STAGING_BANK,
    STAGING_REGIONS,
    OperatorShape,
    choose_tile,
    column_lane_bound,
    declared_view_rows,
    e9_schedule,
    family_ordinals,
    operator_shape,
    queue_count,
    queue_ordinal,
    request_narrows_rows,
    sram_banks,
    sram_ports,
    staging_bank_mask,
)
from compiler.ir.v3.kernel_ir import KernelGraph
from runtime.abi3.capability import Capability
from runtime.abi3.constants import NO_ID, Dma, Major, StorageClass
from runtime.abi3.descriptors import ExtendedDescriptorType
from runtime.abi3.verifier import verify_deployment

from test_hbm_sram_backend import dense_graph
from test_rom_backend import _mutate_descriptor, qwen_shaped_graph

REPO = Path(__file__).resolve().parents[2]
ROM_CAPABILITY = REPO / "configs/hardware/abi3_capability/rom_qwen3.json"
HBM_CAPABILITY = REPO / "configs/hardware/abi3_capability/hbm_sram_single_chip.json"
QWEN_IR = REPO / "build/ir-v3/qwen3-8b/kernel_ir.v3.json"

#: The SCHEDULE fields the rule fixes: every field the cycle model tiles by
#: (``runtime.cycle.model.tile_mapping``), ``bank_mask`` included since
#: AM-E9 v2.
UNIFIED_FIELDS = (
    "tile_rows",
    "tile_cols",
    "tile_depth",
    "issue_window",
    "max_outstanding",
    "queue_index",
    "port_mask",
    "bank_mask",
    "noc_route_class",
)


def _capability(path: Path) -> Capability:
    return Capability.from_dict(json.loads(path.read_text()))


def _operator_schedules(deployment):
    """``[(family, sub, source_kernel_id, schedule payload)]`` in program order."""
    table = {d.descriptor_id: d for d in deployment.table.descriptors()}
    rows = []
    for d in deployment.table.descriptors():
        if d.descriptor_type != ExtendedDescriptorType.OPERATOR:
            continue
        schedule = table[int(d.payload["schedule_id"])].payload
        rows.append(
            (
                int(d.payload["engine_family"]),
                int(d.payload["engine_sub"]),
                int(d.payload["source_kernel_id"]),
                {k: int(v) for k, v in schedule.items()},
            )
        )
    return rows


# ---------------------------------------------------------------------------
# The rule itself
# ---------------------------------------------------------------------------
def test_choose_tile_is_the_largest_divisor_at_or_below_the_target():
    assert choose_tile(4096, 64) == 64
    assert choose_tile(151936, 64) == 64
    assert choose_tile(100, 64) == 50
    assert choose_tile(1, 64) == 1
    assert choose_tile(7, 64) == 7
    with pytest.raises(ValueError):
        choose_tile(0, 64)


@pytest.mark.parametrize("capability_path", [ROM_CAPABILITY, HBM_CAPABILITY])
def test_the_qwen_shapes_take_the_design_values_on_both_vehicles(capability_path):
    """Section 7.2: tile 64 x 128, issue_window = max_outstanding = 16.

    The same shape on either vehicle capability produces the same fields; the
    only vehicle-dependent input the rule reads is the queue and port count,
    and both vehicles serve the pair minimum.
    """
    capability = _capability(capability_path)
    # q_proj / o_proj: 512-row block, N 4096, K 4096.
    rule = e9_schedule(
        OperatorShape(rows=512, cols=4096, reduction=4096, contracts=True),
        Major.TENSOR, capability, ordinal=1,
    )
    assert (rule.tile_rows, rule.tile_cols, rule.tile_depth) == (512, 64, 128)
    assert rule.tiles == 64 * 32
    assert rule.issue_window == rule.max_outstanding == E9_OUTSTANDING
    assert rule.queue_index == 1
    assert rule.port_mask == 0b11
    # down_proj: K 12288 -> 96 depth tiles.
    down = e9_schedule(
        OperatorShape(rows=512, cols=4096, reduction=12288, contracts=True),
        Major.TENSOR, capability, ordinal=6,
    )
    assert (down.tile_cols, down.tile_depth, down.tiles) == (64, 128, 64 * 96)
    # lm_head at one row: the width 151936 takes 64 (= 64 x 2374).
    head = e9_schedule(
        OperatorShape(rows=1, cols=151936, reduction=4096, contracts=True),
        Major.TENSOR, capability, ordinal=0,
    )
    assert (head.tile_rows, head.tile_cols, head.tile_depth) == (1, 64, 128)
    assert head.max_outstanding == E9_OUTSTANDING
    # GQA attention: head_dim 128, context bound 8256 positions -> 128-position
    # blocks with a partial tail, never the divisor 96.
    gqa = e9_schedule(
        OperatorShape(rows=512, cols=128, reduction=8256, contracts=True),
        Major.ATTENTION, capability, ordinal=0,
    )
    assert (gqa.tile_rows, gqa.tile_cols, gqa.tile_depth) == (512, 64, E9_TILE_DEPTH)
    assert gqa.tiles == 2 * 65
    assert gqa.issue_window == gqa.max_outstanding == E9_OUTSTANDING
    assert gqa.queue_index == 0
    # RMS_NORM at width 4096: a pass, depth 1, 64 tiles.
    norm = e9_schedule(
        OperatorShape(rows=512, cols=4096, reduction=1, contracts=False),
        Major.VECTOR, capability, ordinal=0,
    )
    assert (norm.tile_rows, norm.tile_cols, norm.tile_depth, norm.tiles) == (512, 64, 1, 64)
    assert norm.max_outstanding == E9_OUTSTANDING
    # The 128-wide head ops have two tiles and carry that as their bound.
    rope = e9_schedule(
        OperatorShape(rows=512, cols=128, reduction=1, contracts=False),
        Major.VECTOR, capability, ordinal=3,
    )
    assert (rope.tiles, rope.issue_window, rope.max_outstanding) == (2, 2, 2)
    # Per-token rope coefficient gather: one row, 256 wide.
    gather = e9_schedule(
        OperatorShape(rows=1, cols=256, reduction=1, contracts=False),
        Major.DMA, capability, ordinal=0,
    )
    assert (gather.tile_rows, gather.tile_cols, gather.tile_depth) == (1, 64, 1)
    assert (gather.tiles, gather.max_outstanding) == (4, 4)
    # ARGMAX / TOKEN_APPEND: one element.
    argmax = e9_schedule(
        OperatorShape(rows=1, cols=1, reduction=1, contracts=False),
        Major.SELECTION, capability, ordinal=0,
    )
    assert (argmax.tile_rows, argmax.tile_cols, argmax.tile_depth) == (1, 1, 1)
    assert argmax.issue_window == argmax.max_outstanding == 1
    assert argmax.queue_index == 0


def test_tile_cols_is_the_design_width_and_mover_lanes_do_not_narrow_it():
    """[T2.1-3] 64 columns; a DMA engine's 8 ``lanes`` are movers, not columns."""
    hbm = _capability(HBM_CAPABILITY)
    rom = _capability(ROM_CAPABILITY)
    assert hbm.engines["dma"]["lanes"] == 8
    assert hbm.engines["selection"]["lanes"] == 8
    assert int(Major.DMA) not in COLUMN_LANE_FAMILIES
    assert column_lane_bound(Major.DMA, hbm) == E9_TILE_COLS
    assert column_lane_bound(Major.SELECTION, hbm) == E9_TILE_COLS
    # The route engine's lanes are key lanes (section 3.8), not columns.
    assert hbm.engines["route"]["lanes"] == 32
    assert column_lane_bound(Major.ROUTE, hbm) == E9_TILE_COLS
    # Column-lane families are bounded by what they advertise, and every
    # advertised count on the Qwen pair is at least the design width.
    assert COLUMN_LANE_FAMILIES == {
        int(Major.TENSOR), int(Major.VECTOR), int(Major.ATTENTION), int(Major.REDUCTION)
    }
    for family in COLUMN_LANE_FAMILIES:
        for capability in (rom, hbm):
            assert column_lane_bound(family, capability) >= E9_TILE_COLS
    # A capability advertising fewer column lanes narrows the tile.
    narrow = Capability.from_dict({
        **hbm.to_dict(),
        "engines": {**hbm.engines, "vector": {"lanes": 32, "queues": 2}},
    })
    assert column_lane_bound(Major.VECTOR, narrow) == 32
    rule = e9_schedule(
        OperatorShape(rows=512, cols=4096, reduction=1, contracts=False),
        Major.VECTOR, narrow, ordinal=0,
    )
    assert rule.tile_cols == 32


def test_queues_are_the_pair_minimum_and_a_reserved_queue_comes_off_the_top():
    rom = _capability(ROM_CAPABILITY)
    hbm = _capability(HBM_CAPABILITY)
    cluster = cluster32_capability()
    for family in (Major.TENSOR, Major.VECTOR, Major.DMA, Major.ATTENTION, Major.SELECTION):
        assert queue_count(family, rom) == queue_count(family, hbm) == E9_QUEUES[int(family)]
    # The HBM cluster keeps its last DMA queue for the exchange buffer; the
    # ordinary operators still spread over the rule's two.
    assert cluster.engines["dma"]["queues"] == 4
    assert queue_count(Major.DMA, cluster, reserved=1) == 2
    reserved = e9_schedule(
        OperatorShape(rows=512, cols=4096, reduction=1, contracts=False),
        Major.DMA, cluster, ordinal=3, reserved_queues=1,
    )
    assert reserved.queue_index == 1
    assert reserved.queue_index != cluster.engines["dma"]["queues"] - 1


def test_ports_default_to_two_when_unpublished_and_the_mask_names_them_all():
    rom = _capability(ROM_CAPABILITY)
    hbm = _capability(HBM_CAPABILITY)
    assert "ports" not in rom.memory["sram"]
    assert hbm.memory["sram"]["ports"] == 2
    assert sram_ports(rom) == sram_ports(hbm) == 2
    for capability in (rom, hbm):
        rule = e9_schedule(
            OperatorShape(rows=512, cols=4096, reduction=1, contracts=False),
            Major.VECTOR, capability, ordinal=0,
        )
        assert rule.port_mask == 0b11


def test_max_outstanding_never_exceeds_the_capability_limit():
    hbm = _capability(HBM_CAPABILITY)
    tight = Capability.from_dict({
        **hbm.to_dict(),
        "limits": {**hbm.limits, "max_outstanding_per_queue": 4},
    })
    rule = e9_schedule(
        OperatorShape(rows=512, cols=4096, reduction=4096, contracts=True),
        Major.TENSOR, tight, ordinal=0,
    )
    assert rule.issue_window == rule.max_outstanding == 4


@pytest.mark.skipif(not QWEN_IR.exists(), reason="the Qwen IR is a build product")
def test_the_queue_ordinal_is_the_kernels_rank_among_its_family_in_graph_order():
    """Section 10.3 item 4: q/k/v and gate/up land on distinct queues."""
    graph = KernelGraph.read(QWEN_IR)
    ordinals = family_ordinals(graph)
    by_id = {k.kernel_id: k for k in graph.kernels}
    rom = _capability(ROM_CAPABILITY)

    def queue(kernel_id: str) -> int:
        kernel = by_id[kernel_id]
        family, _rank = ordinals[kernel.index]
        return queue_ordinal(ordinals, kernel.index, family) % queue_count(family, rom)

    assert queue("layer.0.attention.query_projection") != queue(
        "layer.0.attention.key_projection"
    )
    assert queue("layer.0.feed_forward.gate_projection") != queue(
        "layer.0.feed_forward.up_projection"
    )
    # An auxiliary operator in another family takes the kernel's graph index.
    kernel = by_id["layer.0.attention.query_projection"]
    assert queue_ordinal(ordinals, kernel.index, int(Major.DMA)) == kernel.index


# ---------------------------------------------------------------------------
# Both backends, one graph, identical tiled fields
# ---------------------------------------------------------------------------
def _assert_pair_is_unified(rom_deployment, hbm_deployment) -> None:
    rom_rows = _operator_schedules(rom_deployment)
    hbm_rows = _operator_schedules(hbm_deployment)
    assert [r[:3] for r in rom_rows] == [h[:3] for h in hbm_rows], (
        "the two backends emit different operators for one graph"
    )
    for (family, sub, kernel_index, rom_sched), (_f, _s, _k, hbm_sched) in zip(
        rom_rows, hbm_rows
    ):
        for field in UNIFIED_FIELDS:
            assert rom_sched[field] == hbm_sched[field], (
                f"kernel {kernel_index} family {family:#x} sub {sub}: "
                f"{field} rom {rom_sched[field]} vs hbm {hbm_sched[field]}"
            )
        # AM-E9 v2: one activation placement.  Both sides name the staging
        # banks of the family's regions, and no operator is emitted
        # unrestricted (0, which the cycle model reads as every bank).
        assert rom_sched["bank_mask"] == hbm_sched["bank_mask"] != 0
    # The design values are what the pair carries.
    tensor = [r for r in rom_rows if r[0] == int(Major.TENSOR)]
    assert tensor
    assert {r[3]["tile_cols"] for r in rom_rows if r[3]["tile_cols"] != 1} <= {
        E9_TILE_COLS
    } | {
        choose_tile(c, E9_TILE_COLS) for c in range(1, E9_TILE_COLS)
    }
    assert all(r[3]["issue_window"] == r[3]["max_outstanding"] for r in rom_rows)
    assert all(r[3]["max_outstanding"] <= E9_OUTSTANDING for r in rom_rows)
    assert all(r[3]["port_mask"] == 0b11 for r in rom_rows + hbm_rows)


def _assert_every_schedule_is_the_rule(graph, deployment, capability) -> None:
    """Each backend emits exactly ``e9_schedule`` of the neutral kernel.

    ``rows`` is the backend's dispatch rows and is taken from the descriptor;
    every other tiled field must be the rule's value for the kernel's shape,
    family and graph ordinal -- no private policy may survive on either side.
    """
    kernels = {k.index: k for k in graph.kernels}
    tensors = (
        dict(graph.tensors)
        if isinstance(graph.tensors, dict)
        else {t.tensor_id: t for t in graph.tensors}
    )
    ordinals = family_ordinals(graph)
    rows = _operator_schedules(deployment)
    assert rows
    for family, sub, kernel_index, payload in rows:
        kernel = kernels[kernel_index]
        own = ordinals.get(kernel_index, (None, 0))[0] == family
        shape = operator_shape(
            kernel, tensors, family, sub,
            rows=payload["tile_rows"], capability=capability,
        )
        if not own:
            shape = OperatorShape(shape.rows, shape.cols, 1, False)
        rule = e9_schedule(
            shape, family, capability,
            ordinal=queue_ordinal(ordinals, kernel_index, family),
        )
        assert payload["tile_cols"] == rule.tile_cols, (kernel.kernel_id, family)
        assert payload["tile_depth"] == rule.tile_depth, (kernel.kernel_id, family)
        assert payload["issue_window"] == rule.issue_window, (kernel.kernel_id, family)
        assert payload["max_outstanding"] == rule.max_outstanding, (kernel.kernel_id, family)
        assert payload["queue_index"] == rule.queue_index, (kernel.kernel_id, family)
        assert payload["port_mask"] == rule.port_mask, (kernel.kernel_id, family)
        assert payload["bank_mask"] == rule.bank_mask, (kernel.kernel_id, family)
        assert payload["bank_mask"] == staging_bank_mask(family, capability)
        assert payload["issue_window"] == payload["max_outstanding"]
        assert payload["tile_cols"] <= E9_TILE_COLS
        assert payload["tile_depth"] <= E9_TILE_DEPTH
        assert payload["max_outstanding"] <= E9_OUTSTANDING


# ---------------------------------------------------------------------------
# AM-E9 v2: one activation-buffer placement
# ---------------------------------------------------------------------------
def test_the_staging_placement_is_one_bank_per_region_and_fits_both_vehicles():
    """One declared table, one bank each, inside both published scratchpads.

    ``runtime.cycle.model.MemorySystem.schedule`` applies ``bank_mask`` to the
    SRAM class alone, so the field is only meaningful over a scratchpad both
    vehicles have.  Both publish 32 banks ([T2.1-20]), so the declared
    placement is expressible on either.
    """
    assert list(STAGING_BANK.values()) == list(range(len(STAGING_REGIONS)))
    assert len(set(STAGING_REGIONS)) == len(STAGING_REGIONS)
    for capability in (_capability(ROM_CAPABILITY), _capability(HBM_CAPABILITY)):
        assert sram_banks(capability) == 32
        assert max(STAGING_BANK.values()) < sram_banks(capability)
    for family, regions in ENGINE_STAGING_REGIONS.items():
        assert regions, family
        assert set(regions) <= set(STAGING_REGIONS), family


def test_both_vehicles_derive_the_same_bank_mask_for_every_family():
    """The mask is a fact about the engine family, not about the chip."""
    rom = _capability(ROM_CAPABILITY)
    hbm = _capability(HBM_CAPABILITY)
    for family in ENGINE_STAGING_REGIONS:
        mask = staging_bank_mask(family, rom)
        assert mask == staging_bank_mask(family, hbm)
        assert mask != 0
        # No family is emitted unrestricted: zero is what the cycle model
        # reads as "every bank", and it was the ROM side's value for every
        # weight-free family before AM-E9 v2.
        assert bin(mask).count("1") == len(ENGINE_STAGING_REGIONS[family])


def test_a_scratchpad_too_narrow_for_the_placement_is_refused():
    hbm = _capability(HBM_CAPABILITY)
    narrow = Capability.from_dict({
        **hbm.to_dict(),
        "memory": {**hbm.memory, "sram": {**hbm.memory["sram"], "banks": 4}},
    })
    with pytest.raises(ValueError):
        staging_bank_mask(int(Major.STATE), narrow)


def test_the_hbm_planner_allocates_the_regions_at_their_declared_banks():
    """The mask names the bank the object actually occupies.

    ``MemorySystem._unit_of`` picks the unit from the address, so a mask over
    a placement the planner did not honour would confine nothing.
    """
    deployment = hbm_lower(dense_graph(), single_chip_capability())
    regions = deployment.notes["sram_regions"]
    assert regions
    for region in regions:
        bank = STAGING_BANK[region["region_id"]]
        assert region["bank_mask"] == 1 << bank, region
        assert region["offset"] == bank * region["size_bytes"], region


def test_the_rom_backend_emits_exactly_the_rule(tmp_path):
    graph = qwen_shaped_graph(tmp_path, layers=2, hidden=1024, span_max=256)
    capability = qwen3_rom_capability(max_context_positions=256, vocabulary_size=32)
    deployment, _plan = build_qwen3_rom_deployment(graph, capability=capability)
    assert verify_deployment(deployment, capability).admitted
    _assert_every_schedule_is_the_rule(graph, deployment, capability)
    rows = _operator_schedules(deployment)
    # A block operator's dispatch covers the token block, never the span
    # maximum; the checker agrees with the emission.
    block = {r[3]["tile_rows"] for r in rows if r[0] == int(Major.TENSOR)}
    assert block <= {1, 256}
    assert 256 in block
    report = check_rom_schedule(graph, deployment, capability)
    assert report["status"] == "pass", report["errors"][:5]


def test_the_hbm_backend_emits_exactly_the_rule():
    graph = dense_graph()
    capability = single_chip_capability()
    deployment = hbm_lower(graph, capability)
    assert verify_deployment(deployment, capability).admitted
    _assert_every_schedule_is_the_rule(graph, deployment, capability)
    rows = _operator_schedules(deployment)
    # issue_window is no longer the queue count and max_outstanding no longer
    # the capability limit: the two origins of the shipped asymmetry.
    tensor_windows = {r[3]["issue_window"] for r in rows if r[0] == int(Major.TENSOR)}
    assert max(tensor_windows) == E9_OUTSTANDING
    assert all(r[3]["max_outstanding"] <= E9_OUTSTANDING for r in rows)
    assert capability.limits["max_outstanding_per_queue"] > E9_OUTSTANDING


@pytest.mark.skipif(not QWEN_IR.exists(), reason="the Qwen IR is a build product")
def test_the_qwen_graph_lowers_to_identical_tiled_fields_on_both_backends():
    """The shipped pair's 31 asymmetries, removed by construction.

    Every one of the asymmetries the C2 audit found in
    ``results/derived/qwen3_n5_design_target_deployment_audit.json`` is in a
    field this rule fixes.  ``bank_mask`` -- the five AM-E9 v1 left, which
    ``results/derived/qwen3_e9_deployment_audit.json`` reports as the whole
    remaining verdict -- is fixed too, by the shared activation placement.
    """
    graph = KernelGraph.read(QWEN_IR)
    rom_capability = _capability(ROM_CAPABILITY)
    hbm_capability = _capability(HBM_CAPABILITY)
    rom_deployment, _plan = build_qwen3_rom_deployment(graph, capability=rom_capability)
    hbm_deployment = hbm_lower(graph, hbm_capability)
    assert verify_deployment(rom_deployment, rom_capability).admitted
    assert verify_deployment(hbm_deployment, hbm_capability).admitted
    _assert_pair_is_unified(rom_deployment, hbm_deployment)
    rows = _operator_schedules(rom_deployment)
    by_kernel = {r[2]: r[3] for r in rows}
    by_id = {k.kernel_id: k.index for k in graph.kernels}
    q = by_kernel[by_id["layer.0.attention.query_projection"]]
    assert (q["tile_rows"], q["tile_cols"], q["tile_depth"]) == (512, 64, 128)
    assert q["issue_window"] == q["max_outstanding"] == 16
    gqa = by_kernel[by_id["layer.0.attention.grouped_query"]]
    assert (gqa["tile_rows"], gqa["tile_cols"], gqa["tile_depth"]) == (512, 64, 128)
    gather = by_kernel[by_id["rope.coefficient_gather"]]
    assert (gather["tile_rows"], gather["tile_cols"], gather["tile_depth"]) == (512, 64, 1)
    assert gather["issue_window"] == gather["max_outstanding"] == 4
    last = by_kernel[by_id["last_token_select"]]
    assert (last["tile_rows"], last["tile_cols"], last["tile_depth"]) == (1, 64, 1)
    head = by_kernel[by_id["vocabulary_projection"]]
    assert (head["tile_rows"], head["tile_cols"], head["tile_depth"]) == (1, 64, 128)
    # Tensor, vector and DMA operators are spread over the two queues both
    # vehicles have; attention and selection have one.
    for family, queues in ((Major.TENSOR, 2), (Major.VECTOR, 2), (Major.DMA, 2),
                           (Major.ATTENTION, 1), (Major.SELECTION, 1)):
        used = {r[3]["queue_index"] for r in rows if r[0] == int(family)}
        assert used == set(range(queues)), (family, used)
    # The ROM side's bank mask names mask-ROM shards, the HBM side's names
    # scratchpad staging groups -- the one cited storage-class consequence.
    classes = {
        int(d.payload["storage_class"])
        for d in rom_deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.MEMORY_OBJECT
    }
    assert int(StorageClass.ROM) in classes


# ---------------------------------------------------------------------------
# ``rows`` is the surface, not the loop trip (section 13 item 28's DMA.SCATTER)
# ---------------------------------------------------------------------------
def _surface_view(deployment, operator):
    """The view ``operand_extents`` reads: ``out0``, or ``in0`` when absent."""
    out0 = int(operator.payload["output_view_0"])
    in0 = int(operator.payload["input_view_0"])
    view = out0 if out0 != NO_ID else in0
    return None if view == NO_ID else view


def _row_tiling(deployment):
    """``[(operator_id, tile_rows, declared surface rows, narrowed?)]``."""
    table = {d.descriptor_id: d for d in deployment.table.descriptors()}
    rows = []
    for d in deployment.table.descriptors():
        if d.descriptor_type != ExtendedDescriptorType.OPERATOR:
            continue
        view = _surface_view(deployment, d)
        if view is None:
            continue
        schedule = table[int(d.payload["schedule_id"])].payload
        rows.append((
            int(d.descriptor_id),
            int(schedule["tile_rows"]),
            declared_view_rows(deployment.table, view),
            request_narrows_rows(deployment.table, view),
        ))
    return rows


@pytest.mark.skipif(not QWEN_IR.exists(), reason="the Qwen IR is a build product")
def test_the_tile_spans_every_request_independent_surface_on_both_backends():
    """AM-E9 section 3.8: row tiling is not a program construct.

    The consumer is ``runtime.cycle.model.tile_mapping``, which charges
    ``ceil(rows / tile_rows)`` row tiles over the operator's own surface.  A
    surface the request does not narrow has its declared extents at every
    request, so a ``tile_rows`` below them is row tiling the rule forbids --
    which is what a backend's loop trip produces, and what made one
    ``DMA.SCATTER`` of a single token row cost 524,288 tiles on the ROM array
    against 1,024 on its HBM twin (design section 13 item 28).
    """
    graph = KernelGraph.read(QWEN_IR)
    rom_capability = _capability(ROM_CAPABILITY)
    hbm_capability = _capability(HBM_CAPABILITY)
    rom_deployment, _plan = build_qwen3_rom_deployment(graph, capability=rom_capability)
    hbm_deployment = hbm_lower(graph, hbm_capability)
    for name, deployment in (("rom", rom_deployment), ("hbm", hbm_deployment)):
        offenders = [
            row for row in _row_tiling(deployment)
            if not row[3] and row[1] < row[2]
        ]
        assert offenders == [], (name, offenders)


@pytest.mark.skipif(not QWEN_IR.exists(), reason="the Qwen IR is a build product")
def test_a_state_scatter_is_tiled_by_the_cache_it_addresses_not_by_the_dispatch():
    """The KV write: one token row into a cache whose extent is fixed.

    Both backends emit the cache's own row count, so the model charges one row
    tile.  Before this rule the ROM side emitted its per-token dispatch and the
    HBM side its token block, and neither described the surface.
    """
    graph = KernelGraph.read(QWEN_IR)
    rom_deployment, _plan = build_qwen3_rom_deployment(
        graph, capability=_capability(ROM_CAPABILITY)
    )
    hbm_deployment = hbm_lower(graph, _capability(HBM_CAPABILITY))
    for name, deployment in (("rom", rom_deployment), ("hbm", hbm_deployment)):
        table = {d.descriptor_id: d for d in deployment.table.descriptors()}
        scatters = [
            d for d in deployment.table.descriptors()
            if d.descriptor_type == ExtendedDescriptorType.OPERATOR
            and int(d.payload["engine_family"]) == int(Major.DMA)
            and int(d.payload["engine_sub"]) == int(Dma.SCATTER)
        ]
        assert scatters, name
        for operator in scatters:
            view = _surface_view(deployment, operator)
            assert view is not None, name
            schedule = table[int(operator.payload["schedule_id"])].payload
            surface = declared_view_rows(deployment.table, view)
            assert int(schedule["tile_rows"]) == surface, (
                name, int(operator.descriptor_id), int(schedule["tile_rows"]), surface
            )


# ---------------------------------------------------------------------------
# The independent ROM checker reads the fields the way the rule states them
# ---------------------------------------------------------------------------
def test_the_rom_checker_reads_port_mask_as_scratchpad_ports(tmp_path):
    """AM-C4: bit p is port p; a bank index in the port field is refused."""
    graph = qwen_shaped_graph(tmp_path, layers=1, hidden=64, span_max=16)
    capability = qwen3_rom_capability(max_context_positions=16, vocabulary_size=32)
    deployment, _plan = build_qwen3_rom_deployment(graph, capability=capability)
    assert check_rom_schedule(graph, deployment, capability)["status"] == "pass"
    schedule = next(
        d for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.SCHEDULE
        and d.payload["engine_family"] == int(Major.VECTOR)
    )
    assert schedule.payload["port_mask"] == 0b11
    # A bank index (the previous reading) names a port the capability has not.
    bank_bit = _mutate_descriptor(deployment, schedule.descriptor_id, "port_mask", 1 << 5)
    report = check_rom_schedule(graph, bank_bit, capability)
    assert report["status"] == "fail"
    assert report["checks"]["memory_port_coverage"] is False
    assert report["checks"]["memory_ports_allocated"] is False
    assert report["checks"]["port_mask_capacity"] is False
    # Naming one port of two omits a port the operands are served on.
    one_port = _mutate_descriptor(deployment, schedule.descriptor_id, "port_mask", 0b01)
    report = check_rom_schedule(graph, one_port, capability)
    assert report["status"] == "fail"
    assert report["checks"]["memory_port_coverage"] is False
    assert report["checks"]["memory_ports_allocated"] is True


def test_the_rom_checker_accepts_a_64_wide_dma_tile_on_a_mover_engine(tmp_path):
    """The DMA engine's ``lanes`` are movers; the tile keeps the design width."""
    graph = qwen_shaped_graph(tmp_path, layers=1, hidden=256, span_max=16)
    base = qwen3_rom_capability(max_context_positions=16, vocabulary_size=32)
    capability = Capability.from_dict({
        **base.to_dict(),
        "engines": {**base.engines, "dma": {"lanes": 8, "queues": 2}},
    })
    deployment, _plan = build_qwen3_rom_deployment(graph, capability=capability)
    dma = [
        d.payload for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.SCHEDULE
        and d.payload["engine_family"] == int(Major.DMA)
    ]
    assert dma and max(p["tile_cols"] for p in dma) == E9_TILE_COLS
    report = check_rom_schedule(graph, deployment, capability)
    assert report["status"] == "pass", report["errors"][:5]
    # A column-lane engine is still bounded by what it advertises.
    tensor = next(
        d for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.SCHEDULE
        and d.payload["engine_family"] == int(Major.TENSOR)
    )
    wide = _mutate_descriptor(
        deployment, tensor.descriptor_id, "tile_cols",
        capability.engines["tensor"]["lanes"] + 1,
    )
    assert check_rom_schedule(graph, wide, capability)["checks"]["tile_geometry"] is False
