"""HOLD CHUNK BUFFER BOUND (FLOW-CLOCK-R5 2026-10-29): ot_repair_hold_guarded caps every hold chunk with
-max_buffer_percent, because -max_iterations does not bound one repair_timing hold pass (KV E0 e0_ff15 GRT: FF ws
-38.91 / TNS -30814.6 flat from it ~1750 to >7780 of a single "-max_iterations 1000" call, +10.8k buffers).
The guard runs under tclsh against a mock repair_timing that honours -max_buffer_percent like OpenROAD (RSZ-0060)."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import closure_loop as cl
import orfs_hold_mm as ohm

TCL = cl.HERE.parent / "orfs_hold_mm.tcl"

MOCK = r"""
set ::buf 0
set ::calls {}
namespace eval ord { proc get_db_block {} { return ::mockblock } }
proc ::mockblock {m} { return [lrepeat [expr {$::inst0 + $::buf}] x] }
proc log_cmd {args} { {*}$args }
proc ot_hold_structural_gate {} {}
proc ot_hm_guard {a} { return $a }
proc ot_hold_stop {a} { return 0 }
proc ot_hold_window_report {why hist} { puts "STALL $why" }
proc ot_hold_stats {} {
  # worst/TNS improve linearly until ::useful buffers, then plateau (unfixable endpoint) or meet hold
  set f [expr {min(1.0, double($::buf) / $::useful)}]
  set w [expr {$::w0 + ($::wend - $::w0) * $f}]
  set t [expr {$w >= 0 ? 0.0 : $::t0 * (1.0 - 0.5 * $f)}]
  return [list $w $t [expr {$w >= 0 ? 0 : 1000}]]
}
proc repair_timing {args} {
  lappend ::calls $args
  set i [lsearch -exact $args -max_buffer_percent]
  set pct [expr {$i >= 0 ? [lindex $args [expr {$i + 1}]] : 20.0}]
  set cap [expr {int($pct * ($::inst0 + $::buf) / 100.0)}]
  # one hold pass wants ::sweep buffers whatever -max_iterations says
  set want [expr {$::sweep - $::swept}]
  if {$want > $cap} {
    incr ::buf $cap; incr ::swept $cap
    error "\[ERROR RSZ-0060\] Max buffer count reached."
  }
  incr ::buf $want; incr ::swept $want
}
"""


def run(env, inst0=195372, useful=3000, sweep=30000, w0=-63.0, wend=-38.91, t0=-63883.8, rt="-hold_margin 15"):
    src = TCL.read_text()
    procs = []
    for name in ("ot_env_num", "ot_hold_stop_args", "ot_repair_hold_guarded"):
        i = src.index(f"proc {name} ")
        j = src.index("\nproc ", i + 1) if f"\nproc " in src[i + 1:] else len(src)
        body = src[i:j]
        if name == "ot_repair_hold_guarded":
            body = body[: body.index("\n}\n") + 3]
        procs.append(body)
    envs = "".join(f"set ::env({k}) {v}\n" for k, v in env.items())
    script = (envs + f"set ::inst0 {inst0}; set ::useful {useful}; set ::sweep {sweep}; set ::swept 0\n"
              f"set ::w0 {w0}; set ::wend {wend}; set ::t0 {t0}\n" + MOCK + "\n".join(procs) +
              f"\nif {{[catch {{ot_repair_hold_guarded {{{rt}}}}} e]}} {{ puts \"ERR $e\" }}\n"
              "puts \"BUF $::buf\"\nputs \"CALLS [llength $::calls]\"\nforeach c $::calls { puts \"CALL $c\" }\n")
    r = subprocess.run(["tclsh"], input=script, capture_output=True, text=True, check=True)
    return r.stdout


def buf(out):
    return int([ln for ln in out.splitlines() if ln.startswith("BUF ")][0].split()[1])


@unittest.skipUnless(shutil.which("tclsh"), "tclsh missing")
class HoldChunkBufCapTests(unittest.TestCase):
    def test_e0_plateau_stops_after_a_flat_chunk(self):
        # E0 shape: 195k instances, gain ends after ~3000 buffers, the single pass would add 30k
        out = run({})
        self.assertIn("STALL stalled", out)
        self.assertLessEqual(buf(out), 3 * 2000)              # 2 useful chunks + 1 flat one (max(1 % = 1954, 2000))
        self.assertIn("buffer cap 2000 reached (RSZ-0060)", out)
        self.assertLess(out.rindex("reached (RSZ-0060), continuing"), out.index("OT_HOLD_MM after repair"))
        self.assertNotIn("ERR", out)

    def test_main_behaviour_without_cap_runs_the_whole_pass(self):
        # OT_HOLD_CHUNK_BUF_PCT=0 = previous guard: one unbounded call per chunk, no -max_buffer_percent added
        out = run({"OT_HOLD_CHUNK_BUF_PCT": 0})
        self.assertEqual(buf(out), 30000)
        self.assertNotIn("-max_buffer_percent", out)

    def test_converging_block_one_uncapped_chunk(self):
        # small block, needs 1500 buffers to meet the margin: the 2000-buffer minimum keeps it in one call
        out = run({}, inst0=20000, useful=1500, sweep=1500, wend=20.0)
        self.assertEqual(buf(out), 1500)
        self.assertNotIn("reached", out)
        self.assertNotIn("OT_HOLD_MM after repair", out)
        self.assertEqual(out.count("CALL "), 1)

    def test_total_budget_reraises_rsz0060(self):
        # the call's own -max_buffer_percent 2 (4000 of 200k) is the total; exhausting it fails as one call did
        out = run({}, inst0=200000, useful=100000, sweep=100000, wend=-1.0, rt="-hold_margin 15 -max_buffer_percent 2")
        self.assertIn("ERR [ERROR RSZ-0060]", out)
        self.assertLessEqual(abs(buf(out) - 4000), 2)

    def test_flow_error_count_tolerated_only_with_trailer(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "5_1_grt.log"
            body = ["[ERROR RSZ-0060] Max buffer count reached.", "OT_HOLD_GUARD chunk 1: buffer cap 1954 reached",
                    "[ERROR RSZ-0060] Max buffer count reached.", "OT_HOLD_GUARD chunk 2: buffer cap 1954 reached"]
            log.write_text("\n".join(body) + "\n")
            self.assertEqual(ohm.tolerate_flow_errors({"globalroute__flow__errors__count": 2}, d)
                             ["globalroute__flow__errors__count"], 2)
            trailer = "OT_HOLD_MM after repair: OT_HOLD_GUARD chunk buffer caps reached (RSZ-0060); continuing"
            log.write_text("\n".join(body + [trailer]) + "\n")
            self.assertEqual(ohm.tolerate_flow_errors({"globalroute__flow__errors__count": 2}, d)
                             ["globalroute__flow__errors__count"], 0)


if __name__ == "__main__":
    unittest.main()
