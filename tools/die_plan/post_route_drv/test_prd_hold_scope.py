"""KW-FIX-24 (COORD 11-06 13:2x item 4): every post-route hold repair in prd_hook.tcl honors OT_HOLD_REPAIR_SCOPE=reg2reg
(orfs_hold_mm.tcl HOLD-REPAIR-SCOPE); env unset = the repair command runs exactly as before (no SDC traffic)."""
import os
import pathlib
import re
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
HOOK = (HERE / "prd_hook.tcl").read_text()

STUB = r'''
set ::log {}
proc L {args} { lappend ::log [join $args " "] }
set ::exc 0
proc write_sdc {args} { set f [lindex $args end]; set h [open $f w]; puts $h "base exc=$::exc $::env(STUB_DRIFT)"; close $h; L write_sdc }
proc read_sdc {f} { L read_sdc; if {$::env(STUB_DRIFT) ne ""} { set ::env(STUB_DRIFT) drifted } }
proc all_clocks {} { return {clk} }
proc get_property {o p} { return {ck} }
proc get_full_name {o} { return $o }
proc all_inputs {} { return {ck a b} }
proc all_outputs {} { return {y} }
proc set_false_path {args} { incr ::exc; L set_false_path {*}$args }
proc unset_path_exceptions {args} { incr ::exc -1; L unset_path_exceptions {*}$args }
proc repair_timing {args} { L repair_timing {*}$args exc=$::exc }
proc ot_hold_guard_on {} { return 1 }
proc ot_rc_cal_hold {body} { L rc_cal; uplevel 1 $body }
proc ot_repair_hold_guarded {a} { L guarded $a exc=$::exc }
set _pass 1
'''
SHARED = r'''
set ::ot_mm_active 1
set ::ot_hold_scope_supported_modes {reg2reg nonport}
proc ot_hold_repair_scope {body} { L shared_scope; uplevel 1 $body }
'''


def hook_parts():
    i = HOOK.index("proc ot_prd_hold_scope {body} {")
    j = HOOK.index("set args [list -hold_margin")
    k = HOOK.index("if {[info exists ::env(OT_PRD_NO_HOLD)]")
    m = HOOK.index("\n}\n", HOOK.index("ot_prd_hold_scope { repair_timing -hold", k)) + 3
    return HOOK[i:j], HOOK[j:m]


class Scope(unittest.TestCase):
    def run_tcl(self, scope=None, two_mode=False, drift="", old_shared=False):
        proc, dispatch = hook_parts()
        with tempfile.TemporaryDirectory() as d:
            s = pathlib.Path(d) / "t.tcl"
            shared = SHARED
            if old_shared:
                shared = shared.replace("set ::ot_hold_scope_supported_modes {reg2reg nonport}\n", "")
            body = STUB + (shared if two_mode else "") + proc + "\n"
            body += "set ::env(OT_HOLD_MARGIN) 0; set ::env(OT_HOLD_MAXBUF) 40; set ::env(OT_HOLD_ALLOW_SETUP) 1\n"
            body += "if {[catch {\n" + dispatch + "\n} e]} { L ERROR $e }\nforeach x $::log { puts \"LOG $x\" }\n"
            body += "puts FILES=[llength [glob -nocomplain -directory " + d + " ot_prd_hold_scope_*]]\n"
            if not two_mode:
                body = body.replace("ot_repair_hold_guarded {a}", "ot_unused_guarded {a}")
            s.write_text(body)
            env = dict(os.environ, RESULTS_DIR=d, STUB_DRIFT=drift)
            env.pop("OT_HOLD_REPAIR_SCOPE", None)
            if scope:
                env["OT_HOLD_REPAIR_SCOPE"] = scope
            r = subprocess.run(["tclsh", str(s)], capture_output=True, text=True, timeout=60, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = r.stdout.splitlines()
            return [x[4:] for x in lines if x.startswith("LOG ")] + [x for x in lines if x.startswith("FILES=")]

    def test_default_single_mode_unchanged(self):
        out = self.run_tcl()
        self.assertEqual([x for x in out if not x.startswith("FILES")],
                         ["repair_timing -hold -hold_margin 0 -max_buffer_percent 40 -allow_setup_violations exc=0"])

    def test_default_two_mode_unchanged(self):
        out = self.run_tcl(two_mode=True)
        self.assertEqual(out[:2], ["rc_cal", "guarded -hold_margin 0 -max_buffer_percent 40 -allow_setup_violations exc=0"])
        self.assertNotIn("shared_scope", out)

    def test_other_value_is_default(self):
        self.assertNotIn("set_false_path", " ".join(self.run_tcl(scope="all")))

    def test_reg2reg_two_mode_uses_shared_scope_inside_rc_cal(self):
        out = self.run_tcl(scope="reg2reg", two_mode=True)
        self.assertEqual(out[:3], ["rc_cal", "shared_scope", "guarded -hold_margin 0 -max_buffer_percent 40 "
                                   "-allow_setup_violations exc=0"])

    def test_reg2reg_single_mode_excludes_ports_and_restores(self):
        out = self.run_tcl(scope="reg2reg")
        self.assertEqual(out[:8], [
            "write_sdc", "set_false_path -hold -from a b", "set_false_path -hold -to y",
            "repair_timing -hold -hold_margin 0 -max_buffer_percent 40 -allow_setup_violations exc=2",
            "unset_path_exceptions -hold -from a b", "unset_path_exceptions -hold -to y", "read_sdc", "write_sdc"])
        self.assertIn("FILES=0", out)

    def test_reg2reg_restore_mismatch_fails_closed(self):
        out = self.run_tcl(scope="reg2reg", drift="x")
        self.assertTrue(any(x.startswith("ERROR OT_HOLD_SCOPE restore differs") for x in out), out)

    def test_nonport_single_mode_retains_output_paths_and_restores(self):
        out = self.run_tcl(scope="nonport")
        self.assertEqual(out[:6], [
            "write_sdc", "set_false_path -hold -from a b",
            "repair_timing -hold -hold_margin 0 -max_buffer_percent 40 -allow_setup_violations exc=1",
            "unset_path_exceptions -hold -from a b", "read_sdc", "write_sdc"])
        self.assertFalse(any("-to y" in x for x in out), out)
        self.assertIn("FILES=0", out)

    def test_nonport_two_mode_uses_matching_shared_scope(self):
        self.assertEqual(self.run_tcl(scope="nonport", two_mode=True)[:2], ["rc_cal", "shared_scope"])

    def test_nonport_old_shared_hook_fails_closed(self):
        out = self.run_tcl(scope="nonport", two_mode=True, old_shared=True)
        self.assertTrue(any(x.startswith("ERROR OT_HOLD_SCOPE nonport requires matching") for x in out), out)
        self.assertFalse(any(x.startswith("guarded ") for x in out), out)

    def test_no_unscoped_hold_repair_left(self):
        # every hold repair call in the hook goes through ot_prd_hold_scope
        calls = [ln.strip() for ln in HOOK.splitlines() if re.search(r"repair_timing -hold|ot_repair_hold_guarded \$", ln)
                 and not ln.strip().startswith(("#", "puts"))]
        self.assertTrue(calls)
        self.assertTrue(all("ot_prd_hold_scope {" in c for c in calls), calls)


if __name__ == "__main__":
    unittest.main()
