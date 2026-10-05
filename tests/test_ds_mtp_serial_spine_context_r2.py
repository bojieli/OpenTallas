import importlib.util
import json
import unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'tools/ds_mtp_serial_spine_context_r2.py'
s=importlib.util.spec_from_file_location('spine_r2',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class CurrentSpine(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.x=m.build()

    def test_current_owner_not_prior_request(self):
        x=self.x
        self.assertEqual(x['authoritative_enrollment'],'a9691644a')
        self.assertEqual((x['requested_slot']['width_um'],x['requested_slot']['height_um']),(128,191.70))
        self.assertEqual(x['kernel']['protected_FF_sinks'],2016)
        prior=json.loads((m.BASE/'inputs/prior_r1_reply.json').read_text())
        self.assertEqual(prior['request']['height_um'],184.14)
        self.assertEqual(prior['local_clock']['protected_FF_sinks'],1944)

    def test_caller_replaces_without_double_leaf_charge(self):
        x=self.x['kernel']
        self.assertEqual((x['leaf_raw'],x['caller_raw'],x['total_raw']),(614,102,716))
        self.assertEqual(x['total_protected_words']*72,2016)
        self.assertEqual((x['raw_state_delta'],x['protected_state_delta']),(29,72))
        self.assertEqual(x['caller_protected_words'],4)

    def test_full_scalar_width_cost_not_FF_only(self):
        x=self.x['scalar_source']
        self.assertEqual((x['K'],x['old_IW'],x['new_IW']),(512,16,21))
        self.assertEqual(x['raw_after']-x['raw_before'],7690)
        self.assertAlmostEqual(x['width_only_50pct_mm2'],.03135116988)
        self.assertEqual(x['width_only_cell_counts']['NAND2x1_ASAP7_75t_R'],99765)
        self.assertFalse(x['clamp_or_BF16_substitution'])
        self.assertFalse(x['zero_added_edges_measured'])

    def test_mandatory_not_performance_lever(self):
        self.assertTrue(self.x['mandatory_correctness'])
        self.assertFalse(self.x['one_percent_performance_filter_applies'])

    def test_slot_area_exact_and_unreserved(self):
        x=self.x['requested_slot']
        self.assertAlmostEqual(x['rectangle_mm2'],.0245376)
        self.assertAlmostEqual(x['spare_geometric_um2'],8.6454)
        self.assertAlmostEqual(x['leaf_plus_scalar_width_only_gross50pct_mm2'],.05588012448)
        self.assertIsNone(x['actual_reserved_rectangle'])
        self.assertFalse(x['fit_qualified'])
        self.assertEqual(x['credits_for_old_state_or_slot_embedding'],0)

    def test_clock_and_reset_cover_every_sink_exactly(self):
        x=self.x['local_clock_reset']
        self.assertEqual(x['buffer_counts'],[252,32,4,1])
        self.assertEqual(x['total_clock_reset_buffers'],578)
        for name in ['CLK_levels','RESETN_levels']:
            ids=[i for g in x[name][0] for i in range(g['first'],g['stop'])]
            self.assertEqual(ids,list(range(2016)))
        self.assertEqual(x['difference_to_old558_buffers'],20)
        self.assertEqual(x['add_clock_tree_charge_again'],0)

    def test_actual_corner_caps_and_unchanged_uncertainties(self):
        x=self.x['local_clock_reset']
        self.assertAlmostEqual(x['SS_CLK_pin_fF'],874.907712)
        self.assertAlmostEqual(x['FF_CLK_pin_fF'],1014.354432)
        self.assertEqual((x['SS_setup_uncertainty_ps'],x['FF_hold_uncertainty_ps']),(60,25))
        self.assertFalse(x['equal_depth_skew_credit'])
        self.assertFalse(x['loaded_SSFF'])
        self.assertGreater(x['scalar_added_CLK_FF_fF'],x['FF_CLK_pin_fF'])

    def test_two_named_producer_cuts_not_single_free_corridor(self):
        x=self.x['signal_channels']
        self.assertEqual(x['leaf_signals'],636)
        self.assertEqual(sum(x['producer_fields'].values()),52)
        self.assertEqual(x['producer_cut_instances'],2)
        self.assertEqual(x['if_all_share_one_cut_signals'],740)
        self.assertEqual(x['each_producer_floor_um_at48nm'],2.496)
        self.assertTrue(x['sum_not_selected_single_corridor'])
        self.assertIsNone(x['legal_tracks_after_PG_via_clock'])

    def test_actual_replica_census_no_NTP_inference(self):
        x=self.x['replica_census']
        self.assertEqual(x['actual_cores_per_source_die_wrapper'],1)
        self.assertEqual(x['one_kernel_per_actual_enrolled_core'],1)
        self.assertEqual(x['enrolled_successor_instances'],0)
        self.assertTrue(x['N_TP_is_link_replication_not_core_count'])
        self.assertTrue(x['actual_fleet_count_unproven'])

    def test_default_runtime_NSLOT1_not_installed8(self):
        self.assertEqual(self.x['kernel']['source_NSLOT_default'],1)
        self.assertFalse(self.x['kernel']['source_installed'])
        self.assertFalse(self.x['kernel']['default_enable'])

    def test_shared_CDC_no_duplicate_component_or_zero_cost(self):
        x=self.x['prospective_CDC']
        self.assertEqual(x['state_bits'],2936)
        for e in x['edges']:
            self.assertEqual((e['W'],e['reverse_W'],e['DEPTH'],e['HOLD']),(121,56,4,2))
            self.assertEqual(e['extra_TOKX_AMAX_FIFO_count'],0)
        self.assertFalse(x['hardware_closure'])
        self.assertFalse(x['phase_or_multicycle_exceptions'])

    def test_tail_and_holder_not_II2_full_draft(self):
        self.assertEqual(self.x['scalar_source']['source_last_input_to_result_edges'],1026)
        self.assertEqual(self.x['latency']['producer_finish_to_first_leaf_query_min_edges'],1)
        self.assertTrue(self.x['signal_channels']['no_full_selector_II2_claim'])
        self.assertIsNone(self.x['latency']['full_token_or_MTP_rate_claim'])

    def test_guarded_launch_not_admission(self):
        self.assertIn('--macro-track-gate',self.x['physical_launch_policy'])
        self.assertIn('ot_mts::place/assert',self.x['physical_launch_policy'])
        self.assertFalse(self.x['admission']['physical_G0'])
        self.assertEqual(self.x['new_jobs'],0)
        self.assertTrue(self.x['global_Z3_unchanged'])

    def test_model_and_pins_exact(self):
        self.assertEqual(self.x,json.loads((m.BASE/'model.json').read_text()))
        self.assertEqual(len(m.checked()),11)

if __name__=='__main__': unittest.main()
