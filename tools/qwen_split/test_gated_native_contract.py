import json
from pathlib import Path
import shutil
import tempfile
import unittest
from gated_native_contract import build

PACKET=Path(__file__).resolve().parents[2]/'results/arch/qwen_gated_native_contract_1019'

class Contract(unittest.TestCase):
    def test_actual_all_K_and_failclosed_physical_admission(self):
        r=build(PACKET)
        self.assertEqual(r['source_model_checks'],1536)
        self.assertEqual(r['scenario_count'],384)
        self.assertIsNone(r['parent_phase_guarantee'])
        self.assertGreater(r['nonpositive_candidate_ideal_setup_bank_cases'],0)
        self.assertTrue(all(x['physical_admission']=='REFUSED' for x in r['rows']))

    def changed(self, change):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'p';shutil.copytree(PACKET,p)
            change(p)
            with self.assertRaises(AssertionError):build(p)

    def test_wrong_declared_edge_rejected(self):
        def change(p):
            f=p/'behavioral_certificate.json';v=json.loads(f.read_text())
            v['rows'][0]['read_generated_edges']=[1,2,9]
            f.write_text(json.dumps(v))
        self.changed(change)

    def test_missing_bank_rejected(self):
        def change(p):
            f=p/'behavioral_certificate.json';v=json.loads(f.read_text())
            v['rows'].pop();f.write_text(json.dumps(v))
        self.changed(change)

    def test_test_enable_source_mutation_rejected(self):
        def change(p):
            f=p/'source/ot_hdc_cg.sv'
            f.write_text(f.read_text().replace(".SE(1'b0)",".SE(1'b1)"))
        self.changed(change)

if __name__=='__main__':unittest.main(verbosity=2)
