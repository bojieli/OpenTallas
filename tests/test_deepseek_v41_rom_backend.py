"""Tests for the DeepSeek-V4.1-Flash two-wafer immutable-ROM backend (WP-E).

The fixture is the V4 wafer fixture's decoder block -- kernel for kernel, so
that what is tested here is the V4.1 *placement*, not a second lowering -- plus
exactly the four things V4.1 adds and the ROM backend has to place:

* a CSA2 global KV cache written by one layer and read by later ones, which is
  the shared-cache placement rule of plan section 6.1;
* a layered Engram lookup table, which is the load-once resident HBM region of
  plan section 3.4;
* a candidate pool (block maximum, block top-k, admission plane) and index
  top-k kernels that carry its mask, which is ``candidate_pool_bound``;
* a routed expert population and top-k that V4's published record would refuse.

The checkpoint is a real file on disk, so the inverse proof reconstructs actual
bytes rather than trusting a recorded digest, and ``--determinism``'s question
-- is a rebuild byte-identical -- is asked here as well.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from compiler.backends.rom.common.check import check_rom_schedule
from compiler.backends.rom.common.inverse import check_rom_inverse
from compiler.backends.rom.deepseek_v41 import (
    DeepSeekV41RomError,
    INTER_WAFER_ROUTE_CLASS,
    NUMERIC_CONTRACTS,
    PROFILES,
    STAGE_COUNT,
    TARGET_ID,
    V41_NUMERIC_CONTRACTS,
    build_deepseek_v41_rom_deployment,
    deepseek_v41_rom_capability,
    deepseek_v41_stage_plan,
    link_class_count,
    region_stage,
    resident_hbm_region,
)
from compiler.ir.v3.kernel_ir import (
    KernelGraph,
    RuntimeSymbol,
    StateResource,
    Symbolic,
    Tensor,
    check_neutral,
)
from runtime.abi3.capability import canonical_json
from runtime.abi3.constants import (
    DTYPE_BITS,
    DType,
    Link,
    Major,
    NO_NODE,
    Permission,
    StorageClass,
    TopologyClass,
)
from runtime.abi3.crc import sha256
from runtime.abi3.descriptors import ExtendedDescriptorType
from runtime.abi3.records import ProgramHeader, decode_body, split_program
from runtime.abi3.verifier import verify_deployment

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _load_v4_fixture_module():
    """The V4 wafer backend's own test fixtures, reused rather than re-typed.

    ``tests`` is not a package, so the predecessor's proven graph and
    checkpoint builders are loaded by path.  Reusing them is the point: a V4.1
    fixture that rebuilt the decoder block differently would be testing a
    different model.
    """
    path = REPOSITORY_ROOT / "tests" / "compiler" / "test_rom_backend.py"
    spec = importlib.util.spec_from_file_location("_v4_rom_fixture", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_V4 = _load_v4_fixture_module()
_GraphBuilder = _V4._GraphBuilder
_finish = _V4._finish

#: The fixture's own geometry.  Every one of these is read back out of the
#: graph by the code under test; none of them is written into the backend.
HIDDEN = 64
KV_WIDTH = 32
EXPERT_WIDTH = 96
VOCABULARY = 32
SPAN_MAX = 16
COMPRESSION_RATIO = 4
INDEX_HEADS = 2
#: Routed experts and the routed top-k.  384 and 6 are the released V4.1 pins;
#: the fixture keeps the *shape* of the rule -- more experts than V4's record
#: admits and a narrower top-k -- at a size a 16-position test can build.
EXPERTS = 12
EXPERTS_PER_TOKEN = 3
#: The candidate pool: positions, the block width, and the blocks chosen.
CANDIDATE_POSITIONS = 8
CANDIDATE_BLOCK_SIZE = 2
CANDIDATE_BLOCKS_CHOSEN = 2
#: mHC streams the inter-layer residual carries.  Four, as the release does.
HC_MULT = 4
#: The fixture's Engram row table: rows x (head_dim + one scale per head).
ENGRAM_ROWS = 64
ENGRAM_HEAD_DIM = 8
ENGRAM_HEADS = 2


def _bytes_per_token(dtype: str, *static_dims: int) -> int:
    elements = 1
    for dim in static_dims:
        elements *= dim
    return (elements * DTYPE_BITS[DType[dtype.upper()]] + 7) // 8


# ---------------------------------------------------------------------------
# The V4.1-shaped graph
# ---------------------------------------------------------------------------
def deepseek_v41_shaped_graph(
    root: Path,
    *,
    owner_layers: tuple[int, ...] = (2, 4),
    engram_layers: tuple[int, ...] = (1,),
    candidate_source_layer: int = 4,
    layers: int = 7,
    strand_a_reader: bool = False,
) -> KernelGraph:
    """A V4.1-shaped decoder: CSA2 sharing, Engram, a candidate pool, MoE.

    ``owner_layers`` are the layers that own a global KV cache; every later
    layer up to the next owner reads it, which is the CSA2 relation the stage
    plan derives.  ``strand_a_reader`` deliberately makes the *last* layer read
    the *first* owner's cache, so that no contiguous two-stage partition leaves
    every reader with its owner -- the locality rule violated on purpose.
    """
    builder = _GraphBuilder(
        root / f"deepseek-v41-l{layers}-o{'-'.join(map(str, owner_layers))}"
        f"-{int(strand_a_reader)}.bin",
        seed=4141,
    )
    span = Symbolic("span_tokens", 1, SPAN_MAX)
    context = Symbolic("context_tokens", 1, SPAN_MAX)
    groups = Symbolic("span_groups_ratio4", 1, max(SPAN_MAX // COMPRESSION_RATIO, 1))

    token_ids = builder.value("input.token_ids", "u32", (span,), "input")
    positions = builder.value("input.positions", "u32", (span,), "input")
    embed = builder.weight("model.embed_tokens.weight", "bf16", (VOCABULARY, HIDDEN))
    residual = builder.value("sequence.embedding", "bf16", (span, HIDDEN), "activation")
    builder.kernel(
        "token_embedding",
        "EMBEDDING_LOOKUP",
        (token_ids, embed),
        (residual,),
        contract="bf16_payload_lookup_v1",
        attributes={"input_dtype": "u32", "output_dtype": "bf16"},
    )

    # One state resource per owner layer.  A reader layer declares none: it
    # reads the cache the owner wrote, which is exactly what makes the shared
    # cache a placement constraint instead of a per-layer buffer.
    states = tuple(
        StateResource(
            state_id=f"global_kv.owner.{owner}",
            state_class="compressed_kv",
            dtype="bf16",
            row_elements=2 * KV_WIDTH,
            capacity_rows=SPAN_MAX,
        )
        for owner in owner_layers
    )
    state_of_owner = {owner: states[index].state_id for index, owner in enumerate(owner_layers)}

    def owner_of(layer: int) -> int:
        candidates = [owner for owner in owner_layers if owner <= layer]
        return candidates[-1] if candidates else owner_layers[0]

    candidate_mask: str | None = None
    for layer in range(layers):
        base = f"model.layers.{layer}"
        prefix = f"decoder.{layer}"
        is_owner = layer in owner_layers
        owner = owner_of(layer)
        if strand_a_reader and layer == layers - 1:
            owner = owner_layers[0]
        state_id = state_of_owner[owner]
        compressed = f"decoder.{owner}.compressed"

        norm = builder.value(f"{prefix}.normalized", "bf16", (span, HIDDEN), "activation")
        builder.kernel(
            f"{prefix}.norm",
            "RMS_NORM",
            (
                residual,
                builder.weight(f"{base}.input_layernorm.weight", "bf16", (HIDDEN,)),
            ),
            (norm,),
            contract="deepseek_v4_hyper_connect_fp32_bf16_v1",
            attributes={"epsilon": 1e-06},
            layer=layer,
        )
        query = builder.value(f"{prefix}.query", "bf16", (span, HIDDEN), "activation")
        builder.kernel(
            f"{prefix}.query_projection",
            "MATMUL",
            (
                norm,
                builder.weight(
                    f"{base}.self_attn.q_proj.weight",
                    "fp8_e4m3fn",
                    (HIDDEN, HIDDEN),
                    scale_block_elements=32,
                ),
            ),
            (query,),
            contract="fp8_e4m3fn_fp8_e4m3fn_fp32_sequential_rne_v1",
            attributes={"input_dtype": "bf16", "second_input_dtype": "fp8_e4m3fn"},
            layer=layer,
        )
        if is_owner:
            latent = builder.value(
                f"{prefix}.latent", "bf16", (span, KV_WIDTH), "activation"
            )
            builder.kernel(
                f"{prefix}.key_value_projection",
                "MATMUL",
                (
                    norm,
                    builder.weight(
                        f"{base}.self_attn.kv_proj.weight",
                        "fp8_e4m3fn",
                        (KV_WIDTH, HIDDEN),
                        scale_block_elements=32,
                    ),
                ),
                (latent,),
                contract="fp8_e4m3fn_fp8_e4m3fn_fp32_sequential_rne_v1",
                attributes={"input_dtype": "bf16", "second_input_dtype": "fp8_e4m3fn"},
                layer=layer,
            )
            builder.kernel(
                f"{prefix}.compression",
                "COMPRESS_PROJECT",
                (
                    latent,
                    builder.weight(
                        f"{base}.compressor.weight", "bf16", (KV_WIDTH, KV_WIDTH)
                    ),
                    positions,
                ),
                (
                    builder.value(
                        f"{prefix}.compressed", "bf16", (groups, KV_WIDTH), "activation"
                    ),
                ),
                contract="deepseek_v4_compress_fp32_bf16_v1",
                attributes={"ratio": COMPRESSION_RATIO},
                layer=layer,
                state_writes=(state_id,),
            )
        index_query = builder.value(
            f"{prefix}.index_query", "bf16", (span, INDEX_HEADS, KV_WIDTH), "activation"
        )
        builder.kernel(
            f"{prefix}.index_query_projection",
            "MATMUL",
            (
                norm,
                builder.weight(
                    f"{base}.indexer.weight", "bf16", (INDEX_HEADS * KV_WIDTH, HIDDEN)
                ),
            ),
            (index_query,),
            contract="matrix_bf16_linear_bf16_v1",
            layer=layer,
        )
        index_weights = builder.value(
            f"{prefix}.index_head_weights", "bf16", (span, INDEX_HEADS), "activation"
        )
        builder.kernel(
            f"{prefix}.index_head_weight_projection",
            "MATMUL",
            (
                norm,
                builder.weight(
                    f"{base}.indexer.head_weight", "bf16", (INDEX_HEADS, HIDDEN)
                ),
            ),
            (index_weights,),
            contract="matrix_bf16_linear_bf16_v1",
            layer=layer,
        )
        scores = builder.value(
            f"{prefix}.index_scores", "bf16", (span, groups), "activation"
        )
        builder.kernel(
            f"{prefix}.index_score",
            "INDEX_SCORE",
            (index_query, compressed, index_weights),
            (scores,),
            contract="deepseek_v4_sparse_attention_fp32_softmax_v1",
            attributes={"head_weight_scale_binary32": "0x3c3504f3"},
            layer=layer,
        )
        if layer == candidate_source_layer:
            # ``select_candidate_blocks``: a block maximum over the candidate
            # scores, a top-k over the blocks, and the chosen block ids expanded
            # into the admission plane every later index top-k carries.
            candidate_scores = builder.value(
                f"{prefix}.candidate_scores",
                "bf16",
                (span, CANDIDATE_POSITIONS),
                "activation",
            )
            builder.kernel(
                f"{prefix}.candidate_score_projection",
                "MATMUL",
                (
                    norm,
                    builder.weight(
                        f"{base}.indexer.candidate_weight",
                        "bf16",
                        (CANDIDATE_POSITIONS, HIDDEN),
                    ),
                ),
                (candidate_scores,),
                contract="matrix_bf16_linear_bf16_v1",
                layer=layer,
            )
            block_scores = builder.value(
                f"{prefix}.block_scores",
                "bf16",
                (span, CANDIDATE_POSITIONS // CANDIDATE_BLOCK_SIZE),
                "activation",
            )
            builder.kernel(
                f"{prefix}.candidate_block_max",
                "BLOCK_MAX",
                (candidate_scores,),
                (block_scores,),
                contract="candidate_mask_v1",
                attributes={"candidate_block_size": CANDIDATE_BLOCK_SIZE},
                layer=layer,
            )
            block_ids = builder.value(
                f"{prefix}.block_ids", "u32", (span, CANDIDATE_BLOCKS_CHOSEN), "activation"
            )
            builder.kernel(
                f"{prefix}.candidate_block_topk",
                "INDEX_TOPK",
                (block_scores,),
                (block_ids,),
                contract="candidate_mask_v1",
                attributes={
                    "input_dtype": "bf16",
                    "output_dtype": "u32",
                    "k": CANDIDATE_BLOCKS_CHOSEN,
                },
                layer=layer,
            )
            candidate_mask = builder.value(
                f"{prefix}.candidate_mask", "u32", (span, CANDIDATE_POSITIONS), "activation"
            )
            builder.kernel(
                f"{prefix}.candidate_mask",
                "CANDIDATE_MASK",
                (block_ids,),
                (candidate_mask,),
                contract="candidate_mask_v1",
                attributes={
                    "candidate_block_size": CANDIDATE_BLOCK_SIZE,
                    "input_dtype": "u32",
                    "output_dtype": "u32",
                },
                layer=layer,
            )
        indices = builder.value(f"{prefix}.indices", "u32", (span, SPAN_MAX), "activation")
        topk_inputs: tuple[str, ...] = (scores,)
        topk_attributes: dict[str, Any] = {
            "input_dtype": "bf16",
            "output_dtype": "u32",
            "k": SPAN_MAX,
        }
        if candidate_mask is not None:
            # AM-E10 slot 3 is the candidate mask, and slots 1 and 2 -- the
            # joined window and the ratio -- are declared absent rather than
            # filled with the mask, which would be a different operator.
            topk_inputs = (scores, candidate_mask)
            topk_attributes["absent_operands"] = [1, 2]
        builder.kernel(
            f"{prefix}.index_topk",
            "INDEX_TOPK",
            topk_inputs,
            (indices,),
            contract="deepseek_v4_sparse_attention_fp32_softmax_v1",
            attributes=topk_attributes,
            layer=layer,
        )
        key_history = builder.value(
            f"{prefix}.key_history", "bf16", (context, KV_WIDTH), "state"
        )
        value_history = builder.value(
            f"{prefix}.value_history", "bf16", (context, KV_WIDTH), "state"
        )
        attention = builder.value(f"{prefix}.context", "bf16", (span, HIDDEN), "activation")
        builder.kernel(
            f"{prefix}.sparse_attention",
            "ATTENTION_SPARSE",
            (query, key_history, value_history, indices),
            (attention,),
            contract="deepseek_v4_sparse_attention_fp32_softmax_v1",
            layer=layer,
            state_reads=(state_id,),
        )
        attention_output = builder.value(
            f"{prefix}.attention_output", "bf16", (span, HIDDEN), "activation"
        )
        builder.kernel(
            f"{prefix}.output_projection",
            "MATMUL",
            (
                attention,
                builder.weight(
                    f"{base}.self_attn.o_proj.weight",
                    "fp8_e4m3fn",
                    (HIDDEN, HIDDEN),
                    scale_block_elements=32,
                ),
            ),
            (attention_output,),
            contract="fp8_e4m3fn_fp8_e4m3fn_fp32_sequential_rne_v1",
            attributes={"input_dtype": "bf16", "second_input_dtype": "fp8_e4m3fn"},
            layer=layer,
        )
        attention_residual = builder.value(
            f"{prefix}.attention_residual", "bf16", (span, HIDDEN), "activation"
        )
        builder.kernel(
            f"{prefix}.attention_residual_add",
            "ADD",
            (residual, attention_output),
            (attention_residual,),
            contract="bf16_add_rne_v1",
            layer=layer,
        )
        if layer in engram_layers:
            # The Engram module: a table a *layer* reads every token.  The
            # prologue's token embedding has no layer and is an ordinary model
            # weight; this one is the load-once resident region.
            engram_rows = builder.value(
                f"{prefix}.engram_rows", "bf16", (span, HIDDEN), "activation"
            )
            builder.kernel(
                f"{prefix}.engram_row_lookup",
                "EMBEDDING_LOOKUP",
                (
                    token_ids,
                    builder.weight(
                        f"{base}.engram.weight", "bf16", (ENGRAM_ROWS, HIDDEN)
                    ),
                ),
                (engram_rows,),
                contract="bf16_payload_lookup_v1",
                attributes={"input_dtype": "u32", "output_dtype": "bf16"},
                layer=layer,
            )
            gated = builder.value(
                f"{prefix}.engram_gated", "bf16", (span, HIDDEN), "activation"
            )
            builder.kernel(
                f"{prefix}.engram_residual_add",
                "ADD",
                (attention_residual, engram_rows),
                (gated,),
                contract="bf16_add_rne_v1",
                layer=layer,
            )
            attention_residual = gated
        feed_forward_norm = builder.value(
            f"{prefix}.feed_forward_normalized", "bf16", (span, HIDDEN), "activation"
        )
        builder.kernel(
            f"{prefix}.feed_forward_norm",
            "RMS_NORM",
            (
                attention_residual,
                builder.weight(
                    f"{base}.post_attention_layernorm.weight", "bf16", (HIDDEN,)
                ),
            ),
            (feed_forward_norm,),
            contract="deepseek_v4_hyper_connect_fp32_bf16_v1",
            attributes={"epsilon": 1e-06},
            layer=layer,
        )
        router_logits = builder.value(
            f"{prefix}.router_logits", "bf16", (span, EXPERTS), "activation"
        )
        builder.kernel(
            f"{prefix}.router_score",
            "ROUTER_SCORE",
            (
                feed_forward_norm,
                builder.weight(f"{base}.mlp.gate.weight", "bf16", (EXPERTS, HIDDEN)),
            ),
            (router_logits,),
            contract="deepseek_v4_router_fp32_sigmoid_v1",
            layer=layer,
        )
        expert_ids = builder.value(
            f"{prefix}.expert_ids", "u32", (span, EXPERTS_PER_TOKEN), "activation"
        )
        expert_weights = builder.value(
            f"{prefix}.expert_weights", "bf16", (span, EXPERTS_PER_TOKEN), "activation"
        )
        builder.kernel(
            f"{prefix}.router_topk",
            "BIASED_TOPK",
            (
                router_logits,
                builder.weight(
                    f"{base}.mlp.gate.e_score_correction_bias", "bf16", (EXPERTS,)
                ),
            ),
            (expert_ids, expert_weights),
            contract="deepseek_v4_router_fp32_sigmoid_v1",
            attributes={"input_dtype": "bf16", "output_dtype": "u32"},
            layer=layer,
        )
        dispatched = builder.value(
            f"{prefix}.dispatched", "bf16", (span, EXPERTS_PER_TOKEN, HIDDEN), "activation"
        )
        dispatched_ids = builder.value(
            f"{prefix}.dispatched_ids", "u32", (span, EXPERTS_PER_TOKEN), "activation"
        )
        builder.kernel(
            f"{prefix}.expert_dispatch",
            "EXPERT_DISPATCH",
            (feed_forward_norm, expert_ids),
            (dispatched, dispatched_ids),
            contract="deepseek_v4_router_fp32_sigmoid_v1",
            attributes={"expert_count": EXPERTS},
            layer=layer,
        )
        expert_output = builder.value(
            f"{prefix}.expert_output",
            "bf16",
            (span, EXPERTS_PER_TOKEN, EXPERT_WIDTH),
            "activation",
        )
        bank = builder.stacked_weight(
            f"{base}.mlp.experts.w1.weight",
            "mxfp4_e2m1",
            (EXPERTS, EXPERT_WIDTH, HIDDEN),
            experts=EXPERTS,
            scale_block_elements=32,
        )
        builder.kernel(
            f"{prefix}.routed_projection",
            "ROUTED_MATMUL",
            (dispatched, bank, dispatched_ids),
            (expert_output,),
            contract="mxfp4_e2m1_fp8_e4m3fn_fp32_blocked_rne_v1",
            attributes={
                "expert_count": EXPERTS,
                "expert_weight_block_elements": 32,
                "expert_weight_dtype": "mxfp4_e2m1",
                "expert_weight_order": "ascending_logical_expert_id",
                "input_dtype": "bf16",
                "second_input_dtype": "mxfp4_e2m1",
            },
            layer=layer,
        )
        feed_forward_output = builder.value(
            f"{prefix}.feed_forward_output", "bf16", (span, HIDDEN), "activation"
        )
        builder.kernel(
            f"{prefix}.expert_reduce",
            "EXPERT_REDUCE",
            (expert_output, expert_weights, dispatched_ids),
            (feed_forward_output,),
            contract="bf16_add_rne_v1",
            layer=layer,
        )
        layer_output = builder.value(
            f"{prefix}.residual", "bf16", (span, HIDDEN), "activation"
        )
        builder.kernel(
            f"{prefix}.feed_forward_residual_add",
            "ADD",
            (attention_residual, feed_forward_output),
            (layer_output,),
            contract="bf16_add_rne_v1",
            layer=layer,
        )
        residual = layer_output

    final = builder.value("sequence.final_norm", "bf16", (span, HIDDEN), "activation")
    builder.kernel(
        "final_norm",
        "RMS_NORM",
        (residual, builder.weight("model.norm.weight", "bf16", (HIDDEN,))),
        (final,),
        contract="deepseek_v4_hyper_connect_fp32_bf16_v1",
        attributes={"epsilon": 1e-06},
    )
    last = builder.value("sequence.last_token", "bf16", (1, HIDDEN), "activation")
    builder.kernel(
        "last_token_select",
        "LAST_TOKEN_SELECT",
        (final, positions),
        (last,),
        contract="exact_index_select_v1",
        attributes={"input_dtype": "bf16", "output_dtype": "bf16"},
    )
    logits = builder.value("output.logits", "bf16", (1, VOCABULARY), "output")
    builder.kernel(
        "vocabulary_projection",
        "VOCAB_PROJECT",
        (last, builder.weight("lm_head.weight", "bf16", (VOCABULARY, HIDDEN))),
        (logits,),
        contract="bf16_bf16_fp32_sequential_rne_v1",
    )
    selected = builder.value("output.selected", "u32", (1,), "activation")
    builder.kernel(
        "token_selection",
        "ARGMAX",
        (logits,),
        (selected,),
        contract="greedy_lowest_token_id_argmax_v1",
        attributes={"input_dtype": "bf16", "output_dtype": "u32"},
    )
    next_token = builder.value("output.next_token", "u32", (1,), "output")
    builder.kernel(
        "token_append",
        "TOKEN_APPEND",
        (selected,),
        (next_token,),
        contract="exact_token_append_eos_v1",
        attributes={"input_dtype": "u32", "output_dtype": "u32"},
    )
    builder.kernel(
        "state_commit",
        "STATE_COMMIT",
        (),
        (),
        contract="bf16_byte_preserving_state_v1",
        state_reads=tuple(s.state_id for s in states),
        state_writes=tuple(s.state_id for s in states),
    )
    return _finish(
        builder,
        model_id="deepseek-v4.1-flash-synthetic",
        states=states,
        vocabulary=VOCABULARY,
        span_max=SPAN_MAX,
        inputs=(token_ids, positions),
        outputs=(logits, next_token),
        extra_symbols=(
            RuntimeSymbol(
                name="span_groups_ratio4",
                minimum=0,
                maximum=max(SPAN_MAX // COMPRESSION_RATIO, 1),
                binding="derived",
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def workspace(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("rom-v41")


@pytest.fixture(scope="module")
def graph(workspace: Path) -> KernelGraph:
    return deepseek_v41_shaped_graph(workspace)


@pytest.fixture(scope="module")
def capability():
    return _capability()


def _capability(**overrides):
    parameters: dict[str, Any] = {
        "max_context_positions": SPAN_MAX,
        "vocabulary_size": VOCABULARY,
        "expert_count": EXPERTS,
        "experts_per_token": EXPERTS_PER_TOKEN,
        "candidate_positions": CANDIDATE_POSITIONS,
        "resident_region_bytes": 1 << 20,
        "tile_rom_bytes": 1 << 16,
        "tiles_per_reticle": 8,
    }
    parameters.update(overrides)
    return deepseek_v41_rom_capability(**parameters)


@pytest.fixture(scope="module")
def build(graph, capability):
    return build_deepseek_v41_rom_deployment(
        graph,
        capability=capability,
        tile_rom_bytes=1 << 16,
        tiles_per_reticle=8,
    )


def _rom_objects(deployment):
    return [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.MEMORY_OBJECT
        and d.payload["storage_class"] == int(StorageClass.ROM)
    ]


def _instructions(deployment):
    _header, body = split_program(deployment.program)
    return decode_body(body)


def _topology(deployment):
    return next(
        d.payload
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.TOPOLOGY
    )


def _communications(deployment):
    return [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.COMMUNICATION
    ]


def _restamp(deployment):
    old, body = split_program(deployment.program)
    fields = {
        "instruction_count": old.instruction_count,
        "entrypoint_count": old.entrypoint_count,
        "required_features": old.required_features,
        "deployment_digest": bytes(32),
        "descriptor_table_digest": deployment.table.digest,
        "topology_digest": old.topology_digest,
        "body_digest": sha256(body),
        "max_retired_work": old.max_retired_work,
        "watchdog_class": old.watchdog_class,
        "entrypoint_table_descriptor": old.entrypoint_table_descriptor,
        "signature_metadata_descriptor": old.signature_metadata_descriptor,
    }
    deployment.program = ProgramHeader(**fields).encode() + body
    fields["deployment_digest"] = deployment.deployment_digest
    deployment.program = ProgramHeader(**fields).encode() + body
    return deployment


# ---------------------------------------------------------------------------
# The graph itself
# ---------------------------------------------------------------------------
def test_fixture_graph_is_neutral(graph):
    assert not check_neutral(graph)


def test_fixture_declares_the_v41_mechanisms(graph):
    kinds = [kernel.kind for kernel in graph.kernels]
    assert kinds.count("BLOCK_MAX") == 1
    assert kinds.count("CANDIDATE_MASK") == 1
    layered_lookups = [
        kernel
        for kernel in graph.kernels
        if kernel.kind == "EMBEDDING_LOOKUP" and kernel.layer is not None
    ]
    assert len(layered_lookups) == 1
    shared = [
        state
        for state in graph.states
        if state.state_class == "compressed_kv"
    ]
    assert len(shared) == 2


# ---------------------------------------------------------------------------
# The stage plan (plan sections 6.1 and 6.2)
# ---------------------------------------------------------------------------
def test_stage_plan_partitions_on_a_shared_cache_boundary(graph):
    plan = deepseek_v41_stage_plan(graph)
    assert plan.stage_count == STAGE_COUNT == 2
    # Two stages, both non-empty, and every layer placed exactly once.
    placed = [layer for layers in plan.layers_by_stage for layer in layers]
    assert sorted(placed) == sorted({k.layer for k in graph.kernels if k.layer is not None})
    assert all(plan.layers_by_stage)
    # The second wafer holds the embedding and the head, as 6.2 states.
    assert plan.global_stage == plan.stage_count - 1
    # Every shared cache has its owner and all its readers on one stage.
    for state, (owner, readers) in plan.shared_states.items():
        stages = {plan.stage_of_run[run] for run in (owner, *readers)}
        assert len(stages) == 1, (state, stages)


def test_stage_plan_refuses_a_partition_that_strands_a_reader(workspace):
    stranded = deepseek_v41_shaped_graph(workspace, strand_a_reader=True)
    with pytest.raises(DeepSeekV41RomError) as excinfo:
        deepseek_v41_stage_plan(stranded)
    message = str(excinfo.value)
    assert "no contiguous 2-stage partition" in message
    assert "shared cache on one wafer" in message


def test_cross_stage_payload_is_derived_from_the_tensors_that_cross(graph):
    plan = deepseek_v41_stage_plan(graph)
    assert len(plan.cross_stage_bytes) == 1
    crossing = plan.cross_stage_tensors[0]
    assert crossing, "a pipeline stage that receives nothing is not a stage"
    expected = sum(
        _bytes_per_token(
            next(t for t in graph.tensors if t.tensor_id == name).dtype,
            *[
                int(dim)
                for dim in next(t for t in graph.tensors if t.tensor_id == name).shape
                if not isinstance(dim, Symbolic)
            ],
        )
        for name in crossing
    )
    assert plan.cross_stage_bytes[0] == expected > 0


def test_the_released_mhc_residual_prices_the_plans_cross_wafer_payload():
    """The derivation, run on the released shape rather than the fixture's.

    Plan section 3.1 quotes 40,960 B of cross-wafer payload per token: the four
    mHC residual streams at BF16 with a 5,120-wide hidden state.  The backend
    computes a crossing's bytes from the tensor's own declared shape, so the
    same function applied to that shape has to reproduce the figure.
    """
    from compiler.backends.rom.deepseek_v41 import _tensor_bytes_per_token

    residual = Tensor(
        tensor_id="decoder.19.residual",
        dtype="bf16",
        shape=(Symbolic("span_tokens", 1, 1048576), HC_MULT, 5120),
        role="activation",
    )
    assert _tensor_bytes_per_token(residual) == 40960


def test_region_stage_refuses_a_key_it_cannot_attribute(graph):
    plan = deepseek_v41_stage_plan(graph)
    assert region_stage("rom.global.k00001.s1", plan) == plan.global_stage
    assert region_stage("rom.r0.p000.s1", plan) == plan.stage_of_run[0]
    assert region_stage("rom.r0.p000.s1.scale", plan) == plan.stage_of_run[0]
    with pytest.raises(DeepSeekV41RomError):
        region_stage("rom.mystery.s0", plan)


# ---------------------------------------------------------------------------
# The deployment
# ---------------------------------------------------------------------------
def test_deployment_is_admitted_by_the_frozen_verifier(build, capability):
    deployment, _plan = build
    verification = verify_deployment(deployment, capability)
    assert verification.admitted, verification.errors
    assert deployment.target_id == TARGET_ID
    assert deployment.backend == "rom.wafer_logical_device"


def test_topology_is_two_wafer_logical_devices(build):
    deployment, _plan = build
    topology = _topology(deployment)
    assert topology["topology_class"] == int(TopologyClass.WAFER_LOGICAL_DEVICE)
    assert topology["node_count"] == 2
    assert topology["link_class_count"] == link_class_count(2) == 4


def test_every_wafer_holds_rom_and_no_region_straddles_one(build):
    deployment, plan = build
    nodes = {
        shard.coordinate.node_id for region in plan.regions for shard in region.shards
    }
    assert nodes == {0, 1}
    for region in plan.regions:
        assert len({shard.coordinate.node_id for shard in region.shards}) == 1, region.key
    # Every *planned* region names the wafer it sits on.  A mask-programmed
    # derived constant -- a rotary table, a position range -- has no checkpoint
    # range and no region, and is emitted with ``NO_NODE``: on a two-wafer
    # machine that is a replica on both wafers rather than a placement on one,
    # which is what the sentinel means and what the ABI has room to say.
    placed = {region.object_id for region in plan.regions} | {
        region.pad_object_id for region in plan.regions if region.pad_bytes
    }
    by_id = {d.descriptor_id: d for d in _rom_objects(deployment)}
    assert {by_id[oid].payload["node_id"] for oid in placed} == {0, 1}
    replicas = [
        d for d in _rom_objects(deployment) if d.descriptor_id not in placed
    ]
    for descriptor in replicas:
        assert descriptor.payload["node_id"] == NO_NODE
        assert deployment.objects[descriptor.descriptor_id].kind == "generated"


def test_the_layer_partition_is_reported_in_the_notes(build, graph):
    deployment, _plan = build
    stage_plan = deployment.notes["stage_plan"]
    placement = deployment.notes["wafer_placement"]
    assert stage_plan["stage_count"] == 2
    assert placement["wafer_count"] == 2
    assert sorted(placement["rom_bytes_by_node"]) == ["0", "1"]
    assert all(int(value) > 0 for value in placement["rom_bytes_by_node"].values())


def test_one_inter_wafer_remote_dma_per_token(build):
    deployment, _plan = build
    instructions = _instructions(deployment)
    remote = [
        i
        for i in instructions
        if i.major == int(Major.LINK) and i.sub == int(Link.REMOTE_DMA)
    ]
    assert len(remote) == 1
    communications = {d.descriptor_id: d for d in _communications(deployment)}
    payload = communications[remote[0].descriptor_id].payload
    assert payload["route_class"] == INTER_WAFER_ROUTE_CLASS == 3
    assert payload["participant_count"] == 2
    assert (payload["source_node"], payload["destination_node"]) == (0, 1)
    assert payload["byte_extent"] > 0


def test_the_inter_wafer_step_carries_the_derived_payload(build, graph):
    deployment, _plan = build
    plan = deepseek_v41_stage_plan(graph)
    communications = {d.descriptor_id: d for d in _communications(deployment)}
    remote = [
        communications[i.descriptor_id].payload
        for i in _instructions(deployment)
        if i.major == int(Major.LINK) and i.sub == int(Link.REMOTE_DMA)
    ]
    assert [p["byte_extent"] for p in remote] == [plan.cross_stage_bytes[0]]


def test_the_resident_region_is_the_layered_lookup_tables(build, graph):
    deployment, _plan = build
    resident = resident_hbm_region(graph)
    assert resident["table_count"] == 1
    assert resident["layers"] == [1]
    assert resident["bytes"] == ENGRAM_ROWS * HIDDEN * 2
    note = deployment.notes["resident_hbm_region"]
    assert {key: note[key] for key in resident} == resident


def test_the_resident_tables_are_in_hbm_and_not_in_the_rom_image(build, graph):
    """The double count, refused: a resident byte is not also a ROM byte.

    The tables are declared in ``memory.hbm.resident_region_bytes`` *and* were
    placed in the ROM image, so every one of these bytes was paid for twice.
    What proves the fix is not a smaller number but a partition: the tensors are
    in the resident region list, they are in no ROM region, the objects behind
    them declare HBM, and the ROM total is the image without them.
    """
    deployment, plan = build
    resident = resident_hbm_region(graph)
    names = {member["tensor_id"] for member in resident["members"]}
    assert names

    rom_placed = {m.tensor_id for r in plan.regions for m in r.members}
    hbm_placed = {m.tensor_id for r in plan.resident_regions for m in r.members}
    assert names <= hbm_placed
    assert not (names & rom_placed)
    assert not (rom_placed & hbm_placed)

    assert plan.resident_payload_bytes == resident["bytes"]
    assert [r.residency for r in plan.resident_regions] == ["hbm"] * len(
        plan.resident_regions
    )
    # every resident region's object is an immutable HBM object
    objects = {
        d.descriptor_id: d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.MEMORY_OBJECT
    }
    for region in plan.resident_regions:
        obj = objects[region.object_id]
        assert obj.payload["storage_class"] == int(StorageClass.HBM)
        assert obj.permissions == int(Permission.READ | Permission.IMMUTABLE)
    for region in plan.regions:
        assert objects[region.object_id].payload["storage_class"] == int(
            StorageClass.ROM
        )

    note = deployment.notes["resident_hbm_region"]
    assert note["storage_class"] == StorageClass.HBM.name
    assert note["planned_bytes"] >= resident["bytes"]
    assert note["rom_bytes_without_it"] == plan.rom_bytes
    # and the plan record says so, which is what the inverse proof reads
    body = plan.to_dict()
    assert len(body["resident_regions"]) == len(plan.resident_regions)
    assert body["totals"]["resident_payload_bytes"] == resident["bytes"]
    assert "resident_regions" not in {
        r["key"] for r in body["regions"]
    }, "the ROM region list must not name the resident regions"


def test_a_resident_region_larger_than_the_capability_is_refused(graph):
    small = _capability(resident_region_bytes=1)
    with pytest.raises(DeepSeekV41RomError) as excinfo:
        build_deepseek_v41_rom_deployment(
            graph, capability=small, tile_rom_bytes=1 << 16, tiles_per_reticle=8
        )
    assert "load-once HBM region needs" in str(excinfo.value)


def test_a_one_node_capability_cannot_host_the_two_wafer_product(graph):
    single = _capability(stage_count=1)
    with pytest.raises(DeepSeekV41RomError) as excinfo:
        build_deepseek_v41_rom_deployment(
            graph,
            capability=single,
            stage_count=2,
            tile_rom_bytes=1 << 16,
            tiles_per_reticle=8,
        )
    assert "pipeline depth is the node count" in str(excinfo.value)


# ---------------------------------------------------------------------------
# The independent schedule checker (plan section 6.3)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def report(build, graph, capability):
    deployment, _plan = build
    return check_rom_schedule(graph, deployment, capability)


def test_schedule_certificate_passes_and_names_the_four_new_rules(report):
    assert report["status"] == "pass", report["errors"]
    for name in (
        "shared_state_locality",
        "resident_hbm_region",
        "candidate_pool_bound",
        "expert_capacity",
    ):
        assert report["checks"][name] is True, name
    assert report["checks"]["wafer_band_path"] is True
    assert report["checks"]["one_node_per_band"] is True


def test_the_checker_refuses_a_reader_moved_to_the_other_wafer(build, graph, capability):
    """The locality rule violated on purpose, at the level it is enforced.

    The backend refuses to *build* a stranded reader (see the stage-plan test),
    so the violation the checker must catch is one introduced afterwards: a
    reader band's mask ROM re-declared on the other device, which is exactly
    what a mis-generated or tampered placement looks like on the wire.
    """
    deployment, plan = build
    reader_runs = {
        run for _owner, readers in deepseek_v41_stage_plan(graph).shared_states.values()
        for run in readers
    }
    assert reader_runs
    candidate = copy.deepcopy(deployment)
    moved = 0
    for region in plan.regions:
        if not region.key.startswith("rom.r"):
            continue
        run = int(region.key[len("rom.r") :].partition(".")[0])
        if run not in reader_runs:
            continue
        descriptor = candidate.table[region.object_id]
        if int(descriptor.payload["node_id"]) != 0:
            continue
        descriptor.payload["node_id"] = 1
        candidate.table.rewrite(region.object_id)
        moved += 1
    assert moved, "the fixture has no reader-owned ROM region to move"
    _restamp(candidate)
    broken = check_rom_schedule(graph, candidate, capability)
    assert broken["status"] == "fail"
    assert broken["checks"]["shared_state_locality"] is False
    assert any("must sit on the device that owns it" in e for e in broken["errors"])


def test_the_checker_refuses_a_candidate_pool_over_the_capability(build, graph):
    deployment, _plan = build
    narrow = _capability(candidate_positions=CANDIDATE_POSITIONS // 2)
    report = check_rom_schedule(graph, deployment, narrow)
    assert report["checks"]["candidate_pool_bound"] is False
    assert any("over the capability's" in e for e in report["errors"])


def test_the_checker_refuses_v4s_expert_limits_for_a_v41_graph(build, graph):
    deployment, _plan = build
    narrow = _capability(expert_count=EXPERTS, experts_per_token=EXPERTS_PER_TOKEN - 1)
    report = check_rom_schedule(graph, deployment, narrow)
    assert report["checks"]["expert_capacity"] is False
    assert any("max_topk" in e for e in report["errors"])


def test_the_checker_refuses_a_writable_resident_table(build, graph, capability):
    """``resident_hbm_region``: a table with a write path is not load-once.

    The rule's three clauses are immutability, no STATE binding and no scatter.
    This exercises the first, which is the one a mutation can reach: the region
    plan has no scatter into a weight to redirect, and the checker's own report
    shows the other two clauses passing on the built deployment.
    """
    deployment, plan = build
    resident = resident_hbm_region(graph)
    names = {member["tensor_id"] for member in resident["members"]}
    assert names
    targets = [
        region.object_id
        for region in plan.resident_regions
        if {member.tensor_id for member in region.members} & names
    ]
    assert targets, "the resident region names no planned object"
    candidate = copy.deepcopy(deployment)
    for object_id in targets:
        descriptor = candidate.table[object_id]
        # Not ``IMMUTABLE | WRITE``: the wire format refuses that mask outright
        # on encode, which is its own separate guard.  Dropping IMMUTABLE is the
        # mask a mutable table would really carry.
        descriptor.permissions = int(Permission.READ | Permission.WRITE)
        candidate.table.rewrite(object_id)
    _restamp(candidate)
    broken = check_rom_schedule(graph, candidate, capability)
    assert broken["checks"]["resident_hbm_region"] is False
    assert any("no immutable object backs them" in e for e in broken["errors"])


# ---------------------------------------------------------------------------
# Inverse proof and byte-identical rebuild (the plan's exit criteria)
# ---------------------------------------------------------------------------
def test_inverse_proof_passes(build, workspace):
    deployment, plan = build
    proof = check_rom_inverse(deployment, root=workspace)
    assert proof["status"] == "pass", proof
    assert proof["all_padding_zero"] is True
    assert proof["placed_tensor_count"] > 0


def test_the_inverse_proof_covers_the_resident_bytes(build, workspace, graph):
    """The resident region is proved, not excused.

    Moving bytes out of the ROM image must not move them out of the proof.  The
    independent checker reconstructs them from the checkpoint bit for bit, the
    same standard the mask image is held to, and reports them separately so a
    reader can see they were not quietly folded into the ROM total.
    """
    deployment, plan = build
    resident = resident_hbm_region(graph)
    proof = check_rom_inverse(deployment, root=workspace)
    assert proof["resident_region_count"] == len(plan.resident_regions) > 0
    assert proof["resident_payload_bytes"] == resident["bytes"]
    assert proof["rom_bytes"] == plan.rom_bytes
    assert proof["bit_identical"] is True
    # the resident tensors are among the reconstructed ones
    assert proof["placed_tensor_count"] == sum(
        len(r.members) for r in (*plan.regions, *plan.resident_regions)
    )


def test_the_inverse_proof_refuses_a_resident_region_left_in_rom(build, workspace):
    """The double count, as a refusal: a ROM object cannot back a resident region.

    The failure this guards is the one the fix is for -- the same bytes declared
    resident and carried by the mask.  Re-pointing a resident region at a ROM
    object is the smallest expression of it, and the proof must not accept it.
    """
    deployment, plan = build
    candidate = copy.deepcopy(deployment)
    body = candidate.notes["rom_plan"]
    rom_object = body["regions"][0]["object_id"]
    body["resident_regions"][0]["object_id"] = rom_object
    with pytest.raises(Exception) as excinfo:
        check_rom_inverse(candidate, root=workspace)
    assert "resident HBM memory object" in str(excinfo.value)


def test_rebuild_is_byte_identical(graph, capability, build):
    deployment, plan = build
    again, again_plan = build_deepseek_v41_rom_deployment(
        graph,
        capability=capability,
        tile_rom_bytes=1 << 16,
        tiles_per_reticle=8,
    )
    assert again.table.encode() == deployment.table.encode()
    assert again.program == deployment.program
    assert canonical_json(again.manifest()) == canonical_json(deployment.manifest())
    assert again_plan.to_dict() == plan.to_dict()
    assert again.deployment_digest == deployment.deployment_digest


# ---------------------------------------------------------------------------
# The published capability
# ---------------------------------------------------------------------------
def test_published_capability_matches_the_profile():
    published = (
        REPOSITORY_ROOT
        / "configs/hardware/abi3_capability/rom_deepseek_v41_wafer.json"
    )
    assert published.is_file(), "publish with tools/publish_abi3_capabilities.py"
    profile = PROFILES["rom-deepseek-v41-wafer-2"]()
    assert canonical_json(json.loads(json.dumps(profile.to_dict()))) == published.read_bytes()


def test_published_capability_states_the_v41_limits():
    profile = PROFILES["rom-deepseek-v41-wafer-2"]()
    assert profile.limits["max_nodes"] == 2
    assert profile.limits["max_expert_ids"] == 384
    assert profile.limits["max_topk"] == 6
    assert profile.limits["max_context_positions"] == 1048576
    assert profile.limits["max_candidate_positions"] == 16384
    assert profile.memory["rom"]["bytes"] >= 307_500_000_000
    assert profile.memory["hbm"]["bytes"] >= 1_440_000_000_000
    assert profile.memory["hbm"]["resident_region_bytes"] == 202_758_032_400
    assert set(V41_NUMERIC_CONTRACTS) <= set(profile.numeric_contracts)


def test_the_new_contracts_are_the_front_ends_own_names():
    """The four AM-E10 contracts are spelled as the V4.1 front end spells them."""
    from compiler.frontends.v3.deepseek_v41 import contract_for

    assert contract_for("CANDIDATE_BLOCK_SELECT") == "candidate_mask_v1"
    assert contract_for("ENGRAM_GATE") == "engram_gate_fp32_v1"
    assert contract_for("ENGRAM_NGRAM_HASH") == "ngram_hash_u32_v1"
    assert contract_for("FP4_MAIN_QDQ") == "fp4_e2m1_s16_e4m3_to_fp8_v1"
    assert set(V41_NUMERIC_CONTRACTS) <= set(NUMERIC_CONTRACTS)


def test_the_released_architecture_pins_are_what_the_capability_declares():
    """The capability's model-shaped defaults against the released pins.

    The point of the check is that nothing in the backend is a second statement
    of a model constant: each default here is the pin the front end confronts
    against the committed ``config.json``, and this test is where the two are
    put side by side.
    """
    from compiler.frontends.v3.deepseek_v41 import V41_FLASH_PROFILE

    pins = dict(V41_FLASH_PROFILE.architecture_pins)
    profile = PROFILES["rom-deepseek-v41-wafer-2"]()
    assert profile.limits["max_expert_ids"] == pins["n_routed_experts"]
    assert profile.limits["max_topk"] == pins["num_experts_per_tok"]
    assert profile.limits["max_vocabulary"] == pins["vocab_size"]
    assert profile.limits["max_context_positions"] == pins["max_position_embeddings"]
    assert (
        profile.limits["max_candidate_positions"]
        == pins["candidate_topk_blocks"] * pins["candidate_block_size"]
    )
    assert profile.memory["hbm"]["resident_region_bytes"] == sum(
        pins["engram_num_embeddings"]
    ) * (pins["engram_head_dim"] + pins["engram_n_heads"])
