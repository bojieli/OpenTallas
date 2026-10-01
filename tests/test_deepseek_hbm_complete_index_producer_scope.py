from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_index_producer_scope as P
import deepseek_hbm_complete_index as I

class ProducerDomain(unittest.TestCase):
    def test_retained_source_binding_and_scale253_counterexample(self):
        x=P.build();self.assertEqual(x['checkpoint_data_reads'],0)
        self.assertIn('tools/w19_hbm_tp96_isa.py:f_compressor',x['function_bindings'])
        self.assertIn('tools/w19_hbm_tp96_isa.py:f_index_q',x['function_bindings'])
        f={i['name']:i for i in x['microfixtures']}
        self.assertEqual(f['zero']['UE8M0_candidate_code'],1)
        self.assertEqual(f['scale252']['UE8M0_candidate_code'],252)
        self.assertEqual(f['finite_scale253']['UE8M0_candidate_code'],253)
        self.assertTrue(f['finite_scale253']['all_outputs_finite'])
        self.assertFalse(f['maximum_finite_F32']['all_outputs_finite'])
        self.assertFalse(x['full_source_domain_coverage']);self.assertFalse(x['actual_68B_producer_found'])
    def test_legacy_proxy_cannot_be_canonical_clock(self):
        import numpy as np
        m=I.SIMT((1,32),{}).run([I.K.ins('MOV','v',0)])
        s=m.summary()
        self.assertIn('legacy_interpreter_proxy_cycles_NOT_service_budget',s['costs'])
        self.assertNotIn('serial_instruction_candidate_cycles',s['costs'])
        self.assertIsNone(s['canonical_service_cycles']);self.assertFalse(s['legacy_interpreter_timing_adopted'])

if __name__=='__main__':unittest.main()
