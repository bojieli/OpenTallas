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


if __name__ == '__main__':
    unittest.main()
