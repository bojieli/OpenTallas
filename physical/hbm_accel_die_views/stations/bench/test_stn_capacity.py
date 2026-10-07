"""Small flow regressions; the full-shape exact/mutant bench stays in the job."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


class StationCapacity(unittest.TestCase):
    def test_capacity_default_optin_and_wrong_master(self):
        shared = (ROOT / 'physical/abi3/v41x_karb_repair_buffer_cap.tcl').read_text()
        capacity = (HERE / 'stn_repair_capacity.tcl').read_text().replace(
            'source /src/physical/abi3/v41x_karb_repair_buffer_cap.tcl', shared)
        for enabled, master, expected in [(False, 'hfd_stn_r33', '100'),
                                           (True, 'hfd_stn_r33', '300'),
                                           (True, 'hfd_stn_r34', 'ERROR')]:
            preamble = ('namespace eval sta {proc check_percent {key val} {if {$val > 100} {error RANGE}}}\n'
                        'proc repair_timing_helper {args} {sta::check_percent -max_buffer_percent [lindex $args end]; puts $args}\n'
                        'namespace eval ord {proc get_db_block {} {return block}}\n'
                        f'proc block {{args}} {{return {master}}}\n')
            if enabled:
                preamble += 'set ::env(OT_STN_R33_CAPACITY) 1\n'
            script = preamble + 'if {[catch {\n' + capacity + '\n} msg]} {puts "ERROR: $msg"; exit}\n'
            script += 'repair_timing_helper -hold_margin 35\n'
            script += 'puts "restored=[catch {sta::check_percent -max_buffer_percent 300}]"\n'
            env = os.environ.copy()
            env.pop('OT_STN_R33_CAPACITY', None)
            p = subprocess.run(['tclsh'], input=script, text=True, capture_output=True, env=env)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn(expected, p.stdout)
            if expected != 'ERROR':
                self.assertIn(f'-hold_margin 35 -max_buffer_percent {expected}', p.stdout)
                self.assertIn('restored=1', p.stdout)

    def test_wrapper_propagates_physical_failure(self):
        # The common wrapper can succeed after appending a successful check to a
        # failed physical rc. It can also leave an old rc=0 if it itself crashes.
        for physical_rc, wrapper_rc, expected in [('0', 0, 0), ('2', 0, 2),
                                                 ('0', 7, 7), ('ports', 0, 1),
                                                 ('0\nrc=2', 0, 1)]:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                common = root / 'physical/hbm_accel_die_views/common'
                common.mkdir(parents=True)
                fake = common / 'route_view.sh'
                fake.write_text('#!/bin/bash\nmkdir -p "$OUT/$1"\n'
                                f"printf '%s\\n' 'rc={physical_rc}' 'check_rc=0' > \"$OUT/$1/exit\"\n"
                                f'exit {wrapper_rc}\n')
                fake.chmod(0o755)
                env = os.environ.copy()
                env.pop('MARGIN', None)
                p = subprocess.run(['bash', str(HERE / 'stn_route.sh'), str(root),
                                    str(root / 'out'), 'test', 'hfd_stn_r33', '0.45'],
                                   env=env, capture_output=True, text=True)
                self.assertEqual(p.returncode, expected, p.stderr)


if __name__ == '__main__':
    unittest.main()
