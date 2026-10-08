import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('hbrom_counterfactual', Path(__file__).parents[1]/'tools/hbrom_counterfactual.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def jobs():
    base = dict(kind='weight', parent='L0.ffn.experts_gu',format='fp4',k=5120,
                activation_bytes=10240,rows=2304,macs=2304*5120,weight_bytes=6266880,result_bytes=9216)
    return [dict(base,id='a',deps=['router']),dict(base,id='b',deps=['a']),
            dict(id='done',deps=['b'],kind='join')]


class CounterfactualTests(unittest.TestCase):
    def test_preserves_segments_and_rewires_completion(self):
        out = c.concat_graph(jobs())
        fused = next(n for n in out if n.get('segments'))
        self.assertEqual(len(fused['segments']),2)
        self.assertEqual(fused['deps'],['router'])
        self.assertEqual(fused['rows'],4608)
        self.assertEqual(next(n for n in out if n['id']=='done')['deps'],[fused['id']])
        self.assertEqual(fused['activation_bytes'],10240)

    def test_incompatible_operand_cannot_merge(self):
        nodes=jobs();nodes[1]['activation_bytes']=4608
        with self.assertRaises(ValueError):c.concat_graph(nodes)

    def test_override_always_restored(self):
        original=c.M.weight_service
        inputs=dict(compute=dict(private_tile_area_mm2=1.,area_mm2=1.))
        with patch.object(c.M,'evaluate',side_effect=RuntimeError('test failure')):
            with self.assertRaises(RuntimeError):c.evaluate(inputs,{},'operand_residency')
        self.assertIs(c.M.weight_service,original)

if __name__=='__main__':unittest.main()
