"""Source/view-bound parameter producer tests for post-expansion health leaves."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import kv_health_plane as H
import kv_expand_parameters as P


class HealthParameters(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.module = 'qkd_hp_or2'
        self.rtl = 'leaf.sv'
        (self.root / self.rtl).write_text('module qkd_hp_or2 #(parameter integer MUT=0)(input a,output q); assign q=a; endmodule')
        vd = self.root / 'views' / self.module
        vd.mkdir(parents=True)
        for suffix in ('.lef', '_tt.lib', '_ff.lib', '/insertion.json'):
            (Path(str(vd / self.module) + suffix) if not suffix.startswith('/') else vd / 'insertion.json').write_text('{}')
        self.binding = dict(master=self.module, rtl=self.rtl, view='views/' + self.module)
        self.profiles = {self.module: dict(parameters={'MUT': 0}, identity=P.artifact_identity(self.root, self.binding['view'], self.rtl))}
        self.plan = dict(nodes=[dict(kind='join', id='fault_10'), dict(kind='join', id='fault_11')])
        self.patch = patch.dict(H.MASTERS, {'join': self.binding})
        self.patch.start(); self.addCleanup(self.patch.stop)

    def test_defaults_preserved_and_native_enumerator_roundtrip(self):
        rows, sidecar = H.parameter_ledger(self.root, self.plan, self.profiles, True)
        self.assertEqual(set(rows), {'hp_fault_10', 'hp_fault_11'})
        self.assertEqual(sidecar['hp_fault_10'], {'MUT': "32'sb" + '0' * 32})
        report = dict(leaves={self.module: self.binding}, parameter_instances=rows)
        insts = [(self.module, n, {}, {}) for n in rows]
        P.verify_bound(self.root, report, sidecar, insts, {self.module: self.rtl}, {}, True)
        del report['parameter_instances']['hp_fault_11']
        with self.assertRaisesRegex(ValueError, 'ledger incomplete'):
            P.verify_bound(self.root, report, sidecar, insts, {self.module: self.rtl}, {}, True)

    def test_missing_profile_refused(self):
        with patch.dict(os.environ, {'OT_KV_PARAM_DIAG': '0'}):
            with self.assertRaisesRegex(ValueError, 'missing selected parameter profile'):
                H.parameter_ledger(self.root, self.plan, {}, True)

    def test_strict_unqualified_refused(self):
        with self.assertRaisesRegex(ValueError, 'native parameter qualification missing'):
            H.parameter_ledger(self.root, self.plan, self.profiles, False)

    def test_explicit_diagnostic_keeps_identity_not_qualification(self):
        with patch.dict(os.environ, {'OT_KV_PARAM_DIAG': '1'}):
            rows, _ = H.parameter_ledger(self.root, self.plan, {}, True)
        self.assertFalse(rows['hp_fault_10']['profile']['native_qualified'])
        self.assertEqual(rows['hp_fault_10']['profile']['identity'], self.profiles[self.module]['identity'])

    def test_changed_rtl_or_view_refused(self):
        for f in [self.root / self.rtl, self.root / self.binding['view'] / (self.module + '_tt.lib')]:
            original = f.read_text(); f.write_text(original + 'changed')
            with self.assertRaisesRegex(ValueError, 'source/view mismatch'):
                H.parameter_ledger(self.root, self.plan, self.profiles, True)
            f.write_text(original)

    def test_duplicate_instance_refused(self):
        plan = dict(nodes=[self.plan['nodes'][0]] * 2)
        with self.assertRaisesRegex(ValueError, 'duplicate health instance'):
            H.parameter_ledger(self.root, plan, self.profiles, True)

    def test_changed_default_refused(self):
        (self.root / self.rtl).write_text('module qkd_hp_or2 #(parameter integer MUT=1)(input a); endmodule')
        with self.assertRaisesRegex(ValueError, 'source/view mismatch'):
            H.parameter_ledger(self.root, self.plan, self.profiles, True)


if __name__ == '__main__':
    unittest.main()
