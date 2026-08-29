"""Export the pinned DeepSeek-V4-Flash-0731 checkpoint into Tensor Kernel IR v3.

This front end is the only place the DeepSeek-V4-Flash forward is expressed for
ABI 3.0.  The shared HBM/SRAM backend and the ROM backend consume the one
document it emits, so it carries complete model semantics and no backend
concept: no memory target, no schedule, no engine instance, no address
(ADR-003 section 15, enforced by ``compiler.ir.v3.kernel_ir.check_neutral``).

What it reuses rather than restates
-----------------------------------
* ``compiler.frontend.deepseek_v4_graph.build_official_graph_contract`` supplies
  the frozen 2,136-node, 46-operator-kind semantic graph.  This module walks
  that graph node by node and lowers each node into one or more neutral
  kernels, so the neutral IR cannot drift from the source-mapped semantics and
  the census can be reported per source operator kind.
* ``compiler.frontend.deepseek_v4`` supplies the 72,317 :class:`TensorSpec`
  records -- exact name, storage dtype, shape, semantic role, scope, layer and
  expert -- derived from the released configuration.
* ``compiler.frontend.checkpoint`` supplies the hash-locked checkpoint whose
  shard headers are re-read here to derive each weight's exact byte range.
* ``runtime.reference.*`` supplies the bit-exact target-precision identity per
  source operator kind; each neutral kernel names the reference that owns its
  numeric contract, qualified by the sub-operation it implements.

Weight bindings
---------------
Every weight tensor carries a :class:`CheckpointBinding` naming the shard file,
the absolute byte offset (safetensors 8-byte length prefix + header length +
the header's ``data_offsets`` start), the byte length, and the SHA-256 of
exactly those bytes.  A backend turns that into an ABI 3.0 object source and
never materialises a private copy of the 156 GB weight image.  Paths are
relative to the checkpoint snapshot so the graph identity is reproducible on
any host that holds the pinned revision.

Block-scaled formats
--------------------
FP8-E4M3 and MXFP4-E2M1 payloads and their E8M0 scale payloads are separate
tensors linked by ``scale_tensor_id``.  ``scale_block_elements`` is the number
of contiguous logical elements **along the reduction axis** covered by one
scale value: 128 for the released 128x128 FP8 weight blocks, 32 for the MXFP4
expert weights, 128 for dynamic activation quantization, and 64 for the
attention KV quantize/dequantize round trip.  The scale tensor's own declared
shape carries the remaining geometry.

Speculation
-----------
``include_speculative`` selects the profile.  The first release graph is the
ordinary target-model path -- the 43 main layers plus the head -- because
ADR-003 section 18 sequences ordinary DeepSeek generation before speculative
execution, and the DSpark verification/acceptance contract is still open
(DSV4-SEM-001).  Setting the flag adds the three ``mtp.*`` DSpark blocks, the
DSpark conditioning projection, the Markov draft head and the confidence head.

Required contract changes
-------------------------
Three source behaviours cannot be expressed in the frozen neutral registry.
No opcode is invented here; each is reported so it can be added through a
versioned change to ``compiler/ir/v3/kernel_ir.py`` and
``compiler/ir/v3/lowering.py``, never privately.

**IR3-GAP-1, stochastic token selection.**  ``inference/model.py:sample``
divides by an exponential draw and takes the argmax (Gumbel-max).  No neutral
kind produces or consumes randomness, so only the greedy branch is
expressible; this export emits ``SCALE`` + ``ARGMAX`` + ``TOKEN_APPEND`` and
declares the boundary in ``generation_policy``.  ``input.entropy_stream`` is
declared and carried unchanged so a later graph can bind it.  Proposal: add
``CATEGORICAL_SAMPLE`` taking (logits, temperature, entropy) and producing
(token, entropy_continuation), lowered to a new ``Selection`` subopcode.
Both-model impact: Qwen3 needs the same kind for any non-greedy request, so
until it exists both lanes are pinned to greedy argmax and neither can honour
the released ``do_sample: true`` generation configuration.

**IR3-GAP-2, predicated execution.**  ``Compressor.forward`` runs its pooling,
normalisation, rotation, quantize/dequantize and compressed-KV commit only at
a ratio-derived boundary, and the source graph carries that as a first-class
node ``guard`` over a boolean predicate value.  :class:`Kernel` has no
predicate field and no neutral kind produces a ``bool`` tensor, so this export
carries the guard in the ``execution_predicate`` attribute, which a backend is
not obliged to honour.  Proposal: add ``predicate: str = ""`` to ``Kernel``,
let ``COMPRESS_STATE_UPDATE`` declare a ``bool`` predicate output, and have
``check_neutral`` require a predicate to be an earlier kernel's output.  ABI
3.0 already carries ``predicate_id`` on its loop descriptor, so the neutral IR
is the only layer missing the concept.  Both-model impact: Qwen3 has no
data-dependent predicate today, but every conditional, early-exit or
speculative profile in either lane needs one, including this model's own
speculative profile.

**IR3-GAP-3, banked weights.**  ``ROUTED_MATMUL`` is lowered with four operand
slots, which reads as (activation, weight bank, scale bank, expert index), but
:class:`CheckpointBinding` names exactly one contiguous byte range and the
released checkpoint interleaves the 256 experts of a layer, so no single range
covers a bank.  This export therefore declares all 66,048 routed expert weight
tensors individually -- each with its real shard, offset, length and SHA-256 --
and names the ordered family in the ``expert_weight_tensors`` attribute.
Proposal: add a segmented binding (an ordered list of ranges plus the SHA-256
of the assembled payload) or an explicit ``TensorBank`` whose members are
declared tensors, so a bank can be an operand instead of an attribute.
Both-model impact: Qwen3-8B has no expert bank and is unaffected today, but any
banked weight -- mixture-of-experts, stacked adapters, or a tensor-parallel
shard set -- hits the same wall.

Arity notes
-----------
``KERNEL_TO_ENGINE`` records a nominal operand arity per kind.  Where the
released semantics differ, this export follows the semantics and stays inside
the ABI 3.0 descriptor limits (at most four input views and two output views,
``runtime/abi3/builder.py``): ``HEAD_RMS_NORM`` takes one input because the
released query head norm is unweighted; ``STATE_READ`` takes one input and
produces one output because a valid-prefix view must yield a tensor;
``EXPERT_DISPATCH`` produces two outputs, the permuted rows and the per-row
expert identity; ``HYPER_CONNECT_PRE`` packs the Sinkhorn post and combination
coefficients into one output because only two output views exist; and
``COMPRESSED_DENSE_INDEX`` reuses ``WINDOW_INDEX`` parameterised by
``index_family``, since both enumerate causal indices from a position.
"""

from __future__ import annotations

import hashlib
import json
import struct
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from compiler.frontend.checkpoint import (
    CheckpointError,
    load_checkpoint_lock,
)
from compiler.frontend.deepseek_v4 import (
    DEFAULT_CONFIG,
    DEFAULT_SOURCE,
    MODEL_ID,
    OFFICIAL_CHECKPOINT_LOCK_ID,
    PAYLOAD_BYTES,
    REPOSITORY,
    REVISION,
    TENSOR_COUNT,
    TENSOR_STRUCTURE_SHA256,
    TensorSpec,
    build_official_tensor_specs,
    load_official_config,
    validate_official_checkpoint_lock,
)
from compiler.frontend.deepseek_v4_graph import (
    MODEL_SOURCE_SHA256,
    KERNEL_SOURCE_SHA256,
    INFERENCE_CONFIG_SHA256,
    OPERATOR_CATALOG,
    build_official_graph_contract,
)
from compiler.ir.v3.kernel_ir import (
    CheckpointBinding,
    Entrypoint,
    Kernel,
    KernelGraph,
    RuntimeSymbol,
    StateResource,
    Symbolic,
    Tensor,
    check_neutral,
)
from compiler.ir.v3.lowering import KERNEL_TO_ENGINE

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/"
    "models--deepseek-ai--DeepSeek-V4-Flash-0731/snapshots/"
    "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
)
DEFAULT_CHECKPOINT_LOCK = Path(
    "/home/ubuntu/.cache/opentallas/deepseek-v4-flash-0731/checkpoint.lock.json"
)

#: Architectural capacity published for this model.  It is not the deployment
#: capacity: ADR-003 section 18 fixes a 200,000-token DeepSeek acceptance run,
#: and the first release targets the next power of two above it.
ARCHITECTURAL_MAX_CONTEXT = 1_048_576

#: Deployment maximum this export targets.  Every ``Symbolic`` maximum and every
#: state capacity below is derived from it.
DEFAULT_CONTEXT_TOKENS = 262_144

NUMERIC_PROFILE = "deepseek_v4_flash_target_precision_v1"
GENERATION_POLICY_ID = "deepseek_v4_flash_greedy_argmax_v1"

EOS_TOKEN_ID = 1
BOS_TOKEN_ID = 0

#: Architectural widths taken from the released configuration and re-checked
#: against it in :func:`export_deepseek_v4_kernel_graph`.
HIDDEN = 4096
HC_MULT = 4
HEADS = 64
HEAD_DIM = 512
ROPE_DIM = 64
NOPE_DIM = HEAD_DIM - ROPE_DIM
Q_RANK = 1024
O_GROUPS = 8
O_RANK = 1024
INDEX_HEADS = 64
INDEX_HEAD_DIM = 128
INDEX_TOPK = 512
VOCABULARY = 129_280
ROUTED_EXPERTS = 256
TOP_K = 6
MOE_INTERMEDIATE = 2048
SLIDING_WINDOW = 128
SWIGLU_LIMIT = 10.0
ROUTE_SCALE = 1.5
DRAFT_BLOCK = 5
MARKOV_RANK = 256
RMS_EPSILON = 1e-6
#: ``(2 + hc_mult) * hc_mult`` mixing rows; the Sinkhorn split yields
#: ``hc_mult`` pre, ``hc_mult`` post and ``hc_mult * hc_mult`` combination
#: coefficients.
HC_MIX = (2 + HC_MULT) * HC_MULT
HC_COEFFICIENTS = HC_MULT + HC_MULT * HC_MULT

#: Dynamic activation quantization block used by ``inference/kernel.py``.
ACTIVATION_BLOCK = 128
#: Block used by the in-place attention KV quantize/dequantize round trip.
KV_QUANT_BLOCK = 64
#: Block used by the MXFP4 expert weights and the indexer FP4 round trip.
FP4_BLOCK = 32
#: Block used by the released 128x128 FP8 weight scales.
FP8_WEIGHT_BLOCK = 128


class DeepSeekV4KernelIRError(RuntimeError):
    """Raised when the pinned DeepSeek source cannot produce a neutral graph."""


# ---------------------------------------------------------------------------
# Source-kind to neutral-kind plan
# ---------------------------------------------------------------------------
#: Every source operator kind and the ordered neutral kinds it lowers to.  A
#: source kind with more than one entry needs several neutral kernels; none
#: invents an opcode.  ``QUANTIZE`` steps marked ``shared`` are emitted once per
#: distinct activation value, so a node that reuses an already quantized
#: activation contributes fewer kernels than this plan lists.
LOWERING_PLAN: Mapping[str, tuple[str, ...]] = {
    "ATTENTION_KV_VIEW": ("CONCAT",),
    "BF16_LINEAR": ("MATMUL",),
    "BINARY32_TO_BF16": ("CONVERT",),
    "BIASED_TOPK_ROUTE": ("BIASED_TOPK",),
    "COMPRESSED_DENSE_INDEX": ("WINDOW_INDEX", "CONCAT"),
    "COMPRESSED_KV_VALID_VIEW": ("STATE_READ",),
    "COMPRESS_KV_WRITE": ("KV_APPEND",),
    "COMPRESS_POOL": ("COMPRESS_POOL",),
    "COMPRESS_PROJECT": ("COMPRESS_PROJECT", "COMPRESS_PROJECT"),
    "COMPRESS_STATE_UPDATE": ("ADD", "COMPRESS_STATE_UPDATE"),
    "CONFIDENCE_SCORE": ("CONCAT", "MATMUL"),
    "DSPARK_MAIN_PROJECT": ("CONCAT", "QUANTIZE", "MATMUL", "RMS_NORM"),
    "DSPARK_NOISE_EMBED": ("SCATTER", "EMBEDDING_LOOKUP", "CONCAT"),
    "DSPARK_PREFILL_KV": (
        "QUANTIZE",
        "MATMUL",
        "RMS_NORM",
        "ROPE",
        "QUANTIZE",
        "DEQUANTIZE",
        "KV_APPEND",
    ),
    "DSPARK_WINDOW_INDEX": ("WINDOW_INDEX",),
    "EXPERT_DISPATCH": ("EXPERT_DISPATCH",),
    "EXPERT_REDUCE": ("EXPERT_REDUCE",),
    "FP4_QDQ": ("QUANTIZE", "DEQUANTIZE"),
    "FP8_LINEAR": ("QUANTIZE", "MATMUL"),
    "FP8_QDQ": ("QUANTIZE", "DEQUANTIZE"),
    "FP8_SWIGLU": (
        "QUANTIZE",
        "MATMUL",
        "MATMUL",
        "SWIGLU",
        "QUANTIZE",
        "MATMUL",
    ),
    "GROUPED_OUTPUT_PROJECT": ("GROUPED_MATMUL",),
    "HADAMARD_ROTATE": ("HADAMARD",),
    "HASH_ROUTE": ("HASH_ROUTE",),
    "HC_EXPAND": ("CONCAT",),
    "HC_HEAD": ("HYPER_CONNECT_HEAD",),
    "HC_POST": ("HYPER_CONNECT_POST",),
    "HC_PRE": ("HYPER_CONNECT_PRE",),
    "HEAD_RMS_NORM": ("HEAD_RMS_NORM",),
    "INDEX_SCORE": ("INDEX_SCORE",),
    "INDEX_TOPK": ("INDEX_TOPK", "CONCAT"),
    "KV_WINDOW_WRITE": ("KV_APPEND",),
    "LM_HEAD": ("LAST_TOKEN_SELECT", "VOCAB_PROJECT"),
    "MARKOV_AUTOREGRESSIVE_LOOP": (
        "EMBEDDING_LOOKUP",
        "VOCAB_PROJECT",
        "ADD",
        "ARGMAX",
        "TOKEN_APPEND",
    )
    * DRAFT_BLOCK
    + ("CONCAT", "CONCAT", "CONCAT", "CONCAT"),
    "MXFP4_SWIGLU": (
        "QUANTIZE",
        "ROUTED_MATMUL",
        "ROUTED_MATMUL",
        "SWIGLU",
        "MUL",
        "QUANTIZE",
        "ROUTED_MATMUL",
    ),
    "RMS_NORM": ("RMS_NORM",),
    "ROPE_APPLY": ("ROPE",),
    "ROPE_INVERSE": ("ROPE_INVERSE",),
    "ROUTER_SCORE": ("ROUTER_SCORE",),
    "ROUTER_WEIGHT_NORMALIZE": ("GATHER", "WEIGHT_NORMALIZE", "SCALE"),
    "SAMPLE": ("SCALE", "ARGMAX", "TOKEN_APPEND"),
    "SPARSE_ATTENTION": ("ATTENTION_SPARSE",),
    "SQRT_SOFTPLUS": ("SQRT_SOFTPLUS",),
    "TARGET_HIDDEN_CAPTURE": ("PARTITION_SUM", "SCALE"),
    "TOKEN_EMBED": ("EMBEDDING_LOOKUP",),
    "WINDOW_INDEX": ("WINDOW_INDEX",),
}

#: Sub-operation name per emitted kernel, qualifying the reference owner that
#: pins its target-precision identity.  ``""`` means the neutral kernel is the
#: whole reference.
_CONTRACT_STEP_SEPARATOR = "#"

#: Counter namespace per neutral kind, named with the ABI 3.0 counter groups in
#: ``runtime.abi3.constants.CounterGroup`` rather than an engine instance.
COUNTER_CLASS_BY_KIND: Mapping[str, str] = {
    "ADD": "vector_reduction",
    "ARGMAX": "selection_eos",
    "ATTENTION_SPARSE": "attention",
    "BIASED_TOPK": "route_expert",
    "CONCAT": "vector_reduction",
    "SCATTER": "memory",
    "CONVERT": "vector_reduction",
    "COMPRESS_POOL": "attention",
    "COMPRESS_PROJECT": "tensor",
    "COMPRESS_STATE_UPDATE": "state",
    "DEQUANTIZE": "vector_reduction",
    "EMBEDDING_LOOKUP": "tensor",
    "EXPERT_DISPATCH": "route_expert",
    "EXPERT_REDUCE": "route_expert",
    "GATHER": "memory",
    "GROUPED_MATMUL": "tensor",
    "HADAMARD": "vector_reduction",
    "HASH_ROUTE": "route_expert",
    "HEAD_RMS_NORM": "vector_reduction",
    "HYPER_CONNECT_HEAD": "vector_reduction",
    "HYPER_CONNECT_POST": "vector_reduction",
    "HYPER_CONNECT_PRE": "vector_reduction",
    "INDEX_SCORE": "attention",
    "INDEX_TOPK": "route_expert",
    "KV_APPEND": "state",
    "LAST_TOKEN_SELECT": "memory",
    "MATMUL": "tensor",
    "MUL": "vector_reduction",
    "PARTITION_SUM": "vector_reduction",
    "QUANTIZE": "vector_reduction",
    "RMS_NORM": "vector_reduction",
    "ROPE": "vector_reduction",
    "ROPE_INVERSE": "vector_reduction",
    "ROUTED_MATMUL": "tensor",
    "ROUTER_SCORE": "route_expert",
    "SCALE": "vector_reduction",
    "STATE_READ": "state",
    "SQRT_SOFTPLUS": "vector_reduction",
    "SWIGLU": "vector_reduction",
    "TOKEN_APPEND": "selection_eos",
    "VOCAB_PROJECT": "tensor",
    "WEIGHT_NORMALIZE": "route_expert",
    "WINDOW_INDEX": "route_expert",
}

#: Attribute keys of the source graph that carry a term ``check_neutral``
#: forbids.  Each is renamed, never dropped, so no source semantics are lost.
_NEUTRAL_ATTRIBUTE_KEY: Mapping[str, str] = {
    "cache_slot": "cache_row",
    "duplicate_slot_order": "duplicate_selection_order",
    "duplicate_slot_policy": "duplicate_selection_policy",
    "kv_read_bytes_per_valid_slot": "kv_read_bytes_per_valid_row",
    "stages": "butterfly_levels",
    "state_slots": "state_rows",
}

_STORAGE_DTYPE: Mapping[str, str] = {
    "BF16": "bf16",
    "F32": "fp32",
    "F8_E4M3": "fp8_e4m3fn",
    "F8_E8M0": "e8m0",
    "I8": "i8",
    "I64": "i64",
}


# ---------------------------------------------------------------------------
# Checkpoint bindings
# ---------------------------------------------------------------------------
def read_checkpoint_bindings(
    snapshot: Path, lock: Mapping[str, Any]
) -> dict[str, CheckpointBinding]:
    """Derive every weight's exact byte range from the real safetensors headers.

    A safetensors tensor payload starts at ``8 + header_length +
    data_offsets[0]``: eight bytes of little-endian header length, the JSON
    header itself, then the contiguous data segment.  Every header is re-read
    here and required to match the hash-locked header and tensor records, so a
    binding cannot drift from the locked 156 GB checkpoint.
    """

    bindings: dict[str, CheckpointBinding] = {}
    for shard in lock["shards"]:
        relative = shard["path"]
        path = Path(snapshot) / relative
        try:
            with path.open("rb") as handle:
                prefix = handle.read(8)
                if len(prefix) != 8:
                    raise DeepSeekV4KernelIRError(
                        f"shard {relative!r} has no header length prefix"
                    )
                header_length = struct.unpack("<Q", prefix)[0]
                if header_length != shard["header_length_bytes"]:
                    raise DeepSeekV4KernelIRError(
                        f"shard {relative!r} header length differs from the lock"
                    )
                raw_header = handle.read(header_length)
        except OSError as exc:
            raise DeepSeekV4KernelIRError(
                f"cannot read shard {relative!r}: {exc}"
            ) from exc
        if len(raw_header) != header_length:
            raise DeepSeekV4KernelIRError(f"shard {relative!r} header is truncated")
        if hashlib.sha256(raw_header).hexdigest() != shard["header_sha256"]:
            raise DeepSeekV4KernelIRError(
                f"shard {relative!r} header differs from the checkpoint lock"
            )
        try:
            header = json.loads(raw_header.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DeepSeekV4KernelIRError(
                f"shard {relative!r} header is not valid JSON: {exc}"
            ) from exc
        payload_start = 8 + header_length
        entries = {
            name: value for name, value in header.items() if name != "__metadata__"
        }
        locked = {record["name"]: record for record in shard["tensors"]}
        if set(entries) != set(locked):
            raise DeepSeekV4KernelIRError(
                f"shard {relative!r} header tensors differ from the checkpoint lock"
            )
        for name in sorted(entries):
            entry = entries[name]
            record = locked[name]
            start, end = entry["data_offsets"]
            if (
                [start, end] != list(record["data_offsets"])
                or entry["dtype"] != record["dtype"]
                or list(entry["shape"]) != list(record["shape"])
                or end - start != record["size_bytes"]
            ):
                raise DeepSeekV4KernelIRError(
                    f"tensor {name!r} in {relative!r} differs from the checkpoint lock"
                )
            if name in bindings:
                raise DeepSeekV4KernelIRError(f"tensor {name!r} appears in two shards")
            bindings[name] = CheckpointBinding(
                source_name=name,
                path=relative,
                offset=payload_start + start,
                bytes=record["size_bytes"],
                sha256=record["payload_sha256"],
                transform="identity",
            )
    return bindings


def verify_checkpoint_bindings(
    snapshot: Path,
    graph: KernelGraph,
    *,
    sample: int = 8,
) -> list[dict[str, Any]]:
    """Re-read ``sample`` bound byte ranges and confirm the recorded SHA-256.

    The sample is deterministic: it is spread evenly across the bound tensors
    in declaration order, so the same graph always verifies the same ranges.
    """

    bound = [t for t in graph.tensors if t.binding is not None]
    if not bound:
        raise DeepSeekV4KernelIRError("graph declares no bound weight tensor")
    count = max(1, min(sample, len(bound)))
    step = max(1, len(bound) // count)
    records: list[dict[str, Any]] = []
    for tensor in bound[:: step][:count]:
        binding = tensor.binding
        assert binding is not None
        path = Path(snapshot) / binding.path
        digest = hashlib.sha256()
        remaining = binding.bytes
        with path.open("rb") as handle:
            handle.seek(binding.offset)
            while remaining:
                chunk = handle.read(min(remaining, 1 << 24))
                if not chunk:
                    raise DeepSeekV4KernelIRError(
                        f"short read for {binding.source_name!r}"
                    )
                digest.update(chunk)
                remaining -= len(chunk)
        observed = digest.hexdigest()
        if observed != binding.sha256:
            raise DeepSeekV4KernelIRError(
                f"{binding.source_name!r} payload differs from its recorded SHA-256"
            )
        records.append(
            {
                "bytes": binding.bytes,
                "offset": binding.offset,
                "path": binding.path,
                "sha256": observed,
                "tensor_id": tensor.tensor_id,
            }
        )
    return records


def _neutral_attributes(attributes: Mapping[str, Any]) -> dict[str, Any]:
    """Rename the source attribute keys that carry a forbidden backend term."""

    out: dict[str, Any] = {}
    for key, value in attributes.items():
        out[_NEUTRAL_ATTRIBUTE_KEY.get(key, key)] = value
    return out


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------
class _Builder:
    """Accumulate tensors, states and kernels in emission order."""

    def __init__(self) -> None:
        self.tensors: list[Tensor] = []
        self.kernels: list[Kernel] = []
        self.states: list[StateResource] = []
        self._tensor_ids: set[str] = set()
        self._state_ids: set[str] = set()
        self.shape: dict[str, tuple[Any, ...]] = {}
        self.dtype: dict[str, str] = {}
        self.kernels_by_source_kind: Counter = Counter()
        self.kernels_by_kind: Counter = Counter()

    def tensor(
        self,
        tensor_id: str,
        dtype: str,
        shape: tuple[Any, ...],
        role: str,
        *,
        binding: CheckpointBinding | None = None,
        scale_tensor_id: str | None = None,
        scale_block_elements: int = 0,
    ) -> str:
        if tensor_id in self._tensor_ids:
            raise DeepSeekV4KernelIRError(f"duplicate tensor {tensor_id!r}")
        self._tensor_ids.add(tensor_id)
        self.tensors.append(
            Tensor(
                tensor_id=tensor_id,
                dtype=dtype,
                shape=tuple(shape),
                role=role,
                binding=binding,
                scale_tensor_id=scale_tensor_id,
                scale_block_elements=scale_block_elements,
            )
        )
        self.shape[tensor_id] = tuple(shape)
        self.dtype[tensor_id] = dtype
        return tensor_id

    def has_tensor(self, tensor_id: str) -> bool:
        return tensor_id in self._tensor_ids

    def has_state(self, state_id: str) -> bool:
        return state_id in self._state_ids

    def state(self, resource: StateResource) -> str:
        if resource.state_id in self._state_ids:
            return resource.state_id
        self._state_ids.add(resource.state_id)
        self.states.append(resource)
        return resource.state_id

    def kernel(
        self,
        kernel_id: str,
        kind: str,
        inputs: Sequence[str],
        outputs: Sequence[str],
        *,
        numeric_contract: str,
        iteration_domain: Mapping[str, Any],
        attributes: Mapping[str, Any],
        source_operation_id: str,
        source_kind: str,
        phases: Sequence[str] = ("prefill", "decode"),
        layer: int | None = None,
        state_reads: Sequence[str] = (),
        state_writes: Sequence[str] = (),
    ) -> None:
        if kind not in KERNEL_TO_ENGINE:
            raise DeepSeekV4KernelIRError(
                f"kernel kind {kind!r} has no ABI 3.0 lowering; the shared table "
                "in compiler/ir/v3/lowering.py is the only place to add one"
            )
        if len(inputs) > 4:
            raise DeepSeekV4KernelIRError(
                f"{kernel_id!r} declares {len(inputs)} inputs; an ABI 3.0 operator "
                "admits at most four input views"
            )
        if len(outputs) > 2:
            raise DeepSeekV4KernelIRError(
                f"{kernel_id!r} declares {len(outputs)} outputs; an ABI 3.0 "
                "operator admits at most two output views"
            )
        self.kernels.append(
            Kernel(
                index=len(self.kernels),
                kernel_id=kernel_id,
                kind=kind,
                inputs=tuple(inputs),
                outputs=tuple(outputs),
                numeric_contract=numeric_contract,
                iteration_domain=dict(iteration_domain),
                attributes=_neutral_attributes(attributes),
                phases=tuple(phases),
                state_reads=tuple(state_reads),
                state_writes=tuple(state_writes),
                counter_class=COUNTER_CLASS_BY_KIND[kind],
                source_operation_id=source_operation_id,
                layer=layer,
            )
        )
        self.kernels_by_kind[kind] += 1
        self.kernels_by_source_kind[source_kind] += 1


def _split_node_id(node_id: str) -> tuple[str, int | None, str]:
    """Return ``(scope, layer, leaf)`` for a source graph node identifier."""

    head, _, rest = node_id.partition(".")
    if rest.startswith("layer") and rest[5:7].isdigit():
        return head, int(rest[5:7]), rest[8:]
    return head, None, rest


def _reference_owner(source_kind: str) -> str:
    return OPERATOR_CATALOG[source_kind].to_dict()["reference_owner"]


def _contract(source_kind: str, step: str = "") -> str:
    owner = _reference_owner(source_kind)
    return f"{owner}{_CONTRACT_STEP_SEPARATOR}{step}" if step else owner


_SOURCE_STATE_SUFFIX_TO_NEUTRAL: Mapping[str, tuple[str, ...]] = {
    "window_kv": ("attention_window",),
    "compressor": ("compressor_window_kv", "compressor_window_score"),
    "compressed_kv": ("compressed_key_value",),
    "index_compressor": (
        "index_compressor_window_kv",
        "index_compressor_window_score",
    ),
    "index_compressed_kv": ("index_compressed_key_value",),
}


def _neutral_state_ids(source_names: Iterable[str]) -> tuple[str, ...]:
    """Translate ``state.<scope>.layer<n>.<suffix>`` into neutral state IDs."""

    out: list[str] = []
    for name in source_names:
        parts = name.split(".")
        if len(parts) != 4 or parts[0] != "state" or not parts[2].startswith("layer"):
            raise DeepSeekV4KernelIRError(f"unrecognised source state {name!r}")
        scope = parts[1]
        layer = int(parts[2][len("layer") :])
        try:
            families = _SOURCE_STATE_SUFFIX_TO_NEUTRAL[parts[3]]
        except KeyError:
            raise DeepSeekV4KernelIRError(
                f"source state {name!r} has no neutral state class"
            ) from None
        out.extend(f"{family}.{scope}.layer.{layer}" for family in families)
    return tuple(out)


def export_deepseek_v4_kernel_graph(
    *,
    snapshot: Path = DEFAULT_SNAPSHOT,
    checkpoint_lock_path: Path = DEFAULT_CHECKPOINT_LOCK,
    config_path: Path = DEFAULT_CONFIG,
    source_path: Path = DEFAULT_SOURCE,
    context_tokens: int = DEFAULT_CONTEXT_TOKENS,
    maximum_new_tokens: int | None = None,
    include_speculative: bool = False,
) -> KernelGraph:
    """Export DeepSeek-V4-Flash-0731 as one neutral Tensor Kernel IR v3 graph.

    ``include_speculative`` selects the profile.  ``False`` -- the first
    release -- emits the ordinary target-model path: the 43 main layers, the
    hyper-connection head, the final norm, the vocabulary head and greedy
    selection.  ``True`` additionally emits the three DSpark draft blocks, the
    DSpark conditioning projection, the Markov draft head and the confidence
    head, which ADR-003 section 18 sequences after ordinary generation and
    whose acceptance contract is still open (DSV4-SEM-001).
    """

    snapshot = Path(snapshot)
    if context_tokens < 1 or context_tokens > ARCHITECTURAL_MAX_CONTEXT:
        raise DeepSeekV4KernelIRError(
            f"deployment context {context_tokens} is outside the architectural "
            f"capacity 1..{ARCHITECTURAL_MAX_CONTEXT}"
        )
    if context_tokens % SLIDING_WINDOW:
        raise DeepSeekV4KernelIRError(
            "deployment context must be a whole number of sliding windows"
        )
    if maximum_new_tokens is None:
        maximum_new_tokens = context_tokens
    if not 1 <= maximum_new_tokens <= context_tokens:
        raise DeepSeekV4KernelIRError(
            "maximum_new_tokens is outside the deployment context"
        )

    config = load_official_config(Path(config_path))
    specs = build_official_tensor_specs(config)
    for key, expected in (
        ("hidden_size", HIDDEN),
        ("hc_mult", HC_MULT),
        ("num_attention_heads", HEADS),
        ("head_dim", HEAD_DIM),
        ("qk_rope_head_dim", ROPE_DIM),
        ("q_lora_rank", Q_RANK),
        ("o_groups", O_GROUPS),
        ("o_lora_rank", O_RANK),
        ("index_head_dim", INDEX_HEAD_DIM),
        ("index_n_heads", INDEX_HEADS),
        ("index_topk", INDEX_TOPK),
        ("vocab_size", VOCABULARY),
        ("n_routed_experts", ROUTED_EXPERTS),
        ("num_experts_per_tok", TOP_K),
        ("moe_intermediate_size", MOE_INTERMEDIATE),
        ("sliding_window", SLIDING_WINDOW),
        ("num_hidden_layers", 43),
    ):
        if int(config[key]) != expected:
            raise DeepSeekV4KernelIRError(
                f"released config {key}={config[key]} differs from the pinned {expected}"
            )

    try:
        lock = load_checkpoint_lock(Path(checkpoint_lock_path))
    except CheckpointError as exc:
        raise DeepSeekV4KernelIRError(
            f"invalid DeepSeek V4 checkpoint lock: {exc}"
        ) from exc
    validate_official_checkpoint_lock(lock, config)
    if (
        lock["lock_id"] != OFFICIAL_CHECKPOINT_LOCK_ID
        or lock["checkpoint"]["tensor_count"] != TENSOR_COUNT
        or lock["checkpoint"]["payload_bytes"] != PAYLOAD_BYTES
    ):
        raise DeepSeekV4KernelIRError(
            "checkpoint lock is not the pinned DeepSeek-V4-Flash-0731 release"
        )
    bindings = read_checkpoint_bindings(snapshot, lock)
    if len(bindings) != TENSOR_COUNT:
        raise DeepSeekV4KernelIRError(
            f"checkpoint headers describe {len(bindings)} tensors, expected {TENSOR_COUNT}"
        )

    contract = build_official_graph_contract()
    nodes = contract["nodes"]

    ratios = [int(r) for r in config["compress_ratios"][:43]]

    # ------------------------------------------------------------------
    # Tensor specification index
    # ------------------------------------------------------------------
    spec_index: dict[tuple[str, int | None, str], list[TensorSpec]] = defaultdict(list)
    for spec in specs:
        spec_index[(spec.scope, spec.layer, spec.semantic_role)].append(spec)
    for group in spec_index.values():
        group.sort(key=lambda s: (-1 if s.expert is None else s.expert, s.name))
    scale_of: dict[str, TensorSpec] = {
        spec.scale_for: spec for spec in specs if spec.scale_for is not None
    }

    builder = _Builder()

    # ------------------------------------------------------------------
    # Runtime symbols and extents
    # ------------------------------------------------------------------
    span = Symbolic("span_tokens", 1, context_tokens)
    dispatch_rows = Symbolic("span_tokens", TOP_K, TOP_K * context_tokens)
    groups = {
        4: Symbolic("span_groups_ratio4", 1, context_tokens // 4),
        128: Symbolic("span_groups_ratio128", 1, context_tokens // 128),
    }
    committed_groups = {
        4: Symbolic("context_groups_ratio4", 1, context_tokens // 4),
        128: Symbolic("context_groups_ratio128", 1, context_tokens // 128),
    }
    attention_rows = {
        0: Symbolic("attention_rows_window", 1, context_tokens + SLIDING_WINDOW),
        4: Symbolic(
            "attention_rows_ratio4",
            1,
            context_tokens + SLIDING_WINDOW + context_tokens // 4,
        ),
        128: Symbolic(
            "attention_rows_ratio128",
            1,
            context_tokens + SLIDING_WINDOW + context_tokens // 128,
        ),
    }
    selected_rows_128 = Symbolic(
        "selected_rows_ratio128", 1, SLIDING_WINDOW + context_tokens // 128
    )
    symbols = (
        RuntimeSymbol("span_tokens", 1, context_tokens, 1, "request"),
        RuntimeSymbol("context_length", 1, context_tokens, 1, "request"),
        RuntimeSymbol("span_groups_ratio4", 0, context_tokens // 4, 1, "derived"),
        RuntimeSymbol("span_groups_ratio128", 0, context_tokens // 128, 1, "derived"),
        RuntimeSymbol("context_groups_ratio4", 0, context_tokens // 4, 1, "derived"),
        RuntimeSymbol(
            "context_groups_ratio128", 0, context_tokens // 128, 1, "derived"
        ),
        RuntimeSymbol(
            "attention_rows_window", 1, context_tokens + SLIDING_WINDOW, 1, "derived"
        ),
        RuntimeSymbol(
            "attention_rows_ratio4",
            1,
            context_tokens + SLIDING_WINDOW + context_tokens // 4,
            1,
            "derived",
        ),
        RuntimeSymbol(
            "attention_rows_ratio128",
            1,
            context_tokens + SLIDING_WINDOW + context_tokens // 128,
            1,
            "derived",
        ),
        RuntimeSymbol(
            "selected_rows_ratio128",
            1,
            SLIDING_WINDOW + context_tokens // 128,
            1,
            "derived",
        ),
    )

    # ------------------------------------------------------------------
    # Request inputs
    # ------------------------------------------------------------------
    token_ids = builder.tensor("input.token_ids", "i32", (span,), "input")
    position_offset = builder.tensor("input.position_offset", "i32", (1,), "input")
    session_ids = builder.tensor("input.session_ids", "u32", (1,), "input")
    temperature = builder.tensor("input.temperature", "fp32", (1,), "input")
    entropy = builder.tensor("input.entropy_stream", "fp32", (1, VOCABULARY), "input")

    value_tensor: dict[str, str] = {
        "request.input_ids": token_ids,
        "request.start_pos": position_offset,
        "request.session_ids": session_ids,
        "request.temperature_binary32": temperature,
        "request.explicit_exponential_entropy": entropy,
    }
    predicate_values: set[str] = set()
    context_of: dict[str, dict[str, str]] = defaultdict(dict)

    role_any: dict[str, list[TensorSpec]] = defaultdict(list)
    for spec in specs:
        role_any[spec.semantic_role].append(spec)
    for group in role_any.values():
        group.sort(key=lambda s: (-1 if s.expert is None else s.expert, s.name))

    def declare_weight(spec: TensorSpec) -> str:
        if builder.has_tensor(spec.name):
            return spec.name
        binding = bindings.get(spec.name)
        if binding is None:
            raise DeepSeekV4KernelIRError(
                f"checkpoint has no payload for {spec.name!r}"
            )
        if binding.bytes != spec.size_bytes:
            raise DeepSeekV4KernelIRError(
                f"{spec.name!r} byte length differs from the derived contract"
            )
        dtype = _STORAGE_DTYPE[spec.storage_dtype]
        shape: tuple[int, ...] = tuple(spec.shape)
        if spec.logical_dtype == "MXFP4_E2M1_X2":
            # Two E2M1 elements share one stored byte; the neutral shape is the
            # architectural one and the binding still names the stored bytes.
            dtype = "mxfp4_e2m1"
            shape = (spec.shape[0], spec.shape[1] * 2)
        scale_spec = scale_of.get(spec.name)
        scale_id: str | None = None
        block = 0
        if scale_spec is not None:
            scale_id = declare_weight(scale_spec)
            block = FP4_BLOCK if dtype == "mxfp4_e2m1" else FP8_WEIGHT_BLOCK
        return builder.tensor(
            spec.name,
            dtype,
            shape,
            "weight",
            binding=binding,
            scale_tensor_id=scale_id,
            scale_block_elements=block,
        )

    def role_specs(role: str, scope: str, layer: int | None) -> list[TensorSpec]:
        for key in ((scope, layer, role), ("global", None, role)):
            if key in spec_index:
                return spec_index[key]
        if role in role_any:
            return role_any[role]
        raise DeepSeekV4KernelIRError(
            f"role {role!r} has no tensor in scope {scope!r} layer {layer!r}"
        )

    def role_weight(role: str, scope: str, layer: int | None) -> str:
        found = role_specs(role, scope, layer)
        if len(found) != 1:
            raise DeepSeekV4KernelIRError(
                f"role {role!r} resolves to {len(found)} tensors, expected one"
            )
        return declare_weight(found[0])

    def role_weight_family(role: str, scope: str, layer: int | None) -> list[str]:
        return [declare_weight(spec) for spec in role_specs(role, scope, layer)]

    def ten(value: str) -> str:
        try:
            return value_tensor[value]
        except KeyError:
            raise DeepSeekV4KernelIRError(
                f"source value {value!r} has no neutral tensor"
            ) from None

    def bind(value: str, tensor_id: str) -> str:
        value_tensor[value] = tensor_id
        return tensor_id

    def act(tensor_id: str, dtype: str, shape: tuple[Any, ...]) -> str:
        return builder.tensor(tensor_id, dtype, shape, "activation")

    def view(tensor_id: str, dtype: str, shape: tuple[Any, ...]) -> str:
        return builder.tensor(tensor_id, dtype, shape, "state")

    def rows_of(tensor_id: str) -> Any:
        return builder.shape[tensor_id][0]

    quantized: dict[tuple[str, int, str, int], tuple[str, str]] = {}

    def quantize(
        source: str,
        *,
        block: int,
        dtype: str,
        width: int | None,
        source_operation_id: str,
        source_kind: str,
        contract: str,
        attributes: Mapping[str, Any],
        layer: int | None,
        phases: Sequence[str],
    ) -> tuple[str, str]:
        """Emit (or reuse) the dynamic quantization of one activation value."""

        shape = builder.shape[source]
        full_width = shape[-1]
        if width is None:
            width = int(full_width)
        key = (source, block, dtype, width)
        if key in quantized:
            return quantized[key]
        suffix = f"quantized_{dtype}_{block}"
        if width != full_width:
            suffix = f"{suffix}_{width}"
        if width % block:
            raise DeepSeekV4KernelIRError(
                f"{source!r} width {width} is not a whole number of {block}-blocks"
            )
        scale = act(
            f"{source}.{suffix}.scale", "e8m0", (*shape[:-1], width // block)
        )
        payload = builder.tensor(
            f"{source}.{suffix}",
            dtype,
            (*shape[:-1], width),
            "activation",
            scale_tensor_id=scale,
            scale_block_elements=block,
        )
        builder.kernel(
            f"{source}.{suffix}",
            "QUANTIZE",
            (source,),
            (payload, scale),
            numeric_contract=contract,
            iteration_domain={"rows": shape[0], "width": width, "block": block},
            attributes=dict(attributes),
            source_operation_id=source_operation_id,
            source_kind=source_kind,
            phases=phases,
            layer=layer,
        )
        quantized[key] = (payload, scale)
        return payload, scale

    def rope_attributes(ratio: int, *, inverse: bool) -> dict[str, Any]:
        if ratio:
            return {
                "beta_fast": int(config["rope_scaling"]["beta_fast"]),
                "beta_slow": int(config["rope_scaling"]["beta_slow"]),
                "factor": float(config["rope_scaling"]["factor"]),
                "inverse": inverse,
                "original_max_position": int(
                    config["rope_scaling"]["original_max_position_embeddings"]
                ),
                "position_scaling": "yarn",
                "rotary_width": ROPE_DIM,
                "theta": float(config["compress_rope_theta"]),
            }
        return {
            "inverse": inverse,
            "position_scaling": "none",
            "rotary_width": ROPE_DIM,
            "theta": float(config["rope_theta"]),
        }

    def ensure_state(state_id: str) -> str:
        if builder.has_state(state_id):
            return state_id
        family, state_scope, _, layer_text = state_id.split(".")
        state_layer = int(layer_text)
        state_ratio = ratios[state_layer] if state_scope == "main" else 0
        coefficient = 2 if state_ratio == 4 else 1
        if family == "attention_window":
            resource = StateResource(
                state_id=state_id,
                state_class="kv_window",
                dtype="bf16",
                row_elements=HEAD_DIM,
                capacity_rows=SLIDING_WINDOW,
                initialization="zero",
            )
        elif family in {"compressor_window_kv", "compressor_window_score"}:
            resource = StateResource(
                state_id=state_id,
                state_class="compressor_window",
                dtype="fp32",
                row_elements=coefficient * HEAD_DIM,
                capacity_rows=coefficient * state_ratio,
                initialization=(
                    "zero"
                    if family.endswith("kv")
                    else "negative_infinity"
                ),
            )
        elif family == "compressed_key_value":
            resource = StateResource(
                state_id=state_id,
                state_class="compressed_kv",
                dtype="bf16",
                row_elements=HEAD_DIM,
                capacity_rows=context_tokens // state_ratio,
                initialization="zero",
            )
        elif family in {
            "index_compressor_window_kv",
            "index_compressor_window_score",
        }:
            resource = StateResource(
                state_id=state_id,
                state_class="compressor_window",
                dtype="fp32",
                row_elements=2 * INDEX_HEAD_DIM,
                capacity_rows=2 * 4,
                initialization=(
                    "zero" if family.endswith("kv") else "negative_infinity"
                ),
            )
        elif family == "index_compressed_key_value":
            resource = StateResource(
                state_id=state_id,
                state_class="compressed_kv",
                dtype="bf16",
                row_elements=INDEX_HEAD_DIM,
                capacity_rows=context_tokens // 4,
                initialization="zero",
            )
        else:  # pragma: no cover - the translation table is closed
            raise DeepSeekV4KernelIRError(f"unknown state family {family!r}")
        return builder.state(resource)

    def states_of(node: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
        reads = _neutral_state_ids(node["state_reads"])
        writes = _neutral_state_ids(node["state_writes"])
        for state_id in (*reads, *writes):
            ensure_state(state_id)
        return reads, writes

    def dedupe(items: Iterable[str]) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for item in items:
            seen.setdefault(item, None)
        return tuple(seen)

    # ------------------------------------------------------------------
    # Lower every source node
    # ------------------------------------------------------------------
    emitted_source_kinds: Counter = Counter()
    for node in nodes:
        node_id = node["id"]
        source_kind = node["kind"]
        speculative = node_id.startswith("dspark.") or source_kind == (
            "TARGET_HIDDEN_CAPTURE"
        )
        if speculative and not include_speculative:
            continue
        emitted_source_kinds[source_kind] += 1
        scope, layer, leaf = _split_node_id(node_id)
        root = f"{scope}.layer{layer:02d}" if layer is not None else scope
        ratio = ratios[layer] if scope == "main" and layer is not None else 0
        phases = tuple(node["phases"])
        attrs = dict(node["attributes"])
        attrs["source_operation_kind"] = source_kind
        source_inputs = list(node["inputs"])
        source_outputs = list(node["outputs"])
        roles = list(node["tensor_roles"])
        reads, writes = states_of(node)
        predicated = [v for v in source_inputs if v in predicate_values]
        if predicated:
            attrs["execution_predicate"] = predicated[0]
        if node["guard"] is not None:
            attrs["execution_predicate"] = node["guard"]
        operands = [ten(v) for v in source_inputs if v not in predicate_values]
        out0 = source_outputs[0]

        def emit(
            kernel_id: str,
            kind: str,
            inputs: Sequence[str],
            outputs: Sequence[str],
            *,
            step: str = "",
            iteration_domain: Mapping[str, Any],
            attributes: Mapping[str, Any] | None = None,
            state: bool = True,
        ) -> None:
            builder.kernel(
                kernel_id,
                kind,
                inputs,
                outputs,
                numeric_contract=_contract(source_kind, step),
                iteration_domain=iteration_domain,
                attributes=attrs if attributes is None else attributes,
                source_operation_id=node_id,
                source_kind=source_kind,
                phases=phases,
                layer=layer,
                state_reads=reads if state else (),
                state_writes=writes if state else (),
            )

        # -- movement, normalisation and dense contraction ---------------
        if source_kind == "TOKEN_EMBED":
            weight = role_weight(roles[0], scope, layer)
            output = act(out0, "bf16", (span, HIDDEN))
            emit(
                node_id,
                "EMBEDDING_LOOKUP",
                (operands[0], weight),
                (output,),
                iteration_domain={"tokens": span, "width": HIDDEN},
            )
            bind(out0, output)

        elif source_kind == "HC_EXPAND":
            source = operands[0]
            output = act(out0, "bf16", (span, HC_MULT, HIDDEN))
            emit(
                node_id,
                "CONCAT",
                (source,) * HC_MULT,
                (output,),
                iteration_domain={"tokens": span, "hyper_streams": HC_MULT,
                                  "width": HIDDEN},
                attributes={**attrs, "axis": 1, "copies": HC_MULT,
                            "source_replication": "single_embedding"},
            )
            bind(out0, output)

        elif source_kind == "HC_PRE":
            hidden = operands[0]
            base = role_weight(roles[0], scope, layer)
            projection = role_weight(roles[1], scope, layer)
            scale = role_weight(roles[2], scope, layer)
            rows = rows_of(hidden)
            branch = act(source_outputs[0], "bf16", (rows, HIDDEN))
            coefficients = act(
                f"{node_id}.coefficients", "fp32", (rows, HC_COEFFICIENTS)
            )
            emit(
                node_id,
                "HYPER_CONNECT_PRE",
                (hidden, projection, scale, base),
                (branch, coefficients),
                iteration_domain={
                    "tokens": rows,
                    "hyper_streams": HC_MULT,
                    "width": HIDDEN,
                    "mix_width": HC_MIX,
                },
                attributes={
                    **attrs,
                    "coefficient_layout": "post_then_combination",
                    "coefficient_width": HC_COEFFICIENTS,
                    "combination_width": HC_MULT * HC_MULT,
                    "epsilon": RMS_EPSILON,
                    "mix_width": HC_MIX,
                    "post_width": HC_MULT,
                    "sinkhorn_iterations": int(config["hc_sinkhorn_iters"]),
                },
            )
            bind(source_outputs[0], branch)
            bind(source_outputs[1], coefficients)
            bind(source_outputs[2], coefficients)
            bind(source_outputs[3], hidden)

        elif source_kind == "HC_POST":
            inputs = dedupe(operands)
            rows = rows_of(inputs[0])
            output = act(out0, "bf16", (rows, HC_MULT, HIDDEN))
            emit(
                node_id,
                "HYPER_CONNECT_POST",
                inputs,
                (output,),
                iteration_domain={
                    "tokens": rows,
                    "hyper_streams": HC_MULT,
                    "width": HIDDEN,
                },
                attributes={
                    **attrs,
                    "coefficient_layout": "post_then_combination",
                    "combination_width": HC_MULT * HC_MULT,
                    "post_width": HC_MULT,
                },
            )
            bind(out0, output)

        elif source_kind == "HC_HEAD":
            hidden = operands[0]
            base = role_weight(roles[0], scope, layer)
            projection = role_weight(roles[1], scope, layer)
            scale = role_weight(roles[2], scope, layer)
            rows = rows_of(hidden)
            output = act(out0, "bf16", (rows, HIDDEN))
            emit(
                node_id,
                "HYPER_CONNECT_HEAD",
                (hidden, projection, scale, base),
                (output,),
                iteration_domain={
                    "tokens": rows,
                    "hyper_streams": HC_MULT,
                    "width": HIDDEN,
                },
            )
            bind(out0, output)

        elif source_kind == "RMS_NORM":
            source = operands[0]
            weight = role_weight(roles[0], scope, layer)
            shape = builder.shape[source]
            output = act(out0, "bf16", shape)
            emit(
                node_id,
                "RMS_NORM",
                (source, weight),
                (output,),
                iteration_domain={"rows": shape[0], "width": int(attrs["width"])},
            )
            bind(out0, output)

        elif source_kind == "HEAD_RMS_NORM":
            source = operands[0]
            shape = builder.shape[source]
            output = act(out0, "bf16", shape)
            emit(
                node_id,
                "HEAD_RMS_NORM",
                (source,),
                (output,),
                iteration_domain={
                    "tokens": shape[0],
                    "heads": HEADS,
                    "width": HEAD_DIM,
                },
            )
            bind(out0, output)

        elif source_kind in {"FP8_LINEAR", "DSPARK_MAIN_PROJECT"}:
            if source_kind == "DSPARK_MAIN_PROJECT":
                rows = rows_of(operands[0])
                joined = act(
                    f"{node_id}.joined_target_hidden",
                    "bf16",
                    (rows, HIDDEN * len(operands)),
                )
                emit(
                    f"{node_id}.concat",
                    "CONCAT",
                    tuple(operands),
                    (joined,),
                    step="target_hidden_concat",
                    iteration_domain={"tokens": rows,
                                      "width": HIDDEN * len(operands)},
                )
                source = joined
                weight = role_weight(roles[0], scope, layer)
                norm_weight = role_weight(roles[2], scope, layer)
            else:
                source = operands[0]
                weight = role_weight(roles[0], scope, layer)
                norm_weight = None
            out_features, in_features = builder.shape[weight]
            payload, scale = quantize(
                source,
                block=ACTIVATION_BLOCK,
                dtype="fp8_e4m3fn",
                width=None,
                source_operation_id=node_id,
                source_kind=source_kind,
                contract=_contract(source_kind, "activation_quantize"),
                attributes={
                    "block_size": ACTIVATION_BLOCK,
                    "amax_floor_binary32": "0x38d1b717",
                    "output_dtype": "fp8_e4m3fn",
                    "rounding": "rne",
                    "scale_format": "ue8m0",
                    "scale_selection": "bit_ceiling_power_of_two",
                    "source_operation_kind": source_kind,
                },
                layer=layer,
                phases=phases,
            )
            rows = rows_of(source)
            if "heads" in attrs:
                shape = (rows, int(attrs["heads"]), int(attrs["head_dim"]))
            else:
                shape = (rows, out_features)
            product = f"{node_id}.projection" if norm_weight else out0
            output = act(product, "bf16", shape)
            emit(
                f"{node_id}.contract",
                "MATMUL",
                (payload, weight),
                (output,),
                step="block_scaled_contraction",
                iteration_domain={
                    "rows": rows,
                    "output_width": out_features,
                    "reduction_width": in_features,
                },
                attributes={
                    **attrs,
                    "accumulator_dtype": "fp32",
                    "activation_block_elements": ACTIVATION_BLOCK,
                    "input_dtype": "fp8_e4m3fn",
                    "output_dtype": "bf16",
                    "reduction_order": "increasing_reduction_index",
                    "transpose_weight": True,
                    "weight_block_elements": FP8_WEIGHT_BLOCK,
                },
            )
            if norm_weight is not None:
                normalized = act(out0, "bf16", shape)
                emit(
                    f"{node_id}.norm",
                    "RMS_NORM",
                    (output, norm_weight),
                    (normalized,),
                    step="conditioning_norm",
                    iteration_domain={"rows": rows, "width": HIDDEN},
                )
                output = normalized
            bind(out0, output)

        elif source_kind == "BF16_LINEAR":
            source = operands[0]
            weight = role_weight(roles[0], scope, layer)
            out_features, in_features = builder.shape[weight]
            rows = rows_of(source)
            output = act(out0, "bf16", (rows, out_features))
            emit(
                node_id,
                "MATMUL",
                (source, weight),
                (output,),
                iteration_domain={
                    "rows": rows,
                    "output_width": out_features,
                    "reduction_width": in_features,
                },
            )
            bind(out0, output)

        elif source_kind in {"ROPE_APPLY", "ROPE_INVERSE"}:
            source = operands[0]
            shape = builder.shape[source]
            output = act(out0, "bf16", shape)
            inverse = source_kind == "ROPE_INVERSE"
            emit(
                node_id,
                "ROPE_INVERSE" if inverse else "ROPE",
                (source, ten("request.start_pos")),
                (output,),
                iteration_domain={"rows": shape[0], "width": ROPE_DIM},
                attributes={**attrs, **rope_attributes(ratio, inverse=inverse)},
            )
            bind(out0, output)

        elif source_kind in {"FP8_QDQ", "FP4_QDQ"}:
            source = operands[0]
            shape = builder.shape[source]
            if source_kind == "FP8_QDQ":
                width = int(attrs["quantized_width"])
                block = KV_QUANT_BLOCK
                payload_dtype = "fp8_e4m3fn"
            else:
                width = int(shape[-1])
                block = FP4_BLOCK
                payload_dtype = "mxfp4_e2m1"
            payload, scale = quantize(
                source,
                block=block,
                dtype=payload_dtype,
                width=width,
                source_operation_id=node_id,
                source_kind=source_kind,
                contract=_contract(source_kind, "quantize"),
                attributes={**attrs, "block_size": block,
                            "output_dtype": payload_dtype},
                layer=layer,
                phases=phases,
            )
            output = act(out0, "bf16", shape)
            carried = width != int(shape[-1])
            emit(
                node_id,
                "DEQUANTIZE",
                (payload, scale, source) if carried else (payload, scale),
                (output,),
                step="reconstruct",
                iteration_domain={"rows": shape[0], "width": int(shape[-1]),
                                  "block": block},
                attributes={
                    **attrs,
                    "block_size": block,
                    "carried_width": int(shape[-1]) - width,
                    "output_dtype": "bf16",
                    "reconstructed_width": width,
                },
            )
            bind(out0, output)

        elif source_kind == "HADAMARD_ROTATE":
            source = operands[0]
            shape = builder.shape[source]
            output = act(out0, "bf16", shape)
            emit(
                node_id,
                "HADAMARD",
                (source,),
                (output,),
                iteration_domain={"rows": shape[0], "width": int(attrs["width"])},
            )
            bind(out0, output)

        # -- window and compression state --------------------------------
        elif source_kind == "WINDOW_INDEX":
            output = act(out0, "i32", (span, SLIDING_WINDOW))
            emit(
                node_id,
                "WINDOW_INDEX",
                (ten("request.start_pos"),),
                (output,),
                iteration_domain={"tokens": span, "width": SLIDING_WINDOW},
                attributes={**attrs, "index_family": "causal_circular_window",
                            "padding_index": -1},
            )
            bind(out0, output)
            context_of[root]["window_indices"] = output

        elif source_kind == "DSPARK_WINDOW_INDEX":
            width = SLIDING_WINDOW + DRAFT_BLOCK
            output = act(out0, "i32", (DRAFT_BLOCK, width))
            emit(
                node_id,
                "WINDOW_INDEX",
                (ten("request.start_pos"),),
                (output,),
                iteration_domain={"tokens": DRAFT_BLOCK, "width": width},
                attributes={
                    **attrs,
                    "index_family": "causal_window_then_current_draft",
                    "padding_index": -1,
                },
            )
            bind(out0, output)
            context_of[root]["window_indices"] = output

        elif source_kind == "KV_WINDOW_WRITE":
            source = operands[0]
            committed = view(out0, "bf16", (SLIDING_WINDOW, HEAD_DIM))
            emit(
                node_id,
                "KV_APPEND",
                (source, ten("request.start_pos")),
                (committed,),
                iteration_domain={"rows": rows_of(source), "width": HEAD_DIM,
                                  "capacity": SLIDING_WINDOW},
            )
            bind(out0, committed)

        elif source_kind == "COMPRESS_PROJECT":
            source = operands[0]
            key_value_weight = role_weight(roles[0], scope, layer)
            gate_weight = role_weight(roles[1], scope, layer)
            width = int(attrs["output_features"])
            rows = rows_of(source)
            key_value = act(source_outputs[0], "fp32", (rows, width))
            score = act(source_outputs[1], "fp32", (rows, width))
            emit(
                f"{node_id}.key_value",
                "COMPRESS_PROJECT",
                (source, key_value_weight),
                (key_value,),
                step="key_value_projection",
                iteration_domain={"tokens": rows, "output_width": width,
                                  "reduction_width": HIDDEN},
            )
            emit(
                f"{node_id}.score",
                "COMPRESS_PROJECT",
                (source, gate_weight),
                (score,),
                step="score_projection",
                iteration_domain={"tokens": rows, "output_width": width,
                                  "reduction_width": HIDDEN},
            )
            bind(source_outputs[0], key_value)
            bind(source_outputs[1], score)

        elif source_kind == "COMPRESS_STATE_UPDATE":
            key_value, score = operands[0], operands[1]
            position_weight = role_weight(roles[0], scope, layer)
            node_ratio = int(attrs["ratio"])
            head_width = int(attrs["head_dim"])
            candidates = 2 * node_ratio if attrs["overlap"] else node_ratio
            rows = rows_of(score)
            biased = act(
                f"{node_id}.positional_score", "fp32", builder.shape[score]
            )
            emit(
                f"{node_id}.positional_score",
                "ADD",
                (score, position_weight),
                (biased,),
                step="positional_score_add",
                iteration_domain={"tokens": rows,
                                  "width": builder.shape[score][-1]},
                state=False,
            )
            group_rows = groups[node_ratio]
            pool_key_value = act(
                source_outputs[0], "fp32", (group_rows, candidates, head_width)
            )
            pool_score = act(
                source_outputs[1], "fp32", (group_rows, candidates, head_width)
            )
            emit(
                node_id,
                "COMPRESS_STATE_UPDATE",
                (key_value, biased),
                (pool_key_value, pool_score),
                step="raw_window_transaction",
                iteration_domain={"groups": group_rows, "candidates": candidates,
                                  "width": head_width},
            )
            bind(source_outputs[0], pool_key_value)
            bind(source_outputs[1], pool_score)
            predicate_values.add(source_outputs[2])

        elif source_kind == "COMPRESS_POOL":
            pool_key_value, pool_score = operands[0], operands[1]
            head_width = int(attrs["head_dim"])
            group_rows = rows_of(pool_key_value)
            output = act(out0, "fp32", (group_rows, head_width))
            emit(
                node_id,
                "COMPRESS_POOL",
                (pool_key_value, pool_score),
                (output,),
                iteration_domain={"groups": group_rows,
                                  "candidates": int(attrs["candidate_count"]),
                                  "width": head_width},
            )
            bind(out0, output)

        elif source_kind == "BINARY32_TO_BF16":
            source = operands[0]
            shape = builder.shape[source]
            output = act(out0, "bf16", shape)
            emit(
                node_id,
                "CONVERT",
                (source,),
                (output,),
                iteration_domain={"rows": shape[0], "width": int(attrs["width"])},
            )
            bind(out0, output)

        elif source_kind == "COMPRESS_KV_WRITE":
            source = operands[0]
            head_width = int(attrs["head_dim"])
            capacity = context_tokens // int(attrs["ratio"])
            committed = view(out0, "bf16", (capacity, head_width))
            emit(
                node_id,
                "KV_APPEND",
                (source, ten("request.start_pos")),
                (committed,),
                iteration_domain={"rows": rows_of(source), "width": head_width,
                                  "capacity": capacity},
            )
            bind(out0, committed)

        elif source_kind == "COMPRESSED_KV_VALID_VIEW":
            source = operands[0]
            head_width = int(attrs["head_dim"])
            node_ratio = int(attrs["ratio"])
            family = (
                "compressed_key_value"
                if attrs["projection_scope"] == "main"
                else "index_compressed_key_value"
            )
            reads = (ensure_state(f"{family}.{scope}.layer.{layer}"),)
            output = view(out0, "bf16", (committed_groups[node_ratio], head_width))
            emit(
                node_id,
                "STATE_READ",
                (source,),
                (output,),
                iteration_domain={"rows": committed_groups[node_ratio],
                                  "width": head_width},
            )
            bind(out0, output)

        # -- attention row space and selection ---------------------------
        elif source_kind == "ATTENTION_KV_VIEW":
            sources = tuple(operands[:-2])
            rows = (
                SLIDING_WINDOW + DRAFT_BLOCK
                if scope == "dspark"
                else attention_rows[ratio]
            )
            output = view(out0, "bf16", (rows, HEAD_DIM))
            emit(
                node_id,
                "CONCAT",
                sources,
                (output,),
                iteration_domain={"rows": rows, "width": HEAD_DIM},
                attributes={
                    **attrs,
                    "axis": 0,
                    "segment_order": (
                        "current_then_committed_window_then_valid_compressed_prefix"
                    ),
                },
            )
            bind(out0, output)

        elif source_kind == "INDEX_SCORE":
            query, key_value, head_weights = operands[0], operands[1], operands[2]
            rows = rows_of(query)
            output = act(out0, "bf16", (rows, committed_groups[4]))
            emit(
                node_id,
                "INDEX_SCORE",
                (query, key_value, head_weights),
                (output,),
                iteration_domain={
                    "tokens": rows,
                    "candidates": committed_groups[4],
                    "heads": INDEX_HEADS,
                    "width": INDEX_HEAD_DIM,
                },
            )
            bind(out0, output)

        elif source_kind == "INDEX_TOPK":
            score = operands[0]
            window_indices = operands[1]
            rows = rows_of(score)
            selected = act(f"{node_id}.selected", "i32", (rows, INDEX_TOPK))
            emit(
                f"{node_id}.select",
                "INDEX_TOPK",
                (score,),
                (selected,),
                step="masked_topk",
                iteration_domain={"tokens": rows, "top_k": INDEX_TOPK},
                attributes={
                    **attrs,
                    "causal_mask": "compressed_group_completed_before_position",
                    "order": "score_descending_then_index_ascending",
                    "padding_index": -1,
                },
            )
            width = SLIDING_WINDOW + INDEX_TOPK
            output = act(out0, "i32", (rows, width))
            emit(
                f"{node_id}.concat",
                "CONCAT",
                (window_indices, selected),
                (output,),
                step="window_then_compressed_indices",
                iteration_domain={"tokens": rows, "width": width},
                attributes={
                    **attrs,
                    "axis": 1,
                    "segment_widths": [SLIDING_WINDOW, INDEX_TOPK],
                },
            )
            bind(out0, output)

        elif source_kind == "COMPRESSED_DENSE_INDEX":
            window_indices = operands[0]
            node_ratio = int(attrs["ratio"])
            dense = act(f"{node_id}.dense", "i32", (span, groups[node_ratio]))
            emit(
                f"{node_id}.enumerate",
                "WINDOW_INDEX",
                (ten("request.start_pos"),),
                (dense,),
                step="causal_compressed_enumeration",
                iteration_domain={"tokens": span, "width": groups[node_ratio]},
                attributes={
                    **attrs,
                    "index_family": "causal_compressed_dense",
                    "padding_index": -1,
                },
            )
            output = act(out0, "i32", (span, selected_rows_128))
            emit(
                f"{node_id}.concat",
                "CONCAT",
                (window_indices, dense),
                (output,),
                step="window_then_compressed_indices",
                iteration_domain={"tokens": span, "width": selected_rows_128},
                attributes={**attrs, "axis": 1},
            )
            bind(out0, output)

        elif source_kind == "SPARSE_ATTENTION":
            query, key_value, indices = operands[0], operands[1], operands[2]
            sink = role_weight(roles[0], scope, layer)
            rows = rows_of(query)
            output = act(out0, "bf16", (rows, HEADS, HEAD_DIM))
            emit(
                node_id,
                "ATTENTION_SPARSE",
                # TA-ABI3-OPCONV-1 amendment A6 freezes q, kv, indices, sink.
                (query, key_value, indices, sink),
                (output,),
                iteration_domain={
                    "tokens": rows,
                    "heads": HEADS,
                    "width": HEAD_DIM,
                    "candidates": builder.shape[indices][-1],
                },
            )
            bind(out0, output)

        elif source_kind == "GROUPED_OUTPUT_PROJECT":
            source = operands[0]
            weight = role_weight(roles[0], scope, layer)
            rows = rows_of(source)
            output = act(out0, "bf16", (rows, O_GROUPS * O_RANK))
            emit(
                node_id,
                "GROUPED_MATMUL",
                (source, weight),
                (output,),
                iteration_domain={
                    "tokens": rows,
                    "groups": O_GROUPS,
                    "output_width": O_RANK,
                    "reduction_width": HEADS * HEAD_DIM // O_GROUPS,
                },
                attributes={
                    **attrs,
                    "accumulator_dtype": "fp32",
                    "input_dtype": "bf16",
                    "output_dtype": "bf16",
                    "weight_dequantization": "block_scaled_fp8_to_bf16",
                    "weight_group_layout": "groups_by_rank_by_reduction",
                },
            )
            bind(out0, output)

        # -- routing and experts ----------------------------------------
        elif source_kind == "ROUTER_SCORE":
            source = operands[0]
            weight = role_weight(roles[0], scope, layer)
            rows = rows_of(source)
            output = act(out0, "fp32", (rows, ROUTED_EXPERTS))
            emit(
                node_id,
                "ROUTER_SCORE",
                (source, weight),
                (output,),
                iteration_domain={"tokens": rows, "experts": ROUTED_EXPERTS,
                                  "reduction_width": HIDDEN},
            )
            bind(out0, output)

        elif source_kind == "SQRT_SOFTPLUS":
            source = operands[0]
            rows = rows_of(source)
            output = act(out0, "fp32", (rows, ROUTED_EXPERTS))
            emit(
                node_id,
                "SQRT_SOFTPLUS",
                (source,),
                (output,),
                iteration_domain={"tokens": rows, "experts": ROUTED_EXPERTS},
            )
            bind(out0, output)

        elif source_kind == "HASH_ROUTE":
            table = role_weight(roles[0], scope, layer)
            rows = rows_of(operands[0])
            output = act(out0, "i32", (rows, TOP_K))
            emit(
                node_id,
                "HASH_ROUTE",
                (ten("request.input_ids"), table),
                (output,),
                iteration_domain={"tokens": rows, "top_k": TOP_K},
                attributes={**attrs, "table_dtype": "i64",
                            "table_rows": VOCABULARY},
            )
            bind(out0, output)
            context_of[root]["expert_indices"] = output

        elif source_kind == "BIASED_TOPK_ROUTE":
            score = operands[0]
            bias = role_weight(roles[0], scope, layer)
            rows = rows_of(score)
            indices = act(out0, "i32", (rows, TOP_K))
            values = act(f"{node_id}.selected_score", "fp32", (rows, TOP_K))
            emit(
                node_id,
                "BIASED_TOPK",
                (score, bias),
                (indices, values),
                iteration_domain={"tokens": rows, "experts": ROUTED_EXPERTS,
                                  "top_k": TOP_K},
                attributes={
                    **attrs,
                    "bias_scope": "selection_only",
                    "order": "score_descending_then_index_ascending",
                    "selected_score_output": (
                        "unused_the_released_graph_regathers_unbiased_scores"
                    ),
                },
            )
            bind(out0, indices)
            context_of[root]["expert_indices"] = indices

        elif source_kind == "ROUTER_WEIGHT_NORMALIZE":
            score, indices = operands[0], operands[1]
            rows = rows_of(score)
            selected = act(f"{node_id}.gathered", "fp32", (rows, TOP_K))
            emit(
                f"{node_id}.gather",
                "GATHER",
                (score, indices),
                (selected,),
                step="unbiased_score_gather",
                iteration_domain={"tokens": rows, "top_k": TOP_K},
            )
            normalized = act(f"{node_id}.normalized", "fp32", (rows, TOP_K))
            emit(
                f"{node_id}.normalize",
                "WEIGHT_NORMALIZE",
                (selected,),
                (normalized,),
                step="selected_sum_normalize",
                iteration_domain={"tokens": rows, "top_k": TOP_K},
            )
            output = act(out0, "fp32", (rows, TOP_K))
            emit(
                f"{node_id}.scale",
                "SCALE",
                (normalized,),
                (output,),
                step="route_scale",
                iteration_domain={"tokens": rows, "top_k": TOP_K},
                attributes={**attrs, "factor": ROUTE_SCALE,
                            "factor_dtype": "fp32"},
            )
            bind(out0, output)
            context_of[root]["route_weights"] = output

        elif source_kind == "EXPERT_DISPATCH":
            source, indices = operands[0], operands[1]
            rows = rows_of(source)
            routed_rows = (
                dispatch_rows if isinstance(rows, Symbolic) else rows * TOP_K
            )
            output = act(out0, "bf16", (routed_rows, HIDDEN))
            emit(
                node_id,
                "EXPERT_DISPATCH",
                (source, indices),
                (output,),
                iteration_domain={"tokens": rows, "top_k": TOP_K,
                                  "routed_rows": routed_rows, "width": HIDDEN},
                attributes={
                    **attrs,
                    "row_order": "ascending_token_then_ascending_selection",
                },
            )
            bind(out0, output)
            context_of[root]["dispatch"] = output

        elif source_kind in {"MXFP4_SWIGLU", "FP8_SWIGLU"}:
            routed = source_kind == "MXFP4_SWIGLU"
            source = operands[0]
            rows = rows_of(source)
            if routed:
                gate_weights = role_weight_family(roles[0], scope, layer)
                down_weights = role_weight_family(roles[2], scope, layer)
                up_weights = role_weight_family(roles[4], scope, layer)
                expert_rows = context_of[root]["expert_indices"]
                route_weights = context_of[root]["route_weights"]
                weight_attributes = {
                    "expert_count": ROUTED_EXPERTS,
                    "expert_weight_block_elements": FP4_BLOCK,
                    "expert_weight_dtype": "mxfp4_e2m1",
                    "expert_weight_order": "ascending_logical_expert_id",
                }
            else:
                gate_weight = role_weight(roles[0], scope, layer)
                down_weight = role_weight(roles[2], scope, layer)
                up_weight = role_weight(roles[4], scope, layer)
                weight_attributes = {}
            payload, scale = quantize(
                source,
                block=ACTIVATION_BLOCK,
                dtype="fp8_e4m3fn",
                width=None,
                source_operation_id=node_id,
                source_kind=source_kind,
                contract=_contract(source_kind, "activation_quantize"),
                attributes={
                    "block_size": ACTIVATION_BLOCK,
                    "output_dtype": "fp8_e4m3fn",
                    "rounding": "rne",
                    "scale_format": "ue8m0",
                    "source_operation_kind": source_kind,
                },
                layer=layer,
                phases=phases,
            )
            gate = act(f"{node_id}.gate", "bf16", (rows, MOE_INTERMEDIATE))
            up = act(f"{node_id}.up", "bf16", (rows, MOE_INTERMEDIATE))
            contraction = {
                "rows": rows,
                "output_width": MOE_INTERMEDIATE,
                "reduction_width": HIDDEN,
            }
            for name, output_id, family_key in (
                ("gate", gate, "gate"),
                ("up", up, "up"),
            ):
                family = gate_weights if family_key == "gate" else up_weights
                if routed:
                    emit(
                        f"{node_id}.{name}",
                        "ROUTED_MATMUL",
                        (payload, expert_rows),
                        (output_id,),
                        step=f"{name}_contraction",
                        iteration_domain=contraction,
                        attributes={
                            **attrs,
                            **weight_attributes,
                            "expert_weight_tensors": family,
                            "projection": name,
                        },
                    )
                else:
                    emit(
                        f"{node_id}.{name}",
                        "MATMUL",
                        (payload, gate_weight if name == "gate" else up_weight),
                        (output_id,),
                        step=f"{name}_contraction",
                        iteration_domain=contraction,
                        attributes={**attrs, "projection": name,
                                    "weight_block_elements": FP8_WEIGHT_BLOCK},
                    )
            activated = act(f"{node_id}.activated", "bf16",
                            (rows, MOE_INTERMEDIATE))
            emit(
                f"{node_id}.activate",
                "SWIGLU",
                (gate, up),
                (activated,),
                step="clamped_silu_product",
                iteration_domain={"rows": rows, "width": MOE_INTERMEDIATE},
                attributes={
                    **attrs,
                    "clamp": "gate_upper_and_up_symmetric",
                    "compute_dtype": "fp32",
                    "swiglu_limit": SWIGLU_LIMIT,
                },
            )
            if routed:
                weighted = act(f"{node_id}.weighted", "bf16",
                               (rows, MOE_INTERMEDIATE))
                emit(
                    f"{node_id}.route_weight",
                    "MUL",
                    (activated, route_weights),
                    (weighted,),
                    step="routing_weight_product",
                    iteration_domain={"rows": rows, "width": MOE_INTERMEDIATE},
                    attributes={**attrs,
                                "broadcast": "routed_row_to_intermediate_width"},
                )
                activated = weighted
            down_payload, _ = quantize(
                activated,
                block=ACTIVATION_BLOCK,
                dtype="fp8_e4m3fn",
                width=None,
                source_operation_id=node_id,
                source_kind=source_kind,
                contract=_contract(source_kind, "activation_quantize"),
                attributes={
                    "block_size": ACTIVATION_BLOCK,
                    "output_dtype": "fp8_e4m3fn",
                    "rounding": "rne",
                    "scale_format": "ue8m0",
                    "source_operation_kind": source_kind,
                },
                layer=layer,
                phases=phases,
            )
            output = act(out0, "bf16", (rows, HIDDEN))
            if routed:
                emit(
                    f"{node_id}.down",
                    "ROUTED_MATMUL",
                    (down_payload, expert_rows),
                    (output,),
                    step="down_contraction",
                    iteration_domain={"rows": rows, "output_width": HIDDEN,
                                      "reduction_width": MOE_INTERMEDIATE},
                    attributes={
                        **attrs,
                        **weight_attributes,
                        "expert_weight_tensors": down_weights,
                        "projection": "down",
                    },
                )
            else:
                emit(
                    f"{node_id}.down",
                    "MATMUL",
                    (down_payload, down_weight),
                    (output,),
                    step="down_contraction",
                    iteration_domain={"rows": rows, "output_width": HIDDEN,
                                      "reduction_width": MOE_INTERMEDIATE},
                    attributes={**attrs, "projection": "down",
                                "weight_block_elements": FP8_WEIGHT_BLOCK},
                )
            bind(out0, output)

        elif source_kind == "EXPERT_REDUCE":
            routed_output, shared_output = operands[1], operands[2]
            rows = rows_of(shared_output)
            output = act(out0, "bf16", (rows, HIDDEN))
            emit(
                node_id,
                "EXPERT_REDUCE",
                (routed_output, shared_output),
                (output,),
                iteration_domain={"tokens": rows, "top_k": TOP_K,
                                  "width": HIDDEN},
                attributes={
                    **attrs,
                    "base_operand_index": 1,
                    "contribution_row_order": (
                        "ascending_token_then_ascending_selection"
                    ),
                    "routing_weight_application": (
                        "already_applied_inside_the_expert_before_the_down_"
                        "projection"
                    ),
                    "top_k": TOP_K,
                },
            )
            bind(out0, output)

        # -- head and selection -----------------------------------------
        elif source_kind == "LM_HEAD":
            source = operands[0]
            weight = role_weight(roles[0], scope, layer)
            if attrs["full_logits"]:
                selected = source
                rows = rows_of(source)
            else:
                rows = 1
                selected = act(f"{node_id}.final_position", "bf16", (1, HIDDEN))
                emit(
                    f"{node_id}.select",
                    "LAST_TOKEN_SELECT",
                    (source, ten("request.start_pos")),
                    (selected,),
                    step="final_source_position",
                    iteration_domain={"rows": 1, "width": HIDDEN},
                )
            output = act(out0, "fp32", (rows, VOCABULARY))
            emit(
                f"{node_id}.project",
                "VOCAB_PROJECT",
                (selected, weight),
                (output,),
                step="vocabulary_projection",
                iteration_domain={"rows": rows, "output_width": VOCABULARY,
                                  "reduction_width": HIDDEN},
            )
            bind(out0, output)

        elif source_kind == "SAMPLE":
            logits = operands[0]
            rows = rows_of(logits)
            scaled = act(f"{node_id}.scaled_logits", "fp32", (rows, VOCABULARY))
            emit(
                f"{node_id}.temperature",
                "SCALE",
                (logits, ten("request.temperature_binary32")),
                (scaled,),
                step="temperature",
                iteration_domain={"rows": rows, "width": VOCABULARY},
                attributes={**attrs, "operation": "reciprocal_temperature_product"},
            )
            token = act(f"{node_id}.argmax", "i32", (rows,))
            emit(
                f"{node_id}.select",
                "ARGMAX",
                (scaled,),
                (token,),
                step="greedy_argmax",
                iteration_domain={"rows": rows, "width": VOCABULARY},
                attributes={**attrs, "tie_rule": "lowest_token_id"},
            )
            appended = act(source_outputs[0], "i32", (rows,))
            emit(
                f"{node_id}.append",
                "TOKEN_APPEND",
                (token,),
                (appended,),
                step="token_append",
                iteration_domain={"rows": rows},
                attributes={**attrs, "eos_token_id": EOS_TOKEN_ID},
            )
            bind(source_outputs[0], appended)
            bind(source_outputs[1], ten("request.explicit_exponential_entropy"))

        # -- speculative profile ----------------------------------------
        elif source_kind == "TARGET_HIDDEN_CAPTURE":
            source = operands[0]
            rows = rows_of(source)
            summed = act(f"{node_id}.stream_sum", "fp32", (rows, HIDDEN))
            emit(
                f"{node_id}.sum",
                "PARTITION_SUM",
                (source,),
                (summed,),
                step="hyper_stream_sum",
                iteration_domain={"tokens": rows, "hyper_streams": HC_MULT,
                                  "width": HIDDEN},
            )
            output = act(out0, "bf16", (rows, HIDDEN))
            emit(
                f"{node_id}.mean",
                "SCALE",
                (summed,),
                (output,),
                step="hyper_stream_mean",
                iteration_domain={"tokens": rows, "width": HIDDEN},
                attributes={**attrs, "factor": 1.0 / HC_MULT,
                            "factor_dtype": "fp32"},
            )
            bind(out0, output)

        elif source_kind == "DSPARK_NOISE_EMBED":
            weight = role_weight(roles[0], scope, layer)
            draft_ids = act(f"{node_id}.draft_token_ids", "i32", (DRAFT_BLOCK,))
            emit(
                f"{node_id}.compose",
                "SCATTER",
                (operands[0],),
                (draft_ids,),
                step="noise_block",
                iteration_domain={"rows": DRAFT_BLOCK},
                attributes={
                    **attrs,
                    "carried_position": 0,
                    "fill_token_id": int(config["dspark_noise_token_id"]),
                },
            )
            embedded = act(f"{node_id}.embedded", "bf16", (DRAFT_BLOCK, HIDDEN))
            emit(
                f"{node_id}.lookup",
                "EMBEDDING_LOOKUP",
                (draft_ids, weight),
                (embedded,),
                step="draft_embedding",
                iteration_domain={"rows": DRAFT_BLOCK, "width": HIDDEN},
            )
            output = act(out0, "bf16", (DRAFT_BLOCK, HC_MULT, HIDDEN))
            emit(
                f"{node_id}.expand",
                "CONCAT",
                (embedded,) * HC_MULT,
                (output,),
                step="hyper_stream_expand",
                iteration_domain={"rows": DRAFT_BLOCK, "hyper_streams": HC_MULT,
                                  "width": HIDDEN},
                attributes={**attrs, "axis": 1, "copies": HC_MULT},
            )
            bind(out0, output)

        elif source_kind == "DSPARK_PREFILL_KV":
            source = operands[0]
            weight = role_weight(roles[0], scope, layer)
            norm_weight = role_weight(roles[2], scope, layer)
            rows = rows_of(source)
            payload, scale = quantize(
                source,
                block=ACTIVATION_BLOCK,
                dtype="fp8_e4m3fn",
                width=None,
                source_operation_id=node_id,
                source_kind=source_kind,
                contract=_contract(source_kind, "activation_quantize"),
                attributes={"block_size": ACTIVATION_BLOCK,
                            "output_dtype": "fp8_e4m3fn",
                            "scale_format": "ue8m0",
                            "source_operation_kind": source_kind},
                layer=layer,
                phases=phases,
            )
            projected = act(f"{node_id}.projection", "bf16", (rows, HEAD_DIM))
            emit(
                f"{node_id}.project",
                "MATMUL",
                (payload, weight),
                (projected,),
                step="key_value_projection",
                iteration_domain={"rows": rows, "output_width": HEAD_DIM,
                                  "reduction_width": HIDDEN},
                state=False,
            )
            normalized = act(f"{node_id}.normalized", "bf16", (rows, HEAD_DIM))
            emit(
                f"{node_id}.norm",
                "RMS_NORM",
                (projected, norm_weight),
                (normalized,),
                step="key_value_norm",
                iteration_domain={"rows": rows, "width": HEAD_DIM},
                state=False,
            )
            rotated = act(f"{node_id}.rotated", "bf16", (rows, HEAD_DIM))
            emit(
                f"{node_id}.rope",
                "ROPE",
                (normalized, ten("request.start_pos")),
                (rotated,),
                step="key_value_rope",
                iteration_domain={"rows": rows, "width": ROPE_DIM},
                attributes={**attrs, **rope_attributes(0, inverse=False)},
                state=False,
            )
            kv_payload, kv_scale = quantize(
                rotated,
                block=KV_QUANT_BLOCK,
                dtype="fp8_e4m3fn",
                width=NOPE_DIM,
                source_operation_id=node_id,
                source_kind=source_kind,
                contract=_contract(source_kind, "quantize"),
                attributes={"block_size": KV_QUANT_BLOCK,
                            "output_dtype": "fp8_e4m3fn",
                            "quantized_width": NOPE_DIM,
                            "scale_format": "ue8m0",
                            "source_operation_kind": source_kind},
                layer=layer,
                phases=phases,
            )
            reconstructed = act(f"{node_id}.key_value", "bf16", (rows, HEAD_DIM))
            emit(
                f"{node_id}.reconstruct",
                "DEQUANTIZE",
                (kv_payload, kv_scale, rotated),
                (reconstructed,),
                step="reconstruct",
                iteration_domain={"rows": rows, "width": HEAD_DIM,
                                  "block": KV_QUANT_BLOCK},
                attributes={**attrs, "carried_width": ROPE_DIM,
                            "reconstructed_width": NOPE_DIM},
                state=False,
            )
            committed = view(out0, "bf16", (SLIDING_WINDOW, HEAD_DIM))
            emit(
                f"{node_id}.commit",
                "KV_APPEND",
                (reconstructed, ten("request.start_pos")),
                (committed,),
                step="window_commit",
                iteration_domain={"rows": rows, "width": HEAD_DIM,
                                  "capacity": SLIDING_WINDOW},
            )
            bind(out0, committed)

        elif source_kind == "MARKOV_AUTOREGRESSIVE_LOOP":
            draft_logits = operands[0]
            embedding_weight = role_weight(roles[0], scope, layer)
            head_weight = role_weight(roles[1], scope, layer)
            carried = operands[1]
            embeds: list[str] = []
            adjusted: list[str] = []
            for step_index in range(DRAFT_BLOCK):
                embed = act(
                    f"{node_id}.step{step_index}.embedding", "bf16", (1, MARKOV_RANK)
                )
                emit(
                    f"{node_id}.step{step_index}.lookup",
                    "EMBEDDING_LOOKUP",
                    (carried, embedding_weight),
                    (embed,),
                    step=f"step{step_index}_lookup",
                    iteration_domain={"rows": 1, "width": MARKOV_RANK},
                )
                bias = act(
                    f"{node_id}.step{step_index}.bias", "fp32", (1, VOCABULARY)
                )
                emit(
                    f"{node_id}.step{step_index}.project",
                    "VOCAB_PROJECT",
                    (embed, head_weight),
                    (bias,),
                    step=f"step{step_index}_head",
                    iteration_domain={"rows": 1, "output_width": VOCABULARY,
                                      "reduction_width": MARKOV_RANK},
                )
                row = act(
                    f"{node_id}.step{step_index}.logits", "fp32", (1, VOCABULARY)
                )
                emit(
                    f"{node_id}.step{step_index}.add",
                    "ADD",
                    (draft_logits, bias),
                    (row,),
                    step=f"step{step_index}_logit_bias",
                    iteration_domain={"rows": 1, "width": VOCABULARY},
                    attributes={**attrs, "left_row_index": step_index},
                )
                token = act(f"{node_id}.step{step_index}.token", "i32", (1,))
                emit(
                    f"{node_id}.step{step_index}.select",
                    "ARGMAX",
                    (row,),
                    (token,),
                    step=f"step{step_index}_argmax",
                    iteration_domain={"rows": 1, "width": VOCABULARY},
                    attributes={**attrs, "tie_rule": "lowest_token_id"},
                )
                carried_next = act(
                    f"{node_id}.step{step_index}.carried", "i32", (1,)
                )
                emit(
                    f"{node_id}.step{step_index}.append",
                    "TOKEN_APPEND",
                    (token,),
                    (carried_next,),
                    step=f"step{step_index}_append",
                    iteration_domain={"rows": 1},
                    attributes={**attrs, "draft_token_ring_width": DRAFT_BLOCK + 1,
                                "draft_token_ring_position": step_index + 1},
                )
                carried = carried_next
                embeds.append(embed)
                adjusted.append(row)
            embed_head = act(f"{node_id}.embedding_head", "bf16", (4, MARKOV_RANK))
            emit(
                f"{node_id}.embedding_head",
                "CONCAT",
                tuple(embeds[:4]),
                (embed_head,),
                step="embedding_concat_head",
                iteration_domain={"rows": 4, "width": MARKOV_RANK},
                attributes={**attrs, "axis": 0},
            )
            embed_all = act(
                source_outputs[2], "bf16", (DRAFT_BLOCK, MARKOV_RANK)
            )
            emit(
                f"{node_id}.embedding_all",
                "CONCAT",
                (embed_head, embeds[4]),
                (embed_all,),
                step="embedding_concat_tail",
                iteration_domain={"rows": DRAFT_BLOCK, "width": MARKOV_RANK},
                attributes={**attrs, "axis": 0},
            )
            logit_head = act(f"{node_id}.logit_head", "fp32", (4, VOCABULARY))
            emit(
                f"{node_id}.logit_head",
                "CONCAT",
                tuple(adjusted[:4]),
                (logit_head,),
                step="logit_concat_head",
                iteration_domain={"rows": 4, "width": VOCABULARY},
                attributes={**attrs, "axis": 0},
            )
            logit_all = act(
                source_outputs[1], "fp32", (DRAFT_BLOCK, VOCABULARY)
            )
            emit(
                f"{node_id}.logit_all",
                "CONCAT",
                (logit_head, adjusted[4]),
                (logit_all,),
                step="logit_concat_tail",
                iteration_domain={"rows": DRAFT_BLOCK, "width": VOCABULARY},
                attributes={**attrs, "axis": 0},
            )
            bind(source_outputs[0], carried)
            bind(source_outputs[1], logit_all)
            bind(source_outputs[2], embed_all)
            bind(source_outputs[3], ten("request.explicit_exponential_entropy"))

        elif source_kind == "CONFIDENCE_SCORE":
            hidden_value, markov_value = operands[0], operands[1]
            weight = role_weight(roles[0], scope, layer)
            width = HIDDEN + MARKOV_RANK
            joined = act(f"{node_id}.joined", "bf16", (DRAFT_BLOCK, width))
            emit(
                f"{node_id}.concat",
                "CONCAT",
                (hidden_value, markov_value),
                (joined,),
                step="hidden_then_markov",
                iteration_domain={"rows": DRAFT_BLOCK, "width": width},
                attributes={**attrs, "axis": 1,
                            "segment_widths": [HIDDEN, MARKOV_RANK]},
            )
            output = act(out0, "fp32", (DRAFT_BLOCK, 1))
            emit(
                f"{node_id}.project",
                "MATMUL",
                (joined, weight),
                (output,),
                step="confidence_projection",
                iteration_domain={"rows": DRAFT_BLOCK, "output_width": 1,
                                  "reduction_width": width},
            )
            bind(out0, output)

        else:  # pragma: no cover - the catalogue is closed and covered
            raise DeepSeekV4KernelIRError(
                f"source operator kind {source_kind!r} has no neutral lowering; "
                "adding one requires a versioned change to "
                "compiler/ir/v3/kernel_ir.py and compiler/ir/v3/lowering.py"
            )

    # ------------------------------------------------------------------
    # Assemble
    # ------------------------------------------------------------------
    declared_symbols = {symbol.name for symbol in symbols}
    for tensor in builder.tensors:
        for extent in tensor.shape:
            if isinstance(extent, Symbolic) and extent.symbol not in declared_symbols:
                raise DeepSeekV4KernelIRError(
                    f"tensor {tensor.tensor_id} uses undeclared symbol "
                    f"{extent.symbol!r}"
                )
    for kernel in builder.kernels:
        for extent in kernel.iteration_domain.values():
            if isinstance(extent, Symbolic) and extent.symbol not in declared_symbols:
                raise DeepSeekV4KernelIRError(
                    f"kernel {kernel.kernel_id} uses undeclared symbol "
                    f"{extent.symbol!r}"
                )

    missing_kinds = sorted(set(OPERATOR_CATALOG) - set(emitted_source_kinds))
    if include_speculative and missing_kinds:
        raise DeepSeekV4KernelIRError(
            f"speculative export omitted source kinds {missing_kinds}"
        )

    outputs: list[str] = [
        value_tensor["main.sample.tokens"],
        value_tensor["main.lm_head.output"],
    ]
    if include_speculative:
        outputs.extend(
            (
                value_tensor["dspark.markov_loop.tokens"],
                value_tensor["dspark.markov_loop.adjusted_logits"],
                value_tensor["dspark.confidence.output"],
            )
        )
    inputs = (token_ids, position_offset, session_ids, temperature, entropy)
    state_ids = tuple(resource.state_id for resource in builder.states)

    generation_policy = {
        "bos_token_id": BOS_TOKEN_ID,
        "eos_token_ids": [EOS_TOKEN_ID],
        "eos_source": "generation_config.json",
        "include_eos_in_output": True,
        "maximum_new_tokens": int(maximum_new_tokens),
        "policy_id": GENERATION_POLICY_ID,
        "selection_mode": "greedy_argmax_lowest_id",
        "speculative_profile": bool(include_speculative),
        "stochastic_sampling": (
            "not_expressible_in_the_frozen_neutral_registry; the released "
            "sample() draws Gumbel-max noise and no neutral kind produces or "
            "consumes an entropy stream, so this export declares the greedy "
            "boundary and carries the entropy input unchanged"
        ),
        "stop_condition": "first_official_eos_or_maximum_new_tokens",
        "tie_rule": "lowest_token_id",
        "vocabulary_size": VOCABULARY,
    }

    graph = KernelGraph(
        model_id=MODEL_ID,
        source={
            "architectural_max_context": ARCHITECTURAL_MAX_CONTEXT,
            "checkpoint_lock_id": lock["lock_id"],
            "checkpoint_payload_bytes": PAYLOAD_BYTES,
            "checkpoint_tensor_count": TENSOR_COUNT,
            "deployment_context_tokens": context_tokens,
            "graph_contract_id": contract["graph_contract_id"],
            "inference_config_sha256": INFERENCE_CONFIG_SHA256,
            "kernel_source_sha256": KERNEL_SOURCE_SHA256,
            "model_source_sha256": MODEL_SOURCE_SHA256,
            "profile": (
                "target_and_speculative" if include_speculative else "target_only"
            ),
            "repository": REPOSITORY,
            "revision": REVISION,
            "source_node_count": len(nodes),
            "tensor_structure_sha256": TENSOR_STRUCTURE_SHA256,
        },
        symbols=symbols,
        tensors=tuple(builder.tensors),
        states=tuple(builder.states),
        kernels=tuple(builder.kernels),
        entrypoints=(
            Entrypoint(
                phase="prefill",
                inputs=inputs,
                outputs=tuple(outputs),
                states=state_ids,
                generation_policy=GENERATION_POLICY_ID,
            ),
            Entrypoint(
                phase="decode",
                inputs=inputs,
                outputs=tuple(outputs),
                states=state_ids,
                generation_policy=GENERATION_POLICY_ID,
            ),
        ),
        numeric_profile=NUMERIC_PROFILE,
        generation_policy=generation_policy,
    )
    errors = check_neutral(graph)
    if errors:
        raise DeepSeekV4KernelIRError(
            "neutral IR rejected:\n  " + "\n  ".join(errors[:40])
        )
    return graph


def graph_census(graph: KernelGraph) -> dict[str, Any]:
    """Return the auditable census the release report quotes."""

    by_kind: Counter = Counter(kernel.kind for kernel in graph.kernels)
    by_source: Counter = Counter(
        kernel.source_operation_id.split(".")[0] for kernel in graph.kernels
    )
    roles: Counter = Counter(tensor.role for tensor in graph.tensors)
    dtypes: Counter = Counter(tensor.dtype for tensor in graph.tensors)
    bound = [t for t in graph.tensors if t.binding is not None]
    return {
        "bound_weight_bytes": sum(t.binding.bytes for t in bound),  # type: ignore[union-attr]
        "bound_weight_tensors": len(bound),
        "entrypoints": [e.phase for e in graph.entrypoints],
        "graph_id": graph.graph_id,
        "kernel_count": len(graph.kernels),
        "kernels_by_kind": dict(sorted(by_kind.items())),
        "kernels_by_scope": dict(sorted(by_source.items())),
        "model_id": graph.model_id,
        "state_count": len(graph.states),
        "states_by_class": dict(
            sorted(Counter(s.state_class for s in graph.states).items())
        ),
        "symbol_count": len(graph.symbols),
        "tensor_count": len(graph.tensors),
        "tensors_by_dtype": dict(sorted(dtypes.items())),
        "tensors_by_role": dict(sorted(roles.items())),
    }


__all__ = [
    "ARCHITECTURAL_MAX_CONTEXT",
    "DEFAULT_CHECKPOINT_LOCK",
    "DEFAULT_CONTEXT_TOKENS",
    "DEFAULT_SNAPSHOT",
    "DeepSeekV4KernelIRError",
    "LOWERING_PLAN",
    "NUMERIC_PROFILE",
    "export_deepseek_v4_kernel_graph",
    "graph_census",
    "read_checkpoint_bindings",
    "verify_checkpoint_bindings",
]
