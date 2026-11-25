"""ADV-SITE-IN-MACRO: plan sites (regs / bit sites / relay / CLAND seats) on a hard core or off the outline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_site_in_macro as M  # noqa: E402
import plan_advisory as PA  # noqa: E402

CELL = [1.404, 0.27]


def ptype(**kw):
    t = {"outline_um": [200.0, 200.0], "hard_cores": [{"inst": "u_m", "origin_um": [100.0, 100.0], "outline_um": [50.0, 40.0], "halo_um": 5.0}]}
    t.update(kw)
    return t


def run(t):
    return M.findings({"partition_types": {"ty": t}}, "p")


def test_clean_type_is_silent():
    t = ptype(internal_stations=[{"conn": "bus:a", "regs_um": [[10.0, 10.0]], "bit_sites_um": [[[20.0, 20.0]]], "bit_site_cell_um": CELL}],
              relay_sites={"r0": [30.0, 30.0]})
    assert run(t) == []


def test_bit_site_on_core_and_in_halo_only_and_touching():
    t = ptype(internal_stations=[{"conn": "bus:i_ectl", "regs_um": [[10.0, 10.0]], "bit_site_cell_um": CELL,
                                  "bit_sites_um": [[[110.0, 110.0], [97.0, 110.0], [92.0, 110.0], [150.0, 110.0 + 40.0 + 5.0]]]}])
    out = run(t)
    assert out[0].startswith("WARN ADV-SITE-IN-MACRO ty: 5 sites: 2 in hard core (1 on the core, 1 in its halo only")
    assert "internal_stations.bit_sites_um 2" in out[0]
    assert out[-1].startswith("LIST ADV-SITE-IN-MACRO 1 type(s): 1 on a core, 1 in a halo only, 0 off the outline")


def test_regs_relay_and_cland_seats():
    t = ptype(ft_slots=[{"name": "ft0", "regs_um": [[120.0, 120.0]]}], relay_sites={"rs[3]": [125.0, 125.0], "rs2": [10.0, 10.0]},
              clock={"landing_status_anchors": {"a": [126.0, 126.0]}})
    r = M.counts({"partition_types": {"ty": t}})["ty"]
    assert r["by_key"] == {"ft_slots.regs_um": 1, "relay_sites": 1} and r["in_core"] == 2 and r["cland"] == 1


def test_cland_seat_alone_is_not_a_warn_but_is_counted():
    t = ptype(clock={"landing_status_anchors": {"a": [126.0, 126.0]}})
    assert run(t) == [] and M.cland_total({"partition_types": {"ty": t}}) == 1


def test_off_outline_and_rotated_core():
    t = ptype(internal_stations=[{"conn": "bus:b", "bit_site_cell_um": CELL, "bit_sites_um": [[[199.5, 50.0], [-1.0, 5.0]]]}],
              hard_cores=[{"inst": "u_r", "origin_um": [10.0, 10.0], "outline_um": [40.0, 10.0], "orient": "R90"}],
              relay_sites={"in_rot": [15.0, 45.0]})
    r = M.counts({"partition_types": {"ty": t}})["ty"]
    assert r["off_outline"] == 2 and r["in_core"] == 1        # R90 swaps 40 x 10 to 10 x 40: (15, 45) is on the core


def test_registered_in_plan_advisory():
    assert ("SITE-IN-MACRO", "adv_site_in_macro") in PA.CHECKS
    lines = PA.run({"partition_types": {"ty": ptype(relay_sites={"r": [120.0, 120.0]})}}, "p", checks=["SITE-IN-MACRO"])
    assert lines and lines[0].startswith("WARN ADV-SITE-IN-MACRO ty:")


def test_off_outline_is_a_fail_class_not_a_warn():
    """COORD K10: an off-outline station site, collector source, port pin or clock tap is FAIL ADV-SITE-OFF-OUTLINE; the advisory stays silent"""
    t = ptype(internal_stations=[{"conn": "bus:o_ectl", "regs_um": [[10.0, 10.0], [210.0, 50.0]]}],
              clock={"landing_contract": {"collector_local_sources": [{"name": "src", "xy_um": [-32.07, 0.0]}],
                                          "pins": [{"name": "p_in", "xy_um": [0.0, 20.0]}, {"name": "p_out", "xy_um": [100.0, 201.0]}]},
                     "edge_clocks": [{"port": "fclk_in_x", "tap_um": [-32.16, 2.656]}],
                     "added_taps": [{"name": "clk_t1", "xy": [50.0, 50.0]}]},
              reset_spine_pins=[{"name": "ri", "sites_um": [[150.0, 190.0]]}])
    raw = {"partition_types": {"ty": t}}
    assert run(t) == []
    out = M.off_outline_findings(raw)
    assert out[0].startswith("FAIL ADV-SITE-OFF-OUTLINE ty: 4 object(s) outside the 200x200 outline")
    assert "[by key cland_seats 1, clock_taps 1, internal_stations.regs_um 1, port_pins 1]" in out[0]
    assert out[-1] == "LIST ADV-SITE-OFF-OUTLINE 1 type(s), 4 object(s) off the outline"
    assert M.off_outline_findings({"partition_types": {"ty": ptype(relay_sites={"r": [10.0, 10.0]})}}) == []


def test_pre_gate_runs_off_outline_as_fail(tmp_path):
    import json
    import plan_gate_pre as P
    p = tmp_path / "plan.json"
    p.write_text(json.dumps({"partition_types": {"ty": ptype(relay_sites={"r": [-1.0, 10.0]})}}))
    out = P.site_off_outline_findings(str(p))
    assert out[0].startswith("FAIL ADV-SITE-OFF-OUTLINE ty: 1 object(s)") and "SITE-OFF-OUTLINE" in P.CLASSES
