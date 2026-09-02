from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "run_world_model_study.py"
CHECKED_IN = ROOT / "results" / "world-model"
ARTIFACTS = ("REPORT.md", "analytical.json", "sweep.csv")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_world_model_study", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory):
    runner = _load_runner()
    first = tmp_path_factory.mktemp("world-model-first")
    second = tmp_path_factory.mktemp("world-model-second")
    result = runner.run(first)
    runner.run(second)
    return runner, result, first, second


def _attribute(
    result: dict, scenario: str, architecture: str
) -> dict:
    return next(
        item
        for item in result["rom_attribution"]
        if item["scenario"] == scenario and item["architecture"] == architecture
    )


def test_world_model_study_is_byte_deterministic_and_checked_in(generated) -> None:
    _, _, first, second = generated
    for artifact in ARTIFACTS:
        assert (first / artifact).read_bytes() == (second / artifact).read_bytes()
        assert (first / artifact).read_bytes() == (
            CHECKED_IN / artifact
        ).read_bytes()


def test_json_csv_and_report_share_one_result(generated) -> None:
    runner, result, generated_root, _ = generated
    decoded = json.loads((generated_root / "analytical.json").read_text())
    assert decoded == result
    body = (generated_root / "analytical.json").read_text()
    assert "NaN" not in body
    assert "Infinity" not in body
    rows = list(
        csv.DictReader(io.StringIO((generated_root / "sweep.csv").read_text()))
    )
    assert len(rows) == len(result["sweep_rows"]) == 90
    assert tuple(rows[0]) == runner.CSV_FIELDS
    assert (generated_root / "REPORT.md").read_text() == (
        runner.render_report(result).rstrip() + "\n"
    )


def test_oasis_source_shape_and_parameter_identities(generated) -> None:
    _, result, _, _ = generated
    inventory = result["derived_inventory"]["oasis"]
    assert inventory == {
        "dit_parameters": 607_943_744,
        "dit_token_row_parameters": 402_981_952,
        "dit_frame_row_parameters": 204_961_792,
        "vae_decoder_parameters": 152_404_144,
        "static_model_parameters": 837_189_904,
        "static_model_bytes_bf16_equivalent": 1_674_379_808,
        "spatial_tokens_per_frame": 144,
        "temporal_kv_bytes_at_32_frames": 301_989_888,
    }
    reference = next(
        point
        for point in result["baseline_points"]
        if point["scenario"] == "reference_recompute-W32"
        and point["architecture"] == "NVIDIA-B300-x1"
    )
    cached = next(
        point
        for point in result["baseline_points"]
        if point["scenario"] == "causal_kv_cache-W32"
        and point["architecture"] == "NVIDIA-B300-x1"
    )
    assert reference["metadata"]["spatial_tokens_per_frame"] == 144
    assert reference["metadata"]["dit_calls_per_frame"] == 10
    assert reference["tensor_operations"] == 37_928_025_325_568
    assert reference["weight_read_bytes"] == 12_463_683_168
    assert cached["metadata"]["dit_calls_per_frame"] == 11
    assert cached["metadata"]["cache_fill_passes"] == 1
    assert cached["tensor_operations"] == 1_490_483_714_048
    assert cached["weight_read_bytes"] == 13_679_570_656
    assert cached["mutable_hbm_bytes"] == 3_227_516_928


def test_h3_checkpoint_header_and_operation_identities(generated) -> None:
    _, result, _, _ = generated
    inventory = result["derived_inventory"]["h3"]
    assert inventory == {
        "main_matrix_parameters": 19_267_584_000,
        "full_transformer_weight_bytes": 66_280_430_144,
        "active_transformer_weight_bytes_per_call": 40_259_514_944,
        "adaln_precomputed_bytes": 26_020_915_200,
    }
    expected = {
        "5.17s-base_dense": (38_222, 174_796_129_257_881_600, 8_054_873_702_400),
        "10.12s-base_dense": (
            73_898,
            523_145_497_987_481_600,
            15_573_205_401_600,
        ),
        "14.38s-base_dense": (
            104_478,
            964_063_077_484_953_600,
            22_017_610_137_600,
        ),
    }
    for scenario, (tokens, operations, qkv_bytes) in expected.items():
        point = next(
            item
            for item in result["baseline_points"]
            if item["scenario"] == scenario
            and item["architecture"] == "NVIDIA-B300-x8"
        )
        assert point["metadata"]["sequence_tokens"] == tokens
        assert point["tensor_operations"] == operations
        assert point["metadata"]["qkv_materialization_floor_bytes"] == qkv_bytes
        assert point["weight_read_bytes"] == 1_972_716_232_256
        assert point["mutable_hbm_bytes"] == 0


def test_causal_cache_exposes_a_conditional_rom_storage_gain(generated) -> None:
    _, result, _, _ = generated
    central = "ROM-wafer-N4-class-HBM3e-central"
    reference = _attribute(result, "reference_recompute-W32", central)
    cached = _attribute(result, "causal_kv_cache-W32", central)
    assert reference["rom_storage_speedup"] == pytest.approx(1.0)
    assert cached["rom_storage_speedup"] > 2.0
    finding = result["findings"]
    assert finding["central_oasis_w32_cache_algorithmic_speedup"] > 25
    assert (
        finding["central_oasis_w32_cached_rom_storage_speedup_local_cache"]
        > finding["central_oasis_w32_cached_rom_storage_speedup_remote_cache"]
    )
    assert (
        finding[
            "central_oasis_w32_cached_rom_storage_speedup_per_stream_proxy"
        ]
        < 1.1
    )


def test_h3_remains_compute_or_noc_bound_under_favorable_controls(generated) -> None:
    _, result, _, _ = generated
    h3 = [
        item for item in result["rom_attribution"] if item["model"] == "MiniMax-H3"
    ]
    assert len(h3) == 3 * 2 * 3
    assert all(item["rom_storage_speedup"] == pytest.approx(1.0) for item in h3)
    assert {
        item["rom_main_phase"]["largest_modeled_term"] for item in h3
    } <= {"compute", "noc_serialization_floor"}
    accelerated = [
        item for item in h3 if item["scenario"].endswith("accelerated_best_case")
    ]
    assert accelerated
    assert all(item["denoise_calls"] == 4 for item in accelerated)
    assert all(item["attention_density"] == 0.1 for item in accelerated)


def test_noc_and_rom_row_service_sensitivities_are_explicit(generated) -> None:
    _, result, _, _ = generated
    noc = result["sensitivities"]["oasis_noc_critical_cut"]
    cached = [
        item for item in noc if item["scenario"] == "causal_kv_cache-W32"
    ]
    assert [item["noc_critical_cut_fraction"] for item in cached] == [
        0,
        0.25,
        0.5,
        1,
    ]
    assert [item["rom_storage_speedup"] for item in cached] == pytest.approx(
        [4.286428749520691, 2.784636875632276, 2.2248980146944204,
         1.7527244853864332]
    )

    h3 = result["sensitivities"]["h3_row_reuse"]
    accelerated = [
        item
        for item in h3
        if item["scenario"].endswith("accelerated_best_case")
    ]
    whole_call = [
        item for item in accelerated if item["rom_row_reuse"] == "whole_call"
    ]
    per_row = [item for item in accelerated if item["rom_row_reuse"] == 1]
    assert all(item["rom_storage_speedup"] == pytest.approx(1.0) for item in whole_call)
    assert [item["rom_storage_speedup"] for item in per_row] == pytest.approx(
        [0.28637112673111415, 0.3186688037230456, 0.34635304417638296]
    )


def test_capacity_calibration_and_source_pins_are_visible(generated) -> None:
    _, result, _, _ = generated
    assert all(item["fits_one_stage"] for item in result["capacity"])
    calibration = result["calibration"]["h3_b300"]
    assert calibration["published_latency_s"] == 19.04
    assert calibration["modeled_to_published_latency_ratio"] == pytest.approx(
        1.2427535431054033
    )
    assert 0.5 < calibration["required_fraction_of_raw_bf16_roof"] < 0.6
    identity = result["input_identity"]
    assert identity["source_pins"]["oasis"]["revision"] == (
        "f59deef2c019c212bd0c5a3a5b986a51f3701847"
    )
    assert identity["source_pins"]["minimax_h3"]["revision"] == (
        "d21241f0a4b3acbb34c97dae47fa417b7065e438"
    )


def test_local_inputs_and_all_imported_equation_sources_are_bound(generated) -> None:
    _, result, _, _ = generated
    expected_sources = {
        "runner": RUNNER,
        "analytical_module": ROOT / "src/opentallas/world_model.py",
        "schema_module": ROOT / "src/opentallas/schema.py",
    }
    assert set(result["producer"]) == set(expected_sources)
    for label, path in expected_sources.items():
        assert result["producer"][label] == {
            "path": str(path.relative_to(ROOT)),
            "sha256": _sha256(path),
        }

    for label in ("study_config", "hardware", "oasis_inventory", "h3_inventory"):
        identity = result["input_identity"][label]
        assert identity["sha256"] == _sha256(ROOT / identity["path"])

    h3_inventory = json.loads(
        (ROOT / result["input_identity"]["h3_inventory"]["path"]).read_text()
    )
    assert h3_inventory["checkpoint_inventory"]["path"] == "FL2VA/transformer"
    assert h3_inventory["diffusers_source"]["scheduling_minimax_h3.py"] == (
        "307d5bf755337ef00c47237f9ac8be116e627d26e1df3b5f0bd504a80f9de8dd"
    )


def test_source_pin_disagreement_fails_closed(generated) -> None:
    runner, _, _, _ = generated
    config = json.loads(runner.CONFIG_PATH.read_text())
    oasis = json.loads((ROOT / config["inputs"]["oasis_inventory"]["path"]).read_text())
    h3 = json.loads((ROOT / config["inputs"]["h3_inventory"]["path"]).read_text())
    config["source_pins"]["oasis"]["revision"] = "0" * 40
    with pytest.raises(RuntimeError, match="oasis source-pin mismatch"):
        runner._assert_source_pin_alignment(config, oasis, h3)


def test_report_does_not_promote_analysis_to_implementation(generated) -> None:
    _, _, generated_root, _ = generated
    report = (generated_root / "REPORT.md").read_text()
    required = (
        "MiniMax-H3 is much",
        "algorithmic cache gain, not a ROM gain",
        "OpenTallas currently supports neither model",
        "not video execution or",
        "one-row/per-stream ROM service proxy",
        "cannot be installed as an",
        "action-to-next-frame loop",
        "Global NoC critical-cut sensitivity",
        "0.286×–0.346× attribution",
    )
    for phrase in required:
        assert phrase in report
