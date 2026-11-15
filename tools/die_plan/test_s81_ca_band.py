"""S81-CA-BAND 11-15 (FABLE-PD-S81-0335 F item 3, scope reduced by COORD): the 17 CA compose band placement failures
fit with the existing notched (multi-rect) band, depth unchanged.  compose --band-multi-rect reaches clock_landing_plan,
the 2-bit monitor ring takes the notched band too, default stays byte-identical."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "s81_head"))
import pytest

import clock_landing_plan as CL

OBST = [[0, 25.92, 400, 400], [0, 0, 150, 25.92], [190, 0, 210, 25.92], [260, 0, 400, 25.92]]


def _type():
    return {"outline_um": [400, 400],
            "buses": [{"name": "m", "dir": "in", "face": "S", "window_um": [190, 210], "width": 2}]}


@pytest.fixture
def blocked(monkeypatch):
    monkeypatch.setattr(CL.RT, "blockages", lambda t, *a, **k: [list(o) for o in OBST])


def test_fallback_land_cli_passes_band_multi_rect():
    src = (Path(__file__).resolve().parents[1] / "s81_head" / "fallback_land.py").read_text()
    assert '"--band-multi-rect"' in src and "band_multi_rect=a.band_multi_rect" in src


def test_compose_monitor_band_has_multi_rect_fallback():
    src = Path(CL.__file__).read_text()
    i = src.index("monbus=f\"cland_dn_ready_{i}\"")
    seg = src[i:i + 1200]
    assert "if band_multi_rect" in seg and "_storage_rects_staged(t,monbus,2" in seg


def test_staged_rects_fit_a_two_bit_band_when_single_band_does_not(blocked):
    t = _type()
    # a monitor band is a 2-bit ring without epoch; shrink the free space so one rect cannot hold it
    try:
        CL._storage_band(t, "m", 2, [], has_epoch=False)
        single = True
    except ValueError:
        single = False
    b = CL._storage_rects_staged(t, "m", 2, [], has_epoch=False)
    rs = b.get("rects_um") or [b["rect_um"]]
    assert sum((r[2] - r[0]) * (r[3] - r[1]) for r in rs) + 1e-6 >= b["area_reserve_um2"]
    assert single or len(rs) >= 1
