#!/usr/bin/env python3
"""Qualify DeepSeek HBM PC 14 HC_PRE over its first 512-token issue.

This is deliberately a functional-operator qualification, not an RTL or model
token-generation result.  It binds the shipped HBM deployment's PC 14 and its
producer views, gathers the real first 512 prompt embeddings from the pinned
official checkpoint, and compares two independent arithmetic paths:

* 128 calls to the bounded (four-token) artifact service; and
* one 512-token ABI functional-device VECTOR.MHC execution.

Every architectural PC-14 output word is compared bit-for-bit.  The compact
checked-in vectors retain input/output hashes and the ordered token IDs rather
than redistributing checkpoint weights.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
import platform
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.builder import DeploymentBuilder  # noqa: E402
from runtime.abi3.capability import Capability  # noqa: E402
from runtime.abi3.constants import (  # noqa: E402
    CompletionStatus,
    Control,
    DType,
    Feature,
    Major,
    Permission,
    ReductionOrder,
    StorageClass,
    TopologyClass,
    Vector,
)
from runtime.abi3.deployment import Deployment, ObjectSource  # noqa: E402
from runtime.abi3.descriptors import Phase  # noqa: E402
from runtime.abi3.records import decode_body, split_program  # noqa: E402
from runtime.service_engine.hc_pre_numeric import (  # noqa: E402
    HC_PRE_FLATTENED_WIDTH,
    HC_PRE_HC_MULT,
    HC_PRE_MIX_FIELDS,
    HC_PRE_NORM_EPSILON_BINARY32,
    HC_PRE_SINKHORN_EPSILON_BINARY32,
    HC_PRE_SINKHORN_ITERATIONS,
    HC_PRE_WIDTH,
    execute_hc_pre,
)
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines.deepseek_vector import HC_PRE  # noqa: E402

# Importing the module above registers VECTOR.MHC with the functional device.


SCHEMA = "opentallas.abi3.deepseek_hbm_hc_pre_t512_qualification.v1"
VECTOR_SCHEMA = "opentallas.abi3.deepseek_hbm_hc_pre_t512_vector.v1"
REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
WORKLOAD_ID = "TA-DS-CTX-200K-1"
WORKLOAD_DIGEST = "803f0c3a3e9bf7ef68ddff00947576d2fab5703d1f4387df1eb2ec11be2c59bd"
WORKLOAD_FILE_SHA256 = (
    "b00dd2f461329c14e0a8c0863dbef78e066950bee0aba053aa651f91890418bb"
)
DEPLOYMENT_SHA256 = (
    "2380c602842f716f1fcdc277751b6243e0e9610bfccdcc7ed9f9c27ef478aff7"
)
CAPABILITY_SHA256 = (
    "1eb2e92dac1d9fb8937b7724953d2f65993bd56e342e9058569442eb61d74bad"
)
DESCRIPTOR_TABLE_SHA256 = (
    "91191d6702e8555eb67310d3b6331c7ed20bd85352ebce075344fa1311b3c753"
)
PROGRAM_SHA256 = "0f5f87529f036c6bfb0f8c12bbc84fb38c5900b6e533540235bdc1315b77c075"

SHARD_1 = "model-00001-of-00048.safetensors"
SHARD_2 = "model-00002-of-00048.safetensors"
SHARD_SHA256 = {
    SHARD_1: "f3668ba4cccf1ca6a7eb84e888fb92c1cdc7204d472ba9db771e6fd3abf6b874",
    SHARD_2: "77b26c939a0e25b3113c8d6bb04e1901a748bd4a7d2589e3bfdaabdf1e9bba14",
}
SHARD_SIZE = {
    SHARD_1: 1_059_061_856,
    SHARD_2: 3_566_321_192,
}
TENSOR_SHA256 = {
    "embed.token_18042": (
        "f91a7a1b42cf9951ca55ac28f76d55cd6f4c4bfd1a5dbab1ac5bcdb5eb55072c"
    ),
    "layers.0.hc_attn_fn": (
        "f5c1ffdfb92df2c04ac17e9a31e38701f2b7a5cac0cd427a2df2aa3e239987fc"
    ),
    "layers.0.hc_attn_base": (
        "edaa695cf5de59f919415f6e71dcb35be5ad817a06fa7222ee3021d9f388adda"
    ),
    "layers.0.hc_attn_scale": (
        "0b0e327d2f4d1a104c53d6e0a9172cf532028383e82cdf6d70537cb83092c63f"
    ),
}

TOKEN_COUNT = 512
SERVICE_TOKENS = 4
SERVICE_COMMAND_COUNT = TOKEN_COUNT // SERVICE_TOKENS
OPERATOR_DESCRIPTOR_ID = 546
PC = 14

DEFAULT_DEPLOYMENT = ROOT / "build/abi3/deepseek-v4-flash-hbm-tokens"
DEFAULT_WORKLOAD = (
    ROOT / "build/workloads/deepseek-v4-flash-0731/TA-DS-CTX-200K-1.json"
)
DEFAULT_SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub"
    / "models--deepseek-ai--DeepSeek-V4-Flash-0731"
    / "snapshots"
    / REVISION
)
DEFAULT_VECTOR_DIR = ROOT / "testdata/runtime/deepseek_hbm_hc_pre_t512"
DEFAULT_RESULT = (
    ROOT / "results/abi3/deepseek_hbm_hc_pre_t512_functional_qualification.json"
)

WEIGHTS_FILE = "expected_pc14_weights.u32le"
COMBINATION_FILE = "expected_pc14_combination.u32le"
VECTOR_FILE = "qualification_vector.json"

SOURCE_PATHS = (
    "runtime/abi3/builder.py",
    "runtime/abi3/deployment.py",
    "runtime/abi3/descriptors.py",
    "runtime/abi3/records.py",
    "runtime/service_engine/hc_pre_numeric.py",
    "runtime/sim/device.py",
    "runtime/sim/engine.py",
    "runtime/sim/engines/deepseek_vector.py",
    "runtime/sim/formats.py",
    "runtime/sim/memory.py",
    "tools/qualify_deepseek_hbm_hc_pre_t512.py",
)

FIRST_WEIGHTS = np.asarray(
    [
        [0x3F800008, 0x3F800008, 0x3F800008, 0x3F800008],
        [0x3D5DD097, 0x320CDE79, 0x322ADE6C, 0x36E5FAB7],
    ],
    dtype=np.uint32,
)
FIRST_COMBINATION = np.asarray(
    [
        [0x3F693333, 0x3B6033A5, 0x3BEAC4CA, 0x3AB4E3C5],
        [0x2FB009DA, 0x3F6789D7, 0x3957C48D, 0x3DF6328B],
        [0x2F258B30, 0x3DBBFE9C, 0x3F7DEEB4, 0x3483C7CA],
        [0x3DB665EC, 0x39B07FFB, 0x3A38D206, 0x3F60DF28],
    ],
    dtype=np.uint32,
)


class QualificationError(RuntimeError):
    """A source or arithmetic identity did not match the frozen contract."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256_bytes(payload: bytes | bytearray | memoryview) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(16 << 20):
            digest.update(block)
    return digest.hexdigest()


def _le_bytes(values: np.ndarray, width: int) -> bytes:
    dtype = np.dtype("<u2" if width == 16 else "<u4")
    return np.ascontiguousarray(values, dtype=dtype).tobytes(order="C")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise QualificationError(message)


def _write_canonical(path: Path, body: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical(body) + b"\n")


def _record_digest(body: dict[str, Any], field: str) -> dict[str, Any]:
    result = dict(body)
    result[field] = _sha256_bytes(_canonical(body))
    return result


def _safe_tensor_header(path: Path) -> tuple[dict[str, Any], int, str]:
    with path.open("rb") as handle:
        length_raw = handle.read(8)
        _require(len(length_raw) == 8, f"{path}: truncated safetensors header")
        header_length = int.from_bytes(length_raw, "little")
        header_raw = handle.read(header_length)
    _require(
        len(header_raw) == header_length,
        f"{path}: truncated safetensors JSON header",
    )
    try:
        header = json.loads(header_raw)
    except json.JSONDecodeError as exc:
        raise QualificationError(f"{path}: invalid safetensors header: {exc}") from exc
    return header, 8 + header_length, _sha256_bytes(header_raw)


def _tensor_extent(
    path: Path, name: str, expected_dtype: str, expected_shape: Iterable[int]
) -> tuple[int, int, dict[str, Any]]:
    header, data_start, header_sha256 = _safe_tensor_header(path)
    _require(name in header, f"{path}: tensor {name!r} is absent")
    tensor = header[name]
    _require(tensor["dtype"] == expected_dtype, f"{name}: wrong dtype")
    _require(tensor["shape"] == list(expected_shape), f"{name}: wrong shape")
    start, stop = (int(value) for value in tensor["data_offsets"])
    absolute_start, absolute_stop = data_start + start, data_start + stop
    _require(
        0 <= absolute_start <= absolute_stop <= path.stat().st_size,
        f"{name}: range lies outside {path}",
    )
    return absolute_start, absolute_stop, {
        "data_start": data_start,
        "header_sha256": header_sha256,
        "range_offset": absolute_start,
        "range_bytes": absolute_stop - absolute_start,
    }


def _read_exact(path: Path, offset: int, length: int) -> bytes:
    with path.open("rb") as handle:
        handle.seek(offset)
        payload = handle.read(length)
    _require(len(payload) == length, f"{path}: short read at {offset}")
    return payload


def _source_map() -> dict[str, str]:
    return {path: _sha256_file(ROOT / path) for path in SOURCE_PATHS}


def _assert_independent_lanes() -> dict[str, Any]:
    service_path = ROOT / "runtime/service_engine/hc_pre_numeric.py"
    engine_path = ROOT / "runtime/sim/engines/deepseek_vector.py"

    def imports(path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module)
        return roots

    service_imports = imports(service_path)
    engine_imports = imports(engine_path)
    service_forbidden = sorted(
        item
        for item in service_imports
        if item.startswith("runtime.sim") or item.startswith("runtime.reference")
    )
    engine_forbidden = sorted(
        item for item in engine_imports if item.startswith("runtime.service_engine")
    )
    _require(not service_forbidden, "service lane imports simulator/reference code")
    _require(not engine_forbidden, "functional lane imports service code")
    return {
        "service_imports_simulator_or_reference": service_forbidden,
        "functional_engine_imports_service": engine_forbidden,
        "separated": True,
        "service_arithmetic": "integer/dyadic exact boundaries and Decimal-certified CR32 transcendental",
        "functional_arithmetic": "NumPy binary32 boundaries with binary64 exact-product FMA and distinct-code scalar CR32 maps",
    }


def _descriptor_record(descriptor: Any) -> dict[str, Any]:
    return {
        "descriptor_id": int(descriptor.descriptor_id),
        "descriptor_type": int(descriptor.descriptor_type),
        "encoded_sha256": _sha256_bytes(descriptor.encode()),
        "primary_object_id": int(descriptor.primary_object_id),
        "secondary_object_id": int(descriptor.secondary_object_id),
        "permissions": int(descriptor.permissions),
        "payload": {
            key: value.hex() if isinstance(value, bytes) else int(value)
            for key, value in sorted(descriptor.payload.items())
        },
    }


def _validate_shipped_pc14(deployment_root: Path) -> tuple[Deployment, dict[str, Any]]:
    deployment = Deployment.read(deployment_root)
    _require(deployment.deployment_digest.hex() == DEPLOYMENT_SHA256, "deployment drift")
    _require(deployment.capability_digest == CAPABILITY_SHA256, "capability drift")
    _require(
        deployment.table.digest.hex() == DESCRIPTOR_TABLE_SHA256,
        "descriptor table drift",
    )
    _require(_sha256_file(deployment_root / "program.bin") == PROGRAM_SHA256, "program drift")
    _, body = split_program(deployment.program)
    instructions = decode_body(body)
    _require(len(instructions) > PC, "shipped program has no PC 14")
    instruction = instructions[PC]
    _require(int(instruction.major) == int(Major.VECTOR), "PC 14 major drift")
    _require(int(instruction.sub) == int(Vector.MHC), "PC 14 subopcode drift")
    _require(instruction.descriptor_id == OPERATOR_DESCRIPTOR_ID, "PC 14 descriptor drift")
    _require(instruction.wait_set_id == 547, "PC 14 wait-set drift")
    _require(instruction.signal_event_id == 4, "PC 14 signal drift")

    operator = deployment.table[546]
    expected_operator = {
        "engine_family": int(Major.VECTOR),
        "engine_sub": int(Vector.MHC),
        "source_kernel_id": 4,
        "counter_class_id": 536,
        "numeric_profile_id": 544,
        "schedule_id": 545,
        "input_view_0": 538,
        "input_view_1": 539,
        "input_view_2": 540,
        "input_view_3": 541,
        "output_view_0": 542,
        "output_view_1": 543,
        "aux_id_0": HC_PRE,
        "aux_id_1": HC_PRE_SINKHORN_ITERATIONS,
        "aux_id_2": HC_PRE_HC_MULT,
    }
    for key, expected in expected_operator.items():
        _require(int(operator.payload[key]) == expected, f"descriptor 546 {key} drift")

    view_expectations = {
        529: (238, int(DType.BF16), (512, 4, 4096), (4096, 0, 1)),
        530: (239, int(DType.BF16), (512, 4, 4096), (16384, 4096, 1)),
        538: (239, int(DType.BF16), (512, 4, 4096), (16384, 4096, 1)),
        539: (1, int(DType.FP32), (24, 16384), (16384, 1)),
        540: (3, int(DType.FP32), (24,), (1,)),
        541: (2, int(DType.FP32), (3,), (1,)),
        542: (240, int(DType.FP32), (512, 2, 4), (8, 4, 1)),
        543: (241, int(DType.FP32), (512, 4, 4), (16, 4, 1)),
    }
    for descriptor_id, (object_id, dtype, dims, strides) in view_expectations.items():
        descriptor = deployment.table[descriptor_id]
        payload = descriptor.payload
        rank = int(payload["rank"])
        observed_dims = tuple(int(payload[f"dim{axis}"]) for axis in range(rank))
        observed_strides = tuple(
            int(payload[f"stride{axis}"]) for axis in range(rank)
        )
        _require(descriptor.primary_object_id == object_id, f"view {descriptor_id} object drift")
        _require(int(payload["dtype"]) == dtype, f"view {descriptor_id} dtype drift")
        _require(observed_dims == dims, f"view {descriptor_id} shape drift")
        _require(observed_strides == strides, f"view {descriptor_id} stride drift")
    _require(deployment.table[529].payload["stride1"] == 0, "HC expand is not stride-zero")

    numeric = deployment.table[544]
    _require(int(numeric.payload["input_dtype"]) == int(DType.BF16), "numeric input drift")
    _require(int(numeric.payload["second_input_dtype"]) == int(DType.FP32), "numeric weight drift")
    _require(int(numeric.payload["accumulator_dtype"]) == int(DType.FP32), "numeric accumulator drift")
    _require(int(numeric.payload["output_dtype"]) == int(DType.FP32), "numeric output drift")
    _require(
        int(numeric.payload["reduction_order"]) == int(ReductionOrder.PAIRWISE_TREE),
        "numeric reduction descriptor drift",
    )
    _require(
        int(numeric.payload["epsilon_bits"]) == HC_PRE_NORM_EPSILON_BINARY32,
        "numeric epsilon drift",
    )
    _require(
        deployment.notes["numeric_contracts"]["544"]
        == "hyper_connection_hc_pre_bf16_v1",
        "numeric contract name drift",
    )
    _require(deployment.table[537].payload["bound_divisor"] == 512, "PC14 block drift")
    _require(deployment.table[537].payload["bound_symbol_id"] == 0, "PC14 span symbol drift")

    source_expectations = {
        1: (SHARD_2, 6_378_032, 1_572_864, TENSOR_SHA256["layers.0.hc_attn_fn"]),
        2: (SHARD_2, 7_950_896, 12, TENSOR_SHA256["layers.0.hc_attn_scale"]),
        3: (SHARD_2, 6_377_936, 96, TENSOR_SHA256["layers.0.hc_attn_base"]),
    }
    for object_id, expected in source_expectations.items():
        segment = deployment.objects[object_id].segments[0]
        observed = (segment.path, segment.offset, segment.bytes, segment.sha256)
        _require(observed == expected, f"object {object_id} layer-zero source drift")

    descriptor_ids = tuple(range(521, 548))
    descriptor_records = [_descriptor_record(deployment.table[index]) for index in descriptor_ids]
    return deployment, {
        "deployment_sha256": deployment.deployment_digest.hex(),
        "capability_sha256": deployment.capability_digest,
        "descriptor_table_sha256": deployment.table.digest.hex(),
        "program_sha256": _sha256_file(deployment_root / "program.bin"),
        "program_pc": PC,
        "pc14_instruction_sha256": _sha256_bytes(instruction.encode()),
        "descriptor_bundle_ids": list(descriptor_ids),
        "descriptor_bundle_sha256": _sha256_bytes(
            b"".join(deployment.table[index].encode() for index in descriptor_ids)
        ),
        "descriptors": descriptor_records,
        "producer_proof": {
            "embedding_lookup_pc": 7,
            "hc_expand_pc": 10,
            "hc_expand_input_view": 529,
            "hc_expand_input_stream_stride": 0,
            "hc_expand_output_view": 530,
            "hc_pre_pc": 14,
            "statement": "each authentic embedding row is replicated over four HC streams by the shipped stride-zero view",
        },
    }


def _load_workload(path: Path) -> tuple[list[int], dict[str, Any]]:
    raw = path.read_bytes()
    _require(_sha256_bytes(raw) == WORKLOAD_FILE_SHA256, "workload file drift")
    body = json.loads(raw)
    _require(body["workload_id"] == WORKLOAD_ID, "wrong workload ID")
    _require(body["digest"] == WORKLOAD_DIGEST, "workload digest drift")
    _require(body["prompt_token_count"] == 200_000, "prompt length drift")
    ids = body["token_ids"]
    _require(len(ids) == 200_000, "workload token array length drift")
    first = [int(value) for value in ids[:TOKEN_COUNT]]
    _require(first[0] == 18_042, "first prompt token drift")
    _require(all(0 <= value < 129_280 for value in first), "illegal prompt token")
    token_bytes = np.asarray(first, dtype="<u4").tobytes()
    return first, {
        "path": str(path.relative_to(ROOT)),
        "file_sha256": _sha256_bytes(raw),
        "workload_id": body["workload_id"],
        "workload_digest": body["digest"],
        "prompt_token_count": body["prompt_token_count"],
        "rendered_text_sha256": body["rendered_text_sha256"],
        "first_issue_token_count": len(first),
        "first_issue_token_ids_u32le_sha256": _sha256_bytes(token_bytes),
        "first_issue_unique_token_count": len(set(first)),
    }


def _load_checkpoint(
    snapshot: Path, token_ids: list[int], *, full_shard_hash: bool
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    shard1 = snapshot / SHARD_1
    shard2 = snapshot / SHARD_2
    for path in (shard1, shard2):
        _require(path.is_file(), f"missing checkpoint shard {path}")
        _require(path.stat().st_size == SHARD_SIZE[path.name], f"{path.name} size drift")
        if full_shard_hash:
            _require(_sha256_file(path) == SHARD_SHA256[path.name], f"{path.name} hash drift")

    embed_start, embed_stop, embed_info = _tensor_extent(
        shard1, "embed.weight", "BF16", (129_280, HC_PRE_WIDTH)
    )
    fn_start, fn_stop, fn_info = _tensor_extent(
        shard2,
        "layers.0.hc_attn_fn",
        "F32",
        (HC_PRE_MIX_FIELDS, HC_PRE_FLATTENED_WIDTH),
    )
    base_start, base_stop, base_info = _tensor_extent(
        shard2, "layers.0.hc_attn_base", "F32", (HC_PRE_MIX_FIELDS,)
    )
    scale_start, scale_stop, scale_info = _tensor_extent(
        shard2, "layers.0.hc_attn_scale", "F32", (3,)
    )
    _require((fn_start, fn_stop - fn_start) == (6_378_032, 1_572_864), "fn offset drift")
    _require((base_start, base_stop - base_start) == (6_377_936, 96), "base offset drift")
    _require((scale_start, scale_stop - scale_start) == (7_950_896, 12), "scale offset drift")

    row_bytes = HC_PRE_WIDTH * 2
    rows = np.empty((TOKEN_COUNT, HC_PRE_WIDTH), dtype="<u2")
    unique_hashes: dict[str, str] = {}
    cache: dict[int, bytes] = {}
    for index, token_id in enumerate(token_ids):
        payload = cache.get(token_id)
        if payload is None:
            offset = embed_start + token_id * row_bytes
            _require(offset + row_bytes <= embed_stop, "embedding row outside tensor")
            payload = _read_exact(shard1, offset, row_bytes)
            cache[token_id] = payload
            unique_hashes[str(token_id)] = _sha256_bytes(payload)
        rows[index] = np.frombuffer(payload, dtype="<u2")
    _require(
        unique_hashes["18042"] == TENSOR_SHA256["embed.token_18042"],
        "token-18042 embedding drift",
    )

    fn_raw = _read_exact(shard2, fn_start, fn_stop - fn_start)
    base_raw = _read_exact(shard2, base_start, base_stop - base_start)
    scale_raw = _read_exact(shard2, scale_start, scale_stop - scale_start)
    for name, payload in (
        ("layers.0.hc_attn_fn", fn_raw),
        ("layers.0.hc_attn_base", base_raw),
        ("layers.0.hc_attn_scale", scale_raw),
    ):
        _require(_sha256_bytes(payload) == TENSOR_SHA256[name], f"{name} drift")

    projection = np.frombuffer(fn_raw, dtype="<f4").reshape(
        HC_PRE_MIX_FIELDS, HC_PRE_FLATTENED_WIDTH
    ).copy()
    base = np.frombuffer(base_raw, dtype="<f4").copy()
    scale = np.frombuffer(scale_raw, dtype="<f4").copy()
    _require(bool(np.all(np.isfinite(projection))), "projection has nonfinite values")
    _require(bool(np.all(np.isfinite(base))), "base has nonfinite values")
    _require(bool(np.all(np.isfinite(scale))), "scale has nonfinite values")

    hidden = np.repeat(rows[:, None, :], HC_PRE_HC_MULT, axis=1)
    _require(hidden.shape == (TOKEN_COUNT, HC_PRE_HC_MULT, HC_PRE_WIDTH), "hidden shape")
    checkpoint = {
        "repository": REPOSITORY,
        "revision": REVISION,
        "snapshot_leaf": snapshot.name,
        "full_relevant_shard_hash_verified": bool(full_shard_hash),
        "shards": {
            path.name: {
                "size_bytes": path.stat().st_size,
                "sha256": SHARD_SHA256[path.name],
            }
            for path in (shard1, shard2)
        },
        "tensors": {
            "embed.weight": {
                **embed_info,
                "dtype": "BF16",
                "shape": [129_280, HC_PRE_WIDTH],
                "ordered_first_512_rows_sha256": _sha256_bytes(_le_bytes(rows, 16)),
                "unique_row_sha256": dict(sorted(unique_hashes.items(), key=lambda item: int(item[0]))),
            },
            "layers.0.hc_attn_fn": {
                **fn_info,
                "dtype": "F32",
                "shape": [HC_PRE_MIX_FIELDS, HC_PRE_FLATTENED_WIDTH],
                "sha256": _sha256_bytes(fn_raw),
            },
            "layers.0.hc_attn_base": {
                **base_info,
                "dtype": "F32",
                "shape": [HC_PRE_MIX_FIELDS],
                "sha256": _sha256_bytes(base_raw),
            },
            "layers.0.hc_attn_scale": {
                **scale_info,
                "dtype": "F32",
                "shape": [3],
                "sha256": _sha256_bytes(scale_raw),
            },
        },
        "pc14_hidden_bf16_u16le_sha256": _sha256_bytes(_le_bytes(hidden, 16)),
    }
    return hidden, projection, base, scale, checkpoint


def _service_composition(
    hidden: np.ndarray,
    projection: np.ndarray,
    base: np.ndarray,
    scale: np.ndarray,
    token_ids: list[int],
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    projection_codes = np.ascontiguousarray(projection).view(np.uint32)
    base_codes = np.ascontiguousarray(base).view(np.uint32)
    scale_codes = np.ascontiguousarray(scale).view(np.uint32)
    projection_list = projection_codes.astype(object).tolist()
    base_list = [int(value) for value in base_codes]
    scale_list = [int(value) for value in scale_codes]

    weights = np.empty((TOKEN_COUNT, 2, HC_PRE_HC_MULT), dtype=np.uint32)
    combination = np.empty(
        (TOKEN_COUNT, HC_PRE_HC_MULT, HC_PRE_HC_MULT), dtype=np.uint32
    )
    commands: list[dict[str, Any]] = []
    global_hashers = {
        name: hashlib.sha256()
        for name in (
            "branch_codes",
            "post_codes",
            "combination_codes",
            "residual_codes",
            "rms_mean_codes",
            "rms_inverse_codes",
            "projection_codes",
            "mix_codes",
            "pre_codes",
            "stable_softmax_codes",
        )
    }
    widths = {
        "branch_codes": 16,
        "post_codes": 32,
        "combination_codes": 32,
        "residual_codes": 16,
        "rms_mean_codes": 32,
        "rms_inverse_codes": 32,
        "projection_codes": 32,
        "mix_codes": 32,
        "pre_codes": 32,
        "stable_softmax_codes": 32,
    }
    total_counters: Counter[str] = Counter()

    for command_index in range(SERVICE_COMMAND_COUNT):
        start = command_index * SERVICE_TOKENS
        stop = start + SERVICE_TOKENS
        chunk = hidden[start:stop]
        x_codes = [[
            [[int(value) for value in stream] for stream in token]
            for token in chunk
        ]]
        result = execute_hc_pre(
            x_codes,
            projection_list,
            scale_list,
            base_list,
            norm_epsilon_binary32=HC_PRE_NORM_EPSILON_BINARY32,
            hc_epsilon_binary32=HC_PRE_SINKHORN_EPSILON_BINARY32,
        )
        _require(
            np.array_equal(np.asarray(result.residual_codes[0], dtype=np.uint16), chunk),
            f"service command {command_index}: residual differs from input",
        )
        pre = np.asarray(result.pre_codes[0], dtype=np.uint32)
        post = np.asarray(result.post_codes[0], dtype=np.uint32)
        comb = np.asarray(result.combination_codes[0], dtype=np.uint32)
        _require(pre.shape == (4, 4), f"service command {command_index}: pre shape")
        _require(post.shape == (4, 4), f"service command {command_index}: post shape")
        _require(comb.shape == (4, 4, 4), f"service command {command_index}: comb shape")
        weights[start:stop, 0, :] = pre
        weights[start:stop, 1, :] = post
        combination[start:stop] = comb
        command_weights = np.stack((pre, post), axis=1)

        field_hashes: dict[str, str] = {}
        for name, width in widths.items():
            values = getattr(result, name)
            payload = _le_bytes(np.asarray(values), width)
            global_hashers[name].update(payload)
            field_hashes[name] = _sha256_bytes(payload)
        counters = {key: int(value) for key, value in result.logical_counters.items()}
        total_counters.update(counters)
        command_body = {
            "command_index": command_index,
            "position_start": start,
            "position_stop_exclusive": stop,
            "token_ids": token_ids[start:stop],
            "input_hidden_bf16_u16le_sha256": _sha256_bytes(_le_bytes(chunk, 16)),
            "service_weights_u32le_sha256": _sha256_bytes(
                _le_bytes(command_weights, 32)
            ),
            "service_combination_u32le_sha256": _sha256_bytes(
                _le_bytes(comb, 32)
            ),
            "service_field_sha256": field_hashes,
            "logical_counters_sha256": _sha256_bytes(_canonical(counters)),
            "branch_saturation_count": int(result.branch_saturation_count),
            "status": "service_completed_and_self_checked",
        }
        commands.append(_record_digest(command_body, "command_sha256"))
        if (command_index + 1) % 8 == 0 or command_index == 0:
            print(
                f"service composition {command_index + 1}/{SERVICE_COMMAND_COUNT}",
                file=sys.stderr,
                flush=True,
            )

    _require(np.array_equal(weights[0], FIRST_WEIGHTS), "token-18042 weights sentinel drift")
    _require(
        np.array_equal(combination[0], FIRST_COMBINATION),
        "token-18042 combination sentinel drift",
    )
    summary = {
        "command_count": SERVICE_COMMAND_COUNT,
        "tokens_per_command": SERVICE_TOKENS,
        "covered_positions": TOKEN_COUNT,
        "composed_field_sha256": {
            name: digest.hexdigest() for name, digest in sorted(global_hashers.items())
        },
        "logical_counter_totals": dict(sorted(total_counters.items())),
        "logical_counter_totals_sha256": _sha256_bytes(
            _canonical(dict(sorted(total_counters.items())))
        ),
    }
    return weights, combination, commands, summary


def _qualification_capability() -> Capability:
    capability = Capability(
        capability_id="",
        topology_class=int(TopologyClass.SINGLE_CHIP),
        features=tuple(
            int(feature)
            for feature in (
                Feature.HOST_QUEUE_ABI,
                Feature.DEPLOYMENT_DESCRIPTOR_ABI,
                Feature.DETERMINISTIC_MICROSEQUENCER,
                Feature.BF16_TENSOR,
                Feature.TRANSACTIONAL_STATE,
                Feature.ON_DEVICE_SELECTION,
            )
        ),
        limits={
            "max_instructions": 64,
            "max_descriptors": 128,
            "max_loop_depth": 4,
            "max_loop_trip": TOKEN_COUNT,
            "max_retired_work": 4096,
            "max_events": 64,
            "max_event_id": 63,
            "max_state_resources": 16,
            "max_outstanding_per_queue": 64,
            "max_context_positions": TOKEN_COUNT,
            "max_expert_ids": 4096,
            "max_topk": 16,
            "max_vocabulary": 262_144,
            "max_sessions": 1,
            "max_nodes": 1,
        },
        numeric_contracts=("hyper_connection_hc_pre_bf16_v1",),
        engines={"vector": {"lanes": 128, "queues": 2}},
        memory={"hbm": {"bytes": 64 << 20}, "sram": {"bytes": 128 << 20}},
        technology_view="functional-operator-qualification-only",
    )
    capability.validate()
    return capability


def _functional_execution(
    hidden: np.ndarray,
    projection: np.ndarray,
    base: np.ndarray,
    scale: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    capability = _qualification_capability()
    builder = DeploymentBuilder(
        target_id="deepseek-hbm-pc14-t512-functional-qualification",
        model_id="deepseek-v4-flash-0731",
        backend="abi3-functional-operator-qualification",
        capability=capability,
    )
    builder.topology(
        topology_class=TopologyClass.SINGLE_CHIP,
        node_count=1,
        hbm_bytes_per_node=64 << 20,
        sram_bytes_per_node=128 << 20,
    )
    initial: dict[int, bytes] = {}

    def memory(values: np.ndarray, *, output: bool = False) -> int:
        payload = np.ascontiguousarray(values).tobytes(order="C")
        object_id = builder.memory_object(
            storage_class=StorageClass.HBM,
            size_bytes=len(payload),
            source=ObjectSource.zeros(len(payload)),
            permissions=int(Permission.READ | Permission.WRITE),
        )
        if not output:
            initial[object_id] = payload
        return object_id

    hidden_object = memory(np.asarray(hidden, dtype=np.uint16))
    fn_object = memory(np.asarray(projection, dtype=np.float32))
    base_object = memory(np.asarray(base, dtype=np.float32))
    scale_object = memory(np.asarray(scale, dtype=np.float32))
    weights_zeros = np.zeros((TOKEN_COUNT, 2, HC_PRE_HC_MULT), dtype=np.float32)
    comb_zeros = np.zeros(
        (TOKEN_COUNT, HC_PRE_HC_MULT, HC_PRE_HC_MULT), dtype=np.float32
    )
    weights_object = memory(weights_zeros, output=True)
    comb_object = memory(comb_zeros, output=True)

    def view(object_id: int, dtype: DType, dims: tuple[int, ...], permissions: int) -> int:
        return builder.tensor_view(
            object_id=object_id,
            dtype=dtype,
            dims=dims,
            permissions=permissions,
        )

    input_views = [
        view(hidden_object, DType.BF16, hidden.shape, int(Permission.READ)),
        view(fn_object, DType.FP32, projection.shape, int(Permission.READ)),
        view(base_object, DType.FP32, base.shape, int(Permission.READ)),
        view(scale_object, DType.FP32, scale.shape, int(Permission.READ)),
    ]
    output_views = [
        view(
            weights_object,
            DType.FP32,
            weights_zeros.shape,
            int(Permission.READ | Permission.WRITE),
        ),
        view(
            comb_object,
            DType.FP32,
            comb_zeros.shape,
            int(Permission.READ | Permission.WRITE),
        ),
    ]
    counter = builder.counter_class(5, (0x05000001, 0x05000002, 0x05000003))
    numeric = builder.numeric(
        contract="hyper_connection_hc_pre_bf16_v1",
        input_dtype=DType.BF16,
        second_input_dtype=DType.FP32,
        accumulator_dtype=DType.FP32,
        output_dtype=DType.FP32,
        reduction_order=ReductionOrder.PAIRWISE_TREE,
        epsilon_bits=HC_PRE_NORM_EPSILON_BINARY32,
    )
    schedule = builder.schedule(
        engine_family=Major.VECTOR,
        queue_index=0,
        issue_window=2,
        tile_rows=64,
        tile_cols=8,
        tile_depth=1,
        bank_mask=8,
        port_mask=3,
        noc_route_class=0,
        resource_bound=128,
        max_outstanding=64,
        priority=0,
    )
    operator = builder.operator(
        engine_family=Major.VECTOR,
        engine_sub=int(Vector.MHC),
        inputs=input_views,
        outputs=output_views,
        aux=(HC_PRE, HC_PRE_SINKHORN_ITERATIONS, HC_PRE_HC_MULT),
        numeric_profile_id=numeric,
        schedule_id=schedule,
        counter_class_id=counter,
        source_kernel_id=4,
    )
    builder.emit(Major.VECTOR, int(Vector.MHC), descriptor_id=operator)
    builder.emit(Major.CONTROL, int(Control.COMPLETE))
    builder.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    deployment = builder.finish()
    device = Device(deployment, capability)
    for object_id, payload in initial.items():
        device.memory[object_id].write(0, payload)
    result = device.run_transaction(device.create_session(), entrypoint_id=0, symbols={})
    _require(result.status == CompletionStatus.SUCCESS, f"functional device: {result.message}")

    def read(view_id: int) -> np.ndarray:
        resolved = device.views.resolve(view_id, {}, {})
        return np.array(device.views.read_array(resolved), copy=True)

    weights = np.ascontiguousarray(read(output_views[0]), dtype=np.float32).view(np.uint32)
    combination = np.ascontiguousarray(read(output_views[1]), dtype=np.float32).view(np.uint32)
    _require(weights.shape == (TOKEN_COUNT, 2, 4), "functional weights shape drift")
    _require(combination.shape == (TOKEN_COUNT, 4, 4), "functional comb shape drift")
    evidence = {
        "harness_kind": "admitted_abi3_functional_device_single_operator",
        "harness_deployment_sha256": deployment.deployment_digest.hex(),
        "harness_capability_sha256": capability.digest,
        "descriptor_equivalence": {
            "source_kernel_id": 4,
            "engine_family": int(Major.VECTOR),
            "engine_sub": int(Vector.MHC),
            "aux": [HC_PRE, HC_PRE_SINKHORN_ITERATIONS, HC_PRE_HC_MULT],
            "numeric_contract": "hyper_connection_hc_pre_bf16_v1",
            "numeric_epsilon_bits": HC_PRE_NORM_EPSILON_BINARY32,
            "numeric_reduction_order": int(ReductionOrder.PAIRWISE_TREE),
            "schedule": {
                "issue_window": 2,
                "tile_rows": 64,
                "tile_cols": 8,
                "tile_depth": 1,
                "bank_mask": 8,
                "port_mask": 3,
                "resource_bound": 128,
                "max_outstanding": 64,
            },
        },
        "transaction_status": result.status.name.lower(),
        "architectural_counters": dict(sorted(result.counters.items())),
        "weights_u32le_sha256": _sha256_bytes(_le_bytes(weights, 32)),
        "combination_u32le_sha256": _sha256_bytes(_le_bytes(combination, 32)),
    }
    return weights, combination, evidence


def _first_difference(expected: np.ndarray, actual: np.ndarray) -> str:
    indices = np.argwhere(expected != actual)
    if not len(indices):
        return "none"
    index = tuple(int(value) for value in indices[0])
    return f"index={index} service=0x{int(expected[index]):08x} functional=0x{int(actual[index]):08x}"


def _build_vector(
    token_ids: list[int],
    workload: Mapping[str, Any],
    checkpoint: Mapping[str, Any],
    shipped: Mapping[str, Any],
    weights: np.ndarray,
    combination: np.ndarray,
) -> dict[str, Any]:
    body = {
        "schema": VECTOR_SCHEMA,
        "workload": dict(workload),
        "checkpoint": {
            "repository": checkpoint["repository"],
            "revision": checkpoint["revision"],
            "pc14_hidden_bf16_u16le_sha256": checkpoint[
                "pc14_hidden_bf16_u16le_sha256"
            ],
            "tensor_sha256": {
                name: record.get("sha256")
                or record.get("ordered_first_512_rows_sha256")
                for name, record in checkpoint["tensors"].items()
            },
        },
        "shipped_artifact": {
            key: shipped[key]
            for key in (
                "deployment_sha256",
                "capability_sha256",
                "descriptor_table_sha256",
                "program_sha256",
                "program_pc",
                "pc14_instruction_sha256",
                "descriptor_bundle_sha256",
            )
        },
        "geometry": {
            "hidden": [TOKEN_COUNT, HC_PRE_HC_MULT, HC_PRE_WIDTH],
            "projection": [HC_PRE_MIX_FIELDS, HC_PRE_FLATTENED_WIDTH],
            "weights_output": [TOKEN_COUNT, 2, HC_PRE_HC_MULT],
            "combination_output": [TOKEN_COUNT, HC_PRE_HC_MULT, HC_PRE_HC_MULT],
            "ordered_projection_fused_product_adds": (
                TOKEN_COUNT * HC_PRE_MIX_FIELDS * HC_PRE_FLATTENED_WIDTH
            ),
        },
        "first_issue_token_ids": token_ids,
        "expected_outputs": {
            "weights": {
                "path": WEIGHTS_FILE,
                "dtype": "u32le",
                "shape": list(weights.shape),
                "bytes": int(weights.size * 4),
                "sha256": _sha256_bytes(_le_bytes(weights, 32)),
            },
            "combination": {
                "path": COMBINATION_FILE,
                "dtype": "u32le",
                "shape": list(combination.shape),
                "bytes": int(combination.size * 4),
                "sha256": _sha256_bytes(_le_bytes(combination, 32)),
            },
        },
        "sentinel": {
            "token_id": token_ids[0],
            "weights_u32_hex": [
                [f"{int(code):08x}" for code in row] for row in FIRST_WEIGHTS
            ],
            "combination_u32_hex": [
                [f"{int(code):08x}" for code in row]
                for row in FIRST_COMBINATION
            ],
        },
    }
    return _record_digest(body, "manifest_sha256")


def _verify_digest_field(body: Mapping[str, Any], field: str) -> None:
    mutable = dict(body)
    recorded = mutable.pop(field)
    _require(recorded == _sha256_bytes(_canonical(mutable)), f"{field} mismatch")


def verify_artifacts(vector_dir: Path, result_path: Path) -> None:
    vector_path = vector_dir / VECTOR_FILE
    vector = json.loads(vector_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    _require(vector["schema"] == VECTOR_SCHEMA, "wrong vector schema")
    _require(result["schema"] == SCHEMA, "wrong result schema")
    _verify_digest_field(vector, "manifest_sha256")
    _verify_digest_field(result, "record_sha256")
    _require(result["status"] == "pass", "qualification did not pass")
    _require(result["vector_manifest_sha256"] == _sha256_file(vector_path), "vector link drift")
    _require(len(vector["first_issue_token_ids"]) == TOKEN_COUNT, "vector token count")
    _require(len(result["service_composition"]["commands"]) == SERVICE_COMMAND_COUNT, "command count")
    for name in ("weights", "combination"):
        record = vector["expected_outputs"][name]
        path = vector_dir / record["path"]
        _require(path.stat().st_size == record["bytes"], f"{name} size drift")
        _require(_sha256_file(path) == record["sha256"], f"{name} hash drift")
        _require(
            result["comparison"][f"{name}_u32le_sha256"] == record["sha256"],
            f"{name} result/vector drift",
        )
    for index, command in enumerate(result["service_composition"]["commands"]):
        _verify_digest_field(command, "command_sha256")
        _require(command["command_index"] == index, "nonconsecutive command index")
        _require(command["position_start"] == index * 4, "command start drift")
        _require(command["position_stop_exclusive"] == (index + 1) * 4, "command stop drift")
        _require(command["bitwise_match_to_functional_slice"], "command mismatch")
    _require(result["comparison"]["mismatched_words"] == 0, "recorded mismatch")
    _require(result["claims"]["rtl_execution"] is False, "result overclaims RTL")
    _require(result["claims"]["model_token_generation"] is False, "result overclaims tokens")
    _require(result["claims"]["tpot"] is False, "result overclaims TPOT")


def qualify(
    deployment_root: Path,
    workload_path: Path,
    snapshot: Path,
    vector_dir: Path,
    result_path: Path,
    *,
    full_shard_hash: bool,
) -> None:
    _require(sys.byteorder == "little", "this evidence writer requires a little-endian host")
    _, shipped = _validate_shipped_pc14(deployment_root)
    token_ids, workload = _load_workload(workload_path)
    hidden, projection, base, scale, checkpoint = _load_checkpoint(
        snapshot, token_ids, full_shard_hash=full_shard_hash
    )
    separation = _assert_independent_lanes()
    sources = _source_map()

    service_weights, service_combination, commands, service_summary = (
        _service_composition(hidden, projection, base, scale, token_ids)
    )
    functional_weights, functional_combination, functional = _functional_execution(
        hidden, projection, base, scale
    )
    weights_equal = np.array_equal(service_weights, functional_weights)
    combination_equal = np.array_equal(service_combination, functional_combination)
    _require(
        weights_equal,
        "weights mismatch: " + _first_difference(service_weights, functional_weights),
    )
    _require(
        combination_equal,
        "combination mismatch: "
        + _first_difference(service_combination, functional_combination),
    )

    for command in commands:
        start = command["position_start"]
        stop = command["position_stop_exclusive"]
        functional_weight_hash = _sha256_bytes(
            _le_bytes(functional_weights[start:stop], 32)
        )
        functional_comb_hash = _sha256_bytes(
            _le_bytes(functional_combination[start:stop], 32)
        )
        _require(
            functional_weight_hash == command["service_weights_u32le_sha256"],
            f"service command {command['command_index']}: packed weights mismatch",
        )
        _require(
            functional_comb_hash == command["service_combination_u32le_sha256"],
            f"service command {command['command_index']}: combination mismatch",
        )
        command.pop("command_sha256")
        command["functional_weights_u32le_sha256"] = functional_weight_hash
        command["functional_combination_u32le_sha256"] = functional_comb_hash
        command["bitwise_match_to_functional_slice"] = bool(
            np.array_equal(service_weights[start:stop], functional_weights[start:stop])
            and np.array_equal(
                service_combination[start:stop], functional_combination[start:stop]
            )
        )
        command.update(_record_digest(command, "command_sha256"))

    weights_payload = _le_bytes(service_weights, 32)
    combination_payload = _le_bytes(service_combination, 32)
    vector_dir.mkdir(parents=True, exist_ok=True)
    (vector_dir / WEIGHTS_FILE).write_bytes(weights_payload)
    (vector_dir / COMBINATION_FILE).write_bytes(combination_payload)
    vector = _build_vector(
        token_ids,
        workload,
        checkpoint,
        shipped,
        service_weights,
        service_combination,
    )
    vector_path = vector_dir / VECTOR_FILE
    _write_canonical(vector_path, vector)

    compared_words = int(service_weights.size + service_combination.size)
    result_body = {
        "schema": SCHEMA,
        "status": "pass",
        "qualification_boundary": (
            "complete functional numeric/operator qualification of the first "
            "T=512 prefill issue at shipped HBM PC 14 / descriptor 546"
        ),
        "source_binding": {
            "policy": "exact SHA-256 of every execution-authoritative source file",
            "files": sources,
            "source_map_sha256": _sha256_bytes(_canonical(sources)),
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "machine": platform.machine(),
            "byteorder": sys.byteorder,
        },
        "workload": workload,
        "checkpoint": checkpoint,
        "shipped_artifact": shipped,
        "lane_independence": separation,
        "numeric_association": {
            "contract": "hyper_connection_hc_pre_bf16_v1",
            "rms_reduction": "balanced binary32 tree over 16384 squares",
            "projection": "24 rows, increasing-K exact-product binary32-RNE fused product-add",
            "projection_fused_product_add_count": (
                TOKEN_COUNT * HC_PRE_MIX_FIELDS * HC_PRE_FLATTENED_WIDTH
            ),
            "projection_post_scale": "separate binary32 multiply by correctly rounded inverse RMS",
            "affine": "separate binary32 multiply then binary32 add",
            "sigmoid": "correctly rounded binary32",
            "softmax_exp": "stable nonpositive-input correctly rounded binary32 exponential",
            "sinkhorn": "one initial column normalization then 19 row/column pairs; 20 row and 20 column stages total",
            "epsilon_bits_hex": f"{HC_PRE_NORM_EPSILON_BINARY32:08x}",
            "matrix_orientation": "source-major [source][destination]",
        },
        "service_composition": {**service_summary, "commands": commands},
        "functional_execution": functional,
        "comparison": {
            "method": "bitwise equality of every u32 architectural output encoding",
            "weights_word_count": int(service_weights.size),
            "combination_word_count": int(service_combination.size),
            "compared_word_count": compared_words,
            "mismatched_words": 0,
            "weights_u32le_sha256": _sha256_bytes(weights_payload),
            "combination_u32le_sha256": _sha256_bytes(combination_payload),
            "weights_bitwise_equal": bool(weights_equal),
            "combination_bitwise_equal": bool(combination_equal),
        },
        "vector_manifest": str(vector_path.relative_to(ROOT)),
        "vector_manifest_sha256": _sha256_file(vector_path),
        "rtl_blockers": "results/abi3/deepseek_hbm_hc_pre_t512_rtl_blockers.json",
        "claims": {
            "full_pc14_first_issue_functional_operator": True,
            "all_pc14_output_words_bitwise_compared": True,
            "rtl_execution": False,
            "model_token_generation": False,
            "end_to_end_decode": False,
            "eos": False,
            "architectural_timing": False,
            "tpot": False,
        },
        "nonclaims": [
            "This is not an RTL execution or an RTL datapath qualification.",
            "This operator does not generate a model token and establishes no end-to-end decode or EOS result.",
            "No host duration in this run is an architectural latency or TPOT measurement.",
            "The admitted single-operator harness checks functional engine semantics; the shipped 32-node program identity is bound separately and was not executed through PC 14 here.",
        ],
    }
    result = _record_digest(result_body, "record_sha256")
    _write_canonical(result_path, result)
    verify_artifacts(vector_dir, result_path)
    print(
        json.dumps(
            {
                "status": "pass",
                "compared_words": compared_words,
                "result": str(result_path),
                "record_sha256": result["record_sha256"],
            },
            sort_keys=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployment", type=Path, default=DEFAULT_DEPLOYMENT)
    parser.add_argument("--workload", type=Path, default=DEFAULT_WORKLOAD)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--vector-dir", type=Path, default=DEFAULT_VECTOR_DIR)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument(
        "--skip-full-shard-hash",
        action="store_true",
        help="trust exact authenticated tensor ranges; the published run does not use this",
    )
    parser.add_argument(
        "--verify-artifacts",
        action="store_true",
        help="verify the retained compact record without reading the checkpoint",
    )
    args = parser.parse_args()
    try:
        if args.verify_artifacts:
            verify_artifacts(args.vector_dir, args.result)
            print(json.dumps({"status": "pass", "mode": "artifact-verification"}))
        else:
            qualify(
                args.deployment,
                args.workload,
                args.snapshot,
                args.vector_dir,
                args.result,
                full_shard_hash=not args.skip_full_shard_hash,
            )
    except (QualificationError, KeyError, OSError, ValueError) as exc:
        print(f"qualification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
