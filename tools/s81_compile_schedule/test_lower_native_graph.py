import copy
import json
from pathlib import Path
import unittest
from lower_native_graph import lower, ROOT


class ActualGraphLoweringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.programs=[json.loads(p.read_text()) for p in sorted((ROOT/'results/rtl/s81_ctrl_20261008/programs').glob('S[0-9][0-9][0-9].json'))]
        cls.result=lower(cls.programs)
        cls.jobs={j['id']:j for j in cls.result['jobs']}

    def test_all2367_actual_operations_remain_covered(self):
        self.assertEqual(len(self.programs),59)
        raw={o['id'] for p in self.programs for o in p['ops']}
        covered=[source for j in self.jobs.values() for source in j['source_ids']]
        self.assertEqual(len(raw),2367)
        self.assertEqual(len(covered),len(set(covered)))
        self.assertEqual(set(covered),raw)
        self.assertEqual(self.result['fused_operations'],704)
        self.assertFalse(self.result['dispatch_eligible'])

    def test_actual_qn_kv_and_hc_quant_fusions(self):
        for L in range(40):
            qn=self.jobs[f'L{L}.attn.q_quant']
            self.assertIn(f'L{L}.attn.q_norm.sumsq',qn['source_ids'])
            self.assertEqual(qn['native_binding']['opcode'],0)
            kv=self.jobs[f'L{L}.attn.kv_rope_qdq']
            self.assertIn(f'L{L}.attn.kv_norm.sumsq',kv['source_ids'])
            self.assertEqual(kv['native_binding']['opcode'],1)
            self.assertIn(f'L{L}.attn.quant',self.jobs[f'L{L}.attn.hc_pre']['source_ids'])

    def test_normalized_projection_and_hbm_tail_are_distinct(self):
        for L in range(40):
            for b in ('attn','ffn'):
                prefix=f'L{L}.{b}.hc.'
                projection=self.jobs[prefix+'fn']
                self.assertEqual(set(projection['source_ids']),{prefix+'fn',prefix+'sumsq',prefix+'rsqrt'})
                self.assertEqual(projection['native_binding']['port'],11)
                tail=self.jobs[prefix+'sinkhorn']
                self.assertIn(prefix+'pre_post',tail['source_ids'])
                self.assertIn(prefix+'raw_allgather',tail['preds'])
                self.assertIsNone(tail['duration_cycles'])

    def test_ffn_projection_reads_actual_updated_h(self):
        for L in range(40):
            store=f'L{L}.attn.hc.h_store_for_hcx'
            self.assertIn(store,self.jobs[f'L{L}.ffn.hc.fn']['preds'])
            self.assertEqual(self.jobs[store]['preds'],[f'L{L}.attn.hc_post'])
            self.assertEqual(self.jobs[store]['native_binding']['opcode'],1)

    def test_missing_native_fusion_target_rejected(self):
        programs=copy.deepcopy(self.programs)
        p=next(p for p in programs if any(o['id']=='L0.attn.q_quant' for o in p['ops']))
        # Rename only the target, leaving alias member q_norm.sumsq intact.
        next(o for o in p['ops'] if o['id']=='L0.attn.q_quant')['id']='L0.attn.unowned_quantizer'
        with self.assertRaisesRegex(ValueError,'fusion target missing'):
            lower(programs)

    def test_injected_dependency_cycle_rejected(self):
        programs=copy.deepcopy(self.programs)
        p=programs[0]
        a=p['ops'][0]; b=p['ops'][1]
        a['preds']=[b['op']];b['preds']=[a['op']]
        with self.assertRaisesRegex(ValueError,'dependency cycle'):
            lower(programs)


if __name__=='__main__':
    unittest.main()
