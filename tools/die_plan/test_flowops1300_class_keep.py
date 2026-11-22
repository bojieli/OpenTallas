"""FLOW-OPS-1300 item 6 / FABLE-CLOSURE-1320 lever 2: relay / station / landing / reset-sync registers are never merged by yosys
opt_merge (replica_keep.class_regs -> OT_KEEP_WIRES Mod:reg; async_reg wires kept in ot_keep_regs.tcl).
    python3 -m pytest tools/die_plan/test_flowops1300_class_keep.py"""
import os, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import replica_keep as RK  # noqa: E402
import gen_phys  # noqa: E402
import pytest  # noqa: E402

HOOK = ROOT / "physical" / "common_flow" / "ot_keep_regs.tcl"

RTL = """
module ot_s81_rly #(parameter W = 4) (input wire clk, input wire [W-1:0] d, output reg [W-1:0] q);
  always @(posedge clk) q <= d;
endmodule
module ot_reset_sync #(parameter ASYNC_STAGES = 2) (input wire clk, rst_ni, output wire rst_no);
  (* async_reg = "true" *) reg [ASYNC_STAGES-1:0] reset_pipe;
  always @(posedge clk or negedge rst_ni) if (!rst_ni) reset_pipe <= 0; else reset_pipe <= {reset_pipe[ASYNC_STAGES-2:0], 1'b1};
  assign rst_no = reset_pipe[ASYNC_STAGES-1];
endmodule
module qc_st_a_station (input wire clk, input wire d, output reg rs_n_c);
  reg tmp;
  always @(posedge clk) begin rs_n_c <= d; end
  always @* tmp = d;
endmodule
module ot_x_sel_hist (input wire clk, input wire [3:0] d, output reg [3:0] gs1);
  reg [3:0] acc;
  always @(posedge clk) begin gs1 <= d; acc <= acc + d; end
endmodule
module ot_core_alu (input wire clk, input wire [3:0] a, output reg [3:0] q, output reg [1:0] sync_q);
  always @(posedge clk) begin q <= a + 1; sync_q <= {sync_q[0], a[0]}; end
endmodule
"""


def test_class_regs_modules_and_named():
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "k.sv").write_text(RTL)
        got = RK.class_regs(d)
        assert "ot_s81_rly:q" in got
        assert "ot_reset_sync:reset_pipe" in got
        assert "qc_st_a_station:rs_n_c" in got and "qc_st_a_station:tmp" not in got     # blocking comb reg is not a register
        assert "ot_x_sel_hist:gs1" in got and "ot_x_sel_hist:acc" not in got           # named fan-out flop only
        assert "ot_core_alu:sync_q" in got and "ot_core_alu:q" not in got              # ordinary logic module: named stages only
        assert got == sorted(set(got))


def test_gen_phys_keep_wires_carry_class_and_opt_out(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "k.sv").write_text(RTL)
        monkeypatch.delenv("OT_REPLICA_KEEP", raising=False)
        monkeypatch.delenv("OT_CLASS_KEEP", raising=False)
        w = gen_phys.replica_keep_wires(d, "extra_y")
        assert "ot_s81_rly:q" in w and "ot_reset_sync:reset_pipe" in w and "extra_y" in w
        monkeypatch.setenv("OT_CLASS_KEEP", "0")
        w = gen_phys.replica_keep_wires(d, "extra_y")
        assert "ot_s81_rly:q" not in w and "extra_y" in w
        monkeypatch.setenv("OT_REPLICA_KEEP", "0")
        monkeypatch.delenv("OT_CLASS_KEEP")
        assert gen_phys.replica_keep_wires(d, None) == []


def test_cli_class_flag(capsys):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "k.sv").write_text(RTL)
        RK.main([d, "--class"])
        assert "ot_s81_rly:q" in capsys.readouterr().out.split()


def test_hook_async_reg_block():
    t = HOOK.read_text()
    assert "w:* a:async_reg %i" in t and 'OT_ASYNC_REG_KEEP) ne "0"' in t
    assert t.index("OT_ASYNC_REG_KEEP") < t.index("yosys select -set ot_kw "), "keep must be set before the kept-FF selection"


DRIVE = r"""yosys -import
read_verilog -sv $::env(SRC)
hierarchy -check -top top
source $::env(HOOK)
synth -flatten -top top
puts "DFFBITS [string trim [tee -q -s result.string select -count t:\$_*DFF*]]"
"""
TOP = """module top (input wire clk, rst_ni, output wire a, b);
  ot_reset_sync u0 (.clk(clk), .rst_ni(rst_ni), .rst_no(a));
  ot_reset_sync u1 (.clk(clk), .rst_ni(rst_ni), .rst_no(b));
endmodule
"""


@pytest.mark.skipif(not shutil.which("yosys"), reason="yosys not on PATH (run inside the ORFS image)")
@pytest.mark.parametrize("env,bits", [({}, 4), ({"OT_ASYNC_REG_KEEP": "0"}, 2)])
def test_yosys_two_synchronisers_stay_two(env, bits):
    with tempfile.TemporaryDirectory() as d:
        src, tcl = Path(d) / "top.sv", Path(d) / "drive.tcl"
        src.write_text(RTL + TOP)
        tcl.write_text(DRIVE)
        e = {k: v for k, v in os.environ.items() if not k.startswith("OT_")}
        e.update(SRC=str(src), HOOK=str(HOOK), **env)
        p = subprocess.run(["yosys", "-q", "-c", str(tcl)], capture_output=True, text=True, env=e, timeout=300)
        assert p.returncode == 0, p.stderr[-2000:]
        assert ("DFFBITS %d" % bits) in p.stdout
