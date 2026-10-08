"""Fail-closed preparation checks; no simulated physical closure claims."""
import copy
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
import s81_root_selective_patch as patch


class PreparationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='root-selective-test-')
        self.root = Path(self.tmp.name)
        self.base = self.root / 'baseline'
        self.base.mkdir()
        self.plan = dict(schema='opentallas.s81.root_selective_patch.v1', cycles_added=0,
                         area_added_um2=.05832,
                         patches=[dict(endpoint='_130070_/A1', expected_master='AOI21x1_ASAP7_75t_R',
                                       cells=['HB1xp67_ASAP7_75t_R'], baseline_ss_ps=632.)],
                         timed_endpoints=['u_root.r2_w[13]$_DFF_P_/D'],
                         original_sha256={name: '' for name in ['6_final.odb', '6_final.sdc', '6_final.spef']})
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
        for key, value in [('endpoint', 'payload[0]/D'), ('cells', ['INVx1_ASAP7_75t_R']), ('expected_master', 'INVx1_ASAP7_75t_R')]:
            candidate = copy.deepcopy(self.plan)
            candidate['patches'][0][key] = value
            with self.assertRaises(ValueError):
                patch.validate(candidate)
        duplicate = copy.deepcopy(self.plan)
        duplicate['patches'].append(copy.deepcopy(duplicate['patches'][0]))
        with self.assertRaises(ValueError):
            patch.validate(duplicate)

    def test_area_cycles_and_receiver_fail_closed(self):
        for key, value in [('area_added_um2', .1), ('cycles_added', 1),
                           ('timed_endpoints', []), ('timed_endpoints', ['u_root.r2_w[42]$_DFF_P_/D'])]:
            plan = copy.deepcopy(self.plan)
            plan[key] = value
            with self.assertRaises(ValueError):
                patch.validate(plan)

    def test_exact_sta_to_odb_identity(self):
        body = (patch.ROOT / 'physical/s81_ph_views/gather/root_selective_patch.tcl').read_text()
        resolver = body.split('foreach {endpoint expected_master masters} $patches {', 1)[1].split('  foreach master $masters {', 1)[0]
        fixture = r'''
namespace eval sta {}
set endpoint {_130070_/A1}
set expected_master AOI21x1_ASAP7_75t_R
proc get_pins {args} {return $::pin_list}
proc get_full_name {p} {return $::endpoint}
proc sta::sta_to_db_pin {p} {return dbterm}
proc dbterm {op} {if {$op eq "getInst"} {return dbinst}; error "Unexpected operation"}
proc dbinst {op args} {
  switch $op {
    findITerm {return $::dterm}
    getMaster {return dbmaster}
    getName {return {_130070_}}
    default {error "Unexpected operation"}
  }
}
proc dbmaster {op} {return $::master}
'''
        for pins, dterm, master, success in [
                ('p0', 'dbterm', 'AOI21x1_ASAP7_75t_R', True),
                ('p0 p1', 'dbterm', 'AOI21x1_ASAP7_75t_R', False),
                ('', 'dbterm', 'AOI21x1_ASAP7_75t_R', False),
                ('p0', 'otherterm', 'AOI21x1_ASAP7_75t_R', False),
                ('p0', 'dbterm', 'INVx1_ASAP7_75t_R', False)]:
            source = fixture + f'\nset pin_list {{{pins}}}\nset dterm {dterm}\nset master {master}\n'
            source += 'set rc [catch {\n' + resolver + '\n} msg]\nputs "RESULT $rc $msg"\n'
            result = subprocess.run(['tclsh'], input=source, text=True, capture_output=True, check=True)
            self.assertIn('RESULT ' + ('0' if success else '1'), result.stdout)
            if success:
                self.assertIn('S81_ROOT_IDENTITY', result.stdout)


if __name__ == '__main__':
    unittest.main()
