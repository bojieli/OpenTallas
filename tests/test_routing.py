from __future__ import annotations

from pathlib import Path

import pytest

from opentallas.routing import generate_synthetic_routes, summarize_routes
from opentallas.schema import ModelProfile


ROOT = Path(__file__).resolve().parents[1]


def test_uniform_trace_matches_closed_form_coverage() -> None:
    model = ModelProfile.load(ROOT / "configs" / "models" / "deepseek-v4-flash-0731.json")
    routes = generate_synthetic_routes(model, 256, seed=3)
    stats = summarize_routes(routes, model.num_experts, (1, 8, 64))
    assert routes.shape == (43, 256, 6)
    for stat in stats:
        assert stat.trace_mean_coverage == pytest.approx(stat.analytical_coverage, abs=0.01)


def test_correlated_zipf_trace_exposes_tail_imbalance() -> None:
    model = ModelProfile.load(ROOT / "configs" / "models" / "deepseek-v4-pro-0813.json")
    routes = generate_synthetic_routes(model, 128, seed=4, zipf_alpha=0.8, persistence=0.65)
    stats = summarize_routes(routes, model.num_experts, (64,))
    assert stats[0].p05_load_balance_efficiency < 0.15
