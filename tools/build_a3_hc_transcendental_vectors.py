#!/usr/bin/env python3
"""Build independent CR32 exponential/sigmoid RTL vectors.

Expected finite codes come from the exact-rational reference lane, which is
independent of the fixed-point interval RTL.  The matrix spans directed MPFR
sentinels, thresholds, subnormals, normals, and deterministic full-code-space
samples.  These are reusable arithmetic vectors, not model outputs or TPOT.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.reference.hyper_connection import (  # noqa: E402
    binary32_exp_rne,
    binary32_sigmoid_rne,
)


DEFAULT_OUTPUT = ROOT / "testdata/rtl/a3_hc_transcendental"
SCHEMA = "opentallas.rtl.a3_hc_transcendental_vectors.v1"
RANDOM_SEED = 0xA3_E5_510D
RANDOM_PER_OPERATION = 2048

OP_EXP_NONPOS = 0
OP_SIGMOID = 1
ERR_NONE = 0
ERR_ARGUMENT = 1

DIRECTED = (
    0x00000000,
    0x80000000,
    0x00000001,
    0x80000001,
    0x007FFFFF,
    0x807FFFFF,
    0x00800000,
    0x80800000,
    0x33800000,
    0xB3800000,
    0x3DCCCCCD,
    0xBDCCCCCD,
    0x3EAAAAAB,
    0xBEAAAAAB,
    0x3F000000,
    0xBF000000,
    0x3F800000,
    0xBF800000,
    0x3FC00000,
    0xBFC00000,
    0x40000000,
    0xC0000000,
    0x40400000,
    0xC0400000,
    0x40E00000,
    0xC0E00000,
    0x41200000,
    0xC1200000,
    0x41A00000,
    0xC1A00000,
    0x41C7FFFF,
    0x41C80000,
    0x41C80001,
    0x42480000,
    0xC2480000,
    0x42A00000,
    0xC2A00000,
    0x42C7FFFF,
    0xC2C7FFFF,
    0x42C80000,
    0xC2C80000,
    0x4315FFFF,
    0xC315FFFF,
    0x43160000,
    0xC3160000,
    0x43160001,
    0xC3160001,
    0x7F7FFFFF,
    0xFF7FFFFF,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def finite(code: int) -> bool:
    return ((code >> 23) & 0xFF) != 0xFF


def case(operation: int, code: int) -> dict[str, int]:
    if not finite(code):
        return {
            "operation": operation,
            "argument": code,
            "expected": 0,
            "error": ERR_ARGUMENT,
        }
    if operation == OP_EXP_NONPOS and not (code & 0x80000000) and code & 0x7FFFFFFF:
        return {
            "operation": operation,
            "argument": code,
            "expected": 0,
            "error": ERR_ARGUMENT,
        }
    expected = (
        binary32_exp_rne(code)
        if operation == OP_EXP_NONPOS
        else binary32_sigmoid_rne(code)
    )
    return {
        "operation": operation,
        "argument": code,
        "expected": expected,
        "error": ERR_NONE,
    }


def build(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    rng = random.Random(RANDOM_SEED)
    pairs: list[tuple[int, int]] = []
    for code in DIRECTED:
        pairs.append((OP_SIGMOID, code))
        pairs.append((OP_EXP_NONPOS, code))
    pairs.extend(
        (OP_SIGMOID, rng.getrandbits(32))
        for _ in range(RANDOM_PER_OPERATION)
    )
    pairs.extend(
        (OP_EXP_NONPOS, rng.getrandbits(31) | 0x80000000)
        for _ in range(RANDOM_PER_OPERATION)
    )
    # Explicit nonfinite and positive-exp refusals survive de-duplication.
    pairs.extend(
        (
            (OP_SIGMOID, 0x7F800000),
            (OP_SIGMOID, 0xFF800000),
            (OP_SIGMOID, 0x7FC00001),
            (OP_EXP_NONPOS, 0x7F800000),
            (OP_EXP_NONPOS, 0xFF800000),
            (OP_EXP_NONPOS, 0x7FC00001),
            (OP_EXP_NONPOS, 0x00000001),
            (OP_EXP_NONPOS, 0x3F800000),
            (OP_EXP_NONPOS, 0x42C80000),
        )
    )

    unique: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for pair in pairs:
        if pair not in seen:
            unique.append(pair)
            seen.add(pair)
    cases = [case(operation, code) for operation, code in unique]
    words = [
        item[field]
        for item in cases
        for field in ("operation", "argument", "expected", "error")
    ]
    image = "".join(f"{word:08x}\n" for word in words).encode("ascii")

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "independent_exact_vectors",
        "case_words": 4,
        "case_count": len(cases),
        "counts": {
            "exp": sum(item["operation"] == OP_EXP_NONPOS for item in cases),
            "sigmoid": sum(item["operation"] == OP_SIGMOID for item in cases),
            "accepted": sum(item["error"] == ERR_NONE for item in cases),
            "refused": sum(item["error"] != ERR_NONE for item in cases),
        },
        "random_seed": RANDOM_SEED,
        "random_per_operation": RANDOM_PER_OPERATION,
        "directed_codes": [f"{code:08x}" for code in DIRECTED],
        "oracle": {
            "implementation": "runtime.reference.hyper_connection exact rational interval lane",
            "source": "runtime/reference/hyper_connection.py",
            "source_sha256": sha256(ROOT / "runtime/reference/hyper_connection.py"),
            "host_math_used": False,
            "rtl_implementation_imported": False,
        },
        "claim_boundary": {
            "reusable_arithmetic_vectors": True,
            "checkpoint_reachable_domain_complete": False,
            "full_hc_pre": False,
            "model_token_generation": False,
            "architectural_timing": False,
            "tpot": False,
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "cases.hex").write_bytes(image)
    body["image_sha256"] = sha256_bytes(image)
    body["vector_set_id"] = sha256_bytes(canonical(body))
    (output / "index.json").write_text(
        json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    return body


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build(args.output)
    print(
        "built HC transcendental vectors: "
        f"{result['case_count']} cases, {result['counts']['refused']} refusals"
    )


if __name__ == "__main__":
    main()
