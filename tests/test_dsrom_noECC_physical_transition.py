import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('transition',ROOT/'tools/dsrom_noECC_physical_transition.py')
t=importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)

class TransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=t.build()

    def test_rectangle_union_no_double_PG_OBS_charge(self):
        self.assertEqual(t.union_area([[0,0,2,2],[1,1,3,3]]),7)
        self.assertEqual(t.union_area([[0,0,2,2],[0,0,2,2]]),4)
        self.assertEqual(t.intersection([0,0,2,2],[2,0,3,2]),0)
        m4=self.m['local_macro_layer_exclusions']['M4']
        self.assertAlmostEqual(m4['OBS_PG_union_um2'],m4['OBS_union_um2'])
        self.assertLess(m4['remaining_planar_area_um2'],10)
        self.assertFalse(m4['usable_tracks_proven'])

    def test_complete_macro_pin_payload_preserved(self):
        g=self.m['macro']
        names={p['name'] for p in g['pins']}
        self.assertEqual(len(names),290)
        self.assertTrue({'clk','ce_in','VDD','VSS'}<=names)
        self.assertEqual(sum(n.startswith('rd_out[') for n in names),274)
        pair=self.m['complete_NB2_PP1_pair']
        self.assertEqual(pair['gross_bits'],4489216)
        self.assertEqual(pair['physical_macros'],4)
        self.assertEqual(pair['existing_capture_bits'],1096)
        for layer in ('M1','M2','M3'):
            self.assertEqual(self.m['local_macro_layer_exclusions'][layer]['remaining_planar_area_um2'],0)

    def test_existing_clock_loads_not_ECC_debt(self):
        clocks=self.m['complete_NB2_PP1_pair']['existing_capture_and4macro_clock_pins']
        self.assertAlmostEqual(clocks['ss']['existing_main_pair_PP_capture_plus4ROM_clock_fF'],524.250448)
        self.assertEqual(clocks['ss']['minimum_46p08fF_load_groups_before_wires_or_other_element_logic'],12)
        self.assertEqual(clocks['ff']['minimum_46p08fF_load_groups_before_wires_or_other_element_logic'],14)
        self.assertEqual(self.m['capture_contract']['ECC_added_cycles'],0)
        self.assertEqual(self.m['capture_contract']['lane_consume_preedge'],3)
        self.assertTrue(self.m['removal_ledger']['shared_valid_owner_backpressure_delivery_ACK_state_not_removed'])

    def test_selector_replacement_displaces_controller_before_logic(self):
        s=self.m['selector_join']
        self.assertEqual(s['compiled'],{'N':4,'NMAX':2048,'LDW':4})
        bounds={x['kind']:x for x in s['state_only_replacement_bounds']}
        staged=bounds['DIG8_staged']
        self.assertAlmostEqual(staged['missing_state_only_mm2'],.0617719608)
        self.assertEqual(staged['displaced_rectangles'][0]['name'],'PROSPECTIVE_COMMON_CONTROLLER_CUT')
        self.assertGreater(staged['displaced_rectangles'][0]['intersect_mm2'],.06177)
        self.assertTrue(staged['reservation_is_replacement_not_addition'])
        self.assertAlmostEqual(staged['source_construction_core_proxy_mm2_at50pct'],1.50883850628)
        self.assertAlmostEqual(staged['construction_displaced_rectangles'][0]['intersect_mm2'],.0826371072)
        self.assertFalse(staged['selected'])
        self.assertTrue(s['filter_serial_quota_still_mandatory'])

    def test_policy_scope_and_no_unbound_area_credit(self):
        self.assertFalse(self.m['policy']['ROM_ECC_required'])
        self.assertTrue(self.m['policy']['SRAM_HBM_link_control_protection_unchanged'])
        self.assertTrue(self.m['policy']['fault_free_golden_exact_required'])
        self.assertEqual(self.m['removal_ledger']['numeric_area_credit_applied_mm2'],0)
        self.assertFalse(self.m['next_gate']['RTL_PR_admitted'])
        data=json.dumps(self.m,indent=2,sort_keys=True)+'\n'
        self.assertEqual(data,(t.BASE/'model.json').read_text())

if __name__=='__main__':
    unittest.main()
