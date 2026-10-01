from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_index_service_plan as P
class Service(unittest.TestCase):
    def test_source_wire_and_nonalias_lifetimes(self):
        m=P.plan();self.assertIn('IKD1 unchanged',m['wire']);self.assertFalse(m['hardware_admitted'])
        self.assertTrue(m['capacity_fits_64KiB_only'])
        ids={p['id']:p for p in m['lifetimes']}
        self.assertIn('controller_actual_WRACK',ids['payload_WRcommit']['requires'])
        self.assertIn('consumer_done',ids['credit_return_and_reuse']['requires'])
        self.assertFalse(m['packed_key_reuse_model_only']['wholeprogram_all_keys_packed_claim'])
    def test_metadata_needs_independent_expected_context(self):
        def execute(wrong):
            mem={}
            for family,n in [('descriptor',8),('external_lease',16)]:
                for w in range(n):
                    mem[f'{family}{w}']=np.full((1,32),w,np.uint32)
                    mem[f'protected_expected_{family}{w}']=np.full((1,32),w,np.uint32)
            if wrong:mem['descriptor2'][0,1]+=1
            return P.authority_execute(mem,trace=True)
        good=execute(False);bad=execute(True)
        self.assertEqual(good.stores['authority_difference'][0,0],0)
        self.assertNotEqual(bad.stores['authority_difference'][0,0],0)
        self.assertEqual(good.metrics['shared_warp_issues'],49)
