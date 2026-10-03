"""Query lifetime gates; synthetic bindings carry shape provenance, no payload.

Full released tensor specs/layer modes are used. No checkpoint, matrix native
handler, physical runtime or numerical full-token claim is involved.
"""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from compiler.frontends.v3 import deepseek_v41 as front
from compiler.backends.hbm_sram.plan import (
    PlanError, build_plan, request_extent_of, symbol_maximum,
    _build_bands, _emission_order, _place_states, _bind_state_tensors,
    _streaming_schedule, _place_activations,
)
from compiler.ir.v3.kernel_ir import CheckpointBinding, Symbolic, Tensor
from runtime.abi3.capability import Capability
from runtime.abi3.descriptors import Phase, Symbol
from runtime.query_execution import admit_query_execution

CONTEXT = 1048576


@pytest.fixture(scope="module")
def shape_exports():
    """Mock only unavailable checkpoint/source IO, never architecture or emit."""
    profile = front.V41_FLASH_PROFILE
    release = profile.release
    config = front.load_official_config(release=release)
    specs = front.build_official_tensor_specs(config, release)
    bindings = {}
    offset = 0
    for spec in specs:
        bindings[spec.name] = CheckpointBinding(
            source_name=spec.name, path="synthetic-shape-only.safetensors",
            offset=offset, bytes=spec.size_bytes,
            sha256=hashlib.sha256(spec.name.encode()).hexdigest(),
        )
        offset += spec.size_bytes
    lock = {"lock_id": release.checkpoint_lock_id,
            "checkpoint": {"tensor_count": release.tensor_count,
                           "payload_bytes": release.payload_bytes}}
    def split_shape_binding(snapshot, binding, groups, rows):
        assert binding.bytes % groups == 0
        return tuple(replace(binding, offset=binding.offset+i*(binding.bytes//groups),
                             bytes=binding.bytes//groups) for i in range(groups))
    with patch.object(front, "split_binding_by_leading_groups", side_effect=split_shape_binding), \
         patch.object(front, "missing_ir_artifacts", return_value=[]), \
         patch.object(front, "confront_source_digests", return_value={}), \
         patch.object(front, "load_checkpoint_lock", return_value=lock), \
         patch.object(front, "read_checkpoint_bindings", return_value=bindings):
        graphs = {
            "generic": front.export_deepseek_v41_kernel_graph(context_tokens=CONTEXT),
            "decode": front.export_deepseek_v41_kernel_graph(
                context_tokens=CONTEXT, execution_mode="decode"),
            "decode_half": front.export_deepseek_v41_kernel_graph(
                context_tokens=CONTEXT//2, execution_mode="decode"),
            "decode_admitted_context": front.export_deepseek_v41_kernel_graph(
                context_tokens=262144, execution_mode="decode"),
            "bounded": front.export_deepseek_v41_kernel_graph(
                context_tokens=CONTEXT, execution_mode="bounded-prefill", prefill_chunk_tokens=128),
        }
    return graphs


def test_full_source_shapes_separate_context_and_query(shape_exports):
    for mode, query in (("generic", CONTEXT), ("decode", 1), ("bounded", 128)):
        graph = shape_exports[mode]
        assert symbol_maximum(graph, "span_tokens", 0) == query
        assert symbol_maximum(graph, "context_length", 0) == CONTEXT
        masks = [s for s in graph.states if s.state_id.startswith("candidate_pool_mask.")]
        selections = [s for s in graph.states if s.state_id.startswith("index_selection.")]
        assert len(masks) == 1 and len(selections) == 8
        assert masks[0].capacity_rows == query
        assert masks[0].row_elements == CONTEXT
        assert all(s.capacity_rows == query for s in selections)
        for tensor in graph.tensors:
            for dim in tensor.shape:
                if isinstance(dim, Symbolic) and dim.symbol == "span_tokens":
                    assert dim.maximum == query * dim.multiplier
        # The source compressor emits a row on ratio-two carry boundaries even
        # when floor(span/2)==0. Preserve its explicit decode modulo predicate.
        compressors = [k for k in graph.kernels if k.kind == "COMPRESS_STATE_UPDATE"]
        assert compressors
        assert any(k.attributes.get("predicate_condition", {}).get("decode") ==
                   "context_length % 2 == 0" for k in compressors)


def test_csa_producer_reuse_and_numerical_order_unchanged(shape_exports):
    generic = shape_exports["generic"]
    for key in ("decode", "bounded"):
        graph = shape_exports[key]
        assert len(graph.kernels) == len(generic.kernels)
        for old, new in zip(generic.kernels, graph.kernels):
            assert (old.kind, old.inputs, old.outputs, old.numeric_contract,
                    old.attributes, old.phases, old.state_reads, old.state_writes,
                    old.source_operation_id) == (
                    new.kind, new.inputs, new.outputs, new.numeric_contract,
                    new.attributes, new.phases, new.state_reads, new.state_writes,
                    new.source_operation_id)
        old_retained = [s for s in generic.states if not s.state_id.startswith(
            ("candidate_pool_mask.", "index_selection."))]
        new_retained = [s for s in graph.states if not s.state_id.startswith(
            ("candidate_pool_mask.", "index_selection."))]
        assert old_retained == new_retained


def _capability():
    path = Path(__file__).resolve().parents[2] / "configs/hardware/abi3_capability/hbm_sram_cluster_n_comparator_8_e4096.json"
    return Capability.from_dict(json.loads(path.read_text()))


def memory_placements(graph):
    """Run production full-graph storage planners without inventing hardware."""
    tensors = {t.tensor_id: t for t in graph.tensors}
    span_max = symbol_maximum(graph, "span_tokens", 0)
    bands, _ = _build_bands(graph, tensors)
    units, positions, owners = _emission_order(graph, bands)
    states, mapping, _ = _place_states(graph, bands, owners, span_max)
    state_tensors = _bind_state_tensors(graph, tensors, mapping)
    _, rolling = _streaming_schedule(graph, tensors, positions, owners, min(span_max,128), span_max)
    keys, arenas, slots, hosts = _place_activations(
        graph, tensors, bands, units, positions, owners, span_max,
        min(span_max,128), state_tensors, rolling,
    )
    return states, arenas, keys, slots, hosts


@pytest.fixture(scope="module")
def admitted_plan(shape_exports):
    return build_plan(shape_exports["decode_admitted_context"], _capability())


def test_full_shape_decode_planner_linear_memory(shape_exports, admitted_plan):
    cap = _capability()
    graph = shape_exports["decode"]
    states, arenas, *_ = memory_placements(graph)
    scratch = [s for s in states if s.state_class == "scratch"]
    assert all(s.capacity_rows == 1 for s in scratch)
    masks = [s for s in scratch if s.dtype == "u8"]
    assert sum(s.size_bytes for s in masks) == sum(len(s.members) for s in masks) * CONTEXT
    assert all(s.row_elements in (640, CONTEXT) for s in scratch)
    # The same full source graph at half context proves the affine scaling;
    # no fake capability relaxation or payload allocation is involved.
    half_states, half_arenas, *_ = memory_placements(shape_exports["decode_half"])
    assert sum(s.size_bytes for s in states) <= 2 * sum(s.size_bytes for s in half_states)
    assert sum(a.size_bytes for a in arenas) <= 2 * sum(a.size_bytes for a in half_arenas)
    with pytest.raises(PlanError, match="context_length.*exceeds capability"):
        build_plan(graph, cap)
    admitted = admitted_plan
    assert admitted.span_max == 1
    for kernel in admitted.kernels:
        if kernel.context_loop:
            assert kernel.context_loop.divisor == 262144
    if os.environ.get("DS_QUERY_EXECUTION_REPORT"):
        payload = {
            "schema": "deepseek-v41-query-storage-v1",
            "context_tokens": CONTEXT,
            "query_tokens": 1,
            "released_layers": 40,
            "checkpoint_binding_scope": "authenticated released tensor shapes; synthetic metadata only; no payload",
            "decode_1M": {
                "state_bytes": sum(s.size_bytes for s in states),
                "activation_arena_bytes": sum(a.size_bytes for a in arenas),
                "query_scratch_bytes": sum(s.size_bytes for s in scratch),
                "candidate_mask_bytes": sum(s.size_bytes for s in masks),
                "candidate_mask_member_count": sum(len(s.members) for s in masks),
            },
            "decode_half": {
                "state_bytes": sum(s.size_bytes for s in half_states),
                "activation_arena_bytes": sum(a.size_bytes for a in half_arenas),
            },
            "actual_capability_context_max": 262144,
            "admitted_262K_exchange_scratch_bytes": admitted.proofs["communication_scratch_bytes"],
            "admitted_262K_hbm_bytes_per_node": admitted.proofs["hbm_bytes_per_node"],
            "one_million_hardware_admitted": False,
            "numerical_full_token_qualified": False,
            "prefill_scope": "bounded position-zero initial block; later chunks refused pending separate causal-stream contract",
        }
        Path(os.environ["DS_QUERY_EXECUTION_REPORT"]).write_text(json.dumps(payload, indent=2)+"\n")
    stale = replace(graph,
        symbols=tuple(replace(s, maximum=CONTEXT//2) if s.name == "context_length" else s
                      for s in graph.symbols))
    with pytest.raises(PlanError, match="bounds disagree"):
        build_plan(stale, cap)


def _symbols(span=1, context=CONTEXT, start=CONTEXT-1):
    return {int(Symbol.SPAN_TOKENS): span, int(Symbol.CONTEXT_LENGTH): context,
            int(Symbol.POSITION_START): start}


def test_phase_admission_refuses_misuse_before_issue():
    decode = front.query_execution_contract(CONTEXT, execution_mode="decode")
    admit_query_execution(decode, _symbols(), int(Phase.DECODE))
    for phase, symbols in (
        (Phase.PREFILL, _symbols(start=0, context=1)),
        (Phase.DECODE, _symbols(span=2)),
        (Phase.DECODE, _symbols(context=CONTEXT+1)),
    ):
        with pytest.raises(ValueError):
            admit_query_execution(decode, symbols, int(phase))
    bounded = front.query_execution_contract(CONTEXT, execution_mode="bounded-prefill", prefill_chunk_tokens=128)
    admit_query_execution(bounded, _symbols(span=128, context=128, start=0), int(Phase.PREFILL))
    admit_query_execution(bounded, _symbols(), int(Phase.DECODE))
    for symbols in (_symbols(span=129, start=0), _symbols(span=128, start=128)):
        with pytest.raises(ValueError):
            admit_query_execution(bounded, symbols, int(Phase.PREFILL))


@pytest.mark.parametrize("mode,chunk", [("bad",None),("decode",128),("generic",1),
                                         ("bounded-prefill",None),("bounded-prefill",0),
                                         ("bounded-prefill",CONTEXT+1)])
def test_invalid_contract_is_refused(mode,chunk):
    with pytest.raises(front.DeepSeekV41KernelIRError):
        front.query_execution_contract(CONTEXT, execution_mode=mode, prefill_chunk_tokens=chunk)


def test_context_extent_validation_keeps_exact_refusal():
    tensor = Tensor("context", "bf16", (Symbolic("context_groups_ratio2",1,CONTEXT//2),512), "activation")
    extent = request_extent_of(tensor, 1, CONTEXT)
    assert extent.symbol == "context_length" and extent.unit == 2
    with pytest.raises(PlanError, match="declares maximum"):
        request_extent_of(replace(tensor, shape=(Symbolic("context_groups_ratio2",1,CONTEXT//2-1),512)),1,CONTEXT)


def test_bounded_prefill_storage_keeps_all_query_masks_until_reuse(shape_exports):
    graph = shape_exports["bounded"]
    states, arenas, *_ = memory_placements(graph)
    masks = [s for s in states if s.state_class == "scratch" and s.dtype == "u8"]
    assert masks and all(s.capacity_rows == 128 for s in masks)
    assert sum(s.size_bytes for s in masks) == sum(len(s.members) for s in masks) * 128 * CONTEXT
    # Score planes are rolling one-query arenas in the production scheduler.
    tensors = {t.tensor_id: t for t in graph.tensors}
    bands, _ = _build_bands(graph, tensors)
    _, positions, owners = _emission_order(graph, bands)
    groups, rolling = _streaming_schedule(graph, tensors, positions, owners, 128, 128)
    scores = [k for k in graph.kernels if k.kind == "INDEX_SCORE"]
    assert scores and all(rolling[k.outputs[0]][1] == 1 for k in scores)


def test_cli_specialization_is_explicit_and_v41_only(capsys):
    from tools.build_deepseek_v4_kernel_ir_v3 import build_parser, main
    args = build_parser().parse_args(["--execution-mode","decode"])
    assert args.execution_mode == "decode" and args.prefill_chunk_tokens is None
    assert main(["--model","deepseek-v4-flash-0731","--execution-mode","decode"]) == 1
    assert "V4.1 option" in capsys.readouterr().err
    assert main(["--model","deepseek-v4.1-flash","--execution-mode","bounded-prefill","--plan-only"]) == 1
    assert "prefill_chunk_tokens" in capsys.readouterr().err


def test_stale_scratch_or_symbol_pins_are_refused(shape_exports):
    graph = shape_exports["decode_admitted_context"]
    with pytest.raises(PlanError, match="scratch capacity"):
        build_plan(replace(graph, states=tuple(
            replace(s,capacity_rows=262144) if s.state_id.startswith("candidate_pool_mask.") else s
            for s in graph.states)), _capability())
    with pytest.raises(PlanError, match="declares maximum"):
        tensors = tuple(replace(t,shape=tuple(
            Symbolic(d.symbol,d.multiplier,262144*d.multiplier)
            if isinstance(d,Symbolic) and d.symbol == "span_tokens" else d
            for d in t.shape)) for t in graph.tensors)
        build_plan(replace(graph,tensors=tensors),_capability())


def test_full_source_specialized_abi_lowering(shape_exports, admitted_plan):
    from compiler.backends.hbm_sram.lower import lower_to_abi3
    from runtime.abi3.verifier import verify_deployment
    graph = shape_exports["decode_admitted_context"]
    deployment = lower_to_abi3(graph, _capability(), plan=admitted_plan)
    assert deployment.notes["query_execution"] == graph.source["query_execution"]
    report = verify_deployment(deployment, _capability())
    assert report.admitted, report.errors[:10]
    from runtime.abi3.constants import Major, Control, InstructionFlag, NO_ID
    from runtime.abi3.descriptors import Comparison
    from runtime.abi3.records import split_program, decode_body
    _, body = split_program(deployment.program)
    instructions = decode_body(body)

    def admission_traps(symbols):
        # Independently walk the actual emitted admission prefix. Stop before
        # any state/engine instruction; no checkpoint or handler is executed.
        pc = 0
        while pc < len(instructions):
            instruction = instructions[pc]
            if instruction.major != int(Major.CONTROL) or instruction.sub not in (
                    int(Control.TRAP), int(Control.BRANCH)):
                return False
            enabled = True
            if instruction.predicate_id != NO_ID:
                pred = deployment.table[instruction.predicate_id].payload
                lhs, rhs = symbols[int(pred["selector_index"])], int(pred["immediate"])
                enabled = {Comparison.EQ: lhs == rhs, Comparison.NE: lhs != rhs,
                           Comparison.LT: lhs < rhs, Comparison.LE: lhs <= rhs,
                           Comparison.GT: lhs > rhs, Comparison.GE: lhs >= rhs}[Comparison(pred["comparison"])]
                if instruction.flags & int(InstructionFlag.PREDICATE_INVERT):
                    enabled = not enabled
            if enabled and instruction.sub == int(Control.TRAP):
                return True
            pc = instruction.control_id if enabled and instruction.sub == int(Control.BRANCH) else pc + 1
        raise AssertionError("admission did not reach mutable-work frontier")

    valid = _symbols(context=262144, start=262143)
    valid[int(Symbol.PHASE)] = int(Phase.DECODE)
    assert not admission_traps(valid)
    for change in ({Symbol.SPAN_TOKENS: 0}, {Symbol.SPAN_TOKENS: 2},
                   {Symbol.CONTEXT_LENGTH: 0}, {Symbol.CONTEXT_LENGTH: 262145},
                   {Symbol.PHASE: int(Phase.PREFILL)}, {Symbol.PHASE: 99}):
        symbols = dict(valid)
        symbols.update({int(key): value for key, value in change.items()})
        assert admission_traps(symbols), change
    # The full source candidate chain shares its one-query loop, while mask
    # writes still address the state plane (not a rolled temporary).
    chain = [p for p in admitted_plan.kernels if p.layer == 20 and p.kind in
             ("INDEX_SCORE","BLOCK_MAX","INDEX_TOPK","CANDIDATE_MASK")]
    assert len(chain) == 5
    assert len({p.stream_group for p in chain}) == 1
    assert all(p.row_loop.divisor == 1 for p in chain)
    assert all(p.context_loop.divisor == 262144 for p in chain)


def test_rom_backend_refuses_unadmitted_specialization(shape_exports):
    from compiler.backends.rom.common.program import RomLowering, RomLoweringError
    with pytest.raises(RomLoweringError, match="HBM/SRAM"):
        RomLowering(shape_exports["decode"], _capability(), None)
