"""Producer plans never need a GPU; execution fails closed while a GPU owner lives."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

class ProducerPlanTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('np4_producer',ROOT/'tools/qwen_rom_dspark_np4_producer.py')
        self.mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.mod)
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.tokens=self.root/'tokens.txt';self.tokens.write_text('20 15 24 13 15 24')
        for layer in range(34):
            for rank in range(4):
                d=self.root/f'L{layer}-d{rank}';d.mkdir();(d/f'layer{layer}_rom.json').write_text('{}')
        self.draft=self.root/'draft';self.draft.mkdir()
        (self.draft/'config.json').write_text(json.dumps(dict(target_layer_ids=[1,9,17,25,33])))
        (self.draft/'model.safetensors').write_bytes(b'fixture-not-executed')
        self.snapshot=self.root/'snapshot';self.snapshot.mkdir();(self.snapshot/'config.json').write_text('{}')
        self.embedding=self.root/'embedding.npz';self.embedding.write_bytes(b'fixture-not-executed')
        self.a=argparse.Namespace(tokens=self.tokens,tokens_sha256=self.mod.sha(self.tokens),position=1,anchor=15,
            host_threads=1,out=self.root/'output',layer_dirs=str(self.root/'L{layer}-d{die}'),
            embedding_npz=self.embedding,snapshot=self.snapshot,draft_dir=self.draft,wait_for_pid=os.getpid(),run=False)

    def test_plan_uses_real_prefix_and_exact_feature_order(self):
        book=self.mod.plan(self.a)
        self.assertEqual(book['feature_layers'],[1,9,17,25,33])
        self.assertEqual(book['feature_shape'],[1,20480])
        self.assertEqual(book['target_layers'],34)
        self.assertFalse(self.a.out.exists())

    def test_wrong_pending_prompt_or_extent_refused(self):
        for name,value in (('anchor',24),('tokens_sha256','bad'),('position',8189)):
            old=getattr(self.a,name);setattr(self.a,name,value)
            with self.subTest(name=name),self.assertRaises(ValueError):self.mod.plan(self.a)
            setattr(self.a,name,old)

    def test_live_owner_blocks_before_nvidia_query_or_numerical_import(self):
        with patch.object(self.mod.subprocess,'run') as query,self.assertRaisesRegex(ValueError,'owner PID still live'):
            self.mod.require_gpu_idle(os.getpid())
        query.assert_not_called()

    def test_another_gpu_owner_blocks_without_fallback(self):
        result=argparse.Namespace(stdout='12345\n')
        with patch.object(self.mod.subprocess,'run',return_value=result),self.assertRaisesRegex(ValueError,'live compute owner'):
            self.mod.require_gpu_idle(999999999)

if __name__=='__main__':unittest.main()
