"""Rung G1b's derivation must measure the layer, never assert it.

Each test here exists because a specific way of getting this rung wrong is
cheap: naming the layer by a program-counter list that one lowering happens to
use, reporting zero mismatches over zero comparisons, defaulting the injected
count to zero when nothing measured it, or -- the one that would matter most --
hard-wiring the red so that a vehicle which really did run the layer could not
turn it green.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools/build_abi3_g1b_layer_closure.py"
VECTORS = ROOT / "testdata/compiler/abi3_shipped_prefix/abi3_shipped_prefix_vectors.json"
BRIDGE = ROOT / "rtl/abi3/ot_a3_engine_issue_bridge.sv"


def _load():
    spec = importlib.util.spec_from_file_location("_g1b_tool", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tool():
    return _load()


@pytest.fixture(scope="module")
def artifact(tool, tmp_path_factory):
    out = tmp_path_factory.mktemp("g1b") / "artifact.json"
    return tool.build(out)


def _observed_cases(vectors_path: Path) -> list[dict[str, int]]:
    """The per-case observation a passing run of that vector set would print."""
    vectors = json.loads(Path(vectors_path).read_text())
    return [
        {
            "index": index,
            "words": int(case["expected"]["result_words"]),
            "fault": int((case.get("first_unsupported") or {}).get("pc", -1)),
        }
        for index, case in enumerate(vectors["cases"])
    ]


def _record(artifact, storage_class):
    return next(
        r for r in artifact["records"] if r["storage_class"] == storage_class
    )


# --------------------------------------------------------------------------
# The layer is named by the graph, not by a program-counter list.
# --------------------------------------------------------------------------
@pytest.mark.parametrize("storage_class", ["rom", "hbm"])
def test_the_layer_is_the_graphs_layer_zero(artifact, storage_class):
    layer = _record(artifact, storage_class)["layer"]
    assert layer["operators_in_layer"] == 19
    kernels = [row["kernel_id"] for row in layer["intermediates"]]
    assert kernels, "no intermediate was attributed to the layer at all"
    assert all(k.startswith("layer.0.") for k in kernels)
    # Every operator the statement names, present exactly once per invocation.
    assert layer["loop"]["operators_per_invocation"] == 19
    assert layer["loop"]["invocations_in_the_program"] == 36
    assert layer["loop"]["issued_instances_in_the_program"] == 19 * 36


def test_the_tool_writes_down_no_program_counter_list(tool, artifact):
    """A PC list is a property of one lowering; the graph is not."""
    import ast

    pcs = {
        row["pc"] for storage_class in ("rom", "hbm")
        for row in _record(artifact, storage_class)["layer"]["intermediates"]
    } | {
        row["pc"] for storage_class in ("rom", "hbm")
        for row in _record(artifact, storage_class)["layer"]["uncovered_operators"]
    }
    tree = ast.parse(TOOL.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            continue
        literals = {
            element.value for element in node.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, int)
        }
        overlap = literals & pcs
        assert len(overlap) < 3, (
            f"a literal collection in the tool holds the layer's program "
            f"counters {sorted(overlap)}; the layer must come from the "
            "certified Kernel IR, not from a list that one lowering happens "
            "to use"
        )
    assert "layer.0." in TOOL.read_text(), (
        "the derivation anchor is the graph's own kernel naming"
    )


def test_the_two_lowerings_are_resolved_independently(artifact):
    rom = {row["pc"]: row["operator_descriptor_id"]
           for row in _record(artifact, "rom")["layer"]["intermediates"]}
    hbm = {row["pc"]: row["operator_descriptor_id"]
           for row in _record(artifact, "hbm")["layer"]["intermediates"]}
    assert set(rom) == set(hbm)
    shared = [pc for pc in rom if rom[pc] == hbm[pc]]
    assert not shared, (
        "the two Qwen lowerings are expected to number the layer's operators "
        f"differently; these program counters agree: {shared}"
    )


# --------------------------------------------------------------------------
# Absence of evidence is a failure, never an unknown and never a zero.
# --------------------------------------------------------------------------
def test_an_absent_campaign_covers_no_operator(tool, tmp_path):
    out = tmp_path / "artifact.json"
    summary = tool.build(out, campaign_path=tmp_path / "nothing.json")
    for record in summary["records"]:
        layer = record["layer"]
        assert layer["operator_count"] == 0
        assert layer["complete"] is False
        assert layer["mismatched_words"] is None, (
            "a mismatch count over zero comparisons is not a zero mismatch "
            "count"
        )
        assert layer["golden_injected_intermediate_count"] is None
        assert record["execution"]["simulated_cycles"] is None
        assert "absent" in record["execution"]["evidence_class"]


def test_a_campaign_bound_to_a_superseded_vector_set_covers_nothing(
    tool, tmp_path
):
    body = json.loads(VECTORS.read_text())
    campaign = {
        "status": "pass",
        "integrated_replay_passed": True,
        "git": {"commit": "0" * 40, "worktree_dirty": False},
        "vector_set": {"sha256": "f" * 64},
        "cases": [{"name": "c", "status": "pass",
                   "run_log": "MEASURE cycles=1 injected_results=0\n"
                              + tool.ENGINE_MARKER + " checks=1\n"}],
    }
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(campaign))
    evidence = tool.integrated_evidence(path)
    assert evidence["usable"] is False
    assert "vector set that is not the one on disk" in evidence["why_unusable"]
    assert body["schema"]  # the real set was read, so the comparison is real


def test_a_run_without_a_measure_line_is_refused(tool, tmp_path):
    campaign = {
        "status": "pass",
        "integrated_replay_passed": True,
        "git": {"commit": "0" * 40, "worktree_dirty": False},
        "vector_set": {"sha256": tool.sha256_file(VECTORS)},
        "cases": [{"name": "c", "status": "pass",
                   "run_log": tool.ENGINE_MARKER + " checks=1\n"}],
    }
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(campaign))
    evidence = tool.integrated_evidence(path)
    assert evidence["usable"] is False
    assert "no MEASURE line" in evidence["why_unusable"]


def test_an_injection_run_cannot_establish_this_rung(tool, tmp_path):
    """G1e's vehicle supplies the engine result; G1b's must compute it."""
    campaign = {
        "status": "pass",
        "integrated_replay_passed": True,
        "git": {"commit": "0" * 40, "worktree_dirty": False},
        "vector_set": {"sha256": tool.sha256_file(VECTORS)},
        "cases": [{"name": "c", "status": "pass",
                   "run_log": "MEASURE cycles=100 injected_results=692\n"
                              + tool.INJECTION_MARKER + " checks=1\n"}],
    }
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(campaign))
    evidence = tool.integrated_evidence(path)
    assert evidence["usable"] is False
    assert "engine array computed" in evidence["why_unusable"]


# --------------------------------------------------------------------------
# The red is a measurement: a vehicle that really ran the layer turns it green.
# --------------------------------------------------------------------------
def _fabricate_complete_vector_set(tool, tmp_path) -> Path:
    """A vector set whose ROM case declares the whole layer executed.

    Nothing about it is real -- it exists to prove that the tool's verdict
    tracks the evidence rather than a constant.  The append cursor and the
    mapped placement are made self-consistent so the replay cannot reject it
    for a reason unrelated to completeness.
    """
    vectors = json.loads(VECTORS.read_text())
    manifest = json.loads(
        (ROOT / "testdata/compiler/abi3_deployment/"
         "abi3_deployment_rtl_vectors.json").read_text()
    )
    images = {
        "descriptor": tool.read_hex(
            ROOT / "testdata/compiler/abi3_deployment/a3_descriptor.hex"),
        "program": tool.read_hex(
            ROOT / "testdata/compiler/abi3_deployment/a3_program.hex"),
        "issue": tool.read_hex(
            ROOT / "testdata/compiler/abi3_deployment/a3_deployment_issue.hex"),
    }
    for case in vectors["cases"]:
        key = case["deployment"]
        if key not in tool.STORAGE_CLASSES.values():
            continue
        kernels = tool.kernel_index(case)
        layer, _ = tool.layer_operators(
            tool.issued_operators(manifest, images, key), kernels
        )
        keep = [op for op in case["supported_prefix"]
                if int(op["pc"]) < min(o["pc"] for o in layer)]
        placement: dict[int, int] = {}
        produced: dict[int, int] = {}
        operations = list(keep)
        # Replay the kept prefix so the produced addresses are right.
        cursor = int(case["bank_mapping"]["output_base"])
        for operation in keep:
            words = 1
            for dim in operation["output_view"]["dims"]:
                words *= int(dim)
            produced[int(operation["pc"])] = cursor
            cursor += words
        # Append the whole layer, one operation per operator.
        by_pc = {op["pc"]: op for op in layer}
        for pc in sorted(by_pc):
            operator = by_pc[pc]
            output = next(
                s for s in operator["slots"] if s["slot"].startswith("output")
            )
            words = 1
            for dim in output["declared_dims"]:
                words *= int(dim)
            words = min(words, 4096)
            operations.append(
                {
                    "kind": operator["mnemonic"].lower().replace(".", "_"),
                    "pc": pc,
                    "descriptor_id": operator["operator_descriptor_id"],
                    "output_view": {"dims": [words]},
                }
            )
            placement[int(output["object_id"])] = cursor
            produced[pc] = cursor
            cursor += words
        # Every operand of the layer resolves to the address that produced it.
        mapped = []
        for pc in sorted(by_pc):
            operator = by_pc[pc]
            for slot in operator["slots"]:
                if slot["slot"].startswith("output"):
                    continue
                object_id = int(slot["object_id"])
                if object_id in placement:
                    mapped.append(
                        {"object_id": object_id, "base_words": placement[object_id]}
                    )
        case["supported_prefix"] = operations
        case["expected"] = dict(case["expected"])
        case["expected"]["result_words"] = (
            cursor - int(case["bank_mapping"]["output_base"])
        )
        mapping = dict(case["bank_mapping"])
        mapping["mapped_placement"] = mapped
        first_layer_pc = min(by_pc)
        # The layer's own producers, for the roles that are not object keyed.
        mapping["rms_input_base"] = produced.get(first_layer_pc, 0)
        case["bank_mapping"] = mapping
    path = tmp_path / "fabricated_vectors.json"
    path.write_text(json.dumps(vectors))
    return path


def test_a_vehicle_that_ran_the_whole_layer_would_turn_the_rung_green(
    tool, tmp_path
):
    vectors_path = _fabricate_complete_vector_set(tool, tmp_path)
    campaign = {
        "status": "pass",
        "integrated_replay_passed": True,
        "evidence_class": "public_open_tool_rtl_simulation",
        "integrated_simulators": ["verilator"],
        "git": {"commit": "0" * 40, "worktree_dirty": False},
        "vector_set": {"sha256": tool.sha256_file(vectors_path)},
        "cases": [{"name": "c", "status": "pass",
                   "observed_cases": _observed_cases(vectors_path),
                   "run_log": "MEASURE cycles=967000000 injected_results=0\n"
                              + tool.ENGINE_MARKER + " checks=1\n"}],
    }
    campaign_path = tmp_path / "campaign.json"
    campaign_path.write_text(json.dumps(campaign))
    summary = tool.build(
        tmp_path / "artifact.json",
        campaign_path=campaign_path,
        vectors_path=vectors_path,
    )
    for record in summary["records"]:
        layer = record["layer"]
        assert layer["operator_count"] == 19, layer["why_not_complete"]
        assert layer["mismatched_words"] == 0
        assert layer["golden_injected_intermediate_count"] == 0
        assert layer["complete"] is True, layer["why_not_complete"]
        assert record["execution"]["simulated_cycles"] == 967_000_000


def test_a_staged_activation_is_counted_as_an_injected_intermediate(
    tool, tmp_path
):
    """The same fabricated run, with one operand no longer RTL-produced."""
    vectors_path = _fabricate_complete_vector_set(tool, tmp_path)
    vectors = json.loads(vectors_path.read_text())
    for case in vectors["cases"]:
        if case["deployment"] in tool.STORAGE_CLASSES.values():
            mapped = case["bank_mapping"]["mapped_placement"]
            assert mapped, "the fabrication must bind mapped operands"
            # Point one activation object at an address nothing produced, in
            # every entry that names it, so the resolution really changes.
            victim = mapped[-1]["object_id"]
            case["bank_mapping"]["mapped_placement"] = [
                dict(entry, base_words=999_999)
                if entry["object_id"] == victim else entry
                for entry in mapped
            ]
    broken = tmp_path / "broken_vectors.json"
    broken.write_text(json.dumps(vectors))
    campaign = {
        "status": "pass",
        "integrated_replay_passed": True,
        "integrated_simulators": ["verilator"],
        "git": {"commit": "0" * 40, "worktree_dirty": False},
        "vector_set": {"sha256": tool.sha256_file(broken)},
        "cases": [{"name": "c", "status": "pass",
                   "observed_cases": _observed_cases(broken),
                   "run_log": "MEASURE cycles=1 injected_results=0\n"
                              + tool.ENGINE_MARKER + " checks=1\n"}],
    }
    campaign_path = tmp_path / "campaign.json"
    campaign_path.write_text(json.dumps(campaign))
    summary = tool.build(
        tmp_path / "artifact.json",
        campaign_path=campaign_path,
        vectors_path=broken,
    )
    for record in summary["records"]:
        layer = record["layer"]
        assert layer["golden_injected_intermediate_count"] >= 1
        assert layer["complete"] is False


# --------------------------------------------------------------------------
# The placement census is counted from the RTL, not written down.
# --------------------------------------------------------------------------
def test_placement_capacity_is_counted_from_the_bridge(tool):
    capacity = tool.placement_capacity()
    text = BRIDGE.read_text()
    roles = capacity["roles"]
    assert roles["matmul_weight"]["slots"] == len(
        set(re.findall(r"cfg_matmul_weight_object_(\d+)\b", text))
    )
    assert roles["mapped_family_operand"]["slots"] == len(
        set(re.findall(r"cfg_map_object_(\d+)\b", text))
    )
    assert capacity["source_sha256"] == tool.sha256_file(BRIDGE)


@pytest.mark.parametrize("storage_class", ["rom", "hbm"])
def test_the_placement_shortfall_is_a_derived_count(artifact, storage_class):
    demand = _record(artifact, storage_class)["layer"]["placement_demand"]
    by_role = {row["role"]: row for row in demand["per_role"]}
    # The layer's seven projection matrices are seven distinct objects, and
    # the bridge declares three weight slots.  If either number moves, this
    # rung's reason must move with it.
    assert by_role["matmul_weight"]["distinct_objects_the_layer_needs"] == 7
    assert by_role["matmul_weight"]["short_by"] == (
        7 - by_role["matmul_weight"]["slots_the_bridge_declares"]
    )
    assert demand["every_role_satisfiable"] is False
    assert not demand["unattributed_operands"], (
        "every operand of the layer must be attributed to a placement role, "
        "or the shortfall is not a complete count"
    )
    reused = demand["output_objects"]["objects_written_more_than_once"]
    assert reused, (
        "the layer reuses buffers; if it did not, an appending output cursor "
        "would be sufficient and this reason would be wrong"
    )


# --------------------------------------------------------------------------
# The rung as shipped.
# --------------------------------------------------------------------------
@pytest.mark.parametrize("storage_class", ["rom", "hbm"])
def test_the_shipped_artifact_states_what_it_measured(storage_class):
    path = ROOT / "results/rtl/abi3_g1b_layer_closure.json"
    if not path.is_file():
        pytest.skip("the rung artifact has not been generated in this tree")
    body = json.loads(path.read_text())
    record = _record(body, storage_class)
    layer = record["layer"]
    assert record["workload_id"] == "TA-QW-EOS-1"
    assert layer["operators_in_layer"] == 19
    # complete may be either; what may never happen is a complete layer with
    # no comparisons behind it, or a zero mismatch count over zero words.
    if layer["complete"]:
        assert layer["operator_count"] == 19
        assert layer["compared_words"]
        assert layer["mismatched_words"] == 0
        assert layer["golden_injected_intermediate_count"] == 0
    else:
        assert layer["why_not_complete"], (
            "an incomplete layer must say why, or the rung is not falsifiable"
        )
    if layer["mismatched_words"] == 0:
        assert layer["compared_words"], (
            "zero mismatches over zero compared words is not evidence"
        )


def test_a_recorded_rerun_changes_no_field_of_the_rung(tool, tmp_path):
    """A run the repository does not hold must not move a gate field."""
    rerun = {
        "status": "pass",
        "integrated_replay_passed": True,
        "integrated_simulators": ["verilator"],
        "git": {"commit": "1" * 40, "worktree_dirty": False},
        "vector_set": {"sha256": tool.sha256_file(VECTORS)},
        "cases": [{"name": "c", "status": "pass",
                   "run_log": "MEASURE cycles=125945126 injected_results=0\n"
                              + tool.ENGINE_MARKER + " checks=189862\n"}],
    }
    path = tmp_path / "rerun.json"
    path.write_text(json.dumps(rerun))
    without = tool.build(tmp_path / "a.json")
    with_rerun = tool.build(tmp_path / "b.json", rerun_path=path)
    assert with_rerun["rerun_not_retained"]["establishes"] == []
    assert with_rerun["rerun_not_retained"]["measure"]["cycles"] == 125_945_126
    for left, right in zip(without["records"], with_rerun["records"]):
        assert left["layer"] == right["layer"]
        assert left["execution"]["simulated_cycles"] == \
            right["execution"]["simulated_cycles"]


@pytest.mark.parametrize("storage_class", ["rom", "hbm"])
def test_the_derived_layer_is_the_layer_the_gate_costed(artifact, storage_class):
    """192,937,984 MACs is the figure G1b's own note states.

    It is not read from the gate file here; it is derived from the weight
    views of the operators this tool identified as the layer.  Agreement is
    the check that the layer being closed is the layer that was costed.
    """
    spec = json.loads(
        (ROOT / "configs/gates/redesign_gates.json").read_text()
    )
    note = next(
        g for g in spec["gates"] if g["id"] == "G1b"
    )["evaluator"]["note"]
    layer = _record(artifact, storage_class)["layer"]
    derived = layer["arithmetic"]["mac_count"]
    assert derived == 192_937_984
    assert f"{derived:,} MACs" in note, (
        "the gate's own cost note and the derived layer disagree; one of them "
        "is describing a different layer"
    )
    assert len(layer["arithmetic"]["per_matmul"]) == 7


def test_the_record_shape_is_the_shape_the_gate_reads(artifact, tmp_path,
                                                      monkeypatch):
    """The gate must be able to both reject and accept this artifact.

    A rung whose field names do not match its evaluator is a rung that can
    never go green whatever the RTL does, which hides the work as surely as a
    gate that cannot fail.  So the real record is fed to the real evaluator
    twice: as it is, and with only the measured fields satisfied.
    """
    spec = importlib.util.spec_from_file_location(
        "_gates", ROOT / "tools/check_redesign_gates.py"
    )
    gates = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gates)
    monkeypatch.setattr(gates, "REPO", tmp_path)
    gate = next(
        g for g in json.loads(
            (ROOT / "configs/gates/redesign_gates.json").read_text()
        )["gates"] if g["id"] == "G1b"
    )
    out = tmp_path / gate["evaluator"]["artifact"]
    out.parent.mkdir(parents=True, exist_ok=True)

    out.write_text(json.dumps(artifact))
    verdict = gates.evaluate(gate)
    assert verdict["status"] == "fail"
    assert "layer.complete" in verdict["why"]

    satisfied = json.loads(json.dumps(artifact))
    for record in satisfied["records"]:
        record["layer"]["complete"] = True
        record["layer"]["mismatched_words"] = 0
        record["layer"]["golden_injected_intermediate_count"] = 0
        record["layer"]["operator_count"] = 19
        record["execution"]["simulator"] = "verilator"
        record["execution"]["simulated_cycles"] = 967_000_000
        record["execution"]["evidence_class"] = (
            "public_open_tool_rtl_simulation"
        )
        record["git"]["worktree_dirty"] = False
    out.write_text(json.dumps(satisfied))
    assert gates.evaluate(gate)["status"] == "pass", (
        "the artifact's field names do not match G1b's evaluator, so the rung "
        "could never go green however the RTL behaved"
    )


def test_a_moved_graph_is_refused_rather_than_read(tool):
    """The layer's definition comes from a certified graph or from nowhere."""
    vectors = json.loads(VECTORS.read_text())
    case = vectors["cases"][0]
    moved = json.loads(json.dumps(case))
    moved["descriptor_derivation"]["kernel_ir_sha256"] = "0" * 64
    with pytest.raises(SystemExit) as moved_error:
        tool.kernel_index(moved)
    assert "the graph has moved under the lowering" in str(moved_error.value)

    absent = json.loads(json.dumps(case))
    absent["descriptor_derivation"]["kernel_ir"] = "build/ir-v3/nothing.json"
    with pytest.raises(SystemExit) as absent_error:
        tool.kernel_index(absent)
    assert "is absent" in str(absent_error.value)

    uncertified = json.loads(json.dumps(case))
    uncertified.pop("descriptor_derivation")
    with pytest.raises(SystemExit) as uncertified_error:
        tool.kernel_index(uncertified)
    assert "does not certify a Kernel IR" in str(uncertified_error.value)


def test_an_append_replay_that_does_not_add_up_is_refused(tool):
    """If the placement replay is wrong, nothing derived from it may ship."""
    vectors = json.loads(VECTORS.read_text())
    case = json.loads(json.dumps(vectors["cases"][0]))
    case["expected"]["result_words"] = int(case["expected"]["result_words"]) + 1
    with pytest.raises(SystemExit) as error:
        tool.executed_span(case, [])
    assert "the placement replay is wrong" in str(error.value)


# --------------------------------------------------------------------------
# What an unkeyed base and an append cursor can and cannot place.
#
# Both predicates were once written as "unkeyed means unplaceable" and
# "distinct outputs must fit in one slot", which called a span blocked whose
# operands the vehicle can address perfectly well.  A rung that is red for a
# reason that is not true is the failure this ladder exists to prevent, so
# each predicate is pinned here in both directions.
# --------------------------------------------------------------------------
def _span(*operators):
    """A minimal issue span: (pc, mnemonic, [(slot, object_id), ...])."""
    return [
        {"pc": pc, "mnemonic": mnemonic,
         "slots": [{"slot": slot, "object_id": object_id}
                   for slot, object_id in slots]}
        for pc, mnemonic, slots in operators
    ]


def test_one_unkeyed_base_places_one_object_and_refuses_two(tool):
    capacity = tool.placement_capacity()
    assert capacity["roles"]["rms_input"]["object_keyed"] is False

    one = tool.placement_demand(
        _span((0, "VECTOR.RMS_NORM",
               [("input_view_0", 40), ("input_view_1", 2),
                ("output_view_0", 90)])),
        capacity,
    )
    by_role = {row["role"]: row for row in one["per_role"]}
    assert by_role["rms_input"]["satisfiable"] is True, (
        "cfg_rms_input_base is one base the harness drives; a span that names "
        "a single object is placeable through it"
    )

    two = tool.placement_demand(
        _span((0, "VECTOR.RMS_NORM",
               [("input_view_0", 40), ("input_view_1", 2),
                ("output_view_0", 90)]),
              (3, "VECTOR.RMS_NORM",
               [("input_view_0", 41), ("input_view_1", 2),
                ("output_view_0", 91)])),
        capacity,
    )
    by_role = {row["role"]: row for row in two["per_role"]}
    assert by_role["rms_input"]["satisfiable"] is False
    assert by_role["rms_input"]["distinct_objects_the_layer_needs"] == 2


def test_the_append_cursor_places_fresh_outputs_and_refuses_a_rewrite(tool):
    capacity = tool.placement_capacity()
    assert capacity["roles"]["appending_output"]["object_keyed"] is False

    fresh = tool.placement_demand(
        _span((0, "TENSOR.MATMUL",
               [("input_view_0", 30), ("input_view_1", 3),
                ("output_view_0", 90)]),
              (3, "TENSOR.MATMUL",
               [("input_view_0", 90), ("input_view_1", 3),
                ("output_view_0", 91)])),
        capacity,
    )
    by_role = {row["role"]: row for row in fresh["per_role"]}
    assert by_role["appending_output"]["distinct_objects_the_layer_needs"] == 2
    assert by_role["appending_output"]["satisfiable"] is True, (
        "an append cursor gives every write a fresh address, so any number of "
        "write-once buffers is placeable through it"
    )
    assert not fresh["output_objects"]["objects_written_more_than_once"]

    rewritten = tool.placement_demand(
        _span((0, "TENSOR.MATMUL",
               [("input_view_0", 30), ("input_view_1", 3),
                ("output_view_0", 90)]),
              (3, "TENSOR.MATMUL",
               [("input_view_0", 90), ("input_view_1", 3),
                ("output_view_0", 90)])),
        capacity,
    )
    by_role = {row["role"]: row for row in rewritten["per_role"]}
    assert by_role["appending_output"]["satisfiable"] is False, (
        "object 90 is written twice; the cursor gives it two addresses and no "
        "reader can name the right one"
    )
    assert rewritten["output_objects"]["objects_written_more_than_once"] == {
        "90": [0, 3]
    }


def test_the_two_selection_families_are_attributed_to_a_placement_role(tool):
    """The bridge names six mapped families; all six must be in the map.

    ``SELECTION.ARGMAX`` and ``SELECTION.TOKEN_APPEND`` were absent, so their
    operands fell through to ``unattributed_operands`` and any span containing
    the head counted no mapped demand at all.
    """
    for mnemonic in ("SELECTION.ARGMAX", "SELECTION.TOKEN_APPEND"):
        for slot in ("input_view_0", "output_view_0"):
            assert tool.OPERAND_ROLE[(mnemonic, slot)] == "mapped_family_operand"

    demand = tool.placement_demand(
        _span((70, "SELECTION.ARGMAX",
               [("input_view_0", 194), ("output_view_0", 200)])),
        tool.placement_capacity(),
    )
    assert not demand["unattributed_operands"]
    by_role = {row["role"]: row for row in demand["per_role"]}
    assert by_role["mapped_family_operand"]["objects"] == [194, 200]
