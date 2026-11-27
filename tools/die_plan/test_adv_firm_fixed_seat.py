"""ADV-FIRM-FIXED-SEAT (C-FIXEDSITE-FIRM-OVERLAP, R3-FIRMSEAT): the QC TT r3c probe2c evidence (FIRM reset relays rrl:* and the
cland reader-start cell placed before place_fixed_sites.tcl seeds the fixed seats) is found, the r3f workaround (seats moved
0.54-1.08 um) and plain layouts are clean, designed overlaps are not the class."""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_spec = importlib.util.spec_from_file_location("adv_firm_fixed_seat", HERE / "adv_firm_fixed_seat.py")
FS = importlib.util.module_from_spec(_spec)
sys.modules["adv_firm_fixed_seat"] = FS
_spec.loader.exec_module(FS)

DFF = "DFFHQNx1_ASAP7_75t_R"
# firm_seat_hits_probe2c.json (QC-R3-TT row/, placed ot_face_flops_probe2c.txt x r3c fixed seats): FIRM x,y are placed lower-left
RELAYS = [
    {"name": "u_rrl_4", "kind": "pad", "depth": 1, "xy": [535.68, 156.33]},
    {"name": "u_rrl_5", "kind": "pad", "depth": 2, "xy": [533.52, 156.33]},
    {"name": "u_srl_5", "kind": "pad", "depth": 2, "xy": [537.84, 156.33]},
    {"name": "u_srl_6", "kind": "pad", "depth": 3, "xy": [535.68, 155.79]},
    {"name": "u_rrl_62", "kind": "tap", "depth": 4, "xy": [187.92, 178.2]},
    {"name": "u_rrl_82", "kind": "tap", "depth": 4, "xy": [285.12, 242.73]},
    {"name": "u_rrl_82_g", "kind": "tap", "depth": 4, "xy": [285.12, 242.46]},
]
KOK = [298.404, 65.88]                      # u_cland_reader_start_kok_3 placed at (298.404, 65.88)
SEATS = {
    "u_1299/_2_": [536.112, 156.33, 536.382, 156.6], "u_1300/_2_": [537.732, 156.33, 538.002, 156.6],
    "u_1298/_2_": [534.6, 156.33, 534.87, 156.6], "u_1301/_2_": [539.352, 156.33, 539.622, 156.6],
    "u_1300/Q$_DFF_PN0_": [535.68, 155.79, 537.084, 156.06], "u_1301/Q$_DFF_PN0_": [537.3, 155.79, 538.704, 156.06],
    "u_hr.u_18327/Q$_DFF_P_": [187.92, 178.2, 190.08, 178.47], "u_hr.u_18210/Q$_DFF_PN0_": [285.12, 242.73, 287.28, 243.0],
    "u_hr.u_18231/Q$_DFF_PN0_": [285.12, 242.46, 287.28, 242.73], "u_16778/Q$_DFF_P_": [300.24, 65.88, 302.4, 66.15],
}
# BUILD-ROW-r3f.json: the workaround's moved footprints
MOVED = {
    "u_1298/_2_": [534.6, 156.87, 534.87, 157.14], "u_1299/_2_": [536.112, 156.87, 536.382, 157.14],
    "u_1300/Q$_DFF_PN0_": [535.68, 155.25, 537.084, 155.52], "u_1300/_2_": [537.732, 156.87, 538.002, 157.14],
    "u_1301/Q$_DFF_PN0_": [537.3, 155.25, 538.704, 155.52], "u_1301/_2_": [539.352, 155.79, 539.622, 156.06],
    "u_16778/Q$_DFF_P_": [300.24, 64.8, 302.4, 65.07], "u_hr.u_18210/Q$_DFF_PN0_": [285.12, 242.19, 287.28, 242.46],
    "u_hr.u_18231/Q$_DFF_PN0_": [285.12, 241.92, 287.28, 242.19], "u_hr.u_18327/Q$_DFF_P_": [187.92, 177.66, 190.08, 177.93],
}
# the 12 (FIRM, seat) pairs of the placed evidence; the model finds 11 (u_rrl_82_g x u_18210 only touches along y: its
# 10 seats are all found, u_18231 is the other seat of u_rrl_82_g)
EVIDENCE = {
    ("u_rrl_4", "u_1299/_2_"), ("u_rrl_4", "u_1300/_2_"), ("u_rrl_5", "u_1298/_2_"), ("u_srl_5", "u_1300/_2_"),
    ("u_srl_5", "u_1301/_2_"), ("u_srl_6", "u_1300/Q$_DFF_PN0_"), ("u_srl_6", "u_1301/Q$_DFF_PN0_"),
    ("u_rrl_62", "u_hr.u_18327/Q$_DFF_P_"), ("u_rrl_82", "u_hr.u_18210/Q$_DFF_PN0_"),
    ("u_rrl_82_g", "u_hr.u_18210/Q$_DFF_PN0_"), ("u_rrl_82_g", "u_hr.u_18231/Q$_DFF_PN0_"), ("u_cland_reader_start_kok_3", "u_16778/Q$_DFF_P_"),
}


def _tt(seats=SEATS):
    return {
        "outline_um": [552.96, 518.4],
        "place_regions": [{"name": "tt_fixed", "kind": "fixed", "box_um": [0, 0, 552.96, 518.4],
                           "fixed_sites": [{"instance": "u_bound.u_core." + n, "master": DFF, "reserve_rect_um": r}
                                           for n, r in seats.items()]}],
        "clock": {"landing_reader_start": {"depth": 1, "branches": {"kok": {"stages": [
            {"xy_um": KOK, "name": "u_cland_reader_start_kok_3"}]}}}},
    }


def _plan(**types):
    return {"partition_types": types, "partitions": [{"name": f"u_{n}", "type": n} for n in types], "ports": []}


def _hits(t, relays=RELAYS):
    return [h for h in FS.overlaps(t, relays) if h["seat_kind"] == "fixed_site"]


def _pairs(hits):
    return {(h["firm"].split(".")[-1] if h["firm_kind"].startswith("rrl") else
             "u_cland_reader_start_kok_3" if "kok" in h["firm"] else h["firm"], h["seat"].split(":")[-1].replace("u_bound.u_core.", ""))
            for h in hits}


def test_tt_evidence_reproduced():
    hs = _hits(_tt())
    seats = {h["seat"] for h in hs}
    assert len(seats) == 10, seats                      # all 10 overlapped seats
    assert len(hs) == 11, [(h["firm"], h["seat"]) for h in hs]
    assert _pairs(hs) <= EVIDENCE                       # 0 false positives against the placed evidence
    assert len(EVIDENCE - _pairs(hs)) == 1              # the one touch-only pair


def test_findings_lines_and_summary():
    out = FS.findings(_plan(tt_ctlm=_tt()), "tt.json", solved={"tt_ctlm": RELAYS})
    assert all(x.startswith("WARN ADV-FIRM-FIXED-SEAT ") for x in out), out        # report only: never FAIL
    assert sum(" overlaps fixed seat " in x for x in out) == 11, out
    assert "fixed_site 11 overlap(s) on 10 seat(s) in 1 type(s) (tt_ctlm)" in out[-1], out[-1]


def test_r3f_workaround_is_clean_control():
    assert _hits(_tt(MOVED)) == []
    out = FS.findings(_plan(tt_ctlm=_tt(MOVED)), "tt_r3f.json", solved={"tt_ctlm": RELAYS})
    assert not any(" overlaps fixed seat " in x for x in out)
    assert "fixed_site 0 overlap(s) on 0 seat(s) in 0 type(s)" in out[-1], out[-1]


def test_plain_layout_and_touching_seat_are_clean():
    far = {"s": [10.0, 10.0, 11.08, 10.27]}
    assert _hits(_tt(far)) == []
    # a seat that only abuts the relay footprint (535.68 + 2.16 = 537.84) is not an overlap
    abut = {"s": [537.84, 156.33, 538.92, 156.6]}
    t = _tt(abut)
    assert [h for h in _hits(t, [RELAYS[0]])] == []
    assert FS.overlaps({"outline_um": [1, 1]}, RELAYS) == []                         # no seats at all


def test_station_collector_on_register_is_designed_not_counted():
    t = {"ft_slots": [{"name": "ft0", "regs_um": [[100.0, 50.22]]}],
         "clock": {"landing_contract": {"collector_local_sources": [{"name": "c0", "xy_um": [100.0, 50.22]}]}}}
    out = FS.findings(_plan(slc=t), "x.json", solved={})
    assert not any(" overlaps " in x for x in out), out
    assert "1 designed overlap(s) not counted" in out[-1], out[-1]
    assert "station 0 in 0 type(s)" in out[-1]


def test_solve_error_is_named_not_clean():
    out = FS.findings(_plan(tt_ctlm=_tt()), "tt.json", solved={"tt_ctlm": FileNotFoundError("sink bins")})
    assert any("not solvable" in x and "relays NOT checked" in x for x in out), out
    assert sum(" overlaps fixed seat " in x for x in out) == 1                       # the plan-point reader hit remains


def test_never_raises():
    assert FS.findings({}, "x.json")[-1].startswith("WARN ADV-FIRM-FIXED-SEAT")
    out = FS.findings(None, "x.json")
    assert out and out[0].startswith("WARN ADV-FIRM-FIXED-SEAT")


def test_registered_report_only():
    import plan_advisory
    assert ("FIRM-FIXED-SEAT", "adv_firm_fixed_seat") in plan_advisory.CHECKS
    assert ("FIRM-FIXED-SEAT" not in getattr(plan_advisory, "PARENT_CHECKS", ()))
