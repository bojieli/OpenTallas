import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "configs" / "pdk" / "asap7_physical_lock.json"
RUNNER = ROOT / "tools" / "run_asap7_physical.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_asap7_physical", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_asap7_lock_is_strict_and_source_hashed():
    runner = load_runner()
    lock = runner.strict_json(LOCK)
    runner.validate_lock(lock)
    assert lock["campaign_id"] == "opentallas-asap7-predictive-physical-v1"
    assert len(lock["cases"]) == 3
    for case in lock["cases"]:
        inventory = runner.verify_source_hashes(case)
        assert len(inventory) == len(case["sources"])
        assert all(item["sha256"] == case["sources"][item["path"]] for item in inventory)


def test_asap7_cases_forbid_fake_memory_and_state_claim_boundary():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    patterns = tuple(lock["acceptance"]["forbidden_memory_name_patterns"])
    assert "fakeram" in patterns
    for case in lock["cases"]:
        joined = " ".join(case["sources"]).lower()
        assert not any(pattern in joined for pattern in patterns)
    boundary = " ".join(lock["claim_boundary"])
    assert "predictive" in boundary
    assert "not tied to a foundry" in boundary
    assert "not OpenTallas target MXFP4" in boundary


def test_asap7_config_and_constraints_are_case_specific():
    runner = load_runner()
    lock = runner.strict_json(LOCK)
    for case in lock["cases"]:
        config = runner.config_text(case, lock)
        sdc = runner.sdc_text(case, lock)
        assert "export PLATFORM = asap7" in config
        assert f"export CORNER = {case['corner']}" in config
        assert f"export VERILOG_TOP_PARAMS = {runner.parameter_text(case)}" in config
        assert "fakeram" not in config.lower()
        assert f"set clk_period {case['clock_period_ns'] * 1000:g}" in sdc
        assert f"[get_ports {case['clock_port']}]" in sdc
        assert "set non_clock_inputs [all_inputs -no_clocks]" in sdc
        assert "remove_from_collection" not in sdc
        for reset in case["async_reset_ports"]:
            assert f"set_false_path -from [get_ports {reset}]" in sdc


def test_asap7_report_does_not_promote_missing_cases():
    runner = load_runner()
    lock = runner.strict_json(LOCK)
    report = runner.render_report(lock, {})
    assert "**Overall status:** **PARTIAL**" in report
    assert "0/3" in report
    assert report.count("NOT RUN") == 3
    assert "not foundry signoff" in report


def test_campaign_git_status_is_snapshotted_across_cases(monkeypatch):
    runner = load_runner()
    calls = []

    def fake_run(command, *, cwd, log=None, timeout_seconds=None):
        calls.append(command)
        if command == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(command, 0, "deadbeef\n", "")
        if command[:2] == ["git", "diff"]:
            return subprocess.CompletedProcess(command, 0, "", "")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(runner, "run_command", fake_run)
    state = runner.git_state(
        {"sources": {"rtl/example.sv": "unused"}}, campaign_status=[]
    )
    assert state["worktree_clean"] is True
    assert state["dirty_paths"] == []
    assert ["git", "status", "--short", "--untracked-files=all"] not in calls

    generated = runner.git_state(
        {"sources": {"rtl/example.sv": "unused"}},
        campaign_status=["?? results/asap7_physical/physical.json"],
    )
    assert generated["worktree_clean"] is False
    assert generated["dirty_paths"] == [
        "?? results/asap7_physical/physical.json"
    ]


def test_container_identity_accepts_config_or_manifest_digest_only(monkeypatch):
    """The classic image store reports the config digest, the containerd store
    the manifest digest; both are the locked image, and nothing else is."""
    runner = load_runner()
    lock = runner.strict_json(LOCK)
    container = lock["toolchain"]["container"]

    class ProbeReached(Exception):
        pass

    def fake_run_for(image_id):
        def fake_run(command, *, cwd, log=None, timeout_seconds=None):
            if command[:3] == ["docker", "image", "inspect"]:
                return subprocess.CompletedProcess(command, 0, image_id + "\n", "")
            raise ProbeReached()
        return fake_run

    for image_id in (container["image_id"], container["amd64_digest"]):
        monkeypatch.setattr(runner, "run_command", fake_run_for(image_id))
        with pytest.raises(ProbeReached):
            runner.verify_toolchain(lock)
    monkeypatch.setattr(runner, "run_command", fake_run_for("sha256:" + "0" * 64))
    with pytest.raises(runner.CampaignError, match="container image ID"):
        runner.verify_toolchain(lock)


def test_asap7_lock_rejects_incomplete_or_unhashed_abc_identity():
    runner = load_runner()
    lock = runner.strict_json(LOCK)
    del lock["toolchain"]["abc"]["sha256"]
    with pytest.raises(runner.CampaignError, match="abc lock is incomplete"):
        runner.validate_lock(lock)
    lock = runner.strict_json(LOCK)
    lock["toolchain"]["abc"]["sha256"] = "not-a-hash"
    with pytest.raises(runner.CampaignError, match="abc hash is invalid"):
        runner.validate_lock(lock)


def test_aiger_pair_rejects_ordered_interface_or_latch_mismatch(tmp_path):
    runner = load_runner()
    left = tmp_path / "left.aag"
    right = tmp_path / "right.aag"
    left.write_text("aag 1 1 0 1 0\n2\n2\ni0 a\no0 y\nc\n", encoding="ascii")
    right.write_text("aag 1 1 0 1 0\n2\n2\ni0 b\no0 y\nc\n", encoding="ascii")
    with pytest.raises(runner.CampaignError, match="names differ"):
        runner.validate_aiger_pair(
            "case", "mapped", {
                "gold": runner.aiger_interface(left),
                "gate": runner.aiger_interface(right),
            }
        )
    interface = runner.aiger_interface(left)
    interface["latches"] = 1
    with pytest.raises(runner.CampaignError, match="contains latches"):
        runner.validate_aiger_pair(
            "case", "mapped", {"gold": interface, "gate": dict(interface)}
        )
    reordered = runner.aiger_interface(left)
    reordered["input_names"] = list(reversed(reordered["input_names"]))
    canonical = runner.validate_aiger_pair(
        "case",
        "postroute",
        {"gold": runner.aiger_interface(left), "gate": reordered},
    )
    assert canonical["matching"].startswith("ABC CEC by unique")


def test_equivalence_scripts_reject_state_feedback_and_remaining_sequential_cells():
    runner = load_runner()
    lock = runner.strict_json(LOCK)
    numeric = runner.case_by_name(lock, "numeric_e1_l16_tc")
    nextstate = runner.nextstate_script(
        numeric,
        lock,
        netlist=None,
        state_json="state.json",
        aiger_binary="net.aig",
        aiger_ascii="net.aag",
    )
    transition = runner.transition_aiger_script(
        "ot_reduction_endpoint", "net.json", "net.aig", "net.aag"
    )
    assert nextstate.count("scc -expect 0") == 2
    assert transition.count("scc -expect 0") == 2
    assert runner.SEQUENTIAL_CELL_SELECTION in nextstate
    assert runner.SEQUENTIAL_CELL_SELECTION in transition


def test_equivalence_method_dispatch(monkeypatch, tmp_path):
    runner = load_runner()
    lock = runner.strict_json(LOCK)
    calls = []

    def record_numeric(*args, **kwargs):
        calls.append(("numeric", kwargs["label"]))
        return {"status": "pass"}

    def record_transition(*args, **kwargs):
        calls.append(("transition", kwargs["label"]))
        return {"status": "pass"}

    monkeypatch.setattr(runner, "run_nextstate_equivalence", record_numeric)
    monkeypatch.setattr(runner, "run_transition_equivalence", record_transition)
    runner.run_equivalence(
        runner.case_by_name(lock, "numeric_e1_l16_tc"),
        lock,
        tmp_path,
        label="mapped",
        netlist=tmp_path / "mapped.v",
    )
    runner.run_equivalence(
        runner.case_by_name(lock, "reduction_s8_g2_tc"),
        lock,
        tmp_path,
        label="postroute",
        netlist=tmp_path / "final.v",
    )
    assert calls == [("numeric", "mapped"), ("transition", "postroute")]


def test_reduction_state_relation_requires_exact_declared_optimization():
    runner = load_runner()
    lock = runner.strict_json(LOCK)
    case = runner.case_by_name(lock, "reduction_s8_g2_tc")
    aliases = case["state_aliases"]
    canonical = set(aliases.values())
    ordinary = {"out_valid", "data_mem[0][0]"}
    gold = {name: {} for name in set(aliases) | canonical | ordinary}
    gate = {name: {} for name in canonical | ordinary}
    audit = runner.state_relation_audit(case, gold, gate)
    assert audit["optimized_alias_bits"] == 14
    assert audit["rtl_state_bits"] == audit["mapped_state_bits"] + 14
    gate["undeclared_gate_state"] = {}
    with pytest.raises(runner.CampaignError, match="mapped state differs"):
        runner.state_relation_audit(case, gold, gate)


def test_transition_polarity_bridge_is_explicit():
    runner = load_runner()
    module = {
        "ports": {
            "clk": {"direction": "input", "bits": [2]},
            "out": {"direction": "output", "bits": [4]},
        },
        "cells": {
            "ff": {
                "type": "$dff",
                "connections": {"CLK": [2], "D": [3], "Q": [4]},
            }
        },
        "netnames": {},
    }
    design = {"modules": {"top": module}}
    records = {
        "out": {
            "cell": "ff",
            "cell_bit": 0,
            "q": 4,
            "d": 3,
            "logical_state_inverted": True,
            "physical_module": "DFFHQNx1_ASAP7_75t_R",
        }
    }
    transformed = runner.transition_combinational_json(
        design,
        "top",
        records,
        full_state_names=["out"],
        aliases={},
        functional_contract=[("clk", "input", 1), ("out", "output", 1)],
    )
    result = transformed["modules"]["top"]
    bridges = [
        cell for cell in result["cells"].values()
        if cell.get("attributes", {}).get("transition_polarity_bridge") == "1"
    ]
    assert len(bridges) == 2
    assert not any(cell.get("type") == "$dff" for cell in result["cells"].values())


def test_result_archiver_includes_raw_mapped_netlist(monkeypatch, tmp_path):
    runner = load_runner()
    case_dir = tmp_path / "case"
    result_dir = case_dir / "results"
    report_dir = case_dir / "reports"
    for directory in (case_dir, result_dir, report_dir):
        directory.mkdir(parents=True, exist_ok=True)
    for name in ("1_2_yosys.v", "6_final.def", "6_final.gds", "6_final.odb", "6_final.sdc", "6_final.spef", "6_final.v"):
        (result_dir / name).write_text(name, encoding="utf-8")
    for name in ("metadata.json", "6_finish.rpt", "5_route_drc.rpt"):
        (report_dir / name).write_text(name, encoding="utf-8")
    for name in (
        "config.mk",
        "constraint.sdc",
        "1_2_yosys.raw.v",
        "openroad_synthesis.log",
        "openroad_flow.log",
        "unconstrained_check.tcl",
        "unconstrained_check.log",
        "unconstrained_endpoints.rpt",
    ):
        (case_dir / name).write_text(name, encoding="utf-8")
    monkeypatch.setattr(runner, "RESULT_ROOT", tmp_path / "archive")
    archived = runner.copy_result_artifacts(
        {"name": "case"}, case_dir, result_dir, report_dir
    )
    assert "1_2_yosys.raw.v" in archived
    assert (tmp_path / "archive" / "case" / "artifacts" / "1_2_yosys.raw.v").is_file()


def test_a_routed_record_with_slew_violations_is_not_closed(tmp_path):
    """Signal-integrity violations refuse closure, and are named.

    An LQ8 route at asap7 was recorded closed=true with 292 max-slew
    violations because the driver read setup, hold, DRC and antenna from the
    ORFS report and never the DRV block beside them.  The verdict must read
    all three DRV counts and refuse to close on any nonzero one.
    """
    import json
    from tools import run_abi3_physical as drv

    metrics = {
        "setup_wns_ns": 1.0, "hold_wns_ns": 0.1, "drc_errors": 0,
        "antenna_violating_nets": 0, "antenna_violating_pins": 0,
        "max_slew_violations": 292, "max_cap_violations": 0, "max_fanout_violations": 0,
        "fmax_hz": 1e8, "standard_cell_count": 10, "standard_cell_area_um2": 1.0,
        "core_area_um2": 2.0, "utilization_fraction": 0.5,
    }
    record = {
        "status": drv.STATUS_PASS,
        "place_and_route": {"metrics": metrics, "clock_period_ns": 16.0},
        "design": {},
    }
    drv.augment_design(record, lanes=None, mac_per_cycle=None, evidence=[], lane_regex=None, netlists=[])
    design = record["design"]
    assert design["signal_integrity_violations"]["max_slew_violations"] == 292
    assert design["signal_integrity_clean"] is False
    assert design["closed"] is False
    assert "max_slew_violations 292" in design["closed_reason"]


def test_archived_records_match_the_lock_or_are_declared_stale():
    """A stale hash in the lock would bind routed evidence to RTL it was not
    produced from.  The lock names the CURRENT sources; an archived record made
    from anything else must be declared stale there, and must not be counted."""
    runner = load_runner()
    lock = runner.strict_json(LOCK)
    completed = runner.load_completed(lock)
    aggregate = runner.strict_json(ROOT / "results" / "asap7_physical" / "physical.json")
    for case in lock["cases"]:
        record = completed.get(case["name"])
        if record is None:
            continue
        if runner.record_is_current(case, record):
            assert "archived_evidence" not in case, case["name"]
            assert case["name"] not in aggregate.get("stale_cases", [])
            continue
        archived = case.get("archived_evidence")
        assert archived is not None, f"{case['name']}: stale record not declared"
        assert archived["record_sources"] == runner.record_sources(record)
        assert case["name"] in aggregate["stale_cases"]
        assert aggregate["all_pass"] is False
        assert aggregate["all_canonical"] is False
    report = runner.render_report(lock, completed)
    assert report == (ROOT / "results" / "asap7_physical" / "REPORT.md").read_text(
        encoding="utf-8"
    )


def test_stale_record_is_never_reported_as_pass():
    runner = load_runner()
    lock = runner.strict_json(LOCK)
    completed = runner.load_completed(lock)
    case = runner.case_by_name(lock, "reduction_s8_g2_tc")
    record = dict(completed["reduction_s8_g2_tc"])
    record["source_inventory"] = [
        {"path": path, "sha256": "0" * 64} for path in case["sources"]
    ]
    report = runner.render_report(lock, {**completed, case["name"]: record})
    assert "**Overall status:** **PARTIAL**" in report
    assert "| `reduction_s8_g2_tc` | STALE |" in report
    with pytest.raises(runner.CampaignError, match="must be 'stale'"):
        runner.validate_archived_evidence(
            {**case, "archived_evidence": {**case["archived_evidence"], "status": "current"}}
        )
    with pytest.raises(runner.CampaignError, match="matches the lock"):
        runner.validate_archived_evidence(
            {
                **case,
                "archived_evidence": {
                    **case["archived_evidence"],
                    "record_sources": dict(case["sources"]),
                },
            }
        )
