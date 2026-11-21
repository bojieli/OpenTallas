"""STATION-CORE: the per-bit census reproduces the kit's site model on every station row (bus chains, relay-sited chains,
centroid rows, ft slots, relay_sites)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import station_core as SC  # noqa: E402


def typ(**kw):
    t = dict(outline_um=[1000.0, 1000.0],
             hard_cores=[dict(inst="u_c", origin_um=[400.0, 400.0], outline_um=[200.0, 100.0])],
             buses=[dict(name="o", dir="out", width=4, face="N", leaf="u_pstn.o"),
                    dict(name="i", dir="in", width=4, face="W", leaf="u_c.i")],
             contents=[], internal_stations=[], ft_slots=[])
    t.update(kw)
    return t


PINS = {"o": {b: (450.0 + 20.0 * b, 1000.0) for b in range(5)}, "i": {b: (0.0, 420.0 + 10.0 * b) for b in range(5)}}


def test_bus_chain_without_core_key_is_tested_per_bit():
    # leaf under the core: every bit's vertical leg runs through it (the sle_ctl b_hw_hc1_o class)
    e = dict(conn="bus:o", bit_route="per_bit", leaf_um=[440.0, 380.0], regs_um=[[0, 0]] * 3, bits=5)
    r = SC.rows(typ(internal_stations=[e]), PINS)[0]
    assert r["kind"] == "bus_chain" and r["bits"] == 5 and r["routes_crossing"] == 5 and r["macros"] == ["u_c"]


def test_centroid_outside_but_per_bit_sites_inside():
    # regs_um centroids are clear of the core (istation_clear passes); the kit's per-bit knee sites are not
    e = dict(conn="bus:o", bit_route="per_bit", leaf_um=[500.0, 300.0], regs_um=[[900.0, 900.0]] * 5, bits=5)
    r = SC.rows(typ(internal_stations=[e]), PINS)[0]
    assert r["sites_in_macro"] > 0 and r["routes_crossing"] == 5


def test_clear_chain_has_no_finding():
    e = dict(conn="bus:o", bit_route="per_bit", leaf_um=[700.0, 380.0], regs_um=[[0, 0]] * 2, bits=5)
    t = typ(internal_stations=[e])
    t["buses"][0]["face"] = "N"
    pins = {"o": {b: (650.0 + 20.0 * b, 1000.0) for b in range(5)}}
    r = SC.rows(t, pins)[0]
    assert r["sites_in_macro"] == 0 and r["routes_crossing"] == 0


def test_relay_sited_chain_is_read_from_its_sites():
    e = dict(conn="bus:o", bit_route="per_bit", leaf_um=[440.0, 380.0], regs_um=[[0, 0]] * 2, bits=5)
    rs = {}
    for b in range(5):                      # around the core on the west side
        rs[f"u_ist_o_0.q[{b}]" if b < 4 else "u_ist_o_0.eq"] = [380.0, 380.0 + b]
        rs[f"u_ist_o_1.q[{b}]" if b < 4 else "u_ist_o_1.eq"] = [380.0, 520.0 + b]
    rws = SC.rows(typ(internal_stations=[e], relay_sites=rs), PINS)
    r = rws[0]
    assert r["kind"] == "bus_chain_relay_sites" and r["sites_in_macro"] == 0
    assert r["routes_crossing"] == 0          # (380, 52x) -> (450.., 1000): the y-first L clears the core
    rs["u_ist_o_1.q[2]"] = [500.0, 450.0]
    r = SC.rows(typ(internal_stations=[e], relay_sites=rs), PINS)[0]
    assert r["sites_in_macro"] == 1
    assert SC.rows(typ(internal_stations=[e], relay_sites=rs), PINS)[-1]["sites_in_macro"] == 1      # the relay_sites row too


def test_packed_row_and_ft_slot_points():
    e = dict(conn="bus:i", regs_um=[[100.0, 440.0], [450.0, 440.0]], bits=5)
    ft = dict(name="f", width=8, regs_um=[[300.0, 450.0], [700.0, 450.0]])
    rws = SC.rows(typ(internal_stations=[e], ft_slots=[ft]), PINS)
    assert rws[0]["kind"] == "centroid" and rws[0]["sites_in_macro"] == 1
    assert rws[1]["kind"] == "ft_slot" and rws[1]["sites_in_macro"] == 0 and rws[1]["routes_crossing"] == 1


def test_knee_route_matches_the_kit_split():
    pts, sites = SC.knee_route(450.0, 1000.0, 500.0, 300.0, "N", "out", (450.0, 1000.0, 530.0, 1000.0), 3)
    assert pts == [(500.0, 300.0), (450.0, 300.0), (450.0, 1000.0)] and len(sites) == 3
    assert sites[0] == (450.0, 300.0) and abs(sites[1][1] - (300.0 + 700.0 / 3)) < 1e-6


def test_in_bus_reports_both_models():
    e = dict(conn="bus:i", bit_route="per_bit", leaf_um=[650.0, 440.0], regs_um=[[200.0, 440.0], [450.0, 440.0]], bits=5)
    r = SC.rows(typ(internal_stations=[e]), PINS)[0]
    assert r["kind"] == "bus_chain_in" and r["regs_in_macro"] == 1 and r["routes_crossing"] == 5
    assert "packed lane-pad form: 1 of 2" in SC.line("t", r)


def test_own_landing_macro_is_not_a_crossing_and_pad_relay_sites_are_read():
    t = typ()
    t["hard_cores"].append(dict(inst="cl_i", module="x_cland_w4", origin_um=[10.0, 400.0], outline_um=[30.0, 80.0]))
    e = dict(conn="bus:i", bit_route="per_bit", leaf_um=[300.0, 440.0], regs_um=[[100.0, 440.0], [200.0, 440.0]], bits=5)
    t["internal_stations"] = [e]
    r = SC.rows(t, PINS)[0]
    assert r["routes_crossing"] == 0 and r["sites_in_macro"] == 0
    t["relay_sites"] = {}
    for b in range(5):
        t["relay_sites"][f"u_lpad_i.r[0][{b}]"] = [100.0, 300.0]
        t["relay_sites"][f"u_lpad_i.q[{b}]"] = [500.0, 300.0 if b else 450.0]
    r = SC.rows(t, PINS)[0]
    assert r["kind"] == "bus_chain_relay_sites" and r["sites_in_macro"] == 1 and r["macros"] == ["u_c"]
