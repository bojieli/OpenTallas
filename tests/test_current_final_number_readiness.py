"""Adversarial publication checks: a plausible PASS must not transfer scope."""
import copy
import importlib.util
import tempfile
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('current_readiness', Path(__file__).resolve().parents[1]/'tools/current_final_number_readiness.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

class CurrentReadinessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ('source.sv', 'reviewed.log'):
            (self.root/name).write_text('pinned receipt\n')
        self.identity = {k: {'bound': True} for k in m.IDENTITY_FIELDS}
        self.identity['source_sha256'] = {'source.sv': m.digest(self.root/'source.sv')}
        self.binding = {'identity_bound': True, 'identity': self.identity, 'claimed_modes': ['AR']}

    def certificate(self, gate='G3', target='qwen_rom'):
        c = dict(schema='opentallas.current-research-gate-certificate.v1', status='pass',
                 evidence_scope='current_full_goal', target=target, gate=gate, mode='AR',
                 identity=copy.deepcopy(self.identity), evidence_sha256={'reviewed.log': m.digest(self.root/'reviewed.log')},
                 checks={k: True for k in m.REQUIREMENTS[gate]}, qualified_modes=['AR'],
                 timing_scope='contextual_parent_extracted', macro_SS_clk_to_q_bound=True,
                 outline_mm=[26, 33], complete_area_mm2=800, source_matched_shoreline_PHY=True,
                 GPU_organisation=True, capacity_basis='actual_layer_pitch_OBS_PG_pin_via_exclusions',
                 layout_basis='disjoint_source_matched_instance_union')
        domains = {'streaming': 1.2e9}
        if target.startswith('deepseek'):
            domains['serial_chain'] = .9e9
        c['timing'] = {d: {check: dict(corner=corner, uncertainty_ps=unc,
             period_ps=1e12/hz, worst_slack_ps=0, unconstrained_paths=0, violations=0)
             for check,corner,unc in [('setup','SS',60),('hold','FF',25)]} for d,hz in domains.items()}
        return c

    def errors(self, c):
        return m.evaluate(self.root, c['target'], c['gate'], self.binding, c, {})['blockers']

    def test_exact_AR_does_not_require_dflash(self):
        for gate in m.REQUIREMENTS:
            self.assertEqual(self.errors(self.certificate(gate)), [])

    def test_TT_and_old_fmax_cannot_qualify(self):
        c=self.certificate(); c['timing']['streaming']['setup']['corner']='TT'
        self.assertTrue(self.errors(c))
        c=self.certificate(); c['timing']['streaming']['setup']['period_ps']=1e12/1.087e9
        self.assertTrue(self.errors(c))

    def test_missing_FF_and_relaxed_uncertainty(self):
        c=self.certificate(); del c['timing']['streaming']['hold']
        self.assertTrue(self.errors(c))
        for check in ['setup','hold']:
            c=self.certificate(); c['timing']['streaming'][check]['uncertainty_ps']=0
            self.assertTrue(self.errors(c))

    def test_negative_slack_unconstrained_and_nan_refused(self):
        for field,value in [('worst_slack_ps',-1),('worst_slack_ps',float('nan')),('unconstrained_paths',1),('violations',1)]:
            c=self.certificate(); c['timing']['streaming']['hold'][field]=value
            self.assertTrue(self.errors(c))

    def test_inherited_area_and_half_track_reserve_not_routed_proof(self):
        c=self.certificate(); c['capacity_basis']='assumed_50_percent_PG_reserve'
        self.assertTrue(self.errors(c))
        c=self.certificate(); c['layout_basis']='inherited_418mm2_debit'
        self.assertTrue(self.errors(c))

    def test_missing_macro_and_hbm_shoreline(self):
        c=self.certificate(); del c['macro_SS_clk_to_q_bound']; self.assertTrue(self.errors(c))
        c=self.certificate(target='qwen_hbm'); del c['source_matched_shoreline_PHY']; self.assertTrue(self.errors(c))

    def test_deepseek_serial_chain_required(self):
        c=self.certificate(target='deepseek_rom'); self.assertFalse(self.errors(c))
        del c['timing']['serial_chain']; self.assertTrue(self.errors(c))

    def test_source_change_and_wrong_config_refused(self):
        c=self.certificate(); c['identity']['parameters']={'NP':1}; self.assertTrue(self.errors(c))
        (self.root/'source.sv').write_text('successor\n'); self.assertTrue(self.errors(self.certificate()))

    def test_receipt_tampering_and_missing_receipts(self):
        c=self.certificate(); c['evidence_sha256']={}; self.assertTrue(self.errors(c))
        c=self.certificate(); (self.root/'reviewed.log').write_text('changed\n'); self.assertTrue(self.errors(c))

    def test_directed_or_column_scope_refused(self):
        for scope in ['directed_uniform','standalone_column','historical_full_die']:
            c=self.certificate(); c['evidence_scope']=scope; self.assertTrue(self.errors(c))
        c=self.certificate(); c['timing_scope']='standalone_column_extracted'; self.assertTrue(self.errors(c))

    def test_claimed_speculation_needs_own_qualification(self):
        self.binding['claimed_modes']=['AR','DFlash']
        for gate in ['G2','G4']:
            self.assertTrue(self.errors(self.certificate(gate)))

    def test_nonfinite_oversized_or_missing_geometry_refused(self):
        for outline,area in [([26,33],924.2886),([27,33],800),([],800),(['proxy',33],800),([26,33],float('inf'))]:
            c=self.certificate(); c['outline_mm']=outline; c['complete_area_mm2']=area
            self.assertTrue(self.errors(c))

    def test_missing_current_identity_refused(self):
        self.binding['identity_bound']=False
        for gate in m.REQUIREMENTS:
            self.assertTrue(self.errors(self.certificate(gate)))

    def budget(self):
        row=dict(schema='opentallas.current-physical-budget.v1',target='deepseek_rom',
                 identity=self.identity,source_sha256=self.identity['source_sha256'],
                 reviewed_complete_inventory=True,unpriced_claim_determining_terms=[],
                 outline_mm=[26,33],complete_area_mm2=800)
        p=self.root/'successor_budget.json'
        p.write_text(json.dumps(row))
        self.binding['physical_budget']=dict(path=p.name,sha256=m.digest(p))
        return p

    def test_explicit_successor_budget_not_vetoed_by_historical_FAIL(self):
        self.budget()
        c=self.certificate(target='deepseek_rom')
        (self.root/'G3.json').write_text(json.dumps(c))
        self.binding['certificates']={'G3':'G3.json'}
        base=self.root/m.BASE;base.mkdir(parents=True)
        (base/'target_bindings.json').write_text(json.dumps({'targets':{'deepseek_rom':self.binding}}))
        old=Path('results/uarch/dsrom_full_product_binding_20261002/compiled_whole_budget-r6.json')
        (self.root/old).parent.mkdir(parents=True)
        shutil.copy2(m.ROOT/old,self.root/old)
        report=m.build(self.root)
        self.assertLess(report['deepseek_S58_physical_screen']['margin_mm2'],0)
        self.assertEqual(report['deepseek_current_bound_budget']['status'],'pass')
        self.assertEqual(report['targets']['deepseek_rom']['gates']['G3']['status'],'pass')
        self.assertFalse(report['terminal_ready'])

    def test_budget_tamper_identity_and_unpriced_cost_refused(self):
        p=self.budget()
        row=json.loads(p.read_text());row['complete_area_mm2']=700;p.write_text(json.dumps(row))
        self.assertEqual(m.current_budget(self.root,self.binding,{})['status'],'blocked')
        self.binding['physical_budget']['sha256']=m.digest(p)
        row['identity']['parameters']={'other':True};p.write_text(json.dumps(row));self.binding['physical_budget']['sha256']=m.digest(p)
        self.assertEqual(m.current_budget(self.root,self.binding,{})['status'],'blocked')
        p=self.budget();row=json.loads(p.read_text());row['unpriced_claim_determining_terms']=['actualPG'];p.write_text(json.dumps(row));self.binding['physical_budget']['sha256']=m.digest(p)
        self.assertEqual(m.current_budget(self.root,self.binding,{})['status'],'blocked')

    def test_missing_inputs_fail_closed(self):
        report=m.build(self.root)
        self.assertFalse(report['terminal_ready'])
        self.assertEqual(report['captured_qwen_TP4_numeric']['status'],'blocked')

    def test_captured_bad_vector_or_receipt_refused(self):
        base=Path('results/rtl/qwen_rom_TP4_terminal_20261002')
        dst=self.root/base
        dst.mkdir(parents=True)
        for name in ['terminal_manifest.json','capture.json','original_terminal.json','verification_capture.json','verification_replay.json']:
            shutil.copy2(m.ROOT/base/name,dst/name)
        self.assertEqual(m.captured_qwen(self.root,{})['status'],'pass')
        v=json.loads((dst/'verification_replay.json').read_text())
        v['checks']['L35_die3_x.hex']['mismatches']=1
        (dst/'verification_replay.json').write_text(json.dumps(v))
        # Even a coherently refreshed receipt cannot hide a failing numeric check.
        t=json.loads((dst/'terminal_manifest.json').read_text())
        t['artifact_sha256']['verification_replay.json']=m.digest(dst/'verification_replay.json')
        (dst/'terminal_manifest.json').write_text(json.dumps(t))
        self.assertEqual(m.captured_qwen(self.root,{})['status'],'blocked')

    def test_cli_refuses_final_and_stale(self):
        result=subprocess.run([sys.executable,str(m.ROOT/'tools/current_final_number_readiness.py'),'--check','--require-final'],capture_output=True,text=True)
        self.assertEqual(result.returncode,1)
        (self.root/'tools').mkdir()
        shutil.copy2(m.ROOT/'tools/current_final_number_readiness.py',self.root/'tools')
        out=self.root/m.BASE
        out.mkdir(parents=True)
        (out/'readiness.json').write_text('{}')
        result=subprocess.run([sys.executable,str(self.root/'tools/current_final_number_readiness.py'),'--check'],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertEqual((out/'readiness.json').read_text(),'{}')

    def test_captured_PASS_is_not_current_completion(self):
        report=m.build()
        self.assertEqual(report['captured_qwen_TP4_numeric']['status'],'pass')
        self.assertFalse(report['captured_qwen_TP4_numeric']['current_G2_credit'])
        self.assertTrue(report['deepseek_S58_physical_screen']['budget_consistent'])
        self.assertLess(report['deepseek_S58_physical_screen']['margin_mm2'],0)
        self.assertFalse(report['terminal_ready'])
        self.assertEqual(set(report['targets']),set(m.TARGETS))

if __name__ == '__main__':
    unittest.main()
