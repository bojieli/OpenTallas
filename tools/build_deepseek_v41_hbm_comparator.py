#!/usr/bin/env python3
"""TA-DS41-HBM, the comparator: profile, sizing and AM-E10 admission evidence.

Plan section 3.3 and work package WP-G of
``docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md``.  That section makes one
claim and asks for two artifacts.  The claim is that **the HBM/SRAM backend is
model-blind and is reused as is**, with "none beyond the new IR kinds" required
of it.  The artifacts are one new profile and one comparison contract.

So this tool does not build a backend.  It

1. states the comparator **profile** -- the shared chip under amendment AM-R1's
   ``CLUSTER_N`` class at a node count that is a capability value, built by
   ``compiler.backends.hbm_sram.capability.cluster_n_capability``, which knows
   no model -- widened by exactly the four AM-E10 numeric contracts plan
   section 6.4 publishes;
2. derives the **node count** the way section 3.3 states it, from the released
   deployment profile's own weight bytes and per-token KV rather than from a
   number written here, and lists every admissible count with its capability
   digest so a comparison contract can pin one;
3. runs an **AM-E10 admission probe** through the unmodified model-blind
   backend: one decode layer carrying ``NGRAM_HASH``, the Engram row read,
   ``ENGRAM_GATE``, ``BLOCK_MAX``, ``CANDIDATE_MASK`` and a mask-carrying
   ``INDEX_TOPK``, with every extent taken from ``DeepSeekV41Profile``.  The
   probe is the evidence for the model-blindness claim that can be produced
   before the V4.1 IR exporter emits a graph, and it is labelled as a probe
   everywhere it appears; and
4. emits the **descriptor multiset** of whatever it lowered, through
   ``compiler.backends.rom.deepseek_v41_array.descriptor_multiset`` -- WP-F's
   own function, so the two sides of the DS41-P3 exit criterion are compared by
   one implementation rather than by two that agree today.

What it does **not** do is claim a comparator deployment.  That needs the V4.1
kernel IR, and ``compiler/frontends/v3/deepseek_v41.py`` does not emit one yet
(WP-D): the profile, the pins, the mode sequence and the census are complete and
the node-by-node lowering is not.  When ``--ir`` names a document, this tool
lowers *that* and the probe is not used; until then the document it writes
records the deployment as ``not_built`` and names what blocks it.

Two runs with the same inputs write byte-identical bytes, so the plan document's
SHA-256 is a rebuild criterion (DS41-P3 exit criterion 4)::

    PYTHONPATH=. python3 tools/build_deepseek_v41_hbm_comparator.py
    PYTHONPATH=. python3 tools/build_deepseek_v41_hbm_comparator.py --repeat
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.backends.hbm_sram.capability import (  # noqa: E402
    CLUSTER_DOMAIN_SIZE,
    HBM_BYTES_PER_NODE,
    SHARED_NUMERIC_CONTRACTS,
    cluster_n_capability,
)
from compiler.backends.hbm_sram.check import check_deployment  # noqa: E402
from compiler.backends.hbm_sram.lower import lower_with_plan  # noqa: E402
from compiler.backends.hbm_sram.plan import (  # noqa: E402
    PlanError,
    TileConfig,
    read_kernel_graph,
)
from compiler.frontends.v3.deepseek_v41 import (  # noqa: E402
    CONTRACT_BASE_BY_SOURCE_KIND,
    DEFAULT_CHECKPOINT_LOCK,
    FP4_MAIN_BLOCK,
    MAIN_LATENT_DTYPE,
    V41_FLASH_PROFILE,
    contract_for,
    missing_ir_artifacts,
)
from compiler.ir.v3.kernel_ir import (  # noqa: E402
    CheckpointBinding,
    Entrypoint,
    IRError,
    Kernel,
    KernelGraph,
    RuntimeSymbol,
    StateResource,
    Symbolic,
    Tensor,
    check_neutral,
)
from compiler.ir.v3.numeric import require_implemented  # noqa: E402
from runtime.abi3.capability import canonical_json  # noqa: E402
from runtime.abi3.constants import TopologyClass  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402
from runtime.reference.engram import ENGRAM_GATE_EPSILON_BINARY32  # noqa: E402

SCHEMA = "opentallas.deepseek_v41.hbm_comparator_plan.v1"
TARGET_ID = "deepseek-v4.1-flash-hbm-cluster-n"

#: The released deployment profile the comparator is sized from.  Section 3.3
#: puts the Engram tables in host memory "as DeepSeek serves them", which is the
#: ``engram_host`` variant: its ``checkpoint_bytes`` is the whole checkpoint
#: minus the two Engram tables, and ``metadata.host_resident_weight_bytes`` is
#: those tables.  Reading the variant is what keeps 307.5 GB out of this file.
CANDIDATE_PROFILE = (
    REPO / "configs" / "models" / "candidates" / "deepseek-v4.1-flash-engram_host.json"
)

#: The mandatory acceptance context (master plan section 4, plan section 3.1).
#: A parameter, and the default is the one the plan makes mandatory.
DEFAULT_CONTEXT_TOKENS = 200_000

#: The plan's own default output.
DEFAULT_OUTPUT = REPO / "results" / "abi3" / "deepseek_v41_hbm_comparator_plan.json"
DEFAULT_MULTISET_OUTPUT = (
    REPO / "results" / "abi3" / "deepseek_v41_hbm_comparator_descriptor_multiset.json"
)
#: The capability record the comparator compiles against, published as a file
#: because ``tools/check_hbm_deployments.py`` and ``tools/run_abi3_cycle.py``
#: read a record from disk.  This tool is its single definition, exactly as
#: ``tools/publish_abi3_capabilities.py`` is for the fixed-cardinality profiles:
#: the file is an artifact, not a second opinion, and it moves when the node
#: count or the declared union does.
DEFAULT_CAPABILITY_OUTPUT = (
    REPO / "results" / "abi3" / "deepseek_v41_hbm_comparator_capability.json"
)

#: The four AM-E10 numeric contracts plan section 6.4 publishes, taken from the
#: V4.1 front end's own contract table rather than restated here: the front end
#: is the authority on which name each new mechanism carries, and a second list
#: is how two lists diverge.  ``require_implemented`` then refuses to declare
#: any of them that nothing in the tree implements.
V41_SOURCE_KINDS: tuple[str, ...] = (
    "CANDIDATE_BLOCK_SELECT",
    "ENGRAM_GATE",
    "ENGRAM_NGRAM_HASH",
    "FP4_MAIN_QDQ",
)


class ComparatorError(RuntimeError):
    """Raised when the comparator plan cannot be stated truthfully."""


# ---------------------------------------------------------------------------
# 1. the profile
# ---------------------------------------------------------------------------
def v41_added_contracts() -> tuple[str, ...]:
    """The contracts the comparator declares beyond the shipped union."""
    names = {contract_for(kind) for kind in V41_SOURCE_KINDS}
    missing = sorted(kind for kind in V41_SOURCE_KINDS
                     if kind not in CONTRACT_BASE_BY_SOURCE_KIND)
    if missing:  # pragma: no cover - the front end would have refused first
        raise ComparatorError(
            f"the V4.1 front end declares no numeric contract for {missing}"
        )
    return require_implemented(
        names - set(SHARED_NUMERIC_CONTRACTS), what="the V4.1 HBM comparator"
    )


def comparator_capability(node_count: int):
    """The comparator profile: the shared chip, ``CLUSTER_N``, V4.1 contracts.

    The only V4.1-specific thing about it is the declared contract union.  The
    topology class, the fabric, the engines, the memory, the limits and the
    feature bits are the shipped chip's, unchanged, which is what makes a
    ROM-versus-HBM comparison a packaging comparison.
    """
    contracts = require_implemented(
        set(SHARED_NUMERIC_CONTRACTS) | set(v41_added_contracts()),
        what="the V4.1 HBM comparator capability",
    )
    return cluster_n_capability(node_count=node_count, numeric_contracts=contracts)


# ---------------------------------------------------------------------------
# 2. the node count, derived
# ---------------------------------------------------------------------------
def comparator_sizing(
    *,
    context_tokens: int = DEFAULT_CONTEXT_TOKENS,
    profile_path: Path = CANDIDATE_PROFILE,
    sessions: int = 1,
) -> dict[str, Any]:
    """Section 3.3's node count, from the released profile's own numbers.

    ``weights + session KV`` against the capability's HBM bytes per node is a
    *capacity floor*, not the fit: the physical plan adds activation arenas,
    generated constants and the compressor's own state, and only
    ``build_plan`` knows those.  The floor is what can be stated without the
    V4.1 IR, and it is labelled as a floor.
    """
    body = json.loads(Path(profile_path).read_text())
    metadata = body["metadata"]
    weights = int(body["checkpoint_bytes"])
    host_resident = int(metadata["host_resident_weight_bytes"])
    global_kv_per_token = float(metadata["global_kv_bytes_per_token"])
    session_kv = int(round(global_kv_per_token * int(context_tokens))) * int(sessions)
    per_node = int(HBM_BYTES_PER_NODE)
    required = weights + session_kv
    floor = -(-required // per_node)
    admissible = smallest_admissible_at_or_above(floor)
    return {
        "source_profile": str(Path(profile_path).relative_to(REPO)),
        "model": body["name"],
        "engram_placement": metadata["engram_placement"],
        "context_tokens": int(context_tokens),
        "sessions": int(sessions),
        "on_device_weight_bytes": weights,
        "host_resident_weight_bytes": host_resident,
        "global_kv_bytes_per_token": global_kv_per_token,
        "session_kv_bytes": session_kv,
        "required_bytes": required,
        "hbm_bytes_per_node": per_node,
        "capacity_floor_nodes": floor,
        "domain_size": int(CLUSTER_DOMAIN_SIZE),
        "smallest_admissible_nodes": admissible,
        "note": (
            "a capacity floor, not a plan fit: the physical plan adds activation "
            "arenas, generated constants and state, so the fitted count is "
            "build_plan's and needs the V4.1 kernel IR"
        ),
    }


def admissible_node_counts(*, maximum: int = 256) -> tuple[int, ...]:
    """Node counts a ``CLUSTER_N`` cluster of this chip can be built at.

    A whole number of the shipped fabric's domains, at least two nodes, and not
    32 -- that count is ``CLUSTER_32`` and the ABI refuses to express it twice.
    """
    counts = []
    for nodes in range(CLUSTER_DOMAIN_SIZE, int(maximum) + 1, CLUSTER_DOMAIN_SIZE):
        if nodes < 2 or nodes == 32:
            continue
        counts.append(nodes)
    return tuple(counts)


def smallest_admissible_at_or_above(floor: int) -> int:
    for nodes in admissible_node_counts():
        if nodes >= floor:
            return nodes
    raise ComparatorError(
        f"no admissible CLUSTER_N node count reaches {floor} nodes"
    )


# ---------------------------------------------------------------------------
# 3. the AM-E10 admission probe
# ---------------------------------------------------------------------------
_ELEMENT_BYTES = {
    "bf16": 2, "fp32": 4, "u32": 4, "i32": 4, "fp8_e4m3fn": 1, "e8m0": 1,
    MAIN_LATENT_DTYPE: 1, "u8": 1, "bool": 1,
}


class _Bindings:
    """Synthetic checkpoint bindings for the probe.

    Every probe weight is bound to a byte range of a file that does not exist.
    That is deliberate and is why the probe is not evidence about the model's
    numbers: it exercises the *lowering* of the AM-E10 kinds, and a lowering
    reads a binding's extent, never its bytes.
    """

    def __init__(self) -> None:
        self.cursor = 0

    def bind(self, name: str, elements: int, dtype: str) -> CheckpointBinding:
        size = elements * _ELEMENT_BYTES[dtype]
        offset = self.cursor
        self.cursor += size
        return CheckpointBinding(
            source_name=name,
            path="probe/model-00000.safetensors",
            offset=offset,
            bytes=size,
            sha256=hashlib.sha256(f"{name}:{offset}:{size}".encode()).hexdigest(),
        )


def am_e10_probe_graph(
    *,
    profile=V41_FLASH_PROFILE,
    span_max: int = 512,
    engram_rows: int | None = None,
    order_minimum: int = 2,
    latent_dtype: str = MAIN_LATENT_DTYPE,
) -> KernelGraph:
    """One decode layer carrying every AM-E10 mechanism, and nothing else.

    No extent here is a literal: the hidden width, the candidate block and block
    count, the pool population bound, the hash column count, the Engram head
    geometry, the compressed vocabulary, the n-gram orders, the sliding window
    and the reindex width all come from ``DeepSeekV41Profile``, and the scale
    group comes from the front end's ``FP4_MAIN_BLOCK``.  ``engram_rows``
    defaults to the released table height and a probe run may reduce it; the
    value used is recorded on the graph's ``source`` so no reader mistakes a
    reduced probe for the release.
    """
    hidden = profile.hidden
    window = profile.sliding_window
    block = profile.candidate_block
    blocks = profile.candidate_blocks
    columns = profile.engram_hash_columns
    heads = profile.engram_heads
    engram_width = profile.engram_head_dim * heads
    latent_row = profile.head_dim
    rows = profile.engram_rows[0] if engram_rows is None else int(engram_rows)
    candidate_axis = blocks * block
    orders = tuple(range(int(order_minimum), profile.engram_max_ngram + 1))

    span = Symbolic("span_tokens")
    context = Symbolic("context_tokens")
    context_blocks = Symbolic(f"context_groups_ratio{block}")

    binder = _Bindings()
    tensors: list[Tensor] = []
    kernels: list[Kernel] = []
    states: list[StateResource] = []

    def weight(name: str, shape: tuple[int, ...], dtype: str = "bf16") -> str:
        elements = 1
        for dim in shape:
            elements *= dim
        tensors.append(
            Tensor(
                tensor_id=name, dtype=dtype, shape=shape, role="weight",
                binding=binder.bind(name, elements, dtype),
            )
        )
        return name

    def act(name: str, shape: tuple, dtype: str = "bf16", role: str = "activation") -> str:
        tensors.append(Tensor(tensor_id=name, dtype=dtype, shape=shape, role=role))
        return name

    def emit(kind: str, ins, outs, contract: str, **kw) -> None:
        kernels.append(
            Kernel(
                index=len(kernels),
                kernel_id=f"k{len(kernels):04d}.{kind.lower()}",
                kind=kind, inputs=tuple(ins), outputs=tuple(outs),
                numeric_contract=contract, **kw,
            )
        )

    # The FP4 main latent, its E4M3-per-16 scale plane, and the window KV.
    states.append(StateResource(
        state_id="main_latent", state_class="kv_cache", dtype=latent_dtype,
        row_elements=latent_row, capacity_rows=span_max))
    states.append(StateResource(
        state_id="main_latent_scales", state_class="kv_cache", dtype="fp8_e4m3fn",
        row_elements=latent_row // FP4_MAIN_BLOCK, capacity_rows=span_max))
    states.append(StateResource(
        state_id="window_kv", state_class="kv_cache", dtype="fp8_e4m3fn",
        row_elements=latent_row, capacity_rows=window))
    act("main_latent", (span_max, latent_row), latent_dtype, role="state")
    act("main_latent_scales", (span_max, latent_row // FP4_MAIN_BLOCK),
        "fp8_e4m3fn", role="state")
    act("window_kv", (window, latent_row), "fp8_e4m3fn", role="state")

    act("tokens", (span, 1), "u32", role="input")
    weight("embed", (profile.vocabulary, hidden))
    act("hidden0", (span, hidden))
    emit("STATE_PREPARE", (), (), "bf16_byte_preserving_state_v1",
         state_writes=tuple(s.state_id for s in states))
    emit("EMBEDDING_LOOKUP", ["tokens", "embed"], ["hidden0"],
         "lookup_bf16_token_embedding_v1")

    # --- Engram: compressed ids, one NGRAM_HASH per order, row read, gate ---
    weight("compressed_ids", (profile.vocabulary, 1), "u32")
    act("engram.ids", (span, 1), "u32")
    emit("GATHER", ["tokens", "compressed_ids"], ["engram.ids"],
         "exact_index_select_v1")

    weight("engram.multipliers", (profile.engram_max_ngram,), "u32")
    weight("engram.columns", (2, len(orders), heads), "u32")
    row_id_parts = []
    for order in orders:
        name = act(f"engram.row_ids.n{order}", (span, heads), "u32")
        row_id_parts.append(name)
        emit("NGRAM_HASH",
             ["engram.ids", "engram.multipliers", "engram.columns"], [name],
             contract_for("ENGRAM_NGRAM_HASH"),
             attributes={
                 # in3, the dead-position flags an image span needs, is absent.
                 "absent_operands": [3],
                 "order": order,
                 "first_order": int(order_minimum),
                 "pad_id": profile.engram_compressed_vocabulary - 1,
                 "compressed_vocabulary": profile.engram_compressed_vocabulary,
             })
    act("engram.row_ids", (span, columns), "u32")
    emit("CONCAT", row_id_parts, ["engram.row_ids"], "exact_index_select_v1",
         attributes={"axis": 1})

    weight("engram.table", (rows, engram_width), "fp8_e4m3fn")
    act("engram.rows", (span, engram_width), "fp8_e4m3fn")
    emit("EMBEDDING_LOOKUP", ["engram.row_ids", "engram.table"], ["engram.rows"],
         "lookup_bf16_token_embedding_v1",
         attributes={"rows_per_token": columns})

    # The gate's key and value are the two planes of ONE projection output, the
    # packing VECTOR.ENGRAM_GATE reads in in1.
    weight("engram.wkv", (engram_width, 2 * hidden))
    weight("engram.wq", (hidden, hidden))
    weight("engram.wkey", (hidden, hidden))
    act("engram.rows_bf16", (span, engram_width))
    act("engram.kv", (span, 2, hidden), "fp32")
    act("engram.h", (span, hidden), "fp32")
    act("engram.q", (span, hidden), "fp32")
    act("engram.k", (span, hidden), "fp32")
    act("engram.gated", (span, hidden), "fp32")
    act("engram.out", (span, hidden))
    emit("CONVERT", ["engram.rows"], ["engram.rows_bf16"],
         "conversion_binary32_tensor_to_bf16_rne_v1")
    emit("MATMUL", ["engram.rows_bf16", "engram.wkv"], ["engram.kv"],
         "bf16_bf16_fp32_sequential_rne_v1")
    emit("CONVERT", ["hidden0"], ["engram.h"],
         "conversion_binary32_tensor_to_bf16_rne_v1")
    emit("MATMUL", ["hidden0", "engram.wq"], ["engram.q"],
         "bf16_bf16_fp32_sequential_rne_v1")
    emit("MATMUL", ["hidden0", "engram.wkey"], ["engram.k"],
         "bf16_bf16_fp32_sequential_rne_v1")
    emit("ENGRAM_GATE", ["engram.h", "engram.kv", "engram.q", "engram.k"],
         ["engram.gated"], contract_for("ENGRAM_GATE"),
         attributes={"epsilon_bits": ENGRAM_GATE_EPSILON_BINARY32})
    emit("CONVERT", ["engram.gated"], ["engram.out"],
         "conversion_binary32_tensor_to_bf16_rne_v1")

    # --- the FP4 main latent read: STATE_READ then DEQUANTIZE --------------
    act("latent.view", (span_max, latent_row), latent_dtype)
    act("latent.scales", (span_max, latent_row // FP4_MAIN_BLOCK), "fp8_e4m3fn")
    act("latent.fp8", (span_max, latent_row), "fp8_e4m3fn")
    emit("STATE_READ", ["main_latent"], ["latent.view"],
         "compressed_kv_valid_view_bf16_v1", state_reads=("main_latent",))
    emit("STATE_READ", ["main_latent_scales"], ["latent.scales"],
         "attention_kv_view_bf16_v1", state_reads=("main_latent_scales",))
    emit("DEQUANTIZE", ["latent.view", "latent.scales"], ["latent.fp8"],
         contract_for("FP4_MAIN_QDQ"),
         attributes={"scale_block_elements": FP4_MAIN_BLOCK})

    # --- the candidate pool: BLOCK_MAX, block top-k, CANDIDATE_MASK --------
    weight("index.wq", (hidden, profile.index_heads * profile.index_head_dim))
    weight("index.head_weights", (profile.index_heads, 1))
    weight("window.ratio", (1, 1), "u32")
    act("index.q", (span, profile.index_heads * profile.index_head_dim))
    act("index.kv", (span_max, profile.index_head_dim), "fp8_e4m3fn")
    act("index.scores", (span, context))
    act("window.index", (span, window), "u32")
    act("pool.block_scores", (span, context_blocks))
    act("pool.block_ids", (span, window + blocks), "u32")
    act("pool.mask", (span, context), "bool")
    act("reindex.indices", (span, window + profile.index_topk), "u32")
    emit("MATMUL", ["engram.out", "index.wq"], ["index.q"],
         "bf16_bf16_fp32_sequential_rne_v1")
    emit("STATE_READ", ["window_kv"], ["index.kv"],
         "attention_kv_view_bf16_v1", state_reads=("window_kv",))
    emit("INDEX_SCORE", ["index.q", "index.kv", "index.head_weights"],
         ["index.scores"], "index_score_bf16_v1",
         iteration_domain={"tokens": span, "candidates": context,
                           "heads": profile.index_heads,
                           "width": profile.index_head_dim})
    emit("BLOCK_MAX", ["index.scores"], ["pool.block_scores"],
         contract_for("CANDIDATE_BLOCK_SELECT"),
         attributes={"block": block, "order": "block_max_ordered_ieee"})
    emit("WINDOW_INDEX", ["window.ratio"], ["window.index"],
         "indexing_window_indices_v1",
         attributes={"index_family": "causal_circular_window",
                     "window_size": window})
    emit("INDEX_TOPK", ["pool.block_scores", "window.index", "window.ratio"],
         ["pool.block_ids"], contract_for("CANDIDATE_BLOCK_SELECT"),
         attributes={"k": blocks, "segment_widths": [window, blocks],
                     "segment_order": "window_then_rebased_compressed",
                     "order": "score_descending_then_index_ascending",
                     "padding_index": -1, "compression_ratio": 1})
    emit("CANDIDATE_MASK", ["pool.block_ids"], ["pool.mask"],
         contract_for("CANDIDATE_BLOCK_SELECT"),
         attributes={"block": block, "width": candidate_axis,
                     "population_bound": profile.candidate_pool_entries})
    emit("INDEX_TOPK",
         ["index.scores", "window.index", "window.ratio", "pool.mask"],
         ["reindex.indices"], contract_for("INDEX_TOPK", "masked_topk"),
         attributes={"k": profile.index_topk,
                     "segment_widths": [window, profile.index_topk],
                     "segment_order": "window_then_rebased_compressed",
                     "order": "score_descending_then_index_ascending",
                     "padding_index": -1, "compression_ratio": 1})

    # --- a consumer, a head, and the state transition ----------------------
    weight("attn.w", (profile.index_heads * profile.index_head_dim, hidden))
    weight("norm.final", (hidden,))
    weight("last.index", (1, 1), "u32")
    weight("lm_head", (hidden, profile.vocabulary))
    act("attn.out", (span, hidden))
    act("res", (span, hidden))
    act("hidden.final", (span, hidden))
    act("hidden.last", (1, hidden))
    act("logits", (1, profile.vocabulary))
    act("token", (1, 1), "u32")
    act("tokens.out", (1, 1), "u32", role="output")
    emit("MATMUL", ["index.q", "attn.w"], ["attn.out"],
         "bf16_bf16_fp32_sequential_rne_v1")
    emit("ADD", ["engram.out", "attn.out"], ["res"], "bf16_add_rne_v1")
    emit("RMS_NORM", ["res", "norm.final"], ["hidden.final"],
         "deepseek_rmsnorm_binary32_v1")
    emit("LAST_TOKEN_SELECT", ["hidden.final", "last.index"], ["hidden.last"],
         "lookup_bf16_token_embedding_v1")
    emit("VOCAB_PROJECT", ["hidden.last", "lm_head"], ["logits"],
         "lm_head_bf16_vocabulary_projection_v1")
    emit("ARGMAX", ["logits"], ["token"], "greedy_lowest_token_id_argmax_v1")
    emit("TOKEN_APPEND", ["token"], ["tokens.out"], "exact_token_append_eos_v1")
    emit("STATE_COMMIT", (), (), "bf16_byte_preserving_state_v1",
         state_writes=tuple(s.state_id for s in states))

    return KernelGraph(
        model_id=f"{profile.model_id}-am-e10-probe",
        source={
            "family": "deepseek-v4.1-flash-am-e10-admission-probe",
            "purpose": (
                "exercise the four AM-E10 kinds and the fp4_e2m1_s16_e4m3 dtype "
                "on the model-blind HBM/SRAM backend; NOT the released model"
            ),
            "main_latent_dtype": latent_dtype,
            "engram_rows_used": rows,
            "engram_rows_released": list(profile.engram_rows),
            "ngram_orders": list(orders),
        },
        symbols=(
            RuntimeSymbol("span_tokens", 1, span_max, 1),
            RuntimeSymbol("context_tokens", 1, span_max, 1),
            RuntimeSymbol(f"context_groups_ratio{block}", 1, span_max // block, 1),
        ),
        tensors=tuple(tensors),
        states=tuple(states),
        kernels=tuple(kernels),
        entrypoints=(
            Entrypoint("prefill", ("tokens",), ("tokens.out",),
                       tuple(s.state_id for s in states)),
            Entrypoint("decode", ("tokens",), ("tokens.out",),
                       tuple(s.state_id for s in states)),
        ),
        generation_policy={
            "eos_token_ids": [profile.vocabulary - 1],
            "maximum_new_tokens": 64,
            "vocabulary_size": profile.vocabulary,
        },
    )


# ---------------------------------------------------------------------------
# 4. lowering, and the descriptor multiset WP-F compares against
# ---------------------------------------------------------------------------
def _new_subop_rows(deployment) -> list[dict[str, Any]]:
    """Every operator of an AM-E10 sub-op, with its operand and aux row.

    The row is the evidence, not the admission: a ``ROUTE.BLOCK_MAX`` with
    ``aux_id_0`` empty is admitted by the verifier and traps at issue, because
    the block width is mandatory in the engine.  Printing the row is what makes
    the difference visible in a document.
    """
    from runtime.abi3.constants import Dma, Major, Route, Vector, NO_ID

    wanted = {
        (int(Major.ROUTE), int(Route.BLOCK_MAX)): "ROUTE.BLOCK_MAX",
        (int(Major.ROUTE), int(Route.CANDIDATE_MASK)): "ROUTE.CANDIDATE_MASK",
        (int(Major.ROUTE), int(Route.INDEX_TOPK)): "ROUTE.INDEX_TOPK",
        (int(Major.DMA), int(Dma.NGRAM_HASH)): "DMA.NGRAM_HASH",
        (int(Major.VECTOR), int(Vector.ENGRAM_GATE)): "VECTOR.ENGRAM_GATE",
    }
    rows: list[dict[str, Any]] = []
    for descriptor in deployment.table.descriptors():
        payload = descriptor.payload
        if "engine_sub" not in payload:
            continue
        key = (int(payload["engine_family"]), int(payload["engine_sub"]))
        name = wanted.get(key)
        if name is None:
            continue
        def slots(prefix: str, count: int) -> list[Any]:
            out = []
            for index in range(count):
                value = payload.get(f"{prefix}{index}")
                out.append(None if value is None or int(value) == int(NO_ID)
                           else int(value))
            return out
        rows.append({
            "engine": name,
            "input_views": slots("input_view_", 4),
            "aux_ids": slots("aux_id_", 4),
        })
    rows.sort(key=lambda row: (row["engine"], str(row["aux_ids"])))
    return rows


def block_max_view_tiling(deployment) -> list[dict[str, Any]]:
    """Does every ``ROUTE.BLOCK_MAX`` view pair tile at its declared block?

    ``runtime.sim.engines.route.block_max`` requires the output to hold exactly
    ``ceil(candidates / block)`` scores, tail included, and faults on a pair
    that does not tile rather than reducing over whatever is in range.  The
    check is measured from the emitted descriptors because this is the one place
    the probe is admitted and would still trap: a candidate axis the *context*
    sizes is planned at the span maximum on both sides unless the operator is
    named in ``compiler.backends.hbm_sram.plan.CONTEXT_LOOP_OPS``, whose own
    comment invites exactly that ("the set of operators reached so far ... will
    name themselves when they are reached").  Naming it changes the dispatch
    granularity of an operator nothing has qualified yet, so it belongs with the
    graph and the execution that can qualify it, not here.
    """
    from runtime.abi3.constants import Major, Route

    table = deployment.table.descriptors()
    rows: list[dict[str, Any]] = []
    for descriptor in table:
        payload = descriptor.payload
        if "engine_sub" not in payload:
            continue
        if (int(payload["engine_family"]), int(payload["engine_sub"])) != (
            int(Major.ROUTE), int(Route.BLOCK_MAX)
        ):
            continue
        block = int(payload.get("aux_id_0") or 0)
        source = table[int(payload["input_view_0"])].payload
        result = table[int(payload["output_view_0"])].payload
        candidates = int(source["dim1"]) or int(source["dim0"])
        scores = int(result["dim1"]) or int(result["dim0"])
        required = -(-candidates // block) if block else 0
        rows.append({
            "operator": int(descriptor.descriptor_id),
            "block": block,
            "candidate_columns": candidates,
            "score_columns": scores,
            "required_score_columns": required,
            "tiles": scores == required,
        })
    return rows


def array_side_reference() -> dict[str, Any]:
    """What the ROM array side declares, for the comparison contract to pin.

    Plan section 3.2 holds "node count and fabric fixed against TA-DS41-HBM",
    and section 3.3 raises this side's node count until the model fits.  Those
    are two different numbers unless a contract says which: the smallest fitting
    count is what 3.3 states and the array's count is what 3.2 wants held, so
    both are reported and neither is chosen here.  WP-N pins one.
    """
    try:
        from compiler.backends.rom import deepseek_v41_array as array
    except Exception as error:  # noqa: BLE001 - the array backend may be absent
        return {"available": False, "reason": repr(error)}
    return {
        "available": True,
        "module": "compiler.backends.rom.deepseek_v41_array",
        "capability_node_count": int(array.NODE_COUNT),
        "planned_node_count": int(array.PLAN_NODE_COUNT),
        "domain_size": int(array.DOMAIN_SIZE),
        "domains": int(array.DOMAIN_COUNT),
        "same_domain_size_as_comparator": (
            int(array.DOMAIN_SIZE) == int(CLUSTER_DOMAIN_SIZE)
        ),
        "note": (
            "a comparison contract that holds the node count fixed pins this "
            "side at the array's capability node count; --nodes selects it"
        ),
    }


def _multiset_document(deployment, *, label: str) -> dict[str, Any]:
    """The descriptor multiset, by WP-F's function, in a comparable form.

    A signature is a tuple of nested tuples, which JSON cannot key on, so each
    signature is recorded under the SHA-256 of its canonical JSON.  Two
    deployments are equal as multisets exactly when these maps are equal, which
    is the DS41-P3 exit criterion WP-F's
    ``compare_descriptor_multisets`` states directly.
    """
    try:
        from compiler.backends.rom.deepseek_v41_array import descriptor_multiset
    except Exception as error:  # noqa: BLE001 - the array backend may be absent
        return {
            "available": False,
            "reason": (
                "compiler.backends.rom.deepseek_v41_array.descriptor_multiset "
                f"could not be imported: {error!r}.  The multiset is WP-F's "
                "function deliberately, so this side does not restate it."
            ),
        }
    multiset = descriptor_multiset(deployment)
    counts: dict[str, int] = {}
    signatures: dict[str, Any] = {}
    by_type: dict[str, int] = {}
    for signature, count in multiset.items():
        blob = canonical_json(json.loads(json.dumps(signature, default=str)))
        key = hashlib.sha256(blob).hexdigest()
        counts[key] = counts.get(key, 0) + int(count)
        signatures[key] = json.loads(json.dumps(signature, default=str))
        by_type[str(signature[0])] = by_type.get(str(signature[0]), 0) + int(count)
    return {
        "available": True,
        "source": "compiler.backends.rom.deepseek_v41_array.descriptor_multiset",
        "label": label,
        "distinct_signatures": len(counts),
        "descriptor_count": sum(counts.values()),
        "by_type": dict(sorted(by_type.items())),
        "signature_counts": dict(sorted(counts.items())),
        "signatures": {key: signatures[key] for key in sorted(signatures)},
    }


def lower(graph: KernelGraph, node_count: int) -> dict[str, Any]:
    """Lower ``graph`` on the comparator profile and report what happened."""
    capability = comparator_capability(node_count)
    neutrality = check_neutral(graph)
    if neutrality:
        raise ComparatorError(
            "the graph is not neutral: " + "; ".join(neutrality)
        )
    deployment, plan = lower_with_plan(graph, capability, tile=TileConfig())
    again, again_plan = lower_with_plan(graph, capability, tile=TileConfig())
    verification = verify_deployment(deployment, capability)
    legality = check_deployment(graph, deployment, capability)
    return {
        "graph_id": graph.graph_id,
        "model_id": graph.model_id,
        "kernels": len(graph.kernels),
        "capability_digest": capability.digest,
        "topology_class": TopologyClass(capability.topology_class).name,
        "node_count": plan.topology.node_count,
        "plan_id": plan.plan_id,
        "deployment_digest": deployment.deployment_digest.hex(),
        "rebuild_identical": (
            again.program == deployment.program
            and again.table.encode() == deployment.table.encode()
            and again.deployment_digest == deployment.deployment_digest
            and again_plan.plan_id == plan.plan_id
        ),
        "instructions": verification.instruction_count,
        "descriptors": verification.descriptor_count,
        "admitted": verification.admitted,
        "verifier_errors": list(verification.errors),
        "checker_ok": bool(legality["ok"]),
        "checker_errors": list(legality["errors"]),
        "hbm_bytes_per_node": int(plan.proofs["hbm_bytes_per_node"]),
        "hbm_available_per_node": int(plan.proofs["hbm_available_per_node"]),
        "hbm_fits": bool(plan.proofs["hbm_fits"]),
        "am_e10_operators": _new_subop_rows(deployment),
    }, deployment


# ---------------------------------------------------------------------------
# the document
# ---------------------------------------------------------------------------
def _source_digest(path: Path) -> dict[str, Any]:
    body = path.read_bytes()
    return {
        "path": str(path.relative_to(REPO)),
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }


SOURCE_PATHS: tuple[str, ...] = (
    "compiler/backends/hbm_sram/capability.py",
    "compiler/backends/hbm_sram/check.py",
    "compiler/backends/hbm_sram/lower.py",
    "compiler/backends/hbm_sram/plan.py",
    "compiler/frontends/v3/deepseek_v41.py",
    "compiler/ir/v3/kernel_ir.py",
    "compiler/ir/v3/lowering.py",
    "runtime/abi3/capability.py",
    "runtime/abi3/verifier.py",
    "runtime/reference/engram.py",
    "tools/build_deepseek_v41_hbm_comparator.py",
)


def build_document(
    *,
    ir: Path | None,
    context_tokens: int,
    node_count: int | None,
    engram_rows: int | None,
) -> tuple[dict[str, Any], Any]:
    sizing = comparator_sizing(context_tokens=context_tokens)
    nodes = int(node_count) if node_count else int(sizing["smallest_admissible_nodes"])

    profile_rows = []
    for candidate in admissible_node_counts(maximum=max(64, nodes)):
        capability = comparator_capability(candidate)
        profile_rows.append({
            "nodes": candidate,
            "domains": capability.fabric["cluster"]["domains"],
            "capability_digest": capability.digest,
            "hbm_bytes": candidate * int(sizing["hbm_bytes_per_node"]),
            "holds_weights_and_session_kv": (
                candidate * int(sizing["hbm_bytes_per_node"])
                >= int(sizing["required_bytes"])
            ),
        })

    missing = missing_ir_artifacts(
        V41_FLASH_PROFILE, V41_FLASH_PROFILE.release.snapshot, DEFAULT_CHECKPOINT_LOCK
    )
    # The new dtype, on its own.  AM-E10 adds ``fp4_e2m1_s16_e4m3`` to the
    # neutral ``DTYPES`` and there is no ABI 3.0 ``DType`` for it, so no backend
    # can place a view of it -- this records the refusal verbatim rather than
    # mapping the format onto ``MXFP4_E2M1``, which would hand an E4M3-per-16
    # table to an engine expecting E8M0-per-32.
    dtype_probe: dict[str, Any] = {"dtype": MAIN_LATENT_DTYPE}
    try:
        lower(am_e10_probe_graph(engram_rows=engram_rows), nodes)
        dtype_probe.update(placed=True, error=None)
    except (PlanError, ComparatorError) as error:
        dtype_probe.update(placed=False, error=str(error))

    if ir is not None:
        graph = read_kernel_graph(ir)
        probe = False
    else:
        # The remaining three mechanisms, with the main latent in the format the
        # ABI does have a storage type for.  Everything AM-E10 added except the
        # dtype is exercised here.
        graph = am_e10_probe_graph(
            engram_rows=engram_rows, latent_dtype="fp8_e4m3fn"
        )
        probe = True
    lowered, deployment = lower(graph, nodes)

    capability = comparator_capability(nodes)
    document = {
        "schema": SCHEMA,
        "target_id": TARGET_ID,
        "plan": {
            "document": "docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md",
            "sections": ["3.3", "6.4", "13 (WP-G)"],
            "gate": "DS41-P3",
            "claim": (
                "the HBM/SRAM backend is model-blind and is reused as is, with "
                "none beyond the new IR kinds required of it"
            ),
        },
        "profile": {
            "name": "cluster-n + the four AM-E10 numeric contracts",
            "built_by": (
                "compiler.backends.hbm_sram.capability.cluster_n_capability"
            ),
            "topology_class": TopologyClass(capability.topology_class).name,
            "technology_view": capability.technology_view,
            "node_count": nodes,
            "capability_digest": capability.digest,
            "link": dict(capability.link),
            "fabric": json.loads(json.dumps(capability.fabric)),
            "shared_contract_count": len(SHARED_NUMERIC_CONTRACTS),
            "added_contracts": list(v41_added_contracts()),
            "declared_contract_count": len(capability.numeric_contracts),
            "admissible_node_counts": profile_rows,
        },
        "sizing": sizing,
        "array_side": array_side_reference(),
        "lowering": lowered,
        "new_dtype": dtype_probe,
        "known_gaps": [
            {
                "id": "am-e10-dtype-has-no-abi-storage-type",
                "owner": "WP-C / AM-E10",
                "statement": (
                    "fp4_e2m1_s16_e4m3 is in the neutral DTYPES and there is no "
                    "runtime.abi3.constants.DType for it, so no backend can "
                    "place a view of it.  Mapping it onto MXFP4_E2M1 would hand "
                    "an E4M3-per-16 table to an engine expecting E8M0-per-32, "
                    "which is what the separate neutral name exists to prevent"
                ),
                "measured": dtype_probe,
            },
            {
                "id": "block-max-context-axis-not-resolved-by-a-loop",
                "owner": "WP-G / WP-D",
                "statement": (
                    "ROUTE.BLOCK_MAX's candidate axis is sized by the CONTEXT, "
                    "and the operator is not named in "
                    "compiler.backends.hbm_sram.plan.CONTEXT_LOOP_OPS, so both "
                    "views are planned at the span maximum and the pair does "
                    "not tile at the declared block.  The verifier admits it "
                    "and the engine faults at issue; naming the operator in "
                    "that set is the fix, and it needs the real graph and an "
                    "execution to qualify"
                ),
                "measured": block_max_view_tiling(deployment),
            },
            {
                "id": "deployment-check-case-does-not-cover-the-new-kinds",
                "owner": "WP-G",
                "statement": (
                    "tools/check_hbm_deployments.py's _DEEPSEEK_ROUTE_CONTRACT "
                    "binds each cluster traffic class to a set of source kinds, "
                    "and BLOCK_MAX, CANDIDATE_MASK and NGRAM_HASH are in none "
                    "of them.  Per amendment A30's own note, an absent kind "
                    "does not fail the check -- it stops being covered by it.  "
                    "Adding them belongs with the first run of the "
                    "deepseek-v41-flash-hbm-cluster case, which needs the "
                    "deployment"
                ),
                "measured": None,
            },
        ],
        "lowered_input": {
            "kind": "am_e10_admission_probe" if probe else "kernel_ir_v3",
            "ir": None if ir is None else str(ir),
            "is_the_released_model": not probe,
        },
        "deployment": {
            "status": "not_built" if probe else "built",
            "blocked_on": (
                [
                    "compiler/frontends/v3/deepseek_v41.py emits no graph body: "
                    "export_deepseek_v41_kernel_graph() stops after resolving "
                    "96,085 tensor specs because the node-by-node lowering "
                    "(WP-D, gate DS41-I2) is not written",
                ]
                if probe
                else []
            ),
            "checkpoint_artifacts_missing": missing,
        },
        "source": {
            name: _source_digest(REPO / name) for name in sorted(SOURCE_PATHS)
        },
    }
    return document, deployment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--ir", type=Path, default=None,
        help=(
            "a published V4.1 Tensor Kernel IR v3 document.  Given one, the "
            "comparator is built from it and the probe is not used"
        ),
    )
    parser.add_argument("--context-tokens", type=int, default=DEFAULT_CONTEXT_TOKENS)
    parser.add_argument(
        "--nodes", type=int, default=None,
        help="override the derived node count (a comparison contract may pin one)",
    )
    parser.add_argument(
        "--engram-rows", type=int, default=1 << 16,
        help=(
            "probe-only: the Engram table height the probe declares.  The "
            "released height is 384,006,168 rows of 264 B, which is 101 GB of "
            "one table and is host-resident in this target, so a probe that is "
            "about the LOWERING declares fewer and says so"
        ),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--multiset-output", type=Path, default=DEFAULT_MULTISET_OUTPUT)
    parser.add_argument(
        "--capability-output", type=Path, default=DEFAULT_CAPABILITY_OUTPUT,
        help="where to publish the comparator's capability record",
    )
    parser.add_argument(
        "--repeat", action="store_true",
        help="build the document twice in one run and compare the two digests",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        document, deployment = build_document(
            ir=args.ir, context_tokens=args.context_tokens,
            node_count=args.nodes, engram_rows=args.engram_rows,
        )
    except (ComparatorError, PlanError, IRError) as error:
        print(f"comparator plan failed: {error}", file=sys.stderr)
        return 4

    blob = canonical_json(document)
    digest = hashlib.sha256(blob).hexdigest()
    repeat_digest = None
    if args.repeat:
        again, _ = build_document(
            ir=args.ir, context_tokens=args.context_tokens,
            node_count=args.nodes, engram_rows=args.engram_rows,
        )
        repeat_digest = hashlib.sha256(canonical_json(again)).hexdigest()

    multiset = _multiset_document(
        deployment, label=document["lowered_input"]["kind"]
    )
    multiset_body = {
        "schema": "opentallas.deepseek_v41.descriptor_multiset.v1",
        "side": "hbm_cluster_n",
        "target_id": TARGET_ID,
        "plan_gate": "DS41-P3",
        "comparable_with": (
            "compiler.backends.rom.deepseek_v41_array.compare_descriptor_multisets"
        ),
        "lowered_input": document["lowered_input"],
        "capability_digest": document["profile"]["capability_digest"],
        "node_count": document["profile"]["node_count"],
        "deployment_digest": document["lowering"]["deployment_digest"],
        "multiset": multiset,
    }
    multiset_blob = canonical_json(multiset_body)
    multiset_digest = hashlib.sha256(multiset_blob).hexdigest()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(blob)
    args.multiset_output.parent.mkdir(parents=True, exist_ok=True)
    args.multiset_output.write_bytes(multiset_blob)
    capability_blob = canonical_json(
        comparator_capability(document["profile"]["node_count"]).to_dict()
    )
    args.capability_output.parent.mkdir(parents=True, exist_ok=True)
    args.capability_output.write_bytes(capability_blob)

    if args.json:
        print(json.dumps(document, indent=2, sort_keys=True))
    else:
        lowered = document["lowering"]
        sizing = document["sizing"]
        print(f"target           {TARGET_ID}")
        print(
            f"profile          {document['profile']['topology_class']} x"
            f"{document['profile']['node_count']} node(s), capability "
            f"{document['profile']['capability_digest'][:16]}"
        )
        print(
            f"contracts        {document['profile']['shared_contract_count']} shared "
            f"+ {len(document['profile']['added_contracts'])} AM-E10 = "
            f"{document['profile']['declared_contract_count']}"
        )
        print(
            f"sizing           {sizing['on_device_weight_bytes'] / 1e9:.1f} GB of "
            f"weights + {sizing['session_kv_bytes'] / 1e6:.1f} MB session KV at "
            f"{sizing['context_tokens']:,} tokens needs "
            f"{sizing['capacity_floor_nodes']} node(s); smallest admissible "
            f"CLUSTER_N is {sizing['smallest_admissible_nodes']}"
        )
        print(
            f"lowered          {document['lowered_input']['kind']}: "
            f"{lowered['kernels']} kernels -> {lowered['instructions']} "
            f"instructions, {lowered['descriptors']} descriptors"
        )
        print(
            f"verifier         "
            f"{'ADMITTED' if lowered['admitted'] else 'REJECTED'}; checker "
            f"{'OK' if lowered['checker_ok'] else 'FAILED'}; rebuild "
            f"{'byte-identical' if lowered['rebuild_identical'] else 'DIVERGED'}"
        )
        for row in lowered["am_e10_operators"]:
            print(
                f"  {row['engine']:<22} in {row['input_views']}  aux {row['aux_ids']}"
            )
        dtype_probe_row = document["new_dtype"]
        print(
            f"new dtype        {dtype_probe_row['dtype']}: "
            + ("placed" if dtype_probe_row["placed"]
               else f"REFUSED -- {dtype_probe_row['error']}")
        )
        print(f"deployment       {document['deployment']['status']}")
        for reason in document["deployment"]["blocked_on"]:
            print(f"  blocked on: {reason}")
        print(f"wrote plan       {args.output}  sha256 {digest}")
        if repeat_digest is not None:
            print(
                f"rebuild          sha256 {repeat_digest}  "
                f"{'IDENTICAL' if repeat_digest == digest else 'DIVERGED'}"
            )
        print(
            f"wrote capability {args.capability_output}  digest "
            f"{document['profile']['capability_digest'][:16]}"
        )
        if multiset["available"]:
            print(
                f"wrote multiset   {args.multiset_output}  sha256 "
                f"{multiset_digest}  ({multiset['distinct_signatures']} distinct "
                f"signatures over {multiset['descriptor_count']} descriptors)"
            )
        else:
            print(f"multiset         unavailable: {multiset['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
