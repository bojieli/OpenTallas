"""S81 strip form B: s81_vp_xr_overlay.py on the D3 (current819) VP / slice sources (fixtures/s81_vp_xr, gzip copies of
the elaboration tree src_s81_pin_3c913dbdfb23_f2s4_cohort_d3 plus the 16 die slice instance lines of die_b178_lfcs.v)."""
import gzip
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s81_vp_xr_overlay as X  # noqa: E402

FX = HERE / "fixtures/s81_vp_xr"
SL = "rtl/dsrom_sys/s81_dv/slice"
FILES = {
    "ot_s81sl_vp.sv.gz": f"{SL}/ot_s81sl_vp.sv",
    "ot_s81sl_slice.sv.gz": f"{SL}/ot_s81sl_slice.sv",
    "ot_s81sl_slice_w3.sv.gz": f"{SL}/cap_end/ot_s81sl_slice_w3.sv",
    "ot_s81sl_slice_c1x_k8_cap5r_w_w3.sv.gz": f"{SL}/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_w_w3.sv",
    "ot_s81sl_slice_c1x_k8_cap5r_lp_w3.sv.gz": f"{SL}/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp_w3.sv",
    "die_b178_lfcs_slices.v.gz": "physical/die_plan/s81/bind/inputs/die_b178_lfcs.v",
}


@pytest.fixture
def tree(tmp_path):
    for src, dst in FILES.items():
        p = tmp_path / dst
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(gzip.decompress((FX / src).read_bytes()))
    (tmp_path / "physical/die_plan/s81/bind/source_modules").mkdir(parents=True, exist_ok=True)
    return tmp_path


def snapshot(root):
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_overlay_forwards_mask_and_activates_only_t34_t62(tree):
    assert X.main([str(tree), "--die", "3S=01000", "--die", "6N=00010"]) == 0
    vp = (tree / X.VP).read_text()
    assert "parameter integer XR = `OT_S81SL_VP_XR_DEFAULT," in vp
    assert "localparam integer CS_HI_E = CS_HI_D + XR;" in vp
    assert ".TREE_STAGES(1 + XR)) u_rr" in vp
    assert ".D(CS_HI_E - CS_HI_GS + HIM)" in vp and ".D(CS_HI_D - CS_HI_GS + HIM)" not in vp
    assert "ot_s81sl_vpw #(.XR(XR)) u_w (" in vp
    # DSR: dswp select = 16 kept copies loaded from dswp1 (like dswp, so cycle-exact); XR 0 keeps the single select
    assert "localparam integer DSR = (XR != 0) ? 16 : 1;" in vp
    assert "(* keep *) reg [DSR-1:0] dswp_q;" in vp and "always @(posedge clk) dswp_q <= {DSR{dswp1}};" in vp
    assert "assign qe = dswp ? q1 : q0; assign qo = dswp ? q0 : q1;" in vp
    assert "wire [127:0] qe = dswp" not in vp
    assert "dswp <= dswp1;" in vp                               # the original stage is unchanged
    vpw = vp[vp.index("module ot_s81sl_vpw"):]
    for n, _ in X.WRITERS:                       # every writer and payload goes through the stage
        assert f"assign {n}_i = {n}_q;" in vpw and f"assign {n}_i = {n};" in vpw
    leaf = (tree / f"{SL}/ot_s81sl_slice.sv").read_text()
    assert "parameter integer VP_XR = 0," in leaf and "ot_s81sl_vp #(.XR(VP_XR), .CS_HI_D" in leaf
    w3 = (tree / f"{SL}/cap_end/ot_s81sl_slice_w3.sv").read_text()
    assert ".VP_XR(LF_VP_XR[k])" in w3                          # slice_w3 leaf k
    assert w3.count(".LF_VP_XR(LF_VP_XR), .LF_CS_HI_D(LF_CS_HI_D)") == 2   # iq_w3 + sukv -> slice_w3
    lp = (tree / f"{SL}/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp_w3.sv").read_text()
    assert [int(i) for i in re.findall(r"\.VP_XR\(LF_VP_XR\[(\d)\]\)", lp)] == [0, 1, 2, 3, 4]
    ww = (tree / f"{SL}/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_w_w3.sv").read_text()
    assert ".LF_VP_XR(LF_VP_XR), .LF_CS_HI_D(LF_CS_HI_D)" in ww
    for t in (w3, lp, ww):                                         # every slice header declares the mask, default 0
        assert len(re.findall(r"parameter \[4:0\] LF_VP_XR = 5'd0, parameter \[19:0\] LF_CS_HI_D = ", t)) == \
            len(re.findall(r"parameter \[19:0\] LF_CS_HI_D = ", t))
    die = (tree / "physical/die_plan/s81/bind/inputs/die_b178_lfcs.v").read_text()
    assert re.search(r"ot_s81sl_slice_iq_w3 #\(\.LF_VP_XR\(5'b01000\), .*\) u_s_3S \(", die)
    assert re.search(r"ot_s81sl_slice_c1x_k8_cap5r_w_w3 #\(\.LF_VP_XR\(5'b00010\), .*\) u_s_6N \(", die)
    assert die.count("LF_VP_XR") == 2                              # the 14 other slices stay XR 0


def test_refusals_leave_tree_unchanged(tree):
    before = snapshot(tree)
    with pytest.raises(SystemExit, match="XR_DIE_MISS"):
        X.main([str(tree), "--die", "9Q=00001"])
    with pytest.raises(SystemExit, match="XR_DIE_BAD_MASK"):
        X.main([str(tree), "--die", "3S=0100"])
    assert snapshot(tree) == before                                # atomic: nothing written on a refusal
    X.main([str(tree)])
    with pytest.raises(SystemExit, match="XR_OVERLAY_TWICE"):
        X.main([str(tree)])


def test_refuses_source_without_wrp(tree):
    p = tree / X.VP
    s = p.read_text()
    p.write_text(s[:s.index("module ot_s81sl_vpw")])
    with pytest.raises(SystemExit, match="XR_OVERLAY_NO_WRP"):
        X.main([str(tree)])


@pytest.mark.skipif(shutil.which("iverilog") is None or shutil.which("vvp") is None, reason="iverilog not installed")
def test_vpw_xr_bench_and_bypass_mutant(tree, tmp_path_factory):
    base = gzip.decompress((FX / "ot_s81sl_vp.sv.gz").read_bytes()).decode()
    X.main([str(tree)])
    xr = (tree / X.VP).read_text()
    w = tmp_path_factory.mktemp("bench")
    (w / "base.sv").write_text(base[base.index("module ot_s81sl_vpw"):].replace("module ot_s81sl_vpw",
                                                                               "module ot_s81sl_vpw_base", 1))
    (w / "xr.sv").write_text(xr[xr.index("module ot_s81sl_vpw"):])
    tb = FX / "tb_vpw_xr.sv"

    def run(*defs):
        out = w / ("m.vvp" if defs else "p.vvp")
        subprocess.run(["iverilog", "-g2012", *defs, "-o", str(out), str(tb), str(w / "base.sv"), str(w / "xr.sv")],
                       check=True, capture_output=True)
        return subprocess.run(["vvp", "-n", str(out)], capture_output=True, text=True)

    ok = run()
    assert "PASS XR write port delay" in ok.stdout, ok.stdout + ok.stderr
    assert int(re.search(r"checks=(\d+)", ok.stdout).group(1)) > 9000
    bad = run("-DMUTANT")
    assert "XR control mismatch" in bad.stdout + bad.stderr


@pytest.mark.skipif(shutil.which("iverilog") is None or shutil.which("vvp") is None, reason="iverilog not installed")
def test_lane_reset_copy_miter_and_early_stage_mutant(tree, tmp_path):
    # The minimum changed mechanism is the real VP reset tree. Arithmetic and
    # memory children are left unresolved (-i); no arithmetic is simulated or
    # claimed. Check the actual generated VP's control and16 lane reset pins.
    X.main([str(tree), "--lane-reset-copies", "--die", "3S=01000", "--die", "6N=00010"])
    vp = tree / X.VP
    relay = Path(__file__).resolve().parents[2] / "rtl/lib/ot_rst_relay.sv"
    assert relay.is_file(), relay
    bench = tmp_path / "reset_tb.sv"
    bench.write_text(r'''
`timescale 1ns/1ps
module tb;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=1;
 wire [3:0] r0,r1;
 ot_rst_relay #(.REGIONS(4),.TREE_STAGES(1)) ref0(.clk(clk),.rst_n_in(rst_n),.rst_n(r0));
 ot_rst_relay #(.REGIONS(4),.TREE_STAGES(2)) ref1(.clk(clk),.rst_n_in(rst_n),.rst_n(r1));
 ot_s81sl_vp #(.XR(0)) dut0(.clk(clk),.rst_n(rst_n));
 ot_s81sl_vp #(.XR(1)) dut1(.clk(clk),.rst_n(rst_n));
 integer i,checks=0,pulses=0; reg [31:0] r;
 initial begin
  rst_n=0;
  for(i=0;i<2000;i=i+1) begin
   @(negedge clk); #2; r=$random;
   rst_n=(i%31>2 && r[4:0]!=0); if(!rst_n) pulses=pulses+1;
   @(posedge clk); #1;
   if(dut0.rsv !== r0 || dut0.rs_ln !== {16{r0[2]}}) $fatal(1,"XR0 reset mismatch %0d",i);
   if(dut1.rsv[3:0] !== r1 || dut1.rs_ln !== {16{r1[2]}}) $fatal(1,"lane reset mismatch %0d",i);
   checks=checks+1;
  end
  $display("PASS lane reset copies checks=%0d reset_pulses=%0d",checks,pulses);$finish;
 end
endmodule
''')
    def run(source, tag):
        out = tmp_path / (tag + ".vvp")
        subprocess.run(["iverilog", "-g2012", "-i", "-s", "tb", "-o", str(out), str(relay), str(source), str(bench)],
                       check=True, capture_output=True)
        return subprocess.run(["vvp", "-n", str(out)], capture_output=True, text=True)
    ok = run(vp, "positive")
    assert ok.returncode == 0 and "checks=2000" in ok.stdout, ok.stdout + ok.stderr
    mutant = tmp_path / "vp_mut.sv"
    source = vp.read_text()
    assert source.count(".TREE_STAGES(1 + XR)) u_rr") == 1
    mutant.write_text(source.replace(".TREE_STAGES(1 + XR)) u_rr", ".TREE_STAGES(1)) u_rr"))
    bad = run(mutant, "early_stage")
    assert bad.returncode != 0 and "lane reset mismatch" in bad.stdout + bad.stderr
