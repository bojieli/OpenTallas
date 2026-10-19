"""RC-CAL (ROOT-RST 2026-10-19): route-time hold repair and spine balancing time clock trees on the RCX-calibrated
upper-layer RC (tools/orfs_hold_mm.tcl ot_rc_cal_*, physical/common_flow/clock_spine.tcl).

Regression for s81lk_kp4_dec-p1-e86bf8cae: the GRT hold repair estimated the BUFx24 spine trunk ~90 ps late at FF
(setRC.tcl M6/M7 C 0.187/0.163 fF/um vs RCX 0.10), saw +30 on parent pin flop -> hard-child u_syn paths, signed off
-64.76.  The procs run under tclsh with OpenROAD stubbed; the committed measurement (evidence/rc_cal_kp4_dec_1019.json)
pins the calibration to the routed numbers."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TCL = HERE.parent / "orfs_hold_mm.tcl"
SPINE = HERE.parent.parent / "physical/common_flow/clock_spine.tcl"
EVIDENCE = HERE / "evidence/rc_cal_kp4_dec_1019.json"
PROCS = ("ot_env_num", "ot_hold_guard_on", "ot_hold_stage", "ot_hold_stop_cap", "ot_hold_stop_args", "ot_hold_stop",
         "ot_rc_cal_on", "ot_rc_cal_rc", "ot_rc_cal_mode", "ot_rc_cal_spine", "ot_rc_cal_apply", "ot_rc_cal_restore",
         "ot_rc_cal_hold", "ot_repair_timing", "ot_repair_hold_guarded")


def procs():
    src = TCL.read_text()
    out = []
    for name in PROCS:
        i = src.index(f"proc {name} ")
        j = src.find("\nproc ", i + 1)
        j = src.find("\n#", i + 1) if j < 0 else j
        out.append(src[i:j])
    return "\n".join(out)


def run(script, routes=True, platform="asap7", env="", spine=False):
    """run SCRIPT after the procs with OpenROAD stubbed; returns the ordered OpenROAD command log"""
    stubs = f"""
set ::log {{}}
set ::env(PLATFORM_DIR) /orfs/platforms/{platform}
{'set ::env(PLATFORM) ' + platform if platform else ''}
namespace eval grt {{ proc have_routes {{}} {{ return {1 if routes else 0} }} }}
proc log_cmd {{args}} {{ lappend ::log "repair_timing [lrange $args 1 end]" }}
proc set_layer_rc {{args}} {{ lappend ::log "set_layer_rc $args" }}
proc set_wire_rc {{args}} {{ lappend ::log "set_wire_rc $args" }}
proc estimate_parasitics {{args}} {{ lappend ::log "estimate_parasitics $args" }}
rename source ot_tcl_source
proc source {{f}} {{ lappend ::log "source $f" }}
proc ot_hold_stats {{}} {{ return {{-5.0 -50.0 3}} }}
proc ot_hm_guard {{a}} {{ return $a }}
proc ot_hold_stop {{a}} {{ return 0 }}
proc ot_hold_window_report {{why hist}} {{ }}
{'set ::ot_sp_insts {b1 b2}' if spine else ''}
{env}
"""
    body = stubs + procs() + "\n" + script + "\nforeach c $::log { puts \"LOG $c\" }\n"
    r = subprocess.run(["tclsh"], input=body, capture_output=True, text=True)
    if r.returncode:
        raise AssertionError(r.stderr + r.stdout)
    return [ln[4:] for ln in r.stdout.splitlines() if ln.startswith("LOG ")]


@unittest.skipUnless(shutil.which("tclsh"), "tclsh missing")
class RcCalHoldTests(unittest.TestCase):
    def test_grt_hold_repair_on_calibrated_upper_layers(self):
        log = run("ot_repair_timing {-setup_margin 0 -hold_margin 30}")
        setup = next(i for i, c in enumerate(log) if c.startswith("repair_timing") and "-setup" in c)
        cal = [i for i, c in enumerate(log) if c.startswith("set_layer_rc")]
        hold = [i for i, c in enumerate(log) if c.startswith("repair_timing") and "-hold" in c.split()[-3:] + c.split()]
        hold = [i for i in hold if i != setup]
        restore = next(i for i, c in enumerate(log) if c.startswith("source"))
        # setup repair keeps the platform RC; the calibration is set after it and before every hold call
        self.assertTrue(setup < min(cal))
        self.assertEqual([log[i] for i in cal], ["set_layer_rc -layer M6 -resistance 0.014 -capacitance 0.105",
                                                 "set_layer_rc -layer M7 -resistance 0.014 -capacitance 0.105"])
        self.assertEqual(log[max(cal) + 1], "estimate_parasitics -global_routing")
        self.assertTrue(hold and max(cal) < min(hold) and max(hold) < restore)
        # platform setRC restored and re-estimated right after the hold repair
        self.assertEqual(log[restore], "source /orfs/platforms/asap7/setRC.tcl")
        self.assertEqual(log[restore + 1], "estimate_parasitics -global_routing")
        self.assertEqual(restore + 2, len(log))

    def test_hold_only_call_is_calibrated(self):
        log = run("ot_repair_timing {-hold_margin 30 -hold}")
        self.assertTrue(log[0].startswith("set_layer_rc -layer M6"))
        self.assertIn("-hold", log[3])
        self.assertEqual(log[-2], "source /orfs/platforms/asap7/setRC.tcl")

    def test_setup_only_call_untouched(self):
        self.assertEqual(run("ot_repair_timing {-setup_margin 0 -setup}"), ["repair_timing -setup_margin 0 -setup"])

    def test_cts_stage_tritoncts_untouched(self):
        # placement parasitics, no spine: a TritonCTS tree's low-layer wiring is not over-estimated (hcoll evidence)
        log = run("ot_repair_timing {-hold_margin 30}", routes=False)
        self.assertFalse([c for c in log if c.startswith(("set_layer_rc", "set_wire_rc", "source"))])

    def test_cts_stage_spine_uses_clock_wire_rc(self):
        log = run("ot_repair_timing {-hold_margin 30}", routes=False, spine=True)
        self.assertIn("set_wire_rc -clock -resistance 0.014 -capacitance 0.105", log)
        self.assertIn("estimate_parasitics -placement", log)
        self.assertEqual(log[-2], "source /orfs/platforms/asap7/setRC.tcl")

    def test_opt_out_and_other_platforms(self):
        for kw in (dict(env="set ::env(OT_RC_CAL) 0"), dict(platform="sky130hd"), dict(platform="")):
            log = run("ot_repair_timing {-hold_margin 30}", **kw)
            self.assertFalse([c for c in log if c.startswith(("set_layer_rc", "source"))], kw)

    def test_knobs(self):
        log = run("ot_repair_timing {-hold_margin 30 -hold}",
                  env="set ::env(OT_RC_CAL_C) 0.12; set ::env(OT_RC_CAL_R) 0.015; set ::env(OT_RC_CAL_LAYERS) {M5 M6 M7}")
        self.assertEqual([c for c in log if c.startswith("set_layer_rc")],
                         [f"set_layer_rc -layer {m} -resistance 0.015 -capacitance 0.12" for m in ("M5", "M6", "M7")])

    def test_restore_even_when_hold_repair_fails(self):
        log = run("proc ot_hold_stop {a} { error boom }\ncatch {ot_repair_timing {-hold_margin 30}}")
        self.assertEqual(log[-2:], ["source /orfs/platforms/asap7/setRC.tcl", "estimate_parasitics -global_routing"])


class RcCalSpineTests(unittest.TestCase):
    def test_spine_balance_uses_and_restores_calibration(self):
        s = SPINE.read_text()
        a = s.index("set ot_rcc [ot_rc_cal_apply spine]")
        loop = s.index("for {set it 0} {$it <= $iters} {incr it}")
        r = s.index("if {$ot_rcc} { ot_rc_cal_restore; estimate_parasitics -placement }")
        dnt = s.index("foreach b $::ot_sp_insts { $b setDoNotTouch 1 }")
        self.assertTrue(a < loop < r < dnt)
        self.assertIn("OT_SPINE_RC_CAL", s)


class RcCalEvidenceTests(unittest.TestCase):
    def test_defaults_match_the_committed_rcx_calibration(self):
        ev = json.loads(EVIDENCE.read_text())
        src = TCL.read_text()
        r = float(re.search(r"OT_RC_CAL_R\)\] \? \$::env\(OT_RC_CAL_R\) : (\S+)\}", src).group(1))
        c = float(re.search(r"OT_RC_CAL_C\)\] \? \$::env\(OT_RC_CAL_C\) : (\S+)\}", src).group(1))
        self.assertEqual((r, c), (ev["calibration"]["resistance"], ev["calibration"]["capacitance"]))
        self.assertIn('"M6 M7"', src)
        # the calibrated C sits inside the RCX trunk range, well below the platform value
        trunks = ev["rcx_fit"]["kp4_dec_spine_trunks"].values()
        per_um = [t["C_fF"] / sum(v for k, v in t.items() if k.endswith("_um")) for t in trunks]
        self.assertTrue(min(per_um) * 0.9 <= c <= max(per_um) * 1.1)
        self.assertLess(c, 0.7 * ev["calibration"]["platform_setRC"]["M7"][1])

    def test_kp4_dec_pair_error_closes(self):
        ev = json.loads(EVIDENCE.read_text())["kp4_dec"]
        p = ev["pair_arrivals"]
        # GRT on platform RC: launch-vs-capture pair 67 ps off routed (repair saw +30, sign-off -64.76)
        self.assertGreater(p["grt"]["pair_skew_error_ps"], 60)
        self.assertLess(abs(p["grtcal"]["pair_skew_error_ps"]), 20)       # < the 30 ps route hold margin
        self.assertLess(abs(p["placecal"]["pair_skew_error_ps"]), 5)
        a = ev["all_register_clock_pins"]
        self.assertLess(a["grtcal"]["err_max_minus_min_ps"], 0.6 * a["grt"]["err_max_minus_min_ps"])
        self.assertLess(abs(a["placecal"]["err_median_ps"]), 10)


if __name__ == "__main__":
    unittest.main()
