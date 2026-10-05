"""The terminal continuation cannot promote allocation or cached targets."""
import copy
import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('continuation',ROOT/'tools/qwen_rom_dspark_np4_continue.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class ContinuationTests(unittest.TestCase):
    def record(self):
        return dict(schema='opentallas.qwen-dspark-oracle-gpu.v1',mode='first_block_inputs',
                    tp=4,groups=6144,su_width=1024,kv_format='fp8',status='actual_draft_inputs_ready',position=8187,anchor=15,
                    feature_shape=[8187,20480],feature_layers=[1,9,17,25,33],
                    captured_positions_per_layer=[8187]*5,target_feature_sha256='producer-digest',
                    step1_draft=dict(start=8187,anchor=15,S=3,kv='fp8',draft_tokens=[20,13,15]),
                    step1=dict(P=8187,positions=[8187,8188,8189,8190],block_tokens=[15,20,13,15]))

    def test_completed_requires_captures_and_actual_draft_identity(self):
        self.assertEqual(mod.completed(self.record()),[15,20,13,15])
        for key,value in (('status','producing_features'),('captured_positions_per_layer',[8187,0,0,0,0]),('target_feature_sha256',None)):
            record=self.record();record[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):mod.completed(record)
        record=self.record();record['step1']['block_tokens']=[15,10952,18065,1269]
        with self.assertRaises(ValueError):mod.completed(record)

    def test_exact_cache_reuse_and_only_missing_row_extraction(self):
        caches=[('A',dict(per_position={'8187':{'token':15},'8188':{'token':20}})),
                ('B',dict(per_position={'8189':{'token':13}}))]
        chosen,missing=mod.choose_slots([15,20,13,15],8187,caches)
        self.assertEqual(chosen,['A','A','B',None]);self.assertEqual(missing,[15])

    def test_pending_history_cannot_be_replaced(self):
        with self.assertRaises(ValueError):mod.choose_slots([24,20,13,15],8187,[('A',dict(per_position={'8187':{'token':15}}))])

if __name__=='__main__':unittest.main()
