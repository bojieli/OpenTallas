"""SDC signal-integrity constraints and source-root provenance of the physical driver.

An LQ8 route at asap7 (results/physical_abi3/asap7/a3_lq8_array/pnr.json at
2f6b0a4) finished with 292 max-slew violations, all against the liberty
files' own 320 ps limit: the SDC the driver wrote carried set_max_fanout 32
and nothing else.  ``--max-transition-ns`` / ``--max-fanout`` /
``--slew-margin-percent`` give repair_design an explicit target, and
``--source-root`` lets a newer driver route a worktree pinned at the RTL's
commit while the record names both commits.  None of it may change what a
run without the options produces, and none of it may touch the closure rule.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import run_abi3_physical as flow  # noqa: E402

LANE_RECORD = ROOT / "results/physical_abi3/asap7/a3_lane_pipelined/pnr.json"

# The SDC of every routed record before the options existed (a3_lane_pipelined
# at 6.0 ns: its constraint.sdc artifact is hashed in the record).
LEGACY_LANE_SDC = (
    "set clk_period 6000\n"
    "create_clock -name core_clk -period $clk_period [get_ports clk]\n"
    "set non_clock_inputs [all_inputs -no_clocks]\n"
    "set_input_delay [expr $clk_period * 0.2] -clock core_clk $non_clock_inputs\n"
    "set_output_delay [expr $clk_period * 0.2] -clock core_clk [all_outputs]\n"
    "set_load 3.898 [all_outputs]\n"
    "set_max_fanout 32 [current_design]\n"
    "set_false_path -from [get_ports rst_n]\n"
)

LANE_BLOCK = {
    "top": "ot_a3_lane_pipelined",
    "sources": [
        "rtl/ot_fp32_rne_pkg.sv",
        "rtl/abi3/ot_a3_lane_pkg.sv",
        "rtl/abi3/ot_a3_lane_pipelined.sv",
    ],
    "parameters": {"ADDER_STAGES": 3, "ACC_SLOTS": 8},
    "clock_port": "clk",
    "false_path_from_ports": ["rst_n"],
}

BASE_ARGV = ["--view", "asap7", "--clock-period-ns", "6.0", "--output", "x.json"]


def _liberty_present(view: str, corner: str) -> bool:
    return all(Path(p).is_file() for p in flow.VIEWS[view]["corners"][corner]["liberty"])


def _asap7() -> tuple[dict, dict]:
    view = flow.VIEWS["asap7"]
    return view, view["corners"]["TT"]


def _sky130() -> tuple[dict, dict]:
    view = flow.VIEWS["sky130hd"]
    return view, view["corners"]["tt"]


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------


def test_options_are_absent_unless_given():
    args = flow.build_parser().parse_args(BASE_ARGV)
    assert args.max_transition_ns is None
    assert args.max_fanout is None
    assert args.slew_margin_percent is None
    assert args.source_root is None


def test_bare_flags_pick_the_library_and_driver_defaults():
    args = flow.build_parser().parse_args(BASE_ARGV + ["--max-transition-ns", "--max-fanout"])
    assert args.max_transition_ns == flow.LIBRARY_LIMIT
    assert args.max_fanout == flow.DRIVER_DEFAULT
    args = flow.build_parser().parse_args(
        BASE_ARGV + ["--max-transition-ns", "library", "--max-fanout", "default"]
    )
    assert args.max_transition_ns == flow.LIBRARY_LIMIT
    assert args.max_fanout == flow.DRIVER_DEFAULT


def test_explicit_values_parse_and_bad_ones_are_refused():
    args = flow.build_parser().parse_args(
        BASE_ARGV + ["--max-transition-ns", "0.25", "--max-fanout", "16", "--slew-margin-percent", "20"]
    )
    assert args.max_transition_ns == 0.25
    assert args.max_fanout == 16
    assert args.slew_margin_percent == 20.0
    for bad in (["--max-transition-ns", "0"], ["--max-transition-ns", "fast"], ["--max-fanout", "-3"], ["--max-fanout", "many"]):
        with pytest.raises(SystemExit):
            flow.build_parser().parse_args(BASE_ARGV + bad)


# --------------------------------------------------------------------------
# The SDC without the options is byte-for-byte what every earlier record had
# --------------------------------------------------------------------------


def test_legacy_sdc_is_unchanged_without_options():
    view, _ = _asap7()
    assert flow.sdc_text(view, LANE_BLOCK, 6.0, None) == LEGACY_LANE_SDC
    assert flow.resolve_signal_integrity_constraints(view, _asap7()[1], None, None, None) is None


@pytest.mark.skipif(not LANE_RECORD.is_file(), reason="lane record not present")
def test_legacy_sdc_matches_the_routed_lane_record_artifact():
    record = json.loads(LANE_RECORD.read_text(encoding="utf-8"))
    artifact = record["place_and_route"]["artifacts"].get("constraint.sdc")
    if not artifact:
        pytest.skip("lane record carries no constraint.sdc artifact hash")
    if record["place_and_route"].get("signal_integrity_constraints"):
        pytest.skip("lane record was routed with explicit constraints; the legacy SDC claim is about records without them")
    assert hashlib.sha256(LEGACY_LANE_SDC.encode("utf-8")).hexdigest() == artifact["sha256"]


def test_legacy_orfs_config_has_no_slew_margin():
    view, _ = _asap7()
    lines = flow.orfs_config_lines("nick", LANE_BLOCK, "asap7", view["pnr"], 35, 0.6, None)
    assert not any(line.startswith("export SLEW_MARGIN") for line in lines)
    assert "export CORNER = TC" in lines
    assert "export VERILOG_TOP_PARAMS = ACC_SLOTS 8 ADDER_STAGES 3" in lines


# --------------------------------------------------------------------------
# Library limits per view
# --------------------------------------------------------------------------


@pytest.mark.skipif(not _liberty_present("asap7", "TT"), reason="asap7 liberty not installed")
def test_asap7_library_limit_is_320_ps():
    view, corner = _asap7()
    limits = flow.library_slew_limits(corner)
    declared = {e["liberty"]: e["default_max_transition"] for e in limits}
    # Four of the five RVT TT libraries declare 320 ps; SIMPLE declares 4000 ps,
    # so the library limit the flow is held to is the 320 ps minimum.
    assert min(v for v in declared.values() if v is not None) == 320.0
    assert all(e["pin_max_transition_count"] > 0 for e in limits)
    constraints = flow.resolve_signal_integrity_constraints(view, corner, flow.LIBRARY_LIMIT, None, None)
    assert constraints["max_transition_ns"] == 0.32
    assert constraints["max_transition_library_units"] == 320.0
    assert constraints["max_transition_source"].startswith("library")
    assert constraints["sdc_lines"] == [
        "set_max_fanout 32 [current_design]",
        "set_max_transition 320 [current_design]",
    ]
    assert "max_fanout" not in constraints


@pytest.mark.skipif(not _liberty_present("sky130hd", "tt"), reason="sky130 liberty not installed")
def test_sky130hd_library_limit_is_1p5_ns():
    view, corner = _sky130()
    constraints = flow.resolve_signal_integrity_constraints(view, corner, flow.LIBRARY_LIMIT, None, None)
    assert constraints["max_transition_ns"] == 1.5
    assert constraints["max_transition_library_units"] == 1.5
    assert constraints["sdc_lines"][-1] == "set_max_transition 1.5 [current_design]"


@pytest.mark.skipif(
    not (_liberty_present("asap7", "TT") and _liberty_present("sky130hd", "tt")),
    reason="liberty not installed",
)
def test_neither_view_declares_a_fanout_limit_so_the_driver_default_is_recorded():
    for view, corner in (_asap7(), _sky130()):
        constraints = flow.resolve_signal_integrity_constraints(view, corner, None, flow.DRIVER_DEFAULT, None)
        assert constraints["max_fanout"] == flow.DEFAULT_MAX_FANOUT == 32
        assert constraints["library_declares_fanout_limit"] is False
        assert constraints["max_fanout_source"].startswith("driver default")
        assert constraints["sdc_lines"] == ["set_max_fanout 32 [current_design]"]
        assert "max_transition_ns" not in constraints


# --------------------------------------------------------------------------
# Explicit values, unit conversion, and what reaches the SDC and config.mk
# --------------------------------------------------------------------------


@pytest.mark.skipif(not _liberty_present("asap7", "TT"), reason="asap7 liberty not installed")
def test_explicit_values_reach_the_sdc_in_library_units():
    view, corner = _asap7()
    constraints = flow.resolve_signal_integrity_constraints(view, corner, 0.25, 16, 20.0)
    assert constraints["max_transition_library_units"] == 250.0  # ps
    assert constraints["max_transition_source"] == "command line"
    assert constraints["max_fanout"] == 16
    assert constraints["slew_margin_percent"] == 20.0
    text = flow.sdc_text(view, LANE_BLOCK, 6.0, constraints)
    assert "set_max_fanout 16 [current_design]\n" in text
    assert "set_max_fanout 32" not in text
    assert "set_max_transition 250 [current_design]\n" in text
    assert text.endswith("set_false_path -from [get_ports rst_n]\n")
    config = flow.orfs_config_lines("nick", LANE_BLOCK, "asap7", view["pnr"], 35, 0.6, constraints)
    assert config[-1] == "export SLEW_MARGIN = 20"
    # A margin alone changes config.mk and nothing in the SDC.
    margin_only = flow.resolve_signal_integrity_constraints(view, corner, None, None, 10.0)
    assert flow.sdc_text(view, LANE_BLOCK, 6.0, margin_only) == LEGACY_LANE_SDC
    assert margin_only["sdc_lines"] == ["set_max_fanout 32 [current_design]"]


@pytest.mark.skipif(not _liberty_present("sky130hd", "tt"), reason="sky130 liberty not installed")
def test_sky130hd_units_are_nanoseconds():
    view, corner = _sky130()
    constraints = flow.resolve_signal_integrity_constraints(view, corner, 0.8, None, None)
    assert constraints["max_transition_library_units"] == 0.8
    assert constraints["sdc_lines"][-1] == "set_max_transition 0.8 [current_design]"


@pytest.mark.skipif(not _liberty_present("asap7", "TT"), reason="asap7 liberty not installed")
def test_out_of_range_values_are_refused():
    view, corner = _asap7()
    with pytest.raises(flow.FlowError):
        flow.resolve_signal_integrity_constraints(view, corner, None, None, 100.0)
    with pytest.raises(flow.FlowError):
        flow.resolve_signal_integrity_constraints(view, corner, -0.1, None, None)


# --------------------------------------------------------------------------
# The closure rule is untouched
# --------------------------------------------------------------------------


def _routed_record(max_slew: int, constraints: dict | None) -> dict:
    metrics = {
        "setup_wns_ns": 1.0, "hold_wns_ns": 0.1, "drc_errors": 0,
        "antenna_violating_nets": 0, "antenna_violating_pins": 0,
        "max_slew_violations": max_slew, "max_cap_violations": 0, "max_fanout_violations": 0,
        "fmax_hz": 1e8, "standard_cell_count": 10, "standard_cell_area_um2": 1.0,
        "core_area_um2": 2.0, "utilization_fraction": 0.5,
    }
    pnr = {"metrics": metrics, "clock_period_ns": 6.0}
    if constraints:
        pnr["signal_integrity_constraints"] = constraints
    return {"status": flow.STATUS_PASS, "place_and_route": pnr, "design": {}}


def test_constraints_do_not_change_the_closure_rule():
    constraints = {
        "max_transition_ns": 0.32, "max_transition_library_units": 320.0, "max_fanout": 32,
        "sdc_lines": ["set_max_fanout 32 [current_design]", "set_max_transition 320 [current_design]"],
    }
    still_violating = _routed_record(7, constraints)
    flow.augment_design(still_violating, lanes=None, mac_per_cycle=None, evidence=[], lane_regex=None, netlists=[])
    assert still_violating["design"]["closed"] is False
    assert "max_slew_violations 7" in still_violating["design"]["closed_reason"]

    repaired = _routed_record(0, constraints)
    flow.augment_design(repaired, lanes=None, mac_per_cycle=None, evidence=[], lane_regex=None, netlists=[])
    assert repaired["design"]["closed"] is True
    assert repaired["design"]["signal_integrity_clean"] is True

    unconstrained_clean = _routed_record(0, None)
    flow.augment_design(unconstrained_clean, lanes=None, mac_per_cycle=None, evidence=[], lane_regex=None, netlists=[])
    assert unconstrained_clean["design"]["closed"] is True


@pytest.mark.skipif(not LANE_RECORD.is_file(), reason="lane record not present")
def test_old_records_without_the_block_still_parse_and_close():
    record = json.loads(LANE_RECORD.read_text(encoding="utf-8"))
    assert record["place_and_route"].get("signal_integrity_constraints") is None
    verdict = flow.evaluate_verdict(record)
    assert verdict["status"] == record["status"]
    flow.augment_design(record, lanes=1, mac_per_cycle=None, evidence=[], lane_regex=None, netlists=[])
    assert record["design"]["closed"] is (record["status"] == flow.STATUS_PASS)


# --------------------------------------------------------------------------
# Source root and driver provenance
# --------------------------------------------------------------------------


def test_driver_identity_names_the_driver_commit_and_whether_the_trees_differ(tmp_path):
    original = flow.ROOT
    try:
        flow.ROOT = flow.DRIVER_ROOT
        same = flow.driver_identity()
        assert same["path"] == str(Path(flow.__file__).resolve())
        assert same["tree"] == str(flow.DRIVER_ROOT)
        assert same["commit"] is None or len(same["commit"]) == 40
        assert same["same_tree_as_sources"] is True
        assert "same tree" in same["note"]
        assert same["sha256"] == hashlib.sha256(Path(flow.__file__).read_bytes()).hexdigest()

        flow.ROOT = tmp_path
        other = flow.driver_identity()
        assert other["same_tree_as_sources"] is False
        assert "--source-root" in other["note"]
        assert other["commit"] == same["commit"]
    finally:
        flow.ROOT = original


def test_source_root_must_hold_rtl_and_rebinds_relative_paths(tmp_path, capsys):
    original = flow.ROOT
    try:
        no_rtl = tmp_path / "empty"
        no_rtl.mkdir()
        assert flow.main(BASE_ARGV + ["--source-root", str(no_rtl)]) == 2
        assert "no rtl/ directory" in capsys.readouterr().err

        pinned = tmp_path / "pinned"
        (pinned / "rtl").mkdir(parents=True)
        (pinned / "x.json").write_text("{}", encoding="utf-8")
        # The relative --output now resolves under the source root, where it
        # already exists, so the driver refuses before running anything.
        assert flow.main(BASE_ARGV + ["--source-root", str(pinned)]) == 2
        assert "refusing to overwrite" in capsys.readouterr().err
        assert flow.ROOT == pinned.resolve()
    finally:
        flow.ROOT = original
