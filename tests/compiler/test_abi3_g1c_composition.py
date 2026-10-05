"""Rung G1c's derivation must measure the loop, never assert it.

G1c's own note requires the loop count and the structural identity of the
invocations to be *mechanically checked*.  A tool that reads 36 out of a
LOOP_CONTROL descriptor and writes it into a gate field has checked nothing:
the program's declaration is what the RTL is supposed to obey, not evidence
that it did.  So every test here is a falsification.  The derivation is fed a
trace a correct control plane would produce and must say the property holds;
it is then fed traces that a *wrong* control plane would produce -- one
invocation short, two operators swapped, one operand offset that stops
advancing, a descriptor that changed between invocations -- and must say it
does not.

The other half of the rung is the handoff, and it is red.  The tests that
matter there are the ones that keep it from going green the wrong way: a
mismatch count over zero comparisons must be ``null`` and never ``0``, and
"no golden value crossed the layer boundary" must be ``null`` when no boundary
was crossed at all.
"""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools/build_abi3_g1c_composition.py"
VECTORS = ROOT / "testdata/compiler/abi3_shipped_prefix/abi3_shipped_prefix_vectors.json"
CHECKPOINT = Path(
    "~/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/"
    "b968826d9c46dd6066d109eabc6255188de91218"
).expanduser()

TRANSACTIONS = 3


def _load():
    spec = importlib.util.spec_from_file_location("_g1c_tool", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tool():
    return _load()


@pytest.fixture(scope="module")
def context(tool):
    """The ROM lowering's program, its layer loop and the model's layer count."""
    vectors = json.loads(VECTORS.read_text())
    key, directory = tool.STORAGE_CLASSES["rom"]
    case = next(c for c in vectors["cases"] if c["deployment"] == key)
    kernels = tool._g1b.kernel_index(case)
    facts = tool.ProgramFacts(ROOT / directory)
    loop = tool.layer_loop(facts, kernels)
    layers = tool.model_layer_count(kernels, None)
    return {"facts": facts, "loop": loop, "layers": layers, "kernels": kernels}


def _synthetic_trace(context) -> list[dict[str, object]]:
    """The issue stream a control plane obeying the program would produce.

    Built from the deployment's own issue sites and its own layer loop: one
    invocation of the body per model layer, per device transaction, with each
    operand offset advancing by a fixed per-invocation stride.  Nothing here
    is a number this test invented about the design; it is the program read
    back as a trace.
    """
    facts, loop, layers = context["facts"], context["loop"], context["layers"]
    # Objects the body writes are its activation buffers: their address does
    # not move with the layer index, which is what makes the boundary an
    # address identity.  Everything else is a per-layer weight and advances.
    written = {
        slot["object_id"]
        for pc in loop["issue_pcs"]
        for slot in facts.issue_sites[pc]["slots"]
        if slot["slot"].startswith("output")
    }

    def stride(object_id: int) -> int:
        return 0 if object_id in written else 4096 * (object_id % 7 + 1)

    issues: list[dict[str, object]] = []
    for _ in range(TRANSACTIONS):
        for invocation in range(layers["layers"]):
            for pc in loop["issue_pcs"]:
                site = facts.issue_sites[pc]
                issues.append(
                    {
                        "family": site["family"],
                        "sub": site["sub"],
                        "descriptor_id": site["operator_descriptor_id"],
                        "pc": pc,
                        "views": [
                            {
                                "slot": index,
                                "descriptor_id": slot["view_descriptor_id"],
                                "extent": slot["declared_dims"][0],
                                "extent_axis": 0,
                                "element_offset": invocation * stride(
                                    slot["object_id"]
                                ),
                                "rank": slot["rank"],
                            }
                            for index, slot in enumerate(site["slots"])
                        ],
                    }
                )
    return issues


def _property(tool, context, issues):
    return tool.loop_property(
        issues, context["loop"], context["layers"], TRANSACTIONS
    )


# --------------------------------------------------------------------------
# The layer loop is found in the program, not written down here.
# --------------------------------------------------------------------------
def test_the_layer_loop_comes_from_the_graph(context):
    loop = context["loop"]
    assert loop["layer_prefix"] == "layer.0."
    assert len(loop["issue_pcs"]) == 19
    assert all(k.startswith("layer.0.") for k in loop["kernel_ids"])
    assert loop["body_start"] < min(loop["issue_pcs"])
    assert loop["back_edge_pc"] >= max(loop["issue_pcs"])


def test_the_two_lowerings_are_resolved_independently(tool):
    vectors = json.loads(VECTORS.read_text())
    seen = {}
    for storage_class, (key, directory) in tool.STORAGE_CLASSES.items():
        case = next(c for c in vectors["cases"] if c["deployment"] == key)
        facts = tool.ProgramFacts(ROOT / directory)
        loop = tool.layer_loop(facts, tool._g1b.kernel_index(case))
        seen[storage_class] = {
            pc: facts.issue_sites[pc]["operator_descriptor_id"]
            for pc in loop["issue_pcs"]
        }
    assert set(seen["rom"]) == set(seen["hbm"])
    shared = [pc for pc in seen["rom"] if seen["rom"][pc] == seen["hbm"][pc]]
    assert not shared, (
        "the two Qwen lowerings number the layer's operators differently; "
        f"these program counters agree: {shared}"
    )


def test_the_tool_writes_down_no_program_counter_list(context):
    """A PC list is a property of one lowering; the graph is not."""
    pcs = set(context["loop"]["issue_pcs"])
    tree = ast.parse(TOOL.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            continue
        literals = {
            element.value for element in node.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, int)
        }
        assert len(literals & pcs) < 3, (
            f"a literal collection in the tool holds {sorted(literals & pcs)}, "
            "which are the layer body's program counters; the loop must come "
            "from the deployment's own LOOP_CONTROL descriptor"
        )


def test_the_layer_count_has_two_independent_sources(tool, context):
    if not CHECKPOINT.is_dir():
        pytest.skip("the Qwen checkpoint snapshot is not present on this host")
    layers = tool.model_layer_count(context["kernels"], CHECKPOINT)
    assert layers["from_kernel_ir"] == layers["from_checkpoint_config"]
    assert layers["sources_agree"] is True
    assert layers["layers"] == layers["from_checkpoint_config"]


def test_a_layer_count_disagreement_refuses(tool, context, tmp_path, monkeypatch):
    fake = tmp_path / "snapshot"
    fake.mkdir()
    (fake / "config.json").write_text(json.dumps({"num_hidden_layers": 35}))
    with pytest.raises(SystemExit) as exc:
        tool.model_layer_count(context["kernels"], fake)
    assert "two numbers for one fact" in str(exc.value)


# --------------------------------------------------------------------------
# The loop property: green on a correct trace, red on every wrong one.
# --------------------------------------------------------------------------
def test_a_correct_trace_establishes_the_loop_property(tool, context):
    record = _property(tool, context, _synthetic_trace(context))
    assert record["invocations_measured"] == TRANSACTIONS * context["layers"]["layers"]
    assert record["invocations_per_transaction"] == [context["layers"]["layers"]]
    assert record["invocation_count_matches_model_layers"] is True
    assert record["structurally_identical"] is True
    assert record["distinct_issue_structures_over_all_invocations"] == 1


def test_one_invocation_short_fails_the_count(tool, context):
    issues = _synthetic_trace(context)
    body = len(context["loop"]["issue_pcs"])
    del issues[:body]  # the first transaction runs 35 layers, not 36
    record = _property(tool, context, issues)
    assert record["invocation_count_matches_model_layers"] is False


def test_a_reordered_invocation_is_not_structurally_identical(tool, context):
    issues = _synthetic_trace(context)
    body = len(context["loop"]["issue_pcs"])
    base = 5 * body
    issues[base + 1], issues[base + 2] = issues[base + 2], issues[base + 1]
    record = _property(tool, context, issues)
    assert record["structurally_identical"] is False


def test_a_changed_descriptor_between_invocations_is_caught(tool, context):
    issues = _synthetic_trace(context)
    body = len(context["loop"]["issue_pcs"])
    issues[7 * body] = dict(issues[7 * body])
    issues[7 * body]["descriptor_id"] = int(issues[7 * body]["descriptor_id"]) + 1
    record = _property(tool, context, issues)
    assert record["structurally_identical"] is False
    assert record["distinct_issue_structures_over_all_invocations"] > 1


def test_an_offset_that_stops_advancing_is_caught(tool, context):
    """A loop whose induction variable stalls issues identical work twice."""
    issues = _synthetic_trace(context)
    body = len(context["loop"]["issue_pcs"])
    stalled = json.loads(json.dumps(issues))
    stalled[9 * body]["views"][0]["element_offset"] = 12345
    record = _property(tool, context, stalled)
    assert record["structurally_identical"] is False
    assert record["per_transaction"][0][
        "element_offsets_are_arithmetic_progressions"
    ] is False


def test_a_changed_view_shape_between_invocations_is_caught(tool, context):
    issues = json.loads(json.dumps(_synthetic_trace(context)))
    body = len(context["loop"]["issue_pcs"])
    issues[3 * body]["views"][0]["extent"] += 1
    record = _property(tool, context, issues)
    assert record["structurally_identical"] is False


# --------------------------------------------------------------------------
# The trace file is bound to the run that produced it.
# --------------------------------------------------------------------------
def _write_trace(path: Path, issues) -> None:
    lines = [
        "FIELDS ISSUE family sub descriptor_id pc queue serial irs_slot",
        "FIELDS VIEW slot descriptor_id extent extent_axis element_offset rank",
    ]
    for issue in issues:
        lines.append(
            "ISSUE {family} {sub} {descriptor_id} {pc} 0 0 0".format(**issue)
        )
        for view in issue["views"]:
            lines.append(
                "VIEW {slot} {descriptor_id} {extent} {extent_axis} "
                "{element_offset} {rank}".format(**view)
            )
    path.write_text("\n".join(lines) + "\n")


def _control_artifact(tool, issues, storage_class="rom", **overrides):
    census: dict[tuple[int, int, int], int] = {}
    for issue in issues:
        key = (issue["family"], issue["sub"], issue["descriptor_id"])
        census[key] = census.get(key, 0) + 1
    key, directory = tool.STORAGE_CLASSES[storage_class]
    facts = tool.ProgramFacts(ROOT / directory)
    record = {
        "storage_class": storage_class,
        "workload_id": "TA-QW-EOS-1",
        "execution": {
            "simulator": "verilator_cpp_executable",
            "simulator_version": "5.050",
            "simulated_cycles": 679220,
            "evidence_class": "public_open_tool_rtl_simulation",
            "vehicle": "rtl/test/a3_shipped_prefix_top.sv",
        },
        "trace": {
            "equals_golden": True,
            "divergence_index": None,
            "compared_issue_count": len(issues),
            "compared_elements": 1,
            "compared_issue_fields": list(tool.CERTIFIED_ISSUE_FIELDS),
            "compared_view_fields": ["slot"],
        },
        "passes": {"executed": TRANSACTIONS},
        "injection": {
            "boundary": "engine_result",
            "control_path_is_rtl": True,
            "measured_at_run_time": {"engine_launches": 0},
        },
        "deployment": {"deployment_sha256": facts.deployment_sha256},
        "issue_census": {
            "rows": [
                {"family": f, "sub": s, "descriptor_id": d, "instances": n}
                for (f, s, d), n in sorted(census.items())
            ]
        },
    }
    for dotted, value in overrides.items():
        node = record
        parts = dotted.split(".")
        for part in parts[:-1]:
            node = node[part]
        node[parts[-1]] = value
    return {
        "schema": tool.G1E_SCHEMA,
        "rung": "G1e",
        "git": {"commit": "0" * 40, "worktree_dirty": False},
        "source_sha256": {
            relative: tool.sha256_file(ROOT / relative)
            for relative in (
                "rtl/abi3/ot_a3_device_top.sv",
                "rtl/test/a3_g1e_control_harness.cpp",
            )
        },
        "records": [record],
    }


def _stage(tool, tmp_path, issues, artifact_body, storage_class="rom"):
    root = tmp_path / "run"
    (root / f"build-{storage_class}").mkdir(parents=True)
    _write_trace(root / f"build-{storage_class}" / "rtl_issue_trace.txt", issues)
    artifact = tmp_path / "control.json"
    artifact.write_text(json.dumps(artifact_body))
    return artifact, root


def test_a_trace_file_that_disagrees_with_the_run_is_refused(tool, context, tmp_path):
    issues = _synthetic_trace(context)
    body = _control_artifact(tool, issues)
    spliced = json.loads(json.dumps(issues))
    spliced[0]["descriptor_id"] = int(spliced[0]["descriptor_id"]) + 1
    artifact, root = _stage(tool, tmp_path, spliced, body)
    evidence = tool.control_run_evidence(artifact, root, "rom")
    assert evidence["usable"] is False
    assert "census" in evidence["why_unusable"]


def test_a_dirty_control_run_is_refused(tool, context, tmp_path):
    issues = _synthetic_trace(context)
    body = _control_artifact(tool, issues)
    body["git"]["worktree_dirty"] = True
    artifact, root = _stage(tool, tmp_path, issues, body)
    evidence = tool.control_run_evidence(artifact, root, "rom")
    assert evidence["usable"] is False
    assert "clean worktree" in evidence["why_unusable"]


def test_a_diverged_trace_is_refused(tool, context, tmp_path):
    issues = _synthetic_trace(context)
    body = _control_artifact(
        tool, issues, **{"trace.equals_golden": False, "trace.divergence_index": 7}
    )
    artifact, root = _stage(tool, tmp_path, issues, body)
    evidence = tool.control_run_evidence(artifact, root, "rom")
    assert evidence["usable"] is False
    assert "not equal to the reference model" in evidence["why_unusable"]


def test_a_run_that_did_not_compare_the_program_counter_is_refused(
    tool, context, tmp_path
):
    issues = _synthetic_trace(context)
    body = _control_artifact(
        tool, issues, **{"trace.compared_issue_fields": ["family", "sub", "descriptor_id"]}
    )
    artifact, root = _stage(tool, tmp_path, issues, body)
    evidence = tool.control_run_evidence(artifact, root, "rom")
    assert evidence["usable"] is False
    assert "'pc'" in evidence["why_unusable"]


def test_an_unusable_control_run_leaves_the_loop_unmeasured(tool, context, tmp_path):
    issues = _synthetic_trace(context)
    body = _control_artifact(tool, issues)
    body["git"]["worktree_dirty"] = True
    artifact, root = _stage(tool, tmp_path, issues, body)
    summary = tool.build(
        tmp_path / "g1c.json", artifact, root, None, None, None
    )
    for record in summary["records"]:
        assert record["loop"]["invocations_measured"] is None
        assert record["loop"]["invocation_count_matches_model_layers"] is False
        assert record["loop"]["structurally_identical"] is False
        assert record["loop"]["why_not_measured"]


# --------------------------------------------------------------------------
# The handoff is red, and cannot go green over an empty set.
# --------------------------------------------------------------------------
def test_the_handoff_reports_null_not_zero_over_zero_comparisons(
    tool, context, tmp_path
):
    issues = _synthetic_trace(context)
    artifact, root = _stage(tool, tmp_path, issues, _control_artifact(tool, issues))
    summary = tool.build(tmp_path / "g1c.json", artifact, root, None, None, None)
    for record in summary["records"]:
        handoff = record["handoff"]
        assert handoff["compared_words_across_the_layer_boundary"] == 0
        assert handoff["mismatched_words"] is None, (
            "zero mismatches over zero comparisons is not a zero mismatch count"
        )
        assert handoff["golden_injected_between_layers"] is None, (
            "'no golden value crossed' over no crossing is a vacuous truth"
        )
        assert handoff["rtl_to_rtl"] is False
        assert handoff["layer_boundary_crossings_observed"] == 0


def _handoff(tool, context, observed):
    vectors = json.loads(VECTORS.read_text())
    key, _ = tool.STORAGE_CLASSES["rom"]
    case = next(c for c in vectors["cases"] if c["deployment"] == key)
    index = vectors["cases"].index(case)
    campaign = {
        "observed_cases": [{"index": index, **observed}],
        "expected_cases": [],
        "operator_admission": {},
    }
    return tool.handoff_evidence(
        campaign, context["facts"], context["loop"], case, index
    )


def test_a_run_past_the_back_edge_without_a_counter_is_undetermined(tool, context):
    """Not derivable is written null, never assumed to be zero or to be fine."""
    record = _handoff(
        tool,
        context,
        {"fetched": len(context["facts"].instructions), "fault": -1, "trap": 0},
    )
    assert record["completed_layer_invocations"] is None
    assert record["layer_boundary_crossings_observed"] is None
    assert record["mismatched_words"] is None
    assert record["rtl_to_rtl"] is False


def test_the_handoff_red_is_not_hard_wired(tool, context):
    """A run that really did cross the boundary and match turns it green."""
    record = _handoff(
        tool,
        context,
        {
            "fetched": len(context["facts"].instructions),
            "fault": -1,
            "trap": 0,
            "back_edge_retirals": 36,
            "boundary_compared_words": 4096,
            "boundary_mismatched_words": 0,
            "boundary_injected_operands": 0,
        },
    )
    assert record["completed_layer_invocations"] == 36
    assert record["layer_boundary_crossings_observed"] == 35
    assert record["compared_words_across_the_layer_boundary"] == 4096
    assert record["mismatched_words"] == 0
    assert record["golden_injected_between_layers"] is False
    assert record["rtl_to_rtl"] is True


def test_one_mismatched_word_across_the_boundary_is_still_red(tool, context):
    record = _handoff(
        tool,
        context,
        {
            "fetched": len(context["facts"].instructions),
            "fault": -1,
            "trap": 0,
            "back_edge_retirals": 36,
            "boundary_compared_words": 4096,
            "boundary_mismatched_words": 1,
            "boundary_injected_operands": 0,
        },
    )
    assert record["mismatched_words"] == 1
    assert record["rtl_to_rtl"] is False


def test_a_golden_value_across_the_boundary_is_still_red(tool, context):
    record = _handoff(
        tool,
        context,
        {
            "fetched": len(context["facts"].instructions),
            "fault": -1,
            "trap": 0,
            "back_edge_retirals": 36,
            "boundary_compared_words": 4096,
            "boundary_mismatched_words": 0,
            "boundary_injected_operands": 3,
        },
    )
    assert record["golden_injected_between_layers"] is True
    assert record["rtl_to_rtl"] is False


def test_a_run_that_stopped_before_the_back_edge_completed_none(tool, context):
    record = _handoff(
        tool,
        context,
        {"fetched": context["loop"]["back_edge_pc"], "fault": 32, "trap": 4},
    )
    assert record["completed_layer_invocations"] == 0
    assert record["layer_boundary_crossings_observed"] == 0
    assert record["compared_words_across_the_layer_boundary"] == 0
    assert record["mismatched_words"] is None


def test_the_boundary_object_is_read_from_the_descriptors(tool, context, tmp_path):
    issues = _synthetic_trace(context)
    artifact, root = _stage(tool, tmp_path, issues, _control_artifact(tool, issues))
    summary = tool.build(tmp_path / "g1c.json", artifact, root, None, None, None)
    for record in summary["records"]:
        boundary = record["handoff"]["boundary_object_the_program_declares"]
        assert boundary["objects_in_common"], (
            "the layer's last operator must write an object its first "
            "operator reads, or the loop is not a residual trunk at all"
        )
        assert boundary["derived_not_measured"] is True


# --------------------------------------------------------------------------
# Address identity across the boundary is measured, and is not the handoff.
# --------------------------------------------------------------------------
def test_address_identity_holds_on_a_correct_trace(tool, context):
    issues = _synthetic_trace(context)
    record = tool.boundary_address_identity(
        issues, context["loop"], context["facts"], TRANSACTIONS
    )
    assert record["shared_objects"], (
        "the layer's last operator must write an object its first reads"
    )
    assert record["boundaries_checked"] == TRANSACTIONS * (
        context["layers"]["layers"] - 1
    )
    assert record["holds"] is True


def test_a_consumer_that_reads_the_wrong_address_is_caught(tool, context):
    issues = json.loads(json.dumps(_synthetic_trace(context)))
    body = len(context["loop"]["issue_pcs"])
    # invocation 1's first operator reads somewhere else entirely
    issues[body]["views"][0]["element_offset"] += 64
    record = tool.boundary_address_identity(
        issues, context["loop"], context["facts"], TRANSACTIONS
    )
    assert record["holds"] is False
    assert record["disagreements"]


def test_address_identity_cannot_stand_in_for_the_handoff(tool, context, tmp_path):
    issues = _synthetic_trace(context)
    artifact, root = _stage(tool, tmp_path, issues, _control_artifact(tool, issues))
    summary = tool.build(tmp_path / "g1c.json", artifact, root, None, None, None)
    # Only the ROM store has a trace staged here, so it is the only record the
    # address identity can be measured in; the other says why it could not be.
    for record in summary["records"]:
        handoff = record["handoff"]
        identity = handoff["address_identity_across_the_layer_boundary"]
        if record["storage_class"] != "rom":
            assert identity["holds"] is False
            assert identity["why_not_measured"]
            continue
        assert identity["holds"] is True
        assert handoff["rtl_to_rtl"] is False, (
            "address identity under injected engine results is not an "
            "RTL-to-RTL data handoff and must not turn the field green"
        )
        assert handoff["mismatched_words"] is None


def test_a_control_run_whose_sources_moved_is_refused(tool, context, tmp_path):
    issues = _synthetic_trace(context)
    body = _control_artifact(tool, issues)
    body["source_sha256"] = {"rtl/abi3/ot_a3_device_top.sv": "f" * 64}
    artifact, root = _stage(tool, tmp_path, issues, body)
    evidence = tool.control_run_evidence(artifact, root, "rom")
    assert evidence["usable"] is False
    assert "have drifted since it ran" in evidence["why_unusable"]


def test_a_control_run_binding_nothing_is_refused(tool, context, tmp_path):
    issues = _synthetic_trace(context)
    body = _control_artifact(tool, issues)
    body.pop("source_sha256")
    artifact, root = _stage(tool, tmp_path, issues, body)
    evidence = tool.control_run_evidence(artifact, root, "rom")
    assert evidence["usable"] is False
    assert "binds no source digests" in evidence["why_unusable"]


def test_the_handoff_records_whether_its_evidence_is_source_current(
    tool, context, tmp_path
):
    issues = _synthetic_trace(context)
    artifact, root = _stage(tool, tmp_path, issues, _control_artifact(tool, issues))
    summary = tool.build(tmp_path / "g1c.json", artifact, root, None, None, None)
    for record in summary["records"]:
        currency = record["handoff"]["evidence_currency"]
        assert currency["retained_campaign_is_usable"] in (True, False)
        if currency["retained_campaign_is_usable"] is False:
            assert currency["why_not"], (
                "an unusable campaign must say why, or the red has no reason"
            )
        assert currency["fields_the_handoff_reads"]


# --------------------------------------------------------------------------
# The cost of the half that has not run is derived, not quoted.
# --------------------------------------------------------------------------
def test_the_layer_arithmetic_comes_from_the_weight_views(tool, context):
    arithmetic = tool.layer_arithmetic(context["facts"], context["loop"])
    assert arithmetic["mac_count"] == sum(
        row["mac_count"] for row in arithmetic["per_matmul"]
    )
    assert arithmetic["per_matmul"]
    literals = {
        node.value
        for node in ast.walk(ast.parse(TOOL.read_text()))
        if isinstance(node, ast.Constant) and isinstance(node.value, int)
    }
    assert arithmetic["mac_count"] not in literals, (
        "the layer's MAC count is written into the tool as a literal; it must "
        "come from each MATMUL's own resolved weight view"
    )


def test_the_rate_is_a_quotient_of_the_runs_own_two_numbers(tool):
    body = json.loads(
        (ROOT / "results/rtl/abi3_shipped_prefix_campaign.json").read_text()
    )
    rate = tool.integrated_rate(body)
    if not rate.get("measured"):
        pytest.skip(rate.get("why_not"))
    assert rate["macs_per_second"] == pytest.approx(
        rate["mac_count"] / rate["simulation_wall_seconds"], rel=1e-6
    )
    assert rate["caveat"]


def test_a_campaign_with_no_wall_time_measures_no_rate(tool):
    rate = tool.integrated_rate({"matmul_mac_count": 1, "cases": []})
    assert rate["measured"] is False
    assert rate["why_not"]


def test_the_loop_is_counted_a_second_time_from_the_sequencers_own_counter(
    tool, context
):
    """The issue trace and the loop-iteration counter must agree."""
    issues = _synthetic_trace(context)
    facts, loop, layers = context["facts"], context["loop"], context["layers"]
    inner = [
        row for row in facts.loops
        if loop["body_start"] <= row["setup_pc"] <= loop["body_end"]
        and row["setup_pc"] != loop["setup_pc"]
    ]
    outside = [
        row for row in facts.loops
        if not (loop["body_start"] <= row["setup_pc"] <= loop["body_end"])
        and row["setup_pc"] != loop["setup_pc"]
    ]
    predicted = (
        layers["layers"] + layers["layers"] * len(inner) + len(outside)
    )
    per_pass = [
        {"index": index, "entrypoint_id": int(index > 0),
         "loop_iterations": predicted}
        for index in range(TRANSACTIONS)
    ]
    record = tool.loop_property(
        issues, loop, layers, TRANSACTIONS, per_pass, facts
    )
    check = record["loop_iteration_cross_check"]
    assert check["checked"] is True
    assert check["agrees"] is True
    assert check["predicted_loop_iterations_per_transaction"] == predicted

    per_pass[1]["loop_iterations"] = predicted + 1
    disagreeing = tool.loop_property(
        issues, loop, layers, TRANSACTIONS, per_pass, facts
    )
    assert disagreeing["loop_iteration_cross_check"]["agrees"] is False, (
        "a sequencer counter that disagrees with the program's own loop "
        "structure must be reported, not absorbed"
    )
