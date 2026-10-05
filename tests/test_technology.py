from __future__ import annotations

import json
from pathlib import Path

import pytest

from opentallas.config import load_architecture_envelopes
from opentallas.technology import (
    cim_weight_bandwidth_density_bytes_s_mm2,
    hbm_package,
    scaled_density_bytes_mm2,
    usable_array_capacity_bytes,
)

from tools.build_iso_node_studies import OUTPUTS, build


ROOT = Path(__file__).resolve().parents[1]


def test_rom_density_scaling_is_explicit_and_reproducible() -> None:
    linear = scaled_density_bytes_mm2(
        anchor_density_mbit_mm2=8.928,
        anchor_node_nm=28,
        target_node_nm=7,
        scaling_exponent=1,
    )
    ideal_area = scaled_density_bytes_mm2(
        anchor_density_mbit_mm2=8.928,
        anchor_node_nm=28,
        target_node_nm=7,
        scaling_exponent=2,
    )
    assert linear == pytest.approx(4.464e6)
    assert ideal_area == pytest.approx(17.856e6)
    assert usable_array_capacity_bytes(
        wafer_area_mm2=46_225,
        macro_density_bytes_mm2=linear,
        array_area_fraction=0.35,
        usable_fraction=0.80,
    ) == pytest.approx(57_777_552_000)


def test_yoloc_operation_rate_converts_to_weight_byte_service() -> None:
    assert cim_weight_bandwidth_density_bytes_s_mm2(
        operations_s=28.8e9,
        macro_area_mm2=0.24,
        operations_per_weight=2,
        weight_bits=8,
    ) == pytest.approx(60e9)


def test_hbm_package_does_not_exceed_first_order_perimeter_pitch() -> None:
    package = hbm_package(
        stacks=56,
        stack_capacity_bytes=36e9,
        stack_bandwidth_bytes_s=968.75e9,
        wafer_perimeter_mm=860,
        stack_pitch_mm=12,
    )
    assert package.capacity_bytes == pytest.approx(2.016e12)
    assert package.bandwidth_bytes_s == pytest.approx(54.25e12)
    assert package.perimeter_pitch_utilization < 0.8
    with pytest.raises(ValueError, match="ideal perimeter pitch"):
        hbm_package(
            stacks=80,
            stack_capacity_bytes=36e9,
            stack_bandwidth_bytes_s=968.75e9,
            wafer_perimeter_mm=860,
            stack_pitch_mm=12,
        )


def test_committed_iso_node_studies_are_byte_reproducible() -> None:
    generated = build()
    for key, path in OUTPUTS.items():
        expected = json.dumps(generated[key], indent=2, sort_keys=True) + "\n"
        assert path.read_text(encoding="utf-8") == expected


def test_rom_compute_envelopes_reproduce_public_anchor_derivations() -> None:
    generated = build()
    n7 = generated["n7_architecture_attribution"]["derivations"]["rom_envelopes"]
    leading = generated["leading_node_market"]["derivations"]["rom_envelopes"]

    n7_anchor = n7[0]["compute_anchor_whole_product_ops_s"]
    assert all(row["compute_anchor_whole_product_ops_s"] == n7_anchor for row in n7)
    assert [row["fp8_peak_ops_s"] for row in n7] == pytest.approx(
        [n7_anchor * 0.10, n7_anchor * 0.25, n7_anchor * 0.50]
    )
    assert [row["fp8_peak_ops_s"] for row in leading] == pytest.approx(
        [125e15 * 0.10, 125e15 * 0.30, 125e15 * 0.50]
    )
    assert all("not" in row["compute_evidence"] for row in [*n7, *leading])


def test_studies_keep_node_and_memory_generations_separate() -> None:
    n7_gpus, n7_wafers, n7_meta = load_architecture_envelopes(
        ROOT / "configs" / "hardware" / "n7_architecture_attribution.json"
    )
    leading_gpus, leading_wafers, leading_meta = load_architecture_envelopes(
        ROOT / "configs" / "hardware" / "leading_node_market.json"
    )
    assert all("A100" in gpu.name for gpu in n7_gpus)
    assert {gpu.model_deployment_policy for gpu in n7_gpus} == {
        "a100_bf16_expanded",
        "a100_packed_hbm_bf16_execute",
    }
    assert all("B300" not in gpu.name for gpu in n7_gpus)
    assert all(gpu.weight_storage_technology == "HBM2e" for gpu in n7_gpus)
    assert all(
        wafer.kv_storage_technology in {"HBM2e", "SRAM_N7"}
        for wafer in n7_wafers
    )
    assert all("B300" in gpu.name for gpu in leading_gpus)
    assert all(gpu.weight_storage_technology == "HBM3e" for gpu in leading_gpus)
    assert all(wafer.kv_storage_technology == "HBM3e" for wafer in leading_wafers)
    assert "A100" in n7_meta["comparison_contract"]
    assert "B300" in leading_meta["comparison_contract"]


def test_storage_tier_capacity_is_not_silently_pooled() -> None:
    _, n7_wafers, _ = load_architecture_envelopes(
        ROOT / "configs" / "hardware" / "n7_architecture_attribution.json"
    )
    rom = next(wafer for wafer in n7_wafers if "central" in wafer.name)
    sram = next(wafer for wafer in n7_wafers if wafer.kind == "sram")
    assert rom.storage_capacity_policy == (
        "physically_separate_ROM_weights_and_mutable_HBM_KV"
    )
    assert sram.storage_capacity_policy == (
        "static_70pct_weight_30pct_KV_partition_no_double_counting"
    )
    # The Graphcore-style control exposes separate slices whose sum reproduces
    # the area-scaled total; no byte belongs to both pools.
    derivation = json.loads(
        (ROOT / "configs" / "hardware" / "n7_architecture_attribution.json").read_text()
    )["derivations"]["sram_control"]
    assert (
        sram.weight_capacity_bytes_per_device + sram.kv_capacity_bytes_per_device
    ) == pytest.approx(derivation["total_sram_capacity_bytes"])
