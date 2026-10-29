"""HBM-CORES-KITS-4 10-28: kit plan_pins.json of a sized plan pin (C25a clock pins M5 0.048 x 0.48) is the io.tcl pin
centre, so kit_preflight pins_canonical passes; unsized pins are unchanged (PIN_LEN_UM/2 inward)."""
import importlib.util
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("coregen_pins_sized", HERE / "gen_core_kit_hbm.py")
coregen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coregen)

W, H = 20.0, 10.0
PINS = [dict(name="clk", layer="M5", x=4.824, y=0.096, w=0.048, h=0.48),
        dict(name="clk_n", layer="M5", x=6.024, y=9.904, w=0.048, h=0.48),
        dict(name="d[0]", layer="M5", x=8.024, y=0.096),
        dict(name="a[0]", layer="M4", x=0.096, y=2.424),
        dict(name="y[0]", layer="M4", x=19.904, y=3.384)]


def _io_centres(io):
    out = {}
    for m in re.finditer(r"place_pin -pin_name \{([^}]*)\} -layer (\S+) -location \{(\S+) (\S+)\}", io):
        out[m.group(1)] = (float(m.group(3)), float(m.group(4)))
    return out


def test_plan_pins_equal_io_centres():
    io, rows = coregen.io_tcl(PINS, W, H, "t")
    recs = coregen.plan_pin_records(rows)
    cen = _io_centres(io)
    assert set(recs) == set(cen)
    for n, r in recs.items():
        assert abs(r["x"] - cen[n][0]) < 1e-4 and abs(r["y"] - cen[n][1]) < 1e-4, (n, r, cen[n])
    assert recs["clk"]["y"] == 0.24 and recs["clk_n"]["y"] == 9.76


def test_unsized_unchanged():
    _, rows = coregen.io_tcl(PINS, W, H, "t")
    recs = coregen.plan_pin_records(rows)
    half = coregen.PIN_LEN_UM / 2
    assert recs["d[0]"]["y"] == round(0.0 + half, 4)
    assert recs["a[0]"]["x"] == round(0.0 + half, 4)
    assert recs["y[0]"]["x"] == round(W - half, 4)
