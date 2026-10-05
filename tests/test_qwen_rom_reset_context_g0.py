import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from qwen_rom_reset_context_g0 import OUT, build, census, load, startup
from uarch_model_qwen_reset import baseline, qwen_rom_reset_context_price


class CensusTests(unittest.TestCase):
    def test_hierarchy_replicates_bits_and_preserves_reset_distinction(self):
        ff = dict(type='$adff', parameters={'WIDTH': '1000'},
                  connections={'CLK': [1], 'ARST': [2], 'D': list(range(3,11)), 'Q': list(range(11,19))}, attributes={})
        child = dict(attributes={}, ports={'clk': {'bits': [1]}, 'rst_n': {'bits': [2]}}, cells={'ff': ff})
        root = dict(attributes={'top': '1'}, ports={'clk': {'bits': [21]}, 'rst_n': {'bits': [22]}}, cells={})
        for name in ['a', 'b']:
            root['cells'][name] = dict(type='child', connections={'clk':[21], 'rst_n':[22]}, attributes={})
        got = census({'modules': {'top': root, 'child': child}})
        self.assertEqual(got['totals']['clock_bits'], 16)
        self.assertEqual(got['totals']['async_reset_bits'], 16)
        self.assertEqual({r['clock'] for r in got['registers']}, {'top/clk[0]'})
        net = {'modules': {'top': root, 'child': copy.deepcopy(child)}}
        net['modules']['child']['cells']['ff']['type'] = '$dff'
        del net['modules']['child']['cells']['ff']['connections']['ARST']
        self.assertEqual(census(net)['totals']['async_reset_bits'], 0)

    def test_unpriced_sequential_cells_fail_closed(self):
        net = {'modules': {'top': dict(attributes={'top':'1'}, ports={}, cells={
            'latch': dict(type='$dlatch', connections={}, attributes={})})}}
        with self.assertRaisesRegex(ValueError, 'Unaccounted sequential'):
            census(net)


class ContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = load(OUT / 'model-r5.json')

    def test_complete_source_census_is_more_than_extracted_cone(self):
        price = self.model['price']
        self.assertGreater(price['source_tile_clock_bits'], 3172)
        self.assertGreater(price['source_tile_async_reset_bits'], 90)
        self.assertEqual(price['remaining_tile_async_reset_bits'], price['source_tile_async_reset_bits'] - 90)
        self.assertEqual(self.model['tile']['primitives']['BUFx4_ASAP7_75t_R'], 76)
        self.assertEqual(self.model['die_bench_hardware']['primitives']['ICGx1_ASAP7_75t_R'], 1)

    def test_startup_nba_edge_and_early_pulse_loss(self):
        trace = startup()
        self.assertEqual([r['reset_before'] for r in trace[:3]], [0, 0, 1])
        self.assertEqual(next(r['edge'] for r in trace if r['producer_read_after']), 5)
        self.assertFalse(any(r['producer_read_after'] for r in startup(first_go_edge=2)))
        self.assertEqual(next(r['edge'] for r in startup(ireg=0) if r['producer_read_after']), 4)

    def test_area_and_nominal_loads_no_distribution_zero_fill(self):
        p = self.model['price']
        self.assertAlmostEqual(p['root_cell_area_um2_per_tile'], .84564)
        self.assertAlmostEqual(p['root_cell_area_mm2_per_die'], .84564 * 1536 / 1e6)
        self.assertEqual(p['upstream_external_reset_added_nominal_pins_per_die'], 3072)
        self.assertAlmostEqual(p['source_pin_loads']['ff']['added_clock_cap_fF'], 2 * .503152)
        self.assertIsNone(p['complete_distribution_and_CTS_area_um2_per_tile'])
        self.assertIsNone(p['source_pin_loads']['ff']['stage2_INV_other_tile_reset_load_fF'])

    def test_no_clock_hold_or_implementation_admission(self):
        p = self.model['price']
        self.assertEqual((p['setup_uncertainty_ps'], p['hold_uncertainty_ps']), (60,25))
        self.assertFalse(p['hold_relaxed'])
        self.assertFalse(p['physical_complete'])
        self.assertIsNone(p['startup_serial_domain_cycles'])
        for k in ['root_RTL','new_mapping','tile_PR','hardware_adoption']:
            self.assertFalse(self.model['admission'][k])

    def test_replica_composition_not_double_counted(self):
        p = self.model['price']
        self.assertEqual(p['source_die_plus_all_tile_clock_bits'],
            p['source_die_core_clock_bits'] + 1536 * p['source_tile_clock_bits'])
        self.assertEqual(p['steady_token_added_cycles'], 0)
        self.assertEqual(p['per_layer_added_cycles'], 0)
        self.assertFalse(p['adoption_1percent_gate'])

    def test_root_recovery_removal_kept_for_both_corners(self):
        for corner in ['ss', 'ff']:
            arcs = self.model['root_RESETN_constraint_grid_envelopes'][corner]
            self.assertIn('recovery_rising', {a['type'] for a in arcs})
            self.assertIn('removal_rising', {a['type'] for a in arcs})
            self.assertTrue(all(a['min_ps'] <= a['max_ps'] for a in arcs))

    def test_external_window_is_conditional_and_preserves_uncertainty(self):
        window = self.model['conditional_external_release_window']
        self.assertAlmostEqual(window['deassert_min_ps_after_previous_root_posedge'], 92.5064)
        self.assertAlmostEqual(window['deassert_max_ps_after_previous_root_posedge'], 791.5025333333333)
        self.assertEqual(window['reset_low_pulse_min_ps'], 321.045)

    def test_persistent_kv_service_slot_remains_blocked(self):
        kv = self.model['persistent_KV']
        self.assertEqual(kv['resources']['assembly_entries_per_stack'], 1024)
        self.assertEqual(kv['slot']['service_macro_count_per_stack'], 96)
        self.assertAlmostEqual(kv['slot']['service_macro_area_mm2_per_stack'], .976969184)
        self.assertIsNone(kv['slot']['current_slot_fit'])
        self.assertIsNone(kv['slot']['current_channel_capacity'])
        self.assertEqual(kv['slot']['fill_boundary_tracks'], 1048)
        self.assertFalse(kv['latency']['admitted_latency_or_rate'])

    def test_fill_wrapper_loads_counted_once_without_payload_reset(self):
        p = self.model['price']
        self.assertEqual(p['source_tile_clock_bits'], p['source_logic_tile_clock_bits'] + 1032)
        self.assertEqual(p['source_tile_async_reset_bits'], p['source_logic_tile_async_reset_bits'] + 1)
        self.assertEqual(self.model['persistent_KV']['fill_capture']['asynchronous_reset_bits'], 1)
        self.assertEqual(self.model['persistent_KV']['latency']['incremental_full_reload_bytes'], 0)
        self.assertEqual(self.model['persistent_KV']['latency']['existing_read_bytes_charged_once'], 150994944)

    def test_parent_literal_milestone_not_timing_or_lowered_window_join(self):
        p = self.model['parent_milestone']
        self.assertEqual(p['literal_review']['parent_final_focused_tests_passed'], 91)
        self.assertFalse(p['hardware_qualification'])
        self.assertFalse(p['r33_lowered_window_join_complete'])
        self.assertFalse(p['provider_additive_manifest']['hardware_qualified'])

    def test_extension_is_explicit_and_does_not_modify_baseline(self):
        self.assertFalse(hasattr(baseline, 'qwen_rom_reset_context_price'))
        self.assertEqual(self.model['selected_model_extension'], 'tools/uarch_model_qwen_reset.py')
        with self.assertRaisesRegex(ValueError, 'Explicit qwen-reset'):
            build(model_extension=None)
        price = qwen_rom_reset_context_price(self.model['tile']['totals'],
            self.model['die_bench_hardware']['totals'],
            load(OUT / 'inputs/reset_producer_price_inputs_r1.json'))
        self.assertEqual(price, self.model['price'])


if __name__ == '__main__':
    unittest.main()
