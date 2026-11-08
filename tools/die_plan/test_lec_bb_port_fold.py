"""BB-PORT-FOLD (DIE-HBM-92-LEC 11-08): a hard-core child whose physical view has one pin where the gold black box
(the as-built composed module) has a W-bit input.  HBM q_b013: ot_hbm_hc_bank128_pair_core square, gold [15:0], view /
master one pin; synthesis resized the cell port 16 -> 1, LEC gave 120 'differs' (square[1..15] of 8 pairs).
    python3 -m pytest -q tools/die_plan/test_lec_bb_port_fold.py
The integration tests need docker + the ORFS image; the rest is pure python."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402

LIB = """library (kid_tt) {
  type (bus_3_0) { base_type : array; data_type : bit; bit_width : 4; bit_from : 3; bit_to : 0; downto : true; }
  type (bus_1_0) { base_type : array; data_type : bit; bit_width : 2; bit_from : 1; bit_to : 0; downto : true; }
  cell (kid) {
    area : 1;
    pin (clk) { direction : input; clock : true; }
    pin (s) { direction : input; timing () { related_pin : "clk"; timing_type : setup_rising; } }
    bus (y) { bus_type : bus_3_0; direction : output;
      pin (y[0]) { direction : output; } }
    bus (w) { bus_type : bus_1_0; direction : input; }
    pin (z) { direction : output; }
  }
  cell (other) { pin (s) { direction : input; } }
}
"""


def test_lib_port_shapes_top_level_pins_and_buses(tmp_path):
    p = tmp_path / "kid_tt.lib"
    p.write_text(LIB)
    assert lec.lib_port_shapes(p, "kid") == {"clk": 1, "s": 1, "y": 4, "w": 2, "z": 1}
    assert lec.lib_port_shapes(p, "nope") == {}


def test_fold_only_scalar_view_pin_of_a_wider_gold_input(tmp_path):
    p = tmp_path / "kid_tt.lib"
    p.write_text(LIB)
    bb = {"kid": [("clk", "input", 1, 0), ("s", "input", 4, 0), ("y", "output", 4, 0), ("w", "input", 4, 0),
                  ("z", "output", 3, 0)],
          "notalib": [("s", "input", 4, 0)]}
    folds, other = lec.bb_port_folds(bb, [p, p])
    assert folds == {"kid": {"s": (4, 0)}}
    # a narrower bus and a scalar OUTPUT are not a broadcast: reported, not modelled (they still fail as before)
    assert other == [dict(module="kid", port="w", dir="input", gold_width=4, view_width=2),
                     dict(module="kid", port="z", dir="output", gold_width=3, view_width=1)]
    assert lec.bb_port_folds({"kid": [("s", "input", 1, 0), ("y", "output", 4, 0)]}, [p]) == ({}, [])


def test_gate_stub_broadcasts_the_view_pin_to_every_gold_compare_bit():
    bb = {"kid": [("clk", "input", 1, 0), ("s", "input", 4, 2), ("y", "output", 4, 0)]}
    gold = lec.stub_verilog(bb)
    gate = lec.stub_verilog(bb, folds={"kid": {"s": (4, 2)}})
    assert "  input [5:2] s;" in gold and "lec_bbi_s <= s;" in gold
    assert "  input s;" in gate and "  (* keep *) reg [5:2] lec_bbi_s;" in gate
    assert "lec_bbi_s <= {4{s}};" in gate
    assert gold.replace("[5:2] s;", "s;").replace("<= s;", "<= {4{s}};") == gate


# ------------------------------------------------------------------------------------------------ integration
def _have_image():
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "image", "inspect", lec.IMAGE], capture_output=True).returncode == 0


GOLD = """module kid(input wire clk, input wire [3:0] s, output wire [3:0] y);
  reg [3:0] q;
  always @(posedge clk) q <= s;
  assign y = q;
endmodule
module lec_t1(input wire clk, input wire d, input wire e, output wire [3:0] o);
  reg [3:0] r;
  always @(posedge clk) r <= R_NEXT;
  kid u_kid(.clk(clk), .s(r), .y(o));
endmodule
"""

GATE = """module lec_t1(clk, d, e, o);
  input clk;
  input d;
  input e;
  output [3:0] o;
  wire rn;
  wire r0;
  DFFHQNx1_ASAP7_75t_R \\r[0]$_DFF_P_  (.CLK(clk), .D(d), .QN(rn));
  INVx1_ASAP7_75t_R u_i (.A(rn), .Y(r0));
  kid u_kid (.clk(clk), .s(r0), .y(o));
endmodule
"""


# the kit view: only the child cell (its RTL body is in the sources, so LEC black-boxes that body: q_b013 shape)
KIT_LIB = """library (kid_tt) {
  type (bus_3_0) { base_type : array; data_type : bit; bit_width : 4; bit_from : 3; bit_to : 0; downto : true; }
  cell (kid) {
    area : 1;
    pin (clk) { direction : input; clock : true; }
    pin (s) { direction : input; }
    bus (y) { bus_type : bus_3_0; direction : output; }
  }
}
"""


def _kit(tmp_path, name, r_next):
    k = tmp_path / name
    (k / "rtl").mkdir(parents=True)
    (k / "macros").mkdir()
    (k / "rtl" / "lec_t1.sv").write_text(GOLD.replace("R_NEXT", r_next))
    (k / "macros" / "kid_tt.lib").write_text(KIT_LIB)
    n = k / "run" / "results" / "asap7" / "lec_t1" / "base"
    n.mkdir(parents=True)
    (n / "1_2_yosys.v").write_text(GATE)
    (k / "config.mk").write_text(
        "export DESIGN_NAME = lec_t1\nexport PLATFORM = asap7\n"
        "export VERILOG_FILES = /work/rtl/lec_t1.sv\nexport VERILOG_INCLUDE_DIRS = /work/rtl\n"
        "export VERILOG_DEFINES = -DSYNTHESIS\nexport SYNTH_HDL_FRONTEND = slang\n"
        "export ADDITIONAL_LIBS = /work/macros/kid_tt.lib\n")
    return k


def _run(kit):
    r = subprocess.run([sys.executable, str(HERE / "lec.py"), str(kit), "--mem", "4"], capture_output=True,
                       text=True, timeout=900)
    return r.returncode, json.loads((kit / "lec" / "lec.json").read_text())


@pytest.mark.skipif(not _have_image(), reason="needs docker + the ORFS image")
def test_folded_pin_driven_by_equal_bits_is_equivalent(tmp_path):
    """gold drives all 4 child bits from one value (q_b013: 71646_q[127:0] <= {128{71653_Q[28]}}), the netlist drives
    the view's one pin: EQUIVALENT, and the fold is reported."""
    rc, r = _run(_kit(tmp_path, "eq", "{4{d}}"))
    assert rc == 0 and r["verdict"] == "EQUIVALENT", r.get("reason")
    assert r["bb_port_folds"] == [dict(module="kid", port="s", gold_width=4, view_width=1, lsb=0,
                                       basis="view pin broadcast to every gold bit; each gold bit compared")]
    assert r["macro_bodies_blackboxed"] == ["kid"] and r["counts"]["differs"] == 0


@pytest.mark.skipif(not _have_image(), reason="needs docker + the ORFS image")
def test_folded_pin_with_one_different_gold_bit_is_caught(tmp_path):
    """mutant: gold bit 2 comes from another input, so the one pin cannot carry it: exactly that bit differs."""
    rc, r = _run(_kit(tmp_path, "mut", "{d, e, d, d}"))
    assert rc == 1 and r["verdict"] == "NOT EQUIVALENT", r.get("reason")
    assert [e["point"] for e in r["failing"]] == ["bb:u_dut.u_kid.lec_bbi_s[2]"]
