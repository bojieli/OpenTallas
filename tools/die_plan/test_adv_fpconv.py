"""tests of adv_fpconv.py (FP-CONVERGE-S81): each check has a pass case and a mutant that must flag."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_fpconv as F  # noqa: E402
import plan_advisory as PA  # noqa: E402


def core(inst, x, y, w, h):
    return {"inst": inst, "origin_um": [x, y], "outline_um": [w, h]}


def base():
    t = {"outline_um": [1000.0, 800.0],
         "hard_cores": [core("a", 100, 100, 200, 200), core("b", 400, 100, 200, 200), core("c", 700, 500, 100, 100)],
         "internal_stations": [{"bits": 8, "launch": "core:a.q", "capture": "core:b.d", "from_um": [300.0, 200.0], "to_um": [400.0, 200.0],
                                 "regs_um": [[315.0, 400.0]]}],
         "ft_slots": [{"name": "ft0", "width": 4, "regs_um": [[50.0, 20.0], [50.0, 700.0]]}],
         "relay_sites": {"r0": [10.0, 10.0]},
         "relay_depth": [{"inst": "u_x", "port": "p", "path_um": 300.0, "stages_existing": 0, "D": 1}],
         "clock": {"added_taps": [{"name": "t0", "xy": [10, 10]}, {"name": "t1", "xy": [200, 700]}],
                   "landing_contract": {"bands": {"b0": {"rect_um": [600, 10, 660, 50], "max_pin_to_band_hop_um": 80}}},
                   "reach_fix_sinks": [[500.0, 400.0, 1.0]]}}
    return {"partition_types": {"T": t}, "reset": {"in_sites": {"T": [900.0, 10.0]}}}


def lines(name, raw):
    return [x for x in F.findings_by_check[name](raw, "p.json") if "summary" not in x]


def mut(fn):
    r = base()
    fn(r["partition_types"]["T"], r)
    return r


def test_base_is_clean_for_every_check():
    r = base()
    for k in F.F:
        assert lines(k, r) == [], k


def test_in_outline():
    r = mut(lambda t, r: r["reset"]["in_sites"].update(T=[1611.8, 12.9]))
    assert "reset root" in lines("IN-OUTLINE", r)[0]
    r = mut(lambda t, r: t["relay_sites"].update(r1=[-3.0, 5.0]))
    assert "relay site" in lines("IN-OUTLINE", r)[0]
    r = mut(lambda t, r: t["internal_stations"][0].update(bit_sites_um=[[999.9, 5.0]], bit_site_cell_um=[1.404, 0.27]))
    assert "bit site" in lines("IN-OUTLINE", r)[0]


def test_leg405_zero():
    r = mut(lambda t, r: t["relay_depth"][0].update(path_um=436.4))
    assert "436.4" in lines("LEG405-ZERO", r)[0]
    r = mut(lambda t, r: t["relay_depth"][0].update(path_um=436.4, stages_existing=1))
    assert lines("LEG405-ZERO", r) == []


def test_relay_seat():
    r = mut(lambda t, r: t["relay_sites"].update(r1=[200.0, 200.0]))
    assert "inside core a" in lines("RELAY-SEAT", r)[0]
    r = mut(lambda t, r: t["relay_sites"].update({f"s{i}": [600.0, 700.0] for i in range(6)}))
    assert "x6 on one point" in lines("RELAY-SEAT", r)[0]


def test_seat_density():
    r = mut(lambda t, r: t["internal_stations"].append({"bits": 2000, "regs_um": [[650.0, 650.0]] * 10}))
    assert "util" in lines("SEAT-DENSITY", r)[0]


def test_pin_face_clear():
    r = mut(lambda t, r: (t["hard_cores"][1].update(origin_um=[330, 100]), t["internal_stations"][0].update(to_um=[330.0, 200.0])))
    assert "a E face 30.0 um clear" in lines("PIN-FACE-CLEAR", r)[0]       # a 30 um slot in front of the pins


def test_hub_box():
    r = base()
    t = r["partition_types"]["T"]
    t["internal_stations"][0]["bits"] = 500
    assert lines("HUB-BOX", r) == []           # a 100 um street W, outline clear S/N/E: two clear faces
    t["hard_cores"] += [core("n", 400, 320, 200, 100), core("s", 400, 20, 200, 60), core("e", 620, 100, 100, 200)]
    out = lines("HUB-BOX", r)                  # boxed in at 20 um on N, S, E (W 100 um clear is only one face)
    assert out and "500 bits" in out[0]


def test_ft_clear():
    r = mut(lambda t, r: t["ft_slots"][0].update(regs_um=[[0.0, 200.0], [600.0, 200.0]]))
    assert "over cores" in lines("FT-CLEAR", r)[0]


def test_tap_step_dup():
    r = mut(lambda t, r: t["clock"]["added_taps"].append({"name": "t2", "xy": [215, 700]}))
    assert "t1/t2" in lines("TAP-STEP-DUP", r)[0]


def test_band_at_pin():
    r = mut(lambda t, r: t["clock"]["landing_contract"]["bands"]["b0"].update(max_pin_to_band_hop_um=392))
    assert "392" in lines("BAND-AT-PIN", r)[0]
    r = mut(lambda t, r: t["clock"]["landing_contract"]["bands"]["b0"].update(rect_um=[120, 120, 180, 160]))
    assert "overlaps a" in lines("BAND-AT-PIN", r)[0]


def test_seat_unique():
    r = mut(lambda t, r: t["internal_stations"].extend({"bits": 1, "regs_um": [[40.0, 40.0]]} for _ in range(5)))
    assert "5 stations" in lines("SEAT-UNIQUE", r)[0]


def test_registered_and_runs_through_plan_advisory():
    names = {n for n, _m in PA.CHECKS}
    for k in F.F:
        assert k in names, k
    r = mut(lambda t, r: r["reset"]["in_sites"].update(T=[1611.8, 12.9]))
    out = PA.run(r, "p.json", checks=["IN-OUTLINE"], jobs=1)
    assert any("ADV-IN-OUTLINE T" in x for x in out)
    assert PA.run(copy.deepcopy(base()), "p.json", checks=list(F.F), jobs=2) is not None


def test_leg405_flags_cland_origin_to_far_reader_without_reader_start():
    """C9-KVPV-CLAND-LEG: origin (400, 75) -> cland_fstart_in_ft42_i (3, 1410) = 1732 um, one cycle, no landing_reader_start"""
    import adv_fpconv as F
    t = {"clock": {"landing_contract": {"pins": [
            {"name": "cland_fstart_in_ft42_i", "xy_um": [3.0, 1410.0]},
            {"name": "cland_fstart_in_near_i", "xy_um": [420.0, 100.0]},
            {"name": "fclk_in_ft42_i", "xy_um": [3.0, 1400.0]}]},
        "landing_raw_branches": [{"name": "o", "consumers": ["origin"], "stages": [{"xy_um": [400.0, 75.0]}]}]}}
    assert F.leg405_zero(t) == [("cland_origin", "reader_start_ft42_i", 1732.0, 0)]
    t["clock"]["landing_reader_start"] = {"branches": {}}
    assert F.leg405_zero(t) == []
    assert F.leg405_zero({"clock": {}}) == []
