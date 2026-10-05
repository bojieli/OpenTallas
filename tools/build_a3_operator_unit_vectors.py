#!/usr/bin/env python3
"""Block vectors for the two operator datapaths this device did not have.

``rtl/abi3/ot_a3_vector_silu_mul.sv`` and
``rtl/abi3/ot_a3_selection_token_append.sv`` are new modules, so each gets a
block campaign of its own before it is trusted inside the issue bridge.

The SiLU-multiply vectors are directed corners first and a seeded spread
second.  The corners are the places the frozen contract's three roundings can
disagree with a shortcut: signed zero, the smallest and largest finite BF16
codes, the exponential's own clamp boundary, magnitudes that saturate the
gated product, and the sign selection that makes ``+0.0`` negate to ``+0.0``.
Expected values come from
``runtime.reference.tensor_accelerator_elementwise.qwen3_silu_mul_bf16``.

The TOKEN_APPEND vectors are a policy matrix.  Every refusal the golden model
distinguishes is a separate case, because "both stopped" is not the same claim
as "stopped for the same reason", and the EOS-versus-length precedence is
checked in the one place it matters: a token that is both.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.reference.tensor_accelerator_elementwise import (  # noqa: E402
    qwen3_silu_mul_bf16,
)
from tools import build_a3_qwen_kv_scatter_vectors as scatter  # noqa: E402


OUTPUT_ROOT = ROOT / "testdata/rtl/a3_operator_units"
SCHEMA = "opentallas.rtl.a3_operator_unit_vectors.v1"

ERR_NONE = 0
ERR_OPERAND_NONFINITE = 1
ERR_INDEX_RANGE = 4
ERR_SHAPE = 7

SILU_CASE_WORDS = 16
APPEND_CASE_WORDS = 32
MAX_EOS_TOKENS = 8
VOCABULARY = 151936

VECTOR_FILES = (
    "silu_cases.hex",
    "silu_gate.hex",
    "silu_up.hex",
    "silu_expected.hex",
    "append_cases.hex",
    "index.json",
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Spread:
    """The same seeded deterministic BF16 spread the admission vectors use."""

    def __init__(self, seed: int) -> None:
        self.state = seed & ((1 << 64) - 1)

    def next(self) -> int:
        self.state = (self.state * 6364136223846793005 + 1442695040888963407) & (
            (1 << 64) - 1
        )
        return self.state >> 33

    def code(self, *, low_exponent: int, high_exponent: int) -> int:
        raw = self.next()
        sign = raw & 1
        exponent = low_exponent + ((raw >> 1) % (high_exponent - low_exponent + 1))
        return (sign << 15) | (exponent << 7) | ((raw >> 9) & 0x7F)


def bf16(value: float) -> int:
    """The BF16 code of a value that is exactly representable in BF16."""

    bits = struct.unpack("<I", struct.pack("<f", value))[0]
    if bits & 0xFFFF:
        raise ValueError(f"{value} is not exactly BF16")
    return bits >> 16


DIRECTED_GATES = [
    0x0000,  # +0.0 -- negates to +0.0, not to -0.0
    0x8000,  # -0.0 -- the sign bit is set, so the argument path differs
    bf16(1.0),
    bf16(-1.0),
    bf16(0.5),
    bf16(-0.5),
    bf16(2.0),
    bf16(-2.0),
    bf16(8.0),
    bf16(-8.0),
    bf16(16.0),
    bf16(-16.0),
    bf16(64.0),
    bf16(-64.0),
    bf16(88.0),
    bf16(-88.0),
    0x0001,  # smallest positive BF16 subnormal
    0x8001,
    0x007F,  # largest BF16 subnormal
    0x0080,  # smallest positive BF16 normal
    0x7F7F,  # largest finite BF16
    0xFF7F,  # most negative finite BF16
    bf16(3.0),
    bf16(-3.0),
    bf16(104.0),   # the reference's exponential clamp boundary, exactly
    bf16(-104.0),
]
# Pairs appended after the cross product because they are chosen for one
# property each rather than for coverage of the grid.
EXTRA_PAIRS = [
    # A gated product above the largest finite BF16 and still inside binary32:
    # the output conversion saturates and the saturation counter must see it.
    (0x7F7E, 0x3F81),
    (0xFF7E, 0x3F81),
]
DIRECTED_UPS = [
    bf16(1.0),
    bf16(-1.0),
    0x0000,
    0x8000,
    0x7F7F,
    0xFF7F,
    bf16(2.0),
    bf16(-0.5),
]
ERR_PRODUCT_RANGE = 2


def directed_pairs() -> tuple[list[int], list[int], list[tuple[int, int]]]:
    """The directed cross product, minus the pairs that leave binary32.

    ``qwen3_silu_mul_bf16`` raises on a gated product outside binary32 rather
    than saturating it, and so does the datapath -- with ERR_PRODUCT_RANGE.
    A pair that overflows therefore belongs in a refusal case, not in a run
    whose whole point is that every element produced a value.  The excluded
    pairs are listed in the manifest so the exclusion is a statement rather
    than a silent filter.
    """

    gates: list[int] = []
    ups: list[int] = []
    excluded: list[tuple[int, int]] = []
    for gate in DIRECTED_GATES:
        for up in DIRECTED_UPS:
            try:
                qwen3_silu_mul_bf16([[gate]], [[up]])
            except Exception:
                excluded.append((gate, up))
                continue
            gates.append(gate)
            ups.append(up)
    for gate, up in EXTRA_PAIRS:
        gates.append(gate)
        ups.append(up)
    return gates, ups, excluded


def silu_cases(gates: list[int], ups: list[int]) -> tuple[
    list[dict[str, Any]], list[int], list[int], list[int]
]:
    """One positive run, then the three ways the datapath refuses."""

    result = qwen3_silu_mul_bf16([gates], [ups])
    expected = list(result.values[0])

    def case(
        name: str,
        *,
        count: int,
        error: int,
        out_count: int,
        work_count: int,
        compare: bool,
        gate_code: int | None = None,
        up_code: int | None = None,
        index: int = 0,
        saturations: int = 0,
        activation_saturations: int = 0,
        note: str,
    ) -> dict[str, Any]:
        return {
            "name": name,
            "count": count,
            "expected_error": error,
            "expected_out_count": out_count,
            "expected_work_count": work_count,
            "expected_saturations": saturations,
            "expected_activation_saturations": activation_saturations,
            "compare_output": compare,
            "poison_gate_enable": int(gate_code is not None),
            "poison_gate_code": 0 if gate_code is None else gate_code,
            "poison_up_enable": int(up_code is not None),
            "poison_up_code": 0 if up_code is None else up_code,
            "poison_index": index,
            "note": note,
        }

    cases = [
        case(
            "silu_mul_directed_and_seeded",
            count=len(gates),
            error=ERR_NONE,
            out_count=len(gates),
            work_count=2 * len(gates),
            compare=True,
            saturations=result.output_saturated_element_count,
            activation_saturations=result.activation_saturated_element_count,
            note="every directed corner and the seeded spread, bit for bit",
        ),
        case(
            "silu_mul_nonfinite_gate",
            count=len(gates),
            error=ERR_OPERAND_NONFINITE,
            out_count=3,
            work_count=6,
            compare=False,
            gate_code=0x7F80,
            index=3,
            note="an infinite gate stops the block before the fourth element",
        ),
        case(
            "silu_mul_nonfinite_up",
            count=len(gates),
            error=ERR_OPERAND_NONFINITE,
            out_count=5,
            work_count=10,
            compare=False,
            up_code=0xFFC0,
            index=5,
            note="a NaN up value is a fault, not a value to skip",
        ),
        case(
            "silu_mul_gated_product_range",
            count=len(gates),
            error=ERR_PRODUCT_RANGE,
            out_count=2,
            work_count=5,
            compare=False,
            gate_code=0x7F7F,
            up_code=0x4000,
            index=2,
            note=(
                "the SiLU activation is in range and the gated product is not: "
                "the work count shows the failure is the second multiply"
            ),
        ),
        case(
            "silu_mul_degenerate_count",
            count=0,
            error=ERR_SHAPE,
            out_count=0,
            work_count=0,
            compare=False,
            note="a zero-element operation is a shape fault",
        ),
    ]
    return cases, gates, ups, expected


def encode_silu_cases(cases: list[dict[str, Any]]) -> list[int]:
    words: list[int] = []
    for item in cases:
        values = [0] * SILU_CASE_WORDS
        values[0] = item["count"]
        values[1] = item["expected_error"]
        values[2] = item["expected_out_count"]
        values[3] = item["expected_work_count"]
        values[4] = item["expected_saturations"]
        values[5] = item["expected_activation_saturations"]
        values[6] = int(item["compare_output"])
        values[7] = item["poison_gate_enable"]
        values[8] = item["poison_gate_code"]
        values[9] = item["poison_up_enable"]
        values[10] = item["poison_up_code"]
        values[11] = item["poison_index"]
        words.extend(value & 0xFFFFFFFF for value in values)
    return words


NO_ID = 0xFFFFFFFF
EOS_A = 151645
EOS_B = 151643


def append_case(
    name: str,
    *,
    token: int,
    ring_bound: bool = True,
    selection_mode: int = 0,
    eos_count: int = 2,
    policy_max: int = 8256,
    vocabulary: int = VOCABULARY,
    request_max: int = 8,
    generated_before: int = 0,
    expected_error: int,
    expected_capability: bool,
    expected_token: int,
    expected_eos: int,
    expected_out_count: int,
    expected_appended: int,
    expected_reads: int,
    note: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "token": token,
        "ring_bound": ring_bound,
        "selection_mode": selection_mode,
        "eos_count": eos_count,
        "policy_max": policy_max,
        "vocabulary": vocabulary,
        "request_max": request_max,
        "generated_before": generated_before,
        "expected_error": expected_error,
        "expected_capability": expected_capability,
        "expected_token": expected_token,
        "expected_eos": expected_eos,
        "expected_out_count": expected_out_count,
        "expected_appended": expected_appended,
        "expected_reads": expected_reads,
        "note": note,
    }


def append_cases() -> list[dict[str, Any]]:
    return [
        append_case(
            "token_append_continues",
            token=12345,
            expected_error=ERR_NONE,
            expected_capability=False,
            expected_token=12345,
            expected_eos=0,
            expected_out_count=1,
            expected_appended=1,
            expected_reads=1,
            note="not EOS, below the request bound",
        ),
        append_case(
            "token_append_official_eos_first_slot",
            token=EOS_A,
            expected_error=ERR_NONE,
            expected_capability=False,
            expected_token=EOS_A,
            expected_eos=1,
            expected_out_count=1,
            expected_appended=1,
            expected_reads=1,
            note="the first EOS token of the shipped policy",
        ),
        append_case(
            "token_append_official_eos_second_slot",
            token=EOS_B,
            expected_error=ERR_NONE,
            expected_capability=False,
            expected_token=EOS_B,
            expected_eos=1,
            expected_out_count=1,
            expected_appended=1,
            expected_reads=1,
            note="the second EOS token: slot scanning, not just slot zero",
        ),
        append_case(
            "token_append_eos_slot_beyond_declared_count",
            token=EOS_B,
            eos_count=1,
            expected_error=ERR_NONE,
            expected_capability=False,
            expected_token=EOS_B,
            expected_eos=0,
            expected_out_count=1,
            expected_appended=1,
            expected_reads=1,
            note=(
                "the same id, one slot outside the declared count: a slot the "
                "policy does not declare is not an EOS token"
            ),
        ),
        append_case(
            "token_append_length_stop",
            token=12345,
            request_max=3,
            generated_before=2,
            expected_error=ERR_NONE,
            expected_capability=False,
            expected_token=12345,
            expected_eos=2,
            expected_out_count=1,
            expected_appended=1,
            expected_reads=1,
            note="this append reaches the request's ceiling",
        ),
        append_case(
            "token_append_eos_beats_length_stop",
            token=EOS_A,
            request_max=3,
            generated_before=2,
            expected_error=ERR_NONE,
            expected_capability=False,
            expected_token=EOS_A,
            expected_eos=1,
            expected_out_count=1,
            expected_appended=1,
            expected_reads=1,
            note=(
                "a final token that is also EOS reports the official reason, "
                "which is the branch the golden model returns early on"
            ),
        ),
        append_case(
            "token_append_without_token_ring",
            token=777,
            ring_bound=False,
            expected_error=ERR_NONE,
            expected_capability=False,
            expected_token=777,
            expected_eos=0,
            expected_out_count=0,
            expected_appended=1,
            expected_reads=1,
            note="the optional ring is unbound: appended, nothing written",
        ),
        append_case(
            "token_append_outside_vocabulary",
            token=VOCABULARY,
            expected_error=ERR_INDEX_RANGE,
            expected_capability=False,
            expected_token=0,
            expected_eos=0,
            expected_out_count=0,
            expected_appended=0,
            expected_reads=1,
            note="one past the last legal id is a fault, not a clamp",
        ),
        append_case(
            "token_append_sampling_policy",
            token=12345,
            selection_mode=1,
            expected_error=ERR_SHAPE,
            expected_capability=True,
            expected_token=0,
            expected_eos=0,
            expected_out_count=0,
            expected_appended=0,
            expected_reads=0,
            note="a sampling policy is a capability refusal",
        ),
        append_case(
            "token_append_request_bound_zero",
            token=12345,
            request_max=0,
            expected_error=ERR_SHAPE,
            expected_capability=True,
            expected_token=0,
            expected_eos=0,
            expected_out_count=0,
            expected_appended=0,
            expected_reads=0,
            note="a request that may generate nothing is refused",
        ),
        append_case(
            "token_append_request_above_policy",
            token=12345,
            policy_max=4,
            request_max=5,
            expected_error=ERR_SHAPE,
            expected_capability=True,
            expected_token=0,
            expected_eos=0,
            expected_out_count=0,
            expected_appended=0,
            expected_reads=0,
            note="the immutable policy is the deployment ceiling",
        ),
        append_case(
            "token_append_eos_count_above_abi_bound",
            token=12345,
            eos_count=MAX_EOS_TOKENS + 1,
            expected_error=ERR_SHAPE,
            expected_capability=False,
            expected_token=0,
            expected_eos=0,
            expected_out_count=0,
            expected_appended=0,
            expected_reads=0,
            note="the frozen ABI bounds the EOS set at eight",
        ),
        append_case(
            "token_append_empty_vocabulary",
            token=0,
            vocabulary=0,
            expected_error=ERR_SHAPE,
            expected_capability=False,
            expected_token=0,
            expected_eos=0,
            expected_out_count=0,
            expected_appended=0,
            expected_reads=0,
            note="a policy with no vocabulary cannot admit any token",
        ),
    ]


def encode_append_cases(cases: list[dict[str, Any]]) -> list[int]:
    words: list[int] = []
    for item in cases:
        values = [0] * APPEND_CASE_WORDS
        values[0] = item["token"]
        values[1] = int(item["ring_bound"])
        values[2] = item["selection_mode"]
        values[3] = item["eos_count"]
        values[4] = item["policy_max"]
        values[5] = item["vocabulary"]
        values[6] = item["request_max"]
        values[7] = item["generated_before"]
        values[8] = item["expected_error"]
        values[9] = int(item["expected_capability"])
        values[10] = item["expected_token"]
        values[11] = item["expected_eos"]
        values[12] = item["expected_out_count"]
        values[13] = item["expected_appended"]
        values[14] = item["expected_reads"]
        for slot in range(MAX_EOS_TOKENS):
            values[16 + slot] = NO_ID
        values[16] = EOS_A
        values[17] = EOS_B
        words.extend(value & 0xFFFFFFFF for value in values)
    return words


def build(output: Path = OUTPUT_ROOT) -> dict[str, Any]:
    gates, ups, excluded = directed_pairs()
    spread = Spread(0x4F50_4552_4154_4F52)
    for _ in range(1024):
        gates.append(spread.code(low_exponent=112, high_exponent=133))
        ups.append(spread.code(low_exponent=112, high_exponent=133))
    cases, gates, ups, expected = silu_cases(gates, ups)
    appends = append_cases()

    output.mkdir(parents=True, exist_ok=True)
    images = {
        "silu_cases.hex": scatter.hex_lines(encode_silu_cases(cases)),
        "silu_gate.hex": scatter.hex_lines(gates),
        "silu_up.hex": scatter.hex_lines(ups),
        "silu_expected.hex": scatter.hex_lines(expected),
        "append_cases.hex": scatter.hex_lines(encode_append_cases(appends)),
    }
    for name, payload in images.items():
        (output / name).write_text(payload, encoding="ascii")

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "abi": {"major": 3, "minor": 0},
        "geometry": {
            "silu_case_words": SILU_CASE_WORDS,
            "silu_case_count": len(cases),
            "silu_element_count": len(gates),
            "silu_directed_count": len(DIRECTED_GATES) * len(DIRECTED_UPS)
            - len(excluded),
            "silu_directed_excluded": len(excluded),
            "append_case_words": APPEND_CASE_WORDS,
            "append_case_count": len(appends),
        },
        "oracles": {
            "silu_mul": (
                "runtime/reference/tensor_accelerator_elementwise.py"
                "::qwen3_silu_mul_bf16"
            ),
            "token_append": "runtime/sim/engines/selection.py::token_append",
            "independent_of_dut": True,
            "silu_expected_bf16_sha256": sha256_bytes(
                struct.pack(f"<{len(expected)}H", *expected)
            ),
        },
        "silu_cases": cases,
        "silu_directed_excluded_pairs": [
            {"gate": gate, "up": up} for gate, up in excluded
        ],
        "append_cases": appends,
        "expected_pass": {
            "silu_cases": len(cases),
            "silu_words": len(expected),
            "append_cases": len(appends),
        },
        "claim_boundary": {
            "block_level_only": True,
            "bit_exact_against_independent_reference": True,
            "shared_certifying_exponential": True,
            "shared_correctly_rounded_divider": True,
            "model_token_generation": False,
            "tpot": False,
        },
    }
    manifest["image_sha256"] = {
        name: sha256_file(output / name)
        for name in VECTOR_FILES
        if name != "index.json"
    }
    (output / "index.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output", type=Path, default=OUTPUT_ROOT)
    return result


def main() -> int:
    args = parser().parse_args()
    manifest = build(args.output)
    print(
        "built ABI3 operator-unit vectors "
        f"silu_elements={manifest['geometry']['silu_element_count']} "
        f"append_cases={manifest['geometry']['append_case_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
