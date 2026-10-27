#!/usr/bin/env python3
"""PORT-LATENCY (ROOT 2215): publish() exports the route's own elaborated pin-register table (physical/common_flow/
ot_pin_regs.tcl output) through tools/ref_tile/port_latency.py, bound to the job's full source SHA; a pin-register kit
whose route left no table fails closed; a kit without pin registers yields no report.  Real Tcl generator, temp git repo,
local stand-in for ssh."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import closure_loop as cl  # noqa: E402

TCL = HERE.parents[1] / "physical/common_flow/ot_pin_regs.tcl"
STUB = '''
set ::env(DESIGN_NAME) example
set ::env(OT_PIN_REGS_CLOCK) ck
set ::env(OT_PIN_REGS_EXCLUDE) {^cfg$}
set ::env(RESULTS_DIR) [lindex $argv 0]
proc yosys {args} {
 if {[lindex $args 0] eq "tee"} {
  set f [open [lindex $args 3] w]
  puts $f {input [0:0] ck
input [0:0] rst_n
input [7:0] cmd
input [2:0] cfg
output [0:0] done}
  close $f
 }
}
source [lindex $argv 1]
'''


def fake_ssh(host, script, timeout=120, **kw):
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True)


class PortLatencyRecord(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        t = Path(self.td.name)
        self.repo, self.run = t / "repo", t / "run"
        kit = self.repo / "physical/ref_tile/ex"
        kit.mkdir(parents=True)
        (kit / "spec.json").write_text(json.dumps({"top": "example"}))
        (kit / "kit.env").write_text("EXTRA=(--orfs-var OT_PIN_REGS=1 --orfs-var OT_PIN_REGS_CLOCK=ck)\n")
        g = ["git", "-C", str(self.repo)]
        subprocess.run(g + ["init", "-q"], check=True)
        subprocess.run(g + ["add", "."], check=True)
        subprocess.run(g + ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "kit"], check=True)
        self.sha = subprocess.run(g + ["rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        self.base = self.run / "routes" / cl.label("ex-r1") / "work/orfs/results/asap7/d/base"
        self.base.mkdir(parents=True)
        subprocess.run(["tclsh", "/dev/stdin", str(self.base), str(TCL)], input=STUB, text=True, check=True,
                       capture_output=True)
        self.saved = (cl.REPO, cl.ssh)
        cl.REPO, cl.ssh = self.repo, fake_ssh
        self.job = {"name": "ex-r1", "host": "fakehost", "run": str(self.run), "commit_full": self.sha,
                    "spec": {"stages": {"route": {"cmd": "bash tools/ref_tile/ref_route.sh physical/ref_tile/ex/kit.env "
                                                         "{LABEL} {RUN}/routes"}}}}

    def tearDown(self):
        cl.REPO, cl.ssh = self.saved
        self.td.cleanup()

    def test_exports_elaborated_stages_bound_to_source(self):
        kit, rep = cl.port_latency_record(self.job)
        self.assertEqual(kit, "physical/ref_tile/ex")
        self.assertEqual(rep["source_commit"], self.sha)
        self.assertEqual(rep["top"], "example")
        self.assertEqual({p: v["register_edges"] for p, v in rep["ports"].items()},
                         dict(ck=0, rst_n=0, cmd=1, cfg=0, done=1))

    def test_missing_table_fails_closed(self):
        (self.base / "ot_pin_regs.tsv").unlink()
        with self.assertRaisesRegex(RuntimeError, "PORT-LATENCY"):
            cl.port_latency_record(self.job)

    def test_kit_without_pin_registers_has_no_report(self):
        self.job["spec"]["stages"]["route"]["cmd"] = "bash tools/other_flow.sh"
        self.assertIsNone(cl.port_latency_record(self.job))


if __name__ == "__main__":
    unittest.main()
