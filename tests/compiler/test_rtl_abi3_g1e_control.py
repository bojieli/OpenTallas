"""Rung G1e's artifact, and the two properties that make it evidence.

The rung's claim is that the governed workload's whole CONTROL path ran in
RTL with only the engine results supplied.  Two things decide whether that is
evidence or theatre, and both are tested here rather than read out of the
artifact's prose:

* the injected values reach only the engine result boundary -- checked by
  re-running the campaign's own audit against the RTL source, and by requiring
  that audit to REFUSE a source with one extra edge spliced in;
* the golden trace is produced independently of the RTL -- checked by
  requiring the builder to contain no RTL path and no RTL artifact read.

Everything else here is the usual source binding: an artifact that no longer
matches the files it names is not current, and a field the run did not measure
must be reported with the value it has and the reason it has it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from runtime.abi3.constants import Major, Selection

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "results/rtl/abi3_g1e_control_end_to_end.json"
TOP = ROOT / "rtl/test/a3_shipped_prefix_top.sv"
BUILDER = ROOT / "tools/build_abi3_g1e_control_vectors.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def artifact() -> dict:
    if not ARTIFACT.is_file():
        pytest.fail(
            f"{ARTIFACT.relative_to(ROOT)} is absent; absence of evidence is a "
            "failing rung, not an unevaluable one"
        )
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_artifact_is_bound_to_the_sources_it_names(artifact: dict) -> None:
    drifted = [
        path
        for path, digest in artifact["source_sha256"].items()
        if not (ROOT / path).is_file() or sha256(ROOT / path) != digest
    ]
    assert drifted == [], f"the artifact's bound sources have moved: {drifted}"


def test_every_storage_class_the_rung_requires_has_a_record(artifact: dict) -> None:
    classes = sorted(record["storage_class"] for record in artifact["records"])
    assert classes == ["hbm", "rom"]


def test_the_provenance_spine_is_present_on_every_record(artifact: dict) -> None:
    for record in artifact["records"]:
        execution = record["execution"]
        assert execution["simulator"], record["storage_class"]
        assert isinstance(execution["simulated_cycles"], int)
        assert execution["simulated_cycles"] > 0
        assert "rtl" in execution["evidence_class"].lower()
        assert record["git"]["worktree_dirty"] is False
        assert record["workload_id"] == "TA-QW-EOS-1"


def test_the_trace_comparison_actually_compared_something(artifact: dict) -> None:
    for record in artifact["records"]:
        trace = record["trace"]
        assert trace["compared_issue_count"] > 0
        assert trace["compared_elements"] > 0
        # A trace that "equals golden" while comparing nothing is the defect
        # this check exists to refuse.
        if trace["equals_golden"]:
            assert trace["divergence_index"] is None
            assert trace["compared_elements"] >= trace["compared_issue_count"]


def test_no_engine_ran_under_injection(artifact: dict) -> None:
    for record in artifact["records"]:
        measured = record["injection"]["measured_at_run_time"]
        assert measured["engine_launches"] == 0
        assert measured["engine_work"] == 0
        assert measured["weight_halfword_reads"] == 0
        assert measured["results_consumed"] == record["trace"]["compared_issue_count"]


def test_the_injection_audit_is_clean_against_the_rtl_as_it_stands_now() -> None:
    from tools.rtl_abi3_g1e_control_campaign import audit_injection

    audit = audit_injection(TOP.read_text(encoding="utf-8"))
    assert audit["outside_allowed_sinks"] == []
    assert audit["instance_ports_outside_allowed"] == []
    assert audit["clean"] is True
    ports = {entry["port"] for entry in audit["instance_ports_reached"]}
    assert {"eng_issue_ready", "eng_issue_fault", "eng_issue_trap_class"} <= ports


def test_the_injection_audit_refuses_an_extra_edge() -> None:
    """An audit that cannot fail is not an audit."""
    from tools.rtl_abi3_g1e_control_campaign import audit_injection, audit_self_test

    source = TOP.read_text(encoding="utf-8")
    self_test = audit_self_test(source)
    assert self_test["ran"] is True
    assert self_test["refused_the_spliced_edge"] is True

    # And a second, independent counter-example: an injected value driving a
    # module-instance port that is not the engine completion.
    spliced = source.replace(
        "        .start(start),", "        .start(start && inj_result_valid),", 1
    )
    assert spliced != source
    assert audit_injection(spliced)["clean"] is False


def test_the_golden_builder_reads_no_rtl() -> None:
    """A golden derived from the run it is compared against proves nothing.

    Checked over the builder's EXECUTABLE code, not its prose: docstrings cite
    the RTL they are talking about, and a citation is not a read.  What must
    not be there is a string the code could open, a simulator it could run, or
    a subprocess it could run one with.
    """
    import ast

    tree = ast.parse(BUILDER.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.add(id(body[0].value))
    literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]
    for text in literals:
        lowered = text.lower()
        for forbidden in ("rtl/", ".sv", "verilator", "iverilog", "vot_a3", "obj_"):
            assert forbidden not in lowered, (
                f"the golden builder's code carries the literal {text!r}; the "
                "golden must be produced by the reference model alone"
            )
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "subprocess" not in imported
    assert "rtl" not in imported


def test_the_golden_reproduces_the_oracle(artifact: dict) -> None:
    oracle = json.loads(
        (ROOT / "results/abi3/qwen3_reference_oracle_eos.json").read_text(
            encoding="utf-8"
        )
    )
    gold = [int(t) for t in oracle["results"]["TA-QW-EOS-1"]["generated_token_ids"]]
    for record in artifact["records"]:
        assert record["oracle"]["generated_token_ids"] == gold
        assert record["eos"]["model_generated_token_ids"] == gold


def test_a_field_the_run_did_not_measure_carries_its_reason(artifact: dict) -> None:
    for record in artifact["records"]:
        eos = record["eos"]
        if not (eos["official_eos_raised"] and eos["post_eos_refused"]):
            assert eos["why_not_measured_in_rtl"].strip()
            assert eos["what_would_measure_them"]
        if record["passes"]["executed"] != record["passes"]["gate_requires"]:
            assert record["passes"]["why_not_the_gate_number"].strip()


def test_a_red_pass_count_carries_the_experiment_that_bounds_it(
    artifact: dict,
) -> None:
    """The reason a red field is red must be measured, not written down.

    A rung is allowed to fail.  What it is not allowed to do is explain the
    failure in prose nobody can check, which is what this field used to be.
    The study has to have executed real submission sequences, the gate's own
    number has to have come out of the gate, and the number the record
    reports has to be the largest one any sequence that reproduces the
    oracle's gold achieved -- not a smaller one that happens to be true.
    """
    for record in artifact["records"]:
        passes = record["passes"]
        study = passes["decomposition_study"]
        assert study["gate_requires_passes"] == passes["gate_requires"]
        cases = study["cases"]
        assert len(cases) >= 2, "one submission sequence is not a comparison"
        correct = [case for case in cases if case["reproduces_gold"]]
        wrong = [case for case in cases if not case["reproduces_gold"]]
        assert correct, "no sequence reproduced the gold; the study proved nothing"
        assert wrong, (
            "every sequence reproduced the gold, so the study cannot "
            "distinguish a design limit from an untried alternative"
        )
        measured = study["measured"]
        assert measured["maximum_device_transactions_over_correct_decompositions"] == max(
            case["device_transactions"] for case in correct
        )
        assert passes["executed"] <= measured[
            "maximum_device_transactions_over_correct_decompositions"
        ]
        assert measured["gate_number_is_reachable"] == (
            measured["maximum_device_transactions_over_correct_decompositions"]
            == passes["gate_requires"]
        )
        # Every sequence that failed must say what it produced instead: a
        # case recorded only as "wrong" is an assertion again.
        for case in wrong:
            assert case["generated_token_ids"] != study["oracle"][
                "generated_token_ids"
            ]
            assert case["transactions"], "a failed sequence with no record of it"


def test_both_eos_fields_follow_the_run_rather_than_a_constant(
    artifact: dict,
) -> None:
    """Neither EOS field may be a literal, and the tool must prove it.

    G1a's own tool decided a gate field by grepping source text, so wiring a
    port would have turned it green with nothing having run.  These two
    fields are conjunctions of run observations, and the campaign carries a
    self test that moves each of them in both directions; if that self test
    were removed or nailed down, this fails.
    """
    for record in artifact["records"]:
        eos = record["eos"]
        decided = eos["how_both_fields_are_decided"]
        inputs = decided["measured_inputs"]
        assert eos["official_eos_raised"] == (
            inputs["selected_eos_reason"] == inputs["official_eos_encoding"]
            and inputs["real_engine_launches"] > 0
        )
        assert eos["post_eos_refused"] == (
            bool(inputs["post_eos_probe_ran"])
            and (
                bool(inputs["post_eos_probe_trapped"])
                or not bool(inputs["post_eos_probe_admitted"])
            )
        )
        self_test = decided["self_test"]
        assert self_test["ran"] and self_test["passed"]
        assert self_test["official_eos_raised"]["true_when_a_real_engine_raised_it"]
        assert not self_test["official_eos_raised"]["false_because_no_engine_ran"]
        assert self_test["post_eos_refused"]["true_when_the_design_trapped_it"]
        assert not self_test["post_eos_refused"][
            "false_when_the_design_completed_the_pass"
        ]


def test_the_control_plane_reached_the_instruction_that_ends_a_generation(
    artifact: dict,
) -> None:
    """A false official_eos_raised must say which half of it was false.

    "The engine did not run" and "the instruction was never issued" are very
    different failures, and the census distinguishes them.  The count comes
    off the RTL's own issue trace, so it cannot be satisfied by the program
    merely containing the instruction.
    """
    for record in artifact["records"]:
        reach = record["eos"]["control_plane_reached_the_eos_instruction"]
        census = {
            (row["family"], row["sub"]): row["instances"]
            for row in record["issue_census"]["rows"]
        }
        family = int(Major.SELECTION)
        assert reach["selection_token_append_issues"] == census.get(
            (family, int(Selection.TOKEN_APPEND)), 0
        )
        assert reach["selection_argmax_issues"] == census.get(
            (family, int(Selection.ARGMAX)), 0
        )
        assert reach["passes"] == record["passes"]["executed"]


def test_the_artifact_status_is_its_own_evidence(artifact: dict) -> None:
    """The summary may not be greener than the records under it."""
    passing = all(
        record["trace"]["equals_golden"]
        and record["injection"]["control_path_is_rtl"]
        and record["passes"]["executed"] == record["passes"]["gate_requires"]
        and record["eos"]["official_eos_raised"]
        and record["eos"]["post_eos_refused"]
        for record in artifact["records"]
    ) and len(artifact["records"]) == 2
    assert artifact["status"] == ("pass" if passing else "fail")
