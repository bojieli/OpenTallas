"""Export the pinned Qwen3-8B checkpoint into Tensor Kernel IR v3.

This front end is the only place the Qwen3 forward is expressed for ABI 3.0.
The shared HBM/SRAM backend and the ROM backend consume the one document it
emits, so it must contain complete model semantics and no backend concept:
no memory target, no schedule, no engine instance, no address (ADR-003
section 15, enforced by ``compiler.ir.v3.kernel_ir.check_neutral``).

What it reuses rather than restates:

* ``compiler.qwen3.adapter`` expands and byte-pins the 399 official tensors and
  the exact released configuration;
* ``compiler.qwen3.graph`` supplies the frozen 616-node semantic graph, which
  is used here as an independent cross-check that every checkpoint tensor is
  consumed exactly once and in the layer the released model assigns it;
* ``compiler.frontend.checkpoint`` supplies the hash-locked checkpoint, whose
  shard headers this module re-reads to derive each weight's exact byte range;
  and
* ``compiler.tensor_accelerator.qwen_full_model_semantics`` supplies the
  numeric-contract identity per operation kind, so an ABI 3.0 kernel keeps the
  numeric meaning that was independently qualified for ABI 2.5.

Every weight tensor carries a :class:`CheckpointBinding` naming the shard, the
absolute byte offset (safetensors 8-byte length prefix + header length + the
header's ``data_offsets`` start), the byte length, and the SHA-256 of exactly
those bytes.  A backend turns that into an object source and never materialises
a private copy of the 16 GB weight image.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from compiler.backends.attention_scale import attention_scale_bf16_code
from compiler.frontend.checkpoint import (
    CheckpointError,
    LockedCheckpointReader,
    build_checkpoint_lock,
    load_checkpoint_lock,
    load_checkpoint_source,
)
from compiler.ir.v3.kernel_ir import (
    TOKEN_DTYPE,
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
from compiler.qwen3.adapter import (
    Qwen3AdapterError,
    OFFICIAL_SOURCE_CONTRACT,
    Qwen3SourceContract,
    build_tensor_specs,
    load_official_config,
    load_source_config,
)
from compiler.qwen3.constants import (
    CONFIG_SHA256,
    DEFAULT_CONFIG,
    DEFAULT_SOURCE,
    LAYER_COUNT,
    MODEL_ID,
    PAYLOAD_BYTES,
    REPOSITORY,
    REVISION,
    SESSION_CONTEXT_CAPACITY,
    TARGET_CONTEXT_TOKENS,
    TENSOR_COUNT,
    TRANSFORMERS_VERSION,
)
from compiler.qwen3.graph import build_graph_nodes

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub"
    / "models--Qwen--Qwen3-8B/snapshots"
    / "b968826d9c46dd6066d109eabc6255188de91218"
)
DEFAULT_CHECKPOINT_LOCK = (
    REPOSITORY_ROOT / "build" / "qwen3-8b" / "checkpoint.lock.json"
)

#: Architectural capacity of one session, separate from the 8,000-token
#: acceptance boundary in ``TARGET_CONTEXT_TOKENS``.
MAX_CONTEXT_TOKENS = SESSION_CONTEXT_CAPACITY

NUMERIC_PROFILE = "qwen3_bf16_gqa_target_v1"

#: Numeric identity per neutral kind.  The first ten values are the contracts
#: that ``compiler/tensor_accelerator/qwen_full_model_semantics.py`` already
#: qualified against the released model; the last two name the on-device
#: selection semantics ABI 3.0 adds (ADR-003 section 8.7).
NUMERIC_CONTRACT_BY_KIND: Mapping[str, str] = {
    "ADD": "bf16_add_rne_v1",
    "ARGMAX": "greedy_lowest_token_id_argmax_v1",
    "ATTENTION_GQA": "qwen3_gqa_fp32_softmax_bf16_v1",
    "EMBEDDING_LOOKUP": "bf16_payload_lookup_v1",
    "HEAD_RMS_NORM": "qwen3_rmsnorm_fp32_bf16_v1",
    "KV_APPEND": "bf16_byte_preserving_state_v1",
    "LAST_TOKEN_SELECT": "exact_index_select_v1",
    # Amendment A7: contractions execute under the blocked contract. The
    # sequential contract remains the qualification oracle and the scalar
    # reference, but naming it here would put every deployment on a kernel
    # measured at 0.353 GMAC/s -- 47.6 hours for one 8,000-token prefill.
    "MATMUL": "bf16_bf16_fp32_blocked_rne_v1",
    "RMS_NORM": "qwen3_rmsnorm_fp32_bf16_v1",
    "GATHER": "exact_index_select_v1",
    "ROPE": "qwen3_rope_fp32_bf16_v1",
    "SILU_MUL": "qwen3_silu_mul_bf16_v1",
    "STATE_COMMIT": "bf16_byte_preserving_state_v1",
    "STATE_PREPARE": "bf16_byte_preserving_state_v1",
    "TOKEN_APPEND": "exact_token_append_eos_v1",
    "VOCAB_PROJECT": "bf16_bf16_fp32_blocked_rne_v1",
}

#: Counter namespace per kind, named with the ABI 3.0 counter groups
#: (``runtime.abi3.constants.CounterGroup``) rather than an engine instance.
COUNTER_CLASS_BY_KIND: Mapping[str, str] = {
    "ADD": "vector_reduction",
    "ARGMAX": "selection_eos",
    "ATTENTION_GQA": "attention",
    "EMBEDDING_LOOKUP": "tensor",
    "HEAD_RMS_NORM": "vector_reduction",
    "KV_APPEND": "memory",
    "LAST_TOKEN_SELECT": "memory",
    "MATMUL": "tensor",
    "RMS_NORM": "vector_reduction",
    "GATHER": "memory",
    "ROPE": "vector_reduction",
    "SILU_MUL": "vector_reduction",
    "STATE_COMMIT": "state",
    "STATE_PREPARE": "state",
    "TOKEN_APPEND": "selection_eos",
    "VOCAB_PROJECT": "tensor",
}

#: One Qwen3-8B decoder layer emits exactly these nineteen kernels, so the
#: whole-model census is ``2 + 36 * 20 + 6 == 728``.  See ``KERNEL_CENSUS``.
KERNELS_PER_LAYER = 20

#: Exact kernel census, justified operation by operation:
#:
#: * ``EMBEDDING_LOOKUP`` 1        -- one token embedding gather.
#: * ``RMS_NORM`` 73               -- 36 input + 36 post-attention + 1 final.
#: * ``HEAD_RMS_NORM`` 72          -- Qwen3 normalises every Q and K head.
#: * ``MATMUL`` 252                -- 36 * (q, k, v, o, gate, up, down).
#: * ``ROPE`` 72                   -- Q and K rotate separately (1 output each).
#: * ``STATE_PREPARE`` 36          -- one prepared KV extent per layer.
#: * ``KV_APPEND`` 72              -- the key plane and the value plane are
#:                                  appended by two independent movements.
#: * ``ATTENTION_GQA`` 36          -- one causal GQA per layer.
#: * ``ADD`` 72                    -- attention and MLP residuals per layer.
#: * ``SILU_MUL`` 36               -- one gated MLP activation per layer.
#: * ``LAST_TOKEN_SELECT`` 1       -- final row before the vocabulary head.
#: * ``VOCAB_PROJECT`` 1           -- untied 151,936-way LM head.
#: * ``ARGMAX`` 1                  -- on-device greedy selection.
#: * ``TOKEN_APPEND`` 1            -- token ring write and EOS test.
#: * ``STATE_COMMIT`` 1            -- ONE atomic commit over all 36 resources.
#:
#: The single terminal commit is deliberate: ADR-003 section 8.6 requires a
#: successful commit to be one atomic architectural transition over the
#: request's declared state set, and the frozen 617-operation Model Graph v2
#: has the same single ``state.commit``.  Committing per layer would let an
#: abort expose a partially advanced token position.
KERNEL_CENSUS: Mapping[str, int] = {
    "ADD": 72,
    "GATHER": 1,
    "ARGMAX": 1,
    "ATTENTION_GQA": 36,
    "EMBEDDING_LOOKUP": 1,
    "HEAD_RMS_NORM": 72,
    "KV_APPEND": 72,
    "LAST_TOKEN_SELECT": 1,
    "MATMUL": 252,
    "RMS_NORM": 73,
    "ROPE": 72,
    "SILU_MUL": 36,
    "STATE_COMMIT": 1,
    "STATE_PREPARE": 36,
    "TOKEN_APPEND": 1,
    "VOCAB_PROJECT": 1,
}
KERNEL_COUNT = sum(KERNEL_CENSUS.values())



def kernel_census_for(layers: int) -> dict[str, int]:
    """The exact kernel census for a Qwen3 of ``layers`` layers.

    Every count above is either fixed or a multiple of the layer count, and the
    docstring states the whole-model total as ``2 + 36 * 20 + 6 == 728``.  This
    reproduces that decomposition so the reduced regression model can be
    checked as strictly as the official one instead of not at all.  The module
    self-check below refuses to import if it does not reproduce KERNEL_CENSUS
    at 36 layers, so the official pin still guards the formula.
    """

    return {
        "ADD": 2 * layers,
        "GATHER": 1,
        "ARGMAX": 1,
        "ATTENTION_GQA": layers,
        "EMBEDDING_LOOKUP": 1,
        "HEAD_RMS_NORM": 2 * layers,
        "KV_APPEND": 2 * layers,
        "LAST_TOKEN_SELECT": 1,
        "MATMUL": 7 * layers,
        "RMS_NORM": 2 * layers + 1,
        "ROPE": 2 * layers,
        "SILU_MUL": layers,
        "STATE_COMMIT": 1,
        "STATE_PREPARE": layers,
        "TOKEN_APPEND": 1,
        "VOCAB_PROJECT": 1,
    }


#: 2 request inputs + the pinned weights + 1 generated rotary table
#: + 2 KV views per layer + 19 activations per layer + 5 non-layer activations
#: + 2 outputs.  At 36 layers and 399 weights this is
#: 2 + 399 + 1 + 72 + 684 + 5 + 2 == 1,165, which is TENSOR_TOTAL below; the
#: self-check refuses to import if it is not.
def tensor_total_for(layers: int, weight_count: int) -> int:
    return 2 + weight_count + 1 + 2 * layers + 19 * layers + 5 + 2


if kernel_census_for(36) != dict(KERNEL_CENSUS):
    raise AssertionError(
        "kernel_census_for(36) does not reproduce the official KERNEL_CENSUS"
    )

#: 2 request inputs + 399 weights + 1 generated rotary table + 72 KV views
#: + 689 activations + 2 outputs.  The key and value planes are appended
#: separately, so each layer declares two appended tensors rather than one.
TENSOR_TOTAL = 1165

if tensor_total_for(36, 399) != TENSOR_TOTAL:
    raise AssertionError(
        "tensor_total_for(36, 399) does not reproduce the official TENSOR_TOTAL"
    )

GENERATION_POLICY_ID = "greedy_argmax_lowest_id_first_eos_v1"


class Qwen3KernelIRError(RuntimeError):
    """Raised when the Qwen3 IR v3 export cannot be proven complete."""


# ---------------------------------------------------------------------------
# Checkpoint binding
# ---------------------------------------------------------------------------
def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _locked_file_record(lock: Mapping[str, Any], relative: str) -> Mapping[str, Any]:
    for item in lock["files"]:
        if item["path"] == relative:
            return item
    raise Qwen3KernelIRError(f"checkpoint lock does not cover {relative!r}")


def _authenticated_bytes(
    snapshot: Path, lock: Mapping[str, Any], relative: str
) -> bytes:
    """Read one auxiliary checkpoint file and require its locked SHA-256."""

    record = _locked_file_record(lock, relative)
    path = Path(snapshot) / relative
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise Qwen3KernelIRError(f"cannot read {relative!r}: {exc}") from exc
    if len(payload) != record["size_bytes"]:
        raise Qwen3KernelIRError(f"{relative!r} size differs from the checkpoint lock")
    if hashlib.sha256(payload).hexdigest() != record["sha256"]:
        raise Qwen3KernelIRError(f"{relative!r} differs from the checkpoint lock")
    return payload


def read_checkpoint_bindings(
    snapshot: Path, lock: Mapping[str, Any]
) -> dict[str, CheckpointBinding]:
    """Derive every weight's exact byte range from the real safetensors headers.

    The safetensors payload of a tensor starts at ``8 + header_length +
    data_offsets[0]``: eight bytes of little-endian header length, the JSON
    header itself, then the contiguous data segment.  Each header is
    re-read here and required to match the hash-locked header and tensor
    records, so a binding cannot drift from the locked checkpoint.
    """

    bindings: dict[str, CheckpointBinding] = {}
    for shard in lock["shards"]:
        relative = shard["path"]
        path = Path(snapshot) / relative
        try:
            with path.open("rb") as handle:
                prefix = handle.read(8)
                if len(prefix) != 8:
                    raise Qwen3KernelIRError(f"shard {relative!r} has no header prefix")
                header_length = struct.unpack("<Q", prefix)[0]
                if header_length != shard["header_length_bytes"]:
                    raise Qwen3KernelIRError(
                        f"shard {relative!r} header length differs from the lock"
                    )
                raw_header = handle.read(header_length)
        except OSError as exc:
            raise Qwen3KernelIRError(f"cannot read shard {relative!r}: {exc}") from exc
        if len(raw_header) != header_length:
            raise Qwen3KernelIRError(f"shard {relative!r} header is truncated")
        if hashlib.sha256(raw_header).hexdigest() != shard["header_sha256"]:
            raise Qwen3KernelIRError(
                f"shard {relative!r} header differs from the checkpoint lock"
            )
        try:
            header = json.loads(raw_header.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise Qwen3KernelIRError(
                f"shard {relative!r} header is not valid JSON: {exc}"
            ) from exc
        payload_start = 8 + header_length
        entries = {
            name: value for name, value in header.items() if name != "__metadata__"
        }
        locked = {record["name"]: record for record in shard["tensors"]}
        if set(entries) != set(locked):
            raise Qwen3KernelIRError(
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
                raise Qwen3KernelIRError(
                    f"tensor {name!r} in {relative!r} differs from the checkpoint lock"
                )
            if name in bindings:
                raise Qwen3KernelIRError(f"tensor {name!r} appears in two shards")
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
    graph: KernelGraph,
    *,
    snapshot: Path = DEFAULT_SNAPSHOT,
    lock: Mapping[str, Any] | None = None,
    checkpoint_lock_path: Path = DEFAULT_CHECKPOINT_LOCK,
    tensor_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Read each named binding's bytes back and require its exact SHA-256.

    Every checked binding is hashed twice from independent code paths: once by
    seeking to ``binding.offset`` in the shard, and once through
    :class:`LockedCheckpointReader`, which resolves the tensor from the locked
    header rather than from this document.  Both digests must equal
    ``binding.sha256``.
    """

    if lock is None:
        lock = load_checkpoint_lock(Path(checkpoint_lock_path))
    snapshot = Path(snapshot)
    weights = {
        tensor.tensor_id: tensor
        for tensor in graph.tensors
        if tensor.role == "weight" and tensor.binding is not None
    }
    names = sorted(weights) if tensor_names is None else list(tensor_names)
    checked_bytes = 0
    shards: set[str] = set()
    with LockedCheckpointReader(snapshot, dict(lock)) as reader:
        for name in names:
            tensor = weights.get(name)
            if tensor is None or tensor.binding is None:
                raise Qwen3KernelIRError(f"{name!r} is not a bound weight tensor")
            binding = tensor.binding
            path = snapshot / binding.path
            digest = hashlib.sha256()
            remaining = binding.bytes
            with path.open("rb") as handle:
                handle.seek(binding.offset)
                while remaining:
                    chunk = handle.read(min(remaining, 8 * 1024 * 1024))
                    if not chunk:
                        raise Qwen3KernelIRError(f"short read for binding {name!r}")
                    digest.update(chunk)
                    remaining -= len(chunk)
            if digest.hexdigest() != binding.sha256:
                raise Qwen3KernelIRError(
                    f"binding {name!r} bytes differ from their declared SHA-256"
                )
            locked_digest = hashlib.sha256()
            record = reader.consume_tensor_payload(
                binding.source_name, locked_digest.update
            )
            if locked_digest.hexdigest() != binding.sha256:
                raise Qwen3KernelIRError(
                    f"binding {name!r} differs from the locked checkpoint payload"
                )
            if record["shard"] != binding.path or record["size_bytes"] != binding.bytes:
                raise Qwen3KernelIRError(f"binding {name!r} shard or length differs")
            checked_bytes += binding.bytes
            shards.add(binding.path)
    return {
        "checked_bytes": checked_bytes,
        "checked_tensors": len(names),
        "shards": sorted(shards),
    }


# ---------------------------------------------------------------------------
# Official generation policy
# ---------------------------------------------------------------------------
def official_generation_policy(
    snapshot: Path,
    lock: Mapping[str, Any],
    *,
    maximum_new_tokens: int,
    has_tokenizer: bool = True,
) -> dict[str, Any]:
    """Read the official EOS set from the checkpoint and confirm it two ways.

    ``generation_config.json`` is authoritative for the stop set.  Its ids are
    then confirmed against ``config.json``'s ``eos_token_id`` and against the
    tokenizer: ``tokenizer_config.json`` names the EOS and pad token strings,
    and ``tokenizer.json`` resolves those strings to ids.  No constant from
    this repository is trusted as the source of the EOS set.

    ``has_tokenizer=False`` is for a pinned source that ships no tokenizer --
    the reduced regression model is a synthetic 4,096-entry vocabulary with no
    text side at all.  The AUTHORITATIVE derivation is unchanged: the stop set
    still comes from ``generation_config.json`` and is still cross-checked
    against ``config.json``, so no constant from this repository becomes the
    source.  What is lost is the SECOND confirmation, and it is recorded as
    unavailable in ``eos_tokenizer_confirmation`` -- a key present ONLY when a
    confirmation is missing, so the official graph_id is untouched -- rather
    than skipped quietly;
    ``eos_token_strings`` is empty because a token string that does not exist
    must not be invented to fill a field.
    """

    generation = json.loads(
        _authenticated_bytes(snapshot, lock, "generation_config.json").decode("utf-8")
    )
    config = json.loads(
        _authenticated_bytes(snapshot, lock, "config.json").decode("utf-8")
    )
    if has_tokenizer:
        tokenizer_config = json.loads(
            _authenticated_bytes(
                snapshot, lock, "tokenizer_config.json"
            ).decode("utf-8")
        )
        tokenizer = json.loads(
            _authenticated_bytes(snapshot, lock, "tokenizer.json").decode("utf-8")
        )

    raw = generation.get("eos_token_id")
    ids = [raw] if isinstance(raw, int) and not isinstance(raw, bool) else raw
    if (
        not isinstance(ids, list)
        or not ids
        or any(isinstance(i, bool) or not isinstance(i, int) or i < 0 for i in ids)
        or len(set(ids)) != len(ids)
    ):
        raise Qwen3KernelIRError("generation_config.json has no usable EOS token set")
    vocabulary = int(config["vocab_size"])
    if any(i >= vocabulary for i in ids):
        raise Qwen3KernelIRError("an official EOS id is outside the vocabulary")
    if config.get("eos_token_id") not in ids:
        raise Qwen3KernelIRError("config.json EOS id is not in the official stop set")

    if has_tokenizer:
        by_id = {
            int(item["id"]): item["content"]
            for item in tokenizer.get("added_tokens", [])
            if isinstance(item, dict) and "id" in item and "content" in item
        }
        strings = []
        for token_id in ids:
            content = by_id.get(token_id)
            if content is None:
                raise Qwen3KernelIRError(
                    f"EOS id {token_id} has no tokenizer.json token string"
                )
            strings.append(content)
        declared = {
            tokenizer_config.get("eos_token"),
            tokenizer_config.get("pad_token"),
        } - {None}
        missing = sorted(declared - set(strings))
        if tokenizer_config.get("eos_token") != strings[0] or missing:
            raise Qwen3KernelIRError(
                "tokenizer_config.json stop tokens differ from the official EOS set"
            )
    else:
        strings = []
    if not 1 <= maximum_new_tokens <= MAX_CONTEXT_TOKENS:
        raise Qwen3KernelIRError("maximum_new_tokens is outside the session capacity")
    policy = {
        "eos_token_ids": [int(i) for i in ids],
        "eos_token_strings": strings,
        "eos_source": "generation_config.json",
        "eos_source_sha256": _locked_file_record(
            lock, "generation_config.json"
        )["sha256"],
        "include_eos_in_output": True,
        "maximum_new_tokens": int(maximum_new_tokens),
        "policy_id": GENERATION_POLICY_ID,
        "selection_mode": "greedy_argmax_lowest_id",
        "stop_condition": "first_official_eos_or_maximum_new_tokens",
        "tie_rule": "lowest_token_id",
        "vocabulary_size": vocabulary,
    }
    if not has_tokenizer:
        # Recorded ONLY when it is missing.  Adding it unconditionally would
        # change the official graph_id, and the official Kernel IR digest is
        # certified and referenced by other artefacts -- so the absence of this
        # key is itself the statement that both confirmations ran.
        policy["eos_tokenizer_confirmation"] = (
            "unavailable: this pinned source ships no tokenizer, so the EOS set "
            "is authoritative from generation_config.json and confirmed only "
            "against config.json#eos_token_id"
        )
    return policy


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------
class _Builder:
    """Accumulate tensors and kernels in emission order."""

    def __init__(self) -> None:
        self.tensors: list[Tensor] = []
        self.kernels: list[Kernel] = []
        self._tensor_ids: set[str] = set()
        self.weight_layer: dict[str, int | None] = {}

    def tensor(
        self,
        tensor_id: str,
        dtype: str,
        shape: tuple[Any, ...],
        role: str,
        binding: CheckpointBinding | None = None,
        generator: str = "",
        generator_parameters: Mapping[str, Any] | None = None,
    ) -> str:
        if tensor_id in self._tensor_ids:
            raise Qwen3KernelIRError(f"duplicate tensor {tensor_id!r}")
        self._tensor_ids.add(tensor_id)
        self.tensors.append(
            Tensor(
                tensor_id=tensor_id,
                dtype=dtype,
                shape=shape,
                role=role,
                binding=binding,
                generator=generator,
                generator_parameters=dict(generator_parameters or {}),
            )
        )
        return tensor_id

    def kernel(
        self,
        kernel_id: str,
        kind: str,
        inputs: Sequence[str],
        outputs: Sequence[str],
        *,
        iteration_domain: Mapping[str, Any],
        attributes: Mapping[str, Any],
        source_operation_id: str,
        layer: int | None = None,
        state_reads: Sequence[str] = (),
        state_writes: Sequence[str] = (),
        weights: Sequence[str] = (),
    ) -> None:
        if kind not in KERNEL_TO_ENGINE:
            raise Qwen3KernelIRError(
                f"kernel kind {kind!r} has no ABI 3.0 lowering; the shared table "
                "in compiler/ir/v3/lowering.py is the only place to add one"
            )
        for name in weights:
            if name in self.weight_layer:
                raise Qwen3KernelIRError(f"weight {name!r} has more than one consumer")
            self.weight_layer[name] = layer
        self.kernels.append(
            Kernel(
                index=len(self.kernels),
                kernel_id=kernel_id,
                kind=kind,
                inputs=tuple(inputs),
                outputs=tuple(outputs),
                numeric_contract=NUMERIC_CONTRACT_BY_KIND[kind],
                iteration_domain=dict(iteration_domain),
                attributes=dict(attributes),
                state_reads=tuple(state_reads),
                state_writes=tuple(state_writes),
                counter_class=COUNTER_CLASS_BY_KIND[kind],
                source_operation_id=source_operation_id,
                layer=layer,
            )
        )


def export_qwen3_kernel_graph(
    *,
    snapshot: Path = DEFAULT_SNAPSHOT,
    checkpoint_lock_path: Path = DEFAULT_CHECKPOINT_LOCK,
    config_path: Path = DEFAULT_CONFIG,
    source_path: Path | None = None,
    maximum_new_tokens: int = MAX_CONTEXT_TOKENS,
    build_lock_if_missing: bool = False,
) -> KernelGraph:
    """Export the complete Qwen3-8B forward as one neutral Kernel IR v3 graph."""

    snapshot = Path(snapshot)
    checkpoint_lock_path = Path(checkpoint_lock_path)
    try:
        config, contract = load_source_config(Path(config_path))
        specs = build_tensor_specs(config, contract)
        semantic_nodes = build_graph_nodes(config, contract)
    except Qwen3AdapterError as exc:
        raise Qwen3KernelIRError(f"pinned Qwen3 source contract failed: {exc}") from exc

    if not checkpoint_lock_path.is_file():
        if not build_lock_if_missing:
            raise Qwen3KernelIRError(
                f"checkpoint lock {checkpoint_lock_path} is missing; build it with "
                "compiler.frontend.checkpoint.build_checkpoint_lock first"
            )
        checkpoint_lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock = build_checkpoint_lock(
            snapshot,
            load_checkpoint_source(
                Path(
                    source_path
                    if source_path is not None
                    else contract.checkpoint_source_path
                )
            ),
        )
        checkpoint_lock_path.write_bytes(
            json.dumps(lock, sort_keys=True, separators=(",", ":")).encode("ascii")
            + b"\n"
        )
    try:
        lock = load_checkpoint_lock(checkpoint_lock_path)
    except CheckpointError as exc:
        raise Qwen3KernelIRError(f"invalid Qwen3 checkpoint lock: {exc}") from exc
    if (
        lock["source"]["repository"] != contract.repository
        or lock["source"]["revision"] != contract.revision
        or lock["checkpoint"]["tensor_count"] != contract.tensor_count
        or lock["checkpoint"]["payload_bytes"] != contract.payload_bytes
    ):
        raise Qwen3KernelIRError(
            f"checkpoint lock is not the pinned {contract.name} release"
        )

    bindings = read_checkpoint_bindings(snapshot, lock)
    generation_policy = official_generation_policy(
        snapshot,
        lock,
        maximum_new_tokens=maximum_new_tokens,
        has_tokenizer=contract.has_tokenizer,
    )

    hidden = int(config["hidden_size"])
    intermediate = int(config["intermediate_size"])
    layers = int(config["num_hidden_layers"])
    query_heads = int(config["num_attention_heads"])
    kv_heads = int(config["num_key_value_heads"])
    head_dim = int(config["head_dim"])
    vocabulary = int(config["vocab_size"])
    epsilon = float(config["rms_norm_eps"])
    rope_theta = int(config["rope_theta"])

    span = Symbolic("span_tokens", 1, MAX_CONTEXT_TOKENS)
    context = Symbolic("context_tokens", 1, MAX_CONTEXT_TOKENS)

    builder = _Builder()
    token_ids = builder.tensor("input.token_ids", TOKEN_DTYPE, (span,), "input")
    # Positions index the rotary table, so they are unsigned like every
    # other index in ABI 3.0; a negative position is meaningless.
    positions = builder.tensor("input.positions", "u32", (span,), "input")
    # The rotary coefficient table exists in no checkpoint: it is a derived
    # constant, computed from theta and head_dim. Declaring it with a generator
    # is what lets VECTOR.ROPE's "coefficient rows" operand slot be filled at
    # all -- previously the position vector was passed there, which is a
    # different tensor of a different shape.
    rope_table = builder.tensor(
        "rope.coefficient_table",
        "fp32",
        (MAX_CONTEXT_TOKENS, 2 * head_dim),
        "constant",
        generator="rope_coefficients_v1",
        generator_parameters={
            "head_dim": head_dim,
            "maximum_position": MAX_CONTEXT_TOKENS,
            "theta": float(config["rope_theta"]),
        },
    )
    rope_rows = builder.tensor(
        "rope.coefficient_rows", "fp32", (span, 2 * head_dim), "activation"
    )
    builder.kernel(
        "rope.coefficient_gather",
        "GATHER",
        (positions, rope_table),
        (rope_rows,),
        iteration_domain={"tokens": span, "width": 2 * head_dim},
        attributes={
            "coefficient_layout": "cos_head_dim_then_sin_head_dim",
            "selector": "input.positions",
        },
        source_operation_id="qwen3.rotary_embedding.coefficient_rows",
    )

    weight_shapes: dict[str, tuple[int, ...]] = {}
    for spec in specs:
        if spec.name not in bindings:
            raise Qwen3KernelIRError(f"checkpoint has no payload for {spec.name!r}")
        binding = bindings[spec.name]
        if binding.bytes != spec.size_bytes:
            raise Qwen3KernelIRError(
                f"{spec.name!r} byte length differs from the formula"
            )
        weight_shapes[spec.name] = spec.shape
        builder.tensor(spec.name, "bf16", spec.shape, "weight", binding)
    if len(weight_shapes) != contract.tensor_count or set(bindings) != set(
        weight_shapes
    ):
        raise Qwen3KernelIRError(
            f"weight coverage differs from the pinned {contract.name} "
            f"{contract.tensor_count} tensors"
        )

    states = tuple(
        StateResource(
            state_id=f"key_value_cache.layer.{layer}",
            state_class="kv_cache",
            dtype="bf16",
            # One row holds this layer's key and value for one token.
            row_elements=2 * kv_heads * head_dim,
            capacity_rows=MAX_CONTEXT_TOKENS,
            initialization="zero",
        )
        for layer in range(layers)
    )

    def matmul(
        kernel_id: str,
        source: str,
        weight: str,
        output: str,
        *,
        layer: int | None,
        source_operation_id: str,
        kind: str = "MATMUL",
    ) -> None:
        rows, reduction = weight_shapes[weight]
        builder.kernel(
            kernel_id,
            kind,
            (source, weight),
            (output,),
            iteration_domain={
                "tokens": 1 if kind == "VOCAB_PROJECT" else span,
                "output_width": rows,
                "reduction_width": reduction,
            },
            attributes={
                "accumulator_dtype": "fp32",
                "input_dtype": "bf16",
                "output_dtype": "bf16",
                "output_rounding": "rne",
                "reduction_order": "strictly_increasing_k",
                "transpose_weight": True,
            },
            source_operation_id=source_operation_id,
            layer=layer,
            weights=(weight,),
        )

    def rms_norm(
        kernel_id: str,
        source: str,
        weight: str,
        output: str,
        *,
        width: int,
        layer: int | None,
        source_operation_id: str,
    ) -> None:
        builder.kernel(
            kernel_id,
            "RMS_NORM",
            (source, weight),
            (output,),
            iteration_domain={"tokens": span, "width": width},
            attributes={
                "epsilon": epsilon,
                "final_weight_product": "bf16_multiply_then_bf16_rne",
                "normalization_width": width,
                "normalized_boundary": "bf16_rne_before_weight",
                "reduction_order": "canonical_balanced_binary32_tree",
                "rsqrt": "correctly_rounded_binary32_rne",
            },
            source_operation_id=source_operation_id,
            layer=layer,
            weights=(weight,),
        )

    embedding = builder.tensor(
        "sequence.embedding", "bf16", (span, hidden), "activation"
    )
    builder.kernel(
        "token_embedding",
        "EMBEDDING_LOOKUP",
        (token_ids, "model.embed_tokens.weight"),
        (embedding,),
        iteration_domain={"tokens": span, "width": hidden},
        attributes={
            "index_conversion": "checked_nonnegative_u32",
            "index_dtype": "u32",
            "output_dtype": "bf16",
            "source_index_dtype": "i64",
            "source_index_max_exclusive": vocabulary,
            "source_index_min": 0,
        },
        source_operation_id="model.embed_tokens",
        weights=("model.embed_tokens.weight",),
    )

    residual = embedding
    for layer in range(layers):
        prefix = f"layer.{layer}"
        base = f"model.layers.{layer}"
        state_id = f"key_value_cache.layer.{layer}"

        attention_norm = builder.tensor(
            f"{prefix}.attention_norm", "bf16", (span, hidden), "activation"
        )
        rms_norm(
            f"{prefix}.attention_norm",
            residual,
            f"{base}.input_layernorm.weight",
            attention_norm,
            width=hidden,
            layer=layer,
            source_operation_id=f"{base}.input_layernorm",
        )

        query = builder.tensor(
            f"{prefix}.attention.query",
            "bf16",
            (span, query_heads, head_dim),
            "activation",
        )
        matmul(
            f"{prefix}.attention.query_projection",
            attention_norm,
            f"{base}.self_attn.q_proj.weight",
            query,
            layer=layer,
            source_operation_id=f"{base}.self_attn.q_proj",
        )
        key = builder.tensor(
            f"{prefix}.attention.key",
            "bf16",
            (span, kv_heads, head_dim),
            "activation",
        )
        matmul(
            f"{prefix}.attention.key_projection",
            attention_norm,
            f"{base}.self_attn.k_proj.weight",
            key,
            layer=layer,
            source_operation_id=f"{base}.self_attn.k_proj",
        )
        value = builder.tensor(
            f"{prefix}.attention.value",
            "bf16",
            (span, kv_heads, head_dim),
            "activation",
        )
        matmul(
            f"{prefix}.attention.value_projection",
            attention_norm,
            f"{base}.self_attn.v_proj.weight",
            value,
            layer=layer,
            source_operation_id=f"{base}.self_attn.v_proj",
        )

        for role, heads, source, weight in (
            ("query", query_heads, query, f"{base}.self_attn.q_norm.weight"),
            ("key", kv_heads, key, f"{base}.self_attn.k_norm.weight"),
        ):
            normalized = builder.tensor(
                f"{prefix}.attention.{role}_normalized",
                "bf16",
                (span, heads, head_dim),
                "activation",
            )
            builder.kernel(
                f"{prefix}.attention.{role}_head_norm",
                "HEAD_RMS_NORM",
                (source, weight),
                (normalized,),
                iteration_domain={"tokens": span, "heads": heads, "width": head_dim},
                attributes={
                    "epsilon": epsilon,
                    "final_weight_product": "bf16_multiply_then_bf16_rne",
                    "normalization_width": head_dim,
                    "normalized_boundary": "bf16_rne_before_weight",
                    "reduction_order": "canonical_balanced_binary32_tree",
                    "rsqrt": "correctly_rounded_binary32_rne",
                    "shared_weight_across_heads": True,
                },
                source_operation_id=f"{base}.self_attn.{role[0]}_norm",
                layer=layer,
                weights=(weight,),
            )

        rotated: dict[str, str] = {}
        for role, heads in (("query", query_heads), ("key", kv_heads)):
            output = builder.tensor(
                f"{prefix}.attention.{role}_rotated",
                "bf16",
                (span, heads, head_dim),
                "activation",
            )
            builder.kernel(
                f"{prefix}.attention.{role}_rotation",
                "ROPE",
                (f"{prefix}.attention.{role}_normalized", rope_rows),
                (output,),
                iteration_domain={
                    "tokens": span,
                    "heads": heads,
                    "head_dim": head_dim,
                },
                attributes={
                    "coefficient_dtype": "fp32",
                    "coefficient_layout": "cos_head_dim_then_sin_head_dim",
                    "interleaved": False,
                    "maximum_position": MAX_CONTEXT_TOKENS - 1,
                    "coefficient_source": "rope.coefficient_rows",
                    "rotation": "concat_neg_second_half_first_half",
                    "theta": rope_theta,
                },
                source_operation_id=f"{base}.self_attn.rotary_embedding.{role}",
                layer=layer,
            )
            rotated[role] = output

        builder.kernel(
            f"{prefix}.attention.state_prepare",
            "STATE_PREPARE",
            (),
            (),
            iteration_domain={"tokens": span},
            attributes={
                "append_rows": "span_tokens",
                "generation_check": "exact_expected_generation",
                "transaction_scope": "model_forward_request",
                "visibility": "transaction_private_until_commit",
            },
            source_operation_id=f"{base}.self_attn.past_key_values.prepare",
            layer=layer,
            state_reads=(state_id,),
            state_writes=(state_id,),
        )

        # The key and the value are appended by two independent movements, not
        # one fused operation. That is what the hardware does -- two DMA
        # descriptors into two extents of the prepared state -- and expressing
        # it as one two-operand kernel forced a mapping onto VECTOR.CONVERT,
        # which the engine correctly read as a dequantize and rejected.
        for role, source, rotated_flag in (
            ("key", rotated["key"], True),
            ("value", value, False),
        ):
            appended = builder.tensor(
                f"{prefix}.attention.appended_{role}",
                "bf16",
                (span, kv_heads, head_dim),
                "activation",
            )
            builder.kernel(
                f"{prefix}.attention.{role}_append",
                "KV_APPEND",
                (source, positions),
                (appended,),
                iteration_domain={
                    "tokens": span,
                    "key_value_heads": kv_heads,
                    "head_dim": head_dim,
                },
                attributes={
                    "append_order": "strictly_increasing_position",
                    "plane": role,
                    "row_layout": "key_plane_then_value_plane",
                    "rotated": rotated_flag,
                    "transform": "byte_preserving",
                },
                source_operation_id=(
                    f"{base}.self_attn.past_key_values.update.{role}"
                ),
                layer=layer,
                state_writes=(state_id,),
            )

        key_history = builder.tensor(
            f"{prefix}.attention.key_history",
            "bf16",
            (context, kv_heads, head_dim),
            "state",
        )
        value_history = builder.tensor(
            f"{prefix}.attention.value_history",
            "bf16",
            (context, kv_heads, head_dim),
            "state",
        )
        attention_context = builder.tensor(
            f"{prefix}.attention.context",
            "bf16",
            (span, query_heads, head_dim),
            "activation",
        )
        builder.kernel(
            f"{prefix}.attention.grouped_query",
            "ATTENTION_GQA",
            (rotated["query"], key_history, value_history, positions),
            (attention_context,),
            iteration_domain={
                "tokens": span,
                "context_tokens": context,
                "query_heads": query_heads,
                "key_value_heads": kv_heads,
                "head_dim": head_dim,
            },
            attributes={
                "causal": True,
                "causal_mask_bf16_code": 0xFF7F,
                "probability_dtype": "bf16",
                "query_heads_per_key_value_head": query_heads // kv_heads,
                #: 1/sqrt(head_dim) in BF16.  This was the literal 0x3DB5
                #: sitting beside a head_dim-derived denominator, so the two
                #: agreed only at Qwen3-8B's head width of 128 and the engine
                #: was handed the 8B softmax scale for any other model.
                "scale_bf16_code": attention_scale_bf16_code(head_dim),
                "scale_denominator_sqrt": head_dim,
                "score_reduction_order": "strictly_increasing_head_dimension",
                "sliding_window": False,
                "softmax_compute_dtype": "fp32",
                "value_reduction_order": "strictly_increasing_context",
            },
            source_operation_id=f"{base}.self_attn.eager_attention_forward",
            layer=layer,
            state_reads=(state_id,),
        )

        attention_output = builder.tensor(
            f"{prefix}.attention.output", "bf16", (span, hidden), "activation"
        )
        matmul(
            f"{prefix}.attention.output_projection",
            attention_context,
            f"{base}.self_attn.o_proj.weight",
            attention_output,
            layer=layer,
            source_operation_id=f"{base}.self_attn.o_proj",
        )

        attention_residual = builder.tensor(
            f"{prefix}.attention_residual", "bf16", (span, hidden), "activation"
        )
        builder.kernel(
            f"{prefix}.attention.residual_add",
            "ADD",
            (residual, attention_output),
            (attention_residual,),
            iteration_domain={"tokens": span, "width": hidden},
            attributes={
                "addition": "binary32_rne",
                "input_dtype": "bf16",
                "output_dtype": "bf16",
                "output_rounding": "rne",
                "zero_canonicalization": "positive",
            },
            source_operation_id=f"{base}.residual.self_attn",
            layer=layer,
        )

        feed_forward_norm = builder.tensor(
            f"{prefix}.feed_forward_norm", "bf16", (span, hidden), "activation"
        )
        rms_norm(
            f"{prefix}.feed_forward_norm",
            attention_residual,
            f"{base}.post_attention_layernorm.weight",
            feed_forward_norm,
            width=hidden,
            layer=layer,
            source_operation_id=f"{base}.post_attention_layernorm",
        )

        gate = builder.tensor(
            f"{prefix}.feed_forward.gate",
            "bf16",
            (span, intermediate),
            "activation",
        )
        matmul(
            f"{prefix}.feed_forward.gate_projection",
            feed_forward_norm,
            f"{base}.mlp.gate_proj.weight",
            gate,
            layer=layer,
            source_operation_id=f"{base}.mlp.gate_proj",
        )
        up = builder.tensor(
            f"{prefix}.feed_forward.up",
            "bf16",
            (span, intermediate),
            "activation",
        )
        matmul(
            f"{prefix}.feed_forward.up_projection",
            feed_forward_norm,
            f"{base}.mlp.up_proj.weight",
            up,
            layer=layer,
            source_operation_id=f"{base}.mlp.up_proj",
        )
        activated = builder.tensor(
            f"{prefix}.feed_forward.activated",
            "bf16",
            (span, intermediate),
            "activation",
        )
        builder.kernel(
            f"{prefix}.feed_forward.activation",
            "SILU_MUL",
            (gate, up),
            (activated,),
            iteration_domain={"tokens": span, "width": intermediate},
            attributes={
                "activation_boundary": "bf16_rne_before_up_multiply",
                "exponential": "correctly_rounded_binary32_rne",
                "input_dtype": "bf16",
                "output_dtype": "bf16",
                "output_rounding": "rne",
                "sigmoid": "stable_sign_selected_binary32",
                "zero_canonicalization": "positive",
            },
            source_operation_id=f"{base}.mlp.act_fn",
            layer=layer,
        )
        feed_forward_output = builder.tensor(
            f"{prefix}.feed_forward.output", "bf16", (span, hidden), "activation"
        )
        matmul(
            f"{prefix}.feed_forward.down_projection",
            activated,
            f"{base}.mlp.down_proj.weight",
            feed_forward_output,
            layer=layer,
            source_operation_id=f"{base}.mlp.down_proj",
        )
        layer_output = builder.tensor(
            f"{prefix}.residual", "bf16", (span, hidden), "activation"
        )
        builder.kernel(
            f"{prefix}.feed_forward.residual_add",
            "ADD",
            (attention_residual, feed_forward_output),
            (layer_output,),
            iteration_domain={"tokens": span, "width": hidden},
            attributes={
                "addition": "binary32_rne",
                "input_dtype": "bf16",
                "output_dtype": "bf16",
                "output_rounding": "rne",
                "zero_canonicalization": "positive",
            },
            source_operation_id=f"{base}.residual.mlp",
            layer=layer,
        )
        residual = layer_output

    final_norm = builder.tensor(
        "sequence.final_norm", "bf16", (span, hidden), "activation"
    )
    rms_norm(
        "final_norm",
        residual,
        "model.norm.weight",
        final_norm,
        width=hidden,
        layer=None,
        source_operation_id="model.norm",
    )
    last_token = builder.tensor(
        "sequence.last_token", "bf16", (1, hidden), "activation"
    )
    builder.kernel(
        "last_token_select",
        "LAST_TOKEN_SELECT",
        (final_norm, positions),
        (last_token,),
        iteration_domain={"tokens": span, "width": hidden},
        attributes={
            "index_dtype": "u32",
            "input_dtype": "bf16",
            "output_dtype": "bf16",
            "selection": "last_logical_row",
        },
        source_operation_id="model.forward.logits_to_keep",
    )
    logits = builder.tensor("output.logits", "bf16", (1, vocabulary), "output")
    matmul(
        "vocabulary_projection",
        last_token,
        "lm_head.weight",
        logits,
        layer=None,
        source_operation_id="lm_head",
        kind="VOCAB_PROJECT",
    )
    selected = builder.tensor("output.selected_token", TOKEN_DTYPE, (1,), "activation")
    builder.kernel(
        "token_selection",
        "ARGMAX",
        (logits,),
        (selected,),
        iteration_domain={"tokens": 1, "width": vocabulary},
        attributes={
            "compare_dtype": "bf16",
            "index_dtype": "u32",
            "selection_mode": "greedy_argmax_lowest_id",
            "tie_rule": "lowest_token_id",
        },
        source_operation_id="generation.greedy_select",
    )
    next_token = builder.tensor("output.next_token", TOKEN_DTYPE, (1,), "output")
    builder.kernel(
        "token_append",
        "TOKEN_APPEND",
        (selected,),
        (next_token,),
        iteration_domain={"tokens": 1},
        attributes={
            "advance_generation_cursor": True,
            "eos_test": "official_eos_token_set",
            "generation_policy": GENERATION_POLICY_ID,
            "vocabulary_check": "exact_tokenizer_vocabulary",
        },
        source_operation_id="generation.token_append",
    )
    state_ids = tuple(state.state_id for state in states)
    builder.kernel(
        "state_commit",
        "STATE_COMMIT",
        (),
        (),
        iteration_domain={"state_count": len(states)},
        attributes={
            "atomic": True,
            "coverage": "complete_request_state_set",
            "generation_increment": 1,
            "transaction_scope": "model_forward_request",
        },
        source_operation_id="generation.state_commit",
        state_reads=state_ids,
        state_writes=state_ids,
    )

    _cross_check_semantic_graph(builder, semantic_nodes)

    entrypoint_inputs = (token_ids, positions)
    entrypoint_outputs = (logits, next_token)
    graph = KernelGraph(
        model_id=contract.model_id,
        source={
            "architecture": str(config["model_type"]),
            "checkpoint_lock_id": lock["lock_id"],
            "config_sha256": contract.released_config_sha256,
            "exporter": "compiler.frontends.v3.qwen3",
            "head_dim": head_dim,
            "hidden_size": hidden,
            "intermediate_size": intermediate,
            "key_value_heads": kv_heads,
            "layer_count": layers,
            "maximum_position_embeddings": int(config["max_position_embeddings"]),
            "payload_bytes": contract.payload_bytes,
            "query_heads": query_heads,
            "repository": contract.repository,
            "revision": contract.revision,
            "rms_norm_epsilon": epsilon,
            "rope_theta": rope_theta,
            "session_context_capacity": MAX_CONTEXT_TOKENS,
            "target_context_tokens": TARGET_CONTEXT_TOKENS,
            "tensor_content_sha256": lock["checkpoint"]["tensor_content_sha256"],
            "tensor_count": contract.tensor_count,
            "transformers_version": TRANSFORMERS_VERSION,
            "vocabulary_size": vocabulary,
        },
        symbols=(
            RuntimeSymbol(
                name="span_tokens",
                minimum=1,
                maximum=MAX_CONTEXT_TOKENS,
                multiple_of=1,
                binding="request",
            ),
            RuntimeSymbol(
                name="context_tokens",
                minimum=1,
                maximum=MAX_CONTEXT_TOKENS,
                multiple_of=1,
                binding="request",
            ),
        ),
        tensors=tuple(builder.tensors),
        states=states,
        kernels=tuple(builder.kernels),
        entrypoints=(
            Entrypoint(
                phase="prefill",
                inputs=entrypoint_inputs,
                outputs=entrypoint_outputs,
                states=state_ids,
                generation_policy=GENERATION_POLICY_ID,
            ),
            Entrypoint(
                phase="decode",
                inputs=entrypoint_inputs,
                outputs=entrypoint_outputs,
                states=state_ids,
                generation_policy=GENERATION_POLICY_ID,
            ),
        ),
        numeric_profile=NUMERIC_PROFILE,
        generation_policy=generation_policy,
    )
    _require_complete(graph, contract)
    return graph


def _cross_check_semantic_graph(builder: _Builder, nodes: Iterable[Any]) -> None:
    """Require the frozen 616-node semantic graph's weight use to be reproduced."""

    expected: dict[str, int | None] = {}
    for node in nodes:
        for name in node.tensors:
            if name in expected:
                raise Qwen3KernelIRError(
                    f"semantic graph uses {name!r} more than once"
                )
            expected[name] = node.layer
    if builder.weight_layer != expected:
        differing = sorted(
            name
            for name in set(expected) | set(builder.weight_layer)
            if expected.get(name, "?") != builder.weight_layer.get(name, "?")
        )
        raise Qwen3KernelIRError(
            "kernel graph weight use differs from the frozen semantic graph: "
            f"{differing[:8]}"
        )


def _require_complete(
    graph: KernelGraph,
    contract: Qwen3SourceContract = OFFICIAL_SOURCE_CONTRACT,
) -> None:
    layers = contract.layer_count
    expected_census = kernel_census_for(layers)
    expected_tensors = tensor_total_for(layers, contract.tensor_count)
    errors = check_neutral(graph)
    if errors:
        raise Qwen3KernelIRError("neutral IR rejected:\n  " + "\n  ".join(errors))
    census = dict(sorted(Counter(k.kind for k in graph.kernels).items()))
    if census != dict(sorted(expected_census.items())):
        raise Qwen3KernelIRError(f"kernel census differs: {census}")
    if len(graph.tensors) != expected_tensors:
        raise Qwen3KernelIRError(
            f"tensor count is {len(graph.tensors)}, expected {expected_tensors}"
        )
    if len(graph.states) != layers:
        raise Qwen3KernelIRError("one KV state resource per layer is required")
    bound = [t for t in graph.tensors if t.role == "weight"]
    if len(bound) != contract.tensor_count or any(t.binding is None for t in bound):
        raise Qwen3KernelIRError(
            f"every one of the {contract.tensor_count} weights must carry a binding"
        )
    unknown = sorted({k.kind for k in graph.kernels} - set(KERNEL_TO_ENGINE))
    if unknown:
        raise Qwen3KernelIRError(f"kinds without an ABI 3.0 lowering: {unknown}")
    written = {s for k in graph.kernels for s in k.state_writes}
    read = {s for k in graph.kernels for s in k.state_reads}
    declared = {s.state_id for s in graph.states}
    if written != declared or read != declared:
        raise Qwen3KernelIRError("every KV state resource must be read and written")


__all__ = [
    "DEFAULT_CHECKPOINT_LOCK",
    "DEFAULT_SNAPSHOT",
    "GENERATION_POLICY_ID",
    "KERNEL_CENSUS",
    "KERNEL_COUNT",
    "MAX_CONTEXT_TOKENS",
    "NUMERIC_CONTRACT_BY_KIND",
    "NUMERIC_PROFILE",
    "Qwen3KernelIRError",
    "TENSOR_TOTAL",
    "export_qwen3_kernel_graph",
    "official_generation_policy",
    "read_checkpoint_bindings",
    "verify_checkpoint_bindings",
]
