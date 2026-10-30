import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import plan_block_identity as B
import kit_wave as K


class Identity(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.oldpath=self.root/'old'/'plan.json';self.newpath=self.root/'new'/'plan.json'
        for p in (self.oldpath,self.newpath):
            p.parent.mkdir();(p.parent/'pins.json').write_text('{"clk":[1,2]}\n')
        self.old={'partition_types':{'x':{'pins_file':str(self.oldpath.parent/'pins.json'),'clock':{'period':833},'reset':{'entry':1},'params':{'N':4},'x':10}},'budgets':{'x':{'clk':405}}}
        self.new=copy.deepcopy(self.old);self.new['partition_types']['x']['pins_file']='pins.json'
        self.record={'die':'d','item':'x','block_sha':B.identities(self.old,self.oldpath)['x']['raw_sha'],'status':'FAIL','class':'PLAN','attempt':2,'reason':'preserve actual failure'}
        self.key=K.item_key('d','event','x',self.record['block_sha']);self.state={'items':{self.key:self.record}}
    def ids(self,p=None,path=None):return B.identities(p or self.new,path or self.newpath,B.PINS)
    def test_raw_exact_legacy_and_no_file_read(self):
        self.old['partition_types']['x']['pins_file']='missing.json'
        r=B.identities(self.old,self.oldpath)['x']
        self.assertEqual(r['block_sha'],B.fingerprint({'type':self.old['partition_types']['x'],'budget':self.old['budgets']['x']}))
    def test_same_payload_different_path(self):
        a=self.ids(self.old,self.oldpath)['x'];b=self.ids()['x']
        self.assertNotEqual(a['raw_sha'],b['raw_sha']);self.assertEqual(a['normalized_node'],b['normalized_node']);self.assertEqual(a['block_sha'],b['block_sha'])
    def test_same_basename_different_bytes(self):
        (self.newpath.parent/'pins.json').write_text('{"clk":[1,3]}\n')
        self.assertNotEqual(self.ids(self.old,self.oldpath)['x']['block_sha'],self.ids()['x']['block_sha'])
    def test_missing_malformed_and_non_json_fail_closed(self):
        for text in ('broken','null','{"x":NaN}'):
            (self.newpath.parent/'pins.json').write_text(text)
            with self.assertRaises((ValueError,json.JSONDecodeError)):self.ids()
        (self.newpath.parent/'pins.json').unlink()
        with self.assertRaises(FileNotFoundError):self.ids()
    def test_every_nonpath_change_matters(self):
        original=self.ids()['x']['block_sha']
        for key,value in (('clock',{'period':832}),('reset',{'entry':2}),('params',{'N':8}),('x',11)):
            p=copy.deepcopy(self.new);p['partition_types']['x'][key]=value
            self.assertNotEqual(original,self.ids(p)['x']['block_sha'])
        p=copy.deepcopy(self.new);p['budgets']['x']['clk']=406
        self.assertNotEqual(original,self.ids(p)['x']['block_sha'])
    def test_reuse_requires_offline_receipt_preserves_exact_old_record(self):
        old=self.ids(self.old,self.oldpath);new=self.ids();blocks={'x':new['x']['block_sha']}
        eff,holds=B.reuse_blocks(blocks,new,old,self.state['items'],die='d',event='event')
        self.assertIn('x',holds);self.assertEqual(eff,blocks)
        receipts=B.proposal(self.state,self.old,self.new,old_path=self.oldpath,new_path=self.newpath,die='d',items=['x'])
        before=copy.deepcopy(self.state)
        eff,holds=B.reuse_blocks(blocks,new,old,self.state['items'],die='d',event='event',receipts=receipts)
        self.assertFalse(holds);self.assertEqual(eff['x'],self.record['block_sha']);self.assertEqual(before,self.state)
        self.assertEqual(self.state['items'][self.key]['status'],'FAIL');self.assertEqual(self.state['items'][self.key]['attempt'],2)
        # The receipt binds actual payload bytes, including later shared-path changes.
        (self.oldpath.parent/'pins.json').write_text('{"clk":[9,9]}')
        (self.newpath.parent/'pins.json').write_text('{"clk":[9,9]}')
        _,holds=B.reuse_blocks(blocks,self.ids(),self.ids(self.old,self.oldpath),self.state['items'],die='d',event='event',receipts=receipts)
        self.assertIn('x',holds)
    def test_bad_stored_hash_and_live_state_refused(self):
        for status in ('RUNNING','LAUNCHING','RETRY-INFRA','ENQUEUED'):
            self.record['status']=status
            with self.assertRaisesRegex(ValueError,'in-flight'):B.proposal(self.state,self.old,self.new,old_path=self.oldpath,new_path=self.newpath,die='d',items=['x'])
        self.record['status']='FAIL';self.record['block_sha']='0'*64
        with self.assertRaisesRegex(ValueError,'exact baseline'):B.proposal(self.state,self.old,self.new,old_path=self.oldpath,new_path=self.newpath,die='d',items=['x'])
    def test_real_profile_change_not_reused_or_held(self):
        self.new['partition_types']['x']['x']=11
        _,holds=B.reuse_blocks({'x':self.ids()['x']['block_sha']},self.ids(),self.ids(self.old,self.oldpath),self.state['items'],die='d',event='event')
        self.assertFalse(holds)
    def test_later_core_profile_changes_are_visible_and_legacy_ambiguity_refused(self):
        p={'hard_cores':[{'module':'C','x':1},{'module':'C','x':2}]}
        before=self.ids(p)['C'];p['hard_cores'][1]['x']=3;after=self.ids(p)['C']
        self.assertEqual(before['raw_sha'],after['raw_sha']);self.assertNotEqual(before['block_sha'],after['block_sha'])
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            B.reuse_record({'item':'C','block_sha':before['raw_sha'],'status':'FAIL'},before,before,item='C',old_key='k',baseline_plan='a',current_plan='b')
    def test_remote_probe_source_default_and_optin(self):
        self.oldpath.write_text(json.dumps(self.old));self.newpath.write_text(json.dumps(self.new))
        def probe(args):
            p=subprocess.run([sys.executable,'-c',K.PROBE_PLAN,json.dumps(args)],capture_output=True,text=True,check=True)
            return json.loads(p.stdout.removeprefix('AP_JSON '))
        raw=probe({'plan':str(self.newpath)})
        self.assertEqual(raw['blocks']['x'],B.identities(self.new,self.newpath)['x']['raw_sha']);self.assertNotIn('identities',raw)
        semantic=probe({'plan':str(self.newpath),'block_identity':B.PINS,'identity_baseline_plan':str(self.oldpath)})
        self.assertEqual(semantic['blocks']['x'],self.ids()['x']['block_sha']);self.assertEqual(semantic['baseline_identities']['x']['block_sha'],semantic['blocks']['x'])
        (self.newpath.parent/'pins.json').unlink();self.assertIn('error',probe({'plan':str(self.newpath),'block_identity':B.PINS}))
    def test_semantic_optin_holds_automatic_infra_retry_before_probe(self):
        from unittest.mock import patch
        from test_kit_wave import FakeAP, cfg
        for mode,expected in ((B.RAW,1),(B.PINS,0)):
            with tempfile.TemporaryDirectory() as directory:
                rec=dict(self.record,status='RETRY-INFRA',event='event28w_c',kind='type')
                rec['die']='qwen_kvsys'
                state={'items':{K.item_key(rec['die'],rec['event'],'x',rec['block_sha']):rec}}
                K.save_state(state,directory)
                ap=FakeAP(directory,json.dumps(cfg(block_identity=mode)))
                with patch.object(K,'collect'),patch.object(K,'plan_dies',return_value=([],[])):
                    result=K.step(ap)
                self.assertEqual(len(ap.units),expected)
                if mode==B.PINS:self.assertEqual(next(iter(result['items'].values())),rec)

    def test_malformed_receipt_config_holds_instead_of_crashing_tick(self):
        current=self.ids();blocks={'x':current['x']['block_sha']}
        for bad in (['receipt'],'receipt',1):
            effective,holds=B.reuse_blocks(blocks,current,self.ids(self.old,self.oldpath),
                                          self.state['items'],die='d',event='event',receipts=bad)
            self.assertEqual(effective,blocks);self.assertIn('must be an object',holds['x'])

    def test_pin_free_type_keeps_legacy_hash(self):
        p={'partition_types':{'z':{'width':12}}}
        self.assertEqual(B.identities(p,self.newpath)['z']['block_sha'],self.ids(p)['z']['block_sha'])

if __name__=='__main__':unittest.main()
