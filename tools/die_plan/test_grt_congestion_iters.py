"""KIT-OPS-5 11-14 (FABLE-ROUTE lever 1): allow-congestion kits cap the GRT congestion iterations at 15."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402


def test_default_is_15(monkeypatch):
    monkeypatch.delenv("OT_GRT_CONGESTION_ITERS", raising=False)
    assert gen_phys.grt_congestion_iters_arg() == " -congestion_iterations 15"


def test_override_and_off(monkeypatch):
    monkeypatch.setenv("OT_GRT_CONGESTION_ITERS", "20")
    assert gen_phys.grt_congestion_iters_arg() == " -congestion_iterations 20"
    for v in ("0", "off", ""):
        monkeypatch.setenv("OT_GRT_CONGESTION_ITERS", v)
        assert gen_phys.grt_congestion_iters_arg() == ""


def test_source_line_carries_the_argument():
    src = (Path(__file__).resolve().parent / "gen_phys.py").read_text()
    assert "-allow_congestion{grt_congestion_iters_arg()}" in src
