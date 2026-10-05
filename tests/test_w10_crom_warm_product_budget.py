import copy
import unittest
from decimal import Decimal as D
from tools.w10_crom_control_reservation import read
from tools.w10_crom_warm_product_budget import build, inventory

class WarmProductTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.warm = read('9bd2ccdf0', 'results/quality/w16_engram_initializer_20261001/warm_residency.json')[0]

    def test_actual_owner_scope(self):
        self.assertEqual(inventory(self.warm), [(r,l) for r in range(4) for l in (1,14)])

    def test_missing_duplicate_and_wrong_storage_rejected(self):
        for mutation in ('duplicate','missing','storage','gamma'):
            w = copy.deepcopy(self.warm)
            owners = w['topology_cases']['stage_local_candidate']['absolute_owner_keys']
            if mutation == 'duplicate': owners.append(dict(next(o for o in owners if o['layer']==1)))
            if mutation == 'missing': owners[:] = [o for o in owners if not (o['rank']==0 and o['layer']==1)]
            if mutation == 'storage': w['extra_product_bits_per_Engram_home'] = 0
            if mutation == 'gamma': next(s for s in w['stages'] if s['layer']==1)['gamma_families'] = 1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): inventory(w)

    def test_cost_and_no_qualification_from_forged_labels(self):
        w = copy.deepcopy(self.warm)
        w['hardware_admission'] = True
        w['warm_tokens']['actual_RTL_cache_module'] = 'forged'
        power = read('e79394b1c','results/uarch/w10_q_power_envelope_r1/power.json')[0]
        clock = read('fea811df4','results/uarch/w10_q_existing_icg_r1/clock.json')[0]
        area = read('6da3c7a60','results/uarch/w10_q_elaboration_inventory_r1/construction.json')[0]
        x = build(w,power,clock,area)
        self.assertEqual(x['per_affected_home']['total_NAND2_cells'],5111808)
        self.assertEqual(x['per_affected_home']['additional_clock_buffers'],27313)
        self.assertEqual(D(x['per_affected_home']['conditional_cell_plus_macro_area_mm2']),D('1.40397281856'))
        self.assertFalse(x['physical_admission'])
        self.assertFalse(x['complete_inventory'])
        self.assertIsNone(x['actual_warm_cycles'])
        self.assertIsNone(x['additional_control_FF_bits'])
        self.assertEqual(x['single_gamma_savings_credit'],0)

if __name__ == '__main__': unittest.main()
