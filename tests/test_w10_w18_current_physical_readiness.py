import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
spec=importlib.util.spec_from_file_location('readiness',Path('tools/w10_w18_current_physical_readiness.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records={k:json.loads(m.blob(m.BASE,p)) for k,p in m.RECORDS.items()}
        cls.x=json.loads(Path('results/quality/w10_w18_current_physical_readiness_r1/readiness.json').read_text())
    def test_current_source_currency_with_mutant(self):
        source=self.records['q_inventory']['source']['source_sha256']
        join=m.source_join(source,lambda p:m.blob(m.BASE,p))
        self.assertTrue(all(r['matches'] for r in join if 'matches' in r))
        altered=m.source_join(source,lambda p:m.blob(m.BASE,p)+b'corrupt')
        self.assertTrue(all(not r['matches'] for r in altered if 'matches' in r))
    def test_structure_or_artifact_labels_never_admit_route(self):
        records=copy.deepcopy(self.records)
        records['bf_structure']['physical_admission']=True
        records['q_fit']['q_final_evidence']['necessary_terminal_inputs_present']=True
        x=m.build(records,{},[],{'synthetic_all_gates_pass':True})
        self.assertFalse(x['physical_admission'])
        self.assertFalse(x['bf']['contextual_SS_FF_qualified'])
        self.assertFalse(x['q']['current_final_LEF_ETMs_qualified'])
        self.assertEqual(x['w18']['queued_routes_admitted'],[])
        self.assertFalse(x['w18']['die_rebase_admitted'])
    def test_terminal_failures_are_whole_context_not_r2r_only(self):
        w=self.x['w18']
        self.assertEqual(w['root_SS_overall_ps'],-570.76)
        self.assertEqual(w['root_FF_hold_ps'],-4.59)
        self.assertEqual(w['region_baseline_SS_overall_ps'],-669.49)
        self.assertEqual(w['region_baseline_FF_hold_ps'],-218.36)
        self.assertEqual(self.x['new_jobs'],0)
        self.assertTrue(self.x['retired_AGIdocks_all_excluded'])
        for k,p in self.x['input_pins'].items():
            if 'commit' in p:self.assertEqual(hashlib.sha256(m.blob(p['commit'],p['path'])).hexdigest(),p['sha256'])
