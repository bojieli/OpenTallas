"""drive-0849 2026-10-10: route-time IO reference defaults to the input pin flops (physical/qwen_die_masters/
pinflop_ref.tcl, used by io_ref_skew.sdc and every mc kit).  Structural checks always; an OpenROAD run when docker and
the ORFS image are available (a port -> BUF -> DFF and a port -> DFF are pin flops, a port -> AND -> DFF is not)."""
import shutil, subprocess, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "physical/qwen_die_masters"
NET = """module top(input clk, input a, input b, input c, input d, output q1);
  wire ab, cd;
  BUFx2_ASAP7_75t_R u_b (.A(a), .Y(ab));
  DFFHQNx1_ASAP7_75t_R r1 (.CLK(clk), .D(ab), .QN());
  DFFHQNx1_ASAP7_75t_R r2 (.CLK(clk), .D(b), .QN());
  DFFHQNx1_ASAP7_75t_R r4 (.CLK(clk), .D(d), .QN());
  AND2x2_ASAP7_75t_R u_a (.A(c), .B(d), .Y(cd));
  DFFHQNx1_ASAP7_75t_R r3 (.CLK(clk), .D(cd), .QN(q1));
endmodule
"""
TCL = """set L /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $L/lib/NLDM/*SEQ*RVT_TT*.lib* $L/lib/NLDM/*SIMPLE*RVT_TT*.lib* $L/lib/NLDM/*INVBUF*RVT_TT*.lib* $L/lib/NLDM/*AO*RVT_TT*.lib*] { read_liberty $f }
read_lef $L/lef/asap7_tech_1x_201209.lef
read_lef $L/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog /w/t.v
link_design top
create_clock -name core_clk -period 833 [get_ports clk]
source /w/pinflop_ref.tcl
puts "PF [lsort [lmap p [ot_pf_clks [all_inputs -no_clocks]] {get_full_name $p}]]"
puts "REF [get_full_name [ot_pf_ref [all_inputs -no_clocks]]]"
set ::env(OT_REF_PINFLOP) 0
puts "OPTOUT [llength [ot_pf_ref [all_inputs -no_clocks]]]"
"""
IMAGE = "openroad/orfs:latest"


class PinflopRef(unittest.TestCase):
    def test_wired_into_route_sdcs_not_signoff(self):
        s = (D / "io_ref_skew.sdc").read_text()
        self.assertIn("proc ot_pf_ref", s)
        self.assertIn("set qdm_ref [ot_pf_ref [all_inputs -no_clocks]]", s)
        self.assertIn("ot_pf_median $ot_gm", s)
        kits = list((D / "mc").glob("*/io_ref_skew.sdc"))
        self.assertTrue(any("ot_pf_ref [get_ports $ins]" in k.read_text() for k in kits))
        g = (D / "jobs/mk_mc_kit.py").read_text()
        self.assertIn("ref_so", g)            # sign-off SDC keeps the original reference

    @unittest.skipUnless(shutil.which("docker"), "no docker")
    def test_openroad_detects_pin_flops(self):
        if subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode:
            self.skipTest("no ORFS image")
        with tempfile.TemporaryDirectory() as t:
            Path(t, "t.v").write_text(NET)
            Path(t, "t.tcl").write_text(TCL)
            shutil.copy(D / "pinflop_ref.tcl", Path(t, "pinflop_ref.tcl"))
            r = subprocess.run(["docker", "run", "--rm", "-v", f"{t}:/w", IMAGE, "/OpenROAD-flow-scripts/tools/install/"
                                "OpenROAD/bin/openroad", "-no_init", "-exit", "/w/t.tcl"], capture_output=True, text=True,
                               timeout=600)
        out = r.stdout + r.stderr
        self.assertIn("PF r1/CLK r2/CLK r4/CLK", out)
        self.assertRegex(out, r"REF r[124]/CLK")
        self.assertIn("OPTOUT 0", out)


class Overlay(unittest.TestCase):
    def test_overlay_patches_old_snapshot_idempotently(self):
        import sys
        sys.path.insert(0, str(ROOT / "tools/closure_loop"))
        import pinflop_overlay as po
        import closure_loop as cl
        procs = (D / "pinflop_ref.tcl").read_text()
        head = "set ot_glob x\nunset_input_delay [all_inputs]\n"
        new = po.patch(head + po.MAIN_OLD, procs)
        self.assertIn("ot_pf_ref [all_inputs -no_clocks]", new)
        self.assertIsNone(po.patch(new, procs))
        self.assertIn('$ot_glob ne "*"', new)                     # REFGLOB='*' is no reference
        self.assertIn("ot_pf_median $ot_gm", new)                 # a matching glob -> its median member
        self.assertEqual(new, po.patch(head + po.MAIN_OLD, procs))
        kit = "# kit\nforeach {clk sk ins outs} {\n  ck 150 {a} {b}\n} {\n" + po.KIT_OLD + "  set_input_delay 1 [get_ports $ins]\n}\n"
        self.assertIn("ot_pf_ref [get_ports $ins]", po.patch(kit, procs))
        self.assertIn("pinflop_overlay.py", cl.HELPERS)
        self.assertIn("pinflop_overlay.py", Path(cl.__file__).read_text())


class InputPinflopRouteTime(unittest.TestCase):
    def test_wiring(self):
        import sys
        sys.path.insert(0, str(ROOT / "tools/closure_loop"))
        import closure_loop as cl
        self.assertEqual(cl.DOCKER_SHIM.count("-e OT_IOREF_INPUT_PF"), 2)
        src = Path(cl.__file__).read_text()
        self.assertIn('env += "export OT_IOREF_INPUT_PF=1\\n"', src)
        sdc = (ROOT / "physical/common_flow/io_ref_routed.sdc").read_text()
        self.assertIn('$::env(OT_IOREF_INPUT_PF) eq "1"', sdc)

    @unittest.skipUnless(shutil.which("docker"), "no docker")
    def test_openroad_inputs_move_outputs_stay(self):
        if subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode:
            self.skipTest("no ORFS image")
        net = """module top(input clk, input a, input b, input c, output q1);
  wire cd, ck2;
  BUFx2_ASAP7_75t_R u_ck (.A(clk), .Y(ck2));
  DFFHQNx1_ASAP7_75t_R r1 (.CLK(ck2), .D(a), .QN());
  DFFHQNx1_ASAP7_75t_R r2 (.CLK(ck2), .D(b), .QN());
  AND2x2_ASAP7_75t_R u_a (.A(c), .B(b), .Y(cd));
  DFFHQNx1_ASAP7_75t_R r3 (.CLK(clk), .D(cd), .QN(q1));
endmodule
"""
        head = TCL.split("source /w/pinflop_ref.tcl")[0]
        body = """create_clock -name vclk -period 833
set_clock_latency 100 [get_clocks vclk]
set_input_delay 316.6 -clock vclk [all_inputs -no_clocks]
set_input_delay -min 0 -clock vclk [all_inputs -no_clocks]
set_output_delay 316.6 -clock vclk [all_outputs]
set_output_delay -min 0 -clock vclk [all_outputs]
set_propagated_clock [get_clocks core_clk]
if {[info exists ::env(PF)]} { set ::env(OT_IOREF_INPUT_PF) 1 }
source /w/io_ref_routed.sdc
write_sdc /tmp/y.sdc
puts [exec grep -E "_delay" /tmp/y.sdc]
"""
        outs = {}
        for pf in (False, True):
            with tempfile.TemporaryDirectory() as t:
                Path(t, "t.v").write_text(net)
                Path(t, "t.tcl").write_text(head + body)
                shutil.copy(ROOT / "physical/common_flow/io_ref_routed.sdc", Path(t, "io_ref_routed.sdc"))
                r = subprocess.run(["docker", "run", "--rm", *(["-e", "PF=1"] if pf else []), "-v", f"{t}:/w", IMAGE,
                                    "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad", "-no_init", "-exit",
                                    "/w/t.tcl"], capture_output=True, text=True, timeout=600)
                outs[pf] = r.stdout + r.stderr
        import re
        mn = lambda o, p: float(re.search(r"set_input_delay (\S+) -clock \[get_clocks \{vclk\}\] -min -add_delay \[get_ports \{%s\}\]" % p, o).group(1))
        om = lambda o: float(re.search(r"set_output_delay (\S+) -clock \[get_clocks \{vclk\}\] -min", o).group(1))
        self.assertEqual(mn(outs[False], "a"), 0.0)                  # off: unchanged
        self.assertIn("OT_IOREF_PF input pin flops 2", outs[True])
        self.assertGreater(mn(outs[True], "a"), 0.0)                 # pin flops later than the boundary mean
        self.assertEqual(om(outs[True]), om(outs[False]))            # outputs keep the boundary mean


if __name__ == "__main__":
    unittest.main()
