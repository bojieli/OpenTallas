"""Adversarial controls for zero-cycle boundary register recutting."""
import copy
import unittest
import tempfile
from pathlib import Path
import gen_core_kit_kv as G
import hr_face_ports as H


def pair(second_clear):
    def flop(q, clear):
        return dict(type='$dffsr', parameters=dict(WIDTH='1', CLK_POLARITY='1', SET_POLARITY='1', CLR_POLARITY='1'),
                    attributes={}, port_directions=dict(D='input', Q='output', CLK='input', SET='input', CLR='input'),
                    connections=dict(D=[2], Q=[q], CLK=[3], SET=['0'], CLR=[clear]))
    return dict(modules=dict(top=dict(ports=dict(d=dict(direction='input', bits=[2]),
                ck=dict(direction='input', bits=[3])), netnames=dict(d=dict(bits=[2], attributes={}),
                ck=dict(bits=[3], attributes={})), cells=dict(a=flop(4,5),b=flop(6,second_clear)))))


class BoundaryControls(unittest.TestCase):
    def test_different_async_clear_must_not_merge(self):
        _, r = H.transform(pair(7), 'top')
        self.assertEqual(r['merged_in'], [])
        self.assertEqual(r['n_multi_in'], 1)

    def test_identical_async_clear_can_merge(self):
        _, r = H.transform(pair(5), 'top')
        self.assertEqual(len(r['merged_in']), 1)
        self.assertEqual(r['n_multi_in'], 0)

    def test_escaped_macro_instance_keeps_reached_master(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'core.v'
            f.write_text('module top;\n  ot_sram_example \\u_slice.g_grp[0].u_rb ( .CK(ck) );\nendmodule\n')
            self.assertIn('ot_sram_example', G.reached_modules([f], 'top').split())

    def test_reset_pins_are_not_data_landing_candidates(self):
        for n in ('rrst_n','wrst_n','u_rx__rrst_n','u_tx__wrst_n'):
            self.assertIsNotNone(H.CLKRST.search(n))


if __name__ == '__main__':
    unittest.main()
