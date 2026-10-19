"""KVJ-F 10-17: ownership producers, boot-loaded die cfg and the landing -> V port check on the static-join template."""
import copy
import unittest

import kv_static as K
import kv_static_boot_join as B
import kv_static_kvjf_join as F


class KvjfJoin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g, cls.bound = F.build()
        cls.ins = {i['name']: i for i in cls.g['instances']}

    def test_ownership_inputs_have_actual_producers(self):
        own, obs, d2d = self.ins['ownership'], self.ins['own_obs'], self.ins['d2d']
        self.assertEqual([p for p, v in own['inputs'].items() if v is None], ['ck', 'rst_n'])
        for p in ('go', 'host_quiet', 'upstream_quiet'):
            self.assertEqual(own['inputs'][p], [dict(instance='own_obs', port=p, lo=0, width=1)])
        for p in ('kv_active_local', 'kv_drained_local', 'kv_flush_local'):
            self.assertEqual(d2d['inputs'][p], [dict(instance='own_obs', port=p, lo=0, width=1)])
        self.assertEqual(obs['inputs']['es_sv'][0], dict(instance='wrn', port='es', lo=288 * 3 + 287, width=1))
        self.assertEqual(obs['inputs']['es_wv'][-1], dict(instance='wrn', port='es', lo=0, width=1))
        self.assertEqual(obs['inputs']['group_fault'], own['inputs']['group_fault'])
        self.assertEqual({k for k, v in obs['inputs'].items() if v is None}, {'ck', 'rst_n', 'host_launch_quiet', 'host_upstream_quiet'})
        dj = {j['consumer'] for j in self.g['die_joins']}
        self.assertTrue({'own_obs.host_launch_quiet', 'own_obs.host_upstream_quiet'} <= dj)
        self.assertEqual(self.ins['drain_EN_7']['inputs']['upstream_quiet'], [dict(instance='phase_EN_7', port='idle_core', lo=0, width=1)])
        self.assertIsNone(obs['parameters']['QUIET_WIN'])                 # compiler-priced, never guessed

    def test_ectl_cfg_boot_loaded_not_strapped(self):
        for s, st in enumerate(F.STACKS):
            for g in range(8):
                self.assertEqual(self.ins[f'ectl_a_{st}_{g}']['inputs']['cfg'],
                                 [dict(instance='diecfg', port='ectl_a_cfg', lo=5 * (8 * s + g), width=5)])
        self.assertFalse(any('strap' in it for i in self.g['instances'] for v in i['inputs'].values() if v
                             for it in v if i['role'] == 'ectla'))
        self.assertEqual(self.ins['boot']['inputs']['diecfg_sealed'], [dict(instance='diecfg', port='sealed', lo=0, width=1)])
        self.assertEqual(self.ins['diecfg']['inputs']['cfg_data'], [dict(instance='boot', port='diecfg_data', lo=0, width=64)])
        rst = [j for j in self.g['die_joins'] if j['consumer'].startswith('rst_region[')]
        self.assertEqual(len(rst), B.DIE_CFG_NRST)
        self.assertEqual(sum(1 for j in self.g['die_joins'] if j['consumer'].startswith('ectl_')), 64)

    def test_die_cfg_image(self):
        a = [(g << 2) | s for s in range(4) for g in range(8)]     # the template's identity values, now boot-loaded
        w = F.die_cfg_image(a, a, a, list(range(B.DIE_CFG_NRST)), 1)
        self.assertEqual(len(w), 32 + B.DIE_CFG_NRST + 2)      # + the capability word (RTL-BUILD-KV/FAULT P8)
        self.assertEqual(w[-1], 0x514b564443464731)
        self.assertEqual(w[-2], 1)
        with self.assertRaises(ValueError):
            F.die_cfg_image(a, a, a, [0], 2)
        self.assertEqual(w[9], a[9] | (a[9] << 5) | (a[9] << 10))
        with self.assertRaises(ValueError):
            F.die_cfg_image(a, a, a[:31], [0], 1)

    def test_vport_join_checked(self):
        self.assertEqual(F.vport_join_check(self.g), 32)
        g = copy.deepcopy(self.g)                                     # mutant: port sides swapped
        ins = {i['name']: i for i in g['instances']}
        v = ins['vport_ES_2']
        v['inputs']['in0_d'], v['inputs']['in1_d'] = v['inputs']['in1_d'], v['inputs']['in0_d']
        with self.assertRaises(ValueError):
            F.vport_join_check(g)
        g = copy.deepcopy(self.g)                                     # mutant: the unmeasured RT 8
        {i['name']: i for i in g['instances']}['vport_WN_1']['parameters']['RT'] = 8
        with self.assertRaises(ValueError):
            F.vport_join_check(g)

    def test_refusals(self):
        g, _ = K.template()
        B.boot_join(g)
        {i['name']: i for i in g['instances']}['boot']['parameters']['DIECFG'] = 0
        with self.assertRaises(ValueError):
            F.die_cfg_join(g)                                         # pre-KVJ-F dispatcher has no target 10
        with self.assertRaises(ValueError):
            F.ownership_join(self.g)                                  # double join refused
        with self.assertRaises(ValueError):
            K.compile_graph(self.g)                                   # still no programme image: never emittable


if __name__ == '__main__':
    unittest.main()
