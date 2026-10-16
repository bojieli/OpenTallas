import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/ref_tile'))
from port_latency import export


class PortLatencyTest(unittest.TestCase):
    def test_actual_hook_output_binds_compiler_without_double_count(self):
        # Execute the real synthesis wrapper generator. The stub only supplies
        # Yosys's elaborated port list; all classification and stage generation
        # runs in the production Tcl helper.
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            script = '''
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
output [0:0] done
inout [0:0] pad}
  close $f
 }
}
source [lindex $argv 1]
'''
            subprocess.run(['tclsh', '/dev/stdin', td,
                            str(ROOT / 'physical/common_flow/ot_pin_regs.tcl')],
                           input=script, text=True, check=True, capture_output=True)
            report = export(path/'ot_pin_regs.tsv', path/'ot_pin_regs_wrapper.v', 'example', '1'*40)
            self.assertEqual({p: v['register_edges'] for p, v in report['ports'].items()},
                             dict(ck=0, rst_n=0, cmd=1, cfg=0, done=1, pad=0))
            dest = path/'port_latency.json'
            dest.write_text(json.dumps(report))
            spec = importlib.util.spec_from_file_location('boundary_compiler', ROOT/'tools/s81_compile_schedule/compile_calendar.py')
            compiler = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(compiler)
            job = dict(kit_boundary=dict(report=dest.name, sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
                                         ports=['cmd', 'done'], duration_measured_at='rtl_core'))
            self.assertEqual(compiler.kit_boundary_edges(job, path), 2)
            job['kit_boundary']['duration_measured_at'] = 'kit_pins'
            self.assertEqual(compiler.kit_boundary_edges(job, path), 0)
            dest.write_text(dest.read_text()+'\n')
            with self.assertRaisesRegex(ValueError, 'stale'):
                compiler.kit_boundary_edges(job, path)
            table = path/'ot_pin_regs.tsv'
            table.write_text(table.read_text()+'cmd\tinput\t8\t1\tpin register\n')
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                export(table, path/'ot_pin_regs_wrapper.v', 'example', '1'*40)


    def test_gate_exports_synthesis_table_and_fails_closed_after_warn_window(self):
        import base64
        import datetime as dt
        import zlib
        import pre_route_gate as G
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            subprocess.run(['tclsh', '/dev/stdin', td, str(ROOT / 'physical/common_flow/ot_pin_regs.tcl')],
                           input=GATE_STUB, text=True, check=True, capture_output=True)
            (path/'kit.env').write_text('EXTRA=(--orfs-var OT_PIN_REGS=1 --orfs-var OT_PIN_REGS_CLOCK=ck)\n')
            enc = lambda f: base64.b64encode(zlib.compress((path/f).read_bytes())).decode()
            out = 'GATE_PIN_REGS_B64 %s %s\n' % (enc('ot_pin_regs.tsv'), enc('ot_pin_regs_wrapper.v'))
            g = G.Gate()
            G.check_port_latency(g, path, dict(top='example'), out, 'b' * 40)
            self.assertEqual(g.verdict, 'PASS')
            self.assertEqual(g.port_latency['source_commit'], 'b' * 40)
            self.assertEqual(g.port_latency['ports']['done']['register_edges'], 1)
            early = dt.datetime.fromisoformat('2026-10-16T00:00:00-07:00')
            late = dt.datetime.fromisoformat('2026-10-17T00:00:00-07:00')
            g = G.Gate()
            G.check_port_latency(g, path, dict(top='example'), 'no table\n', 'b' * 40, now=early)
            self.assertEqual(g.verdict, 'WARN')
            g = G.Gate()
            G.check_port_latency(g, path, dict(top='example'), 'no table\n', 'b' * 40, now=late)
            self.assertEqual(g.verdict, 'FAIL')
            (path/'kit.env').write_text('EXTRA=()\n')
            g = G.Gate()
            G.check_port_latency(g, path, dict(top='example'), 'no table\n', 'b' * 40, now=late)
            self.assertEqual(g.items, [])

    def test_gate_remote_script_formats(self):
        import pre_route_gate as G
        self.assertIn('GATE_PIN_REGS_B64', G.REMOTE_SH)
        G.REMOTE_SH.format(R='r', COMMIT='c', CAP=1, KIT='k', IMG='i', RC='x', TOP='t', CTS=0, PGM=32, TRIAL=0,
                           CLKS='ck', CLK='ck', ARCHIVE_SHA256='s', STEP_CAP=1)


GATE_STUB = '''
set ::env(DESIGN_NAME) example
set ::env(OT_PIN_REGS_CLOCK) ck
set ::env(RESULTS_DIR) [lindex $argv 0]
proc yosys {args} {
 if {[lindex $args 0] eq "tee"} {
  set f [open [lindex $args 3] w]
  puts $f {input [0:0] ck
input [7:0] cmd
output [0:0] done}
  close $f
 }
}
source [lindex $argv 1]
'''


if __name__ == '__main__':
    unittest.main()
