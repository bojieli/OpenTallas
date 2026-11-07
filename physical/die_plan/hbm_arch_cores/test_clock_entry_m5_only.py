"""DIE-HBM-82 11-06 FLOW class: --clock-pin-entry moves only M5 clock pins; non-M5 clock pins keep the table position."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_core_kit_hbm as G

M5 = (0.024, 0.048)


def _entries(tmp_path, ports, xy=(69.12, 108.0)):
    f = tmp_path / "clock_entries.json"
    f.write_text(json.dumps({"t": {"u0": {"module": "m", "xy_um": list(xy), "port": None, "merged_clock_ports": ports}}}))
    return f


def test_m4_clock_pins_keep_table(tmp_path):
    w, h = 142.56, 216.0
    pins = [dict(name=n, layer="M4", x=142.464, y=y, w=0.048, h=0.48) for n, y in (("clk", 13.848), ("clk_cal", 14.04))]
    clks = ["clk", "clk_cal"]
    sel = G.entry_clock_pins(pins, clks)
    assert sel == []
    moved, rec = G.plan_clock_entries(_entries(tmp_path, clks), "m", sel, w, h, M5)
    assert moved == {} and rec is None
    io, rows = G.io_tcl(pins, w, h, "m", clock_entry=dict(names=set(clks), m5=M5))
    for r, p in zip(rows, pins):           # E-face M4 pins at the table point, not the W face
        assert r["face"] == "E" and r["layer"] == "M4" and r["y"] == p["y"]
    assert "-location {0.2400 108.0000}" not in io


def test_mixed_layers_move_only_m5(tmp_path):
    w, h = 142.56, 216.0
    pins = [dict(name="clk", layer="M5", x=10.008, y=0.24, w=0.048, h=0.48),
            dict(name="clk_l0", layer="M4", x=142.464, y=14.328, w=0.048, h=0.48)]
    sel = G.entry_clock_pins(pins, ["clk", "clk_l0"])
    assert sel == ["clk"]
    moved, rec = G.plan_clock_entries(_entries(tmp_path, ["clk", "clk_l0"]), "m", sel, w, h, M5)
    assert set(moved) == {"clk"} and moved["clk"] == (69.144, 108.0)


def test_m5_only_unchanged(tmp_path):
    w, h = 276.48, 336.96
    pins = [dict(name="clk", layer="M5", x=138.264, y=168.48, w=0.048, h=0.48), dict(name="d", layer="M4", x=0.0, y=1.0)]
    assert G.entry_clock_pins(pins, ["clk"]) == ["clk"]
