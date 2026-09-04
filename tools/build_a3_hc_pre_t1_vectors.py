#!/usr/bin/env python3
"""Build exact arithmetic and descriptor vectors for T=1 DeepSeek HC_PRE RTL.

The fused-product-add cases use a self-contained ``Fraction`` oracle with
integer ties-to-even encoding.  The complete token witness is recomputed by
the independent immutable HC_PRE reference from retained, authenticated
checkpoint inputs.  Its final 24 coefficient words must also match the first
token of the separately retained T=512 functional qualification.

The two descriptor configurations are derived from the current shipped ROM
PC15 and HBM PC14 images.  This vector build does not execute RTL, produce a
model token, handle EOS, or establish architectural timing/TPOT.
"""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random
import struct
import sys
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.reference.formats import NumericReferenceError  # noqa: E402
from runtime.reference.hyper_connection import (  # noqa: E402
    HCPreReferenceError,
    hc_pre_bf16,
)
from tools import build_a3_mhc_pre_tile_vectors as tile_vectors  # noqa: E402


CHECKPOINT_ROOT = ROOT / "testdata/rtl/a3_hc_pre_t1_checkpoint"
CHECKPOINT_MANIFEST = CHECKPOINT_ROOT / "index.json"
OUTPUT_ROOT = ROOT / "testdata/rtl/a3_hc_pre_t1"
QUALIFICATION_VECTOR = (
    ROOT / "testdata/runtime/deepseek_hbm_hc_pre_t512/qualification_vector.json"
)
QUALIFIED_WEIGHTS = QUALIFICATION_VECTOR.parent / "expected_pc14_weights.u32le"
QUALIFIED_COMBINATION = (
    QUALIFICATION_VECTOR.parent / "expected_pc14_combination.u32le"
)

FMA_RANDOM_SEED = 0xA3_F4_0001
FMA_RANDOM_CASES = 4_096
FMA_CASE_WORDS = 5
EXPECTED_WORDS = 74
META_WORDS = 8
ERR_NONE = 0
ERR_ARGUMENT = 1
ERR_OVERFLOW = 2
MAX_FINITE = 0x7F7FFFFF

VECTOR_FILES = (
    "meta.hex",
    "fma_cases.hex",
    "expected.hex",
    "rom_config.hex",
    "hbm_config.hex",
    "index.json",
)

EXPECTED_SENTINEL = (
    0x3B98E318,
    0x416A36CF,
    0x3F5CB07B,
    0x3F86E1DC,
    0x3F99F43A,
    0x40022165,
    0xC07F64E9,
    0xC1FC94BE,
    0xC20E28AF,
    0xC1AECD52,
    0x3F5E0909,
    0xBF5DFC47,
    0xB91CE523,
    0xB8448C94,
    0xB7CD3F13,
    0x3F1FC894,
    0xBF4D03E9,
    0x3E3FEBA4,
    0xB7EFB241,
    0x3F86913C,
    0x3F647021,
    0xBFF8BBE5,
    0x3EA726BF,
    0xB95DA937,
    0xB90A961A,
    0xBEA73D53,
    0x4149E890,
    0x4176CEA8,
    0x418CDA33,
    0x41EE1CC5,
    0xC269A8EB,
    0xC3E71609,
    0xC4020F9F,
    0xC39FED1A,
    0x414B23CC,
    0xC14B1820,
    0xBB0F8B09,
    0xBA33D294,
    0xB9BBC799,
    0x41122F8D,
    0xC13B9178,
    0x402F967B,
    0xB9DB4C41,
    0x41763B21,
    0x4150FF67,
    0xC1E39100,
    0x4098ED34,
    0xBB4ACC21,
    0xBAFD95BF,
    0xC09901DC,
    0x3F800008,
    0x3F800008,
    0x3F800008,
    0x3F800008,
    0x3D5DD097,
    0x320CDE79,
    0x322ADE6C,
    0x36E5FAB7,
    0x3F693333,
    0x3B6033A5,
    0x3BEAC4CA,
    0x3AB4E3C5,
    0x2FB009DA,
    0x3F6789D7,
    0x3957C48D,
    0x3DF6328B,
    0x2F258B30,
    0x3DBBFE9C,
    0x3F7DEEB4,
    0x3483C7CA,
    0x3DB665EC,
    0x39B07FFB,
    0x3A38D206,
    0x3F60DF28,
)


class VectorError(RuntimeError):
    """A retained source or exact arithmetic relationship did not hold."""


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VectorError(message)


def pow2(exponent: int) -> Fraction:
    return Fraction(1 << exponent) if exponent >= 0 else Fraction(1, 1 << -exponent)


def decode_fp32(code: int) -> Fraction:
    require(0 <= code < 1 << 32, "FP32 code outside 32 bits")
    exponent = (code >> 23) & 0xFF
    fraction = code & 0x7FFFFF
    if exponent == 0xFF:
        raise ArithmeticError("nonfinite FP32")
    magnitude = (
        Fraction(fraction) * pow2(-149)
        if exponent == 0
        else Fraction((1 << 23) | fraction) * pow2(exponent - 150)
    )
    return -magnitude if code >> 31 else magnitude


def decode_bf16(code: int) -> Fraction:
    require(0 <= code < 1 << 16, "BF16 code outside 16 bits")
    exponent = (code >> 7) & 0xFF
    fraction = code & 0x7F
    if exponent == 0xFF:
        raise ArithmeticError("nonfinite BF16")
    magnitude = (
        Fraction(fraction) * pow2(-133)
        if exponent == 0
        else Fraction((1 << 7) | fraction) * pow2(exponent - 134)
    )
    return -magnitude if code >> 15 else magnitude


def round_integer(value: Fraction) -> int:
    require(value >= 0, "round_integer requires a nonnegative input")
    quotient, remainder = divmod(value.numerator, value.denominator)
    twice = remainder << 1
    if twice > value.denominator or (twice == value.denominator and quotient & 1):
        quotient += 1
    return quotient


def floor_log2(value: Fraction) -> int:
    require(value > 0, "floor_log2 requires a positive input")
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if value < pow2(exponent):
        exponent -= 1
    return exponent


def encode_fp32_rne(value: Fraction) -> int:
    if value == 0:
        return 0
    sign = 0x80000000 if value < 0 else 0
    magnitude = abs(value)
    if magnitude < pow2(-126):
        significand = round_integer(magnitude / pow2(-149))
        if significand == 0:
            return 0
        if significand < 1 << 23:
            return sign | significand
        return sign | 0x00800000
    exponent = floor_log2(magnitude)
    significand = round_integer(magnitude / pow2(exponent - 23))
    if significand == 1 << 24:
        significand = 1 << 23
        exponent += 1
    if exponent > 127:
        raise OverflowError("finite FP32 overflow")
    require(1 << 23 <= significand < 1 << 24, "normal significand invariant")
    return sign | ((exponent + 127) << 23) | (significand - (1 << 23))


def fma_oracle(accumulator: int, activation: int, weight: int) -> tuple[int, int]:
    try:
        exact = decode_fp32(accumulator)
        exact += decode_bf16(activation) * decode_fp32(weight)
        return encode_fp32_rne(exact), ERR_NONE
    except OverflowError:
        return 0, ERR_OVERFLOW
    except ArithmeticError:
        return 0, ERR_ARGUMENT


def finite_fp32(rng: random.Random) -> int:
    while True:
        code = rng.getrandbits(32)
        if ((code >> 23) & 0xFF) != 0xFF:
            return code


def finite_bf16(rng: random.Random) -> int:
    while True:
        code = rng.getrandbits(16)
        if ((code >> 7) & 0xFF) != 0xFF:
            return code


def fma_cases() -> tuple[list[dict[str, int | str]], dict[str, int]]:
    directed = [
        ("all_positive_zero", 0x00000000, 0x0000, 0x00000000),
        ("signed_zero_inputs", 0x80000000, 0x8000, 0x80000000),
        ("one_plus_one", 0x3F800000, 0x3F80, 0x3F800000),
        ("exact_cancellation", 0xBF800000, 0x3F80, 0x3F800000),
        ("negative_product", 0x3F000000, 0xBF80, 0x3F800000),
        ("minimum_subnormal_accumulator", 0x00000001, 0x0001, 0x00000001),
        ("subnormal_weight", 0x00000000, 0x7F7F, 0x00000001),
        ("largest_finite_accumulator", MAX_FINITE, 0x0000, MAX_FINITE),
        ("positive_overflow", MAX_FINITE, 0x7F7F, MAX_FINITE),
        ("negative_overflow", 0xFF7FFFFF, 0xFF7F, MAX_FINITE),
        ("accumulator_infinity", 0x7F800000, 0x3F80, 0x3F800000),
        ("accumulator_nan", 0x7FC00001, 0x3F80, 0x3F800000),
        ("activation_infinity", 0x00000000, 0x7F80, 0x3F800000),
        ("activation_nan", 0x00000000, 0x7FC1, 0x3F800000),
        ("weight_infinity", 0x00000000, 0x3F80, 0x7F800000),
        ("weight_nan", 0x00000000, 0x3F80, 0x7FC00001),
    ]
    cases: list[dict[str, int | str]] = []
    for name, accumulator, activation, weight in directed:
        result, error = fma_oracle(accumulator, activation, weight)
        cases.append(
            {
                "name": name,
                "category": "directed",
                "accumulator": accumulator,
                "activation": activation,
                "weight": weight,
                "result": result,
                "error": error,
            }
        )

    rng = random.Random(FMA_RANDOM_SEED)
    fused_differences = 0
    for index in range(FMA_RANDOM_CASES):
        accumulator = finite_fp32(rng)
        activation = finite_bf16(rng)
        weight = finite_fp32(rng)
        result, error = fma_oracle(accumulator, activation, weight)
        if error == ERR_NONE:
            try:
                separately_rounded = encode_fp32_rne(
                    decode_fp32(accumulator)
                    + decode_fp32(encode_fp32_rne(decode_bf16(activation) * decode_fp32(weight)))
                )
            except OverflowError:
                separately_rounded = -1
            if separately_rounded != result:
                fused_differences += 1
        cases.append(
            {
                "name": f"random_{index:04d}",
                "category": "random_finite",
                "accumulator": accumulator,
                "activation": activation,
                "weight": weight,
                "result": result,
                "error": error,
            }
        )
    counts = Counter(int(case["error"]) for case in cases)
    return cases, {
        "total": len(cases),
        "directed": len(directed),
        "random_finite": FMA_RANDOM_CASES,
        "success": counts[ERR_NONE],
        "argument_errors": counts[ERR_ARGUMENT],
        "overflow_errors": counts[ERR_OVERFLOW],
        "fused_differs_from_separate_rounding": fused_differences,
    }


def read_hex(path: Path) -> tuple[int, ...]:
    return tuple(int(line, 16) for line in path.read_text().splitlines() if line.strip())


def hex_payload(values: Iterable[int], digits: int = 8) -> bytes:
    mask = (1 << (digits * 4)) - 1
    return "".join(f"{int(value) & mask:0{digits}x}\n" for value in values).encode(
        "ascii"
    )


def verify_checkpoint_inputs() -> tuple[dict[str, Any], dict[str, tuple[int, ...]]]:
    raw = CHECKPOINT_MANIFEST.read_bytes()
    manifest = json.loads(raw)
    require(manifest.get("schema") == "opentallas.rtl.a3_hc_pre_t1_checkpoint.v1", "checkpoint vector schema drift")
    without_id = dict(manifest)
    observed_id = without_id.pop("manifest_id", None)
    require(observed_id == sha256_bytes(canonical(without_id)), "checkpoint manifest ID drift")
    values: dict[str, tuple[int, ...]] = {}
    for filename in ("hidden.hex", "projection.hex", "base.hex", "scale.hex"):
        path = CHECKPOINT_ROOT / filename
        record = manifest["files"][filename]
        require(path.stat().st_size == record["bytes"], f"{filename}: byte size drift")
        require(sha256_file(path) == record["sha256"], f"{filename}: hash drift")
        values[filename] = read_hex(path)
        require(len(values[filename]) == record["words"], f"{filename}: word count drift")
    require(len(values["hidden.hex"]) == 16_384, "hidden extent drift")
    require(len(values["projection.hex"]) == 24 * 16_384, "projection extent drift")
    require(len(values["base.hex"]) == 24, "base extent drift")
    require(len(values["scale.hex"]) == 3, "scale extent drift")
    return manifest, values


def descriptor_configs() -> tuple[list[int], list[int], dict[str, object]]:
    manifest = json.loads(tile_vectors.DEPLOYMENT_MANIFEST.read_bytes())
    descriptors = tile_vectors.read_hex(tile_vectors.DESCRIPTOR_IMAGE)
    programs = tile_vectors.read_hex(tile_vectors.PROGRAM_IMAGE)
    bases = tile_vectors.deployment_bases(manifest)
    profiles = {
        target["profile"]: tile_vectors.selected_profile(
            target, manifest, descriptors, programs, bases
        )
        for target in tile_vectors.TARGETS
    }
    rom = tile_vectors.config_words(profiles[tile_vectors.PROFILE_ROM], 1)
    hbm = tile_vectors.config_words(profiles[tile_vectors.PROFILE_HBM], 1)
    require(len(rom) == len(hbm) == 128, "descriptor config length drift")
    identities: dict[str, object] = {}
    for name, words, profile in (
        ("rom_pc15", rom, profiles[tile_vectors.PROFILE_ROM]),
        ("hbm_pc14", hbm, profiles[tile_vectors.PROFILE_HBM]),
    ):
        identities[name] = {
            "profile": int(words[0]),
            "active_tokens": int(words[1]),
            "program_counter": int(words[2]),
            "operator_descriptor_id": int(words[4]),
            "wait_set_descriptor_id": int(words[5]),
            "config_u32le_sha256": sha256_bytes(
                b"".join(int(word).to_bytes(4, "little") for word in words)
            ),
            "deployment_sha256": profile["deployment"]["deployment_sha256"],
            "instruction_sha256": sha256_bytes(profile["instruction_bytes"]),
        }
    require(
        (rom[2], rom[4], hbm[2], hbm[4]) == (15, 381, 14, 545),
        "current ROM/HBM HC_PRE identity drift",
    )
    return rom, hbm, identities


def qualified_prefix() -> tuple[tuple[int, ...], dict[str, object]]:
    vector_bytes = QUALIFICATION_VECTOR.read_bytes()
    vector = json.loads(vector_bytes)
    weights = QUALIFIED_WEIGHTS.read_bytes()
    combination = QUALIFIED_COMBINATION.read_bytes()
    for name, payload in (("weights", weights), ("combination", combination)):
        record = vector["expected_outputs"][name]
        require(len(payload) == record["bytes"], f"qualified {name} size drift")
        require(sha256_bytes(payload) == record["sha256"], f"qualified {name} hash drift")
    first_weights = struct.unpack("<8I", weights[: 8 * 4])
    first_combination = struct.unpack("<16I", combination[: 16 * 4])
    return first_weights + first_combination, {
        "qualification_vector": {
            "path": str(QUALIFICATION_VECTOR.relative_to(ROOT)),
            "sha256": sha256_bytes(vector_bytes),
            "manifest_sha256": vector["manifest_sha256"],
        },
        "weights": {
            "path": str(QUALIFIED_WEIGHTS.relative_to(ROOT)),
            "sha256": sha256_bytes(weights),
        },
        "combination": {
            "path": str(QUALIFIED_COMBINATION.relative_to(ROOT)),
            "sha256": sha256_bytes(combination),
        },
        "prefix_u32le_sha256": sha256_bytes(
            b"".join(code.to_bytes(4, "little") for code in first_weights + first_combination)
        ),
    }


def full_expected(values: dict[str, tuple[int, ...]]) -> tuple[tuple[int, ...], dict[str, object]]:
    hidden_flat = values["hidden.hex"]
    hidden = (
        tuple(
            tuple(hidden_flat[stream * 4_096 : (stream + 1) * 4_096])
            for stream in range(4)
        ),
    )
    projection_flat = values["projection.hex"]
    projection = tuple(
        tuple(projection_flat[field * 16_384 : (field + 1) * 16_384])
        for field in range(24)
    )
    try:
        result = hc_pre_bf16(
            hidden,
            projection,
            values["scale.hex"],
            values["base.hex"],
        )
    except (HCPreReferenceError, NumericReferenceError) as exc:
        raise VectorError(f"independent HC_PRE reference failed: {exc}") from exc

    diagnostics = result.diagnostics
    expected = (
        diagnostics.mean_square_codes[0],
        diagnostics.inverse_rms_codes[0],
        *diagnostics.projection_codes[0],
        *diagnostics.normalized_projection_codes[0],
        *result.pre_binary32_codes[0],
        *result.post_binary32_codes[0],
        *(code for row in result.comb_binary32_codes[0] for code in row),
    )
    require(len(expected) == EXPECTED_WORDS, "full expected vector length drift")
    require(expected == EXPECTED_SENTINEL, "exact checkpoint witness drift")
    prefix, binding = qualified_prefix()
    require(expected[50:] == prefix, "T=1 arithmetic differs from qualified T=512 prefix")
    counters = result.counters
    return expected, {
        "mean_square": f"{expected[0]:08x}",
        "inverse_rms": f"{expected[1]:08x}",
        "projection_u32le_sha256": sha256_bytes(
            b"".join(code.to_bytes(4, "little") for code in expected[2:26])
        ),
        "normalized_projection_u32le_sha256": sha256_bytes(
            b"".join(code.to_bytes(4, "little") for code in expected[26:50])
        ),
        "coefficient_u32le_sha256": binding["prefix_u32le_sha256"],
        "counters": {
            "input_bf16_values": counters.hc_pre_input_bf16_values,
            "rms_square_multiplies": counters.hc_pre_rms_square_multiplies,
            "rms_reduction_adds": counters.hc_pre_rms_reduction_adds,
            "projection_product_accumulates": counters.hc_pre_projection_product_accumulates,
            "projection_rms_multiplies": counters.hc_pre_projection_rms_multiplies,
            "field_affine_multiplies": counters.hc_pre_field_affine_multiplies,
            "field_affine_adds": counters.hc_pre_field_affine_adds,
        },
        "qualified_t512_prefix": binding,
    }


def build(output: Path = OUTPUT_ROOT) -> dict[str, object]:
    checkpoint_manifest, checkpoint_values = verify_checkpoint_inputs()
    expected, witness = full_expected(checkpoint_values)
    cases, case_counts = fma_cases()
    rom, hbm, descriptor_identity = descriptor_configs()

    encoded_cases = [
        value
        for case in cases
        for value in (
            int(case["accumulator"]),
            int(case["activation"]),
            int(case["weight"]),
            int(case["result"]),
            int(case["error"]),
        )
    ]
    payloads = {
        "meta.hex": hex_payload(
            (
                0xA3F40001,
                1,
                len(cases),
                FMA_CASE_WORDS,
                EXPECTED_WORDS,
                16_384,
                24,
                8,
            )
        ),
        "fma_cases.hex": hex_payload(encoded_cases),
        "expected.hex": hex_payload(expected),
        "rom_config.hex": hex_payload(rom),
        "hbm_config.hex": hex_payload(hbm),
    }
    output.mkdir(parents=True, exist_ok=True)
    files: dict[str, object] = {}
    for filename, payload in payloads.items():
        (output / filename).write_bytes(payload)
        files[filename] = {
            "bytes": len(payload),
            "sha256": sha256_bytes(payload),
            "words": len(payload.splitlines()),
        }

    source_paths = (
        CHECKPOINT_MANIFEST,
        ROOT / "runtime/reference/formats.py",
        ROOT / "runtime/reference/hyper_connection.py",
        tile_vectors.DEPLOYMENT_MANIFEST,
        tile_vectors.DESCRIPTOR_IMAGE,
        tile_vectors.PROGRAM_IMAGE,
        ROOT / "tools/build_a3_mhc_pre_tile_vectors.py",
        QUALIFICATION_VECTOR,
        QUALIFIED_WEIGHTS,
        QUALIFIED_COMBINATION,
        Path(__file__).resolve(),
    )
    body: dict[str, object] = {
        "schema": "opentallas.rtl.a3_hc_pre_t1_vectors.v1",
        "status": "exact_checkpoint_and_descriptor_vectors",
        "abi": {"major": 3, "minor": 0},
        "fma": {
            "random_seed": FMA_RANDOM_SEED,
            "case_words": FMA_CASE_WORDS,
            "counts": case_counts,
            "oracle": "self-contained Fraction decode/exact product-add/integer binary32 RNE encode",
            "host_floating_point": False,
        },
        "checkpoint": {
            "manifest_id": checkpoint_manifest["manifest_id"],
            "manifest_sha256": sha256_file(CHECKPOINT_MANIFEST),
            "position": 0,
            "token_id": 18_042,
        },
        "witness": witness,
        "descriptors": descriptor_identity,
        "files": files,
        "source": {
            str(path.relative_to(ROOT)): {
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in source_paths
        },
        "claim_boundary": {
            "exact_bf16_fp32_fused_accumulation_vectors": True,
            "authenticated_checkpoint_t1_full_hc_pre_expected": True,
            "current_rom_pc15_and_hbm_pc14_configs": True,
            "rtl_execution": False,
            "transformer_layer": False,
            "model_token_generation": False,
            "eos": False,
            "architectural_timing": False,
            "tpot": False,
        },
    }
    body["vector_set_id"] = sha256_bytes(canonical(body))
    index_payload = json.dumps(body, indent=2, sort_keys=True).encode("ascii") + b"\n"
    (output / "index.json").write_bytes(index_payload)
    return body


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    result = build(args.output)
    print(
        "built A3 HC_PRE T=1 vectors: "
        f"fma_cases={result['fma']['counts']['total']} "
        f"token={result['checkpoint']['token_id']}"
    )


if __name__ == "__main__":
    main()
