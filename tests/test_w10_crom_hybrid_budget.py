import copy
import unittest
from tools.w10_crom_control_reservation import read
from tools.w10_crom_hybrid_budget import build

class HybridBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h=read('f1af146d6','results/quality/w16_engram_initializer_20261001/hybrid_topology.json')[0]
        cls.t=read('db6ae8e09','results/uarch/w10_crom_ss_route17_budget_r1/budget.json')[0]

    def test_service_not_resident_array_and_no_slack_transfer(self):
        x=build(self.h,self.t)
        self.assertEqual(len(x['cases']),12)
        self.assertEqual(x['persistent_product_FF'],0)
        self.assertEqual(x['operand_FF_per_dense_home_counted_once'],131072)
        self.assertEqual(x['dense_cache_owner_count'],160)
        self.assertFalse(x['historical_SU_slack_used'])
        self.assertFalse(x['physical_admission'])
        self.assertIsNone(x['whole_power_W'])
        self.assertTrue(all(r['source_product_calendar']['commands'] for r in x['cases']))

    def test_missing_owner_or_early_capture_ack_rejected(self):
        for kind in ('owner','ack','roles'):
            h=copy.deepcopy(self.h)
            if kind=='owner':h['topology']['dense_cache_owners'].pop()
            if kind=='ack':
                e=h['product_calendars'][0]['commands'][0]['events'][0]
                e['candidate_owning_slot_reverse_credit_tick']=e['read_capture_tick']
            if kind=='roles':h['hybrid']['single_streamed_product_slot']=0
            with self.subTest(kind=kind),self.assertRaises(ValueError):build(h,self.t)

    def test_forged_provider_label_no_credit(self):
        h=copy.deepcopy(self.h);h['hardware_admission']=True
        h['hybrid']['actual_read_capture_ack_provider']='forged'
        x=build(h,self.t)
        self.assertFalse(x['actual_provider_instantiated'])
        self.assertFalse(x['physical_admission'])
        self.assertIsNone(x['actual_warm_cycles'])

if __name__=='__main__':unittest.main()
