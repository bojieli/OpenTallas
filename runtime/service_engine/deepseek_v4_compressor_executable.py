"""Artifact-driven transactional service for the DeepSeek V4 compressor slice.

The service consumes three immutable packages: a verified deployment, a prior
state version, and a projected-input request.  It builds all candidate state in
memory and publishes one create-once result tree only after every micro-op and
valid-prefix check succeeds.  There is no hidden process-lifetime session state;
the published state subpackage is the restart-persistent successor artifact.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import struct
from typing import Any

from compiler.checking.deepseek_v4_compressor_executable import (
    verify_deepseek_v4_compressor_executable_deployment,
)
from compiler.microcode.deepseek_v4_compressor import (
    APE_BYTES,
    HEAD_DIM,
    MODEL_ID,
    PROGRAM_SHA256,
    PROJECTED_WIDTH,
    RATIO,
    CompressorOpcode,
    decode,
    verify,
)
from runtime.reference.compressed_kv import (
    CompressedKVState,
    compressed_kv_state_bf16,
    compressed_kv_valid_view_bf16,
    compressed_kv_write_bf16,
    zero_compressed_kv_state_bf16,
)
from runtime.reference.compression_pool import compress_pool_f32
from runtime.reference.compression_state import (
    CompressionLaneState,
    CompressionState,
    compress_state_update_f32,
    compression_state_f32,
    zero_compression_state_f32,
)
from runtime.reference.conversion import binary32_tensor_to_bf16_rne
from runtime.reference.formats import decode_binary32
from runtime.service_engine.secure_artifacts import (
    SecureArtifactError,
    SecureDirectory,
    canonical_json_bytes,
    parse_canonical_json,
    publish_payload_tree,
)


DEPLOYMENT_MANIFEST = "deployment_manifest.json"
APE_PATH = "parameters/layers.2.attn.compressor.ape.f32le"
PROGRAM_PATH = "program/compressor.bin"
STATE_SCHEMA = "opentallas.deepseek_v4_compressor_state.v1"
REQUEST_SCHEMA = "opentallas.deepseek_v4_compressor_request.v1"
RESULT_SCHEMA = "opentallas.deepseek_v4_compressor_result.v1"
COUNTER_REPORT_SCHEMA = "opentallas.deepseek_v4_compressor_counter_report.v1"
EXECUTION_REPORT_SCHEMA = "opentallas.deepseek_v4_compressor_execution_report.v1"
INITIAL_BATCH_CAPACITY = 4
INITIAL_CACHE_CAPACITY = 8
MAX_REQUEST_SEQUENCE = 8
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_INPUT_BYTES = INITIAL_BATCH_CAPACITY * MAX_REQUEST_SEQUENCE * PROJECTED_WIDTH * 4
RAW_SLOTS = 2 * RATIO
RAW_VALUES = INITIAL_BATCH_CAPACITY * RAW_SLOTS * PROJECTED_WIDTH
COMPRESSED_VALUES = INITIAL_BATCH_CAPACITY * INITIAL_CACHE_CAPACITY * HEAD_DIM
SESSION_HEX_DIGITS = 64


class DeepSeekV4CompressorExecutableServiceError(RuntimeError):
    """Raised when any artifact, state transition, or publication is poisoned."""


def _poison(message: str, cause: BaseException | None = None) -> None:
    if cause is None:
        raise DeepSeekV4CompressorExecutableServiceError(message)
    raise DeepSeekV4CompressorExecutableServiceError(message) from cause


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _digest(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _poison(f"{label} must be a canonical lowercase SHA-256")
    return value


def _session(value: object, label: str) -> str:
    return _digest(value, label)


def _integer(
    value: object,
    label: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        _poison(f"{label} must be an integer in [{minimum}, {maximum}]")
    return value


def _exact_dict(value: object, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        _poison(f"{label} must be an exact object")
    if set(value) != keys:
        _poison(
            f"{label} fields differ: missing={sorted(keys - set(value))}, "
            f"unknown={sorted(set(value) - keys)}"
        )
    return value


def _json_payload(value: object) -> bytes:
    try:
        return canonical_json_bytes(value)
    except SecureArtifactError as exc:
        _poison(f"cannot encode canonical JSON: {exc}", exc)


def _parse_json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = parse_canonical_json(
            payload,
            label=label,
            maximum_bytes=MAX_JSON_BYTES,
        )
    except SecureArtifactError as exc:
        _poison(str(exc), exc)
    if type(value) is not dict:
        _poison(f"{label} must contain an exact object")
    return value


def _flatten(value: object, *, bits: int, label: str) -> tuple[int, ...]:
    maximum = (1 << bits) - 1
    output: list[int] = []

    def visit(item: object) -> None:
        if type(item) is int:
            if not 0 <= item <= maximum:
                _poison(f"{label} contains a value outside {bits}-bit encoding range")
            output.append(item)
            return
        if type(item) not in {tuple, list}:
            _poison(f"{label} must contain exact list/tuple axes and integer codes")
        for child in item:
            visit(child)

    visit(value)
    return tuple(output)


def _pack_u32(value: object, *, label: str) -> bytes:
    flat = _flatten(value, bits=32, label=label)
    return struct.pack(f"<{len(flat)}I", *flat) if flat else b""


def _pack_u16(value: object, *, label: str) -> bytes:
    flat = _flatten(value, bits=16, label=label)
    return struct.pack(f"<{len(flat)}H", *flat) if flat else b""


def _unpack_u32(payload: bytes, *, count: int, label: str) -> tuple[int, ...]:
    if len(payload) != count * 4:
        _poison(f"{label} has {len(payload)} bytes, expected {count * 4}")
    return tuple(code for (code,) in struct.iter_unpack("<I", payload))


def _unpack_u16(payload: bytes, *, count: int, label: str) -> tuple[int, ...]:
    if len(payload) != count * 2:
        _poison(f"{label} has {len(payload)} bytes, expected {count * 2}")
    return tuple(code for (code,) in struct.iter_unpack("<H", payload))


def _reshape3(
    flat: tuple[int, ...],
    first: int,
    second: int,
    third: int,
) -> tuple:
    result = []
    offset = 0
    for _ in range(first):
        rows = []
        for _ in range(second):
            rows.append(tuple(flat[offset : offset + third]))
            offset += third
        result.append(tuple(rows))
    if offset != len(flat):
        _poison("rank-three tensor reshape did not consume its payload")
    return tuple(result)


def _reshape4(
    flat: tuple[int, ...],
    first: int,
    second: int,
    third: int,
    fourth: int,
) -> tuple:
    result = []
    offset = 0
    for _ in range(first):
        sequences = []
        for _ in range(second):
            heads = []
            for _ in range(third):
                heads.append(tuple(flat[offset : offset + fourth]))
                offset += fourth
            sequences.append(tuple(heads))
        result.append(tuple(sequences))
    if offset != len(flat):
        _poison("rank-four tensor reshape did not consume its payload")
    return tuple(result)


def _descriptor(path: str, payload: bytes, *, dtype: str, shape: list[int]) -> dict[str, Any]:
    return {
        "dtype": dtype,
        "path": path,
        "sha256": _sha256(payload),
        "shape": shape,
        "size_bytes": len(payload),
    }


def _validate_descriptor(
    value: object,
    *,
    path: str,
    dtype: str,
    shape: list[int],
    size_bytes: int,
    label: str,
) -> dict[str, Any]:
    descriptor = _exact_dict(
        value,
        {"dtype", "path", "sha256", "shape", "size_bytes"},
        label,
    )
    expected = {
        "dtype": dtype,
        "path": path,
        "sha256": descriptor.get("sha256"),
        "shape": shape,
        "size_bytes": size_bytes,
    }
    _digest(descriptor.get("sha256"), f"{label}.sha256")
    if _json_payload(descriptor) != _json_payload(expected):
        _poison(f"{label} differs")
    return descriptor


@dataclass(frozen=True)
class CompressorDeployment:
    root: Path
    verification_report: dict[str, Any]
    build_id: str
    ape_codes: tuple[tuple[int, ...], ...]
    instructions: tuple
    artifact_digests: tuple[tuple[str, int, str], ...]

    def verify_snapshot(self) -> None:
        try:
            with SecureDirectory(self.root, label="guarded compressor deployment") as root:
                files, _ = root.enumerate_tree(maximum_depth=4, maximum_entries=64)
                expected = {path for path, _, _ in self.artifact_digests}
                if files != expected:
                    _poison("compressor deployment tree changed after loading")
                for path, size_bytes, digest in self.artifact_digests:
                    source = root.open_file(
                        path,
                        label=f"guarded compressor deployment artifact {path!r}",
                        exact_size=size_bytes,
                        maximum_size=max(1, size_bytes),
                        minimum_size=0,
                    )
                    if source.guarded_sha256 != digest:
                        _poison(
                            f"compressor deployment artifact {path!r} changed after loading"
                        )
                root.verify()
        except DeepSeekV4CompressorExecutableServiceError:
            raise
        except Exception as exc:
            _poison(f"cannot reverify compressor deployment snapshot: {exc}", exc)


def load_deepseek_v4_compressor_executable_deployment(
    deployment_dir: Path,
) -> CompressorDeployment:
    """Load only bytes admitted by the independent deployment checker."""

    root_path = Path(deployment_dir).absolute()
    try:
        report = verify_deepseek_v4_compressor_executable_deployment(root_path)
        with SecureDirectory(root_path, label="compressor deployment") as root:
            manifest_file = root.open_file(
                DEPLOYMENT_MANIFEST,
                label="compressor deployment manifest",
                maximum_size=512 * 1024,
            )
            manifest = _parse_json(
                manifest_file.read_bytes(
                    label="compressor deployment manifest",
                    maximum_bytes=512 * 1024,
                ),
                "compressor deployment manifest",
            )
            build_id = _digest(manifest.get("build_id"), "deployment build_id")
            raw_artifacts = manifest.get("artifacts")
            if type(raw_artifacts) is not list:
                _poison("deployment artifacts must be a list")
            artifact_digests: list[tuple[str, int, str]] = [
                (
                    DEPLOYMENT_MANIFEST,
                    len(_json_payload(manifest)),
                    _sha256(_json_payload(manifest)),
                )
            ]
            for index, raw_record in enumerate(raw_artifacts):
                record = _exact_dict(
                    raw_record,
                    {"path", "role", "sha256", "size_bytes"},
                    f"deployment artifact record {index}",
                )
                path = record["path"]
                if type(path) is not str:
                    _poison(f"deployment artifact record {index} path differs")
                size_bytes = _integer(
                    record["size_bytes"],
                    f"deployment artifact record {index} size",
                    minimum=0,
                    maximum=2 * 1024 * 1024,
                )
                artifact_digests.append(
                    (
                        path,
                        size_bytes,
                        _digest(
                            record["sha256"],
                            f"deployment artifact record {index} digest",
                        ),
                    )
                )
            ape_file = root.open_file(
                APE_PATH,
                label="compressor APE",
                exact_size=APE_BYTES,
                maximum_size=APE_BYTES,
            )
            ape_payload = ape_file.read_bytes(
                label="compressor APE",
                maximum_bytes=APE_BYTES,
            )
            flat_ape = _unpack_u32(
                ape_payload,
                count=RATIO * PROJECTED_WIDTH,
                label="compressor APE",
            )
            ape = tuple(
                tuple(flat_ape[row * PROJECTED_WIDTH : (row + 1) * PROJECTED_WIDTH])
                for row in range(RATIO)
            )
            program_file = root.open_file(
                PROGRAM_PATH,
                label="compressor microcode",
                maximum_size=4096,
            )
            program_payload = program_file.read_bytes(
                label="compressor microcode",
                maximum_bytes=4096,
            )
            if _sha256(program_payload) != PROGRAM_SHA256:
                _poison("compressor microcode identity differs")
            instructions = decode(program_payload)
            verify(instructions)
            root.verify()
    except DeepSeekV4CompressorExecutableServiceError:
        raise
    except Exception as exc:
        _poison(f"cannot load compressor deployment: {exc}", exc)
    return CompressorDeployment(
        root_path,
        report,
        build_id,
        ape,
        instructions,
        tuple(sorted(artifact_digests)),
    )


@dataclass(frozen=True)
class CompressorStatePackage:
    root: Path
    state_id: str
    build_id: str
    sequence_number: int
    prior_state_id: str | None
    transition_id: str | None
    raw_state: CompressionState
    compressed_state: CompressedKVState


def _state_core(
    *,
    build_id: str,
    sequence_number: int,
    prior_state_id: str | None,
    transition_id: str | None,
    raw_state: CompressionState,
    compressed_state: CompressedKVState,
    raw_kv_payload: bytes,
    raw_score_payload: bytes,
    compressed_payload: bytes,
) -> dict[str, Any]:
    return {
        "build_id": build_id,
        "compressed": {
            "lane_active": list(compressed_state.lane_active),
            "next_positions": list(compressed_state.next_positions),
            "payload": _descriptor(
                "compressed_kv.bf16le",
                compressed_payload,
                dtype="BF16",
                shape=[
                    INITIAL_BATCH_CAPACITY,
                    INITIAL_CACHE_CAPACITY,
                    1,
                    HEAD_DIM,
                ],
            ),
            "session_ids": list(compressed_state.session_ids),
            "valid_prefix_lengths": list(compressed_state.valid_prefix_lengths),
            "versions": list(compressed_state.versions),
        },
        "dimensions": {
            "batch_capacity": INITIAL_BATCH_CAPACITY,
            "cache_capacity": INITIAL_CACHE_CAPACITY,
            "head_dim": HEAD_DIM,
            "projected_width": PROJECTED_WIDTH,
            "ratio": RATIO,
            "raw_slots": RAW_SLOTS,
        },
        "model_id": MODEL_ID,
        "prior_state_id": prior_state_id,
        "raw": {
            "kv": _descriptor(
                "raw_kv.f32le",
                raw_kv_payload,
                dtype="F32",
                shape=[INITIAL_BATCH_CAPACITY, RAW_SLOTS, PROJECTED_WIDTH],
            ),
            "lanes": [
                {
                    "next_pos": lane.next_pos,
                    "session_id": lane.session_id,
                    "version": lane.version,
                }
                for lane in raw_state.lanes
            ],
            "scores": _descriptor(
                "raw_scores.f32le",
                raw_score_payload,
                dtype="F32",
                shape=[INITIAL_BATCH_CAPACITY, RAW_SLOTS, PROJECTED_WIDTH],
            ),
        },
        "schema": STATE_SCHEMA,
        "sequence_number": sequence_number,
        "transition_id": transition_id,
    }


def _state_payloads(
    *,
    build_id: str,
    sequence_number: int,
    prior_state_id: str | None,
    transition_id: str | None,
    raw_state: CompressionState,
    compressed_state: CompressedKVState,
) -> tuple[dict[str, bytes], dict[str, Any]]:
    raw_kv = _pack_u32(raw_state.kv_f32_codes, label="raw KV state")
    raw_scores = _pack_u32(raw_state.score_f32_codes, label="raw score state")
    compressed = _pack_u16(
        compressed_state.bf16_codes,
        label="compressed KV state",
    )
    if len(raw_kv) != RAW_VALUES * 4 or len(raw_scores) != RAW_VALUES * 4:
        _poison("raw state payload dimensions differ")
    if len(compressed) != COMPRESSED_VALUES * 2:
        _poison("compressed state payload dimensions differ")
    core = _state_core(
        build_id=build_id,
        sequence_number=sequence_number,
        prior_state_id=prior_state_id,
        transition_id=transition_id,
        raw_state=raw_state,
        compressed_state=compressed_state,
        raw_kv_payload=raw_kv,
        raw_score_payload=raw_scores,
        compressed_payload=compressed,
    )
    manifest = dict(core)
    manifest["state_id"] = _sha256(_json_payload(core))
    return (
        {
            "compressed_kv.bf16le": compressed,
            "raw_kv.f32le": raw_kv,
            "raw_scores.f32le": raw_scores,
            "state_manifest.json": _json_payload(manifest),
        },
        manifest,
    )


def _optional_digest(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _digest(value, label)


def load_deepseek_v4_compressor_state(
    state_dir: Path,
    *,
    expected_build_id: str,
) -> CompressorStatePackage:
    """Validate and reconstruct one immutable raw/compressed state package."""

    root_path = Path(state_dir).absolute()
    try:
        with SecureDirectory(root_path, label="compressor state package") as root:
            files, directories = root.enumerate_tree(maximum_depth=1, maximum_entries=8)
            expected_files = {
                "compressed_kv.bf16le",
                "raw_kv.f32le",
                "raw_scores.f32le",
                "state_manifest.json",
            }
            if files != expected_files or directories:
                _poison("compressor state package tree closure differs")
            manifest_file = root.open_file(
                "state_manifest.json",
                label="compressor state manifest",
                maximum_size=256 * 1024,
            )
            manifest_payload = manifest_file.read_bytes(
                label="compressor state manifest",
                maximum_bytes=256 * 1024,
            )
            manifest = _parse_json(manifest_payload, "compressor state manifest")
            _exact_dict(
                manifest,
                {
                    "build_id",
                    "compressed",
                    "dimensions",
                    "model_id",
                    "prior_state_id",
                    "raw",
                    "schema",
                    "sequence_number",
                    "state_id",
                    "transition_id",
                },
                "compressor state manifest",
            )
            build_id = _digest(manifest["build_id"], "state build_id")
            if build_id != expected_build_id:
                _poison("state package belongs to a different deployment build")
            if manifest["schema"] != STATE_SCHEMA or manifest["model_id"] != MODEL_ID:
                _poison("state package identity differs")
            dimensions = {
                "batch_capacity": INITIAL_BATCH_CAPACITY,
                "cache_capacity": INITIAL_CACHE_CAPACITY,
                "head_dim": HEAD_DIM,
                "projected_width": PROJECTED_WIDTH,
                "ratio": RATIO,
                "raw_slots": RAW_SLOTS,
            }
            if _json_payload(manifest["dimensions"]) != _json_payload(dimensions):
                _poison("state package dimensions differ")
            sequence_number = _integer(
                manifest["sequence_number"],
                "state sequence_number",
                minimum=0,
                maximum=(1 << 64) - 1,
            )
            prior_state_id = _optional_digest(
                manifest["prior_state_id"],
                "state prior_state_id",
            )
            transition_id = _optional_digest(
                manifest["transition_id"],
                "state transition_id",
            )
            if sequence_number == 0:
                if prior_state_id is not None or transition_id is not None:
                    _poison("initial state must not name a prior state or transition")
            elif prior_state_id is None or transition_id is None:
                _poison("successor state must bind its prior state and transition")

            raw_record = _exact_dict(
                manifest["raw"],
                {"kv", "lanes", "scores"},
                "state raw record",
            )
            compressed_record = _exact_dict(
                manifest["compressed"],
                {
                    "lane_active",
                    "next_positions",
                    "payload",
                    "session_ids",
                    "valid_prefix_lengths",
                    "versions",
                },
                "state compressed record",
            )
            raw_kv_descriptor = _validate_descriptor(
                raw_record["kv"],
                path="raw_kv.f32le",
                dtype="F32",
                shape=[INITIAL_BATCH_CAPACITY, RAW_SLOTS, PROJECTED_WIDTH],
                size_bytes=RAW_VALUES * 4,
                label="state raw KV descriptor",
            )
            raw_score_descriptor = _validate_descriptor(
                raw_record["scores"],
                path="raw_scores.f32le",
                dtype="F32",
                shape=[INITIAL_BATCH_CAPACITY, RAW_SLOTS, PROJECTED_WIDTH],
                size_bytes=RAW_VALUES * 4,
                label="state raw score descriptor",
            )
            compressed_descriptor = _validate_descriptor(
                compressed_record["payload"],
                path="compressed_kv.bf16le",
                dtype="BF16",
                shape=[
                    INITIAL_BATCH_CAPACITY,
                    INITIAL_CACHE_CAPACITY,
                    1,
                    HEAD_DIM,
                ],
                size_bytes=COMPRESSED_VALUES * 2,
                label="state compressed KV descriptor",
            )

            def read_descriptor(descriptor: dict[str, Any], label: str) -> bytes:
                source = root.open_file(
                    descriptor["path"],
                    label=label,
                    exact_size=descriptor["size_bytes"],
                    maximum_size=descriptor["size_bytes"],
                )
                payload = source.read_bytes(
                    label=label,
                    maximum_bytes=max(1, descriptor["size_bytes"]),
                )
                if _sha256(payload) != descriptor["sha256"]:
                    _poison(f"{label} differs from its descriptor digest")
                return payload

            raw_kv_payload = read_descriptor(raw_kv_descriptor, "state raw KV")
            raw_score_payload = read_descriptor(raw_score_descriptor, "state raw scores")
            compressed_payload = read_descriptor(
                compressed_descriptor,
                "state compressed KV",
            )
            raw_kv = _reshape3(
                _unpack_u32(raw_kv_payload, count=RAW_VALUES, label="state raw KV"),
                INITIAL_BATCH_CAPACITY,
                RAW_SLOTS,
                PROJECTED_WIDTH,
            )
            raw_scores = _reshape3(
                _unpack_u32(
                    raw_score_payload,
                    count=RAW_VALUES,
                    label="state raw scores",
                ),
                INITIAL_BATCH_CAPACITY,
                RAW_SLOTS,
                PROJECTED_WIDTH,
            )
            raw_lanes_value = raw_record["lanes"]
            if type(raw_lanes_value) is not list or len(raw_lanes_value) != INITIAL_BATCH_CAPACITY:
                _poison("state raw lanes differ")
            raw_lanes = []
            for index, raw_lane in enumerate(raw_lanes_value):
                lane = _exact_dict(
                    raw_lane,
                    {"next_pos", "session_id", "version"},
                    f"state raw lane {index}",
                )
                session_id = lane["session_id"]
                if session_id is not None:
                    session_id = _session(session_id, f"state raw lane {index} session")
                raw_lanes.append(
                    CompressionLaneState(
                        session_id,
                        lane["next_pos"],
                        lane["version"],
                    )
                )
            raw_state = compression_state_f32(
                raw_kv,
                raw_scores,
                tuple(raw_lanes),
                ratio=RATIO,
            )
            compressed_codes = _reshape4(
                _unpack_u16(
                    compressed_payload,
                    count=COMPRESSED_VALUES,
                    label="state compressed KV",
                ),
                INITIAL_BATCH_CAPACITY,
                INITIAL_CACHE_CAPACITY,
                1,
                HEAD_DIM,
            )
            compressed_state = compressed_kv_state_bf16(
                CompressedKVState(
                    ratio=RATIO,
                    bf16_codes=compressed_codes,
                    session_ids=tuple(compressed_record["session_ids"]),
                    lane_active=tuple(compressed_record["lane_active"]),
                    next_positions=tuple(compressed_record["next_positions"]),
                    valid_prefix_lengths=tuple(
                        compressed_record["valid_prefix_lengths"]
                    ),
                    versions=tuple(compressed_record["versions"]),
                )
            )
            expected_core = _state_core(
                build_id=build_id,
                sequence_number=sequence_number,
                prior_state_id=prior_state_id,
                transition_id=transition_id,
                raw_state=raw_state,
                compressed_state=compressed_state,
                raw_kv_payload=raw_kv_payload,
                raw_score_payload=raw_score_payload,
                compressed_payload=compressed_payload,
            )
            observed_core = {key: manifest[key] for key in manifest if key != "state_id"}
            if _json_payload(observed_core) != _json_payload(expected_core):
                _poison("state manifest differs from reconstructed state")
            state_id = _digest(manifest["state_id"], "state state_id")
            if _sha256(_json_payload(expected_core)) != state_id:
                _poison("state_id differs from reconstructed state core")
            root.verify()
    except DeepSeekV4CompressorExecutableServiceError:
        raise
    except Exception as exc:
        _poison(f"cannot load compressor state package: {exc}", exc)
    return CompressorStatePackage(
        root=root_path,
        state_id=state_id,
        build_id=build_id,
        sequence_number=sequence_number,
        prior_state_id=prior_state_id,
        transition_id=transition_id,
        raw_state=raw_state,
        compressed_state=compressed_state,
    )


def build_initial_deepseek_v4_compressor_state(
    deployment_dir: Path,
    output_dir: Path,
) -> CompressorStatePackage:
    """Publish the all-zero, uninitialized state for one verified deployment."""

    deployment = load_deepseek_v4_compressor_executable_deployment(deployment_dir)
    raw = zero_compression_state_f32(
        ratio=RATIO,
        batch_capacity=INITIAL_BATCH_CAPACITY,
        head_dim=HEAD_DIM,
    )
    compressed = zero_compressed_kv_state_bf16(
        ratio=RATIO,
        cache_capacity=INITIAL_CACHE_CAPACITY,
        kv_head_count=1,
        kv_value_width=HEAD_DIM,
        batch_capacity=INITIAL_BATCH_CAPACITY,
    )
    payloads, _ = _state_payloads(
        build_id=deployment.build_id,
        sequence_number=0,
        prior_state_id=None,
        transition_id=None,
        raw_state=raw,
        compressed_state=compressed,
    )
    try:
        publish_payload_tree(
            Path(output_dir),
            payloads=payloads,
            directories=[],
            label="DeepSeek V4 compressor initial state",
            maximum_depth=1,
            maximum_entries=8,
        )
    except SecureArtifactError as exc:
        _poison(f"cannot publish initial compressor state: {exc}", exc)
    return load_deepseek_v4_compressor_state(
        output_dir,
        expected_build_id=deployment.build_id,
    )


def _validate_projected_input(
    value: object,
    *,
    label: str,
    expected_batch: int | None = None,
    expected_sequence: int | None = None,
) -> tuple[tuple, int, int]:
    if type(value) not in {tuple, list} or not value:
        _poison(f"{label} must contain at least one batch")
    batch = len(value)
    if not 1 <= batch <= INITIAL_BATCH_CAPACITY or (
        expected_batch is not None and batch != expected_batch
    ):
        _poison(f"{label} batch extent differs")
    sequence_length: int | None = expected_sequence
    batches = []
    for batch_index, raw_sequence in enumerate(value):
        if type(raw_sequence) not in {tuple, list}:
            _poison(f"{label}[{batch_index}] must be an exact sequence")
        if sequence_length is None:
            sequence_length = len(raw_sequence)
            if not 1 <= sequence_length <= MAX_REQUEST_SEQUENCE:
                _poison(f"{label} sequence extent differs")
        elif len(raw_sequence) != sequence_length:
            _poison(f"{label} must be rectangular on sequence axis")
        rows = []
        for row_index, raw_row in enumerate(raw_sequence):
            if type(raw_row) not in {tuple, list} or len(raw_row) != PROJECTED_WIDTH:
                _poison(
                    f"{label}[{batch_index}][{row_index}] must contain "
                    f"exactly {PROJECTED_WIDTH} codes"
                )
            row = []
            for column, code in enumerate(raw_row):
                if type(code) is not int or not 0 <= code <= 0xFFFFFFFF:
                    _poison(f"{label} contains a non-binary32 encoding")
                decoded = decode_binary32(code)
                if not decoded.finite:
                    _poison(
                        f"{label}[{batch_index}][{row_index}][{column}] is nonfinite"
                    )
                row.append(code)
            rows.append(tuple(row))
        batches.append(tuple(rows))
    assert sequence_length is not None
    return tuple(batches), batch, sequence_length


def build_deepseek_v4_compressor_request(
    deployment_dir: Path,
    prior_state_dir: Path,
    output_dir: Path,
    *,
    projected_kv_f32_codes: object,
    projected_score_f32_codes: object,
    session_ids: object,
    start_pos: int,
) -> dict[str, Any]:
    """Publish one structurally valid request without pre-executing causality."""

    deployment = load_deepseek_v4_compressor_executable_deployment(deployment_dir)
    state = load_deepseek_v4_compressor_state(
        prior_state_dir,
        expected_build_id=deployment.build_id,
    )
    kv, batch_size, sequence_length = _validate_projected_input(
        projected_kv_f32_codes,
        label="projected KV",
    )
    scores, _, _ = _validate_projected_input(
        projected_score_f32_codes,
        label="projected scores",
        expected_batch=batch_size,
        expected_sequence=sequence_length,
    )
    start_pos = _integer(
        start_pos,
        "start_pos",
        minimum=0,
        maximum=INITIAL_CACHE_CAPACITY * RATIO - 1,
    )
    if start_pos > 0 and sequence_length != 1:
        _poison("decode request sequence length must be exactly one")
    if type(session_ids) not in {tuple, list} or len(session_ids) != batch_size:
        _poison("request session_ids must exactly match active batch size")
    sessions = tuple(
        _session(value, f"request session_ids[{index}]")
        for index, value in enumerate(session_ids)
    )
    if len(set(sessions)) != len(sessions):
        _poison("request session_ids must be unique")
    kv_payload = _pack_u32(kv, label="projected KV")
    score_payload = _pack_u32(scores, label="projected scores")
    core = {
        "batch_size": batch_size,
        "build_id": deployment.build_id,
        "expected_prior_state_id": state.state_id,
        "model_id": MODEL_ID,
        "program_sha256": PROGRAM_SHA256,
        "projected_kv": _descriptor(
            "inputs/projected_kv.f32le",
            kv_payload,
            dtype="F32",
            shape=[batch_size, sequence_length, PROJECTED_WIDTH],
        ),
        "projected_scores": _descriptor(
            "inputs/projected_scores.f32le",
            score_payload,
            dtype="F32",
            shape=[batch_size, sequence_length, PROJECTED_WIDTH],
        ),
        "schema": REQUEST_SCHEMA,
        "sequence_length": sequence_length,
        "session_ids": list(sessions),
        "start_pos": start_pos,
    }
    manifest = dict(core)
    manifest["request_id"] = _sha256(_json_payload(core))
    payloads = {
        "inputs/projected_kv.f32le": kv_payload,
        "inputs/projected_scores.f32le": score_payload,
        "request_manifest.json": _json_payload(manifest),
    }
    try:
        publish_payload_tree(
            Path(output_dir),
            payloads=payloads,
            directories=["inputs"],
            label="DeepSeek V4 compressor request",
            maximum_depth=2,
            maximum_entries=8,
        )
    except SecureArtifactError as exc:
        _poison(f"cannot publish compressor request: {exc}", exc)
    return manifest


@dataclass(frozen=True)
class CompressorRequest:
    root: Path
    request_id: str
    expected_prior_state_id: str
    batch_size: int
    sequence_length: int
    start_pos: int
    session_ids: tuple[str, ...]
    projected_kv: tuple
    projected_scores: tuple


def _load_request(
    request_dir: Path,
    *,
    deployment: CompressorDeployment,
) -> CompressorRequest:
    root_path = Path(request_dir).absolute()
    try:
        with SecureDirectory(root_path, label="compressor request") as root:
            files, directories = root.enumerate_tree(maximum_depth=2, maximum_entries=8)
            if files != {
                "inputs/projected_kv.f32le",
                "inputs/projected_scores.f32le",
                "request_manifest.json",
            } or directories != {"inputs"}:
                _poison("compressor request tree closure differs")
            manifest_file = root.open_file(
                "request_manifest.json",
                label="compressor request manifest",
                maximum_size=256 * 1024,
            )
            manifest_payload = manifest_file.read_bytes(
                label="compressor request manifest",
                maximum_bytes=256 * 1024,
            )
            manifest = _parse_json(manifest_payload, "compressor request manifest")
            _exact_dict(
                manifest,
                {
                    "batch_size",
                    "build_id",
                    "expected_prior_state_id",
                    "model_id",
                    "program_sha256",
                    "projected_kv",
                    "projected_scores",
                    "request_id",
                    "schema",
                    "sequence_length",
                    "session_ids",
                    "start_pos",
                },
                "compressor request manifest",
            )
            if (
                manifest["schema"] != REQUEST_SCHEMA
                or manifest["model_id"] != MODEL_ID
                or manifest["program_sha256"] != PROGRAM_SHA256
                or manifest["build_id"] != deployment.build_id
            ):
                _poison("compressor request deployment identity differs")
            batch_size = _integer(
                manifest["batch_size"],
                "request batch_size",
                minimum=1,
                maximum=INITIAL_BATCH_CAPACITY,
            )
            sequence_length = _integer(
                manifest["sequence_length"],
                "request sequence_length",
                minimum=1,
                maximum=MAX_REQUEST_SEQUENCE,
            )
            start_pos = _integer(
                manifest["start_pos"],
                "request start_pos",
                minimum=0,
                maximum=INITIAL_CACHE_CAPACITY * RATIO - 1,
            )
            if start_pos > 0 and sequence_length != 1:
                _poison("decode request sequence length must be one")
            raw_sessions = manifest["session_ids"]
            if type(raw_sessions) is not list or len(raw_sessions) != batch_size:
                _poison("request session_ids differ from batch size")
            sessions = tuple(
                _session(value, f"request session_ids[{index}]")
                for index, value in enumerate(raw_sessions)
            )
            if len(set(sessions)) != len(sessions):
                _poison("request session_ids must be unique")
            expected_prior = _digest(
                manifest["expected_prior_state_id"],
                "request expected_prior_state_id",
            )
            value_count = batch_size * sequence_length * PROJECTED_WIDTH

            def load_tensor(value: object, path: str, label: str) -> tuple:
                descriptor = _validate_descriptor(
                    value,
                    path=path,
                    dtype="F32",
                    shape=[batch_size, sequence_length, PROJECTED_WIDTH],
                    size_bytes=value_count * 4,
                    label=f"request {label} descriptor",
                )
                source = root.open_file(
                    path,
                    label=f"request {label}",
                    exact_size=value_count * 4,
                    maximum_size=MAX_INPUT_BYTES,
                )
                payload = source.read_bytes(
                    label=f"request {label}",
                    maximum_bytes=MAX_INPUT_BYTES,
                )
                if _sha256(payload) != descriptor["sha256"]:
                    _poison(f"request {label} digest differs")
                tensor = _reshape3(
                    _unpack_u32(payload, count=value_count, label=f"request {label}"),
                    batch_size,
                    sequence_length,
                    PROJECTED_WIDTH,
                )
                return _validate_projected_input(
                    tensor,
                    label=f"request {label}",
                    expected_batch=batch_size,
                    expected_sequence=sequence_length,
                )[0]

            projected_kv = load_tensor(
                manifest["projected_kv"],
                "inputs/projected_kv.f32le",
                "projected KV",
            )
            projected_scores = load_tensor(
                manifest["projected_scores"],
                "inputs/projected_scores.f32le",
                "projected scores",
            )
            core = {key: manifest[key] for key in manifest if key != "request_id"}
            request_id = _digest(manifest["request_id"], "request request_id")
            if _sha256(_json_payload(core)) != request_id:
                _poison("request_id differs from canonical request core")
            root.verify()
    except DeepSeekV4CompressorExecutableServiceError:
        raise
    except Exception as exc:
        _poison(f"cannot load compressor request: {exc}", exc)
    return CompressorRequest(
        root=root_path,
        request_id=request_id,
        expected_prior_state_id=expected_prior,
        batch_size=batch_size,
        sequence_length=sequence_length,
        start_pos=start_pos,
        session_ids=sessions,
        projected_kv=projected_kv,
        projected_scores=projected_scores,
    )


def _record(path: str, role: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "role": role,
        "sha256": _sha256(payload),
        "size_bytes": len(payload),
    }


@dataclass(frozen=True)
class CompressorExecutionResult:
    result_id: str
    transition_id: str
    prior_state_id: str
    state_id: str
    request_id: str
    should_compress: bool
    complete_group_count: int
    result_dir: Path
    state_dir: Path
    counters: dict[str, Any]


class DeepSeekV4CompressorExecutableServiceEngine:
    """Interpreter for the exact packaged compressor microprogram."""

    def __init__(self, deployment: CompressorDeployment):
        if type(deployment) is not CompressorDeployment:
            _poison("compressor deployment snapshot is invalid")
        self.deployment = deployment

    @classmethod
    def load(
        cls,
        deployment_dir: Path,
    ) -> "DeepSeekV4CompressorExecutableServiceEngine":
        return cls(load_deepseek_v4_compressor_executable_deployment(deployment_dir))

    def execute(
        self,
        prior_state_dir: Path,
        request_dir: Path,
        result_dir: Path,
    ) -> CompressorExecutionResult:
        """Execute all candidates and atomically publish their successor package."""

        output_root = Path(result_dir).absolute()
        if output_root.name in {"", ".", ".."} or output_root == Path(output_root.anchor):
            _poison("compressor result must name one non-root directory")
        state_output = output_root / "state"
        deployment = self.deployment
        deployment.verify_snapshot()
        prior = load_deepseek_v4_compressor_state(
            prior_state_dir,
            expected_build_id=deployment.build_id,
        )
        request = _load_request(request_dir, deployment=deployment)
        if request.expected_prior_state_id != prior.state_id:
            _poison("request expected_prior_state_id differs from supplied prior state")

        state_result = None
        pool_result = None
        conversion_result = None
        write_result = None
        view_result = None
        completed = False
        trace: list[dict[str, Any]] = []
        try:
            for slot, instruction in enumerate(deployment.instructions):
                opcode = instruction.opcode
                if opcode is CompressorOpcode.RAW_STATE_PREPARE:
                    if slot != 0 or state_result is not None:
                        _poison("RAW_STATE_PREPARE control flow differs")
                    state_result = compress_state_update_f32(
                        prior.raw_state,
                        request.projected_kv,
                        request.projected_scores,
                        deployment.ape_codes,
                        session_ids=request.session_ids,
                        start_pos=request.start_pos,
                    )
                    trace.append({"opcode": opcode.name, "slot": slot, "status": "executed"})
                elif opcode is CompressorOpcode.POOL_IF_READY:
                    if slot != 1 or state_result is None:
                        _poison("POOL_IF_READY control flow differs")
                    if state_result.should_compress:
                        if state_result.pool_inputs is None:
                            _poison("compression boundary omitted pool operands")
                        pool_result = compress_pool_f32(
                            state_result.pool_inputs.kv_f32_codes,
                            state_result.pool_inputs.score_f32_codes,
                            ratio=RATIO,
                        )
                        status = "executed"
                    else:
                        if state_result.pool_inputs is not None:
                            _poison("non-boundary transaction exposed pool operands")
                        status = "guard_false_no_payload"
                    trace.append({"opcode": opcode.name, "slot": slot, "status": status})
                elif opcode is CompressorOpcode.F32_TO_BF16_IF_READY:
                    if slot != 2 or state_result is None:
                        _poison("F32_TO_BF16_IF_READY control flow differs")
                    if pool_result is not None:
                        conversion_result = binary32_tensor_to_bf16_rne(
                            pool_result.pooled_f32_codes
                        )
                        status = "executed"
                    else:
                        status = "guard_false_no_payload"
                    trace.append({"opcode": opcode.name, "slot": slot, "status": status})
                elif opcode is CompressorOpcode.COMPRESSED_KV_COMMIT:
                    if slot != 3 or state_result is None or write_result is not None:
                        _poison("COMPRESSED_KV_COMMIT control flow differs")
                    if conversion_result is None:
                        cache_rows = ((),) * request.batch_size
                    else:
                        cache_rows = tuple(
                            tuple((row,) for row in sequence)
                            for sequence in conversion_result.bf16_codes
                        )
                    write_result = compressed_kv_write_bf16(
                        prior.compressed_state,
                        cache_rows,
                        active_session_ids=request.session_ids,
                        start_pos=request.start_pos,
                        sequence_length=request.sequence_length,
                    )
                    if bool(write_result.counters.completed_rows_per_batch) != bool(
                        conversion_result is not None
                    ):
                        _poison("compressed commit payload boundary differs from conversion")
                    trace.append({"opcode": opcode.name, "slot": slot, "status": "candidate_only"})
                elif opcode is CompressorOpcode.VALID_PREFIX_VIEW:
                    if slot != 4 or write_result is None or view_result is not None:
                        _poison("VALID_PREFIX_VIEW control flow differs")
                    view_result = compressed_kv_valid_view_bf16(
                        write_result.state,
                        active_session_ids=request.session_ids,
                    )
                    trace.append({"opcode": opcode.name, "slot": slot, "status": "candidate_only"})
                elif opcode is CompressorOpcode.COMPLETE:
                    if (
                        slot != len(deployment.instructions) - 1
                        or state_result is None
                        or write_result is None
                        or view_result is None
                        or completed
                    ):
                        _poison("COMPLETE control flow differs")
                    completed = True
                    trace.append({"opcode": opcode.name, "slot": slot, "status": "awaiting_publication"})
                else:  # pragma: no cover - deployment verifier freezes opcodes
                    _poison(f"unsupported compressor opcode {opcode}")
        except DeepSeekV4CompressorExecutableServiceError:
            raise
        except Exception as exc:
            _poison(f"compressor candidate execution poisoned: {exc}", exc)
        if not completed or state_result is None or write_result is None or view_result is None:
            _poison("compressor program did not reach a complete candidate")

        pooled_payload = (
            None
            if pool_result is None
            else _pack_u32(pool_result.pooled_f32_codes, label="pooled F32 output")
        )
        converted_payload = (
            None
            if conversion_result is None
            else _pack_u16(
                conversion_result.bf16_codes,
                label="converted BF16 output",
            )
        )
        view_payload = _pack_u16(view_result.bf16_codes, label="valid BF16 view")
        counters = {
            "compressed_kv_commit": asdict(write_result.counters),
            "conversion": None if conversion_result is None else asdict(conversion_result.counters),
            "logical_only": True,
            "physical_interpretation": None,
            "pool": None if pool_result is None else asdict(pool_result.counters),
            "published_transaction_commits": 1,
            "raw_state_prepare": asdict(state_result.counters),
            "schema": COUNTER_REPORT_SCHEMA,
            "valid_prefix_view": asdict(view_result.counters),
        }
        counter_payload = _json_payload(counters)
        output_hashes = {
            "converted_bf16_sha256": None if converted_payload is None else _sha256(converted_payload),
            "pooled_f32_sha256": None if pooled_payload is None else _sha256(pooled_payload),
            "valid_view_bf16_sha256": _sha256(view_payload),
        }
        transition_core = {
            "build_id": deployment.build_id,
            "counter_report_sha256": _sha256(counter_payload),
            "output_hashes": output_hashes,
            "prior_state_id": prior.state_id,
            "program_sha256": PROGRAM_SHA256,
            "request_id": request.request_id,
        }
        transition_id = _sha256(_json_payload(transition_core))
        state_payloads, state_manifest = _state_payloads(
            build_id=deployment.build_id,
            sequence_number=prior.sequence_number + 1,
            prior_state_id=prior.state_id,
            transition_id=transition_id,
            raw_state=state_result.state,
            compressed_state=write_result.state,
        )
        state_id = state_manifest["state_id"]
        execution_report = {
            "boundary": {
                "input": "post-wkv/wgate projected FP32 codes",
                "post_conversion_harness": (
                    "direct BF16 commit for transactional plumbing; official RMSNorm, "
                    "RoPE, and activation QDQ are outside this slice"
                ),
            },
            "build_id": deployment.build_id,
            "complete_group_count": state_result.counters.complete_group_count,
            "model_id": MODEL_ID,
            "output_hashes": output_hashes,
            "prior_state_id": prior.state_id,
            "program_sha256": PROGRAM_SHA256,
            "request_id": request.request_id,
            "schema": EXECUTION_REPORT_SCHEMA,
            "should_compress": state_result.should_compress,
            "state_id": state_id,
            "timing_claim": None,
            "trace": trace,
            "transition_id": transition_id,
        }
        execution_payload = _json_payload(execution_report)

        payloads: dict[str, bytes] = {
            "outputs/valid_view.bf16le": view_payload,
            "reports/counters.json": counter_payload,
            "reports/execution.json": execution_payload,
        }
        if pooled_payload is not None:
            payloads["outputs/pooled.f32le"] = pooled_payload
        if converted_payload is not None:
            payloads["outputs/converted.bf16le"] = converted_payload
        for path, payload in state_payloads.items():
            payloads[f"state/{path}"] = payload
        artifacts = [
            _record(
                path,
                (
                    "successor_state_artifact"
                    if path.startswith("state/")
                    else "counter_report"
                    if path == "reports/counters.json"
                    else "execution_report"
                    if path == "reports/execution.json"
                    else "valid_prefix_view"
                    if path == "outputs/valid_view.bf16le"
                    else "optional_pool_output_f32"
                    if path == "outputs/pooled.f32le"
                    else "optional_converted_output_bf16"
                ),
                payload,
            )
            for path, payload in sorted(payloads.items())
        ]
        result_core = {
            "artifacts": artifacts,
            "build_id": deployment.build_id,
            "counter_report": "reports/counters.json",
            "execution_report": "reports/execution.json",
            "model_id": MODEL_ID,
            "optional_outputs": {
                "converted_bf16": (
                    None if converted_payload is None else "outputs/converted.bf16le"
                ),
                "pooled_f32": None if pooled_payload is None else "outputs/pooled.f32le",
            },
            "prior_state_id": prior.state_id,
            "program_sha256": PROGRAM_SHA256,
            "request_id": request.request_id,
            "schema": RESULT_SCHEMA,
            "state_id": state_id,
            "state_manifest": "state/state_manifest.json",
            "transition_id": transition_id,
            "valid_view": "outputs/valid_view.bf16le",
        }
        result_manifest = dict(result_core)
        result_manifest["result_id"] = _sha256(_json_payload(result_core))
        payloads["result_manifest.json"] = _json_payload(result_manifest)
        directories = sorted(
            {
                parent.as_posix()
                for path in payloads
                for parent in Path(path).parents
                if parent != Path(".")
            }
        )

        deployment.verify_snapshot()
        # Re-read the prior package immediately before publication.  Any poison
        # leaves it untouched and the create-once result namespace absent.
        confirmed_prior = load_deepseek_v4_compressor_state(
            prior_state_dir,
            expected_build_id=deployment.build_id,
        )
        if confirmed_prior.state_id != prior.state_id:
            _poison("prior compressor state changed before publication")
        try:
            publish_payload_tree(
                output_root,
                payloads=payloads,
                directories=directories,
                label="DeepSeek V4 compressor execution result",
                maximum_depth=3,
                maximum_entries=32,
            )
        except SecureArtifactError as exc:
            _poison(f"cannot atomically publish compressor result: {exc}", exc)
        successor = load_deepseek_v4_compressor_state(
            state_output,
            expected_build_id=deployment.build_id,
        )
        if (
            successor.state_id != state_id
            or successor.prior_state_id != prior.state_id
            or successor.transition_id != transition_id
        ):
            _poison("published compressor successor state differs")
        return CompressorExecutionResult(
            result_id=result_manifest["result_id"],
            transition_id=transition_id,
            prior_state_id=prior.state_id,
            state_id=state_id,
            request_id=request.request_id,
            should_compress=state_result.should_compress,
            complete_group_count=state_result.counters.complete_group_count,
            result_dir=output_root,
            state_dir=state_output,
            counters=counters,
        )


def execute_deepseek_v4_compressor_executable_deployment(
    deployment_dir: Path,
    prior_state_dir: Path,
    request_dir: Path,
    result_dir: Path,
) -> CompressorExecutionResult:
    """Load the deployment and execute exactly one immutable transition."""

    engine = DeepSeekV4CompressorExecutableServiceEngine.load(deployment_dir)
    return engine.execute(prior_state_dir, request_dir, result_dir)


__all__ = [
    "COUNTER_REPORT_SCHEMA",
    "CompressorDeployment",
    "CompressorExecutionResult",
    "CompressorRequest",
    "CompressorStatePackage",
    "DeepSeekV4CompressorExecutableServiceEngine",
    "DeepSeekV4CompressorExecutableServiceError",
    "EXECUTION_REPORT_SCHEMA",
    "INITIAL_BATCH_CAPACITY",
    "INITIAL_CACHE_CAPACITY",
    "MAX_REQUEST_SEQUENCE",
    "REQUEST_SCHEMA",
    "RESULT_SCHEMA",
    "STATE_SCHEMA",
    "build_deepseek_v4_compressor_request",
    "build_initial_deepseek_v4_compressor_state",
    "execute_deepseek_v4_compressor_executable_deployment",
    "load_deepseek_v4_compressor_executable_deployment",
    "load_deepseek_v4_compressor_state",
]
