"""Multi-corner timing reads each memory macro's OWN liberty of that corner, and fails closed without it.

run_abi3_physical --macro-view: the primary ORFS corner (TC/WC/BC) uses NAME_{tt,ss,ff}.lib and every
CORNERS entry appends the macro's liberty of that corner to {C}_LIB_FILES (ADDITIONAL_LIBS reaches only
LIB_FILES).  signoff_analysis analyze: each corner session reads the routed block's macros at that corner.
The OpenSTA check proves the selection matters: a macro whose SS liberty is deliberately slower moves the
SS slack by exactly the clk->q difference.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import run_abi3_physical as rap  # noqa: E402
import signoff_analysis as so  # noqa: E402

CLKQ_PS = {"tt": 100.0, "ss": 400.0, "ff": 60.0}


def macro_lib(name: str, tag: str, clkq_ps: float) -> str:
    return f"""library ({name}_{tag}) {{
  delay_model : table_lookup;
  time_unit : "1ps";
  capacitive_load_unit (1, ff);
  voltage_unit : "1V";
  current_unit : "1mA";
  pulling_resistance_unit : "1kohm";
  leakage_power_unit : "1nW";
  nom_process : 1; nom_voltage : 0.7; nom_temperature : 25;
  cell ({name}) {{
    area : 10;
    pin (CLK) {{ direction : input; clock : true; capacitance : 1; }}
    pin (D) {{ direction : input; capacitance : 1;
      timing () {{ related_pin : "CLK"; timing_type : setup_rising;
        rise_constraint (scalar) {{ values ("20"); }} fall_constraint (scalar) {{ values ("20"); }} }} }}
    pin (Q) {{ direction : output;
      timing () {{ related_pin : "CLK"; timing_type : rising_edge;
        cell_rise (scalar) {{ values ("{clkq_ps:g}"); }} cell_fall (scalar) {{ values ("{clkq_ps:g}"); }}
        rise_transition (scalar) {{ values ("10"); }} fall_transition (scalar) {{ values ("10"); }} }} }}
  }}
}}
"""


def write_macro(d: Path, name: str, tags=("tt", "ss", "ff")) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.lef").write_text("VERSION 5.8 ;\nEND LIBRARY\n")
    for t in tags:
        (d / f"{name}_{t}.lib").write_text(macro_lib(name, t, CLKQ_PS[t]))
    return d


VIEW = {"pnr": {"platform": "asap7", "corner_env": "TC"}, "time_unit_ns": 0.001}


def test_orfs_corners_read_each_macros_own_liberty(tmp_path, monkeypatch):
    monkeypatch.setattr(rap, "ROOT", tmp_path)
    write_macro(tmp_path / "m", "tmac")
    mm = rap.resolve_macro_views("v", VIEW, ["tmac=m"], [2.0, 2.0], None, corners=["WC", "BC"])
    entry = mm["macros"][0]
    assert entry["lib"]["path"] == "/src/m/tmac_tt.lib"
    assert {c: v["path"] for c, v in entry["libs_by_corner"].items()} == {
        "TC": "/src/m/tmac_tt.lib", "WC": "/src/m/tmac_ss.lib", "BC": "/src/m/tmac_ff.lib"}
    lines = rap.corner_lib_lines(["WC", "BC"], mm)
    assert lines[0] == "export CORNERS = WC BC"
    assert lines[1] == "export WC_LIB_FILES = $(WC_NLDM_LIB_FILES) /src/m/tmac_ss.lib"
    assert lines[2] == "export BC_LIB_FILES = $(BC_NLDM_LIB_FILES) /src/m/tmac_ff.lib"


def test_primary_corner_uses_its_matching_macro_lib(tmp_path, monkeypatch):
    monkeypatch.setattr(rap, "ROOT", tmp_path)
    write_macro(tmp_path / "m", "tmac")
    view = {"pnr": {"platform": "asap7", "corner_env": "WC"}, "time_unit_ns": 0.001}
    mm = rap.resolve_macro_views("v", view, ["tmac=m"], [2.0, 2.0], None, corners=["BC"])
    assert mm["macros"][0]["lib"]["path"] == "/src/m/tmac_ss.lib"
    assert "/src/m/tmac_ss.lib" in mm["additional_libs"]


def test_missing_corner_liberty_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(rap, "ROOT", tmp_path)
    write_macro(tmp_path / "m", "tmac", tags=("tt", "ss"))
    with pytest.raises(rap.FlowError, match="no FF liberty"):
        rap.resolve_macro_views("v", VIEW, ["tmac=m"], [2.0, 2.0], None, corners=["WC", "BC"])
    # a macro entry without per-corner liberties (e.g. a single-corner platform fakeram) cannot join CORNERS
    with pytest.raises(rap.FlowError, match="no liberty for ORFS corner WC"):
        rap.corner_lib_lines(["WC"], {"macros": [{"name": "fakeram", "lib": "/x.lib"}]})


def test_signoff_macro_libs_select_and_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "MACRO_DIR", tmp_path)
    write_macro(tmp_path / "tmac", "tmac", tags=("tt", "ss"))
    res = tmp_path / "res"
    res.mkdir()
    (res / "6_final.v").write_text("module top(clk);\n  input clk;\n  tmac u_rom (.CLK(clk));\nendmodule\n")
    assert so.block_macros(res) == ["tmac"]
    [(host, cont)] = so.macro_libs(["tmac"], "SS")
    assert host == tmp_path / "tmac" / "tmac_ss.lib" and cont == "/so_macros/tmac/tmac_ss.lib"
    with pytest.raises(RuntimeError, match="no FF liberty"):
        so.macro_libs(["tmac"], "FF")


STA = rap.STA


@pytest.mark.skipif(not STA.is_file(), reason="local OpenSTA not installed")
def test_slower_ss_macro_liberty_shifts_ss_slack(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "MACRO_DIR", tmp_path)
    write_macro(tmp_path / "tmac", "tmac")
    (tmp_path / "top.v").write_text(
        "module top(clk, d, q);\n input clk, d;\n output q;\n tmac u_rom (.CLK(clk), .D(d), .Q(q));\nendmodule\n")
    (tmp_path / "top.sdc").write_text(
        "create_clock -name clk -period 1000 [get_ports clk]\n"
        "set_input_delay 0 -clock clk [get_ports d]\nset_output_delay 500 -clock clk [get_ports q]\n")
    slack = {}
    for corner in ("TT", "SS"):
        [(lib, _)] = so.macro_libs(["tmac"], corner)
        tcl = tmp_path / f"{corner}.tcl"
        tcl.write_text(
            f"read_liberty {lib}\nread_verilog {tmp_path / 'top.v'}\nlink_design top\n"
            f"read_sdc {tmp_path / 'top.sdc'}\n"
            "puts \"SLACK [sta::time_sta_ui [sta::worst_slack_cmd max]]\"\nexit\n")
        out = subprocess.run([str(STA), "-no_init", "-no_splash", "-exit", str(tcl)],
                             capture_output=True, text=True, timeout=120).stdout
        m = re.search(r"SLACK (-?[0-9.eE+-]+)", out)
        assert m, out
        slack[corner] = float(m.group(1))
    # 1000 - 500 output delay - clk->q: TT 400 ps, SS 100 ps -- the SS corner saw the macro's SS clk->q
    assert slack["TT"] == pytest.approx(400.0, abs=1.0)
    assert slack["SS"] == pytest.approx(100.0, abs=1.0)
