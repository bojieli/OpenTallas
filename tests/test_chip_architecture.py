"""Independent arithmetic and refusal checks for the physical design contract."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from opentallas.chip_architecture import (
    ArchitectureError, path_rate, pipeline_stages, qwen_resource_plan, qwen_units, reduction_service,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs():
    config = json.loads((ROOT / "configs/architecture/chip_design_v2.json").read_text())
    model = json.loads((ROOT / config["qwen"]["model"]).read_text())
    return config, model


def test_stage_plan_covers_checkpoint_and_counts_real_kv_owners(inputs):
    config, model = inputs
    stages = pipeline_stages(qwen_units(model), config["qwen"]["pipeline_stage_last_unit"])
    assert sum(s["weight_bytes"] for s in stages) == 16_381_470_720
    assert [s["kv_layers"] for s in stages] == [6, 8, 9, 8, 5]
    # The largest KV owner is not the largest weight owner.
    assert stages[2]["weight_bytes"] < stages[1]["weight_bytes"]


def test_old_average_kv_allocation_is_rejected(inputs):
    config, model = inputs
    config["qwen"]["profiles"][1]["kv_capacity_bytes_per_die"] = 241_600_000
    with pytest.raises(ArchitectureError, match="KV .* exceeds per-die"):
        qwen_resource_plan(config, model)


def test_repaired_memory_and_phy_fit_on_both_twins(inputs):
    report = qwen_resource_plan(*inputs)
    for p in report["profiles"]:
        assert p["total_area_mm2"] <= 815
        # Opening a new cluster also reserves reduction endpoints and their buffers.
        assert 0 <= p["unused_area_mm2"] < inputs[0]["tensor_tile_mm2"] + .05
        assert p["rom_raw_capacity_bytes_per_die"] * .98 >= p["rom_payload_budget_bytes"]
        assert p["hbm_twin_replacement_sram_area_mm2"] >= 0
        if p["id"] != "qwen_x4":
            assert max(s["kv_bytes"] for s in p["stages"]) <= p["kv_capacity_bytes_per_die"]
    assert report["production_ready"] is False
    assert all(p["qualified_tpot_us"] is None for p in report["profiles"])


def test_kv_rate_is_capped_by_the_delivery_network(inputs):
    p = qwen_resource_plan(*inputs)["profiles"][1]
    assert p["kv_source_bytes_per_cycle"] == 26_112
    assert p["kv_delivered_bytes_per_cycle"] == 4_608
    assert p["kv_service_lower_bound_us"] == pytest.approx(262.144)
    assert max(s["kv_bytes"] for s in p["stages"]) == 304_349_184
    assert not p["prefetch_overlap_credited"]
    # Tensor-parallel shards transfer concurrently: do not accidentally add them.
    assert qwen_resource_plan(*inputs)["profiles"][2]["kv_service_lower_bound_us"] == pytest.approx(32.768)


def test_slowing_any_service_boundary_cannot_improve_delivery(inputs):
    config, model = inputs
    original = qwen_resource_plan(config, model)["profiles"][1]
    config["sdn_bytes_per_cycle"] = 1024
    changed = qwen_resource_plan(config, model)["profiles"][1]
    assert changed["kv_service_lower_bound_us"] == pytest.approx(original["kv_service_lower_bound_us"] * 4.5)
    assert path_rate(128, 32, 64) == 32
    with pytest.raises(ArchitectureError):
        path_rate(128, 0)


def test_all_profiles_fit_shared_mesh_and_coordinate_encoding(inputs):
    config, model = inputs
    for p in qwen_resource_plan(config, model)["profiles"]:
        assert max(p["rom_endpoints"], p["hbm_twin_endpoints"]) <= p["mesh_shape"][0] * p["mesh_shape"][1]
    config["qwen"]["profiles"][2].update(mesh_x=12, mesh_y=12)
    with pytest.raises(ArchitectureError, match="endpoints exceed"):
        qwen_resource_plan(config, model)


def test_mesh_growth_is_charged_to_area(inputs):
    config, model = inputs
    before = qwen_resource_plan(config, model)["profiles"][0]
    config["qwen"]["profiles"][0].update(mesh_x=16, mesh_y=16)
    after = qwen_resource_plan(config, model)["profiles"][0]
    assert after["mesh_area_mm2"] > before["mesh_area_mm2"]
    assert after["tiles"] < before["tiles"]


def test_link_internal_width_limits_phy_throughput(inputs):
    link = qwen_resource_plan(*inputs)["link"]
    assert link["bytes_per_cycle_per_endpoint"] == 64
    assert link["bytes_per_cycle_aggregate"] == 512
    assert link["expert_48k_payload_serialization_cycles"] == 768


@pytest.mark.parametrize("cuts", [[], ["head", "head"], ["layer.99.attention"], ["layer.5.attention"]])
def test_invalid_pipeline_plan_cannot_drop_or_duplicate_units(inputs, cuts):
    with pytest.raises(ArchitectureError):
        pipeline_stages(qwen_units(inputs[1]), cuts)


def test_changed_checkpoint_cannot_reuse_old_placement(inputs):
    config, model = deepcopy(inputs)
    model["checkpoint_bytes"] += 1
    with pytest.raises(ArchitectureError, match="exact checkpoint"):
        qwen_resource_plan(config, model)


def test_mxfp4_cannot_overrun_scalar_reduction_or_ignore_scales(inputs):
    service = reduction_service(inputs[0], bits_per_weight=4, group=4)
    assert service["weight_bytes"] == 4096
    assert service["scale_bytes"] == 256
    assert service["weight_port_cycles"] == 34
    assert service["lane_compute_cycles"] == 32
    assert service["reduction_vector_service_cycles"] == 64
    assert service["minimum_pass_initiation_interval"] == 64
    assert service["last_result_offset_from_first_cycles"] == 63


def test_tree_cannot_claim_uninstantiated_simd_width(inputs):
    inputs[0]["reduction"]["columns_per_cycle"] = 2
    with pytest.raises(ArchitectureError, match="instantiated adders"):
        reduction_service(inputs[0], bits_per_weight=4, group=4)


def test_fp8_scales_are_not_a_free_side_port(inputs):
    service = reduction_service(inputs[0], bits_per_weight=8, group=2)
    assert service["weight_bytes"] == 8192
    assert service["scale_bytes"] == 1
    assert service["minimum_pass_initiation_interval"] == 65


@pytest.mark.parametrize("section,key,value", [
    ("dependence", "overflow_policy", "drop_fifth_object"),
    ("dependence", "frontier_streaming", True),
    ("numeric", "am_e7_enabled", True),
    ("numeric", "grouped_bf16_supported", True),
    ("numeric", "external_oracle_required", False),
])
def test_unproved_execution_features_cannot_enter_the_plan(inputs, section, key, value):
    inputs[0][section][key] = value
    with pytest.raises(ArchitectureError):
        qwen_resource_plan(*inputs)


def test_physical_snapshot_tracks_source_edits_and_full_verdict(tmp_path):
    import hashlib
    from tools.check_chip_architecture import physical_summary
    source = tmp_path / 'lane.sv'
    source.write_text('module lane; endmodule\n')
    record = {'status': 'not_met', 'design': {
        'sources': [{'path': 'lane.sv', 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}],
        'closed': False, 'closed_reason': 'max_slew_violations 292', 'clock_period_ns': 16,
        'signal_integrity_violations': {'max_slew_violations': 292}},
        'place_and_route': {'metrics': {'standard_cell_area_um2': 100, 'core_area_um2': 300,
                                      'setup_wns_ns': 8.74, 'drc_errors': 0}}}
    (tmp_path / 'pnr.json').write_text(json.dumps(record))
    snapshot = physical_summary(tmp_path, 'pnr.json')
    assert snapshot['source_current'] and not snapshot['closed']
    assert snapshot['standard_cell_area_um2'] == 100
    assert snapshot['core_area_um2'] == 300
    assert snapshot['signal_integrity_violations']['max_slew_violations'] == 292
    source.write_text('module changed; endmodule\n')
    snapshot = physical_summary(tmp_path, 'pnr.json')
    assert not snapshot['source_current'] and snapshot['mismatched_sources'] == ['lane.sv']
    source.unlink()
    assert not physical_summary(tmp_path, 'pnr.json')['source_current']
    assert physical_summary(tmp_path, 'missing.json')['status'] == 'missing'


def test_report_check_detects_tampered_json_and_markdown(tmp_path):
    import subprocess
    import sys
    command = [sys.executable, str(ROOT / 'tools/check_chip_architecture.py')]
    retained = tmp_path / 'report.json'
    prose = tmp_path / 'report.md'
    assert subprocess.run([*command, '--output', str(retained), '--markdown', str(prose)],
                          capture_output=True).returncode == 0
    check = [*command, '--check', str(retained), '--check-markdown', str(prose)]
    assert subprocess.run(check, capture_output=True).returncode == 0
    original = retained.read_text()
    retained.write_text('{}\n')
    assert subprocess.run(check, capture_output=True).returncode == 1
    retained.write_text(original)
    prose.write_text(prose.read_text().replace('262.144', '46.4'))
    assert subprocess.run(check, capture_output=True).returncode == 1
