import importlib.util
import json
import random
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_prepare', ROOT/'tools/dsrom_native_masked_backend_prepare.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class NativeProtectionPreparation(unittest.TestCase):
    def test_frozen_input_receipts(self):
        self.assertEqual(len(m.inputs()), 12)

    def test_full_backend_and_raw_event_cost(self):
        x = m.build()['raw_component']
        self.assertEqual((x['macros'], x['data_bits'], x['TAG_W']), (256, 16777216, 227))
        self.assertEqual(x['new_state_bits'], 1088 + 4*(4+4*227+60+64) + 5*227)
        self.assertEqual(x['latency'], dict(raw_read_edges=4, macro_write_visible_edges=2,
                                          registered_raw_visibility_event_edges=3))

    def test_sidecar_address_bijection_all_words(self):
        homes = {tuple(m.parity_home(w).values()) for w in range(32768)}
        self.assertEqual(len(homes), 32768)
        self.assertEqual({h[0] for h in homes}, set(range(4)))
        self.assertEqual({h[1] for h in homes}, set(range(8)))
        self.assertEqual({h[2] for h in homes}, set(range(512)))
        self.assertEqual({h[3] for h in homes}, {0, 1})

    def test_sidecar_shared_port_conflict_is_real(self):
        a, b = m.parity_home(0), m.parity_home(2048)
        self.assertEqual((a['bank'], a['pair']), (b['bank'], b['pair']))
        self.assertNotEqual(a['half'], b['half'])
        # Separate halves share one macro: they cannot gain a second write port.
        self.assertIn('not extra concurrent ports', m.build()['SRAM_protection_candidate']['sidecar_layout'])

    def test_strict_address_and_raw_lane_types(self):
        for value in (-1, 32768, True, 1.0, '1'):
            with self.assertRaises(ValueError): m.parity_home(value)
        for half, value in ((2, 1), (True, 1), (0, -1), (0, 1<<32), (0, True)):
            with self.assertRaises(ValueError): m.update_stripe(0, half, value)

    def test_all_single_error_positions_correct_before_merge(self):
        c = m.codec(); old = 0xFEDCBA9876543210
        for bit in range(72):
            for half in (0, 1):
                code, corrected = m.update_stripe(c.encode64(old) ^ (1<<bit), half, 0x3F800000)
                expected = ((old & 0xFFFFFFFF00000000) | 0x3F800000) if half == 0 else ((0x3F800000<<32) | (old & 0xFFFFFFFF))
                self.assertTrue(corrected)
                self.assertEqual(c.decode64(code), (expected, False, False))

    def test_all_double_error_positions_refuse_write(self):
        code = m.codec().encode64(0x0123456789ABCDEF)
        for a in range(72):
            for b in range(a+1, 72):
                with self.assertRaises(ValueError): m.update_stripe(code ^ (1<<a) ^ (1<<b), 0, 7)

    def test_unmasked_sibling_witness_and_random_rmw(self):
        c = m.codec(); rng = random.Random(94)
        for _ in range(100):
            old, new, half = rng.getrandbits(64), rng.getrandbits(32), rng.randrange(2)
            code, corrected = m.update_stripe(c.encode64(old), half, new)
            result, _, ue = c.decode64(code)
            self.assertFalse(corrected or ue)
            self.assertEqual((result >> (32*half)) & 0xFFFFFFFF, new)
            self.assertEqual((result >> (32*(1-half))) & 0xFFFFFFFF,
                             (old >> (32*(1-half))) & 0xFFFFFFFF)

    def test_no_protection_or_timing_transfer(self):
        x = m.build()
        self.assertTrue(x['SRAM_protection_candidate']['raw_Nplus3_ACK_not_protected_publication'])
        self.assertFalse(x['raw_component']['mutable_metadata_protection_installed'])
        for key in ('raw_component_build', 'connected_protected_VM_build', 'physical', 'full_token'):
            self.assertFalse(x['admission'][key])

    def test_additive_source_default_off_and_full_native_masks(self):
        s = (ROOT/'rtl/model_ready_ds_native_vm_20261003/ot_v41_vm_bank4_macro_pipe_masked_visible.sv').read_text()
        self.assertIn('parameter integer MASKED_VISIBLE = 0', s)
        self.assertIn('ot_v41_vm_bank4_macro_pipe #(', s)
        self.assertIn('DEPTH_GROUPS != 16 || AW != 15', s)
        for lane in ('4*c+3', '4*c+2', '4*c+1', '4*c'):
            self.assertIn('32{wr_mask_local_q['+lane+']}', s)
        self.assertIn('wr_ack_v <= ack_valid_q[2]', s)

    def test_retained_native_read_tree_byte_identical(self):
        original = (m.BASE/'inputs/backend.sv').read_text()
        successor = (ROOT/'rtl/model_ready_ds_native_vm_20261003/ot_v41_vm_bank4_macro_pipe_masked_visible.sv').read_text()
        start = '                // Unique 16-bit-local selector flops'
        end = '                always @(posedge clk) begin'
        a = original.split(start, 1)[1].split(end, 1)[0]
        b = successor.split(start, 1)[1].split(end, 1)[0]
        self.assertEqual(a, b)
        for marker in ('        for (p=0;p<4;p=p+1)', '    always @(posedge clk) begin\n        if (!rst_n) begin\n            rd_cmd_v_q'):
            self.assertEqual(original.split(marker, 1)[1], successor.split(marker, 1)[1])

    def test_cold_model_exact(self):
        self.assertEqual(json.loads((m.BASE/'model.json').read_text()), m.build())


if __name__ == '__main__': unittest.main()
