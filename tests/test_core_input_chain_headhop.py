"""CB-HEADHOP / CB-LOCKUP (FABLE-QC-CB 11-14): tools/die_plan/core_input_chain.tcl sites the HEAD hop of a pipe chain
on the route (it used to leave the head-hop inverter where global placement put it, across the tile), and
core_input_anchor.tcl anchors the pipe register behind the anonymous QN inverter of the lock-up latch.

Fixture (OpenROAD of the ORFS image, ASAP7, one hard macro TILE 100 x 100 um): the head-hop inverter starts in the far
corner.  Case A: hard-core head (TILE.O -> s0 -> inverter -> s1 -> pc): the inverter must end between s0 and s1 on the
route.  Case B: movable head with one load: same.  Case C: head-hop inverter with two loads: it stays put (shared).
Case D: anchor, QN inverter between u_pc_nk register and u_lk_nk latch: pipe_regs 1.
Skipped when docker or the image is missing (OT_IOREF_DOCKER_IMAGE overrides it)."""
import os, re, shutil, subprocess, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "tools/die_plan/core_input_chain.tcl"
ANCHOR = ROOT / "tools/die_plan/core_input_anchor.tcl"
IMAGE = os.environ.get("OT_IOREF_DOCKER_IMAGE", "openroad/orfs:latest")
P = "/OpenROAD-flow-scripts/flow/platforms/asap7/lef"

LEF = """VERSION 5.8 ;
MACRO TILE
  CLASS BLOCK ;
  ORIGIN 0 0 ;
  SIZE 100 BY 100 ;
  SYMMETRY X Y R90 ;
  PIN O
    DIRECTION OUTPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT 99.9 50 100 50.1 ;
    END
  END O
  PIN I
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT 99.9 70 100 70.1 ;
    END
  END I
END TILE
END LIBRARY
"""

NET = """module top(input clk);
  wire o, q0, q0n, q1, q2, q3, h, h0, h0n, h1, h2, ha, hb, hc, sh, sh0, sh0n, sh1, sh2, ld, ln, pq, pqn;
  TILE u_t (.O(o), .I(ln));
  // case A: hard-core head
  DFFHQNx1_ASAP7_75t_R u_d3_a_s0 (.CLK(clk), .D(o), .QN(q0));
  INVx1_ASAP7_75t_R hinv_a (.A(q0), .Y(q0n));
  DFFHQNx1_ASAP7_75t_R u_d3_a_s1 (.CLK(clk), .D(q0n), .QN(q1));
  DFFHQNx1_ASAP7_75t_R u_d3_a_s2 (.CLK(clk), .D(q1), .QN(q2));
  DFFHQNx1_ASAP7_75t_R u_pc_nk_a_n_a (.CLK(clk), .D(q2), .QN(q3));
  // case B: movable head, one load
  DFFHQNx1_ASAP7_75t_R u_src_b (.CLK(clk), .D(q3), .QN(h));
  INVx1_ASAP7_75t_R hinv_b (.A(h), .Y(h0n));
  DFFHQNx1_ASAP7_75t_R u_d3_b_s0 (.CLK(clk), .D(h0n), .QN(h1));
  DFFHQNx1_ASAP7_75t_R u_pc_nk_b_n_a (.CLK(clk), .D(h1), .QN(h2));
  // case C: movable head, two loads (shared head hop)
  DFFHQNx1_ASAP7_75t_R u_src_c (.CLK(clk), .D(h2), .QN(sh));
  INVx1_ASAP7_75t_R hinv_c (.A(sh), .Y(sh0n));
  DFFHQNx1_ASAP7_75t_R u_d3_c_s0 (.CLK(clk), .D(sh0n), .QN(sh1));
  DFFHQNx1_ASAP7_75t_R u_pc_nk_c_n_a (.CLK(clk), .D(sh1), .QN(sh2));
  DFFHQNx1_ASAP7_75t_R u_other_c (.CLK(clk), .D(sh0n), .QN(hc));
  // case E: xstn tap_d register across the tile from its tap face (pipe register FIRM at the east face)
  wire xb, xt, xq, xe1;
  DFFHQNx1_ASAP7_75t_R \\xs.u_st.b_d0 (.CLK(clk), .D(hc), .QN(xb));
  DFFHQNx1_ASAP7_75t_R \\xs.u_st.tap_d0 (.CLK(clk), .D(xb), .QN(xt));
  DFFHQNx1_ASAP7_75t_R \\u_pc_nk_u_t_0_0_tap.q0 (.CLK(clk), .D(xt), .QN(xq));
  // case D: anchor
  DFFHQNx1_ASAP7_75t_R u_pc_nk_d_n_a (.CLK(clk), .D(hc), .QN(pq));
  INVx1_ASAP7_75t_R _123_ (.A(pq), .Y(pqn));
  DLLx1_ASAP7_75t_R u_lk_nk_d_n_a (.CLK(clk), .D(pqn), .Q(ln));
endmodule
"""

TCL = r"""
read_lef %(P)s/asap7_tech_1x_201209.lef
read_lef %(P)s/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /t/tile.lef
read_verilog /t/top.v
link_design top
initialize_floorplan -die_area "0 0 400 400" -core_area "0 0 400 400" -site asap7sc7p5t
set tb_blk [ord::get_db_block]; set tb_u [[ord::get_db_tech] getDbUnitsPerMicron]
proc put {n x y {st PLACED}} { global tb_blk tb_u; set pi [$tb_blk findInst $n]; $pi setLocation [expr {int($x*$tb_u)}] [expr {int($y*$tb_u)}]; $pi setPlacementStatus $st }
put u_t 150 150 FIRM
put u_d3_a_s0 360 200 ;  put hinv_a 20 380 ; put u_d3_a_s1 360 360 ; put u_d3_a_s2 360 300 ; put u_pc_nk_a_n_a 360 20
put u_src_b 20 20 ;  put hinv_b 20 380 ; put u_d3_b_s0 30 30 ; put u_pc_nk_b_n_a 20 300
put u_src_c 100 20 ; put hinv_c 20 380 ; put u_d3_c_s0 110 30 ; put u_pc_nk_c_n_a 100 100 ; put u_other_c 390 390
put xs.u_st.b_d0 20 20 ; put xs.u_st.tap_d0 30 20 ; put u_pc_nk_u_t_0_0_tap.q0 256 160 FIRM
put u_pc_nk_d_n_a 300 20 ; put _123_ 300 30; put u_lk_nk_d_n_a 300 40
set ::env(RESULTS_DIR) /t
puts "TESTRUN chain"
source %(chain)s
puts "TESTRUN anchor"
source %(anchor)s
foreach n {xs.u_st.b_d0 xs.u_st.tap_d0 hinv_a u_d3_a_s0 u_d3_a_s1 hinv_b u_src_b u_d3_b_s0 hinv_c u_pc_nk_d_n_a _123_ u_lk_nk_d_n_a} {
  set pi [$tb_blk findInst $n]; set pb [$pi getBBox]
  puts "POS $n [expr {double([$pb xMin])/$tb_u}] [expr {double([$pb yMin])/$tb_u}] [$pi getPlacementStatus]"
}
exit
"""


def have_image():
    return bool(shutil.which("docker")) and \
        subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode == 0


def run_fixture(chain=CHAIN, anchor=ANCHOR, env=None):
    d = tempfile.mkdtemp(prefix="cih_")
    os.chmod(d, 0o777)
    Path(d, "tile.lef").write_text(LEF)
    Path(d, "top.v").write_text(NET)
    shutil.copy(chain, Path(d, "chain.tcl")); shutil.copy(anchor, Path(d, "anchor.tcl"))
    tcl = TCL % dict(P=P, chain="/t/chain.tcl", anchor="/t/anchor.tcl")
    for k, v in (env or {}).items():
        tcl = tcl.replace("set ::env(RESULTS_DIR) /t", f"set ::env(RESULTS_DIR) /t\nset ::env({k}) {v}")
    Path(d, "t.tcl").write_text(tcl)
    r = subprocess.run(["docker", "run", "--rm", "-v", f"{d}:/t", IMAGE, "bash", "-lc",
                        "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_splash -exit /t/t.tcl"],
                       capture_output=True, text=True, timeout=600)
    shutil.rmtree(d, ignore_errors=True)
    out = r.stdout + r.stderr
    pos = {m.group(1): (float(m.group(2)), float(m.group(3)), m.group(4)) for m in re.finditer(r"^POS (\S+) (\S+) (\S+) (\S+)", out, re.M)}
    return out, pos


@unittest.skipUnless(have_image(), f"docker image {IMAGE} not available")
class HeadHop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out, cls.pos = run_fixture()

    def test_ran(self):
        self.assertIn("OT_NK_CHAIN", self.out, self.out[-2000:])
        self.assertIn("head_hop_cells_moved", self.out)

    def test_hard_core_head_hop_inverter_on_route(self):
        # inverter started at (20, 380); s0 (360, 200) -> s1 stays on the route between the pin stage and the pipe register
        x, y, _ = self.pos["hinv_a"]
        s0 = self.pos["u_d3_a_s0"]
        self.assertGreater(x, 100, f"head-hop inverter still across the tile at {x},{y}\n{self.out[-1500:]}")
        self.assertLess(abs(x - s0[0]) + abs(y - s0[1]), 250)

    def test_movable_head_hop_inverter_on_route(self):
        x, y, _ = self.pos["hinv_b"]
        h = self.pos["u_src_b"]
        self.assertLess(abs(x - h[0]) + abs(y - h[1]), 400, f"{x},{y}")

    def test_shared_head_hop_stays(self):
        x, y, _ = self.pos["hinv_c"]
        self.assertAlmostEqual(x, 20, delta=1)
        self.assertAlmostEqual(y, 380, delta=1)

    def test_anchor_follows_qn_inverter_by_type(self):
        self.assertRegex(self.out, r"OT_NK_ANCHOR latches 1 pipe_regs 1 ")
        for n in ("u_pc_nk_d_n_a", "_123_", "u_lk_nk_d_n_a"):
            self.assertEqual(self.pos[n][2], "FIRM", n)

    def test_xstn_sited_at_tap_face(self):
        # tile TILE spans x 150..250; the tap face is east (pipe register at 256); strip = 100 um outside it
        for n in ("xs.u_st.tap_d0", "xs.u_st.b_d0"):
            x, y, _ = self.pos[n]
            self.assertTrue(250 <= x <= 360, f"{n} at {x},{y}\n{self.out[-1500:]}")
        self.assertRegex(self.out, r"OT_XSTN_SITE xstn 1 kept 0 kept_external 0 moved 1 ")

    def test_xstn_with_external_output_stays(self):
        out, pos = run_fixture(env={"OT_NK_XSTN_EXT_MAX": "-1"})
        self.assertIn("OT_XSTN_KEEP", out)
        self.assertLess(pos["xs.u_st.tap_d0"][0], 100)

    def test_old_hook_leaves_it(self):
        # control: the pre-fix hook (git show of the parent) leaves hinv_a at the far corner
        old = os.environ.get("OT_CHAIN_OLD")
        if not old:
            self.skipTest("OT_CHAIN_OLD not set")
        _, pos = run_fixture(chain=old)
        self.assertAlmostEqual(pos["hinv_a"][0], 20, delta=1)


if __name__ == "__main__":
    unittest.main()
