"""RTL 3.0: the ABI 3.0 RTL must agree with the frozen contracts and the device.

Three independent bindings are checked here:

1. the RTL registry package is a faithful transcription of
   ``runtime.abi3.constants`` -- opcodes, subopcode bounds, flags, descriptor
   types, trap classes and the program magic;
2. the vector set is reproducible and is the golden model's own observation,
   not a hand-written expectation; and
3. both simulators replay every vector through the RTL and print the exact
   marker derived from that observation.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import sys

import pytest

from runtime.sim import engine as _engine_module


@pytest.fixture(autouse=True)
def _restore_engine_registry():
    """Undo this module's engine stubbing before the next test runs.

    ``_install_engine_stubs`` binds every dispatchable operation to a recording
    no-op in a process-global table.  That is right for generating RTL control-
    plane vectors and catastrophic for anything that runs afterwards in the
    same process: ``importlib`` caches the engine modules, so re-importing them
    does not restore the real handlers, and a later golden execution silently
    computes nothing.  It did exactly that to
    ``test_rtl_abi3_engine.py::test_vector_set_is_reproducible``, whose whole
    purpose is correlating the *real* engines -- it passed alone and failed in
    the suite.
    """
    snapshot = _engine_module.snapshot_registry()
    try:
        yield
    finally:
        _engine_module.restore_registry(snapshot)

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import (  # noqa: E402
    INSTRUCTION_FLAG_MASK,
    NO_ID,
    PROGRAM_MAGIC,
    SUBOPCODES,
    DescriptorType,
    Major,
    TrapClass,
)
from runtime.abi3.descriptors import PREDICATE_TYPE  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402
from tools import build_abi3_rtl_vectors as generator  # noqa: E402
from tools import rtl_abi3_campaign as campaign  # noqa: E402

VECTOR_DIR = ROOT / "testdata/compiler/abi3"
VECTOR_JSON = VECTOR_DIR / "abi3_rtl_vectors.json"
PACKAGE = ROOT / "rtl/abi3/ot_a3_pkg.sv"
CAMPAIGN_JSON = ROOT / "results/rtl/abi3_campaign.json"

TOOLS_AVAILABLE = all(
    shutil.which(tool) is not None for tool in ("iverilog", "vvp", "g++")
)


def _vectors() -> dict:
    return json.loads(VECTOR_JSON.read_text(encoding="utf-8"))


def _package_text() -> str:
    return PACKAGE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. registry transcription
# ---------------------------------------------------------------------------
def test_rtl_package_transcribes_the_opcode_registry() -> None:
    text = _package_text()
    for family in Major:
        match = re.search(rf"A3_MAJOR_{family.name}\s*=\s*8'h([0-9a-f]{{2}})", text)
        assert match, f"RTL package does not define {family.name}"
        assert int(match.group(1), 16) == int(family)

        bound = re.search(
            rf"A3_MAJOR_{family.name}:\s*a3_major_sub_bound\s*=\s*"
            r"\{1'b1,\s*8'h([0-9a-f]{2})\}",
            text,
        )
        assert bound, f"RTL package declares no subopcode bound for {family.name}"
        highest = max(int(member) for member in SUBOPCODES[family])
        assert int(bound.group(1), 16) == highest, family.name
        # Contiguity is what makes a bound a complete legality statement.
        assert {int(m) for m in SUBOPCODES[family]} == set(range(highest + 1))


def test_rtl_package_transcribes_traps_flags_and_descriptor_types() -> None:
    text = _package_text()
    trap_names = {
        TrapClass.NONE: "A3_TRAP_NONE",
        TrapClass.ADMISSION_OR_VERSION: "A3_TRAP_ADMISSION",
        TrapClass.AUTHENTICATION_OR_INTEGRITY: "A3_TRAP_INTEGRITY",
        TrapClass.DESCRIPTOR_OR_ADDRESS: "A3_TRAP_DESCRIPTOR",
        TrapClass.CAPABILITY_OR_RESOURCE: "A3_TRAP_CAPABILITY",
        TrapClass.ILLEGAL_INSTRUCTION_OR_CONTROL_FLOW: "A3_TRAP_ILLEGAL",
        TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE: "A3_TRAP_NUMERIC",
        TrapClass.MEMORY_SUBSYSTEM: "A3_TRAP_MEMORY",
        TrapClass.ENGINE: "A3_TRAP_ENGINE",
        TrapClass.STATE_TRANSACTION: "A3_TRAP_STATE",
        TrapClass.TIMEOUT_OR_WATCHDOG: "A3_TRAP_WATCHDOG",
        TrapClass.LINK_OR_NOC: "A3_TRAP_LINK",
        TrapClass.POWER_RESET_OR_THERMAL: "A3_TRAP_POWER",
        TrapClass.INTERNAL_INVARIANT: "A3_TRAP_INTERNAL",
    }
    for trap, name in trap_names.items():
        match = re.search(rf"{name}\s*=\s*16'd(\d+)", text)
        assert match, name
        assert int(match.group(1)) == int(trap)

    mask = re.search(r"A3_FLAG_MASK\s*=\s*16'h([0-9a-f]{4})", text)
    assert mask and int(mask.group(1), 16) == INSTRUCTION_FLAG_MASK

    no_id = re.search(r"A3_NO_ID\s*=\s*32'h([0-9a-f_]+)", text)
    assert no_id and int(no_id.group(1).replace("_", ""), 16) == NO_ID

    magic = re.search(r"A3_PROGRAM_MAGIC\s*=\s*64'h([0-9a-f_]+)", text)
    assert magic
    assert int(magic.group(1).replace("_", ""), 16) == int.from_bytes(
        PROGRAM_MAGIC, "little"
    )

    for descriptor in DescriptorType:
        match = re.search(
            rf"A3_DESC_{descriptor.name}\s*=\s*16'h([0-9a-f]{{4}})", text
        )
        assert match, descriptor.name
        assert int(match.group(1), 16) == int(descriptor)
    predicate = re.search(r"A3_DESC_PREDICATE\s*=\s*16'h([0-9a-f]{4})", text)
    assert predicate and int(predicate.group(1), 16) == PREDICATE_TYPE


# ---------------------------------------------------------------------------
# 2. the vector set is the golden model's own observation
# ---------------------------------------------------------------------------
def test_vector_set_is_reproducible(tmp_path: Path) -> None:
    assert generator.build(["--output", str(tmp_path)]) == 0
    for name in sorted(_vectors()["image_sha256"]):
        assert (tmp_path / name).read_bytes() == (VECTOR_DIR / name).read_bytes(), name
    rebuilt = json.loads((tmp_path / "abi3_rtl_vectors.json").read_text())
    assert rebuilt == _vectors()


def test_every_expectation_comes_from_the_device_or_a_declared_override() -> None:
    """One documented place may differ from the golden observation.

    A branch target outside the authenticated body: the RTL rejects that
    instruction record at admission, so it never retires and never transfers
    control, while the golden model transfers control first and faults at the
    target index.  The two traps that once also needed an override -- a loop
    over its declared maximum and a commit with no open prepare -- no longer
    do: the golden model names the raising instruction itself.
    """
    vectors = _vectors()
    overrides = set()
    for case in vectors["cases"]:
        if not case["device_executed"]:
            # Two distinct reasons a case never reaches the golden model, and
            # they must not be allowed to stand in for each other.  Either the
            # normative decoder rejects the image outright, in which case the
            # rejection must be stated in Python's own words; or the verifier
            # refuses the deployment at admission, in which case the image is
            # well-formed and the case exists to pin the refusal.
            if case["admitted"]:
                assert case["python_rejects_image"], case["name"]
            else:
                assert case["python_rejects_image"] is None, case["name"]
                assert case["note"], case["name"]
            continue
        for key, value in case["expected"].items():
            if key in case["golden"] and case["golden"][key] != value:
                overrides.add((case["name"], key))
                assert case["note"], case["name"]
    assert overrides == {
        ("negative_branch_out_of_range", "branches"),
        ("negative_branch_out_of_range", "first_fault"),
        ("negative_branch_out_of_range", "retired"),
    }


def test_issue_events_are_legal_opcodes_and_counted() -> None:
    vectors = _vectors()
    total = 0
    for case in vectors["cases"]:
        for issue in case["expected_issues"]:
            family = Major(issue["family"])
            assert issue["sub"] in {int(m) for m in SUBOPCODES[family]}
            assert family is not Major.CONTROL
            # Every issuing family except recovery names a typed descriptor.
            if family is not Major.RECOVERY:
                assert issue["descriptor_id"] != NO_ID
            total += 1
    assert total == vectors["issue_event_count"] == 185
    assert vectors["case_count"] == len(vectors["cases"])
    assert vectors["program_run_count"] == sum(
        1 for case in vectors["cases"] if case["runs_program"]
    )


def test_negative_cases_cover_the_required_failures() -> None:
    names = {case["name"]: case for case in _vectors()["cases"]}
    required = {
        "negative_instruction_crc": 2,
        "negative_illegal_opcode": 5,
        "negative_illegal_subopcode": 5,
        "negative_reserved_flag": 5,
        "negative_invert_without_predicate": 5,
        "negative_branch_out_of_range": 5,
        "negative_loop_over_maximum": 4,
        "negative_trap_mid_transaction": 5,
        "negative_commit_without_prepare": 9,
        "negative_wait_unsignalled": 13,
        "negative_work_bound": 10,
    }
    for name, trap in required.items():
        assert name in names, name
        assert names[name]["expected"]["trap_class"] == trap, name
        assert names[name]["expected"]["complete"] is False, name

    # A trap in the middle of a transaction may not commit any state.
    mid = names["negative_trap_mid_transaction"]
    assert mid["expected"]["state_prepares"] == 1
    assert mid["expected"]["state_commits"] == 1          # staged
    assert mid["expected"]["state_commits_applied"] == 0  # never applied
    assert mid["expected"]["state_rows_committed"] == 0

    headers = {
        "negative_header_magic": 1,
        "negative_header_version": 1,
        "negative_header_instruction_bytes": 1,
        "negative_header_zero_count": 1,
        "negative_header_reserved": 1,
        "negative_header_crc": 2,
    }
    for name, trap in headers.items():
        assert names[name]["expected_header_legal"] is False, name
        assert names[name]["expected_header_trap_class"] == trap, name


# ---------------------------------------------------------------------------
# 2b. amendment A13: the partial final iteration of a block loop
# ---------------------------------------------------------------------------
def _views_of(case: dict) -> list[dict]:
    return case["expected_views"]


def _block_views(case: dict, slot: int) -> list[int]:
    """Leading extents of one operand slot, for dispatches inside a loop.

    A case's tail dispatch outside the loop resolves static views; filtering on
    a live loop binding keeps the A13 assertions about the blocked operand.
    """
    return [
        view["dim0"]
        for view in case["expected_views"]
        if view["slot"] == slot and view["loops"]
    ]


def test_a13_vectors_cover_every_block_shape() -> None:
    """The four shapes a block loop over a symbolic extent can take.

    Wire format section 12.4: with tile height T over an extent of N rows, the
    final iteration holds N - T*floor(N/T) rows.  A vector set that only ever
    exercised N divisible by T would pass with A13 unimplemented, which is what
    OI-16 recorded.  ``a13_extent_below_block`` pins the guard that
    ``ViewResolver._remaining_rows`` applies and the prose does not spell out: a
    remaining count that is not below the view's own extent leaves it alone.
    ``a13_extent_above_block`` pins the complementary decision -- a leading
    extent above the block is refused at admission, because that inequality is
    the only one on which the two statements of A13 disagree.

    ``a13_non_leading_axis`` and ``a13_mixed_axes`` pin the question that comes
    before all of those: *whether* a term is walking the leading axis at all.
    Section 12.4 derives it -- one iteration advances by one whole block of the
    leading axis, ``term_stride == stride0 * bound_divisor`` -- rather than
    assuming that a loop-induction term does.  Both the clamp and the admission
    rule apply only to terms that satisfy it.
    """
    names = {case["name"]: case for case in _vectors()["cases"]}
    block = generator.A13_BLOCK

    # (a) N divisible by T: no partial iteration, and A13 must not clamp.
    exact = names["a13_block_exact"]
    leading = _block_views(exact, 0) + _block_views(exact, 4)
    assert leading and set(leading) == {block}, leading

    # (b) N with a partial final iteration.
    for name, expected in (
        ("a13_block_partial", [block, block, 1]),
        ("a13_block_partial_mid", [block, 3]),
    ):
        case = names[name]
        assert _block_views(case, 0) == expected, name
        assert _block_views(case, 4) == expected, name

    # (c) N < T: one short iteration holding the whole span.
    short = names["a13_block_short"]
    assert _block_views(short, 0) == [block - 1]

    # (d) N = 0.  The ABI admits it: ceil(0/T) is zero, so the loop is
    # zero-trip, its body never runs and no view is resolved.  The case still
    # issues its tail operation, so a pass here is not a pass over nothing.
    empty = names["a13_block_empty"]
    assert empty["symbols"]["0"] == 0
    assert empty["expected"]["loop_iterations"] == 0
    assert empty["expected"]["issued"] == 1
    assert all(v["index"] != 1 for v in _views_of(empty))
    assert len(_views_of(empty)) == 3

    # A loop that is not symbol-bounded has no partial iteration to state.
    constant = names["a13_constant_loop"]
    assert _block_views(constant, 0) == [block, block, block]

    # Two symbol-bounded loops over one view: the smallest remaining wins.
    # Both walk the leading axis -- each states the stride its own block
    # implies, ``stride0 * bound_divisor`` -- because a term that does not walk
    # it contributes no bound at all and the fold would never happen.  The two
    # blocks differ, so the condition has to be evaluated against each loop's
    # own divisor rather than one of them twice.
    nested = names["a13_nested_blocks"]
    assert _block_views(nested, 0) == [block, 2, block, 2, 1, 1]

    # The A4 maximum of four dynamic terms, where a term walk that counts to
    # the term count inclusive could wrap back onto term zero.
    four = names["a13_four_terms"]
    assert _block_views(four, 0) == [block, 2, 1, 1]
    assert all(
        v["element_offset"] % 16 == 3
        for v in _views_of(four) if v["slot"] == 0
    )

    # A leading extent below the block: the guard the prose leaves implicit.
    assert _block_views(names["a13_extent_below_block"], 0) == [2, 2]

    # A loop over an axis that is *not* the view's leading one.  Section 12.4
    # derives which terms walk the leading axis rather than assuming that any
    # loop-induction term does: one iteration advances by one whole block of
    # it, so ``term_stride == stride0 * bound_divisor``.  The mHC branch
    # reduction is the shape that forced the derivation -- its leading axis is
    # four hyper-connection streams while its loop steps over tokens -- and
    # clamping it would present four streams as one.
    mhc = names["a13_non_leading_axis"]
    streams = generator.MHC_STREAMS
    token_block = generator.MHC_TOKEN_BLOCK
    assert mhc["admitted"] is True
    assert _block_views(mhc, 0) == [streams] * generator.A13_MAX_ITER
    assert _block_views(mhc, 4) == [streams] * generator.A13_MAX_ITER
    # The final iteration *is* partial -- SPAN_TOKENS is not a multiple of the
    # block -- so the extent above is a decision, not an absence of one.
    assert mhc["symbols"]["0"] % token_block != 0
    # A4 still applies where A13 does not: the window advances by one token
    # block per iteration even though the extent never moves.
    assert [
        view["element_offset"]
        for view in _views_of(mhc) if view["slot"] == 0 and view["loops"]
    ] == [
        index * token_block * generator.A13_ROW_ELEMENTS
        for index in range(generator.A13_MAX_ITER)
    ]
    # And the admission rule follows the same condition: this leading extent is
    # above its loop's block, which is refused only for a term that clamps.
    assert streams > token_block

    # One view, two symbol-bounded block loops, both with a partial final
    # iteration, and only the token loop walks the leading axis.  The clamp is
    # a per-term decision: a resolver that decided once for the whole view
    # would clamp the expert loop's two-stream slice as well.
    mixed = names["a13_mixed_axes"]
    assert mixed["admitted"] is True
    assert _block_views(mixed, 0) == [block, block, block, block, 1, 1]
    assert _block_views(mixed, 4) == [block, block, block, block, 1, 1]

    # A leading extent *above* the block is refused at admission rather than
    # resolved.  It is the one shape on which section 12.4's formula and
    # ViewResolver._remaining_rows disagree, and every such disagreement has
    # dim0 > bound_divisor, so refusing that inequality makes the two
    # statements of A13 the same rule.  A refused case resolves no views.
    above = names["a13_extent_above_block"]
    assert above["admitted"] is False
    assert _views_of(above) == []


def test_a18_vectors_reach_a_non_leading_axis_and_a_group_unit() -> None:
    """Wire format section 12.8: the axis and the unit the view declares.

    A13 clamps ``dim0`` in the bound symbol's own units.  The DeepSeek
    compressor's pool has neither: its request-dependent extent counts *groups*
    of four tokens and it sits at axis 1, behind the batch.  These cases pin
    both halves against the reference resolver's answer.
    """
    names = {case["name"]: case for case in _vectors()["cases"]}
    ratio = generator.A18_RATIO
    groups_per_block = generator.A18_GROUP_BLOCK

    def group_extents(case: dict, slot: int) -> list[int]:
        return [
            view["extent"]
            for view in case["expected_views"]
            if view["slot"] == slot and view["loops"] and view["extent_axis"] == 1
        ]

    # (a) every iteration full: the unit changes nothing when nothing is partial.
    exact = names["a18_group_axis_exact"]
    assert group_extents(exact, 0) == [groups_per_block, groups_per_block]

    # (b) the case A13 could not state.  Twelve tokens of four, blocked eight:
    # the second iteration has four tokens left, which is one group.  A13's
    # clamp is in tokens, so it would have said four; and it clamps dim0, which
    # here is the batch.
    partial = names["a18_group_axis_partial"]
    assert group_extents(partial, 0) == [groups_per_block, 1]
    assert group_extents(partial, 4) == [groups_per_block, 1]
    assert partial["symbols"]["0"] == generator.A18_TOKEN_BLOCK + ratio

    # (c) one whole group and one token over: the floor is the operator's rule.
    assert group_extents(names["a18_group_axis_short"], 0) == [1]

    # (d) no whole group at all.  The floored extent is zero and A18 does not
    # clamp to zero: a view has no zero extent, so "the request has none of
    # this axis" is a predicate question and the operand keeps its block.
    none = names["a18_group_axis_no_whole_group"]
    assert none["symbols"]["0"] < ratio
    assert group_extents(none, 0) == [groups_per_block]

    # (e) a non-leading axis in the symbol's own unit -- the compressor's
    # *input*, which is [1, tokens, ...] because the operator groups along the
    # token axis and cannot have the batch there.
    unit_one = names["a18_axis_unit_one"]
    assert group_extents(unit_one, 0) == [generator.A18_TOKEN_BLOCK, 1]

    # (e2) the third shape: an extent that is *longer* than the request's rows.
    # The attention KV join carries a sliding window, so its extent is
    # ``span + window`` -- and a clamp can only ever shorten, so before A18 the
    # number had no spelling and the engine refused it.  The bias is added
    # after the division and is not part of the step, which is why the window
    # is there for the short final iteration too.
    window = generator.A18_WINDOW
    block = generator.A18_TOKEN_BLOCK
    biased = names["a18_biased_extent"]
    assert group_extents(biased, 0) == [block + window, ratio + window]
    single = names["a18_biased_extent_single_block"]
    assert group_extents(single, 0) == [ratio + window]

    # (e3) all three parts of a compressed layer's join in one affine function:
    # ``context + window + context/4`` is ``floor(5 * context / 4) + window``
    # exactly, because ``5c/4 = c + c/4`` and ``c`` is an integer.  This is the
    # case that says the numerator earns its four bytes.
    both = names["a18_numerator_and_bias"]
    span = block + ratio
    assert group_extents(both, 0) == [
        (ratio + 1) * block // ratio + window,          # full iteration
        (ratio + 1) * (span - block) // ratio + window,  # partial
    ]

    # (f) two admission refusals, both because a declaration that cannot be
    # resolved would leave the operand at its declared maximum -- the
    # 65,536-candidate failure the amendment exists to remove.  The refusal has
    # to name the thing it refused, so the reason is checked and not just the
    # verdict.
    generator._install_engine_stubs()
    capability = generator.rtl_capability()
    reasons = {
        "a18_axis_beyond_rank": (
            generator.case_a18_axis_beyond_rank,
            "extent axis 3 is outside the rank-2 view",
        ),
        "a18_unit_does_not_divide_block": (
            generator.case_a18_unit_does_not_divide_block,
            "no dynamic term walks that axis in that unit",
        ),
    }
    assert generator.A18_WINDOW > 0
    for name, (build, reason) in reasons.items():
        assert names[name]["admitted"] is False, name
        assert _views_of(names[name]) == [], name
        report = verify_deployment(build(capability).deployment, capability)
        assert not report.admitted, name
        assert any(reason in error for error in report.errors), (name, report.errors)


def test_a26_edge_mask_reuses_one_offset_and_clamps_only_the_tail() -> None:
    """The RTL and functional resolver see a 4, 4, 2 rolling-buffer extent."""
    case = next(
        case
        for case in _vectors()["cases"]
        if case["name"] == "a26_edge_mask_partial"
    )
    assert case["admitted"] is True
    source = [
        view
        for view in case["expected_views"]
        if view["slot"] == 0 and view["loops"]
    ]
    destination = [
        view
        for view in case["expected_views"]
        if view["slot"] == 4 and view["loops"]
    ]
    assert [view["extent"] for view in source] == [4, 4, 2]
    assert [view["extent"] for view in destination] == [4, 4, 2]
    assert {view["element_offset"] for view in source} == {0}
    assert len({view["element_offset"] for view in destination}) == 1


def test_a18_leaves_every_pre_amendment_view_where_it_was() -> None:
    """A13 is the ``extent_axis = 0, extent_unit = 1`` case, checked not asserted.

    Section 12.8 claims the substitution is an identity.  Rather than trust the
    algebra, this re-derives A13's own rule -- the pre-amendment resolver, five
    lines of it -- and requires it to agree with the shipped resolver on the
    exhaustive parameter space section 12.4 already cites: divisors 1..8,
    extents 1..11, bounds 0..19 and iterations 0..5.
    """
    from runtime.sim.memory import ViewResolver

    def pre_a18(dim0: int, divisor: int, bound: int, iteration: int) -> int:
        """ViewResolver as it stood before A18, for a term that walks axis 0."""
        remaining = bound - iteration * divisor
        if remaining <= 0 or remaining >= divisor:
            return dim0
        return remaining if 0 < remaining < dim0 else dim0

    def post_a18(dim0: int, divisor: int, bound: int, iteration: int) -> int:
        """The shipped rule at numerator 1, unit 1, bias 0 -- all four zeros."""
        numerator, unit, bias = 1, 1, 0
        block = (numerator * divisor) // unit
        tokens = bound - iteration * divisor
        if tokens <= 0:
            return dim0
        extent = (numerator * tokens) // unit + bias
        if extent <= 0 or extent >= block + bias:
            return dim0
        return extent if 0 < extent < dim0 else dim0

    compared = 0
    for divisor in range(1, 9):
        for dim0 in range(1, 12):
            for bound in range(0, 20):
                for iteration in range(0, 6):
                    assert pre_a18(dim0, divisor, bound, iteration) == post_a18(
                        dim0, divisor, bound, iteration
                    ), (dim0, divisor, bound, iteration)
                    compared += 1
    assert compared == 8 * 11 * 20 * 6

    # And the walk test: at numerator 1 and unit 1 the step is the divisor, so
    # ``term_stride == stride0 * step`` is ``term_stride == stride0 * divisor``,
    # which is what A13 wrote.
    from runtime.abi3.descriptors import iteration_extent

    assert ViewResolver._walks_extent_axis.__doc__
    for divisor in range(1, 9):
        assert iteration_extent(divisor, 1, 1) == divisor


def test_a18_vector_images_move_no_pre_amendment_extent() -> None:
    """Every view the pre-A18 vector set resolved resolves to the same numbers.

    The claim in section 12.8 is that no existing program changes meaning.  The
    401 operand views the 53 pre-A18 cases resolved are all still in the image,
    all with extent axis zero, and all with the extent they had -- the seven new
    cases only add to the set.

    Later amendments that add a non-A18 case add to the non-A18 side of the
    count, and the number below moves with them: A21's ``a21_unstaged_commit``
    resolves three, taking 401 to 404, and A26's fixed-edge transfer resolves
    six, taking it to 410. What the assertion pins is the extent rule, which is
    checked view by view below and has not moved.
    """
    recorded = _vectors()
    views = [
        view
        for case in recorded["cases"]
        for view in case["expected_views"]
    ]
    assert len(views) == recorded["view_resolution_count"]
    # Every view of a case that is not an A18 case declares axis zero, and its
    # resolved extent is its leading extent -- which is what A13 published.
    legacy = [
        view
        for case in recorded["cases"]
        if not case["name"].startswith("a18")
        for view in case["expected_views"]
    ]
    assert len(legacy) == 410
    assert all(view["extent_axis"] == 0 for view in legacy)
    assert all(view["extent"] == view["dim0"] for view in legacy)
    # And the A18 cases are the only place a non-zero axis appears at all.
    a18 = [
        view
        for case in recorded["cases"]
        if case["name"].startswith("a18")
        for view in case["expected_views"]
    ]
    assert a18 and any(view["extent_axis"] == 1 for view in a18)


def test_a13_golden_extents_come_from_the_reference_resolver() -> None:
    """Every recorded extent is re-derived by ViewResolver, not by this file."""
    from runtime.abi3.descriptors import ExtendedDescriptorType, Symbol
    from runtime.sim.device import Device

    generator._install_engine_stubs()
    capability = generator.rtl_capability()
    builders = {
        "a13_block_exact": generator.case_a13_block_exact,
        "a13_block_partial": generator.case_a13_block_partial,
        "a13_block_partial_mid": generator.case_a13_block_partial_mid,
        "a13_block_short": generator.case_a13_block_short,
        "a13_block_empty": generator.case_a13_block_empty,
        "a13_extent_below_block": generator.case_a13_extent_below_block,
        "a13_extent_above_block": generator.case_a13_extent_above_block,
        "a13_symbol_term": generator.case_a13_symbol_term,
        "a13_constant_loop": generator.case_a13_constant_loop,
        "a13_nested_blocks": generator.case_a13_nested_blocks,
        "a13_four_terms": generator.case_a13_four_terms,
        "a13_non_leading_axis": generator.case_a13_non_leading_axis,
        "a13_mixed_axes": generator.case_a13_mixed_axes,
    }
    recorded = {case["name"]: case for case in _vectors()["cases"]}
    compared = 0
    for name, build in builders.items():
        case = build(capability)
        if not case.expect_admitted:
            # A refused deployment never reaches a device, so it has no
            # resolved views to compare.  What it has to prove is that the
            # verifier refuses it, which is the whole point of the case.
            assert not verify_deployment(case.deployment, capability).admitted, name
            assert recorded[name]["expected_views"] == []
            continue
        device = Device(case.deployment, capability, verify=False, trace=True)
        session = device.create_session()
        device.run_transaction(
            session, entrypoint_id=0, symbols=dict(case.symbols)
        )
        symbols = generator.effective_symbols(case)
        fresh: list[tuple] = []
        for entry in device.trace:
            for view in generator.resolved_views(device, entry, symbols):
                fresh.append(
                    (view["descriptor_id"], view["slot"], view["dim0"],
                     view["element_offset"], view["rank"])
                )
        stored = [
            (v["descriptor_id"], v["slot"], v["dim0"], v["element_offset"],
             v["rank"])
            for v in recorded[name]["expected_views"]
        ]
        assert fresh == stored, name
        compared += len(fresh)
    assert compared > 0
    assert compared == sum(
        len(recorded[name]["expected_views"]) for name in builders
    )
    # SPAN_TOKENS = 0 is admissible and resolves nothing, so the A13 evidence
    # cannot rest on that case alone.
    assert compared > len(recorded["a13_block_empty"]["expected_views"])

    # A13 is only visible where a partial extent actually occurs.
    partial = [
        v for name in builders for v in recorded[name]["expected_views"]
        if v["dim0"] != v["dims"][0] or v["dim0"] < generator.A13_BLOCK
    ]
    assert partial, "no vector exercises a partial final extent"
    del ExtendedDescriptorType, Symbol


# ---------------------------------------------------------------------------
# 2c. amendments A14, A15 and A16 -- fields the RTL must *not* read
# ---------------------------------------------------------------------------
def _communication_scopes(case) -> list[int]:
    """Every COMMUNICATION descriptor's participant scope, in table order."""
    from runtime.abi3.descriptors import ExtendedDescriptorType

    table = case.deployment.table
    return [
        int(table[did].payload["participant_scope"])
        for did in table.ids_of_type(ExtendedDescriptorType.COMMUNICATION)
    ]


def _payload_bytes(case, descriptor_id: int, offset: int, length: int) -> bytes:
    """Raw encoded bytes of one descriptor's payload.

    The images both simulators load are 192-byte record prefixes -- a 64-byte
    header and both 64-byte payload blocks -- so a byte read here is a byte the
    RTL really has in memory, not one the prefix elides.
    """
    record = case.deployment.table._records[descriptor_id]  # noqa: SLF001
    assert len(record) >= 64 + offset + length
    return bytes(record[64 + offset : 64 + offset + length])


def test_a14_scope_byte_is_encoded_and_changes_nothing_the_rtl_sees() -> None:
    """Wire format 12.5: ``participant_scope`` reaches the fabric, not the
    microsequencer.

    A LINK instruction's whole admission in ``ot_a3_microsequencer.sv`` is the
    S_ENG_WAIT check ``desc_type != expected_type`` against
    ``a3_family_descriptor_type(A3_MAJOR_LINK) = A3_DESC_COMMUNICATION``; the
    payload is never loaded.  Two cases state that as evidence rather than as a
    reading of the source: the same LINK program with byte 80 at zero and with
    byte 80 at 2 and 1 must leave the *identical* observation.  Before these
    cases the vector set issued no LINK at all, so the claim was untested.
    """
    capability = generator.rtl_capability()
    node = generator.case_a14_link_node_scope(capability)
    wafer = generator.case_a14_link_wafer_scopes(capability)
    refused = generator.case_a14_scope_unsupported(capability)

    # The scopes are really in the payload, at the offset the amendment names.
    assert _communication_scopes(node) == [0, 0]
    assert _communication_scopes(wafer) == [2, 1]
    from runtime.abi3.descriptors import ExtendedDescriptorType

    for case, expected in ((node, (0, 0)), (wafer, (2, 1))):
        ids = case.deployment.table.ids_of_type(
            ExtendedDescriptorType.COMMUNICATION
        )
        for did, scope in zip(ids, expected):
            assert _payload_bytes(case, did, 80, 1) == bytes([scope])
            # A14 shrank the reserved span to 47 bytes at offset 81; the rest
            # of it is still zero, so the only difference between the two
            # programs' communication payloads is the scope byte itself.
            assert _payload_bytes(case, did, 81, 47) == bytes(47)

    recorded = {case["name"]: case for case in _vectors()["cases"]}
    a = recorded["a14_link_node_scope"]
    b = recorded["a14_link_wafer_scopes"]
    assert a["expected"] == b["expected"]
    # The two deployments name their descriptors in different orders, so the
    # comparison is the issue *sequence* -- family, subopcode and instruction
    # index -- rather than the identifiers those two tables happened to assign.
    assert [
        (i["family"], i["sub"], i["index"], i["mnemonic"])
        for i in a["expected_issues"]
    ] == [
        (i["family"], i["sub"], i["index"], i["mnemonic"])
        for i in b["expected_issues"]
    ]
    assert [
        (v["slot"], v["dim0"], v["dims"], v["element_offset"], v["rank"])
        for v in a["expected_views"]
    ] == [
        (v["slot"], v["dim0"], v["dims"], v["element_offset"], v["rank"])
        for v in b["expected_views"]
    ]
    # And the LINK family really issues: a pass over an empty issue list would
    # say nothing about the descriptor-type check.
    families = {(i["family"], i["sub"]) for i in a["expected_issues"]}
    assert (int(Major.LINK), 6) in families
    assert (int(Major.LINK), 7) in families

    # The two admission rules of section 12.5 both fire on a single chip.
    assert not verify_deployment(refused.deployment, capability).admitted
    assert recorded["a14_scope_unsupported"]["admitted"] is False
    assert recorded["a14_scope_unsupported"]["expected_views"] == []
    errors = " ".join(recorded["a14_scope_unsupported"]["verifier_errors"])
    assert "RETICLE-scoped" in errors and "SINGLE_CHIP" in errors


def test_a15_block_scale_rows_does_not_move_a_resolved_extent() -> None:
    """Wire format 12.6: ``scale_block_rows`` at payload offset 104.

    Offset 104 is the first word past the four eight-byte dynamic terms, which
    is exactly where a resolver that walked one term too far would land.
    ``ot_a3_view_resolver.sv`` reads nothing beyond bit 831 -- term three's
    stride -- so a nonzero word there must be inert.  The case carries a scaled
    view and an unscaled sibling of identical geometry through a block loop, so
    the two are compared under A13's clamp rather than only at rest.
    """
    capability = generator.rtl_capability()
    case = generator.case_a15_block_scale_rows(capability)
    from runtime.abi3.descriptors import ExtendedDescriptorType

    views = case.deployment.table.ids_of_type(ExtendedDescriptorType.TENSOR_VIEW)
    scaled = [
        vid for vid in views
        if int(case.deployment.table[vid].payload["scale_block_rows"]) > 1
    ]
    assert len(scaled) == 1
    assert _payload_bytes(case, scaled[0], 104, 4) == (2).to_bytes(4, "little")
    # The rest of the span A15 shortened is still reserved-zero.
    assert _payload_bytes(case, scaled[0], 108, 20) == bytes(20)

    recorded = {c["name"]: c for c in _vectors()["cases"]}["a15_block_scale_rows"]
    per_slot: dict[int, list[tuple]] = {}
    for view in recorded["expected_views"]:
        per_slot.setdefault(view["slot"], []).append(
            (view["dim0"], view["dims"], view["element_offset"], view["rank"])
        )
    # Slot 0 is the block-scaled operand, slot 1 the unscaled sibling: same
    # dims, same terms, same loop.  A13 clamps the last iteration of both.
    assert per_slot[0] == per_slot[1]
    assert [row[0] for row in per_slot[0]] == [
        generator.A13_BLOCK, generator.A13_BLOCK, 1
    ]

    # And the divisibility rule is an admission rule, not an engine fault.
    indivisible = generator.case_a15_scale_rows_indivisible(capability)
    assert not verify_deployment(indivisible.deployment, capability).admitted
    refused = {c["name"]: c for c in _vectors()["cases"]}[
        "a15_scale_rows_indivisible"
    ]
    assert refused["admitted"] is False
    assert refused["expected_views"] == []
    assert any(
        "scale block" in error for error in refused["verifier_errors"]
    ), refused["verifier_errors"]


OPERATOR_PAYLOAD_BITS = re.compile(r"op_payload\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]")
OPERATOR_PAYLOAD_PLUS = re.compile(r"op_payload\s*\[\s*(\d+)\s*\+:\s*(\d+)\s*\]")


def test_a17_join_axis_never_reaches_the_microsequencer() -> None:
    """Wire format 12.7: ``aux_id_0`` reaches the engine, not the sequencer.

    A17 gives ``REDUCTION.GROUPED_CONCAT`` a join axis in ``aux_id_0``, which
    the OPERATOR payload places at byte 48 -- bits 384 and up. The
    microsequencer's whole reading of an operator payload is the operand walk:
    ``input_view_0..3`` and ``output_view_0..1``, payload bytes 24 through 47,
    bits 192 through 383. So the amendment cannot change anything RTL 3.0 does,
    and this states that as evidence rather than as a reading of the source.

    Three things are checked. The axis really is at byte 48 and really differs
    between the two programs; the two programs issue the same instruction
    sequence and walk the same operand slots; and no module under ``rtl/abi3``
    indexes an operator payload at or above bit 384 at all.
    """
    from runtime.abi3.descriptors import ExtendedDescriptorType

    capability = generator.rtl_capability()
    zero = generator.case_a17_join_axis_zero(capability)
    one = generator.case_a17_join_axis_one(capability)
    refused = generator.case_a17_join_axis_undefined(capability)

    # 1. The join axis is where the amendment says it is, and it is the only
    #    auxiliary slot either program names.
    for case, axis in ((zero, 0), (one, 1)):
        ids = case.deployment.table.ids_of_type(ExtendedDescriptorType.OPERATOR)
        assert len(ids) == 1
        did = ids[0]
        assert _payload_bytes(case, did, 48, 4) == axis.to_bytes(4, "little")
        assert _payload_bytes(case, did, 52, 12) == bytes([0xFF]) * 12
        assert verify_deployment(case.deployment, capability).admitted

    recorded = {case["name"]: case for case in _vectors()["cases"]}
    a = recorded["a17_join_axis_zero"]
    b = recorded["a17_join_axis_one"]

    # 2. The same instruction stream and the same operand walk. The four input
    #    views necessarily have different extents -- a row join and a column
    #    join of one buffer are different rectangles -- but the sequencer's
    #    behaviour is the slots it walks and the order it walks them in, and the
    #    output view, which both programs share, resolves identically.
    assert [
        (i["family"], i["sub"], i["index"], i["mnemonic"])
        for i in a["expected_issues"]
    ] == [
        (i["family"], i["sub"], i["index"], i["mnemonic"])
        for i in b["expected_issues"]
    ]
    assert {(int(Major.REDUCTION), 3)} == {
        (i["family"], i["sub"]) for i in a["expected_issues"]
    }
    assert [(v["slot"], v["rank"], v["operand"]) for v in a["expected_views"]] == [
        (v["slot"], v["rank"], v["operand"]) for v in b["expected_views"]
    ]
    assert len(a["expected_views"]) == 5
    out_a = next(v for v in a["expected_views"] if v["operand"] == "output_view_0")
    out_b = next(v for v in b["expected_views"] if v["operand"] == "output_view_0")
    for key in ("dim0", "dims", "element_offset", "rank"):
        assert out_a[key] == out_b[key]
    assert a["expected"] == b["expected"]

    # 3. Nothing in the RTL indexes an operator payload above the operand walk.
    highest = 0
    for source in sorted(Path(ROOT / "rtl/abi3").glob("*.sv")):
        text = source.read_text(encoding="utf-8")
        for match in OPERATOR_PAYLOAD_BITS.finditer(text):
            highest = max(highest, int(match.group(1)))
        for match in OPERATOR_PAYLOAD_PLUS.finditer(text):
            highest = max(highest, int(match.group(1)) + int(match.group(2)) - 1)
    assert highest == 383, highest

    # 4. An axis A17 does not define is an admission refusal, so the vector set
    #    carries one the verifier must reject and the RTL must never run.
    assert not verify_deployment(refused.deployment, capability).admitted
    assert recorded["a17_join_axis_undefined"]["admitted"] is False
    assert recorded["a17_join_axis_undefined"]["expected_views"] == []
    errors = " ".join(recorded["a17_join_axis_undefined"]["verifier_errors"])
    assert "join axis 2" in errors and "A17" in errors


def test_every_operand_slot_of_the_rtl_walk_is_exercised() -> None:
    """``S_VIEW_SCAN`` walks six operand slots; all six must be populated.

    Amendment A16 is the convention that first needed the slots past two inputs
    and one output -- a partial dequantisation carries a third input plane, and
    the ``noaux_tc`` gate writes a second output -- and until those two cases
    existed three arms of the RTL's operand multiplexer had never selected a
    real view.  ``input_view_3`` was the last one left: no operator in the set
    named four inputs until amendment A17's four-block concatenations did.  A
    resolver reached through an arm nothing populates is a resolver nothing
    checks, and now none of the six is such an arm.
    """
    slots = {
        view["slot"]
        for case in _vectors()["cases"]
        for view in case["expected_views"]
    }
    assert slots == {0, 1, 2, 3, 4, 5}, slots
    joined = {case["name"]: case for case in _vectors()["cases"]}
    for name in ("a17_join_axis_zero", "a17_join_axis_one"):
        assert [v["slot"] for v in joined[name]["expected_views"]] == [0, 1, 2, 3, 4]
    recorded = {case["name"]: case for case in _vectors()["cases"]}
    convert = recorded["a16_convert_carried_plane"]
    assert [v["slot"] for v in convert["expected_views"]] == [0, 1, 2, 4]
    topk = recorded["a16_route_biased_topk"]
    assert [v["slot"] for v in topk["expected_views"]] == [0, 1, 4, 5]
    # aux_id_0 sits immediately past the view slots the walk reads, so a
    # populated one is the nearest thing to an overrun this payload allows.
    capability = generator.rtl_capability()
    case = generator.case_a16_route_biased_topk(capability)
    from runtime.abi3.descriptors import ExtendedDescriptorType

    operators = case.deployment.table.ids_of_type(ExtendedDescriptorType.OPERATOR)
    aux = [
        int(case.deployment.table[oid].payload["aux_id_0"]) for oid in operators
    ]
    assert generator.A16_TOPK in aux


# ---------------------------------------------------------------------------
# 3. two-simulator replay
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    not TOOLS_AVAILABLE, reason="Icarus, vvp and a C++ compiler are required"
)
def test_campaign_replays_both_simulators(tmp_path: Path) -> None:
    summary = campaign.run(tmp_path / "build")
    assert summary["status"] == "pass", summary["cases"]
    assert [case["name"] for case in summary["cases"]] == ["iverilog", "verilator"]
    marker = _vectors()["required_marker"]
    for case in summary["cases"]:
        assert case["status"] == "pass"
        assert case["compile_returncode"] == 0
        assert case["run_returncode"] == 0
        assert case["marker_present"], case["run_log"]
        assert marker in case["run_log"]
        assert case["checks"] and case["checks"] > 0
        assert "/tmp/" not in case["compile_command"]
    assert "Verilator 5.05" in summary["tools"]["verilator"]["version"]
    assert "version 11.0" in summary["tools"]["iverilog"]["version"]
    assert summary["correlation"]["issue_event_count"] == 185
    assert summary["correlation"]["reference"] == "runtime.sim.device.Device"
    # A view comparison that compared nothing would be a vacuous pass.
    assert summary["correlation"]["view_resolution_count"] == (
        _vectors()["view_resolution_count"]
    )
    assert summary["correlation"]["view_resolution_count"] > 0


def test_campaign_refuses_to_overwrite_an_existing_artifact(tmp_path: Path) -> None:
    target = tmp_path / "abi3_campaign.json"
    target.write_text("{}\n", encoding="utf-8")
    assert campaign.main(["--output", str(target)]) == 2
    assert target.read_text(encoding="utf-8") == "{}\n"


@pytest.mark.skipif(
    not CAMPAIGN_JSON.exists(), reason="no retained campaign artifact"
)
def test_retained_campaign_artifact_is_bound_to_these_sources() -> None:
    retained = json.loads(CAMPAIGN_JSON.read_text(encoding="utf-8"))
    assert retained["status"] == "pass"
    assert retained["required_marker"] == _vectors()["required_marker"]
    assert CAMPAIGN_JSON.read_bytes() == (
        json.dumps(retained, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    for path, digest in retained["source_sha256"].items():
        actual = campaign.sha256_file(ROOT / path)
        assert actual == digest, f"{path} changed since the campaign was recorded"


# ---------------------------------------------------------------------------
# 4. the deployments this program ships, co-simulated
# ---------------------------------------------------------------------------
# The 65 vectors above are real ABI 3.0 programs written *for* the campaign.
# These bind the separate campaign that replays the three programs the project
# claims to run.  The deployment bundles live under the ignored build/ tree, so
# anything that needs one skips; everything that can be checked from the
# committed vector images and the retained artifact runs unconditionally.
DEPLOYMENT_VECTOR_DIR = ROOT / "testdata/compiler/abi3_deployment"
DEPLOYMENT_VECTOR_JSON = DEPLOYMENT_VECTOR_DIR / "abi3_deployment_rtl_vectors.json"
DEPLOYMENT_CAMPAIGN_JSON = ROOT / "results/rtl/abi3_deployment_campaign.json"


def _deployment_vectors() -> dict:
    return json.loads(DEPLOYMENT_VECTOR_JSON.read_text(encoding="utf-8"))


def _deployment_bundles_present() -> bool:
    from tools import build_abi3_deployment_rtl_vectors as deployment_generator

    return all(
        (ROOT / target.deployment).exists()
        for target in deployment_generator.TARGETS
    )


def test_deployment_vector_set_names_the_programs_this_program_ships() -> None:
    """The digests are the contract: a rebuilt deployment is a different one."""
    vectors = _deployment_vectors()
    shipped = {
        entry["key"]: entry for entry in vectors["deployments"]
    }
    assert shipped["qwen3-8b-rom-single-chip"]["deployment_sha256"].startswith(
        "c71ee77e"
    )
    assert shipped["qwen3-8b-rom-single-chip"]["instruction_count"] == 75
    assert shipped["qwen3-8b-rom-single-chip"]["descriptor_count"] == 239
    assert shipped["qwen3-8b-hbm-single-chip"]["deployment_sha256"].startswith(
        "fb5c66df"
    )
    assert shipped["qwen3-8b-hbm-single-chip"]["instruction_count"] == 75
    assert shipped["qwen3-8b-hbm-single-chip"]["descriptor_count"] == 218
    assert shipped["deepseek-v4-flash-rom-wafer"][
        "deployment_sha256"
    ].startswith("27dd5f55")
    assert shipped["deepseek-v4-flash-rom-wafer"]["instruction_count"] == 1171
    assert shipped["deepseek-v4-flash-rom-wafer"]["descriptor_count"] == 3409
    for entry in shipped.values():
        assert entry["admitted"], (entry["key"], entry["verifier_errors"])


def test_deployment_vector_images_match_the_recorded_digests() -> None:
    vectors = _deployment_vectors()
    for name, digest in vectors["image_sha256"].items():
        assert campaign.sha256_file(DEPLOYMENT_VECTOR_DIR / name) == digest, name


def test_deployment_vector_set_reads_the_rtl_bounds_from_the_rtl() -> None:
    """A bound restated in a second place is a bound that will disagree.

    The vector set records the sequencer's implementation bounds as they stand
    in ``rtl/abi3/ot_a3_pkg.sv``; if that file changes, the record is stale and
    the campaign has to be re-recorded rather than quietly reinterpreted.
    """
    from tools import build_abi3_deployment_rtl_vectors as deployment_generator

    recorded = _deployment_vectors()["rtl_implementation_bounds"]
    assert recorded["source"] == "rtl/abi3/ot_a3_pkg.sv"
    assert recorded["values"] == deployment_generator.rtl_bounds()


def test_deployment_depth_is_recorded_per_case_not_assumed() -> None:
    """Every case says how deep it went, in the program's own terms."""
    vectors = _deployment_vectors()
    assert vectors["case_count"] == len(vectors["cases"])
    for record in vectors["cases"]:
        depth = record["depth"]
        assert depth["instructions_retired"] > 0
        assert depth["engine_issues"] > 0
        assert (
            depth["distinct_static_instructions_reached"]
            <= depth["static_instructions_in_program"]
        )
        # A prefix that stops early has to say so; these all reach COMPLETE.
        assert record["ran_to_completion"]
        assert not record["work_bound_lowered_for_cosimulation"]
    assert vectors["view_resolution_count"] > 0
    assert vectors["issue_event_count"] == sum(
        record["issue_count"] for record in vectors["cases"]
    )


@pytest.mark.skipif(
    not _deployment_bundles_present(),
    reason="the deployment bundles are not built (build/ is ignored)",
)
def test_deployment_vector_set_is_reproducible(tmp_path: Path) -> None:
    from tools import build_abi3_deployment_rtl_vectors as deployment_generator

    assert deployment_generator.build(["--output", str(tmp_path)]) == 0
    for name in sorted(_deployment_vectors()["image_sha256"]):
        assert (tmp_path / name).read_bytes() == (
            DEPLOYMENT_VECTOR_DIR / name
        ).read_bytes(), name
    rebuilt = json.loads(
        (tmp_path / "abi3_deployment_rtl_vectors.json").read_text(encoding="utf-8")
    )
    assert rebuilt == _deployment_vectors()


@pytest.mark.skipif(
    not _deployment_bundles_present(),
    reason="the deployment bundles are not built (build/ is ignored)",
)
def test_a_lowered_work_bound_bounds_both_sides(tmp_path: Path) -> None:
    """The knob that would bound a prefix, exercised rather than advertised.

    None of the six cases needs it -- every one reaches COMPLETE inside its own
    declared bound -- but a bounding mechanism nobody runs is a bounding
    mechanism nobody knows works.  Lowering it must stop the golden model at
    the bound, leave the *declared* header bound untouched so header admission
    still checks the real program, and say so per case.
    """
    from tools import build_abi3_deployment_rtl_vectors as deployment_generator

    assert (
        deployment_generator.build(
            ["--output", str(tmp_path), "--max-retired-work", "1000"]
        )
        == 0
    )
    bounded = json.loads(
        (tmp_path / "abi3_deployment_rtl_vectors.json").read_text(encoding="utf-8")
    )
    assert bounded["completion_count"] == 0
    for record, unbounded in zip(bounded["cases"], _deployment_vectors()["cases"]):
        assert record["work_bound_lowered_for_cosimulation"]
        assert record["work_bound"] == 1000
        assert not record["ran_to_completion"]
        assert record["depth"]["instructions_retired"] == 1001
        # The header still declares what the program declares.
        assert (
            record["declared_max_retired_work"]
            == unbounded["declared_max_retired_work"]
        )
        # A prefix is a prefix: it is the same issue stream, truncated.
        assert record["issue_count"] < unbounded["issue_count"]


@pytest.mark.skipif(
    not DEPLOYMENT_CAMPAIGN_JSON.exists(),
    reason="no retained deployment campaign artifact",
)
def test_retained_deployment_campaign_is_bound_to_these_sources() -> None:
    retained = json.loads(DEPLOYMENT_CAMPAIGN_JSON.read_text(encoding="utf-8"))
    assert retained["required_marker"] == _deployment_vectors()["required_marker"]
    assert DEPLOYMENT_CAMPAIGN_JSON.read_bytes() == (
        json.dumps(retained, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    for path, digest in retained["source_sha256"].items():
        actual = campaign.sha256_file(ROOT / path)
        assert actual == digest, f"{path} changed since the campaign was recorded"
    assert retained["simulators_counted"] == [
        "iverilog_vvp",
        "verilator_cpp_executable",
    ]
    assert retained["cross_simulator_agreement"][
        "simulators_observed_the_same_cases"
    ], "the two simulators did not observe the same thing"
    # A pass and a recorded divergence cannot both be true.
    assert (retained["status"] == "pass") == (not retained["divergences"])


@pytest.mark.skipif(
    not DEPLOYMENT_CAMPAIGN_JSON.exists(),
    reason="no retained deployment campaign artifact",
)
def test_a_deployment_within_the_rtl_bounds_correlates_exactly() -> None:
    """The invariant this campaign exists to hold.

    A shipped deployment whose demands fit the bounds ``rtl/abi3/ot_a3_pkg.sv``
    declares must correlate with ``runtime.sim.device.Device`` on every case; a
    deployment that exceeds one of those bounds is expected to diverge, and the
    artifact has to say which bound and where.  Written this way the test holds
    both today, with DeepSeek-V4-Flash over the state-slot bound, and after the
    bound is raised and it correlates -- and it fails if a deployment is quietly
    dropped from the campaign to make it green.
    """
    retained = json.loads(DEPLOYMENT_CAMPAIGN_JSON.read_text(encoding="utf-8"))
    vectors = _deployment_vectors()
    diverged = {entry["case"] for entry in retained["divergences"]}
    correlated = set(retained["correlated_cases"])
    assert diverged | correlated == {record["name"] for record in vectors["cases"]}
    assert not (diverged & correlated)

    for deployment in retained["what_ran"]["deployments"]:
        cases = [
            record["name"]
            for record in vectors["cases"]
            if record["deployment"] == deployment["key"]
        ]
        assert cases, deployment["key"]
        if deployment["co_simulable_within_rtl_bounds"]:
            assert set(cases) <= correlated, (
                f"{deployment['key']} fits every bound the RTL declares and "
                "must correlate on every case"
            )
        else:
            assert set(cases) <= diverged, deployment["key"]
            assert deployment["rtl_bound_overruns"], deployment["key"]


@pytest.mark.skipif(
    not DEPLOYMENT_CAMPAIGN_JSON.exists(),
    reason="no retained deployment campaign artifact",
)
def test_deployment_campaign_states_what_it_does_not_establish() -> None:
    retained = json.loads(DEPLOYMENT_CAMPAIGN_JSON.read_text(encoding="utf-8"))
    boundary = retained["claim_boundary"]
    assert set(boundary) == {"establishes", "does_not_establish"}
    assert boundary["establishes"]
    prose = " ".join(boundary["does_not_establish"].values())
    assert "engine_arithmetic" in boundary["does_not_establish"]
    assert "no checkpoint byte is read" in prose
    for deployment in retained["what_ran"]["deployments"]:
        if not deployment["co_simulable_within_rtl_bounds"]:
            assert deployment["deployment_sha256"][:8] in prose, (
                "a deployment the campaign could not run has to be named in "
                "the claim boundary, not only in the divergence list"
            )
    # What the sequencer dispatches to, and how little of it exists.
    coverage = retained["engine_coverage"]
    assert coverage["distinct_opcodes_this_run_reached"] > 0
    assert (
        coverage["distinct_opcodes_this_run_reached"]
        <= coverage["distinct_opcodes_the_shipped_programs_issue"]
    )


def test_deployment_campaign_refuses_to_overwrite_an_artifact(
    tmp_path: Path,
) -> None:
    from tools import rtl_abi3_deployment_campaign as deployment_campaign

    target = tmp_path / "abi3_deployment_campaign.json"
    target.write_text("{}\n", encoding="utf-8")
    assert deployment_campaign.main(["--output", str(target)]) == 2
    assert target.read_text(encoding="utf-8") == "{}\n"


@pytest.mark.skipif(
    not TOOLS_AVAILABLE, reason="Icarus, vvp and a C++ compiler are required"
)
def test_deployment_campaign_replays_both_simulators(tmp_path: Path) -> None:
    """Both simulators, on the real programs, seeing the same thing.

    The run is expected to be red while a shipped deployment exceeds an RTL
    bound, so what is asserted is not a pass: it is that both engines compiled
    and ran, that they observed the *same* cases -- including the same
    divergence, at the same instruction, with the same values -- and that the
    two Qwen deployments correlated in full.
    """
    from tools import rtl_abi3_deployment_campaign as deployment_campaign

    summary = deployment_campaign.run(tmp_path / "build")
    assert [case["name"] for case in summary["cases"]] == ["iverilog", "verilator"]
    for case in summary["cases"]:
        assert case["compile_returncode"] == 0, case["compile_log"]
        assert case["checks"] and case["checks"] > 0
        assert "/tmp/" not in case["compile_command"]
    assert "Verilator 5.05" in summary["tools"]["verilator"]["version"]
    assert "version 11.0" in summary["tools"]["iverilog"]["version"]
    assert summary["cross_simulator_agreement"][
        "simulators_observed_the_same_cases"
    ]
    assert (
        summary["cases"][0]["checks"] == summary["cases"][1]["checks"]
    ), "the two checkers compared a different number of things"
    assert (
        summary["cases"][0]["signal_flag_cases"]
        == summary["cases"][1]["signal_flag_cases"]
    )
    correlated = set(summary["correlated_cases"])
    for record in _deployment_vectors()["cases"]:
        deployment = next(
            entry
            for entry in _deployment_vectors()["deployments"]
            if entry["key"] == record["deployment"]
        )
        if deployment["co_simulable_within_rtl_bounds"]:
            assert record["name"] in correlated, record["name"]
    assert (summary["status"] == "pass") == (not summary["divergences"])
