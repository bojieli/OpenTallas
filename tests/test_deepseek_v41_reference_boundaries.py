"""Boundaries of the DeepSeek-V4.1-Flash reference oracle and its references.

WP-H of docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md.  What is pinned here
is the part of the oracle that can be checked without a GPU, a checkpoint or the
vendor snapshot: the two reference extensions section 7 asks for, and the
refusals that stop the oracle reporting a number it did not measure.

The vendor-executing half is evidence, not a test: it needs the pinned snapshot
and a device, and it lives in
``results/abi3/deepseek_v41_reference_oracle_probe.json``.  The tests that would
depend on it are skipped rather than faked.
"""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import pytest

from runtime.reference.candidate_pool import (
    CANDIDATE_MASK_CONTRACT,
    CandidateMaskError,
    NEGATIVE_INFINITY,
    select_candidate_blocks,
    select_candidate_mask,
)
from runtime.reference.engram import (
    ENGRAM_GATE_NUMERIC_CONTRACT,
    EngramReferenceError,
    PINNED_GATE_CLAMP_BINARY32,
    PINNED_GATE_FORM,
    PINNED_NORM_EPS_BINARY32,
    engram_gate_pinned_divergences,
    engram_gate_pinned_form,
    prove_pinned_form_differs,
)
from runtime.reference.formats import decode_binary32, encode_binary32_rne

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "results/abi3/deepseek_v41_reference_oracle_probe.json"


# ---------------------------------------------------------------------------
# select_candidate_blocks: the three decisions between scores and block ids
# ---------------------------------------------------------------------------


def test_pin_is_derived_from_reach_not_from_the_axis():
    """The pinned block follows `compress_lens`, not the width.

    This is the distinction `select_candidate_mask` cannot express: during
    prefill every query pins a different block, and pinning the axis's last
    block would admit positions the query cannot reach.
    """
    width, block = 64, 8
    scores = [Fraction(0)] * width
    for reach, expected in ((1, 0), (8, 0), (9, 1), (24, 2), (25, 3), (64, 7)):
        result = select_candidate_blocks(scores[:], reach, topk_blocks=1, block_size=block)
        assert result["pinned_block"] == expected, (reach, result["pinned_block"])
        #: with topk_blocks=1 the pin is the ONLY admitted block, so the mask
        #: shows the pin alone.
        assert result["blocks"] == (expected,)


def test_decode_case_agrees_with_select_candidate_mask():
    """When the query reaches the whole axis the two references must coincide.

    `select_candidate_mask(pin_last_block=True)` is the decode case, and a
    disagreement here would mean the RTL operand and the pinned function part
    company on the configuration they share.
    """
    width, block = 40, 8
    scores = [Fraction(index) for index in range(width)]
    blocks = select_candidate_blocks(scores, width, topk_blocks=3, block_size=block)
    mask = select_candidate_mask(
        list(blocks["blocks"]), width=width, block=block, pin_last_block=True
    )
    assert blocks["population"] == mask["population"]
    assert blocks["pinned_block"] == mask["pinned_block"]
    assert blocks["contract"] == mask["contract"] == CANDIDATE_MASK_CONTRACT


def test_partial_final_block_is_padded_not_wrapped():
    """A width that is not a multiple of the block admits only real positions."""
    width, block = 21, 8  # three blocks, the last holding 5 real positions
    scores = [Fraction(1)] * width
    result = select_candidate_blocks(scores, width, topk_blocks=8, block_size=block)
    assert result["block_count"] == 3
    assert len(result["mask"]) == width
    assert result["population"] == width  # every block admitted, tail truncated
    assert result["pinned_block"] == 2


def test_unreachable_blocks_are_dropped_not_admitted_as_padding():
    """A pick whose block score is -inf is dropped, so padding is never admitted.

    `topk_blocks` larger than the number of REACHABLE blocks is the ordinary
    case early in a sequence; a reference that admitted the leftover picks would
    report a pool wider than the context.
    """
    width, block = 64, 8
    scores = [Fraction(index) for index in range(11)] + [NEGATIVE_INFINITY] * (width - 11)
    result = select_candidate_blocks(scores, 11, topk_blocks=8, block_size=block)
    #: Only blocks 0 and 1 hold finite scores; block 1 is the pin.
    assert result["blocks"] == (0, 1)
    assert result["dropped_negative_infinity_blocks"]
    assert all(not bit for bit in result["mask"][16:])


def test_pool_population_is_bounded_by_the_pool_not_by_the_context():
    """`topk_blocks * block_size` bounds the admitted count at any width.

    The plan's `candidate_pool_bound` checker states this bound; here it is
    checked against a context far wider than the pool, which is the only
    configuration in which the bound can bind.
    """
    width, block, topk = 4_096, 8, 64
    scores = [Fraction(index % 97) for index in range(width)]
    result = select_candidate_blocks(scores, width, topk_blocks=topk, block_size=block)
    assert result["population"] <= topk * block
    assert result["population"] < width


def test_geometry_is_argued_not_frozen():
    """Every extent is an argument: a different block size is an ordinary input."""
    scores = [Fraction(index) for index in range(30)]
    for block in (2, 3, 5, 8, 16):
        result = select_candidate_blocks(scores, 30, topk_blocks=2, block_size=block)
        assert result["block_size"] == block
        assert result["block_count"] == -(-30 // block)
        assert len(result["mask"]) == 30


@pytest.mark.parametrize(
    "kwargs",
    [
        {"compress_lens": 0},
        {"compress_lens": 65},
        {"compress_lens": -1},
        {"topk_blocks": 0},
        {"block_size": 0},
    ],
)
def test_illegal_bounds_are_refused(kwargs):
    """A bound outside what the axis can express is a fault, not a clamp."""
    call = {"compress_lens": 8, "topk_blocks": 2, "block_size": 8}
    call.update(kwargs)
    with pytest.raises(CandidateMaskError):
        select_candidate_blocks([Fraction(0)] * 64, **call)


def test_a_non_numeric_score_is_refused():
    with pytest.raises(CandidateMaskError):
        select_candidate_blocks(
            [Fraction(0), 1.5, Fraction(2)], 3, topk_blocks=1, block_size=2
        )


# ---------------------------------------------------------------------------
# the pinned Engram gate, and its divergence from engram_gate_fp32_v1
# ---------------------------------------------------------------------------


def test_pinned_form_and_contract_v1_are_different_functions():
    """The divergence is exhibited by execution, not asserted.

    If this test ever fails because the two agree, the four divergences D1-D4
    have been resolved and the evidence documents must be revisited.
    """
    proof = prove_pinned_form_differs()
    assert proof["pinned_form"] == PINNED_GATE_FORM
    assert proof["contract_v1"] == ENGRAM_GATE_NUMERIC_CONTRACT
    assert proof["gate_codes_differ"] is True
    assert proof["outputs_differ"] is True
    assert PINNED_GATE_FORM != ENGRAM_GATE_NUMERIC_CONTRACT


def test_every_divergence_is_named_and_says_whether_it_changes_a_value():
    divergences = engram_gate_pinned_divergences()
    assert {row["id"] for row in divergences} == {
        "D1_clamp_target",
        "D2_mean_not_sum",
        "D3_operand_roles",
        "D4_gated_term",
    }
    for row in divergences:
        assert row["changes_value"] in ("yes", "no")
        assert row["pinned"] and row["contract_v1"]


def test_the_clamp_floors_the_magnitude_of_the_dot():
    """D1: the 1e-6 floors |dot|, so a vanishing dot still yields sigmoid(1e-3).

    An orthogonal h and key give a dot of exactly zero.  Under the pinned form
    the clamp lifts |dot| to 1e-6, whose square root is 1e-3, so the gate is
    sigmoid(1e-3) and NOT sigmoid(0) = 0.5 exactly.
    """
    one = encode_binary32_rne(Fraction(1))
    zero = encode_binary32_rne(Fraction(0))
    #: h = (1, 1), key = (1, -1): the weighted dot is 1*1 + 1*(-1) = 0.
    result = engram_gate_pinned_form(
        (one, one),
        (one, encode_binary32_rne(Fraction(-1))),
        (one, one),
        (one, one),
    )
    assert result["dot_code"] in (zero, 0x80000000)  # +0 or -0
    #: the clamp fired, and the gate is sigmoid(+/-1e-3), not sigmoid(0)
    assert result["clamped"] is True
    gate = decode_binary32(result["gate_code"]).value
    assert gate is not None
    assert gate != Fraction(1, 2)
    assert abs(float(gate) - 0.5) < 1e-3


def test_the_gate_multiplies_value_alone():
    """D4: the residual term is gate * value, with no key factor.

    With h = 0 and value = 1 the output is exactly the gate, which a
    `gate * (key * value)` combine could only match when key is 1.
    """
    one = encode_binary32_rne(Fraction(1))
    zero = encode_binary32_rne(Fraction(0))
    two = encode_binary32_rne(Fraction(2))
    result = engram_gate_pinned_form((zero, zero), (two, two), (one, one), (one, one))
    assert result["output_codes"] == (result["gate_code"], result["gate_code"])


def test_the_pinned_epsilons_are_two_different_values():
    """D1 and D2: the clamp is 1e-6 and the normaliser's eps is 1e-20.

    A single epsilon used twice is the reading `engram_gate_fp32_v1` took, and
    the released module's own attributes contradict it.
    """
    clamp = decode_binary32(PINNED_GATE_CLAMP_BINARY32).value
    eps = decode_binary32(PINNED_NORM_EPS_BINARY32).value
    assert clamp is not None and eps is not None
    assert clamp != eps
    assert float(clamp) == pytest.approx(1e-6, rel=1e-6)
    assert float(eps) == pytest.approx(1e-20, rel=1e-6)


def test_the_gate_width_is_derived_from_the_operands():
    """No width is frozen: the dim**-0.5 factor follows the row length."""
    one = encode_binary32_rne(Fraction(1))
    for width in (1, 2, 8, 17, 256):
        result = engram_gate_pinned_form(
            (one,) * width, (one,) * width, (one,) * width, (one,) * width
        )
        assert result["width"] == width
        assert len(result["output_codes"]) == width


def test_mismatched_operand_rows_are_refused():
    one = encode_binary32_rne(Fraction(1))
    with pytest.raises(EngramReferenceError):
        engram_gate_pinned_form((one, one), (one,), (one, one), (one, one))
    with pytest.raises(EngramReferenceError):
        engram_gate_pinned_form((), (), (), ())


# ---------------------------------------------------------------------------
# the oracle's own refusals
# ---------------------------------------------------------------------------


def test_a_zero_call_count_is_a_refusal_not_a_count():
    """The V4 failure, as a check.

    A rung reporting zero index scans is indistinguishable from an
    implementation that declined to scan its index, so `require_counts` refuses
    rather than reporting the zero.
    """
    from tools.run_deepseek_v41_reference_oracle import (
        COUNTERS,
        OracleError,
        require_counts,
    )

    previous = COUNTERS.indexer_calls
    COUNTERS.indexer_calls = 0
    try:
        with pytest.raises(OracleError, match="zero calls"):
            require_counts("Indexer.forward")
        COUNTERS.indexer_calls = 3
        assert require_counts("Indexer.forward") == {"Indexer.forward": 3}
    finally:
        COUNTERS.indexer_calls = previous


def test_a_count_with_no_layer_id_is_refused():
    """A count attributed to a layer nobody named is refused, not filed under 0."""
    from tools.run_deepseek_v41_reference_oracle import COUNTERS, OracleError

    previous = COUNTERS.layer_id
    COUNTERS.layer_id = None
    try:
        with pytest.raises(OracleError, match="no layer id"):
            COUNTERS._layer(None)
    finally:
        COUNTERS.layer_id = previous


def test_the_profile_supplies_exactly_three_recipe_widths():
    """The comparison needs a main, an index and a window recipe width."""
    from tools.run_deepseek_v41_reference_oracle import profile_recipe_widths

    recipe = profile_recipe_widths()
    widths = recipe["recipe_entry_bytes"]
    assert set(widths) == {"main", "index", "window"}
    for role, value in widths.items():
        assert value is not None and value > 0, role
    assert recipe["num_layers"] > 0


def test_no_entry_width_is_transcribed_in_the_oracle():
    """The measured widths must come from a buffer, not from a constant.

    A literal 1024, 528, 288, 256 or 68 in the tool would be exactly the V4
    mistake -- a hardcoded engine width that went on being wrong silently.  This
    reads the source and refuses those literals outside comments.
    """
    import tokenize

    path = ROOT / "tools/run_deepseek_v41_reference_oracle.py"
    #: Tokenize rather than split on "#": the prose in this tool's docstrings
    #: quotes the V4 widths on purpose, and prose is not a hardcoded width.
    #: Only NUMBER tokens can be one.
    numbers = set()
    with path.open("rb") as handle:
        for token in tokenize.tokenize(handle.readline):
            if token.type == tokenize.NUMBER:
                numbers.add(token.string.replace("_", ""))
    #: The V4.1 recipe and measured entry widths, and the V4 recipe width the
    #: module docstring cites.  256 and 512 are deliberately NOT in this list:
    #: they are the index width and the main extent, but they are also ordinary
    #: token counts and kernel tile sizes, so their presence would not
    #: distinguish a transcribed width from a prefill length.
    for literal in ("1024", "528", "288", "68", "583", "890", "264"):
        assert literal not in numbers, (
            f"{literal} appears as a numeric literal in executable code; an "
            "entry width must be read off a buffer, not transcribed"
        )


# ---------------------------------------------------------------------------
# the executed evidence, when it is present
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PROBE.is_file(), reason="the oracle probe has not been run")
def test_the_probe_records_both_widths_and_does_not_correct_one_into_the_other():
    probe = json.loads(PROBE.read_text())
    assert probe["schema"] == "opentallas.abi3.reference_oracle.v1"
    assert probe["status"] == "completed"
    comparison = probe["entry_widths"]["comparison"]
    roles = {row["role"]: row for row in comparison["rows"]}
    assert set(roles) == {"main", "index", "window"}
    for row in roles.values():
        assert row["measured_grade"] == "executed"
        assert row["recipe_grade"] == "read_from_profile"
        assert row["measured_entry_bytes"] is not None
        assert row["recipe_entry_bytes"] is not None


@pytest.mark.skipif(not PROBE.is_file(), reason="the oracle probe has not been run")
def test_the_probe_exercised_the_indexer_wrap():
    """The single most important line of WP-H, checked against the artifact."""
    probe = json.loads(PROBE.read_text())
    instrumentation = probe["instrumentation"]
    assert instrumentation["wrapped_before_first_run"] is True
    assert "Indexer.forward" in instrumentation["wrapped_symbols"]
    assert "Engram.forward" in instrumentation["wrapped_symbols"]
    assert instrumentation["verification"]["all_installed"] is True
    assert instrumentation["observed_calls"]["Indexer.forward"] > 0
    assert instrumentation["observed_calls"]["Engram.forward"] > 0


@pytest.mark.skipif(not PROBE.is_file(), reason="the oracle probe has not been run")
def test_the_probe_reached_a_rung_where_the_pool_bound_binds():
    """A scan measurement taken only below the bound would test nothing."""
    probe = json.loads(PROBE.read_text())
    scans = probe["index_scans"]
    assert scans["rungs_where_scan_exceeds_the_pool_bound"] > 0
    consumers = [row for row in scans["rows"] if row["role"] == "pool_consumer"]
    assert consumers, "no pool-consuming layer was exercised"
    binding = [row for row in consumers if row["scan_exceeds_pool_bound"]]
    assert binding, "the pool bound never bound"
    for row in binding:
        assert (
            row["index_positions_admitted_total"]
            <= row["candidate_pool_position_bound"]
        )
        assert row["index_positions_scored_total"] > row[
            "index_positions_admitted_total"
        ]


@pytest.mark.skipif(not PROBE.is_file(), reason="the oracle probe has not been run")
def test_the_probe_claims_no_token():
    """Nothing below section 4 of the plan is a TPOT, and no token was produced."""
    probe = json.loads(PROBE.read_text())
    assert probe["tokens"]["grade"] == "not_run"
    assert probe["tokens"]["tokens_produced"] == 0
    assert probe["tokens"]["blocked"] is True
    assert probe["tokens"]["missing_prerequisites"]
