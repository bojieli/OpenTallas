import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "benchmarks" / "local_gpu_break_even.json"
COMPARATOR = (
    ROOT / "configs" / "benchmarks" / "deepseek_v4_flash_b300_comparator_lock.json"
)
MEASURE = ROOT / "tools" / "measure_local_gpu.py"
BREAK_EVEN = ROOT / "tools" / "gpu_break_even.py"


def load_script(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_measurement_contract_is_nondisruptive_and_contended():
    measure = load_script("measure_local_gpu", MEASURE)
    config = measure.strict_json(CONFIG)
    measure.validate_config(config)
    assert config["contamination_policy"]["label"] == "shared_contended"
    assert (
        config["contamination_policy"]["whole_gpu_energy_attribution_allowed"] is False
    )
    assert config["request"]["temperature"] == 0
    assert config["request"]["stream"] is True
    assert config["request"]["include_usage"] is True
    assert max(point["concurrency"] for point in config["sweep"]) == 2
    assert (
        "http://127.0.0.1:8004"
        in config["contamination_policy"][
            "other_endpoints_must_not_be_stopped_or_changed"
        ]
    )


def test_break_even_comparator_lock_is_self_contained():
    break_even = load_script("gpu_break_even_lock", BREAK_EVEN)
    config = break_even.strict_json(CONFIG)
    inputs = break_even.strict_json(COMPARATOR)
    break_even.validate_config(config)
    break_even.validate_comparator_inputs(inputs)
    assert config["break_even"]["comparator_inputs"] == str(
        COMPARATOR.relative_to(ROOT)
    )
    assert "analytical_artifact" not in config["break_even"]
    assert len(inputs["comparator"]["points"]) == 16
    assert "not a measured B300 run" in inputs["evidence_class"]


def test_sse_parser_handles_comments_and_multiline_data():
    measure = load_script("measure_local_gpu_sse", MEASURE)
    lines = [
        b": keepalive\n",
        b'data: {"a":\n',
        b"data: 1}\n",
        b"\n",
        b"data: [DONE]\n",
        b"\n",
    ]
    assert measure.parse_sse_blocks(lines) == ['{"a":\n1}', "[DONE]"]


def test_endpoint_stability_ignores_only_generated_identity_fields():
    measure = load_script("measure_local_gpu_endpoint", MEASURE)
    first = {
        "object": "list",
        "data": [
            {
                "id": "model",
                "root": "root",
                "max_model_len": 1024,
                "created": 1,
                "permission": [{"id": "a", "created": 1, "allow_sampling": True}],
            }
        ],
    }
    second = json.loads(json.dumps(first))
    second["data"][0]["created"] = 2
    second["data"][0]["permission"][0]["id"] = "b"
    assert measure.stable_endpoint_snapshot(first) == measure.stable_endpoint_snapshot(
        second
    )
    second["data"][0]["max_model_len"] = 2048
    assert measure.stable_endpoint_snapshot(first) != measure.stable_endpoint_snapshot(
        second
    )


def test_contaminated_energy_integrates_but_is_not_attributed():
    measure = load_script("measure_local_gpu_energy", MEASURE)
    samples = [
        {"at_s": 0.0, "power_draw_w": 100.0},
        {"at_s": 2.0, "power_draw_w": 200.0},
        {"at_s": 3.0, "power_draw_w": 200.0},
    ]
    assert measure.contaminated_energy_j(samples) == pytest.approx(500.0)
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert (
        config["contamination_policy"]["whole_gpu_energy_attribution_allowed"] is False
    )


def test_inverse_reference_is_mechanical_and_unachieved():
    break_even = load_script("gpu_break_even", BREAK_EVEN)
    result = break_even.build_result(CONFIG, None)
    reference = result["reference_threshold"]
    assert result["status"] == "requirements_derived_not_achieved"
    assert reference["context_tokens"] == 8192
    assert reference["batch_size"] == 1
    assert reference["throughput_multiplier"] == 1
    assert reference["required_aggregate_tokens_s"] == pytest.approx(438.31453860762616)
    assert reference["required_effective_hbm_bandwidth_bytes_s"] == pytest.approx(
        5_775_499_664.075987
    )
    assert reference["required_total_tensor_operations_s"] == pytest.approx(
        sum(reference["required_operations_s_by_exact_format"].values())
    )
    assert reference["comparator_energy_j_token"] == pytest.approx(
        1812.5 / 438.31453860762616
    )
    assert result["local_qwen_measurement"] is None
    assert any(
        "none is an achieved OpenTallas result" in item
        for item in result["claim_boundary"]
    )


def test_capacity_density_and_envelope_stage_screen():
    break_even = load_script("gpu_break_even_capacity", BREAK_EVEN)
    result = break_even.build_result(CONFIG, None)
    central = next(
        row
        for row in result["capacity_requirements_by_rom_area"]
        if row["scenario"] == "48pct_area_central"
    )
    assert central["rom_area_mm2"] == pytest.approx(46_225 * 0.48)
    assert central["required_usable_capacity_bytes"] == pytest.approx(166_878_536_440)
    assert central["required_raw_macro_density_mbit_mm2"] == pytest.approx(
        166_878_536_440 / (46_225 * 0.48) / 0.86 * 8 / 1e6
    )
    envelopes = {
        row["envelope"]: row for row in result["public_assumption_envelope_screen"]
    }
    assert envelopes["conservative"]["minimum_capacity_stages"] == 2
    assert (
        envelopes["conservative"]["one_wafer_checkpoint_fit_under_assumptions"] is False
    )
    assert envelopes["central"]["minimum_capacity_stages"] == 1
    assert envelopes["central"]["compute_comparison_allowed"] is False


def test_speedup_doubles_service_requirements_and_halves_iso_power_energy():
    break_even = load_script("gpu_break_even_speedup", BREAK_EVEN)
    result = break_even.build_result(CONFIG, None)
    selected = [
        row
        for row in result["thresholds"]
        if row["context_tokens"] == 8192 and row["batch_size"] == 1
    ]
    equality = next(row for row in selected if row["throughput_multiplier"] == 1)
    double = next(row for row in selected if row["throughput_multiplier"] == 2)
    assert double["required_aggregate_tokens_s"] == pytest.approx(
        2 * equality["required_aggregate_tokens_s"]
    )
    assert double["required_total_tensor_operations_s"] == pytest.approx(
        2 * equality["required_total_tensor_operations_s"]
    )
    assert double["maximum_decode_step_interval_s"] == pytest.approx(
        equality["maximum_decode_step_interval_s"] / 2
    )
    assert double["maximum_energy_j_token_at_comparator_iso_power"] == pytest.approx(
        equality["maximum_energy_j_token_at_comparator_iso_power"] / 2
    )


def test_report_keeps_local_qwen_and_deepseek_separate():
    break_even = load_script("gpu_break_even_report", BREAK_EVEN)
    result = break_even.build_result(CONFIG, None)
    report = break_even.render_report(result)
    assert "does not report that OpenTallas achieves it" in report
    assert "DeepSeek/B300" in report
    assert "Local Qwen observation" in report
    assert "current public integer-DV RTL does not implement" in report
