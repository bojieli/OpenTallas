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
    assert total == vectors["issue_event_count"] == 132
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

    # A leading extent *above* the block is refused at admission rather than
    # resolved.  It is the one shape on which section 12.4's formula and
    # ViewResolver._remaining_rows disagree, and every such disagreement has
    # dim0 > bound_divisor, so refusing that inequality makes the two
    # statements of A13 the same rule.  A refused case resolves no views.
    above = names["a13_extent_above_block"]
    assert above["admitted"] is False
    assert _views_of(above) == []


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
    assert summary["correlation"]["issue_event_count"] == 132
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
