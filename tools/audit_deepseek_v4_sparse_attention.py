#!/usr/bin/env python3
"""Audit the exact released DeepSeek V4 sparse-attention TileLang kernel.

This is an opt-in development audit, not an ordinary CI test.  It executes the
content-pinned official kernel through TileLang 0.1.8 on the governed CUDA/SM120
stack and compares every BF16 output with the independent OpenTallas target
reference.  The generated JSON excludes timings, timestamps, and host paths so
an identical environment and payload can reproduce it byte-for-byte.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from fractions import Fraction
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import platform
import random
import shutil
import struct
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.reference.formats import encode_bf16_rne  # noqa: E402
from runtime.reference.sparse_attention import (  # noqa: E402
    KERNEL_SOURCE_SHA256,
    SPARSE_ATTENTION_SCALE_BINARY32,
    sparse_attention_bf16,
)


SCHEMA = "opentallas.deepseek_v4_sparse_attention_tilelang_audit.v1"
SOURCE_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
SOURCE_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
TORCH_VERSION = "2.10.0+cu128"
CUDA_VERSION = "12.8"
TILELANG_VERSION = "0.1.8"
TVM_FFI_VERSION = "0.1.8.post2"
Z3_VERSION = "4.14.1.0"
TORCH_DLPACK_VERSION = "0.1.5"
EXPECTED_COMPUTE_CAPABILITY = (12, 0)
FULL_SINK_SHA256 = (
    "2f93e2a35c5ad1dbd4aaff353a46082d6811e7b896bf388583bd05e023c2844f"
)
LAYER0_RANK0_SINK_SHA256 = (
    "71685540a438556a8c98f009de9e8026ebca43b09c810bb4bf06be26de1f8616"
)
INDEX_SHA256 = "f3c3546d46307d66e2c5186b50d882b60f1507f05f3c322ab4c387134831f7b2"

WHEEL_SHA256 = {
    "apache_tvm_ffi-0.1.8.post2-cp310-cp310-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl": (
        "ef922ef3ed971a4e161a0385ef9f67af379d52b0d83d62c08b79f6707b6660b5"
    ),
    "tilelang-0.1.8-cp38-abi3-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl": (
        "5a4018e581f55c852d98a42d3b4acf2dbcfb8b7d8b9156ba7c6b0ab61600a10c"
    ),
    "torch_c_dlpack_ext-0.1.5-cp310-cp310-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl": (
        "c7468df84ec152d930fbc3acf460c44a60b3462b95af3d3a676d133629c7e176"
    ),
    "z3_solver-4.14.1.0-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl": (
        "dc8e48fa2855f6f7fa5fda450a5f7f042651f447835e5a2db531960658eb012d"
    ),
}

CORPORA = (
    {
        "id": "exact_eighths",
        "seed": 0x5350_4152_5345_5841,
        "generator": "uniform_integer_-8_to_8_divided_by_8_then_bf16_rne",
        "expected_input_sha256": (
            "87c7dea88b04c90289062d486bd06b7f0636adc4a641295fd917676d636950c2"
        ),
        "expected_query_sha256": (
            "33258dbcf5b587cd07bcf0295cea04c6121127e3f1f82c0571eb6945c849a1ff"
        ),
        "expected_kv_sha256": (
            "343404f1d1d39edacb59e3fbd3cd67205a243e240f5ec12b04cc569eb221d672"
        ),
        "expected_official_output_sha256": (
            "ba327ffb5c554ff940aa0175dd6584c04cdb8b166f345bc466a940f179af9a6b"
        ),
        "expected_reference_output_sha256": (
            "ba327ffb5c554ff940aa0175dd6584c04cdb8b166f345bc466a940f179af9a6b"
        ),
        "expected_difference_count": 0,
    },
    {
        "id": "broad_bf16",
        "seed": 0x5350_4152_5345_4F46,
        "generator": (
            "uniform_sign_exponent_119_to_129_fraction_0_to_127_bf16_codes"
        ),
        "expected_input_sha256": (
            "c6693d9bc07368d6ba94be6067b238f9088fe651235c8d23622b8766dcbd4e2d"
        ),
        "expected_query_sha256": (
            "666567c54c075741d9e4d3628ce435e191ad80f231929d6b02706c2f3f05276d"
        ),
        "expected_kv_sha256": (
            "a39f8e4f2ce9788aeb16f4806da6f5bb1306874b03c978ca7de279438355b8c1"
        ),
        "expected_official_output_sha256": (
            "bb527d4d81562448cbbcaa0af9083f4789de79994090a27d7fc19c1358d3897c"
        ),
        "expected_reference_output_sha256": (
            "9f90441e6f04c9beec175c46f27c7794eaf361c12cbe6320f6958783921656b8"
        ),
        "expected_difference_count": 3,
    },
)


class AuditError(RuntimeError):
    """Raised when an audit prerequisite or expected result differs."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_exact(path: Path, size: int, label: str) -> bytes:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise AuditError(f"cannot read {label}: {exc}") from exc
    if len(payload) != size:
        raise AuditError(f"{label} has {len(payload)} bytes, expected {size}")
    return payload


def _installed_version(distribution: str, expected: str) -> str:
    try:
        observed = importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError as exc:
        raise AuditError(f"required distribution {distribution} is not installed") from exc
    if observed != expected:
        raise AuditError(
            f"{distribution} version {observed!r} differs from required {expected!r}"
        )
    return observed


def _verify_wheels(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for name, expected_sha256 in sorted(WHEEL_SHA256.items()):
        path = root / name
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise AuditError(f"cannot read governed wheel {name}: {exc}") from exc
        observed_sha256 = _sha256(payload)
        if observed_sha256 != expected_sha256:
            raise AuditError(
                f"wheel {name} SHA-256 {observed_sha256} differs from "
                f"{expected_sha256}"
            )
        records.append(
            {
                "filename": name,
                "sha256": observed_sha256,
                "size_bytes": len(payload),
            }
        )
    return records


def _verify_environment(wheel_root: Path) -> dict[str, Any]:
    import torch

    versions = {
        "apache-tvm-ffi": _installed_version("apache-tvm-ffi", TVM_FFI_VERSION),
        "tilelang": _installed_version("tilelang", TILELANG_VERSION),
        "torch": _installed_version("torch", TORCH_VERSION),
        "torch-c-dlpack-ext": _installed_version(
            "torch-c-dlpack-ext", TORCH_DLPACK_VERSION
        ),
        "z3-solver": _installed_version("z3-solver", Z3_VERSION),
    }
    if torch.version.cuda != CUDA_VERSION:
        raise AuditError(
            f"PyTorch CUDA {torch.version.cuda!r} differs from {CUDA_VERSION!r}"
        )
    if not torch.cuda.is_available():
        raise AuditError("CUDA is unavailable")
    capability = tuple(torch.cuda.get_device_capability())
    if capability != EXPECTED_COMPUTE_CAPABILITY:
        raise AuditError(
            f"compute capability {capability} differs from "
            f"{EXPECTED_COMPUTE_CAPABILITY}"
        )

    nvcc = shutil.which("nvcc")
    if nvcc is None:
        raise AuditError("nvcc is not on PATH")
    completed = subprocess.run(
        [nvcc, "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    nvcc_output = (completed.stdout + completed.stderr).strip()
    if completed.returncode != 0 or "release 12.8" not in nvcc_output:
        raise AuditError("nvcc is not the governed CUDA 12.8 compiler")
    version_line = next(
        (line.strip() for line in nvcc_output.splitlines() if "release" in line),
        "",
    )
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi is None:
        raise AuditError("nvidia-smi is not on PATH")
    driver_query = subprocess.run(
        [
            nvidia_smi,
            "--query-gpu=driver_version",
            "--format=csv,noheader,nounits",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    driver_versions = tuple(
        line.strip()
        for line in driver_query.stdout.splitlines()
        if line.strip()
    )
    if driver_query.returncode != 0 or len(driver_versions) != 1:
        raise AuditError("cannot resolve exactly one NVIDIA driver version")

    return {
        "compute_capability": list(capability),
        "cuda_compiler": version_line,
        "gpu_name": torch.cuda.get_device_name(),
        "kernel_platform": platform.platform(),
        "nvidia_driver": driver_versions[0],
        "package_versions": versions,
        "python": platform.python_version(),
        "pytorch_cuda": torch.version.cuda,
        "wheel_artifacts": _verify_wheels(wheel_root),
    }


def _canonical_sink_payload(root: Path) -> tuple[bytes, dict[str, Any]]:
    chunks: list[bytes] = []
    for scope, count in (("layers", 43), ("mtp", 3)):
        for layer in range(count):
            for rank in range(4):
                path = (
                    root
                    / "ranks"
                    / f"rank-{rank:03d}"
                    / f"{scope}.{layer}.attn.attn_sink.bin"
                )
                chunks.append(_read_exact(path, 64, "attention-sink shard"))
    payload = b"".join(chunks)
    if _sha256(payload) != FULL_SINK_SHA256:
        raise AuditError("complete canonical attention-sink payload hash differs")
    values = struct.unpack(f"<{len(payload) // 4}f", payload)
    codes = struct.unpack(f"<{len(payload) // 4}I", payload)
    if not all(value == value and abs(value) != float("inf") for value in values):
        raise AuditError("canonical attention-sink payload contains a nonfinite value")
    minimum_index = min(range(len(values)), key=values.__getitem__)
    maximum_index = max(range(len(values)), key=values.__getitem__)
    return payload, {
        "byte_count": len(payload),
        "negative_count": sum(value < 0 for value in values),
        "positive_count": sum(value > 0 for value in values),
        "sha256": _sha256(payload),
        "value_count": len(values),
        "value_maximum": {
            "binary32_code": f"0x{codes[maximum_index]:08x}",
            "value": repr(values[maximum_index]),
        },
        "value_minimum": {
            "binary32_code": f"0x{codes[minimum_index]:08x}",
            "value": repr(values[minimum_index]),
        },
        "zero_count": sum(value == 0 for value in values),
    }


def _random_bf16(rng: random.Random) -> int:
    return (
        (rng.randrange(2) << 15)
        | (rng.randrange(119, 130) << 7)
        | rng.randrange(128)
    )


def _build_codes(corpus: dict[str, Any]) -> tuple[Any, Any]:
    rng = random.Random(corpus["seed"])
    if corpus["id"] == "exact_eighths":
        values = tuple(
            encode_bf16_rne(Fraction(integer, 8)).code
            for integer in range(-8, 9)
        )

        def generate() -> int:
            return values[rng.randrange(len(values))]

    elif corpus["id"] == "broad_bf16":

        def generate() -> int:
            return _random_bf16(rng)

    else:  # pragma: no cover - governed constant invariant
        raise AuditError(f"unknown corpus {corpus['id']!r}")

    query = tuple(
        tuple(
            tuple(tuple(generate() for _ in range(512)) for _ in range(16))
            for _ in range(1)
        )
        for _ in range(1)
    )
    kv = tuple(
        tuple(tuple(generate() for _ in range(512)) for _ in range(12))
        for _ in range(1)
    )
    return query, kv


def _pack_query(query: Any) -> bytes:
    flattened = [
        code
        for batch in query
        for position in batch
        for head in position
        for code in head
    ]
    if len(flattened) != 8192:
        raise AuditError("query fixture element count differs")
    return struct.pack("<8192H", *flattened)


def _pack_kv(kv: Any) -> bytes:
    flattened = [code for batch in kv for row in batch for code in row]
    if len(flattened) != 6144:
        raise AuditError("KV fixture element count differs")
    return struct.pack("<6144H", *flattened)


def _load_official_kernel(path: Path):
    payload = _read_exact(path, path.stat().st_size, "official kernel source")
    observed_sha256 = _sha256(payload)
    if observed_sha256 != KERNEL_SOURCE_SHA256:
        raise AuditError(
            f"official kernel SHA-256 {observed_sha256} differs from "
            f"{KERNEL_SOURCE_SHA256}"
        )
    spec = importlib.util.spec_from_file_location(
        "opentallas_pinned_deepseek_v4_kernel",
        path,
    )
    if spec is None or spec.loader is None:
        raise AuditError("cannot construct official kernel module loader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _audit_corpus(
    official_module: Any,
    corpus: dict[str, Any],
    sink_bytes: bytes,
    index_values: tuple[int, ...],
) -> dict[str, Any]:
    import torch

    query, kv = _build_codes(corpus)
    query_bytes = _pack_query(query)
    kv_bytes = _pack_kv(kv)
    index_bytes = struct.pack("<70i", *index_values)
    input_sha256 = _sha256(query_bytes + kv_bytes + sink_bytes + index_bytes)
    observed_hashes = {
        "input": input_sha256,
        "query": _sha256(query_bytes),
        "kv": _sha256(kv_bytes),
    }
    expected_hashes = {
        "input": corpus["expected_input_sha256"],
        "query": corpus["expected_query_sha256"],
        "kv": corpus["expected_kv_sha256"],
    }
    if observed_hashes != expected_hashes:
        raise AuditError(
            f"{corpus['id']} generated input hashes differ: "
            f"{observed_hashes!r} != {expected_hashes!r}"
        )

    sink_codes = struct.unpack("<16I", sink_bytes)
    query_native = torch.tensor(query, dtype=torch.uint16).view(torch.bfloat16).cuda()
    kv_native = torch.tensor(kv, dtype=torch.uint16).view(torch.bfloat16).cuda()
    sink_native = torch.tensor(sink_codes, dtype=torch.uint32).view(torch.float32).cuda()
    index_native = torch.tensor(
        index_values,
        dtype=torch.int32,
        device="cuda",
    ).view(1, 1, -1)
    official_output = official_module.sparse_attn(
        query_native,
        kv_native,
        sink_native,
        index_native,
        512**-0.5,
    )
    torch.cuda.synchronize()
    official_codes = tuple(
        int(code) & 0xFFFF
        for code in official_output.view(torch.int16).reshape(-1).cpu().tolist()
    )

    reference_result = sparse_attention_bf16(
        query,
        kv,
        sink_codes,
        ((index_values,),),
        scale_binary32=SPARSE_ATTENTION_SCALE_BINARY32,
    )
    reference_codes = tuple(
        code
        for batch in reference_result.values
        for position in batch
        for head in position
        for code in head
    )
    if len(official_codes) != 8192 or len(reference_codes) != 8192:
        raise AuditError("sparse-attention output element count differs")

    official_bytes = struct.pack("<8192H", *official_codes)
    reference_bytes = struct.pack("<8192H", *reference_codes)
    official_sha256 = _sha256(official_bytes)
    reference_sha256 = _sha256(reference_bytes)
    if official_sha256 != corpus["expected_official_output_sha256"]:
        raise AuditError(f"{corpus['id']} official output hash differs")
    if reference_sha256 != corpus["expected_reference_output_sha256"]:
        raise AuditError(f"{corpus['id']} reference output hash differs")

    differences: list[dict[str, Any]] = []
    raw_difference_count = 0
    for index, (official_code, reference_code) in enumerate(
        zip(official_codes, reference_codes, strict=True)
    ):
        if official_code != reference_code:
            raw_difference_count += 1
        canonical_official = (
            0 if official_code & 0x7FFF == 0 else official_code
        )
        if canonical_official == reference_code:
            continue
        same_sign = official_code >> 15 == reference_code >> 15
        differences.append(
            {
                "flat_output_index": index,
                "official_bf16": f"0x{official_code:04x}",
                "reference_bf16": f"0x{reference_code:04x}",
                "same_sign": same_sign,
                "same_sign_code_steps": (
                    abs(official_code - reference_code) if same_sign else None
                ),
            }
        )
    if len(differences) != corpus["expected_difference_count"]:
        raise AuditError(
            f"{corpus['id']} difference count {len(differences)} differs from "
            f"{corpus['expected_difference_count']}"
        )

    return {
        "difference_count_after_positive_zero_canonicalization": len(differences),
        "differences": differences,
        "generator": corpus["generator"],
        "id": corpus["id"],
        "input": {
            "combined_sha256": input_sha256,
            "index_sha256": _sha256(index_bytes),
            "kv_sha256": _sha256(kv_bytes),
            "query_sha256": _sha256(query_bytes),
            "seed_hex": f"0x{corpus['seed']:016x}",
            "sink_sha256": _sha256(sink_bytes),
        },
        "logical_reference_counters": asdict(reference_result.counters),
        "official_output_sha256": official_sha256,
        "output_bf16_value_count": len(reference_codes),
        "raw_difference_count": raw_difference_count,
        "reference_output_sha256": reference_sha256,
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", required=True, type=Path)
    parser.add_argument("--canonical-mp4", required=True, type=Path)
    parser.add_argument("--wheel-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    arguments = _arguments()
    environment = _verify_environment(arguments.wheel_dir)
    _, sink_audit = _canonical_sink_payload(arguments.canonical_mp4)
    sink_path = (
        arguments.canonical_mp4
        / "ranks/rank-000/layers.0.attn.attn_sink.bin"
    )
    sink_bytes = _read_exact(sink_path, 64, "layer-0 rank-0 attention sink")
    if _sha256(sink_bytes) != LAYER0_RANK0_SINK_SHA256:
        raise AuditError("layer-0 rank-0 attention-sink hash differs")

    index_values = (
        0,
        1,
        -1,
        2,
        2,
        3,
        4,
        -1,
        5,
        *([-1] * 55),
        6,
        7,
        8,
        -1,
        9,
        10,
    )
    if len(index_values) != 70 or _sha256(struct.pack("<70i", *index_values)) != INDEX_SHA256:
        raise AuditError("governed selected-index fixture differs")

    official_module = _load_official_kernel(arguments.kernel)
    corpus_results = [
        _audit_corpus(official_module, corpus, sink_bytes, index_values)
        for corpus in CORPORA
    ]
    result = {
        "claim_boundary": {
            "establishes": [
                "exact released sparse-attention kernel execution under the declared development stack",
                "bounded official-kernel versus deterministic-target output differences",
                "real canonical checkpoint attention-sink payload identity",
            ],
            "does_not_establish": [
                "universal TileLang or GPU bit identity",
                "checkpoint-derived query or KV attention known answers",
                "service-engine or RTL conformance",
                "cycles, bandwidth, energy, PPA, or GPU product performance",
            ],
        },
        "corpora": corpus_results,
        "environment": environment,
        "schema": SCHEMA,
        "sink_payload_audit": sink_audit,
        "source": {
            "kernel_sha256": KERNEL_SOURCE_SHA256,
            "repository": SOURCE_REPOSITORY,
            "revision": SOURCE_REVISION,
        },
        "status": "bounded_differential_complete",
    }
    payload = (
        json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(payload)
    print(
        json.dumps(
            {
                "output_sha256": _sha256(payload),
                "status": result["status"],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        print(f"AUDIT ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
