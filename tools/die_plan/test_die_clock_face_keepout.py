"""HEAD-PLAN-R4 11-17: die_clock.face_pin_keepouts (opt-in generator carve of partition face signal pins)."""
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_clock as DC


def _plan(d=None):
    die = {"io": []}
    if d is not None:
        die["clock"] = {"face_pin_keepout_um": d}
    types = {"m": {"outline_um": [100.0, 50.0], "buses": [
        {"name": "n_o", "face": "N", "window_um": [10.0, 30.0]},
        {"name": "w_i", "face": "W", "window_um": [5.0, 15.0]},
        {"name": "x", "face": None, "window_um": [1, 2]}]}}
    parts = {"a": {"type": "m"}}
    return SimpleNamespace(die=die, types=types, parts=parts, to_die=lambda n, xy: (xy[0] + 1000.0, xy[1] + 2000.0))


def test_default_off_adds_nothing():
    assert DC.face_pin_keepouts(_plan()) == [] and DC.face_pin_keepouts(_plan(0)) == []
    assert DC.keepouts(_plan()) == []


def test_face_strips_in_die_frame():
    k = DC.face_pin_keepouts(_plan(2.16))
    assert (1010.0, 2047.84, 1030.0, 2050.0, "a/face_pins/n_o") in k
    assert (1000.0, 2005.0, 1002.16, 2015.0, "a/face_pins/w_i") in k
    assert len(k) == 2


def test_keepindex_hits_face_pin():
    K = DC.KeepIndex(DC.keepouts(_plan(2.16)), die=(5000, 5000))
    assert K.hit(1020.0, 2049.0, m=0.0) and not K.hit(1020.0, 2040.0, m=0.0)
