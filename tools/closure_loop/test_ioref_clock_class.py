"""CLOCK-CLASS 2026-10-13 (export-sdc; smh_tile_eg r10 raw / gated diagnosis): the boundary reference is per clock class.

A tile with one raw-clocked boundary flop (ports a -> r_raw -> qa on the clk port net) beside gated-class boundary
flops behind a long clock branch (b* -> r_g* -> qb*), and a port (m) captured in both classes.  With one reference per
clock the raw ports read a false violation of about the class distance; per class every port is referenced to the
registers that launch / capture it, in physical/common_flow/io_ref_routed.sdc (verdict, hold ECO, export replay) and
physical/common_flow/link_budget_consistent.sdc alike, and reading the files again changes nothing.  OpenROAD runs need
docker and the ORFS image."""
import re, shutil, subprocess, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CF = ROOT / "physical/common_flow"
IMAGE = "openroad/orfs:latest"
NBUF, NG = 90, 4
NET = ("module top(input clk, input a, input m, input [%d:0] b, output qa, output [%d:0] qb);\n" % (NG - 1, NG - 1)
       + "  wire [%d:0] g;\n  assign g[0] = clk;\n" % NBUF
       + "".join(f"  BUFx2_ASAP7_75t_R u_ck{i} (.A(g[{i}]), .Y(g[{i + 1}]));\n" for i in range(NBUF))
       + "  DFFHQNx1_ASAP7_75t_R r_raw (.CLK(clk), .D(a), .QN(qa));\n"
       + "  DFFHQNx1_ASAP7_75t_R r_rawm (.CLK(clk), .D(m), .QN());\n"
       + "  DFFHQNx1_ASAP7_75t_R r_gm (.CLK(g[%d]), .D(m), .QN());\n" % NBUF
       + "".join(f"  DFFHQNx1_ASAP7_75t_R r_g{i} (.CLK(g[{NBUF}]), .D(b[{i}]), .QN(qb[{i}]));\n" for i in range(NG))
       + "endmodule\n")
HEAD = """set L /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $L/lib/NLDM/*SEQ*RVT_TT*.lib* $L/lib/NLDM/*SIMPLE*RVT_TT*.lib* $L/lib/NLDM/*INVBUF*RVT_TT*.lib*] { read_liberty $f }
read_lef $L/lef/asap7_tech_1x_201209.lef
read_lef $L/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog /w/t.v
link_design top
create_clock -name core_clk -period 833.333 [get_ports clk]
set_propagated_clock [all_clocks]
proc S {tag} {
  foreach {n spec} {a {-from [get_ports a]} b {-from [get_ports {b[0]}]} qa {-to [get_ports qa]} qb {-to [get_ports {qb[0]}]}} {
    foreach mm {min max} {
      set pe [find_timing_paths -path_delay $mm {*}[subst $spec]]
      puts "S $tag $n $mm [expr {[llength $pe] ? [get_property [lindex $pe 0] slack] : "none"}]"
    }
  }
}
"""
IOREF = HEAD + """create_clock -name vclk -period 833.333
set_input_delay -max 166.7 -clock vclk [all_inputs -no_clocks]
set_input_delay -min 30 -clock vclk [all_inputs -no_clocks]
set_output_delay -max 166.7 -clock vclk [all_outputs]
set_output_delay -min -25 -clock vclk [all_outputs]
set ::env(OT_IOREF_CLASS) 0
read_sdc /w/io_ref_routed.sdc
S one
set ::env(OT_IOREF_CLASS) 1
read_sdc /w/io_ref_routed.sdc
S cls
read_sdc /w/io_ref_routed.sdc
S again
"""
BAKED = HEAD + """sta::redirect_string_begin; report_clock_latency; sta::redirect_string_end
set Lg [get_property [get_pins r_g0/CLK] arrival_max_rise]
set_input_delay -max [expr {166.7 + $Lg + 90}] -clock core_clk [all_inputs -no_clocks]
set_input_delay -min [expr {$Lg - 50}] -clock core_clk [all_inputs -no_clocks]
set_output_delay -max [expr {166.7 - $Lg + 90}] -clock core_clk [all_outputs]
set_output_delay -min [expr {0 - $Lg - 50}] -clock core_clk [all_outputs]
S one
read_sdc /w/io_ref_routed.sdc
S cls
read_sdc /w/io_ref_routed.sdc
S again
"""
LB = HEAD + """read_sdc /w/link_budget_consistent.sdc
S lb
read_sdc /w/io_ref_routed.sdc
S lbio
read_sdc /w/io_ref_routed.sdc
S lbio2
"""


def run(tcl):
    with tempfile.TemporaryDirectory() as t:
        Path(t, "t.v").write_text(NET)
        Path(t, "t.tcl").write_text(tcl)
        for f in ("io_ref_routed.sdc", "link_budget_consistent.sdc"):
            shutil.copy(CF / f, Path(t, f))
        r = subprocess.run(["docker", "run", "--rm", "-v", f"{t}:/w", IMAGE, "/OpenROAD-flow-scripts/tools/install/"
                            "OpenROAD/bin/openroad", "-no_init", "-exit", "/w/t.tcl"], capture_output=True, text=True,
                           timeout=900)
    out = r.stdout + r.stderr
    s = {(m[0], m[1], m[2]): float(m[3]) for m in re.findall(r"^S (\S+) (\S+) (min|max) (-?[0-9.eE+-]+)$", out, re.M)}
    return out, s


def have_image():
    return shutil.which("docker") and not subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode


class ClockClass(unittest.TestCase):
    def test_structural(self):
        io = (CF / "io_ref_routed.sdc").read_text()
        lb = (CF / "link_budget_consistent.sdc").read_text()
        for s in (io, lb):
            self.assertIn("::ot_cls_adj", s)
            self.assertIn("OT_IOREF_CLASS", s)
        self.assertIn("OT_IOREF_CLASS_GAP", io)

    @unittest.skipUnless(have_image(), "no docker / ORFS image")
    def test_ioref_references_each_port_to_its_class(self):
        out, s = run(IOREF)
        self.assertNotIn("Error", out, out[-3000:])
        cls = re.findall(r"^OT_IOREF_CLASS core_clk class (\d)( dominant)? mean (\S+) .* n (\d+) ports_in (\d+) ports_out (\d+)", out, re.M)
        self.assertEqual(len(cls), 4, out[-3000:])                   # 2 classes, printed by the 2nd and 3rd read
        raw, gated = cls[0], cls[1]
        self.assertEqual((raw[1], raw[3:]), ("", ("2", "1", "1")))  # r_raw + r_rawm; ports a / qa
        self.assertEqual((gated[1], gated[3]), (" dominant", str(NG + 1)))
        dist = float(gated[2]) - float(raw[2])
        self.assertGreater(dist, 400)
        self.assertRegex(out, r"OT_IOREF_CLASS core_clk mixed 1 ports .*m\(in: 0\+1\)")
        # one reference per clock: the raw ports are off by about the class distance (false violations)
        self.assertLess(s["one", "qa", "min"], -100)
        self.assertLess(s["one", "a", "max"], -100)
        # per class: a raw port reads what the same port on the gated class reads
        for n_raw, n_g in (("a", "b"), ("qa", "qb")):
            for mm in ("min", "max"):
                self.assertAlmostEqual(s["cls", n_raw, mm], s["cls", n_g, mm], delta=80, msg=f"{n_raw} {mm} {s}")
                self.assertEqual(s["cls", n_raw, mm], s["again", n_raw, mm])      # a second read applies nothing twice
                self.assertEqual(s["cls", n_g, mm], s["again", n_g, mm])
        self.assertGreaterEqual(s["cls", "qa", "min"], 0)
        self.assertEqual(len(re.findall(r"OT_IOREF_CLASS \d+ IO delays re-referenced", out)), 1)

    @unittest.skipUnless(have_image(), "no docker / ORFS image")
    def test_reference_baked_into_real_clock_delays(self):
        # the kit sign-off form (io_ref_skew.sdc): delays on core_clk with the gated pin-flop arrival in the value
        out, s = run(BAKED)
        self.assertNotIn("Error", out, out[-3000:])
        self.assertLess(s["one", "a", "max"], -400)        # smh cgi: gated reference captured by a raw flop
        self.assertLess(s["one", "qa", "min"], -400)       # smh cgo
        for n_raw, n_g in (("a", "b"), ("qa", "qb")):
            for mm in ("min", "max"):
                self.assertAlmostEqual(s["cls", n_raw, mm], s["cls", n_g, mm], delta=80, msg=f"{n_raw} {mm} {s}")
                self.assertEqual(s["cls", n_raw, mm], s["again", n_raw, mm])
                self.assertEqual(s["one", n_g, mm], s["cls", n_g, mm])           # the dominant class is untouched

    @unittest.skipUnless(have_image(), "no docker / ORFS image")
    def test_link_budget_then_ioref_is_the_same_reference(self):
        out, s = run(LB)
        self.assertNotIn("Error", out, out[-3000:])
        self.assertRegex(out, r"OT_LINK_BUDGET clock core_clk .*class")
        for tag in ("lb", "lbio", "lbio2"):
            for n_raw, n_g in (("a", "b"), ("qa", "qb")):
                self.assertAlmostEqual(s[tag, n_raw, "max"], s[tag, n_g, "max"], delta=80, msg=f"{tag} {n_raw} {s}")
        for k in [k for k in s if k[0] == "lbio"]:
            self.assertEqual(s[k], s[("lbio2",) + k[1:]])


if __name__ == "__main__":
    unittest.main()
