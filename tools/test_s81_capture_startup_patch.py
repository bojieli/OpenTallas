"""Fail-closed preparation checks; no simulated physical closure claims."""
import copy
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
import s81_capture_startup_patch as patch


class PreparationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='capture-startup-test-')
        self.root = Path(self.tmp.name)
        self.base = self.root / 'baseline'
        self.base.mkdir()
        self.plan = json.loads((patch.ROOT / 'results/rtl/s81_ph_20261006/capture/startup_endpoint_model_20261007/one_pin_plan.json').read_text())
        for name in self.plan['original_sha256']:
            (self.base / name).write_text('fixture: ' + name)
            self.plan['original_sha256'][name] = patch.sha(self.base / name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_fresh_corner_scripts_and_preserved_constraints(self):
        out = patch.prepare(self.base, self.root / 'candidate', self.plan)
        self.assertEqual((out / '6_final.sdc').read_bytes(), (self.base / '6_final.sdc').read_bytes())
        body = (out / 'patch.tcl').read_text()
        self.assertNotIn('repair_timing', body)
        self.assertNotIn('report_worst_slack', body)
        for corner, check in [('ss', 'max'), ('ff', 'min')]:
            text = (out / f'sta_{corner}.tcl').read_text()
            self.assertIn(f'read_db {out}/6_final.odb', text)
            self.assertIn(f'read_spef {out}/6_final.spef', text)
            self.assertIn('S81_TARGET endpoint=', text)
            self.assertIn('slack_' + check, text)
            self.assertNotIn('insert_buffer', text)
        with self.assertRaises(ValueError):
            patch.prepare(self.base, out, self.plan)

    def test_changed_original_rejected_before_writes(self):
        (self.base / '6_final.spef').write_text('changed')
        with self.assertRaises(ValueError):
            patch.prepare(self.base, self.root / 'candidate', self.plan)
        self.assertFalse((self.root / 'candidate').exists())

    def test_scope_and_logic_negative_controls(self):
        for key, value in [('endpoint', 'payload[0]/D'), ('cells', ['INVx1_ASAP7_75t_R'])]:
            candidate = copy.deepcopy(self.plan)
            candidate['patches'][0][key] = value
            with self.assertRaises(ValueError):
                patch.validate(candidate)
        duplicate = copy.deepcopy(self.plan)
        duplicate['patches'].append(copy.deepcopy(duplicate['patches'][0]))
        with self.assertRaises(ValueError):
            patch.validate(duplicate)

    def test_exact_sta_to_odb_identity(self):
        body = (patch.ROOT / 'physical/s81_ph_views/capture/startup_pin_patch.tcl').read_text()
        resolver = body.split('foreach {endpoint masters} $patches {', 1)[1].split('  foreach master $masters {', 1)[0]
        fixture = r'''
namespace eval sta {}
set endpoint {g_r[12].u_x.w_st_r[0]$_DFF_P_/D}
proc get_pins {args} {return $::pin_list}
proc get_full_name {p} {return $::endpoint}
proc sta::sta_to_db_pin {p} {return dbterm}
proc dbterm {op} {if {$op eq "getInst"} {return dbinst}; error "Unexpected operation"}
proc dbinst {op args} {
  switch $op {
    findITerm {return $::dterm}
    getMaster {return dbmaster}
    getName {return {g_r\[12\].u_x.w_st_r\[0\]$_DFF_P_}}
    default {error "Unexpected operation"}
  }
}
proc dbmaster {op} {return $::master}
'''
        for pins, dterm, master, success in [
                ('p0', 'dbterm', 'DFFHQNx1_ASAP7_75t_R', True),
                ('p0 p1', 'dbterm', 'DFFHQNx1_ASAP7_75t_R', False),
                ('', 'dbterm', 'DFFHQNx1_ASAP7_75t_R', False),
                ('p0', 'otherterm', 'DFFHQNx1_ASAP7_75t_R', False),
                ('p0', 'dbterm', 'INVx1_ASAP7_75t_R', False)]:
            source = fixture + f'\nset pin_list {{{pins}}}\nset dterm {dterm}\nset master {master}\n'
            source += 'set rc [catch {\n' + resolver + '\n} msg]\nputs "RESULT $rc $msg"\n'
            result = subprocess.run(['tclsh'], input=source, text=True, capture_output=True, check=True)
            self.assertIn('RESULT ' + ('0' if success else '1'), result.stdout)
            if success:
                self.assertIn('S81_STARTUP_IDENTITY', result.stdout)


if __name__ == '__main__':
    unittest.main()
