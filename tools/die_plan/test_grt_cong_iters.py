"""FLOW-FIX-0100 (f): generated kits run GRT congestion rounds of 10 iterations (was OpenROAD's 30)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as G  # noqa: E402


def test_default_round_is_10_and_overridable(monkeypatch):
    monkeypatch.delenv("OT_GRT_CONG_ITERS", raising=False)
    assert G._grt_cong_iters() == 10
    monkeypatch.setenv("OT_GRT_CONG_ITERS", "30")
    assert G._grt_cong_iters() == 30
    monkeypatch.setenv("OT_GRT_CONG_ITERS", "x")
    assert G._grt_cong_iters() == 10


def test_config_source_emits_the_iteration_flag():
    src = (Path(__file__).resolve().parent / "gen_phys.py").read_text()
    assert "-congestion_iterations {_grt_cong_iters()}" in src and 'not in (0, 30)' in src
