import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import kv_pvfin_pins_from_def as P

DEF = """UNITS DISTANCE MICRONS 1000 ;
DIEAREA ( 0 0 ) ( 200000 100000 ) ;
PINS 3 ;
    - VDD + NET VDD + SPECIAL + DIRECTION INOUT + USE POWER
      + PORT
        + LAYER M5 ( -60 -1 ) ( 60 1 )
        + FIXED ( 10 10 ) N ;
    - a[0] + NET a[0] + DIRECTION INPUT + USE SIGNAL
      + PORT
        + LAYER M4 ( -21 -24 ) ( 21 24 )
        + PLACED ( 0 30000 ) N ;
    - q + NET q + DIRECTION OUTPUT + USE SIGNAL
      + PORT
        + LAYER M4 ( -21 -24 ) ( 21 24 )
        + PLACED ( 200000 60000 ) N ;
END PINS
"""


def test_signal_pins_only_with_faces():
    j = P.parse(DEF, "m")
    assert j["outline_um"] == [200.0, 100.0]
    assert [(p["name"], p["face"], p["dir"]) for p in j["pins"]] == [("a[0]", "W", "in"), ("q", "E", "out")]
