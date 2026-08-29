from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil

from jsonschema import Draft202012Validator
import pytest

from compiler.tensor_accelerator.common import canonical_json_bytes, load_strict_json
from tools import collect_qwen3_ta_rtl_physical_campaign as campaign


ROOT = Path(__file__).resolve().parents[2]
REPORT = (
    ROOT / "results/tensor_accelerator/qwen3_rtl_ihp_sg13g2_physical_campaign.json"
)
SCHEMA = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_physical_campaign_v1.schema.json"
)
LOCK = ROOT / "physical/ihp_sg13g2_qwen_rtl/add_sram/toolchain.lock.json"
CONFIG = ROOT / "physical/ihp_sg13g2_qwen_rtl/add_sram/config.mk"
SDC = ROOT / "physical/ihp_sg13g2_qwen_rtl/add_sram/constraint.sdc"
EXPECTED_CAMPAIGN_ID = (
    "0af6cbe8da22330c466a5ab1fc5de9c245e97c8375cac42fb8b9451c3b40b316"
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _identity(value: dict[str, object], field: str) -> str:
    body = {key: item for key, item in value.items() if key != field}
    return _sha256(canonical_json_bytes(body))


def _metrics_pairs() -> list[tuple[str, int | float]]:
    values: dict[str, int | float] = {name: 0 for name in campaign.SELECTED_METRICS}
    values.update(
        {
            "finish__design__core__area": 1000.0,
            "finish__design__die__area": 1200.0,
            "finish__design__instance__area__stdcell": 200.0,
            "finish__design__instance__count__stdcell": 20,
            "finish__design__instance__utilization__stdcell": 0.2,
            "finish__design__io": 10,
            "finish__design__nets": 30,
            "finish__timing__fmax__clock:core_clock": 50_000_000.0,
            "finish__timing__hold__ws": 0.1,
            "finish__timing__setup__ws": 1.0,
        }
    )
    pairs = list(values.items())
    for key, count in campaign.ALLOWED_ORFS_DUPLICATES.items():
        pairs.extend((key, float(index)) for index in range(count))
    return pairs


def _write_pairs(path: Path, pairs: list[tuple[str, int | float]]) -> None:
    fields = [f"{json.dumps(key)}:{json.dumps(value)}" for key, value in pairs]
    path.write_text("{" + ",".join(fields) + "}\n", encoding="utf-8")


def _routing_fixture(tmp_path: Path) -> tuple[Path, Path]:
    reports = tmp_path / "reports"
    logs = tmp_path / "logs"
    reports.mkdir()
    logs.mkdir()
    (reports / "5_route_drc.rpt").write_bytes(b"")
    (reports / "drt_antennas.log").write_bytes(b"")
    (reports / "grt_antennas.log").write_bytes(b"")
    (logs / "5_2_route.log").write_text(
        "[INFO DRT-0199]   Number of violations = 0.\n"
        "Total wire length = 1234 um.\n"
        "Total number of vias = 567.\n"
        "[INFO ANT-0002] Found 0 net violations.\n"
        "[INFO ANT-0001] Found 0 pin violations.\n",
        encoding="utf-8",
    )
    (logs / "6_1_merge.log").write_text(
        "KLayout 0.30.7\n"
        "[INFO] All LEF cells have matching GDS/OAS cells\n"
        "[INFO] No orphan cells in the final layout\n",
        encoding="utf-8",
    )
    return reports, logs


def _serialized_sdc(path: Path) -> None:
    lines = [
        "create_clock -name core_clock -period 20.0000 [get_ports {clk}]",
        "create_clock -name io_clock -period 20.0000",
    ]
    lines.extend(
        f"set_input_delay 1.0000 -clock [get_clocks {{io_clock}}] [get_ports {{i{index}}}]"
        for index in range(598)
    )
    lines.extend(
        f"set_output_delay 1.0000 -clock [get_clocks {{io_clock}}] [get_ports {{o{index}}}]"
        for index in range(319)
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_retained_physical_campaign_is_canonical_schema_valid_and_bounded() -> None:
    report = load_strict_json(REPORT)
    schema = load_strict_json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(report)

    assert REPORT.read_bytes() == canonical_json_bytes(report)
    assert report["campaign_id"] == EXPECTED_CAMPAIGN_ID
    assert report["campaign_id"] == _identity(report, "campaign_id")
    assert report["status"] == "pass"
    assert report["qualification"] == {
        "detailed_route_internal_drc": "pass",
        "extracted_setup_hold": "pass",
        "klayout_stream_merge": "pass",
        "open_pdk_rtl_to_gds_feasibility": "pass",
        "post_synthesis_structural_integrity": "pass",
        "timing_constraint_coverage": "pass",
    }
    assert report["claim_boundary"] == {
        "activity_derived_power": False,
        "complete_layer_execution": False,
        "formal_equivalence": False,
        "foundry_drc": False,
        "gds_generated": True,
        "independent_lvs": False,
        "open_pdk_rtl_to_gds_feasibility": True,
        "package_reliability_yield_or_silicon": False,
        "qualified_sram_macro": False,
        "ta_phy_7_closed": False,
        "ta_rtl_6_closed": False,
    }
    assert {item["status"] for item in report["open_gates"]} == {"not_run"}
    assert {item["gate"] for item in report["open_gates"]} == {
        "activity_power_ir_thermal_performance_per_watt",
        "formal_equivalence",
        "foundry_drc_lvs",
        "sram_macro_package_reliability_yield_silicon",
    }


def test_retained_physical_metrics_close_only_the_bounded_gates() -> None:
    report = load_strict_json(REPORT)
    timing = report["metrics"]["timing"]
    aggregate = timing["aggregate_extracted"]
    audit = timing["independent_audit"]
    assert aggregate["setup_wns_ns"] > 0
    assert aggregate["hold_wns_ns"] > 0
    assert aggregate["setup_violations"] == aggregate["hold_violations"] == 0
    assert audit["unconstrained_endpoints"] == 0
    assert audit["check_setup_diagnostics"] == []
    assert set(audit["per_corner"]) == {"slow", "typ", "fast"}
    for corner in audit["per_corner"].values():
        assert corner["setup_wns_ns"] > 0
        assert corner["hold_wns_ns"] > 0
        assert corner["setup_violations"] == corner["hold_violations"] == 0

    routing = report["metrics"]["routing"]
    assert routing["detailed_route_internal_violations"] == 0
    assert routing["antenna_net_violations"] == 0
    assert routing["antenna_pin_violations"] == 0
    assert report["design"]["macro_count"] == 0
    assert "power" not in report["metrics"]
    assert "no execution-derived switching activity" in report[
        "excluded_metrics"
    ]["power_ir_thermal_reason"]


def test_retained_physical_sources_and_toolchain_are_hash_bound() -> None:
    report = load_strict_json(REPORT)
    expected_sources = {
        str(path.relative_to(ROOT)): _sha256(path.read_bytes())
        for path in (
            CONFIG,
            SDC,
            LOCK,
            ROOT / "rtl/ot_ta_command_decoder.sv",
            ROOT / "rtl/ot_bf16_add_rne.sv",
            ROOT / "rtl/ot_ta_add_bf16_executor.sv",
            ROOT / "rtl/ot_ta_add_bf16_sram_engine.sv",
            SCHEMA,
            ROOT / "tools/collect_qwen3_ta_rtl_physical_campaign.py",
        )
    }
    assert report["source_sha256"] == expected_sources
    lock = load_strict_json(LOCK)
    assert report["toolchain"]["container_image_id"] == lock["container"][
        "image_id"
    ]
    assert report["toolchain"]["platform_collateral_sha256"] == lock[
        "platform_files"
    ]
    assert report["structural_integrity"]["formal_equivalence"] is False
    assert report["structural_integrity"]["interfaces_match"] is True
    assert report["structural_integrity"]["mapped_latch_count"] == 0
    assert report["structural_integrity"]["source_latch_count"] == 0


def test_finish_metric_parser_accepts_only_the_known_orfs_ambiguity(
    tmp_path: Path,
) -> None:
    path = tmp_path / "metrics.json"
    pairs = _metrics_pairs()
    _write_pairs(path, pairs)
    parsed, duplicates = campaign.parse_flat_orfs_metrics(path)
    assert set(parsed) == set(campaign.SELECTED_METRICS)
    assert duplicates == campaign.ALLOWED_ORFS_DUPLICATES

    missing = [(key, value) for key, value in pairs if key != "finish__timing__hold__ws"]
    _write_pairs(path, missing)
    with pytest.raises(campaign.CampaignError, match="hold__ws.*occurred 0 times"):
        campaign.parse_flat_orfs_metrics(path)

    duplicated = pairs + [("finish__timing__hold__ws", 0.2)]
    _write_pairs(path, duplicated)
    with pytest.raises(campaign.CampaignError, match="unexpected ORFS metric ambiguity"):
        campaign.parse_flat_orfs_metrics(path)

    unexpected = pairs + [("unexpected", 1), ("unexpected", 2)]
    _write_pairs(path, unexpected)
    with pytest.raises(campaign.CampaignError, match="unexpected ORFS metric ambiguity"):
        campaign.parse_flat_orfs_metrics(path)


def test_finish_metric_gate_rejects_negative_hold_and_driver_violations() -> None:
    values = {name: 0.0 for name in campaign.SELECTED_METRICS}
    values["finish__timing__setup__ws"] = 1.0
    values["finish__timing__hold__ws"] = -0.001
    with pytest.raises(campaign.CampaignError, match="acceptance metrics failed"):
        campaign.validate_finish_metrics(values)
    values["finish__timing__hold__ws"] = 0.1
    values["finish__timing__drv__max_slew"] = 1
    with pytest.raises(campaign.CampaignError, match="max_slew"):
        campaign.validate_finish_metrics(values)


def test_routing_parser_rejects_nonempty_drc_and_residual_antenna(
    tmp_path: Path,
) -> None:
    reports, logs = _routing_fixture(tmp_path)
    parsed = campaign.parse_routing(reports, logs)
    assert parsed["final_wire_length_um"] == 1234
    assert parsed["final_vias"] == 567

    (reports / "5_route_drc.rpt").write_text("violation\n", encoding="utf-8")
    with pytest.raises(campaign.CampaignError, match="DRC report is not empty"):
        campaign.parse_routing(reports, logs)
    (reports / "5_route_drc.rpt").write_bytes(b"")

    route = (logs / "5_2_route.log").read_text(encoding="utf-8")
    (logs / "5_2_route.log").write_text(
        route + "[INFO ANT-0002] Found 1 net violations.\n",
        encoding="utf-8",
    )
    with pytest.raises(campaign.CampaignError, match="final antenna violations"):
        campaign.parse_routing(reports, logs)


def test_routing_parser_refuses_missing_or_ambiguous_merge_evidence(
    tmp_path: Path,
) -> None:
    reports, logs = _routing_fixture(tmp_path)
    (logs / "6_1_merge.log").write_text(
        "KLayout 0.30.7\n[INFO] No orphan cells in the final layout\n",
        encoding="utf-8",
    )
    with pytest.raises(campaign.CampaignError, match="LEF cells"):
        campaign.parse_routing(reports, logs)
    (logs / "5_2_route.log").unlink()
    with pytest.raises(campaign.CampaignError, match="missing detailed-route log"):
        campaign.parse_routing(reports, logs)


def test_serialized_sdc_requires_every_io_delay_to_retain_its_clock(
    tmp_path: Path,
) -> None:
    final_sdc = tmp_path / "final.sdc"
    _serialized_sdc(final_sdc)
    parsed = campaign.parse_config_and_constraints(CONFIG, SDC, final_sdc)
    assert parsed["serialized_input_delay_bits"] == 598
    assert parsed["serialized_output_delay_bits"] == 319

    text = final_sdc.read_text(encoding="utf-8")
    final_sdc.write_text(
        text.replace(" -clock [get_clocks {io_clock}]", "", 1),
        encoding="utf-8",
    )
    with pytest.raises(campaign.CampaignError, match="lost an io_clock"):
        campaign.parse_config_and_constraints(CONFIG, SDC, final_sdc)


def test_corner_audit_rejects_negative_slack_or_missing_metrics() -> None:
    passing = """AUDIT corner fast
worst slack max 1.000000000
worst slack min 0.100000000
tns max 0.000000000
tns min 0.000000000
AUDIT setup_violations 0
AUDIT hold_violations 0
"""
    assert campaign.parse_corner_audit(passing, "fast")["hold_wns_ns"] == 0.1
    with pytest.raises(campaign.CampaignError, match="fast timing failed"):
        campaign.parse_corner_audit(
            passing.replace("worst slack min 0.100000000", "worst slack min -0.001"),
            "fast",
        )
    with pytest.raises(campaign.CampaignError, match="hold TNS.*matched 0 times"):
        campaign.parse_corner_audit(
            passing.replace("tns min 0.000000000\n", ""), "fast"
        )


def test_structural_json_helpers_reject_interface_drift_and_count_latches() -> None:
    ports = {
        name: {"direction": direction, "bits": list(range(width))}
        for name, (direction, width) in campaign.EXPECTED_PORTS.items()
    }
    data = {
        "modules": {
            campaign.TOP: {
                "ports": ports,
                "cells": {
                    "bad": {"type": "$dlatch"},
                    "good": {"type": "$dff"},
                },
                "processes": {"p": {}},
            }
        }
    }
    assert campaign.yosys_json_ports(data, "fixture") == campaign.EXPECTED_PORTS
    assert campaign.yosys_json_counts(data) == (2, 1, 1)
    del ports["clk"]
    assert campaign.yosys_json_ports(data, "fixture") != campaign.EXPECTED_PORTS


def test_run_directory_resolver_refuses_missing_or_ambiguous_tree(
    tmp_path: Path,
) -> None:
    with pytest.raises(campaign.CampaignError, match="missing ORFS logs"):
        campaign.resolve_run_directories(tmp_path, "route-v6")
    with pytest.raises(campaign.CampaignError, match="invalid ORFS variant"):
        campaign.resolve_run_directories(tmp_path, "../escape")


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker is required")
def test_retained_physical_campaign_replays_when_run_root_is_available() -> None:
    raw = os.environ.get("OPENTALLAS_IHP_QWEN_RUN_ROOT")
    if not raw:
        pytest.skip("set OPENTALLAS_IHP_QWEN_RUN_ROOT to replay the physical collector")
    run_root = Path(raw)
    retained = load_strict_json(REPORT)
    replayed = campaign.collect(
        run_root, "route-v6", CONFIG, SDC, LOCK
    )
    assert canonical_json_bytes(replayed) == canonical_json_bytes(retained)
