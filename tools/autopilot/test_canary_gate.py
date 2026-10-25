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
        (p/'canaries.json').write_text(json.dumps({'watch':['tools/die_plan/*']}))
        self.row={'die':'s81','mode':'submit','src':'codex/kit@kit123456789'}
        self.git=lambda *a,**kw:(0,'','')
    def tearDown(self):self.t.cleanup()
    def runref(self,name,verdict=None,src='abc123456789',die='s81'):
        p=self.root/name;p.mkdir();(p/'canary_meta.json').write_text(json.dumps({'spec':{'die':die},'src_commit':src}))
        if verdict:(p/'canary.json').write_text(json.dumps({'verdict':verdict,'src':src}))
        q=p/"canary_meta.json"
        os.utime(q, ns=(1000000000+len(list(self.root.glob("*/canary_meta.json"))),)*2)
        return p
    def gate(self):return assess(self.row,self.root,self.repo,self.git)[0]
    def test_missing_reference_holds(self):self.assertFalse(self.gate())
    def test_pending_newer_run_does_not_mask_completed_pass(self):
        self.runref('old','PASS');self.assertTrue(self.gate());self.runref('new',src='new123456789');self.assertTrue(self.gate())
    def test_pending_only_holds(self):
        self.runref('new');self.assertFalse(self.gate())
    def test_pending_newer_run_with_completed_fail_holds(self):
        self.runref('bad','FAIL');self.runref('new',src='new123456789')
        ok,why=assess(self.row,self.root,self.repo,self.git);self.assertFalse(ok);self.assertIn('failed',why)
    def test_unbound_result_is_not_completed(self):
        p=self.runref('x');(p/'canary.json').write_text(json.dumps({'verdict':'PASS','src':'other'}));self.assertFalse(self.gate())
    def test_stale_corrective_older_fail_newer_fail_allowed(self):
        p=self.runref('bad1','FAIL');self.runref('bad2','FAIL',src='new123456789')
        self.row['canary_fix']='abc123456789@'+str(p/'canary.json');self.assertTrue(self.gate())
    def test_corrective_with_newer_pass_held(self):
        p=self.runref('bad','FAIL');self.runref('good','PASS',src='new123456789')
        self.row['canary_fix']='abc123456789@'+str(p/'canary.json')
        ok,why=assess(self.row,self.root,self.repo,self.git);self.assertFalse(ok);self.assertIn('newer PASS',why)
    def test_corrective_branch_prefixed_string_resolved_by_path(self):
        p=self.runref('bad','FAIL');self.runref('pend',src='new123456789')
        self.row['canary_fix']='claude/path-qc-sramif-1025@90bf56dfa@'+str(p/'canary.json');self.assertTrue(self.gate())
    def test_corrective_pending_newest_allowed_older_pending_held(self):
        p=self.runref('p1');self.row['canary_fix']='x@'+str(p/'canary.json');self.assertTrue(self.gate())
        self.runref('p2',src='new123456789');self.assertFalse(self.gate())
    def test_corrective_unknown_or_other_die_held(self):
        self.runref('bad','FAIL');q=self.runref('qc','FAIL',die='qwen_compute')
        self.row['canary_fix']='x@'+str(q/'canary.json')
        ok,why=assess(self.row,self.root,self.repo,self.git);self.assertFalse(ok);self.assertIn('qwen_compute',why)
        self.row['canary_fix']='x@'+str(self.root/'nope/canary.json')
        ok,why=assess(self.row,self.root,self.repo,self.git);self.assertFalse(ok);self.assertIn('unknown',why)
    def test_main_flow_changed_with_pending_canary_on_it_allowed(self):
        self.runref('old','PASS');self.runref('new',src='new123456789')
        self.git=lambda args,**kw:(0,'tools/die_plan/gen_phys.py\n' if args[-2]=='abc123456789' and args[-1]=='main' else '','')
        self.assertTrue(self.gate())
    def test_main_flow_changed_with_no_canary_on_it_held(self):
        self.runref('old','PASS');self.runref('new',src='new123456789')
        self.git=lambda args,**kw:(0,'tools/die_plan/gen_phys.py\n' if args[-1]=='main' else '','')
        ok,why=assess(self.row,self.root,self.repo,self.git);self.assertFalse(ok);self.assertIn('flow changed',why)
    def test_fail_holds_and_correction_requires_known_path(self):
        p=self.runref('bad','FAIL');self.assertFalse(self.gate())
        self.row['canary_fix']='wrong@'+str(p.parent/'other/canary.json');self.assertFalse(self.gate())
        self.row['canary_fix']='abc123456789@'+str(p/'canary.json');self.assertTrue(self.gate())
    def test_new_flow_blocks_old_pass(self):
        self.runref('old','PASS');self.git=lambda *a,**kw:(0,'tools/die_plan/hold_gate.tcl\n','');self.assertFalse(self.gate())
    def test_main_pass_does_not_clear_kit_from_different_flow(self):
        self.runref('ref','PASS')
        self.git=lambda args,**kw:(0,'tools/die_plan/gen_phys.py\n' if args[-1]=='kit123456789' else '', '')
        ok,why=assess(self.row,self.root,self.repo,self.git);self.assertFalse(ok);self.assertIn('differs from PASS canary',why)
    def test_cp1_uses_s81_reference_but_unknown_die_cannot_bypass(self):
        self.runref('s81_ref','PASS')
        self.row['die']='cp1';self.assertTrue(self.gate())
        self.row['die']='unknown';self.assertFalse(self.gate())
    def test_adopt_never_stalls_observation(self):
        self.row['mode']='adopt';self.assertTrue(self.gate())

if __name__=='__main__':unittest.main()
