"""pytest: ADV-G0-HOPS (S81 c8 post-tail f6b657b60cef: 98 lanes over reach found only at G0)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_g0_hops as A  # noqa: E402


def test_never_raises():
    assert A.findings(None, "p")[0].startswith("WARN ADV-G0-HOPS not checked")


def test_summary_counts_lanes_from_check_hops(monkeypatch, tmp_path):
    import types
    import check as C
    import schema as S

    class FakeR:
        items = []
    fr = FakeR()
    fr.items = [dict(level="ERROR", check="hops", lane="L1", msg="lane L1: hop 3 via mandatory slot pins is 533 um > reach 405 (add stations)"),
                dict(level="ERROR", check="hops", lane="L2", msg="lane L2: hop 1 via mandatory slot pins is 430 um > reach 405 (add stations)")]
    monkeypatch.setattr(C, "Report", lambda *a, **k: fr)
    monkeypatch.setattr(S, "Plan", lambda raw, p: types.SimpleNamespace(lanes={"L1": {}, "L2": {}, "L3": {}}))
    monkeypatch.setattr(C, "lane_geometry", lambda P, lid: None)
    monkeypatch.setattr(C, "check_hops", lambda P, R, geo: None)
    out = A.findings({}, str(tmp_path / "p.json"))
    assert out[-1].startswith("WARN ADV-G0-HOPS summary 2 lane(s) with a hop over reach (2 ERROR(s); worst +128 um) of 3 lanes")
    assert "L1" in out[0]
