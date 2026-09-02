"""Acceptance and mutation tests for the 32-node HBM dataflow schedule."""

from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path

import pytest

from compiler.backends.hbm_sram.check import check_deployment
from compiler.backends.hbm_sram.lower import lower_with_plan
from compiler.ir.v3.kernel_ir import KernelGraph
from runtime.abi3.capability import Capability
from runtime.abi3.constants import InstructionFlag, Link, Major, NO_ID
from runtime.abi3.descriptors import (
    ExtendedDescriptorType,
    SelectorKind,
    Symbol,
)
from runtime.abi3.records import decode_body, split_program
from tools.check_hbm_deployments import (
    _DEEPSEEK_ROUTE_CONTRACT,
    _link_records,
    _scratch_serialization,
    _weight_locality,
)

ROOT = Path(__file__).resolve().parents[2]
DEEPSEEK_IR = ROOT / "build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json"


def _restamp(deployment):
    """Bind a deliberately edited descriptor table through the full chain."""

    header, body = split_program(deployment.program)
    header = dataclasses.replace(
        header,
        descriptor_table_digest=deployment.table.digest,
        deployment_digest=bytes(32),
    )
    deployment.program = header.encode() + body
    deployment.program = dataclasses.replace(
        header, deployment_digest=deployment.deployment_digest
    ).encode() + body
    return deployment


@pytest.fixture(scope="module")
def deepseek_cluster():
    if not DEEPSEEK_IR.exists():
        pytest.skip("DeepSeek IR has not been published into build/ir-v3")
    graph = KernelGraph.read(DEEPSEEK_IR)
    capability = Capability.from_dict(
        json.loads(
            (
                ROOT
                / "configs/hardware/abi3_capability/hbm_sram_cluster_32.json"
            ).read_text()
        )
    )
    deployment, plan = lower_with_plan(graph, capability)
    return graph, capability, deployment, plan


def test_deepseek_expert_sparse_and_reduction_bytes_reach_consumers(
    deepseek_cluster,
) -> None:
    graph, _capability, deployment, plan = deepseek_cluster
    records = _link_records(graph, deployment)

    for name in (
        "expert_dispatch",
        "sparse_gather",
        "activation_transfer",
        "reduction",
    ):
        route, subopcode, collective, source_kinds = _DEEPSEEK_ROUTE_CONTRACT[name]
        matching = [
            record
            for record in records
            if record["route_class"] == route
            and record["subopcode"] == subopcode
            and record["collective_op"] == collective
            and (
                not source_kinds or record["source_kind"] in source_kinds
            )
        ]
        assert matching, name
        assert all(record["pack_bound"] for record in matching), name
        assert all(record["received_data_consumed"] for record in matching), name
        assert all(record["causally_bound"] for record in matching), name
        assert all(record["byte_extent"] > 0 for record in matching), name

    routed_weights = [
        operand
        for kernel in plan.kernels
        for operand in kernel.operands
        if kernel.kind == "ROUTED_MATMUL"
        and operand.direction == "in"
        and operand.slot == 1
        and operand.bank
    ]
    assert routed_weights
    assert {operand.bank for operand in routed_weights} == {256}
    assert {operand.bank_shard for operand in routed_weights} == {8}
    assert deployment.notes["replicated_link_sites"] == {}
    assert plan.proofs["communication_scratch_bytes"] == 805_306_368
    assert plan.proofs["hbm_fits"]


def test_deepseek_capacity_counts_replication_constants_and_rolling_queries(
    deepseek_cluster,
) -> None:
    _graph, _capability, _deployment, plan = deepseek_cluster
    proofs = plan.proofs

    assert proofs["replicated_weight_bytes"] == 4_262_949_084
    assert proofs["node_sharded_weight_bytes"] == 151_752_749_056
    assert (
        proofs["replicated_weight_bytes"]
        + proofs["node_sharded_weight_bytes"]
        == proofs["weight_bytes"]
    )
    assert proofs["materialized_node_sharded_weight_bytes"] == 147_169_738_752
    assert proofs["fallback_replicated_weight_bytes"] == 4_583_010_304
    assert proofs["weight_bytes_per_node"] == 13_445_013_724
    assert proofs["weight_replication_overhead_per_node"] > 4_000_000_000
    assert proofs["generated_constant_bytes"] == 272_629_772

    placements = {item.tensor_id: item for item in plan.weight_placements}
    assert placements["embed.weight"].residency == "replicated"
    assert placements["embed.weight"].shard_count == 1
    assert placements["head.weight"].residency == "node_sharded"
    assert placements["head.weight"].shard_count == 32
    assert placements["head.weight"].materialization == "replicated"
    expert = next(
        placement
        for placement in placements.values()
        if placement.residency == "node_sharded"
        and placement.materialization == "node_sharded"
    )
    assert expert.elements * 32 == sum(
        segment.elements
        for group in plan.weight_groups
        for segment in group.segments
        if segment.tensor_id == expert.tensor_id
    )
    node_groups = [group for group in plan.weight_groups if group.node_segments]
    assert node_groups
    assert all(len(group.node_segments) == 32 for group in node_groups)
    assert all(
        {
            sum(segment.bytes for segment in node_map)
            for node_map in group.node_segments
        }
        == {group.local_size_bytes}
        for group in node_groups
    )
    assert any(group.residency == "mixed" for group in plan.weight_groups)

    stream_groups = {
        kernel.stream_group for kernel in plan.kernels if kernel.stream_group
    }
    assert any("query_stream" in group for group in stream_groups)
    assert any("attention_output_stream" in group for group in stream_groups)
    assert proofs["activation_arena_bytes"] < 72_000_000_000
    assert (
        proofs["hbm_available_per_node"] - proofs["hbm_bytes_per_node"]
        > 12_000_000_000
    )
    assert proofs["hbm_fits"]


def test_weight_locality_checker_rejects_a_false_replica_declaration(
    deepseek_cluster,
) -> None:
    _graph, _capability, _deployment, plan = deepseek_cluster
    placements = tuple(
        dataclasses.replace(
            placement, residency="replicated", shard_count=1
        )
        if placement.tensor_id == "head.weight"
        else placement
        for placement in plan.weight_placements
    )
    mutated = dataclasses.replace(plan, weight_placements=placements)
    locality = _weight_locality(mutated)
    assert locality["placement_mismatches"] == ["head.weight"]


def test_weight_sources_and_views_apply_node_selection_exactly_once(
    deepseek_cluster,
) -> None:
    _graph, _capability, deployment, plan = deepseek_cluster
    node_sources = [
        (object_id, source)
        for object_id, source in deployment.objects.items()
        if source.kind == "node_segments"
    ]
    assert node_sources
    for object_id, source in node_sources:
        descriptor = deployment.table[object_id]
        size = descriptor.payload["size_bytes"]
        assert source.size_bytes == size
        assert (
            descriptor.payload["content_digest"]
            == source.authenticated_content_digest()
        )
        assert len(source.node_segments) == 32
        assert {
            sum(segment.bytes for segment in node_map)
            for node_map in source.node_segments
        } == {size}

    def has_node_term(kernel, operand) -> bool:
        for operator in deployment.table.descriptors():
            if (
                operator.descriptor_type != ExtendedDescriptorType.OPERATOR
                or operator.payload["source_kernel_id"] != kernel.index
            ):
                continue
            view_id = operator.payload[f"input_view_{operand.slot}"]
            if view_id == NO_ID:
                continue
            view = deployment.table[view_id]
            for slot in range(view.payload["dynamic_term_count"]):
                if (
                    view.payload[f"term{slot}_kind"]
                    == int(SelectorKind.RUNTIME_SYMBOL)
                    and view.payload[f"term{slot}_index"] == int(Symbol.NODE_ID)
                ):
                    return True
        return False

    local_kernel = next(
        kernel
        for kernel in plan.kernels
        if any(
            operand.residence == "weight"
            and "node" in operand.terms
            and plan.placement(operand.tensor_id).materialization
            == "node_sharded"
            for operand in kernel.operands
        )
    )
    local_operand = next(
        operand
        for operand in local_kernel.operands
        if operand.residence == "weight"
        and "node" in operand.terms
        and plan.placement(operand.tensor_id).materialization == "node_sharded"
    )
    fallback_kernel = next(
        kernel
        for kernel in plan.kernels
        if any(
            operand.residence == "weight"
            and "node" in operand.terms
            and plan.placement(operand.tensor_id).materialization == "replicated"
            for operand in kernel.operands
        )
    )
    fallback_operand = next(
        operand
        for operand in fallback_kernel.operands
        if operand.residence == "weight"
        and "node" in operand.terms
        and plan.placement(operand.tensor_id).materialization == "replicated"
    )

    assert not has_node_term(local_kernel, local_operand)
    assert has_node_term(fallback_kernel, fallback_operand)


def test_missing_link_pack_dependency_is_rejected_by_semantic_checker(
    deepseek_cluster,
) -> None:
    graph, _capability, deployment, _plan = deepseek_cluster
    _header, body = split_program(deployment.program)
    instructions = decode_body(body)
    original = _link_records(graph, deployment, instructions)
    scatter = next(
        record
        for record in original
        if record["route_class"] == 0
        and record["subopcode"] == int(Link.SCATTER)
    )
    index = int(scatter["instruction_index"])
    instructions[index] = dataclasses.replace(
        instructions[index], wait_set_id=NO_ID
    )

    mutated = _link_records(graph, deployment, instructions)
    record = next(item for item in mutated if item["instruction_index"] == index)
    assert not record["pack_bound"]
    assert not record["causally_bound"]


def test_reduction_pack_flattens_the_partial_token_extent_on_both_dma_views(
    deepseek_cluster,
) -> None:
    graph, _capability, deployment, _plan = deepseek_cluster
    _header, body = split_program(deployment.program)
    instructions = decode_body(body)
    reductions = [
        record
        for record in _link_records(graph, deployment, instructions)
        if record["route_class"] == 3
    ]
    assert reductions

    for record in reductions:
        pack = instructions[record["pack_instruction_indices"][-1]]
        operator = deployment.table[pack.descriptor_id]
        source = deployment.table[operator.payload["input_view_0"]].payload
        destination = deployment.table[operator.payload["output_view_0"]].payload
        assert source["rank"] == 3
        assert destination["rank"] == 2
        experts = int(source["dim0"])
        assert experts * int(source["dim1"]) == int(destination["dim0"])
        assert source["dim2"] == destination["dim1"]
        assert source["extent_axis"] == 1
        assert destination["extent_axis"] == 0
        assert (
            experts * max(int(source["extent_numerator"]), 1)
            == max(int(destination["extent_numerator"]), 1)
        )
        assert source["edge_mask_id"] == destination["edge_mask_id"] != NO_ID

        unpack_index = next(
            index
            for index in record["binding_path"]
            if instructions[index].major == int(Major.DMA)
        )
        unpack = deployment.table[instructions[unpack_index].descriptor_id]
        unpack_destination = deployment.table[
            unpack.payload["output_view_0"]
        ].payload
        for field in (
            "rank",
            "dim0",
            "dim1",
            "dim2",
            "stride0",
            "stride1",
            "stride2",
            "extent_axis",
            "extent_numerator",
            "extent_unit",
            "extent_bias",
            "edge_mask_id",
        ):
            assert source[field] == unpack_destination[field]

        consumer = instructions[record["consumer_instruction_index"]]
        consumer_operator = deployment.table[consumer.descriptor_id]
        assert (
            operator.payload["input_view_0"]
            == consumer_operator.payload["input_view_0"]
        )
        contribution = source
        assert contribution["rank"] == 3
        assert contribution["extent_axis"] == 1
        assert max(int(contribution["extent_numerator"]), 1) == 1
        assert contribution["edge_mask_id"] == source["edge_mask_id"]


def test_severed_receive_unpack_is_rejected_by_semantic_checker(
    deepseek_cluster,
) -> None:
    graph, _capability, deployment, _plan = deepseek_cluster
    _header, body = split_program(deployment.program)
    instructions = decode_body(body)
    original = _link_records(graph, deployment, instructions)
    reduction = next(
        record
        for record in original
        if record["route_class"] == 3
        and record["subopcode"] == int(Link.COLLECTIVE)
    )
    link_index = int(reduction["instruction_index"])
    unpack_index = next(
        index
        for index in reduction["binding_path"]
        if instructions[index].major == int(Major.DMA)
    )
    instructions[unpack_index] = dataclasses.replace(
        instructions[unpack_index], wait_set_id=NO_ID
    )

    mutated = _link_records(graph, deployment, instructions)
    record = next(
        item for item in mutated if item["instruction_index"] == link_index
    )
    assert record["pack_bound"]
    assert not record["received_data_consumed"]
    assert not record["causally_bound"]


def test_shared_exchange_scratch_uses_one_dedicated_one_credit_queue(
    deepseek_cluster,
) -> None:
    _graph, capability, deployment, _plan = deepseek_cluster
    result = _scratch_serialization(deployment, capability)

    assert result["ok"], result["errors"]
    assert result["exchange_object_ids"]
    assert result["triple_count"] == 36
    assert result["scratch_dma_count"] == 72
    assert result["queue_index"] == capability.engines["dma"]["queues"] - 1
    assert result["issue_window"] == 1
    assert result["max_outstanding"] == 1
    assert result["dedicated_queue"]

    # At least one complete exchange is actually loop-carried; otherwise this
    # test would exercise only static site-to-site reuse and miss the reason a
    # sticky completion event is insufficient.
    _header, body = split_program(deployment.program)
    instructions = decode_body(body)
    data_links = [
        record
        for record in _link_records(
            deepseek_cluster[0], deployment, instructions
        )
        if record["route_class"]
        != _DEEPSEEK_ROUTE_CONTRACT["coordinated_commit"][0]
    ]
    loops = [
        deployment.table[descriptor_id].payload
        for descriptor_id in deployment.table.ids_of_type(
            ExtendedDescriptorType.LOOP_CONTROL
        )
        if int(deployment.table[descriptor_id].payload["max_iterations"]) > 1
    ]
    assert any(
        int(loop["body_start"])
        <= int(record["instruction_index"])
        < int(loop["body_end"])
        for loop in loops
        for record in data_links
    )


def test_scratch_checker_rejects_queue_and_credit_mutations(
    deepseek_cluster,
) -> None:
    _graph, capability, deployment, _plan = deepseek_cluster
    baseline = _scratch_serialization(deployment, capability)
    assert baseline["ok"], baseline["errors"]

    wrong_queue = copy.deepcopy(deployment)
    schedule_id = int(baseline["schedule_ids"][0])
    wrong_queue.table[schedule_id].payload["queue_index"] = 0
    queue_result = _scratch_serialization(wrong_queue, capability)
    assert not queue_result["ok"]
    assert any("one physical DMA queue" in error for error in queue_result["errors"])

    extra_credit = copy.deepcopy(deployment)
    extra_credit.table[schedule_id].payload["max_outstanding"] = 2
    credit_result = _scratch_serialization(extra_credit, capability)
    assert not credit_result["ok"]
    assert any("max_outstanding" in error for error in credit_result["errors"])

    # The independently implemented HBM checker is an admission lane, not
    # merely certificate prose.  Restamp the mutation so it reaches the
    # serialization proof rather than failing at the outer digest chain.
    admitted_mutation = copy.deepcopy(deployment)
    admitted_mutation.table[schedule_id].payload["max_outstanding"] = 2
    admitted_mutation.table.rewrite(schedule_id)
    admitted_mutation = _restamp(admitted_mutation)
    independent = check_deployment(
        deepseek_cluster[0], admitted_mutation, capability
    )
    assert not independent["ok"]
    assert independent["checks"]["communication_scratch_serialized"] is False
    assert not independent["verifier"]["admitted"]
    assert (
        independent["verifier"]["checks"]["hbm_exchange_one_outstanding"]
        is False
    )
    assert any("max_outstanding" in error for error in independent["errors"])


def test_scratch_checker_rejects_predicate_and_interleaving_mutations(
    deepseek_cluster,
) -> None:
    graph, capability, deployment, _plan = deepseek_cluster
    _header, body = split_program(deployment.program)
    original = decode_body(body)
    link_index = int(
        next(
            record["instruction_index"]
            for record in _link_records(graph, deployment, original)
            if record["route_class"]
            != _DEEPSEEK_ROUTE_CONTRACT["coordinated_commit"][0]
        )
    )

    predicate_mutation = list(original)
    unpack_index = link_index + 1
    predicate_mutation[unpack_index] = dataclasses.replace(
        predicate_mutation[unpack_index],
        flags=int(predicate_mutation[unpack_index].flags)
        ^ int(InstructionFlag.PREDICATE_INVERT),
    )
    predicate_result = _scratch_serialization(
        deployment, capability, predicate_mutation
    )
    assert not predicate_result["ok"]
    assert any("one predicate" in error for error in predicate_result["errors"])

    interleaved = list(original)
    interleaved[unpack_index], interleaved[unpack_index + 1] = (
        interleaved[unpack_index + 1],
        interleaved[unpack_index],
    )
    interleaved_result = _scratch_serialization(
        deployment, capability, interleaved
    )
    assert not interleaved_result["ok"]
    assert any(
        "immediately followed" in error or "non-interleaved" in error
        for error in interleaved_result["errors"]
    )
