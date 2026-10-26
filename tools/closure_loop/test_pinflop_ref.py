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
        # svc-fix 2026-10-10: r4 is a pin flop on a FORWARDED clock (fk): not on the moved reference tree, so it is
        # not averaged into the input reference ("input pin flops 2", not 3)
        net = """module top(input clk, input fk, input a, input b, input c, input d, output q1);
  wire cd, ck2;
  DFFHQNx1_ASAP7_75t_R r4 (.CLK(fk), .D(d), .QN());
  BUFx2_ASAP7_75t_R u_ck (.A(clk), .Y(ck2));
  DFFHQNx1_ASAP7_75t_R r1 (.CLK(ck2), .D(a), .QN());
  DFFHQNx1_ASAP7_75t_R r2 (.CLK(ck2), .D(b), .QN());
  AND2x2_ASAP7_75t_R u_a (.A(c), .B(b), .Y(cd));
  DFFHQNx1_ASAP7_75t_R r3 (.CLK(clk), .D(cd), .QN(q1));
endmodule
"""
        head = TCL.split("source /w/pinflop_ref.tcl")[0]
        body = """create_clock -name fkc -period 833 [get_ports fk]
create_clock -name vclk -period 833
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
                shutil.copy(D / "pinflop_ref.tcl", Path(t, "pinflop_ref.tcl"))   # PF-HOLDPAD: the shipped {CL} pair
                r = subprocess.run(["docker", "run", "--rm", *(["-e", "PF=1"] if pf else []), "-v", f"{t}:/w", IMAGE,
                                    "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad", "-no_init", "-exit",
                                    "/w/t.tcl"], capture_output=True, text=True, timeout=600)
                outs[pf] = r.stdout + r.stderr
        import re
        mn = lambda o, p: float(re.search(r"set_input_delay (\S+) -clock \[get_clocks \{vclk\}\] -min -add_delay \[get_ports \{%s\}\]" % p, o).group(1))
        om = lambda o: float(re.search(r"set_output_delay (\S+) -clock \[get_clocks \{vclk\}\] -min", o).group(1))
        self.assertEqual(mn(outs[False], "a"), 0.0)                  # off: unchanged
        self.assertRegex(outs[True], r"OT_IOREF_PF \S+ input pin flops 2 ")
        self.assertIn("OT_IOREF_PF search: pinflop_ref.tcl", outs[True])
        self.assertGreater(mn(outs[True], "a"), 0.0)                 # pin flops later than the boundary mean
        self.assertEqual(om(outs[True]), om(outs[False]))            # outputs keep the boundary mean

    def test_openroad_two_clocks_each_own_pinflop_mean(self):
        """mtp-wfc 2026-10-11: two port clocks (ck / ckv as dsfd_wfc_crp): each moved virtual clock's inputs shift by the
        pin-flop mean of ITS real clock.  The core pin flops sit behind a buffer (later than the core boundary mean), the
        ser pin flop IS the ser boundary: the ser input keeps min 0 (the old first-clock mean shifted it by the core's)."""
        if subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode:
            self.skipTest("no ORFS image")
        net = """module top(input clk, input ckv, input a, input b, input c, input e, output q1);
  wire cd, ck2, ck3;
  BUFx2_ASAP7_75t_R u_ck (.A(clk), .Y(ck2));
  BUFx2_ASAP7_75t_R u_ck3 (.A(ck2), .Y(ck3));
  DFFHQNx1_ASAP7_75t_R r1 (.CLK(ck3), .D(a), .QN());
  DFFHQNx1_ASAP7_75t_R r2 (.CLK(ck3), .D(b), .QN());
  AND2x2_ASAP7_75t_R u_a (.A(c), .B(b), .Y(cd));
  DFFHQNx1_ASAP7_75t_R r3 (.CLK(clk), .D(cd), .QN(q1));
  DFFHQNx1_ASAP7_75t_R s1 (.CLK(ckv), .D(e), .QN());
endmodule
"""
        head = TCL.split("source /w/pinflop_ref.tcl")[0]
        body = """create_clock -name ser_clk -period 1111 [get_ports ckv]
create_clock -name vclk -period 833
create_clock -name vclk_s -period 1111
set_clock_latency 100 [get_clocks {vclk vclk_s}]
set ot_ci [get_ports {a b c}]
set_input_delay 316.6 -clock vclk $ot_ci
set_input_delay -min 0 -clock vclk $ot_ci
set_input_delay 372.2 -clock vclk_s [get_ports e]
set_input_delay -min 0 -clock vclk_s [get_ports e]
set_output_delay 316.6 -clock vclk [all_outputs]
set_output_delay -min 0 -clock vclk [all_outputs]
set_propagated_clock [get_clocks {core_clk ser_clk}]
set ::env(OT_IOREF_INPUT_PF) 1
source /w/io_ref_routed.sdc
write_sdc /tmp/y.sdc
puts [exec grep -E "_delay" /tmp/y.sdc]
"""
        with tempfile.TemporaryDirectory() as t:
            Path(t, "t.v").write_text(net)
            Path(t, "t.tcl").write_text(head + body)
            shutil.copy(ROOT / "physical/common_flow/io_ref_routed.sdc", Path(t, "io_ref_routed.sdc"))
            shutil.copy(D / "pinflop_ref.tcl", Path(t, "pinflop_ref.tcl"))   # PF-HOLDPAD: the shipped {CL} pair
            r = subprocess.run(["docker", "run", "--rm", "-v", f"{t}:/w", IMAGE,
                                "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad", "-no_init", "-exit",
                                "/w/t.tcl"], capture_output=True, text=True, timeout=600)
            out = r.stdout + r.stderr
        import re
        mn = lambda ck, p: float(re.search(r"set_input_delay (\S+) -clock \[get_clocks \{%s\}\] -min -add_delay \[get_ports \{%s\}\]" % (ck, p), out).group(1))
        self.assertGreater(mn("vclk", "a"), 0.0, out[-3000:])        # core pin flops later than the core boundary mean
        self.assertAlmostEqual(mn("vclk_s", "e"), 0.0, places=1, msg=out[-3000:])   # ser: its own pin-flop mean = boundary


# PF-HOLDPAD (NATIVE-REF 2026-10-18): the smhq GRT netlist (d[24]: HB2 ot_inhold -> BUFx4f ot_ihdrv -> HB2 -> BUFx2 -> ...
# CTS hold buffers -> pin flop) and the kp4_dec wires-only parent (inputs straight into a hard child; the reference fell
# on the raw child clock pin u_chn/clk, ~250-290 ps before the child flops).
HOLDPAD_NET = """module top(input clk, input a, input b, input r, input h, output q1);
  wire a1, a2, a3, a4, a5, a6, r1, r2, r3, r4a, r4b;
  HB2xp67_ASAP7_75t_R  inh (.A(a), .Y(a1));
  BUFx4f_ASAP7_75t_R   drv (.A(a1), .Y(a2));
  HB2xp67_ASAP7_75t_R  h1 (.A(a2), .Y(a3));
  BUFx2_ASAP7_75t_R    h2 (.A(a3), .Y(a4));
  HB2xp67_ASAP7_75t_R  h3 (.A(a4), .Y(a5));
  BUFx2_ASAP7_75t_R    h4 (.A(a5), .Y(a6));
  DFFHQNx1_ASAP7_75t_R pa (.CLK(clk), .D(a6), .QN(q1));
  BUFx2_ASAP7_75t_R    t0 (.A(r), .Y(r1));
  BUFx2_ASAP7_75t_R    t1 (.A(r1), .Y(r2));
  BUFx2_ASAP7_75t_R    t2 (.A(r2), .Y(r3));
  BUFx2_ASAP7_75t_R    t3a (.A(r3), .Y(r4a));
  BUFx2_ASAP7_75t_R    t3b (.A(r3), .Y(r4b));
  DFFHQNx1_ASAP7_75t_R ra (.CLK(clk), .D(r4a), .QN());
  DFFHQNx1_ASAP7_75t_R rb (.CLK(clk), .D(r4b), .QN());
  hm u_chn (.ck(clk), .d(h), .q());
endmodule
"""
HM_LIB = """library(hm_tt) {
  delay_model : table_lookup; time_unit : "1ps"; voltage_unit : "1V"; current_unit : "1mA";
  capacitive_load_unit(1, ff); pulling_resistance_unit : "1kohm"; leakage_power_unit : "1pW";
  nom_process : 1; nom_voltage : 0.7; nom_temperature : 25;
  cell(hm) {
    area : 100; is_macro_cell : true;
    pin("ck") {
      direction : input; clock : true; capacitance : 1.0;
      timing() { timing_sense : positive_unate; timing_type : min_clock_tree_path;
        cell_rise(scalar) { values("250.0"); } cell_fall(scalar) { values("255.0"); } }
      timing() { timing_sense : positive_unate; timing_type : max_clock_tree_path;
        cell_rise(scalar) { values("300.0"); } cell_fall(scalar) { values("305.0"); } }
    }
    pin("d") { direction : input; capacitance : 1.0;
      timing() { related_pin : "ck"; timing_type : setup_rising;
        rise_constraint(scalar) { values("10.0"); } fall_constraint(scalar) { values("10.0"); } } }
    pin("q") { direction : output;
      timing() { related_pin : "ck"; timing_type : rising_edge;
        cell_rise(scalar) { values("400.0"); } cell_fall(scalar) { values("400.0"); }
        rise_transition(scalar) { values("10.0"); } fall_transition(scalar) { values("10.0"); } } }
  }
}
"""
HM_LEF = """VERSION 5.8 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;
MACRO hm
  CLASS BLOCK ;
  ORIGIN 0 0 ;
  SIZE 10.8 BY 10.8 ;
  PIN ck
    DIRECTION INPUT ; USE CLOCK ;
    PORT LAYER M4 ; RECT 0 0 0.1 0.1 ; END
  END ck
  PIN d
    DIRECTION INPUT ; USE SIGNAL ;
    PORT LAYER M4 ; RECT 0 1 0.1 1.1 ; END
  END d
  PIN q
    DIRECTION OUTPUT ; USE SIGNAL ;
    PORT LAYER M4 ; RECT 0 2 0.1 2.1 ; END
  END q
END hm
END LIBRARY
"""
HOLDPAD_TCL = """set L /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $L/lib/NLDM/*SEQ*RVT_TT*.lib* $L/lib/NLDM/*SIMPLE*RVT_TT*.lib* $L/lib/NLDM/*INVBUF*RVT_TT*.lib* $L/lib/NLDM/*AO*RVT_TT*.lib*] { read_liberty $f }
read_liberty /w/hm_tt.lib
read_lef $L/lef/asap7_tech_1x_201209.lef
read_lef $L/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /w/hm.lef
read_verilog /w/t.v
link_design top
create_clock -name core_clk -period 833 [get_ports clk]
set ::env(ADDITIONAL_LIBS) /w/hm_tt.lib
source /w/pinflop_ref.tcl
puts "PFH [lsort [lmap p [ot_pf_clks [get_ports {a b r}]] {get_full_name $p}]]"
puts "PFM [lsort [lmap p [ot_pf_clks [get_ports h]] {get_full_name $p}]]"
set p [ot_pf_ref [get_ports h]]
puts "REFH [get_full_name $p] RAW [get_property $p arrival_max_rise] MAX [ot_pf_arr $p max] MIN [ot_pf_arr $p min]"
set ::env(OT_PF_HOPS) 3
puts "PF3 [lsort [lmap p [ot_pf_clks [get_ports {a}]] {get_full_name $p}]]"
"""


class HoldPad(unittest.TestCase):
    def test_overlay_refreshes_older_procs(self):
        """an io_ref_skew.sdc that already carries the 10-10 procs (3-hop search, raw macro pin arrival) gets the
        PF-HOLDPAD procs and ot_pf_arr reads; a second pass changes nothing"""
        import sys
        sys.path.insert(0, str(ROOT / "tools/closure_loop"))
        import pinflop_overlay as po
        procs = (D / "pinflop_ref.tcl").read_text()
        self.assertIn(po.MARK, procs)
        r = subprocess.run(["git", "-C", str(ROOT), "show", "2cac78ec5:physical/qwen_die_masters/io_ref_skew.sdc"],
                           capture_output=True, text=True)
        if r.returncode:
            self.skipTest("old blob not in this clone")
        old = r.stdout
        self.assertIn("$hop < 3 && [llength $nets]", old)
        new = po.patch(old, procs)
        self.assertIsNotNone(new)
        self.assertNotIn("$hop < 3 && [llength $nets]", new)
        self.assertIn("set qdm_lmax [ot_pf_arr $qdm_ref max]", new)
        self.assertIn("set qdm_lmin [ot_pf_arr $qdm_ref min]", new)
        self.assertEqual(new.count("proc ot_pf_clks"), 1)
        self.assertEqual(new.count("proc ot_pf_median"), 1)
        self.assertIsNone(po.patch(new, procs))
        self.assertEqual(new, (D / "io_ref_skew.sdc").read_text())   # the committed SDC is the overlay's output
        for k in sorted((D / "mc").glob("*/io_ref_skew.sdc")):        # kit copies: procs + "$ref" reads
            kn = po.patch(k.read_text(), procs)
            self.assertIsNotNone(kn, k)
            self.assertIn("ot_pf_arr $", kn, k)
            self.assertNotRegex(kn, r"get_property \$(qdm_)?ref arrival_m", k)
            self.assertNotIn("$hop < 3 && [llength $nets]", kn, k)
            self.assertIsNone(po.patch(kn, procs), k)
        # a pre-10-10 kit (no procs at all): procs inserted AND reads routed through ot_pf_arr
        kit = ("# kit\nforeach {clk sk ins outs} {\n  ck 150 {a} {b}\n} {\n" + po.KIT_OLD
               + "  set lmax [get_property $ref arrival_max_rise]; set lmin [get_property $ref arrival_min_rise]\n"
               + "  set_input_delay 1 [get_ports $ins]\n}\n")
        kn = po.patch(kit, procs)
        self.assertIn("ot_pf_arr $ref max", kn)
        self.assertIsNone(po.patch(kn, procs))

    def test_routed_ioref_uses_shared_search(self):
        s = (ROOT / "physical/common_flow/io_ref_routed.sdc").read_text()
        self.assertIn("ot_pf_clks [all_inputs -no_clocks]", s)
        self.assertIn("ot_pf_ins $p max", s)

    @unittest.skipUnless(shutil.which("docker"), "no docker")
    def test_openroad_holdpad_chain_and_hard_child(self):
        if subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode:
            self.skipTest("no ORFS image")
        with tempfile.TemporaryDirectory() as t:
            for n, body in (("t.v", HOLDPAD_NET), ("t.tcl", HOLDPAD_TCL), ("hm_tt.lib", HM_LIB), ("hm.lef", HM_LEF)):
                Path(t, n).write_text(body)
            shutil.copy(D / "pinflop_ref.tcl", Path(t, "pinflop_ref.tcl"))
            r = subprocess.run(["docker", "run", "--rm", "-v", f"{t}:/w", IMAGE, "/OpenROAD-flow-scripts/tools/install/"
                                "OpenROAD/bin/openroad", "-no_init", "-exit", "/w/t.tcl"], capture_output=True, text=True,
                               timeout=600)
        out = r.stdout + r.stderr
        import re
        # pa sits 6 buffers deep (smhq GRT shape): found; the fanned-out 5-deep tree (ra / rb, a reset-like tree) is
        # past hop 3 through a 2-load net: not followed
        self.assertRegex(out, r"PFH pa/CLK\n", out[-3000:])
        self.assertRegex(out, r"PFM u_chn/ck\n", out[-3000:])
        m = re.search(r"REFH u_chn/ck RAW (\S+) MAX (\S+) MIN (\S+)", out)
        self.assertIsNotNone(m, out[-3000:])
        raw, mx, mn = map(float, m.groups())
        self.assertAlmostEqual(mx - raw, 300.0, places=3)           # + the child's max_clock_tree_path
        self.assertIn("1 hard-child clock pins at +insertion", out)
        self.assertRegex(out, r"PF3 \n")                            # OT_PF_HOPS=3 = the old search: lost behind the pads

if __name__ == "__main__":
    unittest.main()
