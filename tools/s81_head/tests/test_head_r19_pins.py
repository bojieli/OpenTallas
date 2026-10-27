"""HEAD-R19: plan pin files from built LEFs (PG excluded, multi-track pads at their on-track access point) and the
mirrored-axis track_offset of the R18 delta land every M4/M5 pin on the plan tracks."""
import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


LEF = """MACRO ot_x
  SIZE 9.6 BY 9.6 ;
  PIN a
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT 1.44 9.5 1.464 9.6 ;
    END
  END a
  PIN b
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT 0 2.388 0.1 2.412 ;
    END
  END b
  PIN pad
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT 4.704 4.704 4.896 4.896 ;
    END
  END pad
  PIN VDD
    USE POWER ;
    PORT
      LAYER M5 ;
        RECT 3.0 0.1 3.12 9.5 ;
    END
  END VDD
END ot_x
"""


def test_pg_excluded_and_pad_snapped():
    m = load("head_pins_from_lef")
    macro, outline, pins, pg, moved = m.parse(LEF)
    by = {p["name"]: p for p in pins}
    assert macro == "ot_x" and outline == [9.6, 9.6] and pg == ["VDD"] and "VDD" not in by
    assert moved == 1 and by["a"]["x"] == 1.452 and "rect_centre" not in by["a"]
    assert round(by["pad"]["x"] % 0.048, 4) == 0.012 and 4.704 <= by["pad"]["x"] <= 4.896
    assert by["pad"]["rect_centre"] == [4.8, 4.8]


def test_pad_without_unique_residue_fails():
    m = load("head_pins_from_lef")
    bad = LEF.replace(
        "  PIN pad", "  PIN c\n    USE SIGNAL ;\n    PORT\n      LAYER M5 ;\n        RECT 1.416 9.5 1.44 9.6 ;\n"
        "    END\n  END c\n  PIN pad")
    with pytest.raises(SystemExit):
        m.parse(bad)


@pytest.mark.parametrize("orient", ["R0", "MX", "MY", "R180"])
def test_track_offset_lands_on_plan_tracks(orient):
    d = load("head_r18_plan_delta")
    pf = dict(outline_um=[319.68, 317.672], pins=[dict(name="a", layer="M5", x=157.164, y=0.0),
                                                 dict(name="b", layer="M4", x=0.0, y=100.012)])
    origin = [17.28, 8.64]
    dx, dy = d.track_offset(pf, orient, origin)
    w, h = pf["outline_um"]
    x = origin[0] + dx + (w - 157.164 if orient in ("MY", "R180") else 157.164)
    y = origin[1] + dy + (h - 100.012 if orient in ("MX", "R180") else 100.012)
    for c in (x, y):
        assert abs(((c - 0.024) / 0.048) - round((c - 0.024) / 0.048)) < 1e-6
    assert 0 <= dx < 0.048 and 0 <= dy < 0.048
