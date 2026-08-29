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
        self.bound_bytes = 0

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
        if binding is not None:
            self.bound_bytes += binding.bytes
        return tensor_id

    def has_tensor(self, tensor_id: str) -> bool:
        return tensor_id in self._tensor_ids

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
