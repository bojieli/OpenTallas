import json
import unittest

import qwen_rom_stream4_clock_plan as P
import qwen_rom_runtime_pc_context as C


class PeriodicClockPlan(unittest.TestCase):
    def test_literal_parent_scope(self):
        x = P.compose()
        self.assertEqual(x['selected_controller_sha256'], C.PINS['ot_hbm_r14_stream_pc.sv'])
        self.assertEqual(x['clock_ports']['controller_hclk']['period_ps'], 1024)
        self.assertFalse(x['clock_ports']['tagged_clk']['independent_domain'])
        self.assertFalse(x['tagged_storage_charged_to_selected_P0'])
        self.assertEqual(len(x['frontend_fifos']), 3)
        self.assertFalse(x['controller_logic_changed'])

    def test_finite_once_only_area(self):
        x = P.compose()['area']
        self.assertEqual(x['payload_storage_bits'], 128 * (281 * 64 + 289 * 16 + 9 * 64))
        self.assertEqual(x['FIFO_pointer_online_reset_bits'], 24064)
        self.assertEqual(x['existing_CORE_presentation_FF_bits'], 37632)
        self.assertEqual(x['mailbox_bits'], 96)
        self.assertEqual(x['fault_CDC_bits'], 49)
        self.assertTrue(x['existing_rings_replaced_once_not_added_again'])
        self.assertIsNone(x['physical_slot_fit'])

    def test_absolute_timing_cannot_use_average_or_ideal_PHY(self):
        x = P.compose()
        rcd = x['absolute_HBM_timer_budgets']['T_RCD']
        self.assertEqual(rcd['periodic_budget_ps'], 19456)
        self.assertEqual(rcd['budget_margin_ps'], 81)
        self.assertLess(rcd['selected_edges'] * .833333 * 1000, rcd['source_checker_minimum_ps'])
        self.assertIsNone(x['absolute_PHY_arrival_contract']['actual_receiver_arrival_variation_ps'])
        self.assertFalse(x['whole_context_build_admitted'])

    def test_nonzero_service_and_no_token_prediction(self):
        x = P.compose()
        self.assertEqual(x['source_latency_paths']['GO_to_stack_sample']['max_phase_only_ps'], 5120)
        self.assertEqual(x['source_latency_paths']['stream_RD_to_core_consume']['hclk_read_return_edges'], 23)
        self.assertEqual(x['source_latency_paths']['write_to_done']['hclk_write_return_edges'], 17)
        self.assertEqual(x['source_latency_paths']['stream_RD_to_core_consume']['native_CORE_presentation_edges'], 1)
        self.assertIsNone(x['token_composition']['additional_token_latency_ps'])
        self.assertGreater(x['startup']['CORE_writer_HCLK_reader_ready_upper_ps'], 0)
        self.assertFalse(x['constraints']['blanket_async_clock_groups_allowed'])
        self.assertFalse(x['constraints']['binary_counter_or_payload_false_paths_allowed'])

    def test_periodic_cut_exact_stack_no_clock_generator(self):
        text = (P.BASE / 'ot_qwen_stream4_periodic_controller_context.sv').read_text()
        parent = (C.BASE / 'inputs/ot_qwen_hbm_stream4_tagged.sv').read_text()
        a = parent.index('    for (genvar sk = 0; sk < NSTK;')
        b = parent.index('    // ----', a)
        self.assertIn(parent[a:b], text)
        self.assertIn('wire hclk=controller_hclk, rst_n=controller_rst_n;', text)
        self.assertNotIn('tick_q', text)
        self.assertNotIn('reg [31:0] acc', text)

    def test_interface_is_actual_internal_stream(self):
        x = json.loads((P.BASE / 'boundary_interface.json').read_text())
        ports = {p['backend_pin']: p for p in x['frontend_ports']}
        self.assertEqual(ports['d_v']['die_pin'], 'hd_v')
        self.assertEqual(ports['w_data']['die_pin'], 'hw_data')
        self.assertEqual(ports['w_data']['bits'], 32768)
        self.assertNotIn('t_req_v', ports)
        self.assertFalse(x['runtime_replacement_installed'])

    def test_invalid_fifo_depth_refused(self):
        with self.assertRaisesRegex(ValueError, 'power-of-two'):
            P.fifo('bad', 128, 281, 63, 'HCLK', 'CORE', [], 'invalid')

    def test_cold_equal(self):
        frozen = json.loads((P.BASE / 'selected_P0_clock_boundary_r5.json').read_text())
        self.assertEqual(P.compose(), frozen)


if __name__ == '__main__':
    unittest.main()
