"""S81-LEAF-SWR (11-19): the leaf's vsw -> vs return station at the depths the plan asks for (1; 2 on leaf__t60).
The D8i bind dropped the SWR station rows of kv_leaf__t1 and leaf__t21 / t27 / t60 / t71 because the staged die netlist
carried LF_CS_SWR_D nibble 0 where the plan has 1-2 stations.  The RTL chain exists (ot_s81sl_leaf u_cst_swr); the event
sets the nibble with `stage_lfcs_netlist.py --update SWR_D`.  This file holds the RTL side:
  - source checks on the real RTL: one station carries sw_ri data with sw_vi / sw_fi, depth = CS_SWR_D = the slice's
    LF_CS_SWR_D nibble of that leaf;
  - sim (iverilog) of the real ot_s81sl_cst / ot_s81sl_cst1 modules at W 64, V 2, D 0 / 1 / 2: data and valids move
    together by exactly D clocks, valids are 0 in reset; a reference off by one clock FAILs (the bench sees one station);
  - lint (verilator --lint-only -Wall) of the same modules at D 0 / 1 / 2;
  - --update SWR_D on a staged slice line gives the nibbles the five dropped rows need, depth 2 included.
The full leaf on the 1M-token SU gold at these depths is tools/s81_slice/leaf_cs_matrix.sh (leaf_SWR, leaf_SWR2).
    python3 -m pytest -q tools/die_plan/test_s81_leaf_swr_station.py"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import stage_lfcs_netlist as SN  # noqa: E402

SL = REPO / "rtl/dsrom_sys/s81_dv/slice"
TB = HERE / "fixtures/s81_leaf_swr/tb_cst_swr.sv"


def _verilator():
    p = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
    return str(p) if os.access(p, os.X_OK) else shutil.which("verilator")


def _cst_source(tmp_path):
    """the two station modules cut from the real RTL file (the rest of ot_s81sl_vp.sv needs the whole leaf file list)"""
    t = (SL / "ot_s81sl_vp.sv").read_text()
    # one contiguous region: ot_s81sl_cst1, the file's own lint pragma for D = 0 (clk / rst_n unused), ot_s81sl_cst
    m = re.search(r"^module ot_s81sl_cst1\b.*?^module ot_s81sl_cst\b.*?^endmodule\b", t, re.S | re.M)
    assert m and m.group(0).count("endmodule") == 2, "ot_s81sl_cst1 / ot_s81sl_cst not found together in ot_s81sl_vp.sv"
    f = tmp_path / "cst.sv"
    f.write_text(m.group(0) + "\n")
    return f


def test_leaf_swr_station_is_one_station_at_the_slice_nibble():
    t = (SL / "ot_s81sl_slice.sv").read_text()
    m = re.search(r"ot_s81sl_cst\s*#\(([^;]*?)\)\s*u_cst_swr\s*\(([^;]*?)\);", t, re.S)
    assert m, "u_cst_swr not found"
    par, con = (re.sub(r"\s+", "", x) for x in m.groups())
    assert par == ".W(64),.V(2),.D(CS_SWR_D)", par
    # data and both control bits ride the same station, so no depth can skew valid / fault against the data
    assert ".d(swri_w)" in con and ".dv({swvi_w,swfi_w})" in con and ".q(swri)" in con and ".qv({swvi,swfi})" in con, con
    assert re.search(r"\.CS_SWR_D\(\s*LF_CS_SWR_D\[4 \* k \+: 4\]\s*\)", t), "leaf k does not take nibble k of LF_CS_SWR_D"


def _sim(tmp_path, d, shift):
    out = tmp_path / f"tb_{d}_{shift}.vvp"
    r = subprocess.run(["iverilog", "-g2012", f"-DD={d}", f"-DSHIFT={shift}", "-o", str(out), str(TB),
                        str(_cst_source(tmp_path))], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    res = subprocess.run(["vvp", "-n", str(out)], capture_output=True, text=True).stdout
    return [x for x in res.splitlines() if "CST_SWR_RESULT" in x][-1]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="no iverilog")
@pytest.mark.parametrize("d,shift,want", [
    (0, 0, "PASS"),      # depth 0: a wire (the netlist before the rows)
    (1, 1, "PASS"),      # kv_leaf__t1, leaf__t21 / t27 / t71
    (2, 2, "PASS"),      # leaf__t60
    (1, 0, "FAIL"),      # controls: one station more or less than the reference is seen
    (1, 2, "FAIL"),
    (2, 1, "FAIL"),
])
def test_station_sim(tmp_path, d, shift, want):
    line = _sim(tmp_path, d, shift)
    assert f"CST_SWR_RESULT {want} D {d} shift {shift}" in line, line
    assert "reset_errors 0" in line, line
    assert int(line.split("valids ")[1].split()[0]) > 2000, line      # the valid bits were exercised
    if want == "PASS":
        assert " errors 0 " in line, line


@pytest.mark.skipif(_verilator() is None, reason="no verilator")
@pytest.mark.parametrize("d", [0, 1, 2])
def test_station_lint(tmp_path, d):
    r = subprocess.run([_verilator(), "--lint-only", "-Wall", "-Wno-DECLFILENAME", "-Wno-MULTITOP", "--top-module",
                        "ot_s81sl_cst", "-GW=64", "-GV=2", f"-GD={d}", str(_cst_source(tmp_path))],
                       capture_output=True, text=True)
    assert r.returncode == 0 and "%Warning" not in r.stderr and "%Error" not in r.stderr, r.stderr[-1500:]


def _row(n):
    """one station row in the exact form of lanes/handoff/S81-LEAF-SWR-STATION-ROWS.json (class swr by its conn / capture)"""
    return dict(bits=1, capture="u_lf.u_vs.sw_v", conn="core:u_lf.u_vsw.o_f|core:u_lf.u_vs", launch="core:u_lf.u_vsw.o_f",
                from_um=[0.0, 0.0], to_um=[0.0, 600.0], regs_um=[[0.0, 200.0 * (i + 1)] for i in range(n)])


def test_update_prices_the_handoff_row_form():
    """the five dropped rows on a staged slice line: depth 1 (t21 form) and depth 2 (t60: u_s_6N L2 on D8i) land in the
    leaf's own nibble; SW_D and the other leaves keep their value; a plan without the rows changes nothing"""
    staged = ("module dv_die (input wire clk);\n"
              "    ot_s81sl_slice_x #(.LF_CS_SW_D(20'h11111), .LF_CS_SWR_D(20'h11010)) u_s_6N (.clk(clk));\nendmodule\n")
    plan = dict(partition_types={
        "ot_s81sl_leaf__t60": dict(hard_cores=[1], internal_stations=[_row(2)]),
        "ot_s81sl_leaf__t21": dict(hard_cores=[1], internal_stations=[_row(1)])},
        partitions=[dict(name="s_6N_L2", type="ot_s81sl_leaf__t60"), dict(name="s_6N_L0", type="ot_s81sl_leaf__t21")])
    out, rep = SN.update(plan, staged, ["SWR_D"])
    assert ".LF_CS_SWR_D(20'h11211)" in out and ".LF_CS_SW_D(20'h11111)" in out
    assert rep == [dict(slice="u_s_6N", cls="SWR_D", old="20'h11010", new="20'h11211")]
    out2, rep2 = SN.update(plan, out, ["SWR_D"])
    assert out2 == out and rep2 == []                                   # a second run is a no-op
