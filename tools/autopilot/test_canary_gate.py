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
    def test_missing_reference_holds(self):self.assertFalse(self.gate())
    def test_pending_newer_run_does_not_mask_completed_pass(self):
        self.runref('old','PASS');self.assertTrue(self.gate());self.runref('new',src='new123456789');self.assertTrue(self.gate())
    def test_pending_only_holds(self):
        self.runref('new');self.assertFalse(self.gate())
    def test_pending_newer_run_with_completed_fail_holds(self):
        self.runref('bad','FAIL');self.runref('new',src='new123456789')
        ok,why=assess(self.row,self.root,self.repo,self.git);self.assertFalse(ok);self.assertIn('NO-BASELINE',why)
    def test_unbound_result_is_not_completed(self):
        p=self.runref('x');(p/'canary.json').write_text(json.dumps({'verdict':'PASS','src':'other'}));self.assertFalse(self.gate())
    def test_stale_corrective_older_fail_newer_fail_allowed(self):
        p=self.runref('bad1','FAIL');self.runref('bad2','FAIL',src='new123456789')
        self.row['canary_fix']='abc123456789@'+str(p/'canary.json');self.assertTrue(self.gate())
    def test_corrective_with_newer_pass_held(self):
        p=self.runref('bad','FAIL');self.runref('good','PASS',src='new123456789')
        self.row['canary_fix']='abc123456789@'+str(p/'canary.json')
        ok,why=assess(self.row,self.root,self.repo,self.git);self.assertFalse(ok);self.assertIn('newer NO-REGRESSION',why)
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
    def test_main_moving_past_released_canary_does_not_hold_kit_on_canary_flow(self):
        # AUTOPILOT-FIX 10-25 23:30: rows run on the newest released canary's flow; main's flow is not consulted
        self.runref('old','PASS');self.runref('new',src='new123456789')
        self.git=lambda args,**kw:(0,'tools/die_plan/gen_phys.py\n' if args[-1]=='main' else '','')
        ok,why=assess(self.row,self.root,self.repo,self.git);self.assertTrue(ok,why);self.assertIn('covers kit flow',why)
        self.runref('only','PASS',src='abc123456789')
        self.assertTrue(self.gate())
    def test_newer_completed_canary_holds_kits_from_older_flow(self):
        self.runref('old','PASS');self.runref('new','PASS',src='new123456789')
        self.git=lambda args,**kw:(0,'tools/die_plan/gen_phys.py\n' if args[-2]=='new123456789' and args[-1]=='kit123456789' else '','')
        ok,why=assess(self.row,self.root,self.repo,self.git);self.assertFalse(ok);self.assertIn('differs from released canary new123456789',why)
    def test_fail_holds_and_correction_requires_known_path(self):
        p=self.runref('bad','FAIL');self.assertFalse(self.gate())
        self.row['canary_fix']='wrong@'+str(p.parent/'other/canary.json');self.assertFalse(self.gate())
        self.row['canary_fix']='abc123456789@'+str(p/'canary.json');self.assertTrue(self.gate())
    def test_new_flow_blocks_old_pass(self):
        self.runref('old','PASS');self.git=lambda *a,**kw:(0,'tools/die_plan/hold_gate.tcl\n','');self.assertFalse(self.gate())
    def test_main_pass_does_not_clear_kit_from_different_flow(self):
        self.runref('ref','PASS')
        self.git=lambda args,**kw:(0,'tools/die_plan/gen_phys.py\n' if args[-1]=='kit123456789' else '', '')
        ok,why=assess(self.row,self.root,self.repo,self.git);self.assertFalse(ok);self.assertIn('differs from released canary',why)
    def test_cp1_uses_s81_reference_but_unknown_die_cannot_bypass(self):
        self.runref('s81_ref','PASS')
        self.row['die']='cp1';self.assertTrue(self.gate())
        self.row['die']='unknown';self.assertFalse(self.gate())
    def test_retired_reference_item_neither_binds_nor_holds(self):
        self.row['die']='hbm'
        self.runref('old_cal','PASS',die='hbm',item='calendar@old')
        ok,why=assess(self.row,self.root,self.repo,self.git);self.assertFalse(ok);self.assertIn('item tkm@new',why)
        self.runref('new_tkm',die='hbm',item='tkm@new')
        ok,why=assess(self.row,self.root,self.repo,self.git);self.assertFalse(ok);self.assertIn('pending',why)
        self.assertIn('new_tkm',why)
    def test_kv_core_kit_binds_core_canary(self):
        self.runref('kvio','PASS',die='qwen_kvsys');self.runref('kvcore','FAIL',die='qwen_kvsys_core',item='e1')
        self.row['die']='qwen_kvsys';self.assertTrue(self.gate())
        self.row['runner']='/x/run_kit_kv.sh'
        ok,why=assess(self.row,self.root,self.repo,self.git);self.assertFalse(ok);self.assertIn('kvcore',why)
        del self.row['runner'];k=self.root/'kit';k.mkdir();(k/'run_kit_kv.sh').write_text('')
        self.row['kit']='epyc1:'+str(k);self.assertFalse(self.gate())
    def test_other_die_core_change_does_not_hold_frozen_qc(self):
        self.row['die']='qwen_compute'
        self.runref('qc','PASS',die='qwen_compute')
        spec_path=self.repo/'tools/flow_canary/canaries.json'
        spec=json.loads(spec_path.read_text())
        spec.update(watch=['tools/die_plan/*','physical/die_plan/*'],
                    die_plans={'qwen_compute':['qwen_compute']})
        spec_path.write_text(json.dumps(spec))
        self.git=lambda *a,**kw:(0,'physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py\n','')
        self.assertTrue(self.gate())
        # A change in QC's own recipe, or the shared flow, still blocks it.
        for path in ['physical/die_plan/qwen_compute/cores/gen.py', 'tools/die_plan/gen_phys.py']:
            self.git=lambda *a,**kw:(0,path+'\n','')
            self.assertFalse(self.gate())

    def test_live_spec_fingerprint_other_die_plan_and_docs_do_not_hold_ref_tile_does(self):
        # the canaries.json on this checkout (the live fingerprint), frozen QC and S81-HEAD rows
        live=Path(__file__).resolve().parents[1]/'flow_canary/canaries.json'
        (self.repo/'tools/flow_canary/canaries.json').write_text(live.read_text())
        spec=json.loads(live.read_text())
        for die in ('qwen_compute','s81_head'):
            self.row['die']=die
            self.runref(die,'PASS',die=die,item=next(c['item'] for c in spec['canaries'] if c['die']==die))
            for path in ['physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py',
                         'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py',
                         'physical/die_plan/qwen_kvsys/cores/harden/results/kv3_head_eighth_e1.json',
                         'tools/flow_canary/trigger.py', 'tools/flow_canary/baseline.py',
                         'tools/ref_tile/README.md', 'tools/ref_tile/tests/test_x.py', 'tools/ref_tile/examples/a.tcl',
                         'tools/die_plan/README.md', 'physical/common_flow/x.log', 'tools/autopilot/autopilot.py',
                         'results/fleet_viz/x.json', 'docs/x.md']:
                self.git=lambda *a,**kw:(0,path+'\n','')
                ok,why=assess(self.row,self.root,self.repo,self.git);self.assertTrue(ok,die+' '+path+': '+why)
            for path in ['tools/ref_tile/ref_tile.py', 'tools/ref_tile/layout_dump.tcl', 'tools/ref_tile/ref_route.sh',
                         'tools/die_plan/gen_phys.py', 'physical/common_flow/clock_spine.tcl']:
                self.git=lambda *a,**kw:(0,path+'\n','')
                ok,why=assess(self.row,self.root,self.repo,self.git);self.assertFalse(ok,die+' '+path)
                self.assertIn(path,why)

    def test_adopt_never_stalls_observation(self):
        self.row['mode']='adopt';self.assertTrue(self.gate())

if __name__=='__main__':unittest.main()
