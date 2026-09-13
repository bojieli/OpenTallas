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


def _words(dims) -> int:
    total = 1
    for dim in dims:
        total *= int(dim)
    return total


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
    tracks the evidence rather than a constant.  The object placement is made
    self-consistent so the replay cannot reject it for a reason unrelated to
    completeness.
    """
    vectors = json.loads(VECTORS.read_text())
    _span_of: dict[int, int] = {}
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
        # Every object is allocated fresh, so the fabricated span is
        # self-consistent and cannot be rejected for a reason unrelated to
        # completeness.
        placement: dict[int, int] = {}
        operations = list(keep)
        base = int(case["bank_mapping"]["result_region_base"])
        cursor = base
        written = 0
        for operation in keep:
            words = _words(operation["output_view"]["dims"])
            object_id = int(operation["output_view"]["object_id"])
            if object_id not in placement:
                placement[object_id] = cursor
                _span_of[object_id] = words
                cursor += words
            written += words
        # Append the whole layer, one operation per operator, each result at
        # its OWN object's base.  A buffer the layer rewrites gets one base
        # and is written twice there, which is what the vehicle now does.
        by_pc = {op["pc"]: op for op in layer}
        for pc in sorted(by_pc):
            operator = by_pc[pc]
            output = next(
                s for s in operator["slots"] if s["slot"].startswith("output")
            )
            object_id = int(output["object_id"])
            words = min(_words(output["declared_dims"]), 4096)
            if object_id in placement:
                # A rewrite: same base, and this compact staging gives an
                # object one span, so the size must match.
                words = _span_of[object_id]
            else:
                placement[object_id] = cursor
                _span_of[object_id] = words
                cursor += words
            operations.append(
                {
                    "kind": operator["mnemonic"].lower().replace(".", "_"),
                    "pc": pc,
                    "descriptor_id": operator["operator_descriptor_id"],
                    "output_view": {"dims": [words], "object_id": object_id},
                }
            )
            written += words
        result_span = cursor - base
        # Every operand the layer reads must be placed too, or the replay
        # refuses the span outright.  They are not results, so they are placed
        # outside the region the results allocate.
        for pc in sorted(by_pc):
            for slot in by_pc[pc]["slots"]:
                object_id = int(slot["object_id"])
                if object_id not in placement:
                    placement[object_id] = cursor
                    _span_of[object_id] = 1
                    cursor += 1
        case["supported_prefix"] = operations
        case["expected"] = dict(case["expected"])
        case["expected"]["result_words"] = written
        mapping = dict(case["bank_mapping"])
        mapping["object_placement"] = [
            {"object_id": object_id, "base_words": placement[object_id]}
            for object_id in sorted(placement)
        ]
        mapping["result_region_span"] = result_span
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
            # Drop one activation object out of the placement table
            # entirely, so the operator that reads it has no producer of
            # record and the operand stops being an RTL-to-RTL handoff.
            layer_pcs = {
                int(op["pc"]) for op in case["supported_prefix"]
                if op["kind"] not in ("dma_gather", "tensor_embed_lookup")
            }
            victim = max(
                int(op["output_view"]["object_id"])
                for op in case["supported_prefix"]
                if int(op["pc"]) in layer_pcs
            )
            case["supported_prefix"] = [
                op for op in case["supported_prefix"]
                if int(op["output_view"]["object_id"]) != victim
            ]
            case["expected"] = dict(case["expected"])
            case["expected"]["result_words"] = sum(
                _words(op["output_view"]["dims"])
                for op in case["supported_prefix"]
            )
            # The region shrinks by exactly the object that is gone.
            seen: set[int] = set()
            span = 0
            for op in case["supported_prefix"]:
                object_id = int(op["output_view"]["object_id"])
                if object_id in seen:
                    continue
                seen.add(object_id)
                span += _words(op["output_view"]["dims"])
            case["bank_mapping"] = dict(case["bank_mapping"])
            case["bank_mapping"]["result_region_span"] = span
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
# The placement census is MEASURED, and a port list cannot move it.
#
# The failure this replaces is the one section 11.7 already records once: a
# gate field decided by grepping the verification top's source text for a port
# name, so that wiring the port would have turned the field green with nothing
# having run.  The bridge's placement table is exactly that shape of
# temptation -- widening it is a one-line edit -- so the capacity the demand
# is compared against is the depth a passing RUN resolved, and the port count
# is recorded beside it as a declaration that is credited to nothing.
# --------------------------------------------------------------------------
def _campaign(vectors_path, tool, usable=True):
    return {
        "usable": usable,
        "observed_cases": _observed_cases(vectors_path),
    }


def test_a_second_campaign_measures_the_same_table_and_is_checked(tool):
    """Another passing run of the SAME bridge deepens the measurement.

    The integrated vehicle can only bind the objects its own program span
    names, so the depth it reaches is a fact about that span.  The bridge is
    the same module wherever it is instantiated, so a passing run elsewhere
    measures the same table -- but only if it really is the same module, only
    if it passed, and only up to the table it actually bound.  Each of those
    is checked here in both directions.
    """

    vectors = json.loads(VECTORS.read_text())
    shallow = {"usable": True, "observed_cases": _observed_cases(VECTORS)}
    baseline = tool.placement_capacity(vectors, shallow, others=[])

    deeper = {
        "artifact": "results/rtl/a3_operator_admission_campaign.json",
        "measured_simultaneous_objects": baseline[
            "measured_simultaneous_objects"
        ] + 5,
        "usable": True,
        "why_unusable": None,
    }
    widened = tool.placement_capacity(vectors, shallow, others=[deeper])
    assert widened["measured_simultaneous_objects"] == (
        baseline["measured_simultaneous_objects"] + 5
    )
    assert widened["measured_from"] == deeper["artifact"]
    for role in widened["roles"].values():
        if role["object_keyed"]:
            assert role["slots"] == widened["measured_simultaneous_objects"]

    # The same number, on an artifact that is not usable, must move nothing.
    refused = dict(deeper, usable=False, why_unusable="its status is 'fail'")
    unchanged = tool.placement_capacity(vectors, shallow, others=[refused])
    assert unchanged["measured_simultaneous_objects"] == (
        baseline["measured_simultaneous_objects"]
    )
    assert unchanged["measured_from"] == tool.INTEGRATED_CAMPAIGN
    assert any(
        row["why_unusable"] for row in unchanged["measurements"]
        if not row["usable"]
    ), "an unusable measurement must say why rather than be silent"


def test_an_admission_artifact_is_refused_unless_it_names_this_bridge(tool, tmp_path):
    """The falsification: a fabricated deep measurement must not be credited."""

    fabricated = tmp_path / "fabricated.json"
    fabricated.write_text(json.dumps({
        "status": "pass",
        "storage_class": "rom",
        "placement": {
            "measured_simultaneous_objects": 999,
            "table_entries_bound": 999,
            "bridge_sha256": "0" * 64,
            "vehicle": "rtl/test/tb_a3_operator_admission.sv",
            "vehicle_sha256": "0" * 64,
        },
    }))
    original = tool.ADMISSION_CAMPAIGNS
    try:
        tool.ADMISSION_CAMPAIGNS = (
            str(fabricated.relative_to(tool.ROOT))
            if fabricated.is_relative_to(tool.ROOT) else str(fabricated),
        )
        rows = tool.admission_measurements()
    finally:
        tool.ADMISSION_CAMPAIGNS = original
    assert len(rows) == 1
    assert rows[0]["usable"] is False
    assert rows[0]["measured_simultaneous_objects"] == 0
    assert "different revision of the bridge" in rows[0]["why_unusable"]


def test_the_declared_port_count_is_recorded_but_never_credited(tool):
    vectors = json.loads(VECTORS.read_text())
    text = BRIDGE.read_text()
    declared = len(set(re.findall(r"cfg_place_object_(\d+)\b", text)))
    assert declared > 0, "the bridge declares no placement table at all"

    measured = tool.placement_capacity(
        vectors, {"usable": True, "observed_cases": _observed_cases(VECTORS)}
    )
    assert measured["declared_entries"] == declared
    assert measured["source_sha256"] == tool.sha256_file(BRIDGE)
    # The number every OBJECT-KEYED role is judged against is the measured
    # one, and on the shipped vector set it is strictly smaller than the
    # declaration.  The three staged regions do not draw from the table at
    # all, so widening it does not widen them and they stay at one base each.
    assert measured["measured_simultaneous_objects"] < declared
    keyed = [r for r in measured["roles"].values() if r["object_keyed"]]
    unkeyed = [r for r in measured["roles"].values() if not r["object_keyed"]]
    assert keyed and unkeyed
    for role in keyed:
        assert role["slots"] == measured["measured_simultaneous_objects"]
    for role in unkeyed:
        assert role["slots"] == 1


def test_with_no_usable_campaign_the_measured_capacity_is_zero(tool):
    vectors = json.loads(VECTORS.read_text())
    # ``others=[]`` is "no other campaign measured this table either", which is
    # the state this test is about.  The default reads the operator-admission
    # campaigns from disk, and those are a different question, tested below.
    capacity = tool.placement_capacity(vectors, {"usable": False}, others=[])
    assert capacity["measured_simultaneous_objects"] == 0
    assert all(
        role["slots"] == 0
        for role in capacity["roles"].values() if role["object_keyed"]
    )
    demand = tool.placement_demand(
        _span((0, "VECTOR.RMS_NORM",
               [("input_view_0", 40), ("input_view_1", 2),
                ("output_view_0", 90)])),
        capacity,
    )
    assert demand["every_role_satisfiable"] is False, (
        "absence of evidence is a failure, not an unknown"
    )


@pytest.mark.parametrize("storage_class", ["rom", "hbm"])
def test_the_placement_shortfall_is_a_derived_count(artifact, storage_class):
    demand = _record(artifact, storage_class)["layer"]["placement_demand"]
    by_role = {row["role"]: row for row in demand["per_role"]}
    # The layer's seven projection matrices are seven distinct objects.  If
    # that number moves, this rung's reason must move with it.
    assert by_role["matmul_weight"]["distinct_objects_the_layer_needs"] == 7
    assert not demand["unattributed_operands"], (
        "every operand of the layer must be attributed to a placement role, "
        "or the shortfall is not a complete count"
    )
    # One table serves every role, so the union is the binding constraint and
    # it is stricter than any single role.
    union = next(
        row for row in demand["per_role"] if row["role"].startswith("__")
    )
    assert union["distinct_objects_the_layer_needs"] >= max(
        row["distinct_objects_the_layer_needs"]
        for row in demand["per_role"] if not row["role"].startswith("__")
    )
    assert demand["every_role_satisfiable"] == all(
        row["satisfiable"] for row in demand["per_role"]
    )
    reused = demand["output_objects"]["objects_written_more_than_once"]
    assert reused, (
        "the layer reuses buffers; that is why the campaign has to compare "
        "the engines' write stream and not only the retained image"
    )


def _span(*operators):
    """A minimal issue span: (pc, mnemonic, [(slot, object_id), ...])."""
    return [
        {"pc": pc, "mnemonic": mnemonic,
         "slots": [{"slot": slot, "object_id": object_id}
                   for slot, object_id in slots]}
        for pc, mnemonic, slots in operators
    ]


def _capacity_of(tool, depth):
    """A capacity record with a stated measured depth and nothing else."""
    return {
        "declared_entries": depth,
        "measured_simultaneous_objects": depth,
        "roles": {
            role: {"object_keyed": True, "slots": depth}
            for role in (
                "matmul_weight", "head_rms_weight", "head_rms_input",
                "rope_input", "rope_coefficient", "mapped_family_operand",
                "matmul_input", "rms_input", "rms_weight", "result_object",
            )
        },
    }


def test_object_addressed_results_place_a_rewrite(tool):
    """The predicate that used to be false, in both directions.

    An append cursor gave every write a fresh address, so an object written
    twice occupied two addresses and no reader could name the right one.  A
    result placed at its own object's base does not have that problem, and a
    span that rewrites a buffer is placeable.  What a rewrite still costs is
    recorded, because it is what makes an image comparison insufficient.
    """
    rewritten = tool.placement_demand(
        _span((0, "TENSOR.MATMUL",
               [("input_view_0", 30), ("input_view_1", 3),
                ("output_view_0", 90)]),
              (3, "TENSOR.MATMUL",
               [("input_view_0", 90), ("input_view_1", 3),
                ("output_view_0", 90)])),
        _capacity_of(tool, 8),
    )
    by_role = {row["role"]: row for row in rewritten["per_role"]}
    assert by_role["result_object"]["satisfiable"] is True
    assert rewritten["output_objects"]["objects_written_more_than_once"] == {
        "90": [0, 3]
    }
    assert rewritten["every_role_satisfiable"] is True


def test_the_union_of_the_roles_is_what_one_table_has_to_hold(tool):
    """Every role fits and the span still does not.

    Ten roles that each fit in the table can name more objects between them
    than the table holds.  Reporting only the per-role rows would call such a
    span placeable, which is the reason this row exists.
    """
    span = _span(
        (0, "VECTOR.RMS_NORM",
         [("input_view_0", 1), ("input_view_1", 2), ("output_view_0", 3)]),
        (3, "TENSOR.MATMUL",
         [("input_view_0", 3), ("input_view_1", 4), ("output_view_0", 5)]),
        (6, "VECTOR.ROPE",
         [("input_view_0", 5), ("input_view_1", 6), ("output_view_0", 7)]),
    )
    seven = tool.placement_demand(span, _capacity_of(tool, 7))
    assert all(
        row["satisfiable"] for row in seven["per_role"]
        if not row["role"].startswith("__")
    )
    assert seven["every_role_satisfiable"] is True

    two = tool.placement_demand(span, _capacity_of(tool, 2))
    union = next(row for row in two["per_role"] if row["role"].startswith("__"))
    assert union["distinct_objects_the_layer_needs"] == 7
    assert union["satisfiable"] is False
    assert two["every_role_satisfiable"] is False


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
        _capacity_of(tool, 8),
    )
    assert not demand["unattributed_operands"]
    by_role = {row["role"]: row for row in demand["per_role"]}
    assert by_role["mapped_family_operand"]["objects"] == [194, 200]


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
    board = json.loads(
        (ROOT / "configs/gates/redesign_gates.json").read_text()
    )["gates"]
    rung = next(g for g in board if g["id"] == "G1b")
    # G1b carries one workload binding per model since WP-L of the V4.1 plan.
    # This test is about ONE artifact's field names matching the evaluator that
    # reads it, so it evaluates that artifact's own binding: feeding the whole
    # rung would fail on the other model's absent artifact and say nothing about
    # this one's shape.  The binding is selected by the workload this tool
    # builds for, not by position.
    evaluator = dict(rung["evaluator"])
    bindings = evaluator.pop("workload_bindings", None)
    if bindings is not None:
        binding = next(b for b in bindings if b["workload"] == "TA-QW-EOS-1")
        evaluator.update(binding)
    gate = {**rung, "evaluator": evaluator}
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


def test_a_placement_replay_that_does_not_add_up_is_refused(tool):
    """If the placement replay is wrong, nothing derived from it may ship."""
    vectors = json.loads(VECTORS.read_text())
    case = json.loads(json.dumps(vectors["cases"][0]))
    case["expected"]["result_words"] = int(case["expected"]["result_words"]) + 1
    with pytest.raises(SystemExit) as error:
        tool.executed_span(case, [])
    assert "the placement replay is wrong" in str(error.value)


def test_a_result_object_the_table_does_not_name_is_refused(tool):
    """There is no cursor to fall back on, so this cannot be guessed."""
    vectors = json.loads(VECTORS.read_text())
    case = json.loads(json.dumps(vectors["cases"][0]))
    victim = int(case["supported_prefix"][0]["output_view"]["object_id"])
    case["bank_mapping"]["object_placement"] = [
        entry for entry in case["bank_mapping"]["object_placement"]
        if int(entry["object_id"]) != victim
    ]
    with pytest.raises(SystemExit) as error:
        tool.executed_span(case, [])
    assert "placement table does not name" in str(error.value)
