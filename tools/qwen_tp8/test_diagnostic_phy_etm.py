"""Actual approved profile, failed-case context and downstream null-reference causals."""
import ast
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import diagnostic_phy_etm as P
import die_sta_libs as D
from die_clock.qualification import require_measured_input_boundaries


class ExactInputBoundary(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.saved=Path(self.temp.name);self.root=self.saved/'src';self.case=self.saved/'out/case';self.case.mkdir(parents=True)
        self.view=self.root/P.DIRECTORY;self.view.mkdir(parents=True)
        source=Path(__file__).resolve().parents[2]/P.DIRECTORY
        for suffix in P.APPROVED:shutil.copy2(source/(P.MASTER+suffix),self.view/(P.MASTER+suffix))
        chain=self.saved/'chain';chain.mkdir()
        for n in ('DIAGNOSTIC_ONLY','NOT_A_DIE_RESULT'):(chain/n).write_text('PHYSICAL_DIAGNOSTIC_ONLY\nORIGINAL_GEN_EXIT=1\nCOMPILER=FAIL\n')
        self.manifest=self.saved/'saved_case_diagnostic_manifest.json'
        self.frozen=dict(schema='opentallas.saved_case_physical_diagnostic.v1',original_gen_exit=1,compiler_verdict='FAIL',qualification_eligible=False,
                         sha256={str((self.view/(P.MASTER+s)).relative_to(self.saved)):v for s,v in P.APPROVED.items()})
        self.write_manifest()
        self.libs={c:P.DIRECTORY+'/'+P.MASTER+'_'+c+'.lib'for c in ('tt','ff','ss')}
        self.env={P.FLAG:'1','OT_CHAIN_DIAGNOSTIC':'1','OT_SAVED_CASE_PHYSICAL_DIAGNOSTIC':'1',
                  'OT_SAVED_CASE_ROOT':str(self.saved),'OT_SAVED_CASE_MANIFEST':str(self.manifest)}
        self.patch=patch.dict(os.environ,self.env);self.patch.start();self.addCleanup(self.patch.stop)

    def write_manifest(self):self.manifest.write_text(json.dumps(self.frozen))
    def admit(self):return P.admit(P.MASTER,self.root,self.case,self.view,self.libs)
    def test_exact_source_model_has_null_native_R_and_all_roles(self):
        m=self.admit();self.assertIsNone(m['native_insertion_ps']);self.assertFalse(m['physical_qualification_eligible'])
        self.assertEqual(m['qualification']['status'],'UNMEASURED');self.assertEqual(m['generated_clock_outputs'],[])
        for c in self.libs:self.assertEqual(P.validate_lib_roles((self.root/self.libs[c]).read_text())['arcs'],{'setup_rising':3,'hold_rising':3,'rising_edge':3})
    def test_flag_off_retains_missing_measured_reference_failure(self):
        with patch.dict(os.environ,{P.FLAG:'0'}):self.assertIsNone(self.admit())
        with self.assertRaisesRegex(ValueError,'missing real clock insertion'):
            D.measured_clock_refs(self.view/(P.MASTER+'_tt.lib'),self.view/'insertion.json','tt')
    def test_other_master_never_uses_this_path(self):self.assertIsNone(P.admit('unrelated',self.root,self.case,self.view,self.libs))
    def test_missing_diagnostic_context_rejected(self):
        with patch.dict(os.environ,{'OT_CHAIN_DIAGNOSTIC':'0'}):
            with self.assertRaisesRegex(ValueError,'requires'):self.admit()
    def test_missing_permanent_marker_rejected(self):
        (self.saved/'chain/NOT_A_DIE_RESULT').unlink()
        with self.assertRaisesRegex(ValueError,'marker'):self.admit()
    def test_normal_release_manifest_rejected(self):
        self.frozen['qualification_eligible']=True;self.write_manifest()
        with self.assertRaisesRegex(ValueError,'no qualification'):self.admit()
    def test_unfrozen_source_rejected(self):
        self.frozen['sha256'].pop(next(iter(self.frozen['sha256'])));self.write_manifest()
        with self.assertRaisesRegex(ValueError,'unfrozen'):self.admit()
    def test_source_digest_mutant_rejected(self):
        p=self.view/(P.MASTER+'_model.sv');p.write_text(p.read_text()+'\n// changed\n')
        with self.assertRaisesRegex(ValueError,'source profile'):self.admit()
    def test_missing_corner_rejected(self):
        self.libs.pop('ss')
        with self.assertRaisesRegex(ValueError,'full K source'):self.admit()
    def test_wrong_boundary_clock_direction_rejected(self):
        text=(self.view/(P.MASTER+'_tt.lib')).read_text().replace('pin (clk) {\n      direction : input','pin (clk) {\n      direction : output')
        with self.assertRaisesRegex(ValueError,'direction'):P.validate_lib_roles(text)
    def test_generated_clock_output_rejected(self):
        text=(self.view/(P.MASTER+'_tt.lib')).read_text().replace('pin (tx_up) {','pin (tx_up) {\n      clock : true;')
        with self.assertRaisesRegex(ValueError,'only input clk'):P.validate_lib_roles(text)
    def test_wrong_related_clock_rejected(self):
        text=(self.view/(P.MASTER+'_tt.lib')).read_text().replace('related_pin : "clk"','related_pin : "other"',1)
        with self.assertRaisesRegex(ValueError,'sole input clk'):P.validate_lib_roles(text)
    def test_missing_setup_arc_rejected(self):
        text=(self.view/(P.MASTER+'_tt.lib')).read_text().replace('timing_type : setup_rising','timing_type : setup_falling',1)
        with self.assertRaisesRegex(ValueError,'arc roles'):P.validate_lib_roles(text)
    def test_duplicate_clock_pin_rejected(self):
        text=(self.view/(P.MASTER+'_tt.lib')).read_text().replace('    pin (rst_n) {','    pin (clk) { direction : input; clock : true; }\n    pin (rst_n) {')
        with self.assertRaisesRegex(ValueError,'duplicate'):P.validate_lib_roles(text)
    def test_tcl_has_typed_boundary_no_latency_zero_or_native_clock_target(self):
        leaves={P.MASTER:{c:{'clk':None}for c in ('tt','ff','ss')}}
        text=D.clock_tcl({'stream':[('ucie_kv/clk',P.MASTER,'clk')]},leaves,'tt')
        self.assertIn('UNMEASURED_INPUT_BOUNDARY ucie_kv/clk',text)
        self.assertNotIn('set_clock_latency',text);self.assertIn('set ot_sta_qualification UNMEASURED',text)
        self.assertIn('set ot_region_qualification UNMEASURED',text)
        views={};P.annotate(views,{P.MASTER:self.admit()})
        with self.assertRaisesRegex(ValueError,'UNMEASURED'):require_measured_input_boundaries(views)
    def test_null_reference_never_admitted_for_another_master_or_off_flag(self):
        with self.assertRaisesRegex(ValueError,'exact diagnostic'):D.reference_tcl('x/clk','x','clk',None,'stream')
        with patch.dict(os.environ,{P.FLAG:'0'}):
            with self.assertRaisesRegex(ValueError,'exact diagnostic'):D.reference_tcl('ucie_kv/clk',P.MASTER,'clk',None,'stream')
    def test_actual_libs_main_and_native_prep_refuse_without_zero_inheritance(self):
        shutil.copy2(self.view/(P.MASTER+'.lef'),self.case/'elements.lef')
        (self.case/'die.v').write_text('module die; wire n_clk_d2d; qfd_clkrx clk_rx(.pll_d2d(n_clk_d2d)); '+P.MASTER+' ucie_kv(.clk(n_clk_d2d)); endmodule\n')
        (self.case/'port_dirs.json').write_text(json.dumps({P.MASTER:P.ROLES,'qfd_clkrx':{'pll_d2d':'output'}}))
        bind=self.saved/'bind.json';bind.write_text(json.dumps({'masters_detail':{P.MASTER:{'bound':True,'libs':self.libs,'view':P.DIRECTORY}}}))
        out=self.saved/'libs'
        with patch.object(sys,'argv',['die_sta_libs.py','--case',str(self.case),'--repo',str(self.root),'--bind',str(bind),'--out',str(out)]),contextlib.redirect_stdout(io.StringIO()):D.main()
        views=json.loads((out/'views.json').read_text());self.assertEqual(views['clock_qualification'],'UNMEASURED')
        self.assertNotIn(P.MASTER,views['assumed_clock_insertion']);self.assertNotIn(P.MASTER,views['insertion_ps'])
        self.assertNotIn('set_clock_latency',(out/'clocks_tt.tcl').read_text())
        geom=self.saved/'geom';geom.mkdir();(geom/'clknets.tsv').write_text('clk_rx/pll_d2d\tucie_kv/clk\t'+P.MASTER+'\t0\t0\n')
        native=self.saved/'native';script=Path(__file__).resolve().parents[1]/'die_clock/qwen_compute_dieclk_prep.py'
        p=subprocess.run([sys.executable,str(script),'--geom',str(geom),'--clocks-dir',str(out),'--out',str(native)],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0);self.assertIn('UNMEASURED',p.stderr);self.assertFalse((native/'targets.json').exists())
        if os.environ.get('OT_DIAG_PHY_TEST_ARTIFACT_DIR'):
            review=Path(os.environ['OT_DIAG_PHY_TEST_ARTIFACT_DIR']);review.mkdir(parents=True,exist_ok=True)
            for name in ('views.json','clocks_tt.tcl','clocks_ff.tcl','clocks_ss.tcl'):shutil.copy2(out/name,review/name)
            (review/'native_prep.stderr').write_text(p.stderr)
            (review/'SCOPE.json').write_text(json.dumps(dict(scope='isolated source/model fixture; not an actual Q die/physical run',native_prep_rc=p.returncode,targets_exist=False,qualification='UNMEASURED',native_insertion=None),indent=2)+'\n')
    def test_default_numeric_tcl_byte_identical_to_actual_baseline(self):
        # Baseline blob 83ccdb8e is pinned in the packet; extract only its production clock_tcl.
        repo=Path(__file__).resolve().parents[2]
        text=subprocess.check_output(['git','show','a28cc4ded:tools/qwen_tp8/die_sta_libs.py'],cwd=repo,text=True)
        node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name=='clock_tcl')
        gl={'PERIOD':D.PERIOD,'HOLD_U':D.HOLD_U,'HOLD_NOTE':D.HOLD_NOTE};exec(compile(ast.Module(body=[node],type_ignores=[]),'baseline-clock-tcl','exec'),gl)
        leaves={'L':{c:{'ck':125.0}for c in ('tt','ff','ss')},'D':{c:{'ck':350.0}for c in ('tt','ff','ss')}}
        doms={'stream':[('l/ck','L','ck'),('d/ck','D','ck')]}
        with patch.dict(os.environ,{P.FLAG:'0'}):
            for c in ('tt','ff','ss'):
                for hold in ('tile','die'):self.assertEqual(D.clock_tcl(doms,leaves,c,hold_budget=hold),gl['clock_tcl'](doms,leaves,c,hold_budget=hold))

if __name__=='__main__':unittest.main()
