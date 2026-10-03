import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import h4_hbm_w2_canonical_binding as B
BASE=ROOT/'results/uarch/h4_hbm_w2_canonical_binding_20261003'


class CanonicalW2Binding(unittest.TestCase):
    def setUp(self):
        self.primary=(BASE/'primary_interface.svh').read_text()
        self.endpoint=(ROOT/B.ENDPOINT).read_text()

    def test_actual_all43_ports_enrolled(self):
        self.assertEqual(len(B.validate_wiring(self.primary,self.endpoint)),43)

    def test_no_fence_repair_or_ready_stubs(self):
        for name in ['provider_fenced','reverse_fenced','reset_fenced','repair_busy',
                     'p_wr_done_ready','admission_stop','rearm_v']:
            with self.subTest(name=name),self.assertRaises(ValueError):
                B.validate_wiring(self.primary,self.endpoint.replace('.'+name+'('+name+')',"."+name+"(1'b1)"))

    def test_full_tag_and_generation_not_truncated(self):
        for name in ['c_req_tag','c_req_gen','p_req_tag','p_req_gen','p_rsp_tag',
                     'p_rsp_gen','p_wr_done_tag','p_wr_done_gen']:
            with self.subTest(name=name),self.assertRaises(ValueError):
                B.validate_wiring(self.primary,self.endpoint.replace('.'+name+'('+name+')','.'+name+'('+name+'[15:0])'))

    def test_no_raw_controller_substitution(self):
        with self.assertRaises(ValueError):
            B.validate_wiring(self.primary,self.endpoint.replace('ot_w2_nc6_protected_completion #','ot_hdc_qwen_pc_exact_completion #'))

    def test_missing_reverse_authority_refused(self):
        with self.assertRaises(ValueError):
            B.validate_wiring(self.primary,self.endpoint.replace('.reverse_fenced(reverse_fenced)',''))

    def test_default_off_required(self):
        with self.assertRaises(ValueError):
            B.validate_wiring(self.primary,self.endpoint.replace('OPT_EXACT=0','OPT_EXACT=1'))

    def test_partial_or_leaf_timing_not_enrolled(self):
        report=json.loads((BASE/'source-binding.json').read_text())
        self.assertEqual(report['sizing']['protected_bits'],15768)
        self.assertEqual(report['sizing']['primary_CW']+report['sizing']['secondary_CW'],219)
        self.assertEqual(report['calendar']['source_same_client_II_edges'],19)
        self.assertEqual(report['calendar']['exceptional_CAP4_FIX4_min_edges'],8)
        self.assertTrue(report['calendar']['leaf_8_8_9_not_full_controller_supply'])
        self.assertFalse(report['full_controller_runtime_pass'])
        self.assertFalse(report['compile_launched'])
        self.assertIsNone(report['calendar']['eligible_service_upper_bound'])
        self.assertEqual(report['sizing']['correction_boundary_bits'],1232)

    def test_full_source_list_with_real_helper(self):
        report=json.loads((BASE/'source-binding.json').read_text())
        self.assertEqual([r['role'] for r in report['sources']],
                         ['codec','helper','secondary','primary','canonical_endpoint'])
        self.assertEqual(report['calendar']['cost_key'],'W2.NC6.full219')
        self.assertTrue(report['calendar']['replacement_only'])


if __name__=='__main__':unittest.main()
