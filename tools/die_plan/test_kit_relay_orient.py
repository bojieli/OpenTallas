"""S81-STAGE-SEAT: kit_relay_orient in the kit preflight: oriented, idempotent, off knob, no seats, mutant."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_relay_orient as K  # noqa: E402

SEATS = {"relay_seats": [
    {"elaborated_path": "r0", "master": "m", "engine": 0, "stage": 0, "origin_um": [100, 100], "outline_um": [10, 10]},
    {"elaborated_path": "r1", "master": "m", "engine": 0, "stage": 1, "origin_um": [20, 100], "outline_um": [10, 10]}],
    "exit_relay_seats": [], "hard_seats": []}
TCL = "proc ot_seat {name x y} {}\not_seat {r0} 100 100\not_seat {r1} 20 100\n"


def _kit(tmp, seats=SEATS):
    (tmp / "seats.json").write_text(json.dumps(seats))
    (tmp / "macro_place.tcl").write_text(TCL)
    return tmp


def test_orients_idempotent_and_receipt(tmp_path):
    k = _kit(tmp_path)
    st, line = K.apply(k, env={})
    assert st == "ON" and "flipped=2" in line               # r0 -> r1 goes west: MY; r1 (last, repeats the hop) west: MY
    t = (k / "macro_place.tcl").read_text()
    assert "ot_seat_o {r0} 100 100 MY" in t and "proc ot_seat_o" in t
    assert (k / "macro_place.pre_orient.tcl").read_text() == TCL
    assert json.loads((k / "relay_orient.json").read_text())["relays"] == 2
    st2, _ = K.apply(k, env={})
    assert st2 == "ON" and (k / "macro_place.tcl").read_text() == t


def test_off_knob_and_no_seats_and_bad_json(tmp_path):
    k = _kit(tmp_path)
    assert K.apply(k, env={"OT_RELAY_ORIENT": "0"})[0] == "OFF"
    assert (k / "macro_place.tcl").read_text() == TCL
    assert K.apply(tmp_path / "nokit", env={})[0] == "SKIP"
    (k / "seats.json").write_text("{not json")
    assert K.apply(k, env={})[0] == "FAIL" and (k / "macro_place.tcl").read_text() == TCL


def test_wired_into_preflight_main():
    src = (Path(__file__).resolve().parent / "kit_preflight.py").read_text()
    assert "kit_relay_orient" in src
