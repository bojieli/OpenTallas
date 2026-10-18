"""Q-KVJOIN: the existing boot dispatcher binds every width-exact core-domain cfg input; the join stays unemittable."""
import unittest

import kv_static as K
import kv_static_boot_join as B


class BootJoin(unittest.TestCase):
    def test_core_cfg_bound_and_still_refused(self):
        g, _ = K.template()
        bound = B.boot_join(g)
        self.assertEqual(len(bound), 3 * 3 + 32 * 3 + 4 + 6)      # + link end 4 (LINKCFG 11) + C3 root/join4_cal 6 (ESCFG 12/13)
        for n in ('fanr', 'emb_join'):
            self.assertEqual({i['name']: i for i in g['instances']}[n]['inputs']['cfg_data'],
                             [dict(instance='boot', port='es_cfg_data', lo=0, width=64)])
        self.assertEqual(ins_ := {i['name']: i for i in g['instances']}['d2d']['inputs']['cfg_addr'],
                         [dict(instance='boot', port='link_cfg_addr', lo=0, width=6)])
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

    def test_hbm_cfg_through_actual_boot_cdcs(self):
        g, _ = K.template()
        B.boot_join(g)
        bound = B.boot_cdc_join(g)
        ins = {i['name']: i for i in g['instances']}
        self.assertEqual(sum(1 for i in g['instances'] if i['module'] == 'qkd_static_kv_boot_cdc'), 160)
        self.assertEqual(len(bound), 32 * (4 + 3) + 128 * (4 + 4) + 3 + 2)
        self.assertEqual(ins['fcal_EN_7']['inputs']['cfg_addr'], [dict(instance='bcdc_f_EN_7', port='sink_addr', lo=0, width=8)])
        self.assertEqual(ins['bcdc_f_EN_7']['inputs']['cfg_last'], [dict(instance='boot', port='front_last', lo=31, width=1)])
        self.assertEqual(ins['bcdc_c_WN_3']['inputs']['cfg_we'], [dict(instance='boot', port='controller_we', lo=35, width=1)])
        self.assertEqual(ins['pc_WN_3']['inputs']['cal_seal'], [dict(instance='bcdc_c_WN_3', port='sink_seal', lo=0, width=1)])
        self.assertEqual(ins['pc_WN_3']['inputs']['cal_cfg_addr'][0]['width'], 5)
        obs = ins['boot_obs']['inputs']['applied_hbm']                  # MSB first: [159] = PC 127, [0] = front group 0
        self.assertEqual((obs[0]['instance'], obs[-1]['instance'], obs[-33]['instance']), ('bcdc_c_EN_31', 'bcdc_f_WS_0', 'bcdc_c_WS_0'))
        self.assertEqual(ins['boot']['inputs']['sink_applied'], [dict(instance='boot_obs', port='applied_core', lo=0, width=160)])
        for i in g['instances']:
            if i['role'] in ('front_calendar', 'pc_path'):
                for p in ('cfg_we', 'cfg_addr', 'cfg_data', 'cal_cfg_we', 'cal_cfg_addr', 'cal_cfg_data', 'cal_seal'):
                    if p in i['inputs']:
                        self.assertIsNotNone(i['inputs'][p], f'{i["name"]}.{p}')
        with self.assertRaises(ValueError):
            B.boot_cdc_join(g)                                        # double join refused
        with self.assertRaises(ValueError):
            K.compile_graph(g)

    def test_cdc_join_needs_boot(self):
        g, _ = K.template()
        with self.assertRaises(ValueError):
            B.boot_cdc_join(g)

    def test_host_admission_join(self):
        g, _ = K.template()
        B.boot_join(g)
        B.boot_cdc_join(g)
        bound, joins = B.host_admission_join(g)
        ins = {i['name']: i for i in g['instances']}
        self.assertEqual(ins['boot']['inputs']['execution_active'], [dict(instance='d2d', port='execution_active', lo=0, width=1)])
        self.assertEqual([x['instance'] for x in ins['boot']['inputs']['local_configured']], ['ownership', 'wprg', 'layer_programme'])
        self.assertEqual({j['consumer'] for j in joins if j['consumer'].startswith('boot.')},
                         {f'boot.{p}' for p, v in ins['boot']['inputs'].items()
                          if v is None and p not in ('ck', 'rst_n', 'diecfg_sealed', 'diecfg_fault')})   # KVJ-F die_cfg_join
        self.assertIn(dict(consumer='host.static_setup_ready', producer='boot.setup_ready', width=1,
                           host_master=B.HOST[0] + ':' + B.HOST[1]), joins)

    def test_pt_host_root_refused(self):                               # mutant: the pre-swap HOST root has no boot ports
        g, _ = K.template()
        B.boot_join(g)
        with self.assertRaises(ValueError):
            B.host_admission_join(g, host=('rtl/qwen_sys/split_20261014/qkd_host_root_pt.sv', 'qkd_host_root_pt'))


if __name__ == '__main__':
    unittest.main()
