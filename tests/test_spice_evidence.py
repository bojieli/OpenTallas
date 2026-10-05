from __future__ import annotations

import json
import hashlib
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def test_open_pdk_contracts_validate_without_tools() -> None:
    runners = (
        "spice/run_sky130_rom_read.py",
        "tools/run_sky130_physical.py",
        "tools/run_sky130_extracted_pvt.py",
        "tools/run_sky130_extracted_mismatch.py",
        "tools/run_sky130_resistance.py",
        "tools/run_ihp_device_smoke.py",
        "tools/run_ihp_physical.py",
        "tools/run_ihp_extracted_pvt.py",
        "tools/run_ihp_resistance.py",
    )
    for runner in runners:
        completed = subprocess.run(
            ["python3", str(ROOT / runner), "--validate-only"],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
        assert completed.returncode == 0, completed.stdout
        assert "PASS" in completed.stdout


def test_ihp_device_smoke_is_replayed_locked_and_strictly_bounded() -> None:
    result = load("results/spice/ihp_device_smoke/device_smoke.json")
    lock = load("configs/pdk/ihp_sg13g2_physical_lock.json")

    assert result["status"] == "pass"
    assert result["pdk"]["status"] == "pass"
    assert result["pdk"]["root_commit"] == lock["pdk"]["commit"]
    assert result["pdk"]["submodules"] == lock["pdk"]["submodules"]
    assert result["pdk"]["tree"]["payload_entries"] == 5121
    assert result["pdk"]["tree"]["regular_files"] == 5120
    assert result["pdk"]["tree"]["symlinks"] == 1
    assert result["pdk"]["tree"]["gitlinks"] == 5
    assert result["pdk"]["tree"]["manifest_sha256"] == lock["pdk"][
        "installed_tree"
    ]["manifest_sha256"]

    compilation = result["model_compilation"]
    assert compilation["define"] == "__NGSPICE__"
    assert compilation["target_cpu"] == "generic"
    assert compilation["semantic_replay"]["status"] == "pass"
    assert set(compilation["primary"]) == set(lock["osdi_models"]["models"])
    assert set(compilation["replay"]) == set(lock["osdi_models"]["models"])
    for name, expected in lock["osdi_models"]["models"].items():
        primary = compilation["primary"][name]
        replay = compilation["replay"][name]
        assert primary["source_sha256"] == expected["source_sha256"]
        assert primary["output_sha256"] == expected["output_sha256"]
        assert replay["output_sha256"] == expected["output_sha256"]
        assert primary["output_size_bytes"] == expected["output_size_bytes"]
        assert replay["output_size_bytes"] == expected["output_size_bytes"]
        assert compilation["semantic_replay"]["models"][name] == {
            "byte_identical": True,
            "sha256": expected["output_sha256"],
        }

    simulation = result["simulation"]
    assert simulation["status"] == "pass"
    assert simulation["official_subcircuits"] == [
        "sg13_lv_nmos",
        "sg13_lv_pmos",
    ]
    assert simulation["model_corner"] == "mos_tt"
    assert simulation["supply_v"] == 1.2
    assert simulation["temperature_c"] == 27
    metrics = simulation["metrics"]
    assert 1.19 <= metrics["dc_out_low_v"] <= 1.200001
    assert -1e-6 <= metrics["dc_out_high_v"] <= 1e-3
    assert -1e-6 <= metrics["tran_out_low_v"] <= 1e-3
    assert 1.19 <= metrics["tran_out_high_v"] <= 1.200001
    assert 0 < metrics["tphl_s"] <= 1e-9
    assert 0 < metrics["tplh_s"] <= 1e-9
    assert simulation["unexpected_errors"] == []

    for input_record in result["inputs"].values():
        assert input_record["sha256"] == sha256(ROOT / input_record["path"])
    for artifact in result["artifacts"]:
        path = ROOT / artifact["path"]
        assert path.is_file()
        assert path.stat().st_size == artifact["size_bytes"]
        assert sha256(path) == artifact["sha256"]

    boundary = result["claim_boundary"]
    assert boundary["target_node_scaling_rule"] is None
    assert boundary["target_node_scaling_status"] == "prohibited"
    forbidden = " ".join(boundary["forbidden_inferences"])
    assert "ROM topology" in forbidden
    assert "N7 or N4" in forbidden
    assert "GPU speedup" in forbidden
    assert "silicon" in forbidden


def test_ihp_physical_replication_is_unique_port_complete_and_hash_bound() -> None:
    result = load("results/spice/ihp_sg13g2_physical/physical.json")
    lock = load("configs/pdk/ihp_sg13g2_physical_lock.json")

    assert result["status"] == "pass"
    assert result["verification"]["drc"] == {"errors": 0, "status": "pass"}
    assert result["verification"]["lvs"]["final_result"] == (
        "Circuits match uniquely."
    )
    assert result["verification"]["lvs"]["pin_lists_equivalent"] is True
    topology = result["metrics"]["topology"]
    assert topology["device_count"] == 10
    assert topology["device_counts"] == {
        "sg13_lv_nmos": 6,
        "sg13_lv_pmos": 4,
    }
    assert topology["net_count"] == 15
    assert len(topology["ports"]) == len(set(topology["ports"])) == 10
    assert topology["programmed_row_device"]["nodes_dgsb"][2] == "BL_PRESENT"
    assert topology["unprogrammed_row_device"]["nodes_dgsb"][2] == (
        "ROM_DRAIN_ABSENT"
    )
    assert result["metrics"]["layout"]["programming_via1"] == {
        "absent_column_count": 5,
        "delta": 1,
        "present_column_count": 6,
    }
    assert result["metrics"]["parasitics"]["capacitance_element_count"] == 59
    assert result["pdk"]["tree"]["manifest_sha256"] == lock["pdk"][
        "installed_tree"
    ]["manifest_sha256"]
    assert result["contract"]["sha256"] == sha256(ROOT / result["contract"]["path"])
    for input_record in result["inputs"].values():
        assert input_record["sha256"] == sha256(ROOT / input_record["path"])
    assert len(result["artifacts"]) == 12
    for artifact in result["artifacts"]:
        path = ROOT / artifact["path"]
        assert path.is_file()
        assert path.stat().st_size == artifact["size_bytes"]
        assert sha256(path) == artifact["sha256"]

    boundary = result["claim_boundary"]
    assert boundary["target_node_scaling_rule"] is None
    assert boundary["target_node_scaling_status"] == "prohibited"
    forbidden = " ".join(boundary["forbidden_inferences"])
    assert "N7 or N4" in forbidden
    assert "GPU speedup" in forbidden
    assert "silicon correlation" in forbidden


def test_ihp_extracted_pvt_is_complete_official_model_and_physically_bound() -> None:
    result = load("results/spice/ihp_sg13g2_extracted_pvt.json")
    physical_path = ROOT / "results/spice/ihp_sg13g2_physical/physical.json"
    physical = load("results/spice/ihp_sg13g2_physical/physical.json")

    assert result["status"] == "pass"
    assert result["summary"]["cases_total"] == 33
    assert result["summary"]["cases_passed"] == 33
    assert result["summary"]["cases_failed"] == 0
    assert len(result["cases"]) == 33
    assert all(case["status"] == "pass" for case in result["cases"])
    assert all(not case["unexpected_warnings"] for case in result["cases"])
    assert result["summary"]["expected_benign_warning_counts"] == {
        "m=xx on .subckt line will override multiplier m hierarchy!": 33
    }
    assert result["pdk"]["corner_sections"] == {
        "ff": "mos_ff",
        "ss": "mos_ss",
        "tt": "mos_tt",
    }
    assert len(result["toolchain"]["osdi_modules"]) == 4
    assert result["upstream_physical"]["sha256"] == sha256(physical_path)
    pex = next(
        artifact
        for artifact in physical["artifacts"]
        if artifact["path"].endswith("ihp_sg13g2_rom_slice.pex.spice")
    )
    assert result["upstream_physical"]["pex_sha256"] == pex["sha256"]
    assert result["upstream_physical"]["pdk_tree_manifest_sha256"] == physical[
        "pdk"
    ]["tree"]["manifest_sha256"]
    for record_name in ("runner", "contract", "template", "spice_init"):
        record = result[record_name]
        assert record["sha256"] == sha256(ROOT / record["path"])
    assert result["claim_boundary"]["target_node_scaling_rule"] is None
    assert result["claim_boundary"]["target_node_scaling_status"] == "prohibited"


def test_ihp_detailed_rc_is_replayed_complete_and_locally_bounded() -> None:
    result = load("results/spice/ihp_sg13g2_resistance/resistance.json")
    physical_path = ROOT / "results/spice/ihp_sg13g2_physical/physical.json"
    pvt_path = ROOT / "results/spice/ihp_sg13g2_extracted_pvt.json"
    styles = {
        "nominal",
        "high_r_high_c",
        "high_r_low_c",
        "low_r_high_c",
        "low_r_low_c",
    }

    assert result["status"] == "pass"
    electrical = result["summary"]["electrical"]
    assert electrical["cases_total"] == 165
    assert electrical["cases_passed"] == 165
    assert electrical["cases_failed"] == 0
    assert electrical["unexpected_warning_counts"] == {}
    assert len(result["cases"]) == 165
    assert all(case["status"] == "pass" for case in result["cases"])
    assert all(not case["unexpected_warnings"] for case in result["cases"])

    extraction = result["summary"]["extraction"]
    assert set(extraction["by_style"]) == styles
    assert extraction["styles_total"] == 5
    assert extraction["styles_passed_semantic_replay"] == 5
    for style_id, item in extraction["by_style"].items():
        assert item["replay"]["status"] == "pass"
        assert item["metrics"]["devices"] == {
            "count": 10,
            "model_counts": {"sg13_lv_nmos": 6, "sg13_lv_pmos": 4},
        }
        assert item["metrics"]["resistors"]["count"] == 41
        assert item["metrics"]["capacitors"]["count"] == 68
        connectivity = item["metrics"]["connectivity"]
        for key in (
            "present_required_connected",
            "present_forbidden_disconnected",
            "absent_required_connected",
            "absent_forbidden_disconnected",
            "program_states_are_disjoint",
        ):
            assert connectivity[key] is True
        body_paths = item["metrics"]["nmos_body_paths"]
        assert body_paths["count"] == 6
        assert body_paths["all_nmos_bodies_are_non_ground_nodes"] is True
        assert body_paths["non_ground_body_count_matches"] is True
        assert body_paths["all_body_components_reach_ground"] is True
        assert item["magic"]["feedback_error_count"] == 0
        assert item["magic"]["feedback_errors"] == []
        assert item["metrics"]["semantic_sha256"] == item["replay"][
            "semantic_sha256"
        ]
        assert len(
            [case for case in result["cases"] if case["style_id"] == style_id]
        ) == 33

    nominal = electrical["by_style"]["nominal"]["nominal_case"]
    assert nominal["metrics"]["discharge_delay_ns"] > nominal["baseline_metrics"][
        "discharge_delay_ns"
    ]
    assert electrical["global_max_discharge_delay_ns"]["value"] == max(
        case["metrics"]["discharge_delay_ns"] for case in result["cases"]
    )
    assert result["upstream"]["physical"]["sha256"] == sha256(physical_path)
    assert result["upstream"]["deterministic_pvt"]["sha256"] == sha256(pvt_path)
    assert result["runner"]["sha256"] == sha256(ROOT / result["runner"]["path"])
    assert result["contract"]["sha256"] == sha256(ROOT / result["contract"]["path"])
    assert result["template"]["sha256"] == sha256(ROOT / result["template"]["path"])
    assert result["spice_init"]["sha256"] == sha256(
        ROOT / result["spice_init"]["path"]
    )
    for dependency in result["dependencies"].values():
        assert dependency["sha256"] == sha256(ROOT / dependency["path"])
    assert len(result["artifacts"]) == 50
    assert len({artifact["path"] for artifact in result["artifacts"]}) == 50
    for artifact in result["artifacts"]:
        path = ROOT / artifact["path"]
        assert path.is_file()
        assert path.stat().st_size == artifact["size_bytes"]
        assert sha256(path) == artifact["sha256"]

    boundary = result["claim_boundary"]
    assert boundary["target_node_scaling_rule"] is None
    assert boundary["target_node_scaling_status"] == "prohibited"
    forbidden = " ".join(boundary["forbidden_inferences"])
    assert "full-array" in forbidden
    assert "N7 or N4" in forbidden
    assert "GPU speedup" in forbidden
    assert "silicon correlation" in forbidden


def test_physical_result_closes_only_declared_local_gates() -> None:
    result = load("results/spice/sky130_physical/physical.json")
    assert result["status"] == "pass"
    assert result["verification"]["drc"] == {"errors": 0, "status": "pass"}
    assert result["verification"]["lvs"]["final_result"] == "Circuits match uniquely."
    assert result["verification"]["lvs"]["pin_lists_equivalent"] is True
    assert result["metrics"]["topology"]["device_count"] == 10
    assert result["metrics"]["topology"]["net_count"] == 15
    assert len(result["metrics"]["topology"]["ports"]) == 10
    assert result["metrics"]["layout"]["programming_via1"] == {
        "absent_column_count": 5,
        "delta": 1,
        "present_column_count": 6,
    }
    assert result["metrics"]["parasitics"]["capacitance_element_count"] == 59
    assert result["claim_boundary"]["target_node_scaling_rule"] is None
    assert result["claim_boundary"]["target_node_scaling_status"] == "prohibited"
    assert "not_a_ROM_cell_density" in result["metrics"]["layout"][
        "footprint_density_status"
    ]
    for artifact in result["artifacts"]:
        path = ROOT / artifact["path"]
        assert path.is_file()
        assert path.stat().st_size == artifact["size_bytes"]
        assert sha256(path) == artifact["sha256"]


def test_extracted_pvt_result_is_complete_and_bound_to_physical_pex() -> None:
    result = load("results/spice/sky130_extracted_pvt.json")
    physical = load("results/spice/sky130_physical/physical.json")
    assert result["status"] == "pass"
    assert result["summary"]["cases_total"] == 33
    assert result["summary"]["cases_passed"] == 33
    assert result["summary"]["cases_failed"] == 0
    assert all(case["status"] == "pass" for case in result["cases"])
    assert all(not case["unexpected_warnings"] for case in result["cases"])
    assert result["claim_boundary"]["target_node_scaling_rule"] is None
    pex = next(
        artifact
        for artifact in physical["artifacts"]
        if artifact["path"].endswith("sky130_rom_slice.pex.spice")
    )
    assert result["upstream_physical"]["pex_sha256"] == pex["sha256"]
    assert result["upstream_physical"]["pdk_tree_manifest_sha256"] == physical["pdk"][
        "tree"
    ]["manifest_sha256"]


def test_extracted_mismatch_result_is_reproducible_and_not_a_yield_claim() -> None:
    result = load("results/spice/sky130_extracted_mismatch.json")
    physical = load("results/spice/sky130_physical/physical.json")
    deterministic = load("results/spice/sky130_extracted_pvt.json")
    assert result["status"] == "pass"
    assert result["summary"]["samples_total"] == 256
    assert result["summary"]["samples_passed"] == 256
    assert result["summary"]["samples_failed"] == 0
    assert result["summary"]["valid_measure_vectors"] == 256
    assert result["summary"]["failure_reason_counts"] == {}
    assert result["summary"]["unexpected_warning_counts"] == {}
    assert all(sample["status"] == "pass" for sample in result["samples"])
    assert all(not sample["unexpected_warnings"] for sample in result["samples"])

    seeds = [sample["seed"] for sample in result["samples"]]
    assert len(seeds) == len(set(seeds)) == 256
    assert [sample["sample_index"] for sample in result["samples"]] == list(range(256))
    seed_list_text = "".join(
        f"{sample['sample_index']}:{sample['seed']}\n" for sample in result["samples"]
    )
    assert hashlib.sha256(seed_list_text.encode("utf-8")).hexdigest() == result[
        "input_model"
    ]["sampling"]["ordered_seed_list_sha256"]
    assert all(
        sample["seed_control"]["netlist_option"] == f".option seed={sample['seed']}"
        for sample in result["samples"]
    )

    replay = result["summary"]["same_seed_replay"]
    assert replay["status"] == "pass"
    assert replay["maximum_abs_measure_delta_si"] == 0
    assert all(delta == 0 for delta in replay["all_measure_deltas_si"].values())
    assert result["samples"][0]["deck_sha256"] == result["replay"]["deck_sha256"]
    variation = result["summary"]["variation_detection"]
    assert variation["status"] == "pass"
    assert variation["distinct_discharge_delay_values"] >= 2
    assert variation["distinct_read_margin_values"] >= 2

    activation = result["pdk"]["mismatch_activation"]
    assert activation["mc_mm_switch"] == 1
    assert activation["mc_pr_switch"] == 0
    assert activation["mismatch_expression_total"] > 0
    assert result["upstream"]["physical"]["pex_sha256"] == next(
        artifact["sha256"]
        for artifact in physical["artifacts"]
        if artifact["path"].endswith("sky130_rom_slice.pex.spice")
    )
    assert result["upstream"]["deterministic_pvt"]["sha256"] == sha256(
        ROOT / "results/spice/sky130_extracted_pvt.json"
    )
    assert result["upstream"]["physical"]["sha256"] == deterministic[
        "upstream_physical"
    ]["sha256"]
    assert result["claim_boundary"]["target_node_scaling_rule"] is None
    assert result["claim_boundary"]["target_node_scaling_status"] == "prohibited"
    assert any(
        "silicon yield" in boundary
        for boundary in result["claim_boundary"]["forbidden_inferences"]
    )
    assert result["runner"]["sha256"] == sha256(
        ROOT / result["runner"]["path"]
    )
    assert result["contract"]["sha256"] == sha256(
        ROOT / result["contract"]["path"]
    )
    assert result["template"]["sha256"] == sha256(
        ROOT / result["template"]["path"]
    )


def test_distributed_rc_result_is_complete_replayed_and_locally_bounded() -> None:
    result = load("results/spice/sky130_resistance/resistance.json")
    physical_path = ROOT / "results/spice/sky130_physical/physical.json"
    pvt_path = ROOT / "results/spice/sky130_extracted_pvt.json"
    styles = {
        "nominal",
        "high_r_high_c",
        "high_r_low_c",
        "low_r_high_c",
        "low_r_low_c",
    }

    assert result["status"] == "pass"
    electrical = result["summary"]["electrical"]
    assert electrical["cases_total"] == 165
    assert electrical["cases_passed"] == 165
    assert electrical["cases_failed"] == 0
    assert electrical["unexpected_warning_counts"] == {}
    assert len(result["cases"]) == 165
    assert all(case["status"] == "pass" for case in result["cases"])
    assert all(not case["unexpected_warnings"] for case in result["cases"])

    extraction = result["summary"]["extraction"]
    assert set(extraction["by_style"]) == styles
    assert extraction["styles_total"] == 5
    assert extraction["styles_passed_semantic_replay"] == 5
    for style_id, item in extraction["by_style"].items():
        assert item["replay"]["status"] == "pass"
        assert item["metrics"]["devices"]["count"] == 10
        assert item["metrics"]["resistors"]["count"] == 630
        assert item["metrics"]["capacitors"]["count"] == 269
        assert all(item["metrics"]["connectivity"].values())
        style_cases = [
            case for case in result["cases"] if case["style_id"] == style_id
        ]
        assert len(style_cases) == 33
        assert item["metrics"]["semantic_sha256"] == item["replay"][
            "semantic_sha256"
        ]

    nominal = electrical["by_style"]["nominal"]["nominal_case"]
    assert nominal["metrics"]["discharge_delay_ns"] > nominal["baseline_metrics"][
        "discharge_delay_ns"
    ]
    assert electrical["global_max_discharge_delay_ns"]["value"] == max(
        case["metrics"]["discharge_delay_ns"] for case in result["cases"]
    )

    assert result["upstream"]["physical"]["sha256"] == sha256(physical_path)
    assert result["upstream"]["deterministic_pvt"]["sha256"] == sha256(pvt_path)
    assert result["runner"]["sha256"] == sha256(ROOT / result["runner"]["path"])
    assert result["contract"]["sha256"] == sha256(ROOT / result["contract"]["path"])
    assert result["template"]["sha256"] == sha256(ROOT / result["template"]["path"])
    for dependency in result["dependencies"].values():
        assert dependency["sha256"] == sha256(ROOT / dependency["path"])
    for artifact in result["artifacts"]:
        path = ROOT / artifact["path"]
        assert path.is_file()
        assert path.stat().st_size == artifact["size_bytes"]
        assert sha256(path) == artifact["sha256"]

    boundary = result["claim_boundary"]
    assert boundary["target_node_scaling_rule"] is None
    assert boundary["target_node_scaling_status"] == "prohibited"
    forbidden = " ".join(boundary["forbidden_inferences"])
    assert "full-array" in forbidden
    assert "N7 or N4" in forbidden
    assert "GPU speedup" in forbidden
    assert "silicon correlation" in forbidden


def test_schematic_only_sky130_sweep_is_now_clean_but_remains_synthetic() -> None:
    result = load("results/spice/sky130_rom_read.json")
    assert result["status"] == "pass"
    assert result["summary"]["cases_total"] == 51
    assert result["summary"]["cases_passed"] == 51
    assert all(not case["warnings"] for case in result["cases"])
    assert result["input_model"]["netlist"]["parasitic_status"] == (
        "synthetic_lumped_capacitance_not_extracted_layout"
    )
    assert result["claim_boundary"]["target_node_scaling_rule"] is None
