"""lef_pin_narrow (FLOW-OBS-GCELL-R2 11-21): the automatic narrowing reproduces the S81-BKSEL-R6 hand rows byte for byte and
leaves wire-width pins, multi-rect pins and layers without a blanket OBS alone."""
import hashlib
import json
from pathlib import Path

import pytest

import lef_pin_narrow as N

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

LEF = """MACRO m
  SIZE 10 BY 10 ;
  PIN a
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT  1.188 9.52 1.236 10 ;
    END
  END a
  PIN b
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT  2.16 9.52 2.184 10 ;
    END
  END b
  PIN c
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT  3.12 9.52 3.144 10 ;
    END
  END c
  PIN d
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT  0 4.98 0.5 5.046 ;
    END
  END d
  OBS
    LAYER M5 ;
     RECT  0 0 10 10 ;
  END
END m
"""


def test_wide_edge_pin_narrowed_to_on_track_centre():
    new, ch = N.narrow_text(LEF)
    assert [(c["pin"], c["new"]) for c in ch] == [("a", "1.200 9.52 1.224 10")]   # residue 12 of b, c; inside 1.188..1.236
    assert "RECT  2.16 9.52 2.184 10 ;" in new and "RECT  0 4.98 0.5 5.046 ;" in new   # wire width / no M4 blanket: untouched
    assert len(new.splitlines()) == len(LEF.splitlines())


def test_no_blanket_no_change():
    lef = LEF.replace("LAYER M5 ;\n     RECT  0 0 10 10 ;", "LAYER M5 ;\n     RECT  0 0 2 2 ;")
    assert N.narrow_text(lef) == (lef, [])


@pytest.mark.parametrize("name,base_rel", [
    ("dsdv_bksel_c.lef", "physical/die_plan/s81/cores/views/bksel_c_qrx_1117/dsdv_bksel_c/dsdv_bksel_c.lef")])
def test_reproduces_bksel_override_row(name, base_rel):
    base = ROOT / base_rel
    if not base.is_file():
        pytest.skip("plan view not in this checkout")
    row = json.loads((HERE / "lef_overrides" / "map.json").read_text())[name]
    assert hashlib.sha256(base.read_bytes()).hexdigest() == row["base_sha256"]
    new, ch = N.narrow_text(base.read_text())
    assert len(ch) == 1 and hashlib.sha256(new.encode()).hexdigest() == row["sha256"]
