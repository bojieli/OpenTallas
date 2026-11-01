"""Instance / net name clash (COORD 10-31, HEAD hd_turn_a): OpenROAD writes a forwarded-clock buffer whose instance
name equals its output net (cland_fwd_fclk_out_t_o); Yosys refuses the 6_final.v ('Re-definition of cell').  lec.py
renames such instances on a copy (no logic change).
    python3 -m pytest -q tools/die_plan/test_lec_inst_rename.py"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402

NET = """module BUFx2 (input A, output Y); assign Y = A; endmodule
module top (a, cland_fwd_fclk_out_t_o, y, z);
  input a;
  output cland_fwd_fclk_out_t_o;
  output y;
  output z;
  wire \\n[0] ;
  wire n_9;
  BUFx2 cland_fwd_fclk_out_t_o (.A(a),
    .Y(cland_fwd_fclk_out_t_o));
  BUFx2 \\n[0]  (.A(a), .Y(\\n[0] ));
  BUFx2 u2 (.A(\\n[0] ), .Y(y));
  BUFx2 n_9 (.A(a), .Y(n_9));
  BUFx2 n_9__lecinst (.A(n_9), .Y(z));
endmodule
"""


def _yosys_ok(path):
    r = subprocess.run(["yosys", "-q", "-p", f"read_verilog {path}; hierarchy -top top; flatten; opt_clean; stat"],
                       capture_output=True, text=True, timeout=120)
    return r.returncode == 0, r.stdout + r.stderr


def test_renames_only_clashing_instances(tmp_path):
    src = tmp_path / "6_final.v"
    src.write_text(NET)
    rec = {}
    got = lec.instance_net_clash_normalise(str(src), tmp_path, rec)
    assert got != str(src) and src.read_text() == NET          # a copy; the kit netlist is untouched
    t = Path(got).read_text()
    assert "BUFx2 cland_fwd_fclk_out_t_o__lecinst (.A(a)," in t
    assert "BUFx2 \\n[0]__lecinst   (.A(a), .Y(\\n[0] ));" in t
    assert "BUFx2 n_9__lecinst1 (.A(a), .Y(n_9));" in t          # unique against an existing instance name
    assert "BUFx2 n_9__lecinst (.A(n_9), .Y(z));" in t and "BUFx2 u2 (" in t
    assert ".Y(cland_fwd_fclk_out_t_o));" in t                   # nets and ports unchanged
    assert rec["instance_net_renames"]["n"] == 3


def test_no_clash_returns_netlist_unchanged(tmp_path, monkeypatch):
    src = tmp_path / "6_final.v"
    src.write_text(NET.replace("BUFx2 cland_fwd_fclk_out_t_o (", "BUFx2 u_c (").replace("BUFx2 \\n[0]  (", "BUFx2 u0 (")
                   .replace("BUFx2 n_9 (", "BUFx2 u9 ("))
    rec = {}
    assert lec.instance_net_clash_normalise(str(src), tmp_path, rec) == str(src) and not rec
    monkeypatch.setenv("OT_LEC_INST_RENAME", "0")
    src.write_text(NET)
    assert lec.instance_net_clash_normalise(str(src), tmp_path, {}) == str(src)


@pytest.mark.skipif(not shutil.which("yosys"), reason="yosys not installed")
def test_yosys_reads_the_renamed_copy(tmp_path):
    src = tmp_path / "6_final.v"
    src.write_text(NET)
    ok, msg = _yosys_ok(src)
    assert not ok and "Re-definition of cell" in msg                # the failure mode
    ok, msg = _yosys_ok(lec.instance_net_clash_normalise(str(src), tmp_path, {}))
    assert ok, msg
