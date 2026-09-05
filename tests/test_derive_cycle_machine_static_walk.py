"""The audit's static walk, where the program's control flow is data-dependent.

The walk that ``survey_deployment`` uses to count engine issues interprets the
CONTROL stream without running the program.  Some predicates it meets cannot be
read that way -- ``BOOLEAN_OBJECT`` and ``EOS_MEMBER`` read a word in device
memory -- and the walk used to refuse outright whenever it met one.  Refusing
was too blunt, and it cost a real audit: every DeepSeek deployment carries the
KV compressor's group-boundary flag as a ``BOOLEAN_OBJECT``, so the walk refused
on all of them, ``survey_deployment`` fell back to enumerating OPERATOR
descriptors with an *empty* loop map, and the first tensor view carrying a
``LOOP_INDUCTION`` selector could not resolve.  The whole DeepSeek half of the
fairness gate was unevaluable for that reason alone.

Predication in ABI-3 is not a branch.  A predicated instruction that is not a
control transfer has one successor on both arms, ``pc + 1``, and touches
nothing the walk carries.  So the two arms rejoin immediately and their union
is exact with no path enumeration.  Only when the unreadable predicate gates a
control transfer do the arms go different places, and there the walk must still
refuse.

These tests fail in four specific situations:

1.  The union stops being taken and a straight-line data-dependent predicate
    refuses again -- the defect above, returning.
2.  The union starts being taken over a *control transfer*, where it would be
    a guess rather than a union.
3.  The survey stops saying that a unioned issue list is an upper bound, or
    stops naming which operators the bound is loose on.  A survey that looks
    exact when it is not would let a program look more comparable than it is.
4.  The rule changes what the walk reports for a program with no data-dependent
    predicate at all.  The Qwen pair is that program, it passes today, and it
    must not move.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.derive_cycle_machine import (  # noqa: E402
    _PC_REDIRECTING_CONTROL,
    _static_issues,
    _StaticWalkError,
    audit_deployments,
    decode_request_symbols,
    survey_deployment,
)

# The Qwen pair the gate passes on today, and the DeepSeek pair it could not
# evaluate at all.  Both are build products; the tests that need them skip
# rather than fail when the tree has not been built.
QWEN_ROM = REPO / "build/abi3/qwen3-8b-rom-e9"
QWEN_HBM = REPO / "build/abi3/qwen3-8b-hbm-e9"
DEEPSEEK_ROM = REPO / "build/abi3/deepseek-v4-flash-rom-array-32-e9"
DEEPSEEK_HBM = REPO / "build/abi3/deepseek-v4-flash-hbm-e9"

#: The issue count the Qwen walk has reported since it was written.  This is
#: the number the shipped Qwen audits and machine-pair artifacts were derived
#: from; the union rule must not move it by one.
QWEN_ISSUES = 691

needs_qwen = pytest.mark.skipif(
    not (QWEN_ROM / "deployment.json").exists()
    or not (QWEN_HBM / "deployment.json").exists(),
    reason="the Qwen e9 pair is not built in this tree",
)
needs_deepseek = pytest.mark.skipif(
    not (DEEPSEEK_ROM / "deployment.json").exists()
    or not (DEEPSEEK_HBM / "deployment.json").exists(),
    reason="the DeepSeek e9 pair is not built in this tree",
)


# ----------------------------------------------------------------------------
# A synthetic program with exactly the shape that used to refuse.
# ----------------------------------------------------------------------------

def _fixture_with_boolean_predicate(tmp_path, target, *, invert=False):
    """The conformance fixture with one instruction gated by a device word.

    ``target`` picks which instruction gets the predicate as ``(major, sub)``.
    The fixture's TENSOR.MATMUL sits inside a tile loop and its operand views
    carry LOOP_INDUCTION selectors, so predicating it reproduces the DeepSeek
    failure exactly: an unreadable predicate standing between the walk and a
    loop map that the views need.
    """
    from runtime.abi3.builder import DeploymentBuilder
    from runtime.abi3.constants import StorageClass
    from runtime.abi3.descriptors import PredicateKind
    from runtime.abi3.fixture import build_fixture

    original_emit = DeploymentBuilder.emit
    seen: dict[str, int] = {}

    def emit_with_predicate(self, major, sub, **kwargs):
        if (int(major), int(sub)) == (int(target[0]), int(target[1])) \
                and "predicate" not in seen and kwargs.get("predicate_id") is None:
            # One BOOLEAN_OBJECT reading element 0 of the token ring, which
            # every fixture build already declares.  Its truth is a word in
            # device memory: exactly what the walk cannot read.
            seen["predicate"] = self.predicate(
                kind=PredicateKind.BOOLEAN_OBJECT,
                object_id=self.lookup("obj.tokens"),
                element_index=0,
                key="pred.test.device_word",
            )
            kwargs["predicate_id"] = seen["predicate"]
            kwargs["invert_predicate"] = invert
        return original_emit(self, major, sub, **kwargs)

    monkey = pytest.MonkeyPatch()
    monkey.setattr(DeploymentBuilder, "emit", emit_with_predicate)
    try:
        root = build_fixture(storage_class=StorageClass.ROM).write(tmp_path)
    finally:
        monkey.undo()
    assert "predicate" in seen, f"no {target} instruction to predicate"
    return root


@pytest.fixture()
def symbols():
    return decode_request_symbols(1, 4)


def test_a_device_word_over_an_engine_issue_is_unioned_not_refused(tmp_path, symbols):
    """The arms of a predicated engine issue rejoin, so the walk takes both.

    This is the DeepSeek shape in miniature: the predicated operator is inside
    a loop, and its views can only resolve against that loop's induction value.
    The walk must therefore keep walking -- with the loop map intact -- rather
    than hand ``survey_deployment`` an empty one.
    """
    from runtime.abi3.constants import Major, Tensor

    root = _fixture_with_boolean_predicate(tmp_path, (Major.TENSOR, Tensor.MATMUL))
    survey = survey_deployment(
        root, symbols=symbols, params_for=_lanes(8),
    )
    assert survey["static_walk"].startswith("complete over the UNION")
    assert "REFUSED" not in survey["static_walk"]

    detail = survey["static_walk_detail"]
    assert [p["kind"] for p in detail["unevaluable_predicates"]] == ["BOOLEAN_OBJECT"]
    assert detail["conditional_issues"] > 0
    assert detail["conditional_issues"] <= detail["total_issues"]

    # The predicated operator resolved -- which is the whole point.  Under the
    # old refusal it did not: see the companion test below.
    matmul = [r for r in survey["operators"] if r["family"] == "tensor"]
    assert matmul, "the tensor operator vanished from the survey"
    assert all("tile_error" not in r for r in matmul)
    assert all(r["issues"] == r["conditional_issues"] for r in matmul)


def test_the_empty_loop_map_fallback_could_not_have_surveyed_this_program(
        tmp_path, symbols):
    """Why a loop map built without predicate truth is not the fix.

    The obvious alternative -- keep refusing, but give the survey a path that
    builds a loop map anyway -- has no answer to give.  The loop map is not a
    static property of the program: a view resolves against the loop's *current*
    induction value, and the final iteration of a symbol-bounded loop clamps it.
    There is no value to supply that is not a guess, and the empty map the old
    fallback supplied is not even a guess -- it simply fails.  This pins that,
    so nobody re-adopts it.
    """
    from runtime.abi3.constants import Major, Tensor
    from runtime.abi3.deployment import Deployment
    from runtime.abi3.descriptors import ExtendedDescriptorType
    from runtime.sim.memory import MemoryError_, ViewResolver
    from tools.derive_cycle_machine import _describe_operator

    root = _fixture_with_boolean_predicate(tmp_path, (Major.TENSOR, Tensor.MATMUL))
    dep = Deployment.read(str(root))
    views = ViewResolver(dep, None)
    operators = [
        d.descriptor_id for d in dep.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.OPERATOR
    ]
    with pytest.raises(MemoryError_, match="is not active"):
        for operator_id in operators:
            _describe_operator(dep, views, operator_id, {}, symbols, _lanes(8), None)


@pytest.mark.parametrize("invert", [False, True], ids=["plain", "inverted"])
def test_the_union_does_not_depend_on_the_invert_flag(tmp_path, symbols, invert):
    """Unknown-inverted is still unknown: the union of the arms is the same set."""
    from runtime.abi3.constants import Major, Tensor

    root = _fixture_with_boolean_predicate(
        tmp_path, (Major.TENSOR, Tensor.MATMUL), invert=invert,
    )
    survey = survey_deployment(root, symbols=symbols, params_for=_lanes(8))
    assert survey["static_walk_detail"]["conditional_issues"] > 0
    assert survey["static_walk_detail"]["bound"].startswith("UPPER")


def test_a_device_word_over_a_control_transfer_is_still_refused(tmp_path, symbols):
    """The arms of a predicated COMPLETE do not rejoin, so the walk refuses.

    This is the boundary the union rule must not cross.  Taking the union here
    would mean enumerating two paths that go different places, and answering
    without doing so would be a guess.
    """
    from runtime.abi3.constants import Control, Major
    from runtime.abi3.deployment import Deployment

    root = _fixture_with_boolean_predicate(tmp_path, (Major.CONTROL, Control.COMPLETE))
    dep = Deployment.read(str(root))
    with pytest.raises(_StaticWalkError, match="do not\n?\\s*rejoin|rejoin"):
        _static_issues(dep, symbols)

    # And the refusal must reach the caller as a verdict, not as a crash.
    # The fallback enumerates OPERATORs with an empty loop map, which cannot
    # resolve a loop-carried view; that is absence of evidence, so it is
    # reported as a per-operator ``tile_error`` -- which the audit counts as
    # not comparable -- rather than escaping as MemoryError_.
    survey = survey_deployment(root, symbols=symbols, params_for=_lanes(8))
    assert survey["static_walk"].startswith("REFUSED")
    assert "static_walk_detail" not in survey
    errors = [r for r in survey["operators"] if "tile_error" in r]
    assert errors, "a refused walk must say which operators it could not decompose"
    assert any("loop bindings are unknown" in r["tile_error"] for r in errors)
    assert survey["families"]["tensor"]["tile_errors"] >= 1


def test_the_refusal_boundary_is_the_set_of_pc_redirecting_controls():
    """Named, so that widening it is a deliberate edit and not a slip."""
    assert _PC_REDIRECTING_CONTROL == frozenset(
        {"LOOP_SETUP", "LOOP_NEXT", "BRANCH", "COMPLETE", "TRAP"}
    )
    from runtime.abi3.constants import Control

    # Everything else the CONTROL major can encode leaves the walk at pc + 1,
    # which is what makes the union exact rather than an approximation.
    rejoining = {c.name for c in Control} - _PC_REDIRECTING_CONTROL
    assert rejoining == {"NOP", "WAIT", "FENCE", "ASSERT"}


# ----------------------------------------------------------------------------
# The programs the gate actually runs on.
# ----------------------------------------------------------------------------

@needs_qwen
@pytest.mark.parametrize("root", [QWEN_ROM, QWEN_HBM], ids=["rom", "hbm"])
def test_the_qwen_walk_is_untouched_by_the_union_rule(root):
    """The Qwen pair passes the gate today and must not move by one issue.

    The Qwen programs contain no predicated instruction at all, so the union
    rule is unreachable for them -- but "unreachable" is a claim, and this is
    the assertion of it.  ``static_walk`` must still read exactly ``complete``
    and the survey must not grow the detail key, because the shipped Qwen
    artifacts quote both.
    """
    survey = survey_deployment(
        root, symbols=decode_request_symbols(1, 8192), params_for=_lanes(1024),
    )
    assert survey["static_walk"] == "complete"
    assert "static_walk_detail" not in survey
    assert sum(r["issues"] for r in survey["operators"]) == QWEN_ISSUES
    assert all("conditional_issues" not in r for r in survey["operators"])


@needs_qwen
def test_no_qwen_instruction_is_predicated_at_all():
    """The reason the rule cannot reach the Qwen walk, asserted at the source."""
    from runtime.abi3.constants import InstructionFlag
    from runtime.abi3.deployment import Deployment
    from runtime.abi3.records import decode_body, split_program

    for root in (QWEN_ROM, QWEN_HBM):
        dep = Deployment.read(str(root))
        _, body = split_program(dep.program)
        predicated = [
            i for i, ins in enumerate(decode_body(body))
            if ins.flags & InstructionFlag.PREDICATED
        ]
        assert predicated == [], (root.name, predicated)


@needs_deepseek
@pytest.mark.parametrize("root", [DEEPSEEK_ROM, DEEPSEEK_HBM], ids=["rom", "hbm"])
def test_the_deepseek_survey_completes_and_declares_its_upper_bound(root):
    """The survey that used to crash now runs, and says what it is worth."""
    survey = survey_deployment(
        root, symbols=decode_request_symbols(1, 8192), params_for=_lanes(1024),
    )
    assert survey["static_walk"].startswith("complete over the UNION")
    detail = survey["static_walk_detail"]
    assert detail["bound"].startswith("UPPER")
    assert {p["kind"] for p in detail["unevaluable_predicates"]} == {"BOOLEAN_OBJECT"}
    assert 0 < detail["conditional_issues"] < detail["total_issues"]
    # The bound must name where it is loose, not just that it is.
    assert detail["conditional_operators"]
    assert all("tile_error" not in r for r in survey["operators"])


@needs_deepseek
def test_no_deepseek_device_word_gates_a_control_transfer():
    """The precondition that makes the DeepSeek union exact rather than partial.

    Every unreadable predicate in both DeepSeek programs gates a straight-line
    instruction -- a DMA or vector issue, or a WAIT.  If a lowering ever puts
    one on a BRANCH or a LOOP_SETUP the walk will refuse again, and it should:
    this test says so out loud rather than letting it surface as a crash.
    """
    from runtime.abi3.constants import Control, InstructionFlag, Major
    from runtime.abi3.deployment import Deployment
    from runtime.abi3.descriptors import ExtendedDescriptorType, PredicateKind
    from runtime.abi3.records import decode_body, split_program

    unreadable = {PredicateKind.BOOLEAN_OBJECT, PredicateKind.EOS_MEMBER,
                  PredicateKind.ENGINE_STATUS, PredicateKind.ROUTE_VALID}
    for root in (DEEPSEEK_ROM, DEEPSEEK_HBM):
        dep = Deployment.read(str(root))
        _, body = split_program(dep.program)
        for pc, ins in enumerate(decode_body(body)):
            if not ins.flags & InstructionFlag.PREDICATED:
                continue
            kind = PredicateKind(
                dep.table.get(
                    ins.predicate_id, ExtendedDescriptorType.PREDICATE
                ).payload["predicate_kind"]
            )
            if kind not in unreadable or int(ins.major) != int(Major.CONTROL):
                continue
            assert Control(ins.sub).name not in _PC_REDIRECTING_CONTROL, (
                root.name, pc, kind.name, Control(ins.sub).name
            )


@needs_deepseek
def test_the_audit_reaches_a_verdict_on_the_deepseek_pair():
    """A verdict, of either kind, is the deliverable; a crash is not.

    NOT COMPARABLE is a perfectly good outcome and the one this pair reaches.
    What matters is that the audit produces a named, directed asymmetry list
    instead of dying in the view resolver.
    """
    report = audit_deployments(
        DEEPSEEK_ROM, DEEPSEEK_HBM, lanes=1024,
        symbols=decode_request_symbols(1, 8192),
    )
    assert isinstance(report["comparable"], bool)
    assert report["verdict"].startswith(("COMPARABLE", "NOT COMPARABLE"))
    assert report["asymmetries"], "the audit reported no field comparison at all"
    assert report["operators"], "no operator was matched between the two sides"
    # Whatever the verdict, both surveys must own up to the union.
    for side in ("rom", "hbm"):
        assert report[side]["static_walk"].startswith("complete over the UNION")
        assert report[side]["static_walk_detail"]["bound"].startswith("UPPER")


@needs_deepseek
def test_the_union_costs_the_two_sides_the_same(  # noqa: D401
):
    """The union must not be a thumb on the scale for either backend.

    Both DeepSeek programs carry the same construct -- the KV compressor's
    group-boundary flag -- lowered by the two backends from one source.  The
    union therefore adds the same number of conditional issues to each side,
    and cannot make either look better than the other.  If a lowering change
    ever makes the two counts differ, the audit is comparing an upper bound on
    one side against a tighter one on the other, and that has to be visible.
    """
    counts = {}
    for side, root in (("rom", DEEPSEEK_ROM), ("hbm", DEEPSEEK_HBM)):
        survey = survey_deployment(
            root, symbols=decode_request_symbols(1, 8192), params_for=_lanes(1024),
        )
        counts[side] = survey["static_walk_detail"]["conditional_issues"]
    assert counts["rom"] == counts["hbm"], counts


# ----------------------------------------------------------------------------

def _lanes(n):
    from tools.derive_cycle_machine import _fallback_params_for

    return _fallback_params_for(n)
