"""Precise SOURCE binding (r2, 2026-10-14): a gate that records the files it consumed is refused only when one of those
files differs at the route source; other staged-file differences are reported, not refused.  Regression:
  qfd_slab_pg_col_pr-pr4-4e5fd7784 was refused only because tools/ref_tile/specs_q14r6/qfd_su_lane_t_i2.json (another
  job's spec, shipped with tools/ but never read by this gate) changed between gate and submit -> now passes.
Negatives: the kit's RTL (spec sources), an `include of it, a hook its kit names, the kit spec itself, a gate-executed
overlay, and a tampered consumed record all still refuse and name the file.  Old-format gates (no record) are unchanged."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE), str(HERE.parent / 'closure_loop')]
import helper_overlay as HO
import pre_route_gate as PG
import source_binding as SB

GATE = 'tools/textbook_lint.py'
OTHER_SPEC = 'tools/ref_tile/specs_q14r6/qfd_su_lane_t_i2.json'
RTL = 'rtl/physical/ot_slab.sv'
INC = 'rtl/physical/ot_slab_defs.svh'
HOOK = 'physical/common_flow/pin_reg_split.tcl'
UNUSED_HOOK = 'physical/common_flow/other_hook.tcl'
KIT = 'physical/ref_tile/qfd_slab_pg_col_pr'


class ConsumedSourceBinding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root, self.daemon = Path(self.tmp.name) / 'repo', Path(self.tmp.name) / 'daemon'
        for d in ('tools/closure_loop', 'tools/ref_tile/specs_q14r6', 'rtl/physical', 'physical/common_flow', KIT):
            (self.root / d).mkdir(parents=True, exist_ok=True)
        (self.daemon / 'tools').mkdir(parents=True)
        self.git('init')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.com')
        self.spec = {'name': 'qfd_slab_pg_col_pr', 'top': 'ot_slab', 'kind': 'tile', 'sources': [RTL],
                     'macros': [], 'children': []}
        self.tip = self.commit({
            GATE: b'# lint v1\n', OTHER_SPEC: b'{"name": "qfd_su_lane_t_i2"}\n',
            RTL: b'`include "ot_slab_defs.svh"\nmodule ot_slab; endmodule\n', INC: b'`define W 8\n',
            HOOK: b'# split pin regs\n', UNUSED_HOOK: b'# not this kit\n',
            f'{KIT}/spec.json': json.dumps(self.spec).encode(),
            f'{KIT}/pre_gpl.tcl': f'source $::env(SRC)/{HOOK}\n# see {UNUSED_HOOK} (comment only)\n'.encode(),
            f'{KIT}/job.json': json.dumps({'source': {'extra_paths': []}}).encode()})
        (self.daemon / GATE).write_bytes(b'# lint v1\n')
        self.stack = [patch.object(PG, 'ROOT', self.root), patch.object(PG, 'DAEMON_TREE', self.daemon),
                      patch.object(PG, 'SHIP_HELPERS', (GATE,)), patch.object(HO, 'HELPERS', ('../textbook_lint.py',))]
        for p in self.stack:
            p.start()
        plan, payloads = HO.capture_plan(self.daemon, self.root)
        data = PG.ship_tar({'tools', 'rtl', 'physical'}, payloads, {f['path']: f['mode'] for f in plan['files']})
        self.legacy = SB.snapshot(data, self.root, self.tip, self.daemon, None, (GATE,))
        self.legacy.update(route_overlay_plan=plan, remote_archive_verified=True)
        self.binding = json.loads(json.dumps(self.legacy))
        self.binding['consumed'] = PG.gate_consumed(data, self.root / KIT, self.spec, [], self.binding['files'])
        (self.root / KIT / 'gate_result.json').write_text(json.dumps(
            {'source_binding': self.binding, 'clock': {'max_root_sinks': 9000, 'verdict': 'PASS'}}))

    def tearDown(self):
        for p in reversed(self.stack):
            p.stop()
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.DEVNULL).decode().strip()

    def commit(self, files):
        for rel, data in files.items():
            (self.root / rel).write_bytes(data)
        self.git('add', *files)
        self.git('commit', '-m', 'update')
        return self.git('rev-parse', 'HEAD')

    def test_consumed_set_is_the_kit_closure(self):
        used = set(self.binding['consumed']['paths'])
        self.assertTrue({RTL, INC, HOOK, GATE, f'{KIT}/spec.json', f'{KIT}/pre_gpl.tcl'} <= used, used)
        self.assertNotIn(OTHER_SPEC, used)
        self.assertNotIn(UNUSED_HOOK, used)       # named only in a comment
        self.assertNotIn(f'{KIT}/job.json', used)  # the route's job spec, not a gate input
        self.assertEqual(self.binding['consumed']['sha256'][RTL],
                         {e['path']: e['sha256'] for e in self.binding['files']}[RTL])

    def test_qfd_slab_pr4_other_jobs_spec_change_is_reported_not_refused(self):
        later = self.commit({OTHER_SPEC: b'{"name": "qfd_su_lane_t_i2", "tag": "i3"}\n'})
        ok, why = SB.validate(self.binding, self.root, self.daemon, later)
        self.assertTrue(ok, why)
        self.assertIn('reported, not refused', why)
        self.assertIn(OTHER_SPEC, why)
        g = PG.Gate()
        PG.check_clock_evidence(g, self.root / KIT, source_commit=later)
        sb = [i for i in g.items if i['check'] == 'source_binding']
        self.assertNotIn('FAIL', [i['severity'] for i in sb], sb)
        self.assertTrue(any(OTHER_SPEC in i['message'] for i in sb if i['severity'] == 'INFO'), sb)

    def test_old_format_gate_still_refuses_the_same_change(self):
        later = self.commit({OTHER_SPEC: b'{"tag": "i3"}\n'})
        ok, why = SB.validate(self.legacy, self.root, self.daemon, later)
        self.assertFalse(ok)
        self.assertIn(f'route source differs from staged snapshot: {OTHER_SPEC}', why)

    def write_gate(self, binding):
        (self.root / KIT / 'gate_result.json').write_text(json.dumps(
            {'source_binding': binding, 'clock': {'max_root_sinks': 9000, 'verdict': 'PASS'}}))

    def test_v1_gate_without_record_is_reconstructed_from_its_staged_blobs(self):
        # the live pr4 gate predates the record: the same closure over its own staged blobs passes it as-is
        self.write_gate(self.legacy)
        rec = PG.reconstruct_consumed(self.legacy, self.root / KIT)
        self.assertEqual(rec['paths'], self.binding['consumed']['paths'])
        # submit_check passes the kit materialised in a temp dir, outside ROOT
        self.assertEqual(PG.reconstruct_consumed(self.legacy, Path(self.tmp.name) / 'materialised' / KIT)['paths'],
                         rec['paths'])
        later = self.commit({OTHER_SPEC: b'{"tag": "i3"}\n'})
        g = PG.Gate()
        PG.check_clock_evidence(g, self.root / KIT, source_commit=later)
        self.assertNotIn('FAIL', [i['severity'] for i in g.items if i['check'] == 'source_binding'], g.items)
        later = self.commit({RTL: b'module ot_slab; wire y; endmodule\n'})
        g = PG.Gate()
        PG.check_clock_evidence(g, self.root / KIT, source_commit=later)
        fail = [i for i in g.items if i['check'] == 'source_binding' and i['severity'] == 'FAIL']
        self.assertTrue(fail and RTL in fail[0]['message'], g.items)

    def test_v1_gate_with_unrecoverable_staged_blob_is_handled_as_before(self):
        b = json.loads(json.dumps(self.legacy))
        for e in b['files']:
            if e['path'] == f'{KIT}/pre_gpl.tcl':
                e['git_blob'] = 'f' * 40         # a dirty staged hook never committed: closure cannot be rebuilt
        b['manifest_sha256'] = SB.canonical_digest(b['files'])
        self.assertIsNone(PG.reconstruct_consumed(b, self.root / KIT))

    def assert_refused(self, rel, data):
        later = self.commit({rel: data, OTHER_SPEC: b'{"tag": "i4"}\n'})
        ok, why = SB.validate(self.binding, self.root, self.daemon, later)
        self.assertFalse(ok, why)
        self.assertIn(f'route source differs from staged snapshot: {rel}', why)
        self.assertNotIn(f'snapshot: {OTHER_SPEC}', why)
        g = PG.Gate()
        PG.check_clock_evidence(g, self.root / KIT, source_commit=later)
        fail = [i for i in g.items if i['check'] == 'source_binding' and i['severity'] == 'FAIL']
        self.assertTrue(fail and rel in fail[0]['message'], g.items)

    def test_consumed_rtl_change_refuses(self):
        self.assert_refused(RTL, b'`include "ot_slab_defs.svh"\nmodule ot_slab; wire x; endmodule\n')

    def test_included_header_change_refuses(self):
        self.assert_refused(INC, b'`define W 16\n')

    def test_kit_hook_dependency_change_refuses(self):
        self.assert_refused(HOOK, b'set ot_split_v 2 ;# split pin regs v2\n')

    def test_kit_spec_change_refuses(self):
        self.assert_refused(f'{KIT}/spec.json', json.dumps({**self.spec, 'top': 'ot_slab2'}).encode())

    def test_gate_executed_overlay_change_still_refuses(self):
        self.commit({GATE: b'# lint v2\n'})
        (self.daemon / GATE).write_bytes(b'# lint v2\n')
        ok, why = SB.validate(self.binding, self.root, self.daemon, self.tip)
        self.assertFalse(ok)
        self.assertIn(f'gate-executed daemon overlay changed: {GATE}', why)

    def test_tampered_consumed_record_refuses(self):
        b = json.loads(json.dumps(self.binding))
        b['consumed']['paths'].remove(RTL)
        self.assertFalse(SB.validate(b, self.root, self.daemon, self.tip)[0])
        b['consumed']['digest'] = SB.canonical_digest(b['consumed']['paths'])
        b['consumed']['sha256'][HOOK] = '0' * 64
        ok, why = SB.validate(b, self.root, self.daemon, self.tip)
        self.assertFalse(ok)
        self.assertIn('consumed-file record', why)


if __name__ == '__main__':
    unittest.main()
