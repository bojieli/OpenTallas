"""QC-STA-HOP 11-25: station_site / ADV-G0-HOPS follow the kit for explicit_stage0 slots (face_flops.tcl + ft_bit_sites.table).
Each test fails on the pre-QC-STA-HOP mapping (stage j -> bit_sites_um[j-1], stage 0 = in pin)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_hop_scan as D
import ft_bit_sites as B

AP, BP = (600.0, 5.0, "E"), (5.0, 1339.0, "N")
CELL = [1.4, 0.27]
STAGES = [(540.0, 250.0), (220.0, 250.0), (7.0, 363.0), (7.0, 688.0), (7.0, 1013.0)]


def slot(n, **kw):
    s = {"name": "s", "stations": 5, "width": 0, "bit_site_cell_um": CELL, "bit_sites_um": [[list(p)] for p in STAGES[:n]]}
    s.update(kw)
    B.validate_slot(s)
    return s


def c(p):
    return (p[0] + CELL[0] / 2, p[1] + CELL[1] / 2)


def test_unlanded_explicit_full_places_bs_j_at_stage_j():
    s = slot(5, explicit_stage0=True)
    assert [D.station_site(s, j, 0, AP, BP, normal=True) for j in range(5)] == [c(p) for p in STAGES]


def test_landed_explicit_full_skips_dead_bs0():
    # landed loop: station i takes key i+1; stage 0 is the ring at the in pin, bs[0] is never placed
    s = slot(5, explicit_stage0=True)
    pts = [D.station_site(s, j, 0, AP, BP, normal=False) for j in range(5)]
    assert pts[0] == D.input_site(AP)
    assert pts[1:] == [c(p) for p in STAGES[1:]]


def test_unlanded_explicit_partial_stage0_is_regs0():
    regs = [[530.0, 240.0], [220.0, 250.0], [7.0, 363.0], [7.0, 688.0], [7.0, 1013.0]]
    s = slot(4, explicit_stage0=True, regs_um=regs)
    assert D.station_site(s, 0, 0, AP, BP, normal=True) == (530.0, 240.0)
    assert D.station_site(s, 1, 0, AP, BP, normal=True) == c(STAGES[0])


def test_legacy_slots_unchanged():
    s = slot(4)
    for nm in (True, False):
        assert D.station_site(s, 0, 0, AP, BP, normal=nm) == D.input_site(AP)
        assert [D.station_site(s, j, 0, AP, BP, normal=nm) for j in range(1, 5)] == [c(p) for p in STAGES[:4]]


def test_explicit_full_helper_casts_stations():
    assert D.explicit_full(slot(5, explicit_stage0=True))
    s = slot(5, explicit_stage0=True); s["stations"] = 5.0
    assert D.explicit_full(s)
    assert not D.explicit_full(slot(4, explicit_stage0=True)) and not D.explicit_full(slot(4))


def _worst(monkeypatch, s, landed):
    import adv_g0_hops as G
    monkeypatch.setattr(D, "normal_slot", lambda P, tn, sn, **kw: not landed)
    pins = {"s_i": {0: AP}, "s_o": {0: BP}}
    return G.slot_bit_worst(None, "t", s, pins)


def test_slot_bit_worst_unlanded_counts_in_pin_to_s0(monkeypatch):
    far = [list(p) for p in STAGES]; far[0] = [100.0, 250.0]   # S0 far from the in pin: pin -> S0 = 745 um
    s = {"name": "s", "stations": 5, "width": 0, "bit_site_cell_um": CELL, "explicit_stage0": True, "bit_sites_um": [[p] for p in far]}
    w, b, i = _worst(monkeypatch, s, landed=False)
    assert i == -1 and w > 700


def test_slot_bit_worst_landed_full_reports_ring_to_bs1(monkeypatch):
    s = slot(5, explicit_stage0=True)
    w, b, i = _worst(monkeypatch, s, landed=True)
    # ring (in pin) -> bs[1]: |600-4-220.7| + |5-250.1| ~ 620 um, the real landed first hop (st_a b_hw_ctl_hc0 class)
    assert i == 0 and 600 < w < 640


def test_landed_regs_only_stage0_is_ring():
    regs = [[500.0, 100.0], [220.0, 250.0], [7.0, 363.0], [7.0, 688.0], [7.0, 1013.0]]
    s = {"name": "s", "stations": 5, "width": 0, "regs_um": regs}
    assert D.station_site(s, 0, 0, AP, BP, normal=False) == D.input_site(AP)
    assert D.station_site(s, 0, 0, AP, BP, normal=True) == D.input_site(AP)
    assert D.station_site(s, 2, 0, AP, BP, normal=False) == (7.0, 363.0)
