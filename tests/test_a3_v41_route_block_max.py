"""Evidence checks for ROUTE.BLOCK_MAX: the reference, the RTL text, the record.

Three things are checked here, none of which is the RTL simulation itself (that
is ``tools/run_a3_v41_block_max_rtl_campaign.py`` and its artifact):

1. the independent reference ``runtime.reference.candidate_pool.block_max_rows``
   against a THIRD path -- the host's own binary32 comparison via ``struct`` --
   and against the operator's stated rules (the negative-infinity padding of a
   partial final block, the signed-zero order, the refusals);
2. the acceptance criterion that no model geometry is frozen into
   ``rtl/abi3/ot_a3_route_block_max.sv``: every extent in the block's body comes
   from a parameter or an operand field;
3. the campaign record, including that its ``source_sha256`` still matches the
   files on disk -- a record whose sources have moved underneath it is stale
   evidence, not evidence.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import re
import struct

import pytest

from runtime.reference.candidate_pool import (
    BLOCK_MAX_NUMERIC_CONTRACT,
    BLOCK_MAX_V41_BLOCK,
    BLOCK_MAX_V41_ROW_BLOCKS,
    BlockMaxReferenceError,
    block_max_padding_code,
    block_max_rows,
)

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl/abi3/ot_a3_route_block_max.sv"
CAMPAIGN_JSON = ROOT / "results/rtl/a3_v41_block_max_campaign.json"

NEG_INF = 0xFF800000
POS_INF = 0x7F800000
NEG_ZERO = 0x80000000


def _code(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def _value(code: int) -> float:
    return struct.unpack("<f", struct.pack("<I", code))[0]


# ----- the reference -------------------------------------------------------
def test_contract_and_defaults_are_the_v41_pool() -> None:
    assert BLOCK_MAX_NUMERIC_CONTRACT == "block_max_ordered_ieee_v1"
    assert BLOCK_MAX_V41_BLOCK == 8
    assert BLOCK_MAX_V41_ROW_BLOCKS == 2048
    assert block_max_padding_code() == NEG_INF
    assert block_max_padding_code(8, 7) == 0xFF80  # BF16 negative infinity
    assert block_max_padding_code(5, 10) == 0xFC00  # FP16 negative infinity


def test_reference_agrees_with_the_host_binary32_comparison() -> None:
    """A third path: the host's own float ordering over non-zero finite scores."""

    rng = random.Random(4113)
    rows = []
    for _ in range(64):
        length = rng.randint(1, 40)
        row = []
        while len(row) < length:
            candidate = rng.uniform(-1e6, 1e6) * (10 ** rng.randint(-6, 6))
            if candidate == 0.0:
                continue
            row.append(_code(struct.unpack("<f", struct.pack("<f", candidate))[0]))
        rows.append(row)
    reduced = block_max_rows(rows, 8)
    for row, blocks in zip(rows, reduced):
        assert len(blocks) == (len(row) + 7) // 8
        for index, code in enumerate(blocks):
            chunk = row[index * 8:(index + 1) * 8]
            assert _value(code) == max(_value(item) for item in chunk)


def test_partial_final_block_is_the_negative_infinity_padding() -> None:
    rng = random.Random(99)
    row = [_code(rng.uniform(-100.0, -1.0)) for _ in range(9)]
    padded = row + [NEG_INF] * 7
    assert block_max_rows([row], 8) == block_max_rows([padded], 8)
    #: and the tail is not dropped: two blocks, the second one position wide
    assert len(block_max_rows([row], 8)[0]) == 2
    assert block_max_rows([row], 8)[0][1] == row[8]


def test_a_zero_pad_would_change_the_answer() -> None:
    """The rule matters: every score in this block is negative."""

    row = [_code(-3.0), _code(-2.0), _code(-9.0)]
    assert block_max_rows([row], 8) == ((_code(-2.0),),)
    assert block_max_rows([row + [_code(0.0)] * 5], 8) == ((_code(0.0),),)


def test_signed_zero_and_infinity_order() -> None:
    assert block_max_rows([[NEG_ZERO, _code(0.0)]], 2) == ((_code(0.0),),)
    assert block_max_rows([[_code(0.0), NEG_ZERO]], 2) == ((_code(0.0),),)
    assert block_max_rows([[NEG_ZERO, NEG_ZERO]], 2) == ((NEG_ZERO,),)
    assert block_max_rows([[NEG_INF, NEG_INF]], 2) == ((NEG_INF,),)
    assert block_max_rows([[POS_INF, _code(3.4e38)]], 2) == ((POS_INF,),)
    assert block_max_rows([[NEG_INF, _code(-3.4e38)]], 2) == ((_code(-3.4e38),),)


def test_subnormal_order_is_exact() -> None:
    least = 1                       # 2**-149
    greatest_subnormal = 0x007FFFFF
    assert block_max_rows([[least, greatest_subnormal, NEG_ZERO]], 3) == ((greatest_subnormal,),)
    assert block_max_rows([[least, 0x80000001]], 2) == ((least,),)


def test_rows_of_every_length_and_the_empty_row() -> None:
    rng = random.Random(7)
    for length in range(0, 33):
        row = [_code(rng.uniform(-5.0, 5.0)) for _ in range(length)]
        blocks = block_max_rows([row], 8)[0]
        assert len(blocks) == (length + 7) // 8
    assert block_max_rows([[]], 8) == ((),)


def test_block_of_one_is_the_identity() -> None:
    rng = random.Random(11)
    row = [_code(rng.uniform(-5.0, 5.0)) for _ in range(17)]
    assert block_max_rows([row], 1) == (tuple(row),)


def test_bf16_and_fp16_rows() -> None:
    #: BF16: 1.0 is 0x3f80, 2.0 is 0x4000, -1.0 is 0xbf80
    assert block_max_rows([[0x3F80, 0x4000, 0xBF80, 0xFF80]], 4,
                          exponent_bits=8, mantissa_bits=7) == ((0x4000,),)
    #: FP16: 1.0 is 0x3c00, 2.0 is 0x4000
    assert block_max_rows([[0x3C00, 0x4000, 0xBC00]], 3,
                          exponent_bits=5, mantissa_bits=10) == ((0x4000,),)


def test_refusals() -> None:
    with pytest.raises(BlockMaxReferenceError):
        block_max_rows([[0x7FC00000, _code(1.0)]], 2)          # NaN
    with pytest.raises(BlockMaxReferenceError):
        block_max_rows([[_code(1.0)]], 0)                      # block below one
    with pytest.raises(BlockMaxReferenceError):
        block_max_rows([[1 << 32]], 1)                         # code outside the format
    with pytest.raises(BlockMaxReferenceError):
        block_max_rows([[0x1_0000]], 1, exponent_bits=8, mantissa_bits=7)  # too wide for BF16
    with pytest.raises(BlockMaxReferenceError):
        block_max_rows([[_code(1.0)]], 8, exponent_bits=1, mantissa_bits=1)


# ----- the RTL text: no frozen model geometry ------------------------------
def _rtl_text() -> str:
    return RTL.read_text(encoding="utf-8")


def _rtl_body() -> list[str]:
    """The block's lines after the port list, comments removed."""

    lines = _rtl_text().splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith(");"))
    body = []
    for line in lines[start:]:
        stripped = line.split("//")[0]
        if stripped.strip():
            body.append(stripped)
    return body


@pytest.mark.parametrize("parameter,default", [
    ("BLOCK", "8"),
    ("SCORE_W", "32"),
    ("EXP_W", "8"),
    ("MANT_W", "23"),
    ("MAX_BLOCKS", "2048"),
    ("CMP_STAGES", "1"),
])
def test_geometry_is_a_parameter_with_the_v41_default(parameter: str, default: str) -> None:
    pattern = re.compile(rf"^\s*parameter integer {parameter}\s*=\s*{default}\s*[,)]",
                         re.MULTILINE)
    assert pattern.search(_rtl_text()), f"{parameter} is not a parameter defaulting to {default}"


def test_no_extent_literal_survives_in_the_block_body() -> None:
    """The mistake this criterion exists to prevent: a geometry constant in the body."""

    body = "\n".join(_rtl_body())
    for literal in ("2048", "4096", "2047", "'d8", "8'd8", "16'd8"):
        assert literal not in body, f"the body carries the literal {literal}"
    #: the only numeric literals the body may carry are bit-width-neutral ones
    for match in re.finditer(r"\b(\d+)\b", body):
        assert match.group(1) in {"0", "1", "2", "7", "8", "32", "255"}, (
            f"unexpected numeric literal {match.group(1)} in the block body")


def test_the_module_header_states_the_pipeline_and_the_padding_rule() -> None:
    header = _rtl_text().split("module ot_a3_route_block_max")[0]
    assert "STAGE COUNT" in header
    assert "INITIATION INTERVAL" in header
    assert "NON-MULTIPLE ROW LENGTH" in header
    assert "block_max_ordered_ieee_v1" in header
    assert "runtime/reference/candidate_pool.py" in header


def test_the_block_refers_to_the_engine_package_by_scope() -> None:
    text = _rtl_text()
    assert "ot_a3_engine_pkg::ERR_SHAPE" in text
    assert "import ot_a3" not in text


# ----- the campaign record -------------------------------------------------
@pytest.mark.skipif(not CAMPAIGN_JSON.exists(), reason="campaign has not been run")
def test_campaign_record_is_a_pass_on_both_simulators() -> None:
    record = json.loads(CAMPAIGN_JSON.read_text(encoding="utf-8"))
    assert record["schema"] == "opentallas.rtl.a3_v41_block_max_campaign.v1"
    assert record["status"] == "pass"
    assert record["simulators_agree"] is True
    assert record["reference"] == "runtime.reference.candidate_pool.block_max_rows"
    assert "5.050" in record["tools"]["verilator"]["version"]
    assert record["tools"]["verilator"]["executable"].startswith("<HOME>/.local/opentallas-tools")
    assert "Icarus Verilog version 11" in record["tools"]["iverilog"]["version"]
    assert record["verilator_lint"]["clean"] is True

    names = {configuration["name"] for configuration in record["configurations"]}
    assert "v41_binary32_block8" in names
    assert len(names) >= 6, "the sweep is the no-frozen-geometry evidence"
    for configuration in record["configurations"]:
        checks = configuration["checks_per_simulator"]
        assert set(checks) == {"iverilog", "verilator"}
        assert checks["iverilog"] == checks["verilator"] > 0
        assert configuration["simulators_agree"] is True
        assert configuration["status"] == "pass"
        for interval in configuration["initiation_interval"]:
            assert interval["cycles_per_block"] == 1.0
        depth = configuration["geometry"]["pipeline_depth"]
        block = configuration["geometry"]["block"]
        levels = 0 if block <= 1 else (block - 1).bit_length()
        assert depth == levels * configuration["geometry"]["cmp_stages"] + 2


@pytest.mark.skipif(not CAMPAIGN_JSON.exists(), reason="campaign has not been run")
def test_campaign_record_states_what_it_does_not_establish() -> None:
    record = json.loads(CAMPAIGN_JSON.read_text(encoding="utf-8"))
    boundary = record["claim_boundary"]
    assert boundary["reference_derived_from_the_rtl"] is False
    assert boundary["wired_into_ot_a3_engine_array_or_reachable_from_a_program"] is False
    assert boundary["is_placed_or_routed"] is False
    assert boundary["establishes_a_frequency_a_period_or_any_physical_number"] is False
    assert boundary["checks_block_max_against_an_independent_python_reference"] is True
    assert record["limitations"]


@pytest.mark.skipif(not CAMPAIGN_JSON.exists(), reason="campaign has not been run")
def test_campaign_sources_have_not_moved_underneath_the_record() -> None:
    record = json.loads(CAMPAIGN_JSON.read_text(encoding="utf-8"))
    stale = {}
    for path, digest in record["source_sha256"].items():
        current = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        if current != digest:
            stale[path] = {"recorded": digest, "current": current}
    assert not stale, f"the record is bound to superseded sources: {stale}"
