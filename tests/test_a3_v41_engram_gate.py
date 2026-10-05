"""``ot_a3_vector_engram_gate`` is bit-exact, and its geometry is not frozen.

VECTOR.ENGRAM_GATE is the V4.1-Flash Engram gate: a normalised dot, a SIGNED
square root, a sigmoid and a residual add, under the numeric contract
``engram_gate_fp32_v1`` (plan section 5 row 6, WP-K).

The expensive mistake this repository has already made once is a datapath whose
geometry lived in localparams: the engine bridge refused shapes it could compute,
and the frozen constant had propagated into a Python mirror, a campaign leg plan
and a testbench array size.  So the tests below do two different things.

The reference tests pin the contract's own properties -- the correctly rounded
square root, the 1e-6 clamp on an all-zero row, the sign the signed square root
carries, and the order independence that makes the exact reduction a claim rather
than a hope.

The RTL test ELABORATES THE BLOCK AT A GEOMETRY THE CAMPAIGN DOES NOT USE, 48
elements wide with 2 lanes, and compares every output word against the same
reference.  The four campaign geometries could all be passing because the
campaign's own numbers were generated for them; a fifth geometry invented by the
test cannot be.
"""

from __future__ import annotations

import math
import random
import re
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

from runtime.reference.engram import (
    ENGRAM_GATE_DEFAULT_ACC_EXP_MAX,
    ENGRAM_GATE_DEFAULT_ACC_EXP_MIN,
    ENGRAM_GATE_EPSILON_BINARY32,
    binary32_sqrt_rne,
    engram_gate,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
UNIT_SOURCE = REPO_ROOT / "rtl/abi3/ot_a3_vector_engram_gate.sv"
TREE_SOURCE = REPO_ROOT / "rtl/abi3/ot_a3_engram_exact_dot_tree.sv"
SQRT_SOURCE = REPO_ROOT / "rtl/abi3/ot_a3_engram_fp32_sqrt_rne_pipe.sv"
TESTBENCH_SOURCE = REPO_ROOT / "rtl/test/tb_a3_v41_engram_gate.sv"
CAMPAIGN_RECORD = REPO_ROOT / "results/rtl/a3_v41_engram_gate_campaign.json"

SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/abi3/ot_a3_engram_fp32_sqrt_rne_pipe.sv",
    "rtl/abi3/ot_a3_engram_exact_dot_tree.sv",
    "rtl/abi3/ot_a3_vector_engram_gate.sv",
    "rtl/test/tb_a3_v41_engram_gate.sv",
)

MAGIC = 0xA341_E9A7
SENTINEL = 0xDEADBEEF
CASE_WORDS = 8
EXPECT_SCALARS = 16


def code(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def value_of(encoded: int) -> float:
    return struct.unpack("<f", struct.pack("<I", encoded))[0]


# ---------------------------------------------------------------------------
# the reference's own properties
# ---------------------------------------------------------------------------


def test_reference_square_root_is_correctly_rounded() -> None:
    """The reference square root agrees with a correctly rounded host root.

    The host computes in binary64 and rounds once to binary32.  A binary32
    square root is either exactly representable or irrational, so it can never
    sit on a binary32 midpoint, and the double rounding cannot disagree with the
    correctly rounded single rounding on this input class.
    """

    generator = random.Random(0x5127)
    directed = (
        0x00000000,
        0x00000001,
        0x007FFFFF,
        0x00800000,
        0x3F800000,
        0x40000000,
        0x7F7FFFFF,
    )
    samples = list(directed) + [
        generator.randrange(1, 0x7F800000) for _ in range(4000)
    ]
    for encoded in samples:
        assert binary32_sqrt_rne(encoded) == code(math.sqrt(value_of(encoded)))


def test_square_root_refuses_a_negative_or_nonfinite_argument() -> None:
    from runtime.reference.formats import NumericReferenceError

    for encoded in (0xBF800000, 0x7F800000, 0x7FC00000):
        with pytest.raises(NumericReferenceError):
            binary32_sqrt_rne(encoded)


def test_the_clamp_fires_on_an_all_zero_row() -> None:
    """A zero row has zero norms, so only the 1e-6 clamp keeps the divide legal.

    The gate is then sigmoid(+0) = 0.5 exactly and the residual passes through
    unchanged.  Without the clamp this row is a division by zero.
    """

    zero = [0] * 4
    result = engram_gate(zero, zero, zero, zero, zero)
    assert result.refusal_stage == 0
    assert result.denominator_raw_code == 0
    assert result.denominator_code == ENGRAM_GATE_EPSILON_BINARY32
    assert result.clamped is True
    assert result.cosine_code == 0
    assert result.gate_code == code(0.5)
    assert result.output_codes == (0, 0, 0, 0)


def test_the_signed_square_root_keeps_the_sign_of_the_normalised_dot() -> None:
    """An antiparallel pair gives a NEGATIVE gate argument.

    sqrt of a negative value does not exist, so a block that took the square
    root before restoring the sign would fail closed here, and one that dropped
    the sign would gate with sigmoid(+1) instead of sigmoid(-1).
    """

    width = 8
    query = [code(0.5)] * width
    gate_key = [code(-0.5)] * width
    zero = [0] * width
    result = engram_gate(zero, zero, zero, query, gate_key)
    assert result.refusal_stage == 0
    assert value_of(result.cosine_code) == pytest.approx(-1.0, abs=1e-6)
    assert result.signed_sqrt_code & 0x80000000 != 0
    assert value_of(result.gate_code) < 0.5

    parallel = engram_gate(zero, zero, zero, query, query)
    assert parallel.signed_sqrt_code & 0x80000000 == 0
    assert value_of(parallel.gate_code) > 0.5


def test_the_reduction_is_order_independent() -> None:
    """Permuting the row cannot change a code, because the reduction is exact.

    This is the property that lets the RTL reduce LANES elements per cycle
    through a registered tree and an accumulator without the lane count
    appearing in the contract.  A reduction that rounded per addition would fail
    this test on most permutations.
    """

    generator = random.Random(0x0D0D)
    width = 64
    query = [code(generator.uniform(-1.0, 1.0)) for _ in range(width)]
    gate_key = [code(generator.uniform(-1.0, 1.0)) for _ in range(width)]
    hidden = [code(generator.uniform(-1.0, 1.0)) for _ in range(width)]
    straight = engram_gate(hidden, hidden, hidden, query, gate_key)
    order = list(range(width))
    for _ in range(8):
        generator.shuffle(order)
        permuted = engram_gate(
            [hidden[index] for index in order],
            [hidden[index] for index in order],
            [hidden[index] for index in order],
            [query[index] for index in order],
            [gate_key[index] for index in order],
        )
        assert permuted.dot_code == straight.dot_code
        assert permuted.norm_q_square_code == straight.norm_q_square_code
        assert permuted.norm_k_square_code == straight.norm_k_square_code
        assert permuted.gate_code == straight.gate_code


def test_a_product_outside_the_exactness_window_is_refused_not_rounded() -> None:
    """The window is a parameter pair and its boundary is exact on both sides."""

    inside = [code(2.0**-40)] * 4
    outside = [code(2.0**-41)] * 4
    zero = [0] * 4
    assert engram_gate(zero, zero, zero, inside, inside).refusal_stage == 0
    assert engram_gate(zero, zero, zero, outside, outside).refusal_stage == 3

    ceiling = [code(2.0**31)] * 4
    above = [code(2.0**32)] * 4
    assert engram_gate(zero, zero, zero, ceiling, ceiling).refusal_stage == 0
    assert engram_gate(zero, zero, zero, above, above).refusal_stage == 3


def test_the_row_length_is_a_request_field_not_a_reference_constant() -> None:
    """Any length up to the built width runs; one element more is refused."""

    for width in (1, 3, 17, 256):
        row = [code(0.25)] * width
        assert engram_gate(row, row, row, row, row).refusal_stage == 0
    row = [code(0.25)] * 257
    assert engram_gate(row, row, row, row, row).refusal_stage == 1
    assert engram_gate(row, row, row, row, row, max_width=272).refusal_stage == 0


# ---------------------------------------------------------------------------
# the RTL's geometry
# ---------------------------------------------------------------------------


def test_the_unit_holds_its_geometry_in_parameters() -> None:
    """Every dimension is a parameter, and no dimension is a localparam."""

    text = UNIT_SOURCE.read_text()
    header = text[text.index("module ot_a3_vector_engram_gate") : text.index(") (")]
    for name in (
        "VECTOR_WIDTH",
        "LANES",
        "ACC_EXP_MIN",
        "ACC_EXP_MAX",
        "GATE_EPSILON_CODE",
        "SQRT_FRAC_SHIFT",
    ):
        assert re.search(rf"parameter\s+(?:integer\s+|\[31:0\]\s+)?{name}\s*=", header), name
    #: Outside its comments, the V4.1 row width appears exactly once in the
    #: header: as the default of VECTOR_WIDTH.
    code_only = "\n".join(
        line.split("//")[0] for line in header.splitlines()
    )
    assert code_only.count("256") == 1
    assert len(re.findall(r"localparam[^;]*\b(?:24|256|264|12672)\b", text)) == 0
    #: The only width predicate compares the request against the parameter.
    assert "cfg_count > VECTOR_WIDTH" in text
    assert re.search(r"cfg_count\s*[!=]=\s*(?:32'd)?256", text) is None


def test_the_pipeline_declares_its_stage_count_and_initiation_interval() -> None:
    """The header states both numbers, because a reviewer has to be able to
    check the claim without reading the datapath."""

    for source in (UNIT_SOURCE, TREE_SOURCE, SQRT_SOURCE):
        text = source.read_text()
        head = text[: text.index("module ")]
        assert "INITIATION INTERVAL" in head.upper()
        assert "stage" in head.lower()


def test_no_reduction_node_is_a_binary32_adder() -> None:
    """The registered tree adds on an exact integer grid.

    A tree whose nodes were ``fp32_add_rne`` would be a correct tree and a slow
    one: that function resolves align, add, normalise and round through a
    524-bit intermediate in one combinational block.
    """

    tree = TREE_SOURCE.read_text()
    code_only = "\n".join(line.split("//")[0] for line in tree.splitlines())
    assert "fp32_add_rne" not in code_only
    assert "fp32_mul_rne" not in code_only
    assert "node[index] <= node[2*index] + node[2*index+1];" in code_only


def _emit_vectors(
    destination: Path,
    cases: list[dict[str, list[int]]],
    *,
    vector_limit: int,
    max_width: int,
    lanes: int,
    acc_exp_max: int,
) -> None:
    """Write one vector set in the testbench's own format."""

    region_count = 6
    memory_words = (region_count + 1) * vector_limit
    requests: list[int] = []
    inputs: list[int] = []
    expected: list[int] = []
    for index, case in enumerate(cases):
        bases = {
            name: slot * vector_limit
            for slot, name in enumerate(("h", "key", "value", "q", "k", "out"))
        }
        width = len(case["h"])
        requests += [
            width,
            bases["h"],
            bases["key"],
            bases["value"],
            bases["q"],
            bases["k"],
            bases["out"],
            0,
        ]
        for operand in ("h", "key", "value", "q", "k"):
            row = list(case[operand])
            inputs += row + [0] * (vector_limit - len(row))
        result = engram_gate(
            case["h"],
            case["key"],
            case["value"],
            case["q"],
            case["k"],
            max_width=max_width,
            combine_group=lanes,
            acc_exp_max=acc_exp_max,
        )
        expected += [
            result.error_code,
            result.refusal_stage,
            result.written_words,
            result.reduced_words,
            result.dot_code,
            result.norm_q_square_code,
            result.norm_k_square_code,
            result.norm_q_code,
            result.norm_k_code,
            result.denominator_raw_code,
            result.denominator_code,
            result.cosine_code,
            result.signed_sqrt_code,
            result.gate_code,
            int(result.clamped),
            int(result.refusal_stage == 0),
        ]
        row = list(result.output_codes)
        expected += row + [SENTINEL] * (vector_limit - len(row))

    def write(name: str, words: list[int]) -> None:
        (destination / name).write_text("".join(f"{word:08x}\n" for word in words))

    write(
        "meta.hex",
        [
            MAGIC,
            1,
            len(cases),
            vector_limit,
            CASE_WORDS,
            EXPECT_SCALARS,
            memory_words,
            SENTINEL,
        ],
    )
    write("cases.hex", requests)
    write("input.hex", inputs)
    write("expect.hex", expected)


@pytest.mark.skipif(
    shutil.which("iverilog") is None or shutil.which("vvp") is None,
    reason="Icarus Verilog is not installed",
)
def test_the_rtl_is_bit_exact_at_a_geometry_the_campaign_never_builds(
    tmp_path: Path,
) -> None:
    """Elaborate the block 48 wide with 2 lanes and compare every output word.

    The campaign builds 256/4, 256/8, 272/4 and 272/4 with a wider window.  This
    geometry is none of those: the width is not the V4.1 row width, the lane
    count is not the default, 48 is not a multiple of the widths any of the four
    legs used, and two of the cases are not multiples of the lane count either.
    """

    generator = random.Random(0xE9A7_0048)
    max_width = 48
    lanes = 2
    cases: list[dict[str, list[int]]] = []
    for width in (1, 5, 16, 47, 48):
        cases.append(
            {
                operand: [
                    code(generator.uniform(-1.0, 1.0)) for _ in range(width)
                ]
                for operand in ("h", "key", "value", "q", "k")
            }
        )
    #: The clamp, and a refusal, at this geometry too.
    cases.append({operand: [0] * 4 for operand in ("h", "key", "value", "q", "k")})
    poisoned = {
        operand: [code(generator.uniform(-1.0, 1.0)) for _ in range(16)]
        for operand in ("h", "key", "value", "q", "k")
    }
    poisoned["h"][5] = 0x7FC00000
    cases.append(poisoned)
    #: A row one element longer than this instance is built for.
    cases.append(
        {
            operand: [code(0.5)] * (max_width + 1)
            for operand in ("h", "key", "value", "q", "k")
        }
    )

    vector_limit = max_width + 1
    _emit_vectors(
        tmp_path,
        cases,
        vector_limit=vector_limit,
        max_width=max_width,
        lanes=lanes,
        acc_exp_max=ENGRAM_GATE_DEFAULT_ACC_EXP_MAX,
    )

    binary = tmp_path / "tb.vvp"
    compile_result = subprocess.run(
        [
            "iverilog",
            "-g2012",
            f"-Ptb_a3_v41_engram_gate.GATE_VECTOR_WIDTH={max_width}",
            f"-Ptb_a3_v41_engram_gate.GATE_LANES={lanes}",
            f"-Ptb_a3_v41_engram_gate.GATE_ACC_EXP_MIN={ENGRAM_GATE_DEFAULT_ACC_EXP_MIN}",
            f"-Ptb_a3_v41_engram_gate.GATE_ACC_EXP_MAX={ENGRAM_GATE_DEFAULT_ACC_EXP_MAX}",
            "-s",
            "tb_a3_v41_engram_gate",
            "-o",
            str(binary),
            *[str(REPO_ROOT / source) for source in SOURCES],
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert compile_result.returncode == 0, compile_result.stderr

    simulate = subprocess.run(
        [
            "vvp",
            str(binary),
            f"+META={tmp_path / 'meta.hex'}",
            f"+REQUESTS={tmp_path / 'cases.hex'}",
            f"+INPUTS={tmp_path / 'input.hex'}",
            f"+EXPECTED={tmp_path / 'expect.hex'}",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    log = simulate.stdout + simulate.stderr
    assert simulate.returncode == 0, log
    assert "PASS a3_v41_engram_gate" in log
    retiring = sum(
        1
        for case in cases
        if engram_gate(
            case["h"],
            case["key"],
            case["value"],
            case["q"],
            case["k"],
            max_width=max_width,
            combine_group=lanes,
        ).refusal_stage
        == 0
    )
    expected_checks = 4 + len(cases) * (16 + vector_limit) + 5 * retiring
    assert f"checks={expected_checks}" in log
    #: The refused wide row must have been refused for its shape, and the zero
    #: row must have reported the clamp, at this geometry as at the others.
    assert "clamped=1" in log
    assert f"cases={len(cases)}" in log


@pytest.mark.skipif(
    not CAMPAIGN_RECORD.is_file(), reason="the campaign record has not been produced"
)
def test_the_retained_campaign_record_is_source_current() -> None:
    """The record's digests still describe the tree it claims to describe."""

    import importlib.util

    specification = importlib.util.spec_from_file_location(
        "run_a3_v41_engram_gate_rtl_campaign",
        REPO_ROOT / "tools/run_a3_v41_engram_gate_rtl_campaign.py",
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    assert module.validate_retained(CAMPAIGN_RECORD) == []


@pytest.mark.skipif(
    not CAMPAIGN_RECORD.is_file(), reason="the campaign record has not been produced"
)
def test_the_campaign_record_states_what_it_does_not_establish() -> None:
    """A pass that does not say what it leaves open is not evidence."""

    import json

    record = json.loads(CAMPAIGN_RECORD.read_text())
    boundary = record["claim_boundary"]
    assert boundary["bit_exact_against_an_independent_python_reference"] is True
    assert boundary["dual_simulator"] is True
    assert record["simulators_agree"] is True
    for absent in (
        "establishes_vendor_engram_forward_equivalence",
        "establishes_target_frequency_or_timing_closure",
        "is_placed_or_routed",
        "establishes_a_token_a_layer_or_a_tpot",
        "executes_the_engram_row_gather_or_the_ngram_hash",
    ):
        assert boundary[absent] is False
    assert record["reference"]["function"] == "engram_gate"
    assert len(record["legs"]) == 4
