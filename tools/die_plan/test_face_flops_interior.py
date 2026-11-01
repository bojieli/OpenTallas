"""DIE-KV-60 11-01: an interior signal pin (> OT_FF_INTERIOR_UM from every core edge) gets its pin register at the pin
(ff_put_near), not in the band of the nearest face (KV phy cland_tstart_in: face E put it 426 um away)."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SRC = Path(__file__).with_name("face_flops.tcl").read_text()
pytestmark = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh unavailable")


def _between(a, b):
    i = SRC.index(a)
    return SRC[i:SRC.index(b, i)]


def classify(pins, env=None):
    """run the threshold set-up + the face/interior decision of the face loop on (px, py) dbu pins"""
    setup = _between("set ff_interior_dbu", "\nset ff_interior {}") + "\nset ff_interior {}\n"
    decide = _between("    set d [list [list", "\n    if {$face in {E W}} {")
    script = ("set ff_dbu 1000\n" + "".join(f"set ::env({k}) {v}\n" for k, v in (env or {}).items()) + setup +
              "\nset ff_x0 4320; set ff_y0 4320; set ff_x1 859680; set ff_y1 1516320\n"
              "foreach p {" + " ".join(f"{{{x} {y}}}" for x, y in pins) + "} {\n lassign $p px py; set f F; set nm N\n"
              " foreach once {1} {\n" + decide + "\n puts \"FACE $px $face\"\n }\n}\n"
              "foreach e $ff_interior { puts \"INT [lindex $e 1] [lindex $e 2]\" }\n")
    cp = subprocess.run(["tclsh"], input=script, capture_output=True, text=True)
    assert cp.returncode == 0 and not cp.stderr, cp.stderr
    return re.findall(r"FACE (\d+) (\w)", cp.stdout), re.findall(r"INT (\d+) (\d+)", cp.stdout)


def test_centre_pin_is_interior_not_east_face():
    faces, ints = classify([(432032, 758700)])
    assert faces == [] and ints == [("432032", "758700")]


def test_edge_pins_keep_their_face():
    faces, ints = classify([(863904, 1065624), (0, 500000), (431520, 1517984), (440160, 2656)])
    assert [f for _, f in faces] == ["E", "W", "N", "S"] and ints == []


def test_threshold_zero_restores_face_band():
    faces, ints = classify([(432032, 758700)], env={"OT_FF_INTERIOR_UM": 0})
    assert ints == [] and faces == [("432032", "E")]


def test_interior_pass_uses_put_near_after_explicit_reservations():
    i_res = SRC.index("proc ff_reserve_explicit")
    i_near = SRC.index("proc ff_put_near")
    i_pass = SRC.index("foreach e $ff_interior")
    assert i_res < i_near < i_pass < SRC.index("close $ff_out")
