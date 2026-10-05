import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_noECC_mapped_element_join as t

class MappedJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.m=t.build()

    def test_complete_real_hardware_and_capture_counts(self):
        q=self.m['elements']['q'];b=self.m['elements']['bfcolumn']
        self.assertEqual((q['FF_cells'],b['FF_cells']),(28942,91374))
        for e in (q,b):
            self.assertEqual((e['physical_macros'],e['ICG_cells'],e['capture_FF']),(4,8,1088))
            self.assertEqual(e['physical_macro_width_bits'],274)
            self.assertFalse(e['WAKE']['required_local_replica_retention_PASS'])
            self.assertFalse(e['physical_G0'])

    def test_actual_loads_exceed_unbuffered_source(self):
        b=self.m['elements']['bfcolumn']['clock_profiles']['ff']['branches']['g_wake.g_leaf[3].u_cg.u_icg']
        self.assertAlmostEqual(b['actual_pin_cap_fF'],35111.338584,places=5)
        self.assertGreater(b['source_unbuffered_ICG_cap_ratio'],760)
        tree=b['capacitance_only_BUF4_construction']
        self.assertEqual((tree['end_buffers'],tree['parent_buffers']),(191,1))
        self.assertLess(tree['ICG_load_fF'],46.08)

    def test_area_deficit_remedy_preserves_one_candidate(self):
        q=self.m['elements']['q']['area'];b=self.m['elements']['bfcolumn']['area']
        self.assertLess(q['current_reservation_margin_before_CTS_wire_um2'],0)
        self.assertEqual(q['proposed_outline_DBU'],[0,0,510840,151200])
        self.assertAlmostEqual(q['extra_reservation_over_already_priced_frame_um2'],3310.2432)
        self.assertEqual(b['extra_reservation_over_already_priced_frame_um2'],0)
        self.assertTrue(self.m['no_NP_depth_stage_TP_sweep'])

    def test_current_complete_selector_not_old_proxy(self):
        sel=self.m['current_selector']
        self.assertAlmostEqual(sel['slot']['known_service_overlay']['revised_rectangles'][0]['area_mm2'],1.68241961736)
        self.assertEqual(sel['composed_ROM']['added_cycles_per_position'],1278)
        self.assertFalse(self.m['configuration_ROM_ECC_required'])
        self.assertFalse(self.m['physical_admission']['PnR'])

    def test_byte_identical_replay_and_narrow_capture_constraint(self):
        self.assertEqual(json.dumps(self.m,indent=2,sort_keys=True)+'\n',(t.BASE/'model.json').read_text())
        c=self.m['capture_constraints']
        self.assertTrue(c['two_cycle_setup_only_macro_read_to_selected_cap0_cap1'])
        self.assertTrue(c['forbid_multicycle_to_arithmetic_or_valid_metadata'])

if __name__=='__main__':unittest.main()
