"""ADV-RECT-OUTLINE (COORD 11-24): clock-band / tap-window / tap-reserved / landing-contract rects outside the outline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_geom_static as G  # noqa: E402
import plan_advisory as PA  # noqa: E402


def plan(h=200.0):
    """svc_lo after an N-edge shrink of 34.56 um that moved only two-number points"""
    return {"partition_types": {
        "svc_lo__t7": {"outline_um": [300.0, h], "clock": {
            "landing_contract": {"bands": {
                "attn_i0": {"rect_um": [10, 190, 120, 230], "tap_windows_um": [[50, 210, 58.64, 218.64]]},
                "ok": {"rects_um": [[0, 0, 300, 10], [5, 5, 20, 20]]}},
                "reserved_sites_um": [{"rect_um": [290, 100, 310, 120], "kind": "landing_ring_bank"}],
                "start_capture_um": [150, 250]},
            "band_fixed_um": {"attn_i0": {"rects_um": [[10, 190, 50, 230]], "tap_windows_um": [[[50, 210], [58.64, 218.64]]]}},
            "band_tap_windows_um": [[50, 210, 58.64, 218.64]],
            "tap_reserved_um": [[-1, 10, 5, 20], [10, 10, 20, 20]]}},
        "clean": {"outline_um": [100, 100], "clock": {"landing_contract": {"bands": {"b": {"rect_um": [0, 0, 100, 100]}}},
                                                        "tap_reserved_um": [[0, 0, 10, 10]]}},
    }}


def test_outside_rects_are_reported_per_type():
    out = G.rect_outline(plan(), "p.json")
    w = [ln for ln in out if ln.startswith("WARN ADV-RECT-OUTLINE")]
    assert len(w) == 1 and w[0].startswith("WARN ADV-RECT-OUTLINE svc_lo__t7: 7 clock rect(s) outside")
    assert "landing_contract.bands.attn_i0.rect_um" in w[0] and "(30.00 um out)" in w[0]
    s = out[-1]
    assert s.startswith("LIST ADV-RECT-OUTLINE 7 rect(s) on 1 type(s)")
    assert "band_fixed_um 2" in s and "clock 2" in s and "landing_contract.bands 2" in s and "landing_contract 1" in s


def test_points_are_not_rects_and_inside_is_clean():
    rs = dict(G.clock_rects(plan()["partition_types"]["svc_lo__t7"]))
    assert not any("start_capture_um" in k for k in rs)          # a two-number point is not a rect
    assert G.rect_outline({"partition_types": {"clean": plan()["partition_types"]["clean"]}}, "p") == []
    assert G.rect_outline(plan(h=240.0), "p.json") == [] or "attn_i0" not in G.rect_outline(plan(h=240.0), "p")[0]


def test_registered_in_plan_advisory():
    assert ("RECT-OUTLINE", "adv_rect_outline") in PA.CHECKS
    import adv_rect_outline
    assert adv_rect_outline.findings is G.rect_outline
