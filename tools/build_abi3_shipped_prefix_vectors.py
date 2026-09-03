#!/usr/bin/env python3
"""Build the smallest honest shipped-program sequencer/engine RTL witness.

The four shipped ABI 3.0 decode entrypoints all begin with a bounded sequence
that the RTL can execute without pretending an unsupported model operator
exists: generated-row ``DMA.GATHER`` operations, one checkpoint-backed
``TENSOR.EMBED_LOOKUP``, then Qwen ``VECTOR.RMS_NORM`` or DeepSeek
stride-zero ``DMA.TRANSFER``.  Row movement lowers to the existing index
mover; RMSNorm uses the independently correlated exact arithmetic slice.

This generator retains those exact program and descriptor identities, resolves
their real views for the same 16-token decode request used by the deployment
campaign, materialises only the selected generated RoPE rows, and performs
bounded reads of token zero's BF16 checkpoint row and Qwen's layer-zero gain.
The hardware must produce every retained result word, then fail closed at the
exact next unsupported instruction.  It does not claim a whole model,
prefill, token selection, or decoding result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import (  # noqa: E402
    Control,
    Dma,
    DType,
    Major,
    NO_ID,
    Tensor,
    Vector,
)
from runtime.abi3.deployment import Deployment, resolve_path  # noqa: E402
from runtime.abi3.descriptors import (  # noqa: E402
    ExtendedDescriptorType,
    SelectorKind,
    Symbol,
)
from runtime.abi3.records import decode_body, split_program  # noqa: E402
from runtime.sim.generators import _rope_frequencies_binary32  # noqa: E402
from runtime.sim.memory import ViewResolver  # noqa: E402
from runtime.reference.tensor_accelerator_rmsnorm import (  # noqa: E402
    rms_norm_bf16,
)
from tools.build_abi3_deployment_rtl_vectors import (  # noqa: E402
    CASE_STRIDE as DEPLOYMENT_CASE_STRIDE,
    TARGETS,
    certified_deployment_identity,
)


OUTPUT_DIR = ROOT / "testdata/compiler/abi3_shipped_prefix"
DEPLOYMENT_VECTOR_DIR = ROOT / "testdata/compiler/abi3_deployment"
DEPLOYMENT_VECTOR_JSON = (
    DEPLOYMENT_VECTOR_DIR / "abi3_deployment_rtl_vectors.json"
)

VECTOR_SCHEMA = "opentallas.rtl.abi3_shipped_prefix_vectors.v1"
CASE_STRIDE = 48
META_WORDS = 16
INDEX_WORDS = 64
SOURCE_WORDS = 65536
RESULT_WORDS = 65536
PROMPT_TOKENS = 16
INDEX_VALUE = 16
EMBED_TOKEN = 0
EMBED_WIDTH = 4096
EXACT_INDEX_SELECT = hashlib.sha256(b"exact_index_select_v1").digest()
QWEN_EMBED_CONTRACT = hashlib.sha256(b"bf16_payload_lookup_v1").digest()
DEEPSEEK_EMBED_CONTRACT = hashlib.sha256(
    b"lookup_bf16_token_embedding_v1"
).digest()
QWEN_RMS_CONTRACT = hashlib.sha256(
    b"qwen3_rmsnorm_fp32_bf16_v1"
).digest()
DEEPSEEK_TRANSFER_CONTRACT = hashlib.sha256(
    b"structural_hc_expand_bf16_v1"
).digest()
EMBED_DESCRIPTOR_IDS = (41, 54, 356, 527)
RMS_DESCRIPTOR_IDS = (50, 64)
TRANSFER_DESCRIPTOR_IDS = (363, 532)
NEXT_BOUNDARIES = (
    (11, int(Major.TENSOR), int(Tensor.MATMUL), 59, "TENSOR.MATMUL"),
    (11, int(Major.TENSOR), int(Tensor.MATMUL), 72, "TENSOR.MATMUL"),
    (13, int(Major.LINK), 3, 368, "LINK.MULTICAST"),
    (14, int(Major.VECTOR), int(Vector.MHC), 546, "VECTOR.MHC"),
)

INPUT_IMAGES = (
    "a3_program.hex",
    "a3_descriptor.hex",
    "a3_symbol.hex",
)
OUTPUT_IMAGES = (
    "p3_case.hex",
    "p3_issue.hex",
    "p3_index.hex",
    "p3_source.hex",
    "p3_expect.hex",
    "p3_meta.hex",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hex_lines(
    values: list[int], width: int = 32, total: int | None = None
) -> str:
    if total is not None:
        if len(values) > total:
            raise SystemExit(
                f"image has {len(values)} words, exceeds its {total}-word RTL bound"
            )
        values = values + [0] * (total - len(values))
    digits = width // 4
    return "".join(f"{value & ((1 << width) - 1):0{digits}x}\n" for value in values)


def _deployment_vectors() -> tuple[dict[str, Any], list[int]]:
    if not DEPLOYMENT_VECTOR_JSON.is_file():
        raise SystemExit(
            "the shipped deployment vector set is missing; run "
            "tools/build_abi3_deployment_rtl_vectors.py"
        )
    vectors = json.loads(DEPLOYMENT_VECTOR_JSON.read_text(encoding="utf-8"))
    if vectors.get("schema") != "opentallas.rtl.abi3_deployment_vectors.v1":
        raise SystemExit("the shipped deployment vector set has an unknown schema")
    if vectors.get("prompt_tokens") != PROMPT_TOKENS:
        raise SystemExit(
            f"the shipped vector request has {vectors.get('prompt_tokens')} prompt "
            f"tokens; this witness requires {PROMPT_TOKENS}"
        )
    for name in INPUT_IMAGES:
        expected = vectors.get("image_sha256", {}).get(name)
        actual = _sha256_file(DEPLOYMENT_VECTOR_DIR / name)
        if actual != expected:
            raise SystemExit(
                f"{name} is not the image bound by {DEPLOYMENT_VECTOR_JSON}"
            )
    case_path = DEPLOYMENT_VECTOR_DIR / "a3_deployment_case.hex"
    expected_case = vectors.get("image_sha256", {}).get(case_path.name)
    if _sha256_file(case_path) != expected_case:
        raise SystemExit("the shipped deployment case image is stale")
    case_words = [
        int(line, 16)
        for line in case_path.read_text(encoding="ascii").splitlines()
        if line.strip()
    ]
    if len(case_words) != len(vectors["cases"]) * DEPLOYMENT_CASE_STRIDE:
        raise SystemExit("the shipped deployment case image has the wrong length")
    return vectors, case_words


def _resolved_views(
    deployment: Deployment,
    operator_id: int,
    loops: dict[int, int],
    symbols: dict[int, int],
    *,
    major: int,
) -> list[dict[str, Any]]:
    if major == int(Major.LINK):
        # LINK descriptors are COMMUNICATION records, not OPERATOR records,
        # and do not own tensor-view operands at the sequencer boundary.
        return []
    operator = deployment.table.get(
        operator_id, ExtendedDescriptorType.OPERATOR
    )
    resolver = ViewResolver(deployment, None)  # resolution does not read memory
    out: list[dict[str, Any]] = []
    fields = (
        "input_view_0",
        "input_view_1",
        "input_view_2",
        "input_view_3",
        "output_view_0",
        "output_view_1",
    )
    for slot, field in enumerate(fields):
        view_id = int(operator.payload[field])
        if view_id == NO_ID:
            continue
        resolved = resolver.resolve(view_id, loops, symbols)
        out.append(
            {
                "slot": slot,
                "descriptor_id": view_id,
                "object_id": int(resolved.object_id),
                "dtype": int(resolved.dtype),
                "dims": [int(value) for value in resolved.dims],
                "strides": [int(value) for value in resolved.strides],
                "element_offset": int(resolved.element_offset),
                "extent_axis": int(resolved.extent_axis),
                "extent": int(resolved.dims[resolved.extent_axis]),
            }
        )
    return out


def _loop_trip(payload: dict[str, Any], symbols: dict[int, int]) -> int:
    kind = int(payload["bound_selector_kind"])
    lower = int(payload["lower_bound"])
    step = int(payload["step"])
    if step <= 0:
        raise SystemExit("shipped prefix contains a non-positive loop step")
    if kind == int(SelectorKind.CONSTANT):
        upper = int(payload["upper_bound"])
    elif kind == int(SelectorKind.RUNTIME_SYMBOL):
        symbol = int(payload["bound_symbol_id"])
        if symbol not in symbols:
            raise SystemExit(f"shipped prefix loop names unbound symbol {symbol}")
        divisor = max(int(payload["bound_divisor"]), 1)
        upper = (int(symbols[symbol]) + divisor - 1) // divisor
    else:
        raise SystemExit("shipped prefix loop uses an unsupported selector")
    span = max(upper - lower, 0)
    return (span + step - 1) // step


def _generated_row(
    deployment: Deployment,
    object_id: int,
    index: int,
    trailing: int,
    cache: dict[tuple[str, int, int], bytes],
) -> tuple[bytes, dict[str, Any]]:
    """Materialise one generator row without allocating its complete table.

    The DeepSeek coefficient object is 128 MiB.  Generating all 262,144 rows
    to retain the one 512-byte row this RTL witness reads would make a focused
    vector rebuild contend with model-capture jobs.  These expressions are the
    selected-row forms of ``runtime.sim.generators`` and are source-bound by
    the campaign.  The retained row hashes remain byte-identical to the normal
    full-object generator boundary.
    """
    source = deployment.objects[object_id]
    if source.kind != "generated":
        raise SystemExit(
            f"source object {object_id} is {source.kind}, expected generated"
        )
    key = (source.digest, index, trailing)
    row = cache.get(key)
    if row is None:
        parameters = source.parameters
        if source.generator == "rope_coefficients_v1":
            head_dim = int(parameters["head_dim"])
            if trailing != 2 * head_dim:
                raise SystemExit("Qwen generated-row width changed")
            half = head_dim // 2
            theta = float(parameters["theta"])
            inverse = np.array(
                [
                    1.0 / (theta ** ((2.0 * channel) / head_dim))
                    for channel in range(half)
                ],
                dtype=np.float64,
            )
            angles = np.float64(index) * inverse
            cosine = np.cos(angles)
            sine = np.sin(angles)
            values = np.empty(trailing, dtype=np.float64)
            values[:half] = cosine
            values[half:head_dim] = cosine
            values[head_dim : head_dim + half] = sine
            values[head_dim + half :] = sine
            row = np.ascontiguousarray(values, dtype=np.float32).tobytes()
        elif source.generator == "deepseek_rope_coefficients_v1":
            rotary_width = int(parameters["rotary_width"])
            if trailing != 2 * rotary_width:
                raise SystemExit("DeepSeek generated-row width changed")
            frequencies = _rope_frequencies_binary32(
                parameters,
                rotary_width=rotary_width,
                theta=float(parameters["theta"]),
                scaling=str(parameters["position_scaling"]),
            )
            angles = np.asarray(
                np.float32(index) * frequencies, dtype=np.float32
            )
            cosine = np.asarray(
                np.cos(np.asarray(angles, dtype=np.float64)), dtype=np.float32
            )
            sine = np.asarray(
                np.sin(np.asarray(angles, dtype=np.float64)), dtype=np.float32
            )
            values = np.empty(trailing, dtype=np.float32)
            values[0:rotary_width:2] = cosine
            values[1:rotary_width:2] = cosine
            values[rotary_width::2] = sine
            values[rotary_width + 1 :: 2] = sine
            row = np.ascontiguousarray(values, dtype=np.float32).tobytes()
        else:
            raise SystemExit(
                f"unsupported selected-row generator {source.generator!r}"
            )
        cache[key] = row
    if len(row) != trailing * 4:
        raise SystemExit("generated source row has the wrong byte count")
    return row, {
        "object_id": object_id,
        "kind": source.kind,
        "generator": source.generator,
        "parameters": dict(source.parameters),
        "object_sha256": source.digest,
        "row_index": index,
        "row_bytes": len(row),
        "row_sha256": hashlib.sha256(row).hexdigest(),
    }


def _checkpoint_row(
    target: Any,
    deployment: Deployment,
    object_id: int,
    token: int,
    width: int,
) -> tuple[bytes, dict[str, Any]]:
    """Read one BF16 row from the exact segment named by the deployment.

    This deliberately performs a bounded 8 KiB read.  The deployment and its
    retained certificate bind the complete segment digest; this witness binds
    the selected bytes again by their own SHA-256, but does not rescan a 1--4
    GiB checkpoint shard while another model-capture process is live.
    """
    source = deployment.objects[object_id]
    if source.kind != "segments":
        raise SystemExit(
            f"embedding object {object_id} is {source.kind}, expected segments"
        )
    row_bytes = width * 2
    logical_start = token * row_bytes
    logical_stop = logical_start + row_bytes
    cursor = 0
    selected = None
    selected_local = 0
    for segment in source.segments:
        stop = cursor + int(segment.bytes)
        if cursor <= logical_start and logical_stop <= stop:
            selected = segment
            selected_local = logical_start - cursor
            break
        cursor = stop
    if selected is None:
        raise SystemExit(
            f"embedding row {token} spans or exceeds declared source segments"
        )
    root = Path(target.checkpoint).expanduser()
    path = resolve_path(root, selected.path)
    file_offset = int(selected.offset) + selected_local
    if file_offset + row_bytes > path.stat().st_size:
        raise SystemExit("selected embedding row exceeds its checkpoint shard")
    with path.open("rb") as handle:
        handle.seek(file_offset)
        row = handle.read(row_bytes)
    if len(row) != row_bytes:
        raise SystemExit("checkpoint returned a short embedding row")
    memory = deployment.table.get(
        object_id, ExtendedDescriptorType.MEMORY_OBJECT
    )
    object_digest = bytes(memory.payload["content_digest"]).hex()
    if not object_digest or object_digest == "00" * 32:
        raise SystemExit("embedding MEMORY_OBJECT has no content digest")
    return row, {
        "object_id": object_id,
        "object_content_sha256": object_digest,
        "checkpoint_revision": root.name,
        "shard": selected.path,
        "declared_segment_offset": int(selected.offset),
        "declared_segment_bytes": int(selected.bytes),
        "declared_segment_sha256": str(selected.sha256),
        "selected_token_id": token,
        "selected_row_logical_offset": logical_start,
        "selected_row_segment_offset": selected_local,
        "selected_row_file_offset": file_offset,
        "selected_row_bytes": row_bytes,
        "selected_row_file_range": {
            "start": file_offset,
            "stop_exclusive": file_offset + row_bytes,
        },
        "selected_row_sha256": hashlib.sha256(row).hexdigest(),
        "authentication_boundary": (
            "only this selected byte range was re-read and hashed; complete "
            "segment identity and its declared SHA-256 are bound by the "
            "certified deployment but the complete segment was not rehashed"
        ),
    }


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)

    deployment_vectors, deployment_case_words = _deployment_vectors()
    deployment_cases = deployment_vectors["cases"]
    deployment_records = {
        entry["key"]: entry for entry in deployment_vectors["deployments"]
    }

    case_words: list[int] = []
    issue_words: list[int] = []
    index_words: list[int] = []
    source_words: list[int] = []
    expected_words: list[int] = []
    records: list[dict[str, Any]] = []
    row_cache: dict[tuple[str, int, int], bytes] = {}
    total_launches = 0
    total_gathers = 0
    total_embeddings = 0
    total_rms_norms = 0
    total_transfers = 0
    total_rope_words = 0
    total_rms_words = 0
    total_transfer_words = 0
    total_embedding_checkpoint_bytes = 0
    total_rms_checkpoint_bytes = 0
    total_checkpoint_bytes = 0
    total_views = 0

    for target_index, target in enumerate(TARGETS):
        case_name = f"{target.key}/decode"
        matches = [
            (index, case)
            for index, case in enumerate(deployment_cases)
            if case.get("name") == case_name
        ]
        if len(matches) != 1:
            raise SystemExit(f"expected one shipped case named {case_name}")
        deployment_case_index, deployment_case = matches[0]
        base = deployment_case_index * DEPLOYMENT_CASE_STRIDE
        source_case = deployment_case_words[base : base + DEPLOYMENT_CASE_STRIDE]

        expected_identity = certified_deployment_identity(target)
        deployment = Deployment.read(ROOT / target.deployment)
        deployment_sha = deployment.deployment_digest.hex()
        if deployment_sha != expected_identity.deployment_sha256:
            raise SystemExit(f"{target.key}: deployment certificate is stale")
        if deployment_sha != deployment_case["deployment_sha256"]:
            raise SystemExit(f"{target.key}: shipped RTL vectors are stale")
        deployment_record = deployment_records[target.key]
        if deployment_record["deployment_sha256"] != deployment_sha:
            raise SystemExit(f"{target.key}: deployment identity disagreement")

        _, body = split_program(deployment.program)
        instructions = decode_body(body)
        entry = next(
            item
            for item in deployment.entrypoints
            if int(item["entrypoint_id"]) == 1
        )
        entry_pc = int(entry["first_instruction"])
        if entry_pc != int(source_case[7]):
            raise SystemExit(f"{target.key}: decode entry PC changed")

        symbols = {
            int(key): int(value)
            for key, value in deployment_case["symbols"].items()
        }
        if symbols[int(Symbol.POSITION_START)] != INDEX_VALUE:
            raise SystemExit(
                f"{target.key}: decode position is not {INDEX_VALUE}"
            )

        loops: dict[int, int] = {}
        gathers: list[dict[str, Any]] = []
        embeddings: list[dict[str, Any]] = []
        rms_norms: list[dict[str, Any]] = []
        transfers: list[dict[str, Any]] = []
        prefix_views: list[dict[str, Any]] = []
        fetched = retired = issued = loop_iterations = wait_events = signals = 0
        unsupported: dict[str, Any] | None = None
        pc = entry_pc
        while pc < len(instructions):
            instruction = instructions[pc]
            fetched += 1
            major = int(instruction.major)
            sub = int(instruction.sub)
            if major == int(Major.CONTROL):
                if sub == int(Control.LOOP_SETUP):
                    loop_id = int(instruction.control_id)
                    descriptor = deployment.table.get(
                        loop_id, ExtendedDescriptorType.LOOP_CONTROL
                    )
                    trip = _loop_trip(descriptor.payload, symbols)
                    if trip == 0:
                        raise SystemExit(
                            f"{target.key}: prefix loop {loop_id} is empty"
                        )
                    loops[loop_id] = int(descriptor.payload["lower_bound"])
                elif sub == int(Control.LOOP_NEXT):
                    loop_id = int(instruction.control_id)
                    if loop_id not in loops:
                        raise SystemExit(f"{target.key}: unmatched LOOP_NEXT")
                    del loops[loop_id]
                    loop_iterations += 1
                else:
                    raise SystemExit(
                        f"{target.key}: unexpected CONTROL.{sub:#x} in prefix"
                    )
                if int(instruction.signal_event_id) != NO_ID:
                    signals += 1
                retired += 1
                pc += 1
                continue

            issued += 1
            resolved = _resolved_views(
                deployment,
                int(instruction.descriptor_id),
                loops,
                symbols,
                major=major,
            )
            prefix_views.extend({"pc": pc, **view} for view in resolved)
            if int(instruction.wait_set_id) != NO_ID:
                wait_events += 1
            if major == int(Major.DMA) and sub == int(Dma.GATHER):
                if int(instruction.wait_set_id) != NO_ID:
                    raise SystemExit(f"{target.key}: gather unexpectedly waits")
                operator = deployment.table.get(
                    int(instruction.descriptor_id), ExtendedDescriptorType.OPERATOR
                )
                payload = operator.payload
                if [view["slot"] for view in resolved] != [0, 1, 4]:
                    raise SystemExit(f"{target.key}: gather arity changed")
                by_slot = {int(view["slot"]): view for view in resolved}
                index_view = by_slot[0]
                source_view = by_slot[1]
                output_view = by_slot[4]
                if (
                    index_view["dtype"] != int(DType.U32)
                    or index_view["dims"] != [1]
                    or source_view["dtype"] != int(DType.FP32)
                    or output_view["dtype"] != int(DType.FP32)
                    or len(source_view["dims"]) != 2
                    or output_view["dims"]
                    != [1, int(source_view["dims"][1])]
                ):
                    raise SystemExit(f"{target.key}: gather shape changed")
                numeric_id = int(payload["numeric_profile_id"])
                numeric = deployment.table.get(
                    numeric_id, ExtendedDescriptorType.NUMERIC
                )
                if bytes(numeric.payload["contract_digest"]) != EXACT_INDEX_SELECT:
                    raise SystemExit(f"{target.key}: gather contract changed")
                trailing = int(source_view["dims"][1])
                row, source_identity = _generated_row(
                    deployment,
                    int(source_view["object_id"]),
                    INDEX_VALUE,
                    trailing,
                    row_cache,
                )
                row_words = [
                    int.from_bytes(row[offset : offset + 4], "little")
                    for offset in range(0, len(row), 4)
                ]
                gathers.append(
                    {
                        "kind": "dma_gather",
                        "pc": pc,
                        "descriptor_id": int(instruction.descriptor_id),
                        "numeric_profile_id": numeric_id,
                        "index_view": index_view,
                        "source_view": source_view,
                        "output_view": output_view,
                        "numeric_input_dtype": int(numeric.payload["input_dtype"]),
                        "contract": "exact_index_select_v1",
                        "contract_sha256": EXACT_INDEX_SELECT.hex(),
                        "source": source_identity,
                        "expected_row_sha256": hashlib.sha256(row).hexdigest(),
                        "_source_words": row_words,
                        "_expected_words": [
                            int.from_bytes(row[offset : offset + 4], "little")
                            for offset in range(0, len(row), 4)
                        ],
                    }
                )
                if int(instruction.signal_event_id) != NO_ID:
                    signals += 1
                retired += 1
                pc += 1
                continue

            if major == int(Major.TENSOR) and sub == int(Tensor.EMBED_LOOKUP):
                if int(instruction.wait_set_id) != NO_ID:
                    raise SystemExit(
                        f"{target.key}: embedding lookup unexpectedly waits"
                    )
                operator = deployment.table.get(
                    int(instruction.descriptor_id),
                    ExtendedDescriptorType.OPERATOR,
                )
                payload = operator.payload
                if (
                    int(instruction.descriptor_id)
                    != EMBED_DESCRIPTOR_IDS[target_index]
                    or int(payload["engine_family"]) != major
                    or int(payload["engine_sub"]) != sub
                    or int(payload["numeric_profile_id"]) == NO_ID
                    or [view["slot"] for view in resolved] != [0, 1, 4]
                    or any(
                        int(payload[field]) != NO_ID
                        for field in (
                            "input_view_2",
                            "input_view_3",
                            "output_view_1",
                            "aux_id_0",
                            "aux_id_1",
                            "aux_id_2",
                            "aux_id_3",
                        )
                    )
                ):
                    raise SystemExit(
                        f"{target.key}: embedding operator profile changed"
                    )
                by_slot = {int(view["slot"]): view for view in resolved}
                index_view = by_slot[0]
                source_view = by_slot[1]
                output_view = by_slot[4]
                expected_vocabulary = 151_936 if target_index < 2 else 129_280
                if (
                    index_view["dtype"] != int(DType.U32)
                    or index_view["dims"] != [1]
                    or index_view["strides"] != [1]
                    or index_view["element_offset"] != 0
                    or source_view["dtype"] != int(DType.BF16)
                    or source_view["dims"]
                    != [expected_vocabulary, EMBED_WIDTH]
                    or source_view["strides"] != [EMBED_WIDTH, 1]
                    or source_view["element_offset"] != 0
                    or output_view["dtype"] != int(DType.BF16)
                    or output_view["dims"] != [1, EMBED_WIDTH]
                    or output_view["strides"] != [EMBED_WIDTH, 1]
                    or output_view["element_offset"] != 0
                    or any(view["extent_axis"] != 0 for view in resolved)
                ):
                    raise SystemExit(
                        f"{target.key}: embedding view profile changed"
                    )
                numeric_id = int(payload["numeric_profile_id"])
                numeric = deployment.table.get(
                    numeric_id, ExtendedDescriptorType.NUMERIC
                )
                expected_contract = (
                    QWEN_EMBED_CONTRACT
                    if target_index < 2
                    else DEEPSEEK_EMBED_CONTRACT
                )
                contract_name = (
                    "bf16_payload_lookup_v1"
                    if target_index < 2
                    else "lookup_bf16_token_embedding_v1"
                )
                numeric_payload = numeric.payload
                if (
                    int(numeric_payload["input_dtype"]) != int(DType.U32)
                    or int(numeric_payload["second_input_dtype"])
                    != int(DType.BF16)
                    or int(numeric_payload["accumulator_dtype"])
                    != int(DType.FP32)
                    or int(numeric_payload["output_dtype"])
                    != int(DType.BF16)
                    or any(
                        int(numeric_payload[field]) != 0
                        for field in (
                            "rounding_mode",
                            "reduction_order",
                            "saturate",
                            "nan_policy",
                            "epsilon_bits",
                            "scale_bits",
                            "flags",
                        )
                    )
                    or bytes(numeric_payload["contract_digest"])
                    != expected_contract
                ):
                    raise SystemExit(
                        f"{target.key}: embedding numeric profile changed"
                    )
                row, source_identity = _checkpoint_row(
                    target,
                    deployment,
                    int(source_view["object_id"]),
                    EMBED_TOKEN,
                    EMBED_WIDTH,
                )
                embeddings.append(
                    {
                        "kind": "tensor_embed_lookup",
                        "pc": pc,
                        "descriptor_id": int(instruction.descriptor_id),
                        "numeric_profile_id": numeric_id,
                        "index_view": index_view,
                        "source_view": source_view,
                        "output_view": output_view,
                        "token_id": EMBED_TOKEN,
                        "contract": contract_name,
                        "contract_sha256": expected_contract.hex(),
                        "source": source_identity,
                        "expected_row_sha256": hashlib.sha256(row).hexdigest(),
                        "_source_words": [
                            int.from_bytes(row[offset : offset + 2], "little")
                            for offset in range(0, len(row), 2)
                        ],
                        "_expected_words": [
                            int.from_bytes(row[offset : offset + 2], "little")
                            for offset in range(0, len(row), 2)
                        ],
                    }
                )
                if int(instruction.signal_event_id) != NO_ID:
                    signals += 1
                retired += 1
                pc += 1
                continue

            if major == int(Major.VECTOR) and sub == int(Vector.RMS_NORM):
                if target_index >= 2 or len(embeddings) != 1:
                    raise SystemExit(
                        f"{target.key}: RMSNorm appeared outside the Qwen "
                        "post-embedding prefix"
                    )
                operator = deployment.table.get(
                    int(instruction.descriptor_id),
                    ExtendedDescriptorType.OPERATOR,
                )
                payload = operator.payload
                if (
                    int(instruction.descriptor_id)
                    != RMS_DESCRIPTOR_IDS[target_index]
                    or int(payload["engine_family"]) != major
                    or int(payload["engine_sub"]) != sub
                    or int(payload["numeric_profile_id"]) == NO_ID
                    or [view["slot"] for view in resolved] != [0, 1, 4]
                    or any(
                        int(payload[field]) != NO_ID
                        for field in (
                            "input_view_2",
                            "input_view_3",
                            "output_view_1",
                            "aux_id_0",
                            "aux_id_1",
                            "aux_id_2",
                            "aux_id_3",
                        )
                    )
                ):
                    raise SystemExit(
                        f"{target.key}: RMSNorm operator profile changed"
                    )
                by_slot = {int(view["slot"]): view for view in resolved}
                input_view = by_slot[0]
                weight_view = by_slot[1]
                output_view = by_slot[4]
                embedding = embeddings[0]
                if (
                    input_view["dtype"] != int(DType.BF16)
                    or input_view["dims"] != [1, EMBED_WIDTH]
                    or input_view["strides"] != [EMBED_WIDTH, 1]
                    or input_view["element_offset"] != 0
                    or input_view["object_id"]
                    != embedding["output_view"]["object_id"]
                    or weight_view["dtype"] != int(DType.BF16)
                    or weight_view["dims"] != [EMBED_WIDTH]
                    or weight_view["strides"] != [1]
                    or weight_view["element_offset"] != 0
                    or output_view["dtype"] != int(DType.BF16)
                    or output_view["dims"] != [1, EMBED_WIDTH]
                    or output_view["strides"] != [EMBED_WIDTH, 1]
                    or output_view["element_offset"] != 0
                    or any(view["extent_axis"] != 0 for view in resolved)
                ):
                    raise SystemExit(
                        f"{target.key}: RMSNorm view profile changed"
                    )
                numeric_id = int(payload["numeric_profile_id"])
                numeric = deployment.table.get(
                    numeric_id, ExtendedDescriptorType.NUMERIC
                )
                numeric_payload = numeric.payload
                if (
                    int(numeric_payload["input_dtype"]) != int(DType.BF16)
                    or int(numeric_payload["second_input_dtype"])
                    != int(DType.BF16)
                    or int(numeric_payload["accumulator_dtype"])
                    != int(DType.FP32)
                    or int(numeric_payload["output_dtype"])
                    != int(DType.BF16)
                    or int(numeric_payload["rounding_mode"]) != 0
                    or int(numeric_payload["reduction_order"]) != 1
                    or int(numeric_payload["saturate"]) != 0
                    or int(numeric_payload["nan_policy"]) != 0
                    or int(numeric_payload["epsilon_bits"]) != 0x358637BD
                    or int(numeric_payload["scale_bits"]) != 0
                    or int(numeric_payload["flags"]) != 0
                    or bytes(numeric_payload["contract_digest"])
                    != QWEN_RMS_CONTRACT
                ):
                    raise SystemExit(
                        f"{target.key}: RMSNorm numeric profile changed"
                    )
                gain, gain_identity = _checkpoint_row(
                    target,
                    deployment,
                    int(weight_view["object_id"]),
                    0,
                    EMBED_WIDTH,
                )
                gain_words = tuple(
                    int.from_bytes(gain[offset : offset + 2], "little")
                    for offset in range(0, len(gain), 2)
                )
                input_words = tuple(
                    int(code) for code in embedding["_expected_words"]
                )
                result = rms_norm_bf16((input_words,), gain_words)
                result_words = list(result.values[0])
                result_bytes = b"".join(
                    code.to_bytes(2, "little") for code in result_words
                )
                if (
                    result.mean_square_codes != (0x3A5BF2CA,)
                    or result.inverse_rms_codes != (0x420A0297,)
                    or result.normalized_saturated_element_count != 0
                    or result.output_saturated_element_count != 0
                    or hashlib.sha256(result_bytes).hexdigest()
                    != "976d6de1a3ed91a066c7efed4354e578edf366a3b51a7e6077d68282981ffa58"
                ):
                    raise SystemExit(
                        f"{target.key}: exact RMSNorm oracle result changed"
                    )
                rms_norms.append(
                    {
                        "kind": "vector_rms_norm",
                        "pc": pc,
                        "descriptor_id": int(instruction.descriptor_id),
                        "numeric_profile_id": numeric_id,
                        "input_view": input_view,
                        "weight_view": weight_view,
                        "output_view": output_view,
                        "contract": "qwen3_rmsnorm_fp32_bf16_v1",
                        "contract_sha256": QWEN_RMS_CONTRACT.hex(),
                        "input_source": "prior_embedding_result_bank",
                        "weight_source": gain_identity,
                        "mean_square_code": result.mean_square_codes[0],
                        "inverse_rms_code": result.inverse_rms_codes[0],
                        "normalized_saturated_element_count": (
                            result.normalized_saturated_element_count
                        ),
                        "output_saturated_element_count": (
                            result.output_saturated_element_count
                        ),
                        "expected_row_sha256": hashlib.sha256(
                            result_bytes
                        ).hexdigest(),
                        "_weight_words": list(gain_words),
                        "_expected_words": result_words,
                    }
                )
                if int(instruction.signal_event_id) != NO_ID:
                    signals += 1
                retired += 1
                pc += 1
                continue

            if major == int(Major.DMA) and sub == int(Dma.TRANSFER):
                if target_index < 2 or len(embeddings) != 1:
                    raise SystemExit(
                        f"{target.key}: transfer appeared outside the "
                        "DeepSeek post-embedding prefix"
                    )
                operator = deployment.table.get(
                    int(instruction.descriptor_id),
                    ExtendedDescriptorType.OPERATOR,
                )
                payload = operator.payload
                if (
                    int(instruction.descriptor_id)
                    != TRANSFER_DESCRIPTOR_IDS[target_index - 2]
                    or int(payload["engine_family"]) != major
                    or int(payload["engine_sub"]) != sub
                    or int(payload["numeric_profile_id"]) == NO_ID
                    or [view["slot"] for view in resolved] != [0, 4]
                    or int(payload["input_view_1"]) != NO_ID
                    or any(
                        int(payload[field]) != NO_ID
                        for field in (
                            "input_view_2",
                            "input_view_3",
                            "output_view_1",
                            "aux_id_0",
                            "aux_id_1",
                            "aux_id_2",
                            "aux_id_3",
                        )
                    )
                ):
                    raise SystemExit(
                        f"{target.key}: transfer operator profile changed"
                    )
                by_slot = {int(view["slot"]): view for view in resolved}
                input_view = by_slot[0]
                output_view = by_slot[4]
                embedding = embeddings[0]
                if (
                    input_view["dtype"] != int(DType.BF16)
                    or input_view["dims"] != [1, 4, EMBED_WIDTH]
                    or input_view["strides"] != [EMBED_WIDTH, 0, 1]
                    or input_view["element_offset"] != 0
                    or input_view["object_id"]
                    != embedding["output_view"]["object_id"]
                    or output_view["dtype"] != int(DType.BF16)
                    or output_view["dims"] != [1, 4, EMBED_WIDTH]
                    or output_view["strides"]
                    != [4 * EMBED_WIDTH, EMBED_WIDTH, 1]
                    or output_view["element_offset"] != 0
                    or any(view["extent_axis"] != 0 for view in resolved)
                ):
                    raise SystemExit(
                        f"{target.key}: transfer view profile changed"
                    )
                numeric_id = int(payload["numeric_profile_id"])
                numeric = deployment.table.get(
                    numeric_id, ExtendedDescriptorType.NUMERIC
                )
                numeric_payload = numeric.payload
                if (
                    int(numeric_payload["input_dtype"]) != int(DType.BF16)
                    or int(numeric_payload["second_input_dtype"])
                    != int(DType.BF16)
                    or int(numeric_payload["accumulator_dtype"])
                    != int(DType.FP32)
                    or int(numeric_payload["output_dtype"])
                    != int(DType.BF16)
                    or any(
                        int(numeric_payload[field]) != 0
                        for field in (
                            "rounding_mode",
                            "reduction_order",
                            "saturate",
                            "nan_policy",
                            "epsilon_bits",
                            "scale_bits",
                            "flags",
                        )
                    )
                    or bytes(numeric_payload["contract_digest"])
                    != DEEPSEEK_TRANSFER_CONTRACT
                ):
                    raise SystemExit(
                        f"{target.key}: transfer numeric profile changed"
                    )
                result_words = list(embedding["_expected_words"]) * 4
                result_bytes = b"".join(
                    code.to_bytes(2, "little") for code in result_words
                )
                transfers.append(
                    {
                        "kind": "dma_transfer",
                        "pc": pc,
                        "descriptor_id": int(instruction.descriptor_id),
                        "numeric_profile_id": numeric_id,
                        "input_view": input_view,
                        "output_view": output_view,
                        "contract": "structural_hc_expand_bf16_v1",
                        "contract_sha256": DEEPSEEK_TRANSFER_CONTRACT.hex(),
                        "lowering": {
                            "operation": "four_row_gather",
                            "indices": [0, 0, 0, 0],
                            "slots": 4,
                            "trailing": EMBED_WIDTH,
                            "extent": 1,
                            "source": "prior_embedding_result_bank",
                        },
                        "expected_payload_sha256": hashlib.sha256(
                            result_bytes
                        ).hexdigest(),
                        "_expected_words": result_words,
                    }
                )
                if int(instruction.signal_event_id) != NO_ID:
                    signals += 1
                retired += 1
                pc += 1
                continue

            unsupported = {
                "pc": pc,
                "family": major,
                "sub": sub,
                "opcode": str(instruction).split(maxsplit=1)[0],
                "descriptor_id": int(instruction.descriptor_id),
                "trap_class": 4,
            }
            break

        if unsupported is None:
            raise SystemExit(f"{target.key}: no fail-closed prefix boundary")
        expected_gathers = 1 if target_index < 2 else 2
        if len(gathers) != expected_gathers:
            raise SystemExit(
                f"{target.key}: expected {expected_gathers} gathers, found "
                f"{len(gathers)}"
            )
        if len(embeddings) != 1:
            raise SystemExit(
                f"{target.key}: expected one embedding, found {len(embeddings)}"
            )
        if target_index < 2:
            if len(rms_norms) != 1 or transfers:
                raise SystemExit(
                    f"{target.key}: expected one RMSNorm and no transfer"
                )
        elif len(transfers) != 1 or rms_norms:
            raise SystemExit(
                f"{target.key}: expected one transfer and no RMSNorm"
            )
        trailing_values = {int(g["source_view"]["dims"][1]) for g in gathers}
        if len(trailing_values) != 1:
            raise SystemExit(f"{target.key}: prefix gather widths differ")
        trailing = trailing_values.pop()

        index_base = len(index_words)
        source_base = len(source_words)
        output_base = len(expected_words)
        source_stride = (INDEX_VALUE + 1) * trailing
        for launch, gather in enumerate(gathers):
            index_words.append(INDEX_VALUE)
            want_source_cursor = source_base + launch * source_stride
            if len(source_words) != want_source_cursor:
                raise SystemExit("source-bank cursor drift")
            source_words.extend([0] * (INDEX_VALUE * trailing))
            source_words.extend(gather.pop("_source_words"))
            expected_words.extend(gather.pop("_expected_words"))

        embedding = embeddings[0]
        embedding_source_base = len(source_words)
        index_words.append(EMBED_TOKEN)
        source_words.extend(embedding.pop("_source_words"))
        expected_words.extend(embedding.pop("_expected_words"))
        case_rope_words = len(gathers) * trailing
        case_embedding_words = EMBED_WIDTH
        rms_input_base = output_base + case_rope_words
        rms_weight_base = 0
        transfer_index_base = 0
        transfer_source_base = output_base + case_rope_words
        case_rms_words = 0
        case_transfer_words = 0
        if rms_norms:
            rms_norm = rms_norms[0]
            rms_weight_base = len(source_words)
            source_words.extend(rms_norm.pop("_weight_words"))
            rms_expected = rms_norm.pop("_expected_words")
            expected_words.extend(rms_expected)
            case_rms_words = len(rms_expected)
        else:
            transfer = transfers[0]
            transfer_index_base = len(index_words)
            index_words.extend([0, 0, 0, 0])
            transfer_expected = transfer.pop("_expected_words")
            expected_words.extend(transfer_expected)
            case_transfer_words = len(transfer_expected)
        case_launches = len(gathers) + 2
        case_result_words = (
            case_rope_words
            + case_embedding_words
            + case_rms_words
            + case_transfer_words
        )

        state_count = int(source_case[34])
        if state_count != 0:
            raise SystemExit(f"{target.key}: production profile contains STATE")
        expected_boundary = NEXT_BOUNDARIES[target_index]
        if target_index < 2:
            expected_counts = {
                "fetched": 12,
                "retired": 11,
                "issued": 4,
                "loop_iterations": 3,
                "wait_events": 2,
                "signals": 3,
                "views": 12,
            }
        elif target_index == 2:
            expected_counts = {
                "fetched": 14,
                "retired": 13,
                "issued": 5,
                "loop_iterations": 4,
                "wait_events": 1,
                "signals": 4,
                "views": 11,
            }
        else:
            expected_counts = {
                "fetched": 15,
                "retired": 14,
                "issued": 5,
                "loop_iterations": 4,
                "wait_events": 2,
                "signals": 4,
                "views": 17,
            }
        observed_counts = {
            "fetched": fetched,
            "retired": retired,
            "issued": issued,
            "loop_iterations": loop_iterations,
            "wait_events": wait_events,
            "signals": signals,
            "views": len(prefix_views),
        }
        observed_boundary = (
            unsupported["pc"],
            unsupported["family"],
            unsupported["sub"],
            unsupported["descriptor_id"],
            unsupported["opcode"],
        )
        if observed_boundary != expected_boundary:
            raise SystemExit(
                f"{target.key}: next fail-stop boundary {observed_boundary}, "
                f"expected {expected_boundary}"
            )
        if observed_counts != expected_counts:
            raise SystemExit(
                f"{target.key}: prefix counts {observed_counts}, expected "
                f"{expected_counts}"
            )

        words = [
            int(source_case[0]),       # deployed program-image base
            int(source_case[1]),       # instruction count
            int(source_case[2]),       # descriptor-image base
            int(source_case[3]),       # descriptor count
            int(source_case[4]),       # symbol-image base
            int(source_case[5]),       # symbol bound mask
            entry_pc,
            int(source_case[8]),       # max retired work, low
            int(source_case[9]),       # max retired work, high
            state_count,
            index_base,
            source_base,
            source_stride,
            output_base,
            case_launches,
            case_result_words,
            unsupported["pc"],
            (unsupported["family"] << 8) | unsupported["sub"],
            unsupported["descriptor_id"],
            expected_counts["fetched"],
            expected_counts["retired"],
            expected_counts["issued"],
            expected_counts["loop_iterations"],
            expected_counts["signals"],
            expected_counts["views"],
            INDEX_VALUE,
            int(gathers[0]["source_view"]["dims"][0]),
            EMBED_WIDTH,
            target_index,
            1,                         # one capability response
            0,                         # descriptor/engine faults
            len(issue_words) // 4,     # expected response-stream base
            embedding_source_base,
            len(gathers),
            1,                         # one embedding launch
            expected_counts["wait_events"],
            case_rope_words,
            case_embedding_words,
            EMBED_TOKEN,
            trailing,
            rms_input_base,
            rms_weight_base,
            transfer_index_base,
            transfer_source_base,
            len(rms_norms),
            len(transfers),
            case_rms_words,
            case_transfer_words,
        ]
        if len(words) != CASE_STRIDE:
            raise SystemExit("internal case-record length error")
        case_words.extend(words)
        for gather in gathers:
            issue_words.extend(
                [
                    (int(Major.DMA) << 8) | int(Dma.GATHER),
                    int(gather["descriptor_id"]),
                    int(gather["pc"]),
                    0,
                ]
            )
        issue_words.extend(
            [
                (int(Major.TENSOR) << 8) | int(Tensor.EMBED_LOOKUP),
                int(embedding["descriptor_id"]),
                int(embedding["pc"]),
                0,
            ]
        )
        if rms_norms:
            rms_norm = rms_norms[0]
            issue_words.extend(
                [
                    (int(Major.VECTOR) << 8) | int(Vector.RMS_NORM),
                    int(rms_norm["descriptor_id"]),
                    int(rms_norm["pc"]),
                    0,
                ]
            )
        else:
            transfer = transfers[0]
            issue_words.extend(
                [
                    (int(Major.DMA) << 8) | int(Dma.TRANSFER),
                    int(transfer["descriptor_id"]),
                    int(transfer["pc"]),
                    0,
                ]
            )
        issue_words.extend(
            [
                (unsupported["family"] << 8) | unsupported["sub"],
                unsupported["descriptor_id"],
                unsupported["pc"],
                unsupported["trap_class"],
            ]
        )
        total_launches += case_launches
        total_gathers += len(gathers)
        total_embeddings += 1
        total_rms_norms += len(rms_norms)
        total_transfers += len(transfers)
        total_rope_words += case_rope_words
        total_rms_words += case_rms_words
        total_transfer_words += case_transfer_words
        embedding_checkpoint_bytes = int(
            embedding["source"]["selected_row_bytes"]
        )
        rms_checkpoint_bytes = (
            int(rms_norms[0]["weight_source"]["selected_row_bytes"])
            if rms_norms
            else 0
        )
        total_embedding_checkpoint_bytes += embedding_checkpoint_bytes
        total_rms_checkpoint_bytes += rms_checkpoint_bytes
        total_checkpoint_bytes += (
            embedding_checkpoint_bytes + rms_checkpoint_bytes
        )
        total_views += expected_counts["views"]
        records.append(
            {
                "name": case_name,
                "deployment": target.key,
                "deployment_sha256": deployment_sha,
                "deployment_identity_evidence": expected_identity.record(),
                "input_deployment_vector_case": deployment_case_index,
                "request": {
                    "entrypoint_id": 1,
                    "phase": "decode",
                    "prompt_tokens": PROMPT_TOKENS,
                    "position_start": INDEX_VALUE,
                    "embedding_token_id": EMBED_TOKEN,
                    "embedding_probe_scope": (
                        "bounded synthetic legal-vocabulary probe; not a "
                        "natural-language or end-to-end model claim"
                    ),
                    "symbols": {str(k): v for k, v in sorted(symbols.items())},
                },
                "bank_mapping": {
                    "index_base": index_base,
                    "source_base": source_base,
                    "source_launch_stride": source_stride,
                    "embedding_source_base": embedding_source_base,
                    "rms_input_base": rms_input_base,
                    "rms_weight_base": rms_weight_base,
                    "transfer_index_base": transfer_index_base,
                    "transfer_source_base": transfer_source_base,
                    "output_base": output_base,
                },
                "expected": {
                    **expected_counts,
                    "real_engine_launches": case_launches,
                    "dma_gather_launches": len(gathers),
                    "embedding_launches": 1,
                    "rms_norm_launches": len(rms_norms),
                    "dma_transfer_launches": len(transfers),
                    "rope_result_words": case_rope_words,
                    "embedding_result_words": case_embedding_words,
                    "rms_norm_result_words": case_rms_words,
                    "dma_transfer_result_words": case_transfer_words,
                    "selected_embedding_checkpoint_bytes": (
                        embedding_checkpoint_bytes
                    ),
                    "selected_rms_checkpoint_bytes": rms_checkpoint_bytes,
                    "selected_checkpoint_bytes": (
                        embedding_checkpoint_bytes + rms_checkpoint_bytes
                    ),
                    "result_words": case_result_words,
                    "trap_class": 4,
                    "first_fault_instruction": unsupported["pc"],
                    "complete": False,
                    "state_compat": 0,
                },
                "supported_prefix": [
                    {key: value for key, value in gather.items()}
                    for gather in gathers
                ]
                + [{key: value for key, value in embedding.items()}]
                + [
                    {key: value for key, value in operation.items()}
                    for operation in rms_norms + transfers
                ],
                "first_unsupported": unsupported,
                "resolved_prefix_views": prefix_views,
            }
        )

    if (
        total_launches != 14
        or total_gathers != 6
        or total_embeddings != 4
        or total_rms_norms != 2
        or total_transfers != 2
        or total_rope_words != 1_024
        or total_rms_words != 8_192
        or total_transfer_words != 32_768
        or len(expected_words) != 58_368
        or total_embedding_checkpoint_bytes != 32_768
        or total_rms_checkpoint_bytes != 16_384
        or total_checkpoint_bytes != 49_152
        or total_views != 52
    ):
        raise SystemExit(
            "witness depth changed: "
            f"launches={total_launches}, gathers={total_gathers}, "
            f"embeddings={total_embeddings}, rope_words={total_rope_words}, "
            f"rms_norms={total_rms_norms}, transfers={total_transfers}, "
            f"rms_words={total_rms_words}, "
            f"transfer_words={total_transfer_words}, "
            f"words={len(expected_words)}, "
            f"embedding_checkpoint_bytes={total_embedding_checkpoint_bytes}, "
            f"rms_checkpoint_bytes={total_rms_checkpoint_bytes}, "
            f"checkpoint_bytes={total_checkpoint_bytes}, views={total_views}"
        )
    files = {
        "p3_case.hex": _hex_lines(case_words),
        "p3_issue.hex": _hex_lines(issue_words),
        "p3_index.hex": _hex_lines(index_words, total=INDEX_WORDS),
        "p3_source.hex": _hex_lines(source_words, total=SOURCE_WORDS),
        "p3_expect.hex": _hex_lines(expected_words),
        "p3_meta.hex": _hex_lines(
            [
                len(records),
                total_launches,
                len(expected_words),
                total_views,
                CASE_STRIDE,
                INDEX_WORDS,
                SOURCE_WORDS,
                RESULT_WORDS,
                total_gathers,
                total_embeddings,
                total_rope_words,
                total_checkpoint_bytes,
                total_rms_norms,
                total_transfers,
                total_rms_words,
                total_transfer_words,
            ]
        ),
    }
    for name, payload in files.items():
        (args.output / name).write_text(payload, encoding="ascii")

    marker = (
        "PASS: ABI3 shipped-prefix engine integration "
        f"cases={len(records)} launches={total_launches} "
        f"words={len(expected_words)} capability_faults={len(records)}"
    )
    summary = {
        "schema": VECTOR_SCHEMA,
        "abi": {"major": 3, "minor": 0},
        "state_compat": 0,
        "request_scope": {
            "phase": "decode",
            "prompt_tokens": PROMPT_TOKENS,
            "position_start": INDEX_VALUE,
            "embedding_token_id": EMBED_TOKEN,
            "embedding_probe_scope": (
                "bounded synthetic legal-vocabulary probe; not a "
                "natural-language or end-to-end model claim"
            ),
        },
        "claim": (
            "exact shipped decode-program prefixes: six real DMA.GATHER "
            "launches copy 1,024 authentic generated RoPE words and four "
            "TENSOR.EMBED_LOOKUP launches copy 16,384 BF16 codes from four "
            "bounded, authenticated checkpoint-row reads; two exact Qwen "
            "VECTOR.RMS_NORM launches produce 8,192 BF16 codes using two "
            "bounded gain reads, and two DeepSeek stride-zero DMA.TRANSFER "
            "launches produce 32,768 BF16 codes from the prior embedding "
            "result; Qwen then fails closed at TENSOR.MATMUL and DeepSeek at "
            "LINK.MULTICAST or VECTOR.MHC; this is not a whole-model, "
            "prefill, token-selection, or decoding claim"
        ),
        "supported_profile": (
            "dense one-index FP32 DMA.GATHER plus exact token-zero BF16 "
            "TENSOR.EMBED_LOOKUP with 4,096-code rows, exact one-row Qwen "
            "BF16 RMSNorm, and DeepSeek four-copy stride-zero BF16 transfer; "
            "resolved views, unscaled operands, and numeric contracts are "
            "bound before each launch"
        ),
        "unsupported_policy": (
            "every other family/subopcode returns CAPABILITY before any engine "
            "launch, result write, retirement, or signal publication"
        ),
        "case_count": len(records),
        "real_engine_launch_count": total_launches,
        "dma_gather_launch_count": total_gathers,
        "embedding_launch_count": total_embeddings,
        "rms_norm_launch_count": total_rms_norms,
        "dma_transfer_launch_count": total_transfers,
        "rope_result_word_count": total_rope_words,
        "embedding_result_word_count": total_embeddings * EMBED_WIDTH,
        "rms_norm_result_word_count": total_rms_words,
        "dma_transfer_result_word_count": total_transfer_words,
        "selected_embedding_checkpoint_byte_count": (
            total_embedding_checkpoint_bytes
        ),
        "selected_rms_checkpoint_byte_count": total_rms_checkpoint_bytes,
        "selected_checkpoint_byte_count": total_checkpoint_bytes,
        "result_word_count": len(expected_words),
        "resolved_view_count": total_views,
        "capability_fault_count": len(records),
        "required_marker": marker,
        "geometry": {
            "case_stride": CASE_STRIDE,
            "index_words": INDEX_WORDS,
            "source_words": SOURCE_WORDS,
            "result_words": RESULT_WORDS,
            "case_words_used": len(case_words),
            "issue_words_used": len(issue_words),
            "issue_stride": 4,
            "index_words_used": len(index_words),
            "source_words_used": len(source_words),
            "expected_words_used": len(expected_words),
        },
        "input_deployment_vectors": {
            "path": str(DEPLOYMENT_VECTOR_JSON.relative_to(ROOT)),
            "sha256": _sha256_file(DEPLOYMENT_VECTOR_JSON),
            "images": {
                name: _sha256_file(DEPLOYMENT_VECTOR_DIR / name)
                for name in INPUT_IMAGES
            },
        },
        "image_sha256": {
            name: hashlib.sha256(payload.encode("ascii")).hexdigest()
            for name, payload in sorted(files.items())
        },
        "cases": records,
    }
    (args.output / "abi3_shipped_prefix_vectors.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        "abi3 shipped-prefix vectors: "
        f"cases={len(records)} launches={total_launches} "
        f"words={len(expected_words)} views={total_views}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
