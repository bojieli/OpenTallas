"""The sparse-KV traffic model must keep reproducing a run it never fitted.

``tools/check_deepseek_v4_context_gate.py`` refuses a DeepSeek accelerator run
whose attention counters differ from the traffic the pinned profile implies.
That is only a gate while the model is right, and the evidence that it is right
is that it reproduces the one completed DeepSeek backend run exactly, on all
four counters, without having been fitted to it.

This test holds that evidence in place.  If the profile, the model, or the
committed record moves, the checker stops being a checker and this fails.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RECORD = (
    REPO / "results/abi3/accelerator_tokens/deepseek_v4_flash_rom_p32_raw.json"
)
PROFILE = REPO / "configs/models/deepseek-v4-flash-0731.json"


def _checker():
    spec = importlib.util.spec_from_file_location(
        "deepseek_context_gate",
        REPO / "tools" / "check_deepseek_v4_context_gate.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_model_reproduces_the_only_completed_deepseek_backend_run():
    module = _checker()
    recorded = json.loads(RECORD.read_text())["counters"]
    predicted = module.predict(
        int(json.loads(RECORD.read_text())["prompt_tokens"]), 0, PROFILE
    )
    for name, value in predicted.items():
        assert recorded[name] == value, (
            f"{name}: the profile says {value:,}, the committed run recorded "
            f"{recorded[name]:,}"
        )


def test_the_window_and_the_ranking_both_bind():
    """The model is not a dense count wearing a sparse name."""
    module = _checker()
    window, _heads, layers = module.layer_table(PROFILE)
    # A query far past the window sees the window, not its whole history.
    assert module.gathered_rows_for_query(10_000, window, 0, 0) == window
    # A ranked layer stops at top_k once the candidates exceed it.
    ratio, top_k = next((r, k) for r, k in layers if k)
    assert module.gathered_rows_for_query(
        ratio * (top_k + 1) - 1, window, ratio, top_k
    ) == window + top_k
    # An unranked compressing layer never stops.
    ratio_dense = next(r for r, k in layers if r and not k)
    assert module.gathered_rows_for_query(
        ratio_dense * 4096 - 1, window, ratio_dense, 0
    ) == window + 4096
