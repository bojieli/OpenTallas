"""Regression for measured SerDes clk/rst M5 short-spacing, DRT r2 it20."""
import json
from pathlib import Path
import head_serdes_core_kit as K

def test_wide_clock_entry_meets_m5_parallel_spacing():
    # Actual asap7_tech_1x_201209.lef: M5 WIDTH >= .025 -> .072 spacing.
    table = {p["name"]: p for p in K.pins()}
    emitted = []
    def face(*args):
        return "", []
    _, rows = K.interior_io(face, None)(K.pins(), *K.OUTLINE, "test")
    entries = {r["bus"]: r for r in rows}
    clock, reset = entries["clk"], entries["rst_n"]
    assert clock["size"] == [.048, .48]
    gap = clock["x"] - clock["size"][0]/2 - (reset["x"] + reset["size"][0]/2)
    assert gap >= .072 - 1e-9
    assert table["clk"]["x"] == 108.12  # clock tree entry stays fixed
    tracked = json.loads((Path(K.__file__).parent / "data/kp4_dchn_pins.json").read_text())
    assert tracked == K.pins()
