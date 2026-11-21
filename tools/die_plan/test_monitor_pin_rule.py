"""S81-MONITOR-PIN-1745 (FABLE-CLOSURE-1730 lever 2): a landing monitor and its cland_dn pins are one site.

J5 (224567138ab): aced0fb210 (CBC rule 4, reset hop 300) re-wired the die reset wavefront; the monitor tree follows it, so 103
monitor parents changed and the cland_dn pins moved to the new reset-out sites, while the frozen clock.band_fixed_um.monitor_<i>
(S81-BANDTAP-1115) kept every seat where D8i had it: slice_station t36 31 -> 2,057 um (-766 ps), iqf t1 2,337 um (-1,040 ps).
Rule: every cland_dn pin within cbc_rules.MONITOR_PIN_REACH_UM (300) of its monitor seat; the compose re-seats a far frozen
seat, monitor-home re-seats an existing plan (pins slide when no seat fits at the pin), precheck MONITOR-PIN reports it.
"""
import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "precheck"))
import cbc_rules as CBC  # noqa: E402
import clock_landing_plan as CP  # noqa: E402
import precheck as PC  # noqa: E402

W = H = 1000.0
OLD = [17.28, 17.28, 30.24, 25.92]          # D8i seat on the S-W corner


def _pins(x, y, face="N"):
    names = ("fclk_in_cland_dn_0", "cland_dn_ready_0", "cland_dn_fault_0")
    if face in "NS":
        return [dict(name=n, dir="in", kind="clock" if n.startswith("fclk") else "ctl", layer="M7", epoch=False,
                     xy_um=[round(x + 2.16 * (k + 1), 3), y]) for k, n in enumerate(names)]
    return [dict(name=n, dir="in", kind="clock" if n.startswith("fclk") else "ctl", layer="M7", epoch=False,
                 xy_um=[x, round(y + 2.16 * (k + 1), 3)]) for k, n in enumerate(names)]


def _band(rect):
    return dict(rect_um=list(rect), width=2, ring_width=64, instance="u_cland_monitor_0", ring_place="ff",
                band_use_target=0.5, placement="PROPOSED legal macro-free band; mapped anchoring pending")


def _plan(pins, hard_cores=()):
    other = dict(rect_um=[900.0, 17.28, 980.0, 60.0], width=64, instance="u_cland_a", ring_place="ff")
    lc = dict(pins=pins, bands=dict(monitor_0=_band(OLD), a=copy.deepcopy(other)), base_type="x")
    t = dict(outline_um=[W, H], hard_cores=[copy.deepcopy(h) for h in hard_cores], buses=[],
             clock=dict(landing_contract=lc, band_fixed_um=dict(monitor_0=_band(OLD), a=copy.deepcopy(other)),
                        edge_clocks=[dict(port="fclk_in_cland_dn_0", tap_um=pins[0]["xy_um"], period_mult=1)]))
    side = dict(collector=dict(types=dict(x=dict(bus_geometry={}, bands=dict(monitor_0=_band(OLD))))))
    return dict(partition_types=dict(x=t)), side


def test_distances_and_rule_value():
    assert CBC.MONITOR_PIN_REACH_UM == 300.0
    lc = dict(pins=_pins(500.0, 997.344), bands=dict(monitor_0=_band([0, 0, 10, 10]), ft0_i=_band([0, 0, 1, 1])))
    d = CBC.monitor_pin_distances(lc)
    assert [x[1] for x in d] == ["cland_dn_ready_0", "cland_dn_fault_0", "fclk_in_cland_dn_0"]
    assert all(x[0] == "0" for x in d)
    assert abs(dict((x[1], x[2]) for x in d)["fclk_in_cland_dn_0"] - (502.16 - 5 + 997.344 - 5)) < 1e-6
    assert CBC.monitor_pin_distances(dict(pins=lc["pins"], bands=dict(monitor_0=dict(placement="FAIL", rect_um=None)))) == []
    assert CBC.monitor_pin_distances(None) == []


def test_precheck_flags_far_seat_only():
    far = dict(pins=_pins(500.0, 997.344), bands=dict(monitor_0=_band(OLD)))
    f = PC.monitor_pin_findings(far)
    assert len(f) == 1 and f[0][0] > 1000 and "monitor_0" in f[0][1]
    near = dict(pins=_pins(20.0, 2.656, "S"), bands=dict(monitor_0=_band(OLD)))
    assert PC.monitor_pin_findings(near) == []
    assert "MONITOR-PIN" in PC.CHECKS and "MONITOR-PIN" not in PC.OPT_IN


def test_monitor_home_reseats_at_the_pins():
    p, side = _plan(_pins(500.0, 997.344))
    new, nside, rep = CP.rehome_far_monitors(p, side)
    assert len(rep) == 1 and rep[0]["new_rect_um"] is not None and "pins_moved_um" not in rep[0]
    ck = new["partition_types"]["x"]["clock"]
    nb = ck["landing_contract"]["bands"]["monitor_0"]
    assert all(d <= CBC.MONITOR_PIN_REACH_UM for _, _, d in CBC.monitor_pin_distances(ck["landing_contract"]))
    assert nb["reseated_from_um"] == OLD and nb["ring_place"] == "ff" and nb["instance"] == "u_cland_monitor_0"
    assert ck["band_fixed_um"]["monitor_0"] == nb and nside["collector"]["types"]["x"]["bands"]["monitor_0"] == nb
    old_ck = p["partition_types"]["x"]["clock"]
    assert ck["landing_contract"]["bands"]["a"] == old_ck["landing_contract"]["bands"]["a"]   # other bands untouched
    assert ck["landing_contract"]["pins"] == old_ck["landing_contract"]["pins"]
    assert old_ck["landing_contract"]["bands"]["monitor_0"]["rect_um"] == OLD                 # input untouched
    rows = CP.monitor_seat_rows(rep)
    assert rows[0]["paths"] == ["partition_types.x.clock.landing_contract.bands.monitor_0",
                                "partition_types.x.clock.band_fixed_um.monitor_0"]
    assert CP.BAND_RESERVE == "padded" and CP.BAND_RING == "all" and CP.BAND_USE_MAX is None   # module modes restored


def test_monitor_home_leaves_near_seats_byte_identical():
    p, side = _plan(_pins(20.0, 2.656, "S"))
    new, nside, rep = CP.rehome_far_monitors(p, side)
    assert rep == [] and new == p and nside == side


def test_monitor_home_slides_pins_off_a_hard_core_corner():
    # gunit__t1 J5 form: the child's reset-out pin sits on the N face above a hard core that covers the N-W corner, so no
    # seat fits within 300 um of the pin; the pin trio slides to the nearest outline point that has one
    core = dict(inst="u_core", module="m", origin_um=[12.96, 420.0], outline_um=[440.0, 580.0], orient="R0", halo_um=0.0)
    p, side = _plan(_pins(13.472, 997.344), hard_cores=[core])
    new, nside, rep = CP.rehome_far_monitors(p, side)
    assert len(rep) == 1 and rep[0]["new_rect_um"] is not None, rep
    assert rep[0]["pins_moved_um"]
    ck = new["partition_types"]["x"]["clock"]
    assert all(d <= CBC.MONITOR_PIN_REACH_UM for _, _, d in CBC.monitor_pin_distances(ck["landing_contract"]))
    moved = {q["name"]: q["xy_um"] for q in ck["landing_contract"]["pins"]}
    assert ck["edge_clocks"][0]["tap_um"] == moved["fclk_in_cland_dn_0"]
    r = ck["landing_contract"]["bands"]["monitor_0"]["rect_um"]
    c = [12.96, 420.0, 452.96, 1000.0]
    assert not (min(r[2], c[2]) > max(r[0], c[0]) and min(r[3], c[3]) > max(r[1], c[1]))     # seat off the core
    assert CP.monitor_seat_rows(rep)[0]["pin_paths"] == ["partition_types.x.clock.landing_contract.pins",
                                                         "partition_types.x.clock.edge_clocks"]


def test_compose_does_not_take_a_far_frozen_monitor_seat():
    src = Path(CP.__file__).read_text()
    i = src.index("stale=bool(fxm and fxm.get(\"rect_um\") and monitor_seat_um(")
    seg = src[i:i + 900]
    assert "CBC.MONITOR_PIN_REACH_UM" in seg and "if fxm and fxm.get(\"rect_um\") and not stale:band=copy.deepcopy(fxm)" in seg
    j = src.index("MONITOR-PIN: monitor_{i} seat")
    assert "placement_failures.append" in src[j - 200:j]
    assert CP.monitor_seat_um([0, 0, 10, 10], [305, 5]) == 300.0
