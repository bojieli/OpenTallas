"""Q-KVJOIN: the existing boot dispatcher binds every width-exact core-domain cfg input; the join stays unemittable."""
import unittest

import kv_static as K
import kv_static_boot_join as B


class BootJoin(unittest.TestCase):
    def test_core_cfg_bound_and_still_refused(self):
        g, _ = K.template()
        bound = B.boot_join(g)
        self.assertEqual(len(bound), 3 * 3 + 32 * 3)
        ins = {i['name']: i for i in g['instances']}
        self.assertEqual(ins['lcal_EN_7']['inputs']['cfg_we'], [dict(instance='boot', port='landing_we', lo=31, width=1)])
        self.assertEqual(ins['lcal_WS_0']['inputs']['cfg_we'][0]['lo'], 0)
        for n in ('layer_programme', 'wprg', 'ownership'):
            self.assertTrue(all(ins[n]['inputs'][p] for p in ('cfg_we', 'cfg_addr', 'cfg_data')))
        self.assertTrue(all(v is None for v in ins['boot']['inputs'].values()))
        self.assertIsNone(ins['fcal_WS_0']['inputs']['cfg_we'])      # HBM domain: needs boot_cdc successor
        with self.assertRaises(ValueError):
            K.compile_graph(g)                                        # no programme image: never emittable

    def test_double_join_refused(self):
        g, _ = K.template()
        B.boot_join(g)
        with self.assertRaises(ValueError):
            B.boot_join(g)


if __name__ == '__main__':
    unittest.main()
