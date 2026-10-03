import json
from pathlib import Path
import tempfile
import unittest
import hbm_w6_contextual_plan as P
import hbm_w6_physical_source_adapter as A

class PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=json.loads((P.BASE/'selected_plan.json').read_text())
    def test_exact_clocks_distinct_from_bench(self):
        c=self.plan['clocks'];self.assertEqual(c['period_ps'],1000/1.2)
        self.assertEqual((c['SS_setup_uncertainty_ps'],c['FF_hold_uncertainty_ps']),(60,25))
        self.assertEqual(c['functional_bench_period_ps'],10000)
        self.assertFalse(c['functional_bench_proves_target_clock'])
    def test_all32_fullwidth_and_protected_storage(self):
        self.assertEqual(self.plan['parameter']['replicas'],32)
        self.assertEqual(self.plan['state']['full32_protected_RTL_bits'],4608)
        self.assertEqual(self.plan['source_depth']['identity_match_ports'],7)
    def test_serial_source_depth_not_age_pipeline(self):
        d=self.plan['source_depth'];self.assertEqual(d['decode_syndrome_longest_serial_XOR'],36)
        self.assertEqual(d['encode_check_longest_serial_XOR'],35)
        self.assertFalse(d['reduction_tree_guaranteed_by_source'])
        self.assertTrue(self.plan['clocks']['boundary_age_is_not_combinational_pipeline'])
    def test_single_selected_route_no_newlayers(self):
        r=self.plan['selected_route'];self.assertEqual(r['alternatives'],0)
        self.assertEqual(r['signal_layers'],['M2','M3','M4','M5'])
        self.assertFalse(r['additional_layers_allowed'])
        self.assertEqual(r['backend_macro_count_RF'],4096)
    def test_actual_inventory_missing_failsclosed(self):
        with self.assertRaises(ValueError):P.validate_inventory(self.plan,{})
        self.assertFalse(self.plan['launch_ready'])
    def test_physical_clock_cost_not_already_qualified(self):
        self.assertGreater(self.plan['slot']['full32_clock_pin_load_fF'],0)
        self.assertTrue(self.plan['slot']['CTS_reset_hold_repair_and_pin_escape_area_not_yet_charged'])
        self.assertFalse(self.plan['physical_qualified'])
    def test_literal_frontend_and_full32_source_exact(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'source';r=A.prepare(out)
            expected=json.loads((P.BASE/'prepared_source/source_representation.json').read_text())
            self.assertEqual(r,expected)
            top=(out/'w6_full32_context.sv').read_text()
            self.assertIn('sm<32',top);self.assertIn('parameter bit ENABLE=0',top)
            for p in P.portbook():self.assertIn('.'+p['name']+'(',top)
    def test_source_library_hashes(self):
        for p,h in self.plan['sourcepins'].items():self.assertEqual(P.sha(P.ROOT/p),h)
    def test_no_guess_runtime_or_memory_caps(self):
        r=self.plan['resources']
        for n in ('build_wall_limit','CPU_time_limit','FSIZE_limit','AS_limit','memory_hard_limit','swap_hard_limit'):self.assertIsNone(r[n])
        self.assertFalse(r['PVE2_PVE3'])
    def test_whole_caller_not_required_for_local_timing(self):
        i=self.plan['Ampere_inventory_contract']
        self.assertTrue(i['excludes_fullbridge_functional_requirement'])
        self.assertTrue(i['installed_allcopy_producer_not_required_for_local_timing'])

if __name__=='__main__':unittest.main()
