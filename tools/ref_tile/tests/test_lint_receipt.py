"""lint_receipt: the kit CDC lint is keyed by its exact inputs, reused from a matching receipt, never run on localhost.

Light: a stub lint and a stub `yosys -V`; only the remote-refusal case runs the real tool modules (no elaboration)."""
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lint_receipt as L


class Boom(Exception):
    pass


def make_root(tmp, kit=True):
    root = Path(tmp)
    (root / 'rtl').mkdir()
    (root / 'rtl/a.v').write_text('module a; endmodule\n')
    if kit:
        (root / L.KIT_ROOT / 'kit_a').mkdir(parents=True)
    yosys = root / 'yosys'
    yosys.write_text('#!/bin/sh\necho "Yosys 0.68 (stub)"\n')
    yosys.chmod(0o755)
    return root, str(yosys)


def spec(**kw):
    s = dict(name='kit_a', top='a', kind='tile', clock='multiple_cts_roots', sources=['rtl/a.v'],
             clock_entry_domains={'core': {'ratio': [1, 1], 'ports': ['clk']}}, std_area_um2=100,
             route={'period_ps': 770, 'utilization': 0.3})
    s.update(kw)
    return s


class Receipt(unittest.TestCase):
    def setUp(self):
        L._MEMO.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.root, self.yosys = make_root(self.tmp.name)
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def lint(self, s, root):
        self.calls.append(s)
        return {'counts': {'consumer': 3}, 'source_sha256': {'rtl/a.v': 'x'}}

    def key(self, s, root=None, policy='reviewed_gray_fifos'):
        return L.key_of(L.components(policy, s, root or self.root, self.yosys))

    def test_key_covers_exact_lint_inputs_only(self):
        k = self.key(spec())
        self.assertEqual(k, self.key(spec(std_area_um2=200, route={'period_ps': 770, 'utilization': 0.5})))
        self.assertNotEqual(k, self.key(spec(params={'W': 2})))
        self.assertNotEqual(k, self.key(spec(route={'period_ps': 700})))          # signoff_period reads period_ps
        self.assertNotEqual(k, self.key(spec(), policy='cdc_synchronizers'))
        (self.root / 'rtl/a.v').write_text('module a; wire w; endmodule\n')
        self.assertNotEqual(k, self.key(spec()))
        self.assertIn('clock_entry_constraints.py', L.components('p', spec(), self.root, self.yosys)['tool'])

    def test_receipt_reused_then_invalidated_by_source_change(self):
        r1 = L.record('reviewed_gray_fifos', self.lint, Boom, spec(), self.root, self.yosys)
        self.assertEqual(len(self.calls), 1)
        doc = json.loads((self.root / L.KIT_ROOT / 'kit_a' / L.RECEIPT).read_text())
        self.assertEqual(doc['schema'], L.SCHEMA)
        self.assertEqual(doc['lints']['reviewed_gray_fifos']['key'], self.key(spec()))
        self.assertNotIn('std_area_um2', self.calls[0])                           # the lint sees the projection
        L._MEMO.clear()
        self.assertEqual(L.record('reviewed_gray_fifos', self.lint, Boom, spec(), self.root, self.yosys), r1)
        self.assertEqual(len(self.calls), 1)                                      # matching receipt: no re-run
        L._MEMO.clear()
        (self.root / 'rtl/a.v').write_text('module a; wire w; endmodule\n')
        L.record('reviewed_gray_fifos', self.lint, Boom, spec(), self.root, self.yosys)
        self.assertEqual(len(self.calls), 2)                                      # stale receipt: re-run

    def test_failure_is_never_cached(self):
        def bad(s, root):
            raise Boom('refused')
        with self.assertRaises(Boom):
            L.record('reviewed_gray_fifos', bad, Boom, spec(), self.root, self.yosys)
        self.assertFalse((self.root / L.KIT_ROOT / 'kit_a' / L.RECEIPT).exists())

    def test_non_fixture_root_goes_to_fleet_never_local(self):
        with mock.patch.object(L, 'local_allowed', return_value=False), \
                mock.patch.object(L, 'remote', return_value=({'remote': 1}, {'host': 'ot-x'})) as rem:
            rec = L.record('reviewed_gray_fifos', self.lint, Boom, spec(), self.root, self.yosys)
        self.assertEqual(rec, {'remote': 1})
        self.assertEqual(self.calls, [])
        rem.assert_called_once()

    def test_local_policy(self):
        env = {k: v for k, v in os.environ.items() if k != 'OT_LINT_LOCAL'}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(L, 'ot_run', return_value='/x/ot-run'):
            self.assertFalse(L.local_allowed(L.HERE.parents[1]))                  # the repository: fleet only
            self.assertFalse(L.local_allowed())
            self.assertTrue(L.local_allowed(self.root))                           # temp fixture root
        with mock.patch.dict(os.environ, {'OT_LINT_LOCAL': '1'}):
            self.assertTrue(L.local_allowed(L.HERE.parents[1]))

    def test_remote_runner_refuses_key_mismatch(self):
        s = spec()
        data = L.payload('reviewed_gray_fifos', s, self.root, 'f' * 64)
        with tempfile.TemporaryDirectory() as run, tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(run)
            self.assertTrue((Path(run) / 'rtl/a.v').is_file())
            out = io.StringIO()
            with mock.patch('sys.stdout', out):
                L.run_job(str(Path(run) / 'lint_job.json'))
            res = json.loads(out.getvalue().strip().splitlines()[-1])
        self.assertFalse(res['ok'])
        self.assertIn('refusing', res['error'])


if __name__ == '__main__':
    unittest.main()
