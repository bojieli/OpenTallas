"""Fail-closed checks for the ABI-3 HBM rolling-compressor representation."""

from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path

import pytest

from compiler.backends.hbm_sram.check import check_deployment
from compiler.backends.hbm_sram.lower import lower_with_plan
from compiler.backends.hbm_sram.plan import read_kernel_graph
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    CommitPolicy,
    DType,
    Dma,
    InstructionFlag,
    Major,
    NO_ID,
    Permission,
    Reduction,
    State,
    StateClass,
    Vector,
)
from runtime.abi3.crc import sha256
from runtime.abi3.deployment import ObjectSource
from runtime.abi3.descriptors import Descriptor, ExtendedDescriptorType
from runtime.abi3.records import decode_body, split_program
from runtime.abi3.verifier import verify_deployment
from runtime.sim.generators import digest_of
from runtime.sim.memory import ViewResolver

ROOT = Path(__file__).resolve().parents[2]
DEEPSEEK_IR = ROOT / "build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json"
CAPABILITY = ROOT / "configs/hardware/abi3_capability/hbm_sram_cluster_32.json"

pytestmark = pytest.mark.skipif(
    not DEEPSEEK_IR.exists(), reason="DeepSeek IR not built"
)


@pytest.fixture(scope="module")
def compressor_build():
    graph = read_kernel_graph(DEEPSEEK_IR)
    capability = Capability.from_dict(json.loads(CAPABILITY.read_text()))
    deployment, _plan = lower_with_plan(graph, capability)
    return graph, capability, deployment


def _restamp(deployment, *, descriptors_changed: bool) -> None:
    """Restamp an intentionally self-consistent semantic mutation."""

    header, body = split_program(deployment.program)
    if descriptors_changed:
        deployment.program = (
            dataclasses.replace(
                header, descriptor_table_digest=deployment.table.digest
            ).encode()
            + body
        )
        header, body = split_program(deployment.program)
    deployment.program = (
        dataclasses.replace(
            header, deployment_digest=deployment.deployment_digest
        ).encode()
        + body
    )


def _operator_pairs(deployment, kernel_index: int):
    _header, body = split_program(deployment.program)
    pairs = []
    for instruction in decode_body(body):
        descriptor_id = int(instruction.descriptor_id)
        if (
            int(instruction.source_operation_id) != kernel_index
            or descriptor_id == NO_ID
            or not 0 <= descriptor_id < len(deployment.table)
        ):
            continue
        descriptor = deployment.table[descriptor_id]
        if descriptor.descriptor_type == ExtendedDescriptorType.OPERATOR:
            pairs.append((instruction, descriptor))
    return pairs


def _first_ratio4_kernel(graph) -> int:
    return next(
        kernel.index
        for kernel in graph.kernels
        if kernel.kind == "COMPRESS_STATE_UPDATE"
        and int(kernel.attributes["ratio"]) == 4
    )


def _replace_program_instruction(deployment, index: int, replacement) -> None:
    header, body = split_program(deployment.program)
    instructions = decode_body(body)
    instructions[index] = replacement
    mutated_body = b"".join(instruction.encode() for instruction in instructions)
    deployment.program = (
        dataclasses.replace(header, body_digest=sha256(mutated_body)).encode()
        + mutated_body
    )


def test_checker_reconstructs_the_complete_direct_hbm_contract(
    compressor_build,
) -> None:
    graph, capability, deployment = compressor_build
    report = check_deployment(graph, deployment, capability)
    assert report["ok"], report["errors"]
    assert report["compressor"] == {
        "graph_kernels": 62,
        "emitted_kernels": 5,
        "required_ring_moduli": [4, 8, 128],
        "ring_object_ids": {
            "4": [report["compressor"]["ring_object_ids"]["4"][0]],
            "8": [report["compressor"]["ring_object_ids"]["8"][0]],
            "128": [report["compressor"]["ring_object_ids"]["128"][0]],
        },
        "history_object_ids": report["compressor"]["history_object_ids"],
        "physical_batch": 1,
    }
    assert len(report["compressor"]["history_object_ids"]) == 6
    for name in (
        "compressor_ring_inventory",
        "compressor_ring_authenticated_hbm",
        "compressor_history_direct_hbm",
        "compressor_history_index_ring",
        "compressor_batch_one",
        "compressor_boundary_ring_binding",
        "compressed_scatter_path_predicates",
        "compressed_scatter_path_geometry",
        "compressed_scatter_mutual_exclusion",
        "direct_state_has_no_state_descriptors",
        "direct_state_has_no_state_instructions",
    ):
        assert report["checks"][name]
    assert not deployment.table.ids_of_type(ExtendedDescriptorType.STATE)
    _header, body = split_program(deployment.program)
    assert all(
        int(instruction.major) != int(Major.STATE)
        for instruction in decode_body(body)
    )


def test_ratio4_partial_final_block_resolves_every_score_add_view_to_p32(
    compressor_build,
) -> None:
    """A 544-token prefill resolves the second 512-token block to exactly 32.

    These are the five explicit views that implement one source FP32 score
    update: raw KV and score planes split from the packed projection, gathered
    APE scratch, ORDERED_SUM's singleton-term base, and biased-score output.
    The three operands of ORDERED_SUM must name the same 32*width elements even
    though the APE term carries a leading reduction axis of one.
    """

    graph, _capability, deployment = compressor_build
    kernel_index = _first_ratio4_kernel(graph)
    pairs = _operator_pairs(deployment, kernel_index)
    ape_gather = next(
        operator
        for _instruction, operator in pairs
        if int(operator.payload["engine_family"]) == int(Major.DMA)
        and int(operator.payload["engine_sub"]) == int(Dma.GATHER)
        and int(operator.payload["input_view_0"]) != NO_ID
        and deployment.objects[
            deployment.table[int(operator.payload["input_view_0"])].primary_object_id
        ].generator
        == "ring_indices_v1"
        and int(
            deployment.objects[
                deployment.table[
                    int(operator.payload["input_view_0"])
                ].primary_object_id
            ].parameters["modulus"]
        )
        == 4
    )
    score_add = next(
        operator
        for _instruction, operator in pairs
        if int(operator.payload["engine_family"]) == int(Major.REDUCTION)
        and int(operator.payload["engine_sub"]) == int(Reduction.ORDERED_SUM)
    )
    kv_scatter, score_scatter = [
        operator
        for _instruction, operator in pairs
        if int(operator.payload["engine_family"]) == int(Major.DMA)
        and int(operator.payload["engine_sub"]) == int(Dma.SCATTER)
    ]

    raw_kv_id = int(kv_scatter.payload["input_view_1"])
    raw_score_id = int(score_add.payload["input_view_1"])
    ape_scratch_id = int(ape_gather.payload["output_view_0"])
    ape_term_id = int(score_add.payload["input_view_0"])
    biased_score_id = int(score_add.payload["output_view_0"])
    assert int(score_scatter.payload["input_view_1"]) == biased_score_id

    width = int(graph.kernels[kernel_index].attributes["head_dim"]) * 2
    assert width == 1024
    resolver = ViewResolver(deployment, None)

    def resolve_p32(view_id: int):
        descriptor = deployment.table[view_id]
        loop_ids = [
            int(descriptor.payload[f"term{slot}_index"])
            for slot in range(int(descriptor.payload["dynamic_term_count"]))
            if int(descriptor.payload[f"term{slot}_kind"]) == 0
        ]
        assert len(loop_ids) == 1
        loop_id = loop_ids[0]
        loop = deployment.table.get(
            loop_id, ExtendedDescriptorType.LOOP_CONTROL
        )
        assert int(loop.payload["bound_divisor"]) == 512
        assert int(loop.payload["bound_symbol_id"]) == 0
        return resolver.resolve(
            view_id,
            loops={loop_id: 1},
            symbols={0: 544},
        )

    raw_kv = resolve_p32(raw_kv_id)
    raw_score = resolve_p32(raw_score_id)
    ape_scratch = resolve_p32(ape_scratch_id)
    ape_term = resolve_p32(ape_term_id)
    biased_score = resolve_p32(biased_score_id)

    assert raw_kv.dims == (32, width)
    assert raw_score.dims == (32, width)
    assert ape_scratch.dims == (32, width)
    assert ape_term.dims == (1, 32, width)
    assert biased_score.dims == (32, width)
    assert raw_kv.strides == raw_score.strides == (2 * width, 1)
    assert raw_score.element_offset - raw_kv.element_offset == width
    assert ape_scratch.strides == biased_score.strides == (width, 1)
    assert ape_term.strides == (0, width, 1)
    assert ape_scratch.object_id == ape_term.object_id
    assert ape_scratch.element_offset == ape_term.element_offset
    assert (
        ape_term.element_count
        == raw_score.element_count
        == biased_score.element_count
        == 32 * width
    )


def test_checker_rejects_a_digest_consistent_wrong_history_ring(
    compressor_build,
) -> None:
    graph, capability, deployment = compressor_build
    mutated = copy.deepcopy(deployment)
    rings = {
        int(source.parameters["modulus"]): object_id
        for object_id, source in mutated.objects.items()
        if source.generator == "ring_indices_v1"
    }
    kernel_index = _first_ratio4_kernel(graph)
    scatter = next(
        operator
        for _instruction, operator in _operator_pairs(mutated, kernel_index)
        if int(operator.payload["engine_family"]) == int(Major.DMA)
        and int(operator.payload["engine_sub"]) == int(Dma.SCATTER)
    )
    view_id = int(scatter.payload["input_view_0"])
    view = mutated.table[view_id]
    assert int(view.primary_object_id) == rings[8]
    view.primary_object_id = rings[4]
    mutated.table.rewrite(view_id)
    _restamp(mutated, descriptors_changed=True)

    assert verify_deployment(mutated, capability).admitted
    report = check_deployment(graph, mutated, capability)
    assert not report["ok"]
    assert not report["checks"]["compressor_history_index_ring"]


def test_checker_rejects_zero_padding_in_a_score_history(
    compressor_build,
) -> None:
    graph, capability, deployment = compressor_build
    mutated = copy.deepcopy(deployment)
    score_object = next(
        object_id
        for object_id, source in mutated.objects.items()
        if source.generator == "constant_u32_v1"
        and int(source.parameters.get("value", 0)) == 0xFF800000
        and bool(mutated.table[object_id].permissions & Permission.WRITE)
    )
    size = mutated.objects[score_object].size_bytes
    mutated.objects[score_object] = ObjectSource.zeros(size)
    mutated.table[score_object].payload["content_digest"] = bytes(32)
    mutated.table.rewrite(score_object)
    _restamp(mutated, descriptors_changed=True)

    assert verify_deployment(mutated, capability).admitted
    report = check_deployment(graph, mutated, capability)
    assert not report["ok"]
    assert not report["checks"]["compressor_history_direct_hbm"]


def test_checker_rejects_ignored_ring_generator_parameters(
    compressor_build,
) -> None:
    """The generator ignores extras; the independent declaration must not."""

    graph, capability, deployment = compressor_build
    mutated = copy.deepcopy(deployment)
    object_id, source = next(
        (object_id, source)
        for object_id, source in mutated.objects.items()
        if source.generator == "ring_indices_v1"
        and int(source.parameters["modulus"]) == 8
    )
    parameters = {**dict(source.parameters), "ignored": 0}
    mutated.objects[object_id] = ObjectSource.generated(
        "ring_indices_v1",
        parameters,
        source.size_bytes,
        digest_of("ring_indices_v1", parameters),
    )
    _restamp(mutated, descriptors_changed=False)

    assert verify_deployment(mutated, capability).admitted
    report = check_deployment(graph, mutated, capability)
    assert not report["ok"]
    assert not report["checks"]["compressor_ring_parameters_exact"]


def test_checker_rejects_batch_two_views_over_batch_one_histories(
    compressor_build,
) -> None:
    graph, capability, deployment = compressor_build
    mutated = copy.deepcopy(deployment)
    kernel_index = _first_ratio4_kernel(graph)
    prefill = next(
        operator
        for _instruction, operator in _operator_pairs(mutated, kernel_index)
        if int(operator.payload["engine_family"]) == int(Major.VECTOR)
        and int(operator.payload["engine_sub"]) == int(Vector.COMPRESS)
        and int(operator.payload["aux_id_0"]) == 2
    )
    for field in ("input_view_0", "output_view_0", "output_view_1"):
        view_id = int(prefill.payload[field])
        view = mutated.table[view_id]
        assert int(view.payload["dim0"]) == 1
        assert int(view.payload["dim1"]) % 2 == 0
        assert int(view.payload["stride0"]) % 2 == 0
        view.payload["dim0"] = 2
        view.payload["dim1"] //= 2
        view.payload["stride0"] //= 2
        mutated.table.rewrite(view_id)
    _restamp(mutated, descriptors_changed=True)

    assert verify_deployment(mutated, capability).admitted
    report = check_deployment(graph, mutated, capability)
    assert not report["ok"]
    assert not report["checks"]["compressor_batch_one"]


def test_checker_rejects_a_noninverted_decode_cache_scatter(
    compressor_build,
) -> None:
    graph, capability, deployment = compressor_build
    mutated = copy.deepcopy(deployment)
    kernel = next(
        kernel
        for kernel in graph.kernels
        if kernel.kind == "KV_APPEND"
        and int(kernel.attributes.get("ratio", 0)) == 4
        and kernel.attributes.get("cache_row")
        == "completed_absolute_position_floor_div_ratio"
    )
    _header, body = split_program(mutated.program)
    instructions = decode_body(body)
    instruction_index = next(
        index
        for index, instruction in enumerate(instructions)
        if int(instruction.source_operation_id) == kernel.index
        and int(instruction.major) == int(Major.DMA)
        and int(instruction.sub) == int(Dma.SCATTER)
        and int(instruction.flags) & int(InstructionFlag.PREDICATE_INVERT)
    )
    instruction = instructions[instruction_index]
    _replace_program_instruction(
        mutated,
        instruction_index,
        dataclasses.replace(
            instruction,
            flags=(
                int(instruction.flags)
                & ~int(InstructionFlag.PREDICATE_INVERT)
            ),
        ),
    )
    _restamp(mutated, descriptors_changed=False)

    assert verify_deployment(mutated, capability).admitted
    report = check_deployment(graph, mutated, capability)
    assert not report["ok"]
    assert not report["checks"]["compressed_scatter_path_predicates"]
    assert not report["checks"]["compressed_scatter_paths_exact"]


def test_checker_rejects_state_machinery_for_direct_hbm_histories(
    compressor_build,
) -> None:
    graph, capability, deployment = compressor_build
    mutated = copy.deepcopy(deployment)
    baseline = check_deployment(graph, mutated, capability)
    history_object = baseline["compressor"]["history_object_ids"][0]
    history_view = next(
        descriptor.descriptor_id
        for descriptor in mutated.table.descriptors()
        if descriptor.descriptor_type == ExtendedDescriptorType.TENSOR_VIEW
        and int(descriptor.primary_object_id) == history_object
    )
    state_descriptor = Descriptor(
        descriptor_id=NO_ID,
        descriptor_type=ExtendedDescriptorType.STATE,
        payload={
            "state_class": int(StateClass.COMPRESSED_KV),
            "commit_policy": int(CommitPolicy.REQUEST_SPAN),
            "element_dtype": int(DType.FP32),
            "session_binding_id": 0,
            "committed_object_id": history_object,
            "prepared_object_id": history_object,
            "row_bytes": 4,
            "capacity_rows": 1,
            "initial_cursor_rows": 0,
            "generation_bits": 64,
            "counter_class_id": NO_ID,
            "view_descriptor_id": history_view,
            "node_id": 0,
            "initial_digest": bytes(32),
        },
        primary_object_id=history_object,
        secondary_object_id=history_object,
        permissions=int(
            Permission.READ | Permission.STATE_PREPARE | Permission.STATE_COMMIT
        ),
    )
    state_id = mutated.table.add(state_descriptor)

    _header, body = split_program(mutated.program)
    instructions = decode_body(body)
    instruction_index = next(
        index
        for index, instruction in enumerate(instructions)
        if int(instruction.major) == int(Major.CONTROL)
        and int(instruction.descriptor_id) == NO_ID
    )
    _replace_program_instruction(
        mutated,
        instruction_index,
        dataclasses.replace(
            instructions[instruction_index],
            major=int(Major.STATE),
            sub=int(State.PREPARE),
            descriptor_id=state_id,
        ),
    )
    _restamp(mutated, descriptors_changed=True)

    report = check_deployment(graph, mutated, capability)
    assert not report["ok"]
    assert not report["checks"]["direct_state_has_no_state_descriptors"]
    assert not report["checks"]["direct_state_has_no_state_instructions"]
