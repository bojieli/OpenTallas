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


def test_bit_lines_report_per_bit_over_reach(monkeypatch):
    import types
    import die_hop_scan as D
    slot = dict(name="ft0", stations=2, bit_sites_um=[[[300.0, 0.0], [300.0, 500.0]]], bit_site_cell_um=[0.0, 0.0])
    P = types.SimpleNamespace(types={"T": {"ft_slots": [slot]}}, reach=405.0)
    pins = {"ft0_i": {0: (0.0, 0.0, "W"), 1: (0.0, 0.0, "W")}, "ft0_o": {0: (600.0, 0.0, "E"), 1: (600.0, 0.0, "E")}}
    monkeypatch.setattr(D, "pin_table", lambda P, tn: pins)
    monkeypatch.setattr(D, "normal_slot", lambda P, tn, sn: True)
    monkeypatch.setattr(D, "input_site", lambda p: (p[0], p[1]))
    out = A.bit_lines(P)
    assert out[0].startswith("WARN ADV-G0-HOPS BIT type T slot ft0: bit 1 hop 0 is 800 um > reach 405")
    assert "1 ft slot(s) with a per-bit hop over reach (worst 800 um) of 1 checked / 1 ft slots; report only" in out[-1]


def test_bit_lines_off(monkeypatch):
    monkeypatch.setenv("OT_ADV_G0_HOPS_BIT_S", "0")
    assert A.bit_lines(None)[0] == "WARN ADV-G0-HOPS bit summary off (OT_ADV_G0_HOPS_BIT_S=0)"


def test_regs_only_advisory_uses_the_kits_affine_lanes(monkeypatch):
    from types import SimpleNamespace

    import die_hop_scan as D

    slot = dict(name="ft0", stations=2, regs_um=[[500, 800], [500, 400]])
    P = SimpleNamespace(types={"T": {}})
    pins = {"ft0_i": {0: (100, 800, "N"), 1: (900, 800, "N")},
            "ft0_o": {0: (100, 0, "S"), 1: (900, 0, "S")}}
    monkeypatch.setattr(D, "normal_slot", lambda *_: True)
    monkeypatch.setattr(D, "input_site", lambda p: p[:2])
    monkeypatch.delenv("OT_FT_LANE", raising=False)
    assert A.slot_bit_worst(P, "T", slot, pins)[0] == 400
    monkeypatch.setenv("OT_FT_LANE", "0")
    assert A.slot_bit_worst(P, "T", slot, pins)[0] == 800


def test_landed_first_hop_uses_the_declared_ring_extent(monkeypatch):
    from types import SimpleNamespace

    import die_hop_scan as D

    slot = dict(name="ft0", stations=2, regs_um=[[0, 1000], [0, 300]])
    landing = {"bands": {"ft0_i": {"rect_um": [0, 600, 10, 650]}}}
    P = SimpleNamespace(types={"T": {"clock": {"landing_contract": landing}}})
    pins = {"ft0_i": {0: (0, 1000, "N")}, "ft0_o": {0: (0, 0, "S")}}
    monkeypatch.setattr(D, "normal_slot", lambda *_: False)
    monkeypatch.setattr(D, "input_site", lambda p: p[:2])
    assert A.slot_bit_worst(P, "T", slot, pins) == (360, 0, 0)
