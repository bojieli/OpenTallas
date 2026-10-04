import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
S=importlib.util.spec_from_file_location('join',Path(__file__).resolve().parents[1]/'tools/model_dsrom_xneed_s82_join.py')
M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
class SourceJoin(unittest.TestCase):
    def test_replay(self):self.assertEqual(M.model(),json.loads((M.ROOT/'model.json').read_text()))
    def test_actual_parent_is_external_field(self):
        m=M.model();self.assertTrue(m['external_field_boundary']);self.assertFalse(m['lookahead_installed_in_parent'])
    def test_replication_exact_once(self):
        r=M.model()['replication'];self.assertEqual(r['FF_increment_per_rankdie'],1876*252)
        self.assertEqual(r['FF_increment_all_rankdies'],1876*252*328)
        self.assertEqual(r['BF_pairs_unchanged'],512)
    def test_no_half_rate(self):
        c=M.model()['cycles'];self.assertEqual(c['lookahead_accepted_II_model'],1)
        self.assertEqual(c['lookahead_increment_model'],0);self.assertIsNone(c['measured_added_cycles'])
    def test_old_pipeline_not_selected(self):
        c=M.model()['cycles'];self.assertEqual((c['inherited_Rcap0_total_extra'],c['inherited_Rcap1_total_extra']),(2,3))
        self.assertIsNone(c['qualified_selected_total_extra'])
    def test_gross_area_requires_reconciliation(self):
        r=M.model()['replication'];self.assertLess(r['gross_margin_after_uncredited_increment_mm2'],0)
        self.assertEqual(r['overlap_credit'],0);self.assertTrue(r['area_reconciliation_required'])
    def test_tampered_source_refused(self):
        with tempfile.TemporaryDirectory() as t:
            r=Path(t)/'r';shutil.copytree(M.ROOT,r)
            e=json.loads((r/'source_inputs.json').read_text())[0];p=r/e['archive'];p.write_bytes(p.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'source archive changed'):M.model(r)
    def test_no_execution_admission(self):
        m=M.model();self.assertFalse(m['new_RTL']);self.assertEqual(m['new_builds'],0);self.assertFalse(m['adoption'])
if __name__=='__main__':unittest.main()
