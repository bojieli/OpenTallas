"""DIE-QC-97 11-10: parent route channels through a hard core (core_route_channel.py)."""
import pytest

import core_route_channel as CRC
import master_slice as MS
import schema as S
from test_core_infra import sample

CH = dict(dir="EW", span_um=[830, 990], layers=["M6"], reason="parent E-W band")
OL = [457.92, 1157.76]

LEF = """MACRO m
  SIZE 457.92 BY 1157.76 ;
  PIN a
    PORT
      LAYER M6 ;
        RECT 0 900 0.1 900.1 ;
    END
  END a
  OBS
    LAYER M5 ;
     RECT 0 4.297 457.92 1153.463 ;
    LAYER M6 ;
        RECT 0 100.000 457.920 100.032 ;
        RECT 0 850.000 457.920 850.032 ;
        RECT 10 800.000 20.000 1000.000 ;
    LAYER M7 ;
        RECT 5 850 6 860 ;
  END
END m
"""


def test_rect_and_frames():
    assert CRC.rect(CH, OL) == [0.0, 830.0, 457.92, 990.0]
    assert CRC.rect(dict(CH, dir="NS", span_um=[100, 200]), OL) == [100.0, 0.0, 200.0, 1157.76]
    with pytest.raises(ValueError):
        CRC.rect(dict(CH, span_um=[1100, 1200]), OL)       # outside the core height
    with pytest.raises(ValueError):
        CRC.norm(dict(CH, span_um=[990, 830]))
    with pytest.raises(ValueError):
        CRC.norm(dict(CH, layers=["X6"]))


def test_module_channels_one_list_per_master():
    h = dict(inst="u_a", module="nk", route_channels=[CH])
    assert CRC.module_channels([("t1", h), ("t2", dict(h, inst="u_b"))]) == [
        dict(dir="EW", span_um=[830.0, 990.0], layers=["M6"])]
    assert CRC.module_channels([("t1", dict(inst="u_a", module="nk"))]) == []
    with pytest.raises(ValueError, match="differ across uses"):
        CRC.module_channels([("t1", h), ("t2", dict(inst="u_b", module="nk"))])


def test_slice_keepout_validates_and_emits_routing_obstruction_only():
    ch = dict(CH, span_um=[300, 400])
    keep = CRC.slice_keepouts([("t1", dict(inst="u_a", module="nk", route_channels=[ch]))], [864, 864])
    assert keep == [dict(name="route_channel0", rect_um=[0.0, 300.0, 864.0, 400.0], kind="route_channel", use=[],
                         layers=["M6"])]
    sl = sample()
    sl["keepouts"] = list(sl.get("keepouts", [])) + keep
    assert MS.validate(sl) == []
    tcl = MS.emit_tcl(sl)
    assert "ot_ms_obstruction $ms_b M6 0 300000 864000 400000" in tcl
    assert "placement blockage: keepout route_channel0" not in tcl


def test_lef_check_and_grt_view():
    bad = CRC.lef_violations(LEF, [CH], OL)
    assert {tuple(b["rect"]) for b in bad} == {(0, 850, 457.92, 850.032), (10, 800, 20, 1000)}
    text, rec = CRC.open_grt_view(LEF, [CH], OL)
    assert rec["rects_cut"] == 2 and rec["pieces_kept"] == 2       # the band rect goes; the tall one is split
    assert CRC.lef_violations(text, [CH], OL) == []
    assert "RECT 10.000 800.000 20.000 830.000 ;" in text and "RECT 10.000 990.000 20.000 1000.000 ;" in text
    assert "RECT 0 100.000 457.920 100.032 ;" in text                # outside the band: byte-identical
    assert "RECT 5 850 6 860 ;" in text and "RECT 0 4.297 457.92 1153.463 ;" in text   # other layers kept
    assert "RECT 0 900 0.1 900.1 ;" in text                          # pins untouched


def test_schema_accepts_route_channels():
    hc = S.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["hard_cores"]["items"]
    rc = hc["properties"]["route_channels"]["items"]
    assert set(rc["required"]) == {"dir", "span_um", "layers", "reason"}
    assert rc["properties"]["dir"]["enum"] == ["EW", "NS"]
