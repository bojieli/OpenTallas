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
    def runref(self,name,verdict=None):
        p=self.root/name;p.mkdir();(p/'canary_meta.json').write_text(json.dumps({'spec':{'die':'s81'},'src_commit':'abc123456789'}))
        if verdict:(p/'canary.json').write_text(json.dumps({'verdict':verdict,'src':'abc123456789'}))
        q=p/"canary_meta.json"
        os.utime(q, ns=(1000000000+len(list(self.root.glob("*/canary_meta.json"))),)*2)
        return p
    def gate(self):return assess(self.row,self.root,self.repo,self.git)[0]
    def test_missing_reference_holds(self):self.assertFalse(self.gate())
    def test_new_pending_supersedes_old_pass(self):
        self.runref('old','PASS');self.assertTrue(self.gate());self.runref('new');self.assertFalse(self.gate())
    def test_fail_holds_and_correction_requires_exact_source_and_path(self):
        p=self.runref('bad','FAIL');self.assertFalse(self.gate())
        self.row['canary_fix']='wrong@'+str(p/'canary.json');self.assertFalse(self.gate())
        self.row['canary_fix']='abc123456789@'+str(p/'canary.json');self.assertTrue(self.gate())
    def test_new_flow_blocks_old_pass(self):
        self.runref('old','PASS');self.git=lambda *a,**kw:(0,'tools/die_plan/hold_gate.tcl\n','');self.assertFalse(self.gate())
    def test_main_pass_does_not_clear_kit_from_different_flow(self):
        self.runref('ref','PASS')
        self.git=lambda args,**kw:(0,'tools/die_plan/gen_phys.py\n' if args[-2]=='kit123456789' else '', '')
        self.assertFalse(self.gate())
    def test_cp1_uses_s81_reference_but_unknown_die_cannot_bypass(self):
        self.runref('s81_ref','PASS')
        self.row['die']='cp1';self.assertTrue(self.gate())
        self.row['die']='unknown';self.assertFalse(self.gate())
    def test_adopt_never_stalls_observation(self):
        self.row['mode']='adopt';self.assertTrue(self.gate())

if __name__=='__main__':unittest.main()
