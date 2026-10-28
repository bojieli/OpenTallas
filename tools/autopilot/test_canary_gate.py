import json
import os
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from canary_gate import assess

class Gate(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); self.root=Path(self.t.name)
        self.repo=self.root/'repo'; p=self.repo/'tools/flow_canary';p.mkdir(parents=True)
        (p/'canaries.json').write_text(json.dumps({'watch':['tools/die_plan/*'],'canaries':[{'die':'hbm','item':'tkm@new'},{'die':'qwen_kvsys_core','item':'e1'}]}))
        self.row={'die':'s81','mode':'submit','src':'codex/kit@kit123456789'}
        self.git=lambda *a,**kw:(0,'','')
    def tearDown(self):self.t.cleanup()
    def runref(self,name,verdict=None,src='abc123456789',die='s81',item=None):
        sp={'die':die}
        if item:sp['item']=item
        p=self.root/name;p.mkdir();(p/'canary_meta.json').write_text(json.dumps({'spec':sp,'src_commit':src}))
        if verdict:(p/'canary.json').write_text(json.dumps({'verdict':verdict,'src':src}))
        q=p/"canary_meta.json"
        os.utime(q, ns=(1000000000+len(list(self.root.glob("*/canary_meta.json"))),)*2)
        return p
    def gate(self):return assess(self.row,self.root,self.repo,self.git)[0]
    def verdicts(self, values):
        from unittest.mock import patch
        return patch('canary_gate.regression', side_effect=lambda r,*a,**k: values.get(r['src'], ('NO-REGRESSION','ok')))

    def test_missing_and_pending_are_background(self):
        self.assertTrue(self.gate())
        self.runref('pending')
        self.assertTrue(self.gate())

    def test_unbound_result_is_pending_not_release_evidence(self):
        p=self.runref('x')
        (p/'canary.json').write_text(json.dumps({'verdict':'PASS','src':'other'}))
        ok,why=assess(self.row,self.root,self.repo,self.git)
        self.assertTrue(ok)
        self.assertIn('pending',why)

    def test_missing_source_and_watch_integrity_still_fail(self):
        self.row['src']=''
        self.assertFalse(self.gate())
        self.row['src']='kit@123'
        (self.repo/'tools/flow_canary/canaries.json').write_text('{}')
        self.assertFalse(self.gate())

    def test_matching_regression_blocks_even_with_pending_and_correction(self):
        p=self.runref('bad','FAIL')
        self.runref('pending',src='new123')
        self.row['canary_fix']='x@'+str(p/'canary.json')
        with self.verdicts({'abc123456789':('REGRESSION','hold got worse')}):
            ok,why=assess(self.row,self.root,self.repo,self.git)
            self.assertFalse(ok)
            self.assertIn('REGRESSION',why)

    def test_different_source_regression_is_advisory(self):
        self.runref('bad','FAIL')
        self.git=lambda *a,**k:(0,'tools/die_plan/gen_phys.py\n','')
        with self.verdicts({'abc123456789':('REGRESSION','bad')}):
            self.assertTrue(self.gate())

    def test_newer_matching_release_clears_old_regression(self):
        self.runref('bad','FAIL')
        self.runref('good','PASS',src='good123')
        with self.verdicts({'abc123456789':('REGRESSION','bad')}):
            self.assertTrue(self.gate())

    def test_newer_unknown_does_not_erase_old_regression(self):
        self.runref('bad','FAIL')
        self.runref('unknown','FAIL',src='unknown123')
        with self.verdicts({'abc123456789':('REGRESSION','bad'),'unknown123':('NO-BASELINE','not measured')}):
            self.assertFalse(self.gate())

    def test_no_baseline_advisory_but_evaluation_error_still_fails(self):
        self.runref('unknown','FAIL')
        with self.verdicts({'abc123456789':('NO-BASELINE','not measured')}):
            self.assertTrue(self.gate())
        with self.verdicts({'abc123456789':('NO-BASELINE','regression verdict error ValueError: invalid')}):
            self.assertFalse(self.gate())

    def test_corrective_reference_identity_still_fails_closed(self):
        self.row['canary_fix']='x@'+str(self.root/'missing/canary.json')
        self.assertFalse(self.gate())
        p=self.runref('other','FAIL',die='qwen_compute')
        self.row['canary_fix']='x@'+str(p/'canary.json')
        self.assertFalse(self.gate())

    def test_stale_corrective_does_not_serialize_released_flow(self):
        p=self.runref('old')
        self.row['canary_fix']='x@'+str(p/'canary.json')
        self.runref('new','PASS',src='new123')
        self.assertTrue(self.gate())

    def test_matching_regression_has_no_24_hour_expiry(self):
        p=self.runref('bad','FAIL')
        t=os.path.getmtime(p/'canary.json')-25*3600
        os.utime(p/'canary.json',(t,t))
        self.runref('new','PASS',src='new123')
        self.git=lambda args,**kw:(0,'tools/die_plan/gen_phys.py\n' if args[-2]=='new123' else '','')
        with self.verdicts({'abc123456789':('REGRESSION','bad')}):
            self.assertFalse(self.gate())

    def test_kv_alias_and_core_reference_stay_separate(self):
        self.runref('type','PASS',die='qwen_kvsys')
        self.runref('core','FAIL',src='badcore',die='qwen_kvsys_core',item='e1')
        self.row['die']='kv'
        with self.verdicts({'badcore':('REGRESSION','core regression')}):
            self.assertTrue(self.gate())
            self.row['runner']='/work/run_kit_kv.sh'
            self.assertFalse(self.gate())

    def test_real_watch_scope_only_applies_matching_regression(self):
        live=Path(__file__).resolve().parents[1]/'flow_canary/canaries.json'
        (self.repo/'tools/flow_canary/canaries.json').write_text(live.read_text())
        self.row['die']='qwen_compute'
        spec=json.loads(live.read_text())
        item=next(c['item'] for c in spec['canaries'] if c['die']=='qwen_compute')
        self.runref('qc','FAIL',die='qwen_compute',item=item)
        with self.verdicts({'abc123456789':('REGRESSION','bad')}):
            self.git=lambda *a,**kw:(0,'physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py\n','')
            self.assertFalse(self.gate()) # unrelated change leaves the regressed flow identical
            self.git=lambda *a,**kw:(0,'tools/die_plan/gen_phys.py\n','')
            self.assertTrue(self.gate()) # changed flow has no measured regression yet

    def test_existing_adoption_observation_unblocked(self):
        self.row['mode']='adopt'
        self.assertTrue(self.gate())

if __name__=='__main__':unittest.main()
