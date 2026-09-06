"""The L3 calibration artifact (gate G4) must reproduce from its inputs and fail
when the RTL and the cycle model disagree.

``tools/derive_cycle_machine.py --calibrate`` charges the cycle model with
exactly the operations the L1 block records ran and divides by what the RTL
took.  These tests exist to fail in four situations:

1.  The artifact on disk no longer reproduces from the inputs it digests --
    an input moved and the calibration was not re-run.
2.  A perturbed rate or cycle count does NOT leave the band: the ratio would
    then be a note, not a measurement.
3.  The charge stops being the model's own formula (``_compute_cycles`` and
    ``_time_steps``), or the whole-run decomposition drifts.
4.  The verdict stops being a conjunction over every ratio, every block and
    the boundary rule of docs/CHIP_ARCHITECTURE_DESIGN.md section 11.5.
"""

from __future__ import annotations

import copy
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.derive_cycle_machine import (  # noqa: E402
    CALIBRATED_BLOCKS,
    CALIBRATION_BAND,
    CALIBRATION_BAND_SOURCE,
    CALIBRATION_SCHEMA,
    DEFAULT_ANALYTICAL,
    DEFAULT_CALIBRATION_OUT,
    DEFAULT_TECHNOLOGY,
    DESIGN_DOC,
    GATES_CONFIG,
    TENSOR_WORK_UNITS_PER_PRODUCT,
    calibrate,
    calibration_input_paths,
    canonical,
    design_boundary_rule,
    load_anchor,
    model_block_charge,
    run_calibration,
)

ROM_DESIGN = "Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4"
HBM_DESIGN = "Qwen3-8B/b200_sxm-x2-tensor"
ANALYTICAL = REPO / DEFAULT_ANALYTICAL
TECHNOLOGY = REPO / DEFAULT_TECHNOLOGY
ARTIFACT = REPO / DEFAULT_CALIBRATION_OUT
RECORD_KEYS = ("lane", "lane_groups", "lq8", "control_plane", "reconciliation",
               "rom_cost_table", "hbm_cost_table", "rom_capability")


@pytest.fixture(scope="module")
def anchor():
    return load_anchor(
        ANALYTICAL, TECHNOLOGY, rom_design=ROM_DESIGN, hbm_design=HBM_DESIGN,
        batch_size=1, context_tokens=8192,
    )


@pytest.fixture(scope="module")
def paths():
    return calibration_input_paths(ANALYTICAL, TECHNOLOGY)


@pytest.fixture(scope="module")
def loaded(paths):
    body = {k: json.loads(paths[k].read_text()) for k in RECORD_KEYS}
    body["doc_text"] = paths["design_doc"].read_text()
    return body


@pytest.fixture(scope="module")
def fresh(anchor):
    return run_calibration(anchor, ANALYTICAL, TECHNOLOGY)


def _calibrate(anchor, loaded, **overrides):
    kw = {
        "lane": loaded["lane"],
        "lane_groups": loaded["lane_groups"],
        "lq8": loaded["lq8"],
        "control_plane": loaded["control_plane"],
        "reconciliation": loaded["reconciliation"],
        "rom_table": loaded["rom_cost_table"],
        "hbm_table": loaded["hbm_cost_table"],
        "rom_capability": loaded["rom_capability"],
        "doc_text": loaded["doc_text"],
    }
    kw.update(overrides)
    return calibrate(anchor, **kw)


def _without_git(body):
    return {k: v for k, v in body.items() if k != "git"}


# ---------------------------------------------------------------------------
# 1.  The artifact is what its inputs say it is
# ---------------------------------------------------------------------------
def _require_artifact():
    if not ARTIFACT.exists():
        pytest.skip(
            f"{ARTIFACT.relative_to(REPO)} is absent; G4 fails on absence until "
            "tools/derive_cycle_machine.py --calibrate has been run"
        )
    return json.loads(ARTIFACT.read_text())


def test_the_artifact_reproduces_from_its_inputs(fresh):
    on_disk = _require_artifact()
    assert on_disk["schema"] == CALIBRATION_SCHEMA
    moved = sorted(
        rel for rel, entry in fresh["inputs"].items()
        if on_disk["inputs"].get(rel, {}).get("sha256") != entry["sha256"]
    )
    assert canonical(_without_git(fresh)) == canonical(_without_git(on_disk)), (
        "the calibration artifact no longer reproduces from its inputs; "
        + (f"inputs whose digest moved: {moved}; " if moved else "")
        + "re-run tools/derive_cycle_machine.py --calibrate"
    )


def test_the_artifact_was_emitted_from_committed_inputs():
    on_disk = _require_artifact()
    assert on_disk["git"]["dirty_inputs"] == [], (
        "the artifact digests inputs that were uncommitted when it was emitted: "
        f"{on_disk['git']['dirty_inputs']}"
    )
    assert len(on_disk["git"]["commit"]) == 40


def test_every_input_is_digested(fresh, paths):
    digested = set(fresh["inputs"])
    for role, path in paths.items():
        rel = str(path.resolve().relative_to(REPO))
        assert rel in digested, f"{role} ({rel}) is read but not digested"
    for rel in ("runtime/cycle/model.py", "runtime/cycle/machine.py",
                DESIGN_DOC, "configs/gates/redesign_gates.json"):
        assert rel in digested
    for entry in fresh["inputs"].values():
        assert len(entry["sha256"]) == 64


def test_check_mode_agrees_with_the_artifact():
    _require_artifact()
    result = subprocess.run(
        [sys.executable, "tools/derive_cycle_machine.py", "--calibrate", "--check"],
        cwd=REPO, text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "reproduces from its inputs" in result.stdout


# ---------------------------------------------------------------------------
# 2.  Every ratio is reported, and the verdict is a conjunction over them
# ---------------------------------------------------------------------------
def _rate_entries(loaded):
    for key in ("lane", "lane_groups", "lq8"):
        for depth, entries in loaded[key]["measured"]["rates_by_depth"].items():
            for entry in entries:
                yield key, depth, entry


def test_every_rate_case_yields_three_ratios_on_both_simulators(fresh, loaded):
    cal = fresh["calibration"]
    entries = list(_rate_entries(loaded))
    assert entries, "no rate cases in the L1 records"
    assert cal["ratio_count"] == 3 * len(entries) == len(cal["ratios"])
    seen = {
        (r["block"], r["depth"], r["case"], r["simulator"], r["quantity"])
        for r in cal["ratios"]
    }
    for key, depth, entry in entries:
        for quantity in ("steady_state", "per_pass", "whole_run"):
            assert (key, depth, int(entry["case"]), entry["simulator"], quantity) in seen
    lo, hi = CALIBRATION_BAND
    for r in cal["ratios"]:
        assert r["ratio_model_over_rtl"] == pytest.approx(r["model_cycles"] / r["rtl_cycles"])
        assert r["within_band"] == (lo <= r["ratio_model_over_rtl"] <= hi)
    assert set(cal["per_depth"]) == {"L1", "L2", "L3"}
    for block in ("lane", "lane_groups", "lq8"):
        assert cal["per_block"][block]["ratios"] > 0


def test_the_steady_state_charge_matches_the_rtl_window_exactly(fresh):
    """At the block's own rate the wave count and quantisation must be exact."""
    for r in fresh["calibration"]["ratios"]:
        if r["quantity"] == "steady_state":
            assert r["model_cycles"] == r["rtl_cycles"], r


def test_the_verdict_is_a_conjunction_not_an_average(fresh):
    cal = fresh["calibration"]
    expected = (
        cal["block_ratios_within_band"]
        and not cal["blocks_without_measured_cycles"]
        and cal["boundary"]["rung_item_met"]
    )
    assert cal["block_cycles_within_band"] == expected
    assert cal["calibrated_blocks"] == list(CALIBRATED_BLOCKS)
    # The band is +/-10 %, and the artifact must say where it read that from.
    # The section 11.5 table row the gate's note cites was replaced by prose
    # at 13e6a5a, so the source names the gate's own note and says so.
    assert cal["band"]["low"] == CALIBRATION_BAND[0]
    assert cal["band"]["high"] == CALIBRATION_BAND[1]
    assert cal["band"]["source"] == CALIBRATION_BAND_SOURCE
    assert GATES_CONFIG in cal["band"]["source"]
    assert "no longer exists" in cal["band"]["source"]
    assert cal["reason"]


# ---------------------------------------------------------------------------
# 3.  A perturbed rate or cycle count breaks the band
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("rate, direction", [(0.8, "above"), (1.2, "below")])
def test_a_perturbed_lane_rate_breaks_the_band(anchor, loaded, rate, direction):
    lane = copy.deepcopy(loaded["lane"])
    lane["measured"]["mac_per_lane_cycle"] = rate
    cal = _calibrate(anchor, loaded, lane=lane)
    lane_rows = [r for r in cal["ratios"] if r["block"] == "lane"]
    assert lane_rows and not any(r["within_band"] for r in lane_rows)
    lo, hi = CALIBRATION_BAND
    for r in lane_rows:
        if direction == "above":
            assert r["ratio_model_over_rtl"] > hi
        else:
            assert r["ratio_model_over_rtl"] < lo
    assert cal["block_ratios_within_band"] is False
    assert cal["block_cycles_within_band"] is False
    assert "lane L1 case 61" in cal["reason"]
    # The other blocks keep their own verdicts: the failure is attributed.
    assert cal["per_block"]["lq8"]["all_within_band"] is True


def test_a_perturbed_lq8_cycle_count_breaks_the_band(anchor, loaded):
    lq8 = copy.deepcopy(loaded["lq8"])
    for entries in lq8["measured"]["rates_by_depth"].values():
        for entry in entries:
            entry["window_cycles"] = int(round(entry["window_cycles"] * 1.15))
            entry["total_cycles"] = int(round(entry["total_cycles"] * 1.15))
    cal = _calibrate(anchor, loaded, lq8=lq8)
    rows = [r for r in cal["ratios"] if r["block"] == "lq8"]
    assert rows and not any(r["within_band"] for r in rows)
    assert cal["per_block"]["lq8"]["all_within_band"] is False
    assert cal["per_block"]["lane"]["all_within_band"] is True
    assert cal["block_cycles_within_band"] is False


def test_a_rate_inside_the_band_stays_inside_it(anchor, loaded):
    """The band is +/-10 %: a 5 % perturbation must not fail it."""
    lane = copy.deepcopy(loaded["lane"])
    lane["measured"]["mac_per_lane_cycle"] = 1.0 / 1.05
    cal = _calibrate(anchor, loaded, lane=lane)
    lane_rows = [r for r in cal["ratios"] if r["block"] == "lane"]
    assert all(r["within_band"] for r in lane_rows)
    assert all(r["ratio_model_over_rtl"] > 1.04 for r in lane_rows)


# ---------------------------------------------------------------------------
# 4.  The charge is the model's own formula
# ---------------------------------------------------------------------------
def _mirror(rows, cols, depth, lanes, rate, tile_issue=1):
    """Local mirror of the tensor branch, kept apart from the model on purpose."""
    waves = math.ceil(rows / min(rows, lanes)) * cols if lanes >= rows else rows * cols
    units = rate * TENSOR_WORK_UNITS_PER_PRODUCT
    per_wave = max(math.ceil(depth * TENSOR_WORK_UNITS_PER_PRODUCT / units), tile_issue)
    return waves, per_wave


def test_the_charge_is_the_models_tensor_branch(fresh, loaded):
    from runtime.abi3.capability import Capability
    from runtime.cycle.machine import CostTable, MachineModel

    machine = MachineModel(
        Capability.from_dict(loaded["rom_capability"]),
        CostTable.from_dict(loaded["rom_cost_table"]),
    )
    engine, seq, mem = machine.engine("tensor"), machine.sequencer(), machine.memory()
    for rows, cols, depth, lanes, rate in (
        (32, 48, 1024, 1, 1.0), (8, 48, 1024, 8, 2.0), (16, 48, 1024, 1, 4.0),
        (8, 48, 1000, 8, 1.0), (32, 48, 1024, 1, 0.8),
    ):
        charge = model_block_charge(
            rows=rows, cols=cols, depth=depth, lanes=lanes,
            products_per_lane_cycle=rate, engine=engine, sequencer=seq, memory=mem,
        )
        waves, per_wave = _mirror(rows, cols, depth, lanes, rate)
        assert charge["output_waves"] == waves
        assert charge["compute_cycles"] == waves * per_wave
        assert charge["work_units_per_product"] == TENSOR_WORK_UNITS_PER_PRODUCT
        assert charge["whole_run_cycles"] == (
            seq.fetch_cycles + seq.decode_cycles + seq.queue_transit_cycles
            + charge["compute_cycles"] + engine.fixed_latency_cycles
        )
    machine_block = fresh["calibration"]["machine"]
    assert machine_block["sequencer"] == seq.to_dict()
    assert machine_block["tensor_engine_as_derived"]["fixed_latency_cycles"] == engine.fixed_latency_cycles


# ---------------------------------------------------------------------------
# 5.  The boundary: unmeasured, reported, and folded in by section 11.5
# ---------------------------------------------------------------------------
def test_the_boundary_is_read_off_the_design_document(loaded):
    """Both forms of section 2.1 row 33 are read, and neither is invented.

    The design asserted "**120 cycles** (band 107-137)" until commit 13e6a5a
    and asserts nothing since.  The tool must read whichever the document
    holds, and must refuse a row it cannot read rather than defaulting -- a
    default would be a figure no document states.
    """
    rule = design_boundary_rule(loaded["doc_text"])
    # The document as it stands: the figure is withdrawn.
    assert rule["design_states_a_figure"] is False
    assert rule["design_cycles_per_boundary"] is None
    assert rule["design_band"] is None
    assert sorted(rule["design_withdrawn_figures_cycles"]) == [39, 120]
    assert "L3/G4" in rule["rung_rule"]

    # The historical form still parses, so an older document reproduces its
    # own artifact.
    historical = (
        "| 33 | Per-boundary exposed latency (N5) | **120 cycles** (band "
        "107\u2013137): control tree 8 + fill 36 + K-block tree 25\u201335 | A | x | both |\n"
        "5. **L3/G4:** calibrated block and full dependent-boundary cycles.\n"
    )
    old_rule = design_boundary_rule(historical)
    assert old_rule["design_states_a_figure"] is True
    assert old_rule["design_cycles_per_boundary"] == 120
    assert old_rule["design_band"] == [107, 137]
    assert "fill 36" in old_rule["design_decomposition"]

    with pytest.raises(Exception):
        design_boundary_rule("| 33 | something else |\n")


def test_the_boundary_is_unmeasured_and_folded_into_the_verdict(fresh):
    """No chain record exists, so the item FAILS on absence and says why."""
    b = fresh["calibration"]["boundary"]
    assert b["measured"] is False
    assert b["rtl_measured_boundary_cycles"] is None
    assert b["model_exposed_chain_cycles"] == sum(b["model_exposed_chain_decomposition"].values())
    # The design withdrew its figure, so there is no ratio to take and no
    # band the model's number could sit inside.
    assert b["design_cycles_per_boundary"] is None
    assert b["ratio_model_chain_over_design"] is None
    assert b["model_chain_within_design_band"] is False
    assert b["technology_latency_rederived"] is False
    assert b["rung_item_met"] is False
    assert "unmet, on absence" in b["rung_item_decision"]
    assert "--boundary-chain-record" in b["why_unmeasured"]
    assert fresh["calibration"]["block_cycles_within_band"] is False
    assert "boundary item unmet" in fresh["calibration"]["reason"]


def test_a_chain_record_is_refused_unless_both_simulators_agree(fresh):
    """A record that is short of the provenance spine does not count.

    Absence is FAIL; so is a record that passed on one simulator, or whose
    two simulators disagree, or that carries no boundary figure.  The four
    refusals are exercised here so a future record cannot meet the item by
    being merely present.
    """
    from tools.derive_cycle_machine import _boundary_measurement

    good = {
        "campaign": "rtl3_abi3_boundary_chain",
        "status": "pass",
        "boundary": {
            "cycles": 217,
            "simulators_agree": True,
            "per_simulator": [
                {"simulator": "iverilog", "cycles": 217},
                {"simulator": "verilator", "cycles": 217},
            ],
        },
    }
    assert _boundary_measurement(good)["measured"] is True
    assert _boundary_measurement(good)["rtl_measured_boundary_cycles"] == 217

    assert _boundary_measurement(None)["measured"] is False

    failed = copy.deepcopy(good)
    failed["status"] = "fail"
    assert _boundary_measurement(failed)["measured"] is False

    one_sim = copy.deepcopy(good)
    one_sim["boundary"]["per_simulator"] = [{"simulator": "verilator", "cycles": 217}]
    assert _boundary_measurement(one_sim)["measured"] is False

    disagree = copy.deepcopy(good)
    disagree["boundary"]["simulators_agree"] = False
    disagree["boundary"]["per_simulator"][1]["cycles"] = 219
    assert _boundary_measurement(disagree)["measured"] is False

    no_figure = copy.deepcopy(good)
    no_figure["boundary"]["cycles"] = None
    assert _boundary_measurement(no_figure)["measured"] is False


def test_the_lane_fill_is_an_observation_not_a_ratio(fresh):
    b = fresh["calibration"]["boundary"]
    assert b["lane_fill_observations"]
    for obs in b["lane_fill_observations"]:
        assert obs["first_retire_cycle"] > 0
    assert not any(
        r["quantity"] == "fill" for r in fresh["calibration"]["ratios"]
    )


# ---------------------------------------------------------------------------
# 6.  The control plane's measured cycles, and the ratio they support
# ---------------------------------------------------------------------------
def test_the_control_plane_cycles_are_measured_on_both_simulators(fresh, loaded):
    """Section 13 item 13's second half: the ratio is no longer null.

    Every case of every simulator must carry a positive measured span and two
    ratios over it, and the ratios must be the model's charge divided by the
    RTL's own count -- not a restatement of the charge.
    """
    cp = fresh["calibration"]["control_plane"]
    assert cp["measured"] is True and cp["status"] == "measured"
    assert cp["ratio_count"] == 32, cp["ratio_count"]
    simulators = {case["simulator"] for case in cp["cases"]}
    assert simulators == {"iverilog", "verilator"}, simulators
    quantities = {case["quantity"] for case in cp["cases"]}
    assert quantities == {"transaction", "transaction_less_bench"}
    for case in cp["cases"]:
        assert case["rtl_cycles"] > 0
        assert case["model_cycles"] > 0
        assert case["ratio_model_over_rtl"] == pytest.approx(
            case["model_cycles"] / case["rtl_cycles"]
        )
        assert case["within_band"] is not None
        mix = case["instruction_mix"]
        assert sum(
            mix[k] for k in (
                "predicate_steps", "engine_steps", "control_branch_steps",
                "control_loop_next_steps", "control_other_steps",
            )
        ) == case["rtl_fetched"]
        # the bench's own stalls are a strict subset of the span
        assert (
            case["rtl_issue_backpressure_cycles"]
            + case["rtl_predicate_service_cycles"]
        ) < case["rtl_transaction_cycles"]
    assert "control_plane" not in fresh["calibration"]["blocks_without_measured_cycles"]
    block = fresh["calibration"]["per_block"]["control_plane"]
    assert block["ratios"] == 32
    assert block["all_within_band"] is False


def test_the_control_plane_ratio_is_the_finding_not_a_fit(fresh):
    """The measured front end is an order of magnitude slower than the model.

    This test pins the direction and the scale of the disagreement, so a
    later change that quietly brought the ratio into band by moving the model
    rather than the RTL would have to say so here.
    """
    cp = fresh["calibration"]["control_plane"]
    ratios = [case["ratio_model_over_rtl"] for case in cp["cases"]]
    assert max(ratios) < 0.1, max(ratios)
    assert min(ratios) > 0.01, min(ratios)
    assert fresh["calibration"]["block_ratios_within_band"] is False
    assert "control-plane ratios outside" in fresh["calibration"]["reason"]


def test_a_record_without_cycles_is_unmeasured_and_fails(fresh, loaded):
    """Strip the cycle counts and the block goes back to failing on absence."""
    from tools.derive_cycle_machine import calibrate_control_plane
    from runtime.abi3.capability import Capability
    from runtime.cycle.machine import CostTable, MachineModel

    machine = MachineModel(
        Capability.from_dict(loaded["rom_capability"]),
        CostTable.from_dict(loaded["rom_cost_table"]),
    )
    stripped = copy.deepcopy(loaded["control_plane"])
    for sim in stripped["cases"]:
        for case in sim["observed_cases"]:
            case.pop("rtl_transaction_cycles", None)
    cp = calibrate_control_plane(stripped, machine.sequencer())
    assert cp["measured"] is False and cp["status"] == "unmeasured"
    assert cp["ratio_count"] == 0
    assert all(case["ratio_model_over_rtl"] is None for case in cp["cases"])
    assert "carries no clock-cycle count" in cp["why"]


# ---------------------------------------------------------------------------
# 7.  The derived machine against the analytical artifact
# ---------------------------------------------------------------------------
def test_the_derived_machine_reproduces_the_analytical_anchor(fresh, anchor, loaded):
    d = fresh["calibration"]["derived_machine"]
    assert d["reproduces_anchor"] is True
    assert d["anchor"]["compute_roof_ops_s"] == anchor.compute_roof_ops_s
    assert d["anchor"]["component_times_s_compute"] == anchor.rom["component_times_s"]["compute"]
    for role in ("rom_machine", "hbm_machine"):
        assert d[role]["relative_error"] < 1e-9
        assert d[role]["compute_roof_ops_s"] == pytest.approx(anchor.compute_roof_ops_s, rel=1e-12)
    assert d["compute_time_relative_error"] < 1e-9
    assert fresh["calibration"]["derived_machine_reproduces_anchor"] is True
    regime = fresh["calibration"]["binding_regime"]
    recon = loaded["reconciliation"]["targets"]
    for role in ("rom", "hbm"):
        assert regime[role] == recon[role]["binding_regime"]
    assert regime["same_regime_both_targets"] == all(
        recon[r]["binding_regime"]["same_regime"] for r in ("rom", "hbm")
    )


def test_a_moved_roof_is_not_reproduced(anchor, loaded):
    table = copy.deepcopy(loaded["rom_cost_table"])
    table["parameters"]["engine.tensor.work_per_lane_cycle"]["value"] *= 1.0 + 1e-6
    cal = _calibrate(anchor, loaded, rom_table=table)
    assert cal["derived_machine_reproduces_anchor"] is False
    assert cal["derived_machine"]["rom_machine"]["relative_error"] > 1e-9


# ---------------------------------------------------------------------------
# 8.  Gate G4 reads this artifact and follows its verdict
# ---------------------------------------------------------------------------
def test_g4_reads_the_artifact_and_follows_its_verdict():
    on_disk = _require_artifact()
    from tools.check_redesign_gates import evaluate

    gates = json.loads((REPO / "configs/gates/redesign_gates.json").read_text())
    g4 = next(g for g in gates["gates"] if g["id"] == "G4")
    assert g4["evaluator"]["require"]["field"] == "calibration.block_cycles_within_band"
    assert g4["evaluator"]["also_require"]["field"] == "calibration.derived_machine_reproduces_anchor"
    result = evaluate(g4)
    cal = on_disk["calibration"]
    expected = "pass" if (
        cal["block_cycles_within_band"] and cal["derived_machine_reproduces_anchor"]
    ) else "fail"
    assert result["status"] == expected, result
    assert "calibration.block_cycles_within_band" in result["why"]
