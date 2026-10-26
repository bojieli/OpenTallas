"""KVJ-SMALL (c) 10-17: the completion-fault OR tree on the static-join template (kv_static_kvjf_join.build)."""
import copy
import unittest

import kv_static as K
import kv_static_cfault_join as C
import kv_static_kvjf_join as F


class CfaultJoin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g, cls.bound = F.build()
        cls.ins = {i['name']: i for i in cls.g['instances']}

    def test_every_completion_fault_reaches_the_root_once(self):
        nodes = [i for i in self.g['instances'] if i['module'] == C.TREE[1]]
        self.assertEqual(len(nodes), 43)
        self.assertTrue(all(v is not None for i in nodes for p, v in i['inputs'].items() if p == 'fault_in'))
        self.assertEqual({p for i in nodes for p, v in i['inputs'].items() if v is None}, {'ck', 'rst_n'})

        def leaves(n):
            out = []
            for it in self.ins[n]['inputs']['fault_in']:
                out += [it['instance']] if it['port'] == 'completion_fault' else leaves(it['instance'])
            return out
        lf = leaves('cf_root')
        pcs = [i['name'] for i in self.g['instances'] if i['role'] == 'pc_path']
        self.assertEqual(len(pcs), 128)
        self.assertEqual(sorted(lf), sorted(pcs))                       # each of the 128 exactly once

    def test_neighbour_groups(self):
        # level 1 = the 4 PCs of one group (abutted strip slots), named by the group
        for st in C.STACKS:
            for k, g in enumerate(C.ORDER):
                self.assertEqual([it['instance'] for it in self.ins[f'cf1_{st}_{g}']['inputs']['fault_in']],
                                 [f'pc_{st}_{4 * k + q}' for q in (3, 2, 1, 0)])
        j = [d for d in self.g['die_joins'] if d['consumer'] == 'host.ctrl_completion_fault']
        self.assertEqual(len(j), 1)
        self.assertEqual((j[0]['producer'], j[0]['lo'], j[0]['width']), ('cf_root.fault', 0, 1))
        self.assertIsNone(C.latency(self.g))                            # STAGES compiler-priced, never guessed
        g = copy.deepcopy(self.g)
        for i in g['instances']:
            if i['module'] == C.TREE[1]:
                i['parameters']['STAGES'] = 1
        self.assertEqual(C.latency(g), 4)

    def test_refusals(self):
        with self.assertRaises(ValueError):
            C.cfault_join(self.g)                                       # double join refused
        g, _ = K.template()
        g['instances'] = [i for i in g['instances'] if i['name'] != 'pc_EN_31']
        with self.assertRaises(ValueError):
            C.cfault_join(g)                                            # a missing controller is never skipped


if __name__ == '__main__':
    unittest.main()
