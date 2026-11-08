"""Real STA paths and exact SDC restoration for the opt-in GRT scope."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/"die_plan/post_route_drv"))
import test_nonport_scope_sta as fixture
OPENROAD=os.environ.get("OPENROAD_BIN")or shutil.which("openroad")

@unittest.skipUnless(OPENROAD,"OpenROAD required")
class GrtNonportSTA(unittest.TestCase):
    def run_graph(self,enabled=True,body_error=False,mm=False):
        with tempfile.TemporaryDirectory(prefix="grt-nonport-sta-")as td:
            d=Path(td)
            (d/"fixture.lib").write_text(fixture.LIB)
            (d/"fixture.lef").write_text(fixture.LEF)
            (d/"fixture.v").write_text(fixture.NETLIST)
            script=f"read_lef {{{d}/fixture.lef}}\nread_liberty {{{d}/fixture.lib}}\n"
            if mm:
                script+=f"set_mode tc\nset_mode ff\ndefine_scene TC -mode tc -liberty {{{d}/fixture.lib}}\n"
                script+=f"define_scene BC -mode ff -liberty {{{d}/fixture.lib}}\n"
            script+=f"read_verilog {{{d}/fixture.v}}\nlink_design top\n"
            for mode in(["tc","ff"]if mm else[""]):
                if mode:script+=f"set_mode {mode}\n"
                script+="""
create_clock -name clk -period 0.833 [get_ports CK]
set_clock_uncertainty -hold 0.025 [get_clocks clk]
set_input_delay -clock clk -min -0.02012345678901234 [get_ports DIN]
set_input_delay -clock clk -max 0.10012345678901234 [get_ports DIN]
set_output_delay -clock clk -min 0.00012345678901234 [all_outputs]
set_output_delay -clock clk -max 0.10012345678901234 [all_outputs]
set_false_path -hold -from [get_ports DIN] -to [get_pins u_macro/D]
"""
            script+=f"set ::env(RESULTS_DIR) {{{d}}}\nset ::env(OT_HOLD_SCOPE_KEEP_SDC) 1\n"
            script+="set ::env(OT_VCLK_CORNER) ff\nset ::env(CORNER) BC\n"
            if enabled:script+="set ::env(OT_GRT_NONPORT_HOLD) 1\n"
            if mm:
                script+="set_mode tc\nset ::ot_mm_active 1\nset ::ot_mm_synced 1\nset ::ot_mm_stage 4_cts.sdc\n"
                script+="proc ot_hold_stats {} {return [sta::worst_slack_cmd min]}\n"
                script+=fixture.production_helper(True)+"\n"
                script+="set ::env(OT_HOLD_REPAIR_SCOPE) reg2reg\n"
            script+="proc snapshot {path} {\n"
            if mm:script+="set_scene BC\n"
            scenes=" -scenes BC"if mm else""
            script+=f"report_checks -path_delay min{scenes} -group_path_count 100 -endpoint_path_count 100 > $path\n"
            if mm:script+="set_scene TC\n"
            scenes=" -scenes TC"if mm else""
            script+=f"report_checks -path_delay max{scenes} -group_path_count 100 -endpoint_path_count 100 > ${{path}}.setup\n"
            script+="}\n"
            body=f"snapshot {{{d}/during.rpt}}; "
            body+="error expected-body-error"if body_error else"return helper-ok"
            if mm:
                script+="proc ot_repair_timing {rt_args} {return [ot_hold_repair_scope {"+body+"}]}\n"
                invoke="ot_repair_timing {-hold}"
            else:
                script+="proc fixture_original {args} {set ::got $args; "+body+"}\n"
                # Existing HEAD HB4 wrapper must remain in the call chain.
                script+="proc repair_timing_helper {args} {return [fixture_original {*}$args -max_buffer_percent 100]}\n"
                invoke="repair_timing_helper -hold -hold_margin 0"
                script+="set old_body [info body repair_timing_helper]\n"
            script+=f"snapshot {{{d}/before.rpt}}\nsource {{{HERE}/grt_nonport_hold.tcl}}\n"
            script+="set rc [catch {"+invoke+"} msg]\n"
            if body_error:script+='if {!$rc || $msg ne "expected-body-error"} {error "wrong error: $rc $msg"}\n'
            else:script+='if {$rc || $msg ne "helper-ok"} {error "wrong return: $rc $msg"}\n'
            script+=f"snapshot {{{d}/after.rpt}}\n"
            if not mm:
                script+='if {$::got ne {-hold -hold_margin 0 -max_buffer_percent 100}} {error "HB4 cap wrapper lost: $::got"}\n'
                if not enabled:script+='if {[info body repair_timing_helper] ne $old_body} {error "default changed helper"}\n'
            else:
                script+='if {[sta::cmd_mode_name] ne "tc"} {error "mode not restored"}\n'
                script+='if {$::env(OT_HOLD_REPAIR_SCOPE) ne "reg2reg"} {error "scope env not restored"}\n'
            script+="exit\n"
            (d/"fixture.tcl").write_text(script)
            p=subprocess.run([OPENROAD,"-no_init","-exit",str(d/"fixture.tcl")],capture_output=True,text=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr+"\n"+script)
            self.assertTrue((d/"after.rpt").exists(),p.stdout+p.stderr)
            reports=[(d/(n+".rpt")).read_text()for n in("before","during","after")]
            self.assertEqual(reports[0],reports[2],"full hold constraints/paths not restored")
            setups=[(d/(n+".rpt.setup")).read_text()for n in("before","during","after")]
            self.assertEqual(setups[0],setups[1],"setup timing changed during hold scope")
            self.assertEqual(setups[0],setups[2],"setup timing changed after hold scope")
            if enabled:
                self.assertRegex(reports[0],r"Startpoint: DIN\b")
                self.assertNotRegex(reports[1],r"Startpoint: DIN\b")
                self.assertRegex(reports[1],r"Endpoint: R2O\b")
                self.assertRegex(reports[1],r"Startpoint: u_macro\b")
                self.assertRegex(reports[1],r"Endpoint: u_macro_capture\b")
                self.assertIn("restored exact",p.stdout)
            else:self.assertEqual(reports[0],reports[1])

    def test_native_ff_paths_and_hb4_wrapper(self):self.run_graph()
    def test_native_ff_error_restores_constraints(self):self.run_graph(body_error=True)
    def test_default_is_inert(self):self.run_graph(enabled=False)
    def test_mm_reuses_exact_ff_scope_and_restores_entry_mode(self):self.run_graph(mm=True)
    def test_mm_error_restores_scope_and_mode(self):self.run_graph(mm=True,body_error=True)

    def test_explicit_native_tc_context_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="grt-nonport-tc-")as td:
            d=Path(td)
            script=f"""
set ::env(OT_GRT_NONPORT_HOLD) 1
set ::env(OT_VCLK_CORNER) tt
set ::env(CORNER) TC
proc repair_timing_helper {{args}} {{return untouched}}
set before [info body repair_timing_helper]
set rc [catch {{source {{{HERE}/grt_nonport_hold.tcl}}}} msg]
if {{!$rc || ![string match "*must explicitly select FF*" $msg]}} {{error "wrong guard: $rc $msg"}}
if {{[info body repair_timing_helper] ne $before}} {{error "helper changed before FF guard"}}
exit
"""
            (d/"guard.tcl").write_text(script)
            p=subprocess.run([OPENROAD,"-no_init","-exit",str(d/"guard.tcl")],capture_output=True,text=True,timeout=30)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)

if __name__=="__main__":unittest.main()

