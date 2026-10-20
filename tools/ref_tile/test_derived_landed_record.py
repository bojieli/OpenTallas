"""Paired AHUB6 provenance/source tests; run with the candidate source branch.

The helper alone has no AHUB6 source fixture in main. Its review must include
this paired suite from the AHUB6 candidate, alongside the ordinary clock suites.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import derived_landed_record as D

ROOT = Path(__file__).resolve().parents[2]
RECORD = 'results/arch/kv_ahub6_1020/qkd_ahub_static_dw_g6_lp_record.json'
SPEC = 'physical/ref_tile/qkd_ahub_g6a/spec.json'


class ArtifactIdentity(unittest.TestCase):
    def test_missing_stale_and_escape(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'x').write_text('actual')
            entry=dict(path='x',sha256=hashlib.sha256(b'actual').hexdigest())
            self.assertEqual(D._identity(root,entry),b'actual')
            for delta in (dict(path='../x'),dict(path='/x'),dict(sha256='0'*64),dict(extra=1)):
                with self.subTest(delta=delta),self.assertRaises(ValueError):
                    D._identity(root,dict(entry,**delta))
            with self.assertRaises(FileNotFoundError):D._identity(root,dict(entry,path='missing'))


@unittest.skipUnless((ROOT/RECORD).exists(), 'requires paired AHUB6 source candidate')
class PairedAHUB6(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.spec=json.loads((ROOT/SPEC).read_text())
        self.record=json.loads((ROOT/RECORD).read_text())
        p=self.record['derived_lp']
        artifacts=[p[k] for k in ('canonical_record','canonical_rtl','canonical_spec','canonical_generator','postprocessor')]
        artifacts+=p['inputs']+p['outputs']
        for entry in artifacts:
            path=entry['path'];dst=self.root/path;dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/path,dst)

    def validate(self):return D.validate(self.spec,self.root,self.record)

    def rehash(self,key):
        item=self.record['derived_lp'][key]
        item['sha256']=hashlib.sha256((self.root/item['path']).read_bytes()).hexdigest()

    def alter_output(self,old,new):
        item=self.record['derived_lp']['outputs'][0];p=self.root/item['path']
        text=p.read_text();self.assertIn(old,text);p.write_text(text.replace(old,new,1))
        item['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()

    def test_canonical_replay_full_record_and_actual_topology(self):self.validate()

    def test_missing_provenance(self):
        del self.record['derived_lp']['canonical_rtl']
        with self.assertRaisesRegex(ValueError,'provenance fields'):self.validate()

    def test_stale_output_hash(self):
        entry=self.record['derived_lp']['outputs'][0];(self.root/entry['path']).write_text('stale')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):self.validate()

    def test_stale_source_hash(self):
        item=self.record['derived_lp']['inputs'][0];(self.root/item['path']).write_text('stale')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):self.validate()

    def test_missing_actual_source_identity(self):
        self.record['derived_lp']['outputs'].pop()
        with self.assertRaisesRegex(ValueError,'actual source identity'):self.validate()

    def test_effective_parameters_changed(self):
        self.spec['params']['Z_LAND']=7
        with self.assertRaisesRegex(ValueError,'parameters changed'):self.validate()

    def test_extra_full_contract_field(self):
        self.record['unreviewed_extra']='unsafe'
        with self.assertRaisesRegex(ValueError,'full canonical contract'):self.validate()

    def test_changed_full_contract_field(self):
        self.record['compiler']['reset_release_added_edges']+=1
        with self.assertRaisesRegex(ValueError,'full canonical contract'):self.validate()

    def test_rehashed_canonical_record_is_replayed(self):
        p=self.root/self.record['derived_lp']['canonical_record']['path'];d=json.loads(p.read_text())
        d['unknown_contract']='extra';p.write_text(json.dumps(d));self.rehash('canonical_record')
        with self.assertRaisesRegex(ValueError,'canonical deterministic replay'):self.validate()

    def test_rehashed_canonical_rtl_is_replayed(self):
        p=self.root/self.record['derived_lp']['canonical_rtl']['path'];p.write_text(p.read_text()+'\n')
        self.rehash('canonical_rtl')
        with self.assertRaisesRegex(ValueError,'canonical deterministic replay'):self.validate()

    def test_rehashed_wrong_clock_topology(self):
        self.alter_output('u_lpr_root_r0 (.ck(ck_c)','u_lpr_root_r0 (.ck(ck_w)')
        with self.assertRaisesRegex(ValueError,'topology changed'):self.validate()

    def test_rehashed_wrong_landing(self):
        self.alter_output('.i(amw_c), .bank(lpl_0_bank)', '.i(ame_c), .bank(lpl_0_bank)')
        with self.assertRaisesRegex(ValueError,'topology changed'):self.validate()

    def test_rehashed_changed_landing_width(self):
        self.alter_output('.W(((71) - (0) + 1))','.W(73)')
        with self.assertRaisesRegex(ValueError,'topology changed'):self.validate()

    def test_rehashed_changed_reset_leaf_expression(self):
        self.alter_output('localparam integer LPR_LEAVES_c = 1+', 'localparam integer LPR_LEAVES_c = 2+')
        with self.assertRaisesRegex(ValueError,'parameter expressions changed'):self.validate()


if __name__=='__main__':unittest.main()
