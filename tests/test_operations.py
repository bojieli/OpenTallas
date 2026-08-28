from __future__ import annotations

from pathlib import Path

import pytest

from opentallas.operations import (
    BF16_X_BF16,
    FP4_X_FP4,
    FP8_X_FP8,
    MXFP4_X_FP8,
    operation_inventory,
)
from opentallas.schema import ModelProfile


ROOT = Path(__file__).resolve().parents[1]


def model(slug: str) -> ModelProfile:
    return ModelProfile.load(ROOT / "configs" / "models" / f"{slug}.json")


def test_flash_operator_inventory_uses_official_shapes() -> None:
    flash = model("deepseek-v4-flash-0731")
    inventory = operation_inventory(flash, 200_000)
    named = inventory.named_operations()

    assert inventory.method == "deepseek_v4_official_operator_inventory_v1"
    assert len(inventory.per_layer_operations_by_format) == 43
    assert named["routed_expert_swiglu"] / 43 == pytest.approx(
        6 * 4096 * 2048 * 6
    )
    assert named["indexer_qk_scan"] / 21 == pytest.approx(
        2 * 64 * 128 * (200_001 // 4)
    )
    assert named["final_vocabulary_head"] == 2 * 4096 * 129_280
    assert inventory.operations_for(MXFP4_X_FP8) > 0
    assert inventory.operations_for(FP4_X_FP4) > 0
    assert inventory.total_tensor_operations == pytest.approx(49_965_039_616)


def test_pro_long_context_work_matches_public_curve_scale_without_calibration() -> None:
    pro = model("deepseek-v4-pro-0813")
    inventory = operation_inventory(pro, 1_000_000)

    assert inventory.operations_for(FP4_X_FP4) == pytest.approx(
        30 * 2 * 64 * 128 * (1_000_001 // 4)
    )
    assert inventory.total_tensor_operations == pytest.approx(294_162_104_320)
    # DeepSeek's plotted 1M endpoint is approximately 0.32T equivalent-FP8
    # FLOPs.  This is a loose independent cross-check, not a calibration target.
    assert inventory.total_tensor_operations == pytest.approx(0.32e12, rel=0.10)


def test_context_dependent_attention_is_not_hidden_in_active_parameters() -> None:
    flash = model("deepseek-v4-flash-0731")
    short = operation_inventory(flash, 0)
    long = operation_inventory(flash, 1_000_000)

    assert long.operations_for(FP4_X_FP4) > short.operations_for(FP4_X_FP4)
    assert long.operations_for(FP8_X_FP8) > short.operations_for(FP8_X_FP8)
    assert long.operations_for(BF16_X_BF16) > short.operations_for(BF16_X_BF16)
    assert long.total_tensor_operations > 5 * short.total_tensor_operations
    assert long.auxiliary_counts["topk_candidates"] > 0
    assert long.auxiliary_counts["topk_selected"] == 21 * 512


def test_non_deepseek_model_is_explicitly_fallback() -> None:
    qwen = model("qwen3-8b")
    inventory = operation_inventory(qwen, 8_192)

    assert inventory.method == "active_parameter_fallback"
    assert inventory.total_tensor_operations == pytest.approx(
        qwen.operations_per_active_parameter * qwen.active_parameters
    )
