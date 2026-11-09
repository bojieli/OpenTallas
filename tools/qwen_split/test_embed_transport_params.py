from types import SimpleNamespace as NS
import unittest

import embed_transport_params as ET

PORTS = {('embed_prov', 'embed_code_re'): 'code_re', ('embed_prov', 'embed_code_addr'): 'code_addr',
         ('native59', 'emb_code_q'): 'code_q', ('embed_prov', 'embed_scale_re'): 'scale_re',
         ('embed_prov', 'embed_scale_addr'): 'scale_addr', ('native59', 'emb_scale_q'): 'scale_q'}


def ctx(**over):
    depth = dict(code_re=4, code_addr=4, code_q=7, scale_re=6, scale_addr=5, scale_q=6)
    depth.update(over)
    return NS(depth=lambda path, port: {b: v for b, v in enumerate(depth[PORTS[(path, port)]] if isinstance(depth[PORTS[(path, port)]], list)
                                                                 else [depth[PORTS[(path, port)]]] * 4)})


class EmbedTransport(unittest.TestCase):
    def test_bound_depths_give_the_measured_offsets(self):
        params, record = ET.regen(ctx())
        self.assertEqual(params['native59'], dict(EMB_RT_CODE=11, EMB_RT_SCALE=12))
        self.assertEqual(record['dr_o_added_edges'], 11)

    def test_values_follow_the_plan_no_hand_number(self):
        self.assertEqual(ET.regen(ctx(code_re=3, code_addr=3, code_q=5, scale_re=2, scale_addr=2))[0]['native59'], dict(EMB_RT_CODE=8, EMB_RT_SCALE=8))

    def test_address_later_than_enable_is_a_tear(self):
        with self.assertRaisesRegex(ValueError, 'read tear'):
            ET.regen(ctx(scale_addr=7))

    def test_bits_of_one_port_must_land_together(self):
        with self.assertRaisesRegex(ValueError, 'one depth per port'):
            ET.regen(ctx(code_q=[7, 8, 7, 7]))


if __name__ == '__main__':
    unittest.main()
