from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from opentallas.analytical import AnalyticalSimulator
from opentallas.config import load_architectures
from opentallas.schema import HardwareProfile, ModelProfile, SimulationRequest, SpeculationProfile


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def setup():
    gpus, rom, _ = load_architectures(ROOT / "configs" / "hardware" / "architectures.json")
    sim = AnalyticalSimulator(HardwareProfile(gpu=gpus[0], rom=rom))
    return gpus, rom, sim


@pytest.mark.parametrize(
    ("slug", "stages", "context"),
    [
        ("deepseek-v4-flash-0731", 2, 200_000),
        ("deepseek-v4-pro-0813", 6, 200_000),
        # Ten wafers have enough aggregate bytes, but Kimi's indivisible ~17 GB
        # transformer layers cannot be packed into ten 160 GB contiguous stages.
        ("kimi-k3", 11, 200_000),
        ("qwen3-8b", 1, 8_192),
    ],
)
def test_released_checkpoint_stage_count(
    setup, slug: str, stages: int, context: int
) -> None:
    _, rom, sim = setup
    model = ModelProfile.load(ROOT / "configs" / "models" / f"{slug}.json")
    point = sim.simulate(model, rom, SimulationRequest(context_tokens=context, batch_size=1))
    assert point.stages == stages
    assert point.metrics["C10_per_user_pipeline_multiplier"] == stages


def test_low_batch_gpu_does_not_claim_all_expert_bandwidth(setup) -> None:
    gpus, _, sim = setup
    model = ModelProfile.load(ROOT / "configs" / "models" / "deepseek-v4-pro-0813.json")
    b1 = sim.simulate(model, gpus[-1], SimulationRequest(context_tokens=200_000, batch_size=1))
    b64 = sim.simulate(model, gpus[-1], SimulationRequest(context_tokens=200_000, batch_size=64))
    assert b1.metrics["C3_engaged_gpu_devices"] < gpus[-1].device_count
    assert b64.metrics["C3_engaged_gpu_devices"] > b1.metrics["C3_engaged_gpu_devices"]


def test_beachfront_capacity_can_make_point_infeasible(setup) -> None:
    _, rom, sim = setup
    model = ModelProfile.load(ROOT / "configs" / "models" / "kimi-k3.json")
    tiny_hbm = replace(rom, kv_capacity_bytes_per_device=1e6)
    point = sim.simulate(model, tiny_hbm, SimulationRequest(context_tokens=1_000_000, batch_size=1))
    assert not point.feasible
    assert any("C7/C8" in reason for reason in point.infeasible_reasons)


def test_pipeline_capacity_charges_one_resident_microbatch_per_stage(setup) -> None:
    _, rom, sim = setup
    model = ModelProfile.load(ROOT / "configs" / "models" / "kimi-k3.json")
    feasible = sim.simulate(
        model,
        rom,
        SimulationRequest(context_tokens=1_000_000, batch_size=17),
    )
    infeasible = sim.simulate(
        model,
        rom,
        SimulationRequest(context_tokens=1_000_000, batch_size=18),
    )
    assert feasible.feasible
    assert feasible.metrics["C7_C8_resident_users_required"] == 187
    assert feasible.metrics["C7_C8_max_batch_per_stage"] == 17
    assert not infeasible.feasible
    assert "batch 18 x 11 stages" in " ".join(infeasible.infeasible_reasons)


def test_rom_layout_is_fixed_across_context_and_batch(setup) -> None:
    _, rom, sim = setup
    model = ModelProfile.load(ROOT / "configs" / "models" / "deepseek-v4-pro-0813.json")
    points = [
        sim.simulate(model, rom, SimulationRequest(context_tokens=context, batch_size=batch))
        for context in (200_000, 1_000_000)
        for batch in (1, 8, 64)
    ]
    assert len({point.metrics["stage_partitions"] for point in points}) == 1
    assert all(point.metrics["C9_exact_layer_weight_inventory"] for point in points)


def test_each_rom_stage_respects_local_weight_capacity(setup) -> None:
    _, rom, sim = setup
    for slug in (
        "deepseek-v4-flash-0731",
        "deepseek-v4-pro-0813",
        "kimi-k3",
        "qwen3-8b",
    ):
        model = ModelProfile.load(ROOT / "configs" / "models" / f"{slug}.json")
        context = 8_192 if slug == "qwen3-8b" else 200_000
        point = sim.simulate(
            model,
            rom,
            SimulationRequest(context_tokens=context, batch_size=1),
        )
        # Stored as a tuple string in the compact scalar metrics map.
        import ast

        stage_storage = ast.literal_eval(
            point.metrics["C9_checkpoint_storage_bytes_by_stage"]
        )
        assert max(stage_storage) <= rom.weight_capacity_bytes_per_device + 1
        assert sum(stage_storage) == pytest.approx(model.checkpoint_bytes)


def test_speculation_has_explicit_draft_cost_and_not_pure_multiplier(setup) -> None:
    gpus, _, sim = setup
    model = ModelProfile.load(ROOT / "configs" / "models" / "deepseek-v4-flash-0731.json")
    base = sim.simulate(model, gpus[1], SimulationRequest(context_tokens=200_000, batch_size=8))
    spec = SpeculationProfile(draft_tokens=5, acceptance_probability=0.7, draft_cost_fraction=0.08)
    point = sim.simulate(
        model,
        gpus[1],
        SimulationRequest(context_tokens=200_000, batch_size=8, speculation=spec),
    )
    assert "speculative_draft_cost" in point.component_times_s
    assert point.component_times_s["speculative_draft_cost"] > 0
    assert point.metrics["C1_draft_weight_bytes_per_step"] > 0
    assert point.aggregate_tokens_s != pytest.approx(base.aggregate_tokens_s * spec.expected_output_tokens)


def test_kv_reread_amplification_is_explicit_and_monotonic(setup) -> None:
    gpus, _, sim = setup
    model = ModelProfile.load(ROOT / "configs" / "models" / "kimi-k3.json")
    request = SimulationRequest(context_tokens=1_000_000, batch_size=8)
    ideal = sim.simulate(model, gpus[-1], request)
    reread = sim.simulate(model, replace(gpus[-1], kv_read_amplification=2.0), request)
    assert ideal.metrics["C2_kv_read_amplification"] == 1.0
    assert reread.metrics["C2_kv_transfer_bytes_per_user_token_after_amplification"] > ideal.metrics[
        "C2_kv_transfer_bytes_per_user_token_after_amplification"
    ]
    assert reread.per_user_tokens_s < ideal.per_user_tokens_s


def test_collective_serialization_grows_with_batch(setup) -> None:
    _, rom, sim = setup
    model = ModelProfile.load(ROOT / "configs" / "models" / "deepseek-v4-pro-0813.json")
    b1 = sim.simulate(model, rom, SimulationRequest(context_tokens=200_000, batch_size=1))
    b64 = sim.simulate(model, rom, SimulationRequest(context_tokens=200_000, batch_size=64))
    assert b64.component_times_s["collective_floor_C6"] > b1.component_times_s["collective_floor_C6"]


def test_b300_uses_published_device_capacity(setup) -> None:
    gpus, _, _ = setup
    b300_x8 = next(gpu for gpu in gpus if gpu.name == "NVIDIA-B300-x8")
    assert b300_x8.weight_capacity_bytes_per_device == pytest.approx(288e9)
    assert b300_x8.device_count * b300_x8.weight_capacity_bytes_per_device == pytest.approx(
        2.304e12
    )
    assert b300_x8.hbm_capacity_utilization == pytest.approx(0.9)


def test_small_gpu_profiles_cover_dense_control_fairly(setup) -> None:
    gpus, _, _ = setup
    assert {gpu.name for gpu in gpus} >= {
        "NVIDIA-B200-x1",
        "NVIDIA-B200-x2",
        "NVIDIA-B300-x1",
        "NVIDIA-B300-x2",
    }
    for family, capacity in (("B200", 180e9), ("B300", 288e9)):
        one = next(gpu for gpu in gpus if gpu.name == f"NVIDIA-{family}-x1")
        assert one.weight_capacity_bytes_per_device == capacity
        assert one.collective_latency_s_per_layer == 0


def test_partial_tco_exposes_capex_and_electricity(setup) -> None:
    gpus, _, sim = setup
    model = ModelProfile.load(ROOT / "configs" / "models" / "deepseek-v4-flash-0731.json")
    point = sim.simulate(
        model,
        gpus[1],
        SimulationRequest(context_tokens=200_000, batch_size=8),
    )
    assert point.amortized_capex_per_million_tokens > 0
    assert point.electricity_cost_per_million_tokens > 0
    assert point.partial_tco_per_million_tokens == pytest.approx(
        point.amortized_capex_per_million_tokens
        + point.electricity_cost_per_million_tokens
    )
    assert point.power_w >= gpus[1].device_count * gpus[1].power_w_per_device
    assert point.metrics["partial_tco_scope"] == (
        "hardware_and_nre_capex_plus_active_electricity_only"
    )


def test_compute_service_separates_dense_and_routed_format_roofs(setup) -> None:
    _, rom, sim = setup
    model = ModelProfile.load(ROOT / "configs" / "models" / "deepseek-v4-pro-0813.json")
    request = SimulationRequest(context_tokens=200_000, batch_size=64)
    baseline = sim.simulate(model, rom, request)
    slower_dense = sim.simulate(
        model,
        replace(
            rom,
            higher_precision_peak_ops_s_per_device=(
                rom.higher_precision_peak_ops_s_per_device / 2
            ),
        ),
        request,
    )
    assert baseline.metrics["C5_dense_higher_precision_operations"] > 0
    assert baseline.metrics["C5_routed_low_precision_operations"] > 0
    assert slower_dense.per_user_tokens_s < baseline.per_user_tokens_s
