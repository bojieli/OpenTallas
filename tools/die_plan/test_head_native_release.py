"""Focused fail-closed checks for explicit conditional native-reset receipts."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import head_native_release as H


class NativeReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sources = {s: self.root / Path(s).name for s in [
            'rtl/dsrom_sys/s81_head/ot_s81hd_serdes_link_ls.sv',
            *['rtl/dsrom_sys/s81_link/' + n + '.sv' for n in
              ['ot_pdie_serdes_locksafe', 'ot_pdie_serdes', 'ot_s81_kp4_dec', 'ot_s81_kp4_dchn']]]}
        self.files = {}
        for name, p in self.sources.items():
            p.write_text(name)
            self.files[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
        self.bindings = [dict(part='lk_' + str(i), target='u_phy.u_link.u_dec.u_chn.rst_n',
                              native_clock_root='pma_rck') for i in range(12)]
        self.P = SimpleNamespace(raw={'identity': 'candidate'}, parts={b['part']: {'type': 'hd_serdes'} for b in self.bindings},
            types={'hd_serdes': dict(contents=[dict(inst='u_phy', module='ot_s81hd_serdes_link_ls',
                params=dict(LOCKSAFE=1, HOLD_EDGES=64), bind=dict(pma_lock='pad:pma_lock',
                pma_rck='pad:pma_rck', ck='clk', rst_n='rst_n'))],
                hard_cores=[dict(inst='u_phy.u_link.u_dec.u_chn', module='ot_s81_kp4_dchn')])})
        self.W = dict(note='', parts={b['part']: dict(core_release={b['target']: None},
            native_release={b['target']: dict(status='PENDING', native_clock_root='pma_rck', core_cycle_release=None)})
            for b in self.bindings}, release_qualification=dict(verdict='PENDING', native_targets=self.bindings))
        runs = {}
        bench = self.root / 'bench.sv'
        bench.write_text('always @(leaf_clock or pck)')
        self.files[bench.name] = hashlib.sha256(bench.read_bytes()).hexdigest()
        for name in ['positive', 'early_hold', 'ignore_lock', 'leaf_reset', 'leaf_clock']:
            log = self.root / (name + '.log')
            text = '\n'.join(f'HEAD_RELEASE epoch={e} guard_rck_edge=66 native_rck_edge=68' for e in range(3))
            log.write_text(text + '\nHEAD_NATIVE_RELEASE PASS leaf_binding=1\n' if name == 'positive' else 'FATAL: injected failure\n')
            self.files[log.name] = hashlib.sha256(log.read_bytes()).hexdigest()
            runs[name] = dict(log=log.name, bench=bench.name, returncode=0 if name == 'positive' else 1)
        self.r = dict(schema='opentallas.head_native_release.v1', plan_sha256=H.digest(self.P.raw),
            files=self.files, bindings=self.bindings, proof=dict(verdict='PASS', guard_edges=66, leaf_edges=68,
            actual_codec_and_fifo=True, actual_leaf_binding=True,
            epochs=['cold', 'stopped_clock_lock_loss', 'stopped_clock_warm_reset'],
            mutants={n: 'DETECTED' for n in runs if n != 'positive'}, runs=runs,
            production_sources={n: self.files[p.name] for n, p in self.sources.items()}))

    def run_receipt(self, r=None, P=None):
        receipt = self.root / 'receipt.json'
        receipt.write_text(json.dumps(self.r if r is None else r))
        with patch('cores.resolve', side_effect=lambda n: self.sources[n]):
            return H.qualify(self.P if P is None else P, copy.deepcopy(self.W), receipt)

    def test_valid_is_conditional_and_keeps_unknown_core_deadline(self):
        w = self.run_receipt()
        self.assertEqual(w['release_qualification']['verdict'], 'QUALIFIED_CONDITIONAL')
        for b in self.bindings:
            self.assertIsNone(w['parts'][b['part']]['core_release'][b['target']])
            self.assertEqual(w['parts'][b['part']]['native_release'][b['target']]['min_recovered_edges_after_authorities_high'], 68)

    def test_wrong_plan_rejected(self):
        p = copy.deepcopy(self.P);p.raw['identity'] = 'old POR'
        with self.assertRaisesRegex(ValueError, 'plan identity'):self.run_receipt(P=p)

    def test_missing_duplicate_or_unknown_leaf_rejected(self):
        for bindings in [self.bindings[:-1], self.bindings[:-1] + [self.bindings[0]],
                         self.bindings[:-1] + [dict(self.bindings[-1], target='other.rst_n')]]:
            r = copy.deepcopy(self.r);r['bindings'] = bindings
            with self.assertRaises(ValueError):self.run_receipt(r)

    def test_wrong_actual_authority_or_module_rejected(self):
        for field, value in [('pma_lock', "1'b1"), ('pma_rck', 'clk'), ('rst_n', 'die_reset')]:
            p = copy.deepcopy(self.P);p.types['hd_serdes']['contents'][0]['bind'][field] = value
            with self.assertRaises(ValueError):self.run_receipt(P=p)
        p = copy.deepcopy(self.P);p.types['hd_serdes']['contents'][0]['module'] = 'ot_s81hd_serdes_link'
        with self.assertRaises(ValueError):self.run_receipt(P=p)

    def test_changed_input_rejected(self):
        next(iter(self.sources.values())).write_text('changed source')
        with self.assertRaisesRegex(ValueError, 'changed input'):self.run_receipt()

    def test_missing_or_ineffective_mutant_rejected(self):
        for change in ['missing', 'passed']:
            r = copy.deepcopy(self.r)
            if change == 'missing':del r['proof']['mutants']['leaf_clock']
            else:r['proof']['runs']['leaf_clock']['returncode'] = 0
            with self.assertRaises(ValueError):self.run_receipt(r)

    def test_shortened_hold_or_incomplete_epochs_rejected(self):
        for field, value in [('guard_edges', 65), ('leaf_edges', 67), ('epochs', ['cold'])]:
            r = copy.deepcopy(self.r);r['proof'][field] = value
            with self.assertRaises(ValueError):self.run_receipt(r)

    def test_posedge_only_clock_observation_rejected(self):
        p = self.root / 'bench.sv'
        p.write_text('always @(posedge pck)')
        self.r['files'][p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'both-edge'):self.run_receipt()


if __name__ == '__main__':
    unittest.main()
