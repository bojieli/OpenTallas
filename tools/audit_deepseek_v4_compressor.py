#!/usr/bin/env python3
"""Audit released DeepSeek V4 compressor APE and bounded source behavior.

This opt-in evidence tool byte-range fetches every compressor APE tensor from
the pinned public checkpoint, validates its exact metadata and payload, then
executes the unmodified pinned ``Compressor.forward`` and
``overlap_transform`` methods with projection/normalization/QDQ test doubles.
The test doubles isolate the compressor-pooling boundary; the official methods
still perform APE addition, overlap assembly, softmax, weighted reduction, and
the visible BF16 conversion.

The output deliberately contains no timings, timestamps, or local paths.  It
does not measure service cycles, bandwidth, energy, area, or PPA.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import concurrent.futures
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import random
import struct
import subprocess
import sys
import types
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.ir.model import canonical_json_bytes  # noqa: E402
from runtime.reference.compression_pool import (  # noqa: E402
    compress_pool_prefill_f32,
)
from runtime.reference.formats import binary32_bits_to_bf16_rne  # noqa: E402


SCHEMA = "opentallas.deepseek_v4_compressor_audit.v1"
SOURCE_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
SOURCE_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
INDEX_SHA256 = "98efab455cf08dfbbbaaba6f570e1bf10bf927d2b4c3c453a59c2f6f0e3be92b"
TORCH_VERSION = "2.10.0+cu128"
CUDA_VERSION = "12.8"
EXPECTED_COMPUTE_CAPABILITY = (12, 0)

COMPRESSOR_CLASS_LINES = (285, 383)
COMPRESSOR_CLASS_SHA256 = (
    "7d1cc51b4e19ccd10d083d00a57b4fd3e219d65ab17cd72febe328c2c7fb9ef5"
)
OVERLAP_METHOD_LINES = (313, 320)
OVERLAP_METHOD_SHA256 = (
    "6b956922a6c32d1c3986e20730a69a81326c5b904e70cd6abf7a6da2775088cd"
)
FORWARD_METHOD_LINES = (322, 383)
FORWARD_METHOD_SHA256 = (
    "892ce7ca46af7a150a7370253743c33602bb63edd3736960a700756ac38c8bac"
)

EXPECTED_APE_TENSOR_COUNT = 62
EXPECTED_APE_VALUE_COUNT = 1_418_240
EXPECTED_APE_BYTE_COUNT = 5_672_960
EXPECTED_APE_SHA256 = (
    "ad6333d91c83b72c3fc426ea712b91446ef4020eac1dc39a299d9e56ab288ea4"
)
EXPECTED_APE_PROFILES = {
    (4, 256): {
        "byte_count": 86_016,
        "sha256": "fed11b86399a41f1e89255f993a17aa7f889e7d69ffcb3f7175211f7c3336dfd",
        "tensor_count": 21,
    },
    (4, 1024): {
        "byte_count": 344_064,
        "sha256": "0005f188b47d4183093f7c20b8a351462a3eaaef6b4e2c562924baf3d2a3a65e",
        "tensor_count": 21,
    },
    (128, 512): {
        "byte_count": 5_242_880,
        "sha256": "73c7f7030dd68cd8715571272915b1ae11253fe08fd63ae41043b988df60a4aa",
        "tensor_count": 20,
    },
}
DIFFERENTIAL_APE_TENSOR = "layers.2.attn.compressor.ape"
DIFFERENTIAL_APE_SHA256 = (
    "f93afef4a88371262663f89f026a48b79f7187bd9d6498742c1db2860ae73554"
)
DIFFERENTIAL_SEED = 0x434F_4D50_4E41_5449
EXPECTED_DIFFERENTIALS = {
    "ape_cancelled_exact": {
        "input_sha256": "083adaf2657f00daf8c07ca2245bdce346f24f02fc78f298ef721a326175fb3d",
        "kv_sha256": "c8e3abe2fa2962ebc6df61ca1aa82e3cbbfac349dd7466ad69da13dfa61b99b2",
        "score_sha256": "0fe5a5a0ec1e545805a58404413fb1a759d511c377e9f08ddb2df685b23ecb8f",
        "target_output_sha256": "539d6235e9e75c4e4dd051b1dec413a5e21ea4b7670f22f7431141039ba9bcef",
        "official_output_sha256": "539d6235e9e75c4e4dd051b1dec413a5e21ea4b7670f22f7431141039ba9bcef",
        "difference_count": 0,
        "difference": None,
    },
    "broad_exact_eighths": {
        "input_sha256": "af18df60051642d6f3612cd391a63036ec2994d2c13537373d2887bee32ad038",
        "kv_sha256": "c853754428ccffd2d195fb54f45e3b379479b27c2608bba90a7ac7130bbe2a50",
        "score_sha256": "b1a7c75cbe84957d79a5c6bcbb6ae52dc579e36dbc6ecd4d790804f8c40b7000",
        "target_output_sha256": "545368262c0155f705ba9c5c691df299f5d3de15c0f49ea6da01a175f2294bb9",
        "official_output_sha256": "e14f1ede0bcf8ed7149cb1eeb52c024a0a520cf7e433a2f0a13ae71ee455adcb",
        "difference_count": 1,
        "difference": {
            "flat_index": 672,
            "official_bf16": "0x3d08",
            "ordered_encoding_steps": 1,
            "target_bf16": "0x3d09",
        },
    },
}
EXPECTED_FULL_REPORT_SHA256 = (
    "d14c2b33d9cfc105af9ba3dc18c4ac3b749a203bd0a6b0d3f1d8592315651324"
)


class AuditError(RuntimeError):
    """Raised when a pinned prerequisite or expected result differs."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _strict_json(path: Path) -> Any:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise AuditError(f"duplicate JSON key {key!r} in {path.name}")
            output[key] = value
        return output

    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=object_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot parse {path.name}: {exc}") from exc


def _source_slice(lines: list[bytes], line_range: tuple[int, int]) -> bytes:
    start, stop = line_range
    if len(lines) < stop:
        raise AuditError("pinned model source is shorter than the audited methods")
    return b"".join(lines[start - 1 : stop])


def _audit_source(path: Path) -> tuple[bytes, dict[str, Any]]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise AuditError(f"cannot read pinned model source: {exc}") from exc
    if _sha256(payload) != MODEL_SOURCE_SHA256:
        raise AuditError("model source SHA-256 differs from the pinned release")
    lines = payload.splitlines(keepends=True)
    methods = []
    for name, line_range, expected in (
        ("Compressor", COMPRESSOR_CLASS_LINES, COMPRESSOR_CLASS_SHA256),
        ("Compressor.overlap_transform", OVERLAP_METHOD_LINES, OVERLAP_METHOD_SHA256),
        ("Compressor.forward", FORWARD_METHOD_LINES, FORWARD_METHOD_SHA256),
    ):
        method_payload = _source_slice(lines, line_range)
        observed = _sha256(method_payload)
        if observed != expected:
            raise AuditError(f"{name} source slice SHA-256 differs")
        methods.append(
            {
                "byte_count": len(method_payload),
                "line_start": line_range[0],
                "line_stop_inclusive": line_range[1],
                "name": name,
                "sha256": observed,
            }
        )
    return payload, {"method_slices": methods, "sha256": _sha256(payload)}


def _range_fetch(url: str, start: int, stop_inclusive: int) -> bytes:
    request = Request(
        url,
        headers={
            "Range": f"bytes={start}-{stop_inclusive}",
            "User-Agent": "OpenTallas-evidence-audit/1",
        },
    )
    try:
        with urlopen(request, timeout=120) as response:
            payload = response.read()
            status = response.status
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise AuditError(f"byte-range fetch failed: {exc}") from exc
    expected = stop_inclusive - start + 1
    if status != 206 or len(payload) != expected:
        raise AuditError(
            f"byte-range response was status {status} with {len(payload)} bytes, "
            f"expected status 206 and {expected} bytes"
        )
    return payload


def _checkpoint_records(
    *,
    index_path: Path,
    header_dir: Path,
) -> list[dict[str, Any]]:
    try:
        index_payload = index_path.read_bytes()
    except OSError as exc:
        raise AuditError(f"cannot read checkpoint index: {exc}") from exc
    if _sha256(index_payload) != INDEX_SHA256:
        raise AuditError("checkpoint index SHA-256 differs from the pinned release")
    index = _strict_json(index_path)
    if type(index) is not dict or type(index.get("weight_map")) is not dict:
        raise AuditError("checkpoint index has no exact weight_map object")

    records: list[dict[str, Any]] = []
    header_cache: dict[str, dict[str, Any]] = {}
    for name, shard in sorted(index["weight_map"].items()):
        if not name.endswith("compressor.ape"):
            continue
        if type(shard) is not str or not shard.endswith(".safetensors"):
            raise AuditError(f"APE tensor {name!r} has an invalid shard")
        if shard not in header_cache:
            header = _strict_json(header_dir / f"{shard}.json")
            if type(header) is not dict:
                raise AuditError(f"header for {shard} is not an object")
            header_cache[shard] = header
        tensor = header_cache[shard].get(name)
        if type(tensor) is not dict or set(tensor) != {
            "data_offsets",
            "dtype",
            "shape",
        }:
            raise AuditError(f"APE tensor {name!r} has invalid header metadata")
        offsets = tensor["data_offsets"]
        shape = tensor["shape"]
        if (
            tensor["dtype"] != "F32"
            or type(offsets) is not list
            or len(offsets) != 2
            or any(type(value) is not int for value in offsets)
            or not 0 <= offsets[0] < offsets[1]
            or type(shape) is not list
            or len(shape) != 2
            or any(type(value) is not int or value <= 0 for value in shape)
        ):
            raise AuditError(f"APE tensor {name!r} metadata is malformed")
        profile = (shape[0], shape[1])
        if profile not in EXPECTED_APE_PROFILES:
            raise AuditError(f"APE tensor {name!r} has unexpected shape {shape}")
        expected_bytes = shape[0] * shape[1] * 4
        if offsets[1] - offsets[0] != expected_bytes:
            raise AuditError(f"APE tensor {name!r} byte extent differs from shape")
        records.append(
            {
                "data_stop": offsets[1],
                "data_start": offsets[0],
                "dtype": "F32",
                "name": name,
                "shape": shape,
                "shard": shard,
            }
        )
    if len(records) != EXPECTED_APE_TENSOR_COUNT:
        raise AuditError(
            f"found {len(records)} compressor APE tensors, expected "
            f"{EXPECTED_APE_TENSOR_COUNT}"
        )
    observed_profiles = Counter(tuple(record["shape"]) for record in records)
    expected_profiles = Counter(
        {
            profile: expectation["tensor_count"]
            for profile, expectation in EXPECTED_APE_PROFILES.items()
        }
    )
    if observed_profiles != expected_profiles:
        raise AuditError("compressor APE profile counts differ")
    return records


def _fetch_ape_payloads(
    records: list[dict[str, Any]],
    *,
    base_url: str,
) -> list[tuple[dict[str, Any], bytes]]:
    shards = sorted({record["shard"] for record in records})

    def header_length(shard: str) -> tuple[str, int]:
        payload = _range_fetch(f"{base_url}/{shard}", 0, 7)
        return shard, struct.unpack("<Q", payload)[0]

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        header_lengths = dict(executor.map(header_length, shards))

    def fetch(record: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
        base = 8 + header_lengths[record["shard"]]
        payload = _range_fetch(
            f"{base_url}/{record['shard']}",
            base + record["data_start"],
            base + record["data_stop"] - 1,
        )
        return record, payload

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        fetched = list(executor.map(fetch, records))
    return fetched


def _ape_report(
    fetched: list[tuple[dict[str, Any], bytes]],
) -> tuple[dict[str, Any], dict[str, bytes]]:
    aggregate = b"".join(payload for _, payload in fetched)
    if len(aggregate) != EXPECTED_APE_BYTE_COUNT or _sha256(aggregate) != EXPECTED_APE_SHA256:
        raise AuditError("aggregate compressor APE payload differs")

    profile_payloads: defaultdict[tuple[int, int], list[bytes]] = defaultdict(list)
    tensor_payloads: dict[str, bytes] = {}
    tensor_reports: list[dict[str, Any]] = []
    values: list[tuple[float, int, str, int]] = []
    for record, payload in fetched:
        profile = tuple(record["shape"])
        profile_payloads[profile].append(payload)
        tensor_payloads[record["name"]] = payload
        tensor_reports.append(
            {
                "byte_count": len(payload),
                "dtype": record["dtype"],
                "name": record["name"],
                "sha256": _sha256(payload),
                "shape": record["shape"],
                "shard": record["shard"],
            }
        )
        floats = struct.unpack(f"<{len(payload) // 4}f", payload)
        codes = struct.unpack(f"<{len(payload) // 4}I", payload)
        values.extend(
            (value, code, record["name"], index)
            for index, (value, code) in enumerate(zip(floats, codes, strict=True))
        )
    if len(values) != EXPECTED_APE_VALUE_COUNT or any(
        not math.isfinite(value) for value, _, _, _ in values
    ):
        raise AuditError("compressor APE value count or finiteness differs")

    profiles = []
    for profile in sorted(profile_payloads):
        payload = b"".join(profile_payloads[profile])
        expectation = EXPECTED_APE_PROFILES[profile]
        if len(payload) != expectation["byte_count"] or _sha256(payload) != expectation["sha256"]:
            raise AuditError(f"compressor APE profile {profile} differs")
        profiles.append(
            {
                "byte_count": len(payload),
                "sha256": _sha256(payload),
                "shape": list(profile),
                "tensor_count": len(profile_payloads[profile]),
            }
        )

    minimum = min(values, key=lambda item: item[0])
    maximum = max(values, key=lambda item: item[0])
    return (
        {
            "aggregate_sha256": _sha256(aggregate),
            "byte_count": len(aggregate),
            "finite_value_count": len(values),
            "maximum": {
                "binary32_code": f"0x{maximum[1]:08x}",
                "flat_tensor_index": maximum[3],
                "tensor": maximum[2],
                "value": repr(maximum[0]),
            },
            "minimum": {
                "binary32_code": f"0x{minimum[1]:08x}",
                "flat_tensor_index": minimum[3],
                "tensor": minimum[2],
                "value": repr(minimum[0]),
            },
            "negative_value_count": sum(value < 0 for value, _, _, _ in values),
            "positive_value_count": sum(value > 0 for value, _, _, _ in values),
            "profiles": profiles,
            "tensor_count": len(fetched),
            "tensors": tensor_reports,
            "zero_value_count": sum(value == 0 for value, _, _, _ in values),
        },
        tensor_payloads,
    )


def _signed_i32(code: int) -> int:
    return code if code < 1 << 31 else code - (1 << 32)


def _nested_signed(value: Any) -> Any:
    if type(value) is tuple:
        return [_nested_signed(item) for item in value]
    return _signed_i32(value)


def _flatten_codes(value: Any) -> tuple[int, ...]:
    result: list[int] = []

    def visit(item: Any) -> None:
        if type(item) is tuple:
            for child in item:
                visit(child)
        else:
            result.append(item)

    visit(value)
    return tuple(result)


def _u32_payload(codes: Any) -> bytes:
    flat = _flatten_codes(codes)
    return struct.pack(f"<{len(flat)}I", *flat)


def _u16_payload(codes: Any) -> bytes:
    flat = _flatten_codes(codes)
    return struct.pack(f"<{len(flat)}H", *flat)


def _float_code(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def _corpora(ape: tuple[tuple[int, ...], ...]) -> list[dict[str, Any]]:
    exact_scores = (
        tuple(
            tuple(code ^ 0x80000000 for code in ape[phase])
            for _group in range(2)
            for phase in range(4)
        ),
    )
    exact_kv = (
        tuple(
            tuple(_float_code(((position * 1024 + column) % 17 - 8) / 8) for column in range(1024))
            for position in range(8)
        ),
    )
    rng = random.Random(DIFFERENTIAL_SEED)

    def broad_code() -> int:
        return _float_code(rng.randint(-32, 32) / 8)

    broad_kv = (tuple(tuple(broad_code() for _ in range(1024)) for _ in range(8)),)
    broad_scores = (
        tuple(tuple(broad_code() for _ in range(1024)) for _ in range(8)),
    )
    return [
        {
            "generator": "ape_sign_flip_uniform_softmax_and_exact_eighth_kv",
            "id": "ape_cancelled_exact",
            "kv": exact_kv,
            "scores": exact_scores,
            "seed": None,
        },
        {
            "generator": "uniform_integer_-32_to_32_divided_by_8_binary32",
            "id": "broad_exact_eighths",
            "kv": broad_kv,
            "scores": broad_scores,
            "seed": DIFFERENTIAL_SEED,
        },
    ]


def _load_official_module(model_path: Path) -> Any:
    fake_kernel = types.ModuleType("kernel")
    for name in (
        "act_quant",
        "fp4_act_quant",
        "fp8_gemm",
        "fp4_gemm",
        "sparse_attn",
        "hc_split_sinkhorn",
    ):
        setattr(fake_kernel, name, lambda *args, **kwargs: None)
    previous_kernel = sys.modules.get("kernel")
    module_name = "opentallas_pinned_deepseek_v4_model_audit"
    previous_module = sys.modules.get(module_name)
    sys.modules["kernel"] = fake_kernel
    try:
        spec = importlib.util.spec_from_file_location(module_name, model_path)
        if spec is None or spec.loader is None:
            raise AuditError("cannot construct pinned model module spec")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception as exc:
        raise AuditError(f"cannot import pinned model source: {exc}") from exc
    finally:
        if previous_kernel is None:
            sys.modules.pop("kernel", None)
        else:
            sys.modules["kernel"] = previous_kernel
        if previous_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous_module


def _source_forward(
    module: Any,
    *,
    kv: Any,
    scores: Any,
    ape: Any,
    device: str,
) -> tuple[int, ...]:
    import torch

    class Project(torch.nn.Module):
        def __init__(self, tensor: Any):
            super().__init__()
            self.tensor = tensor

        def forward(self, _value: Any) -> Any:
            return self.tensor

    class NormCapture(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.seen: Any = None

        def forward(self, value: Any) -> Any:
            self.seen = value.detach().clone()
            return value

    def tensor32(codes: Any) -> Any:
        return torch.tensor(
            _nested_signed(codes),
            dtype=torch.int32,
            device=device,
        ).view(torch.float32)

    args = module.ModelArgs(
        dim=1,
        max_batch_size=1,
        max_seq_len=16,
    )
    compressor = module.Compressor(args, 4, 512, False).to(device)
    compressor.ape.data.copy_(tensor32(ape))
    compressor.kv_cache = torch.zeros(
        1,
        4,
        512,
        dtype=torch.bfloat16,
        device=device,
    )
    compressor.freqs_cis = torch.ones(
        16,
        32,
        dtype=torch.complex64,
        device=device,
    )
    compressor.wkv = Project(tensor32(kv))
    compressor.wgate = Project(tensor32(scores))
    capture = NormCapture()
    compressor.norm = capture
    module.apply_rotary_emb = lambda value, *args, **kwargs: value
    module.act_quant = lambda *args, **kwargs: None
    dummy = torch.zeros(1, 8, 1, dtype=torch.bfloat16, device=device)
    output = compressor(dummy, 0)
    if output is None or capture.seen is None or capture.seen.dtype != torch.bfloat16:
        raise AuditError("official compressor did not expose the expected BF16 boundary")
    return tuple(
        int(code)
        for code in capture.seen.view(torch.uint16).reshape(-1).cpu().tolist()
    )


def _ordered_bf16(code: int) -> int:
    return (~code & 0xFFFF) if code >> 15 else code | 0x8000


def _environment(*, require_cuda: bool) -> dict[str, Any]:
    import torch

    if str(torch.__version__) != TORCH_VERSION:
        raise AuditError(
            f"PyTorch version {torch.__version__!s} differs from {TORCH_VERSION}"
        )
    environment: dict[str, Any] = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "pytorch": str(torch.__version__),
        "pytorch_cuda": torch.version.cuda,
    }
    if require_cuda:
        if not torch.cuda.is_available() or torch.version.cuda != CUDA_VERSION:
            raise AuditError("the governed CUDA 12.8 PyTorch runtime is unavailable")
        capability = tuple(torch.cuda.get_device_capability())
        if capability != EXPECTED_COMPUTE_CAPABILITY:
            raise AuditError(
                f"compute capability {capability} differs from "
                f"{EXPECTED_COMPUTE_CAPABILITY}"
            )
        query = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=driver_version",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        drivers = [line.strip() for line in query.stdout.splitlines() if line.strip()]
        if query.returncode != 0 or len(drivers) != 1:
            raise AuditError("cannot resolve exactly one NVIDIA driver")
        environment.update(
            {
                "compute_capability": list(capability),
                "gpu_name": torch.cuda.get_device_name(),
                "nvidia_driver": drivers[0],
            }
        )
    return environment


def _differential_report(
    *,
    module: Any,
    ape_payload: bytes,
    require_cuda: bool,
) -> list[dict[str, Any]]:
    if len(ape_payload) != 4 * 1024 * 4 or _sha256(ape_payload) != DIFFERENTIAL_APE_SHA256:
        raise AuditError("differential APE tensor differs")
    flat_ape = struct.unpack("<4096I", ape_payload)
    ape = tuple(tuple(flat_ape[start : start + 1024]) for start in range(0, 4096, 1024))
    devices = ["cpu", *( ["cuda"] if require_cuda else [] )]
    reports = []
    for corpus in _corpora(ape):
        target = compress_pool_prefill_f32(
            corpus["kv"],
            corpus["scores"],
            ape,
            ratio=4,
        )
        target_bf16 = tuple(
            binary32_bits_to_bf16_rne(code).code
            for code in _flatten_codes(target.pooled_f32_codes)
        )
        device_reports = []
        for device in devices:
            observed = _source_forward(
                module,
                kv=corpus["kv"],
                scores=corpus["scores"],
                ape=ape,
                device=device,
            )
            differences = [
                {
                    "flat_index": index,
                    "official_bf16": f"0x{official:04x}",
                    "target_bf16": f"0x{expected:04x}",
                    "ordered_encoding_steps": abs(
                        _ordered_bf16(official) - _ordered_bf16(expected)
                    ),
                }
                for index, (official, expected) in enumerate(
                    zip(observed, target_bf16, strict=True)
                )
                if official != expected
            ]
            device_reports.append(
                {
                    "device": device,
                    "difference_count": len(differences),
                    "differences": differences,
                    "maximum_ordered_encoding_steps": max(
                        (record["ordered_encoding_steps"] for record in differences),
                        default=0,
                    ),
                    "official_output_sha256": _sha256(_u16_payload(observed)),
                }
            )
        reports.append(
            {
                "ape_sha256": _sha256(ape_payload),
                "ape_tensor": DIFFERENTIAL_APE_TENSOR,
                "device_results": device_reports,
                "generator": corpus["generator"],
                "id": corpus["id"],
                "input_sha256": _sha256(
                    _u32_payload(corpus["kv"])
                    + _u32_payload(corpus["scores"])
                    + ape_payload
                ),
                "kv_sha256": _sha256(_u32_payload(corpus["kv"])),
                "output_bf16_value_count": len(target_bf16),
                "score_sha256": _sha256(_u32_payload(corpus["scores"])),
                "seed": corpus["seed"],
                "target_output_sha256": _sha256(_u16_payload(target_bf16)),
            }
        )
    for report in reports:
        expected = EXPECTED_DIFFERENTIALS[report["id"]]
        for key in (
            "input_sha256",
            "kv_sha256",
            "score_sha256",
            "target_output_sha256",
        ):
            if report[key] != expected[key]:
                raise AuditError(
                    f"{report['id']} {key} differs from the governed corpus"
                )
        for device in report["device_results"]:
            if (
                device["official_output_sha256"]
                != expected["official_output_sha256"]
                or device["difference_count"] != expected["difference_count"]
                or device["maximum_ordered_encoding_steps"]
                != int(expected["difference_count"] > 0)
            ):
                raise AuditError(
                    f"{report['id']} {device['device']} differential differs"
                )
            expected_differences = (
                [] if expected["difference"] is None else [expected["difference"]]
            )
            if device["differences"] != expected_differences:
                raise AuditError(
                    f"{report['id']} {device['device']} difference detail differs"
                )
    return reports


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--header-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--base-url",
        default=(
            f"https://huggingface.co/{SOURCE_REPOSITORY}/resolve/{SOURCE_REVISION}"
        ),
    )
    parser.add_argument(
        "--cpu-only",
        action="store_true",
        help="omit the governed CUDA/SM120 differential",
    )
    args = parser.parse_args()

    _, source_report = _audit_source(args.model)
    records = _checkpoint_records(
        index_path=args.index,
        header_dir=args.header_dir,
    )
    fetched = _fetch_ape_payloads(records, base_url=args.base_url.rstrip("/"))
    ape_report, tensor_payloads = _ape_report(fetched)
    environment = _environment(require_cuda=not args.cpu_only)
    module = _load_official_module(args.model)
    differentials = _differential_report(
        module=module,
        ape_payload=tensor_payloads[DIFFERENTIAL_APE_TENSOR],
        require_cuda=not args.cpu_only,
    )
    report = {
        "ape_checkpoint_audit": ape_report,
        "claim_boundary": {
            "establishes": [
                "exact released compressor APE payload identity and finite range",
                "independent deterministic pool numeric target",
                "bounded official Compressor.forward and overlap_transform differential",
                "explicit raw-state and compressed-cache transaction contracts",
            ],
            "does_not_establish": [
                "checkpoint-derived compressor projection inputs",
                "complete layer or model execution",
                "service-engine or RTL execution",
                "cycles bandwidth latency energy area PPA or GPU advantage",
            ],
        },
        "environment": environment,
        "method_differentials": differentials,
        "schema": SCHEMA,
        "source": {
            "model": source_report,
            "repository": SOURCE_REPOSITORY,
            "revision": SOURCE_REVISION,
        },
    }
    payload = canonical_json_bytes(report)
    if not args.cpu_only and _sha256(payload) != EXPECTED_FULL_REPORT_SHA256:
        raise AuditError("complete governed report SHA-256 differs")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    print(_sha256(payload))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        print(f"audit error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
