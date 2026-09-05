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
    """A golden derived from the run it is compared against proves nothing."""
    text = BUILDER.read_text(encoding="utf-8")
    body = "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("#")
    )
    # The docstring names the RTL it is NOT reading; strip it before looking.
    body = body.split('"""', 2)[-1]
    for forbidden in ("rtl/", "verilator", "iverilog", "Vot_a3", "obj_g1e"):
        assert forbidden not in body, (
            f"the golden builder mentions {forbidden!r}; the golden must be "
            "produced by the reference model alone"
        )


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
            assert record["passes"]["why_not_19"].strip()


def test_the_artifact_status_is_its_own_evidence(artifact: dict) -> None:
    """The summary may not be greener than the records under it."""
    passing = all(
        record["trace"]["equals_golden"]
        and record["injection"]["control_path_is_rtl"]
        and record["passes"]["executed"] == 19
        and record["eos"]["official_eos_raised"]
        and record["eos"]["post_eos_refused"]
        for record in artifact["records"]
    ) and len(artifact["records"]) == 2
    assert artifact["status"] == ("pass" if passing else "fail")
