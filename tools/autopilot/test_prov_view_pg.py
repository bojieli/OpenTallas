"""check_routed accepts a routed view whose libs list VDD/VSS as pins; signal mismatches still fail."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("prov_view", Path(__file__).with_name("prov_view.py"))
PV = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PV)

M = "m"
LEF = """MACRO m
  SIZE 10 BY 20 ;
  PIN a
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
      RECT 0 0 1 1 ;
    END
  END a
%s
END m
"""
PG = """  PIN VDD
    DIRECTION INOUT ;
    USE POWER ;
    PORT
      LAYER M5 ;
      RECT 0 0 1 1 ;
    END
  END VDD"""


def view(tmp_path, ports, lef_pg):
    (tmp_path / "m.lef").write_text(LEF % (PG if lef_pg else ""))
    body = "".join(f"  pin({p}) {{ direction : input; }}\n" for p in ports)
    for c in ("tt", "ff"):
        (tmp_path / f"m_{c}.lib").write_text(f"library(x) {{\n cell(m) {{\n{body} }}\n}}\n")
    return PV.check_routed(str(tmp_path), M, {"outline_um": [10, 20]}, [{"name": "a"}], None)


@pytest.mark.parametrize("lef_pg", [True, False])
def test_lib_pg_pins_do_not_fail_the_view(tmp_path, lef_pg):
    assert view(tmp_path, ["a", "VDD", "VSS"], lef_pg) == (True, "ok")


def test_lib_without_pg_still_passes(tmp_path):
    assert view(tmp_path, ["a"], False) == (True, "ok")


def test_extra_signal_port_still_fails(tmp_path):
    ok, why = view(tmp_path, ["a", "b", "VDD"], False)
    assert not ok and "ports != LEF ports" in why


def test_missing_signal_port_still_fails(tmp_path):
    ok, why = view(tmp_path, ["VDD", "VSS"], False)
    assert not ok and "ports != LEF ports" in why
