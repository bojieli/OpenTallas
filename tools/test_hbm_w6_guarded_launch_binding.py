import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import hbm_w6_guarded_launch_binding as B

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.rf='ot_sram_1r1w_128x256_m1_r2c2';self.sc='ot_sram_1r1w_1024x256_m2_r2c2'
        self.args=['--macro-view',self.rf+'=physical/asap7_memory_macros/'+self.rf,'--macro-view',self.sc+'=physical/asap7_memory_macros/'+self.sc]
        self.r=json.loads(B.RECORD.read_text())
    def call(self,args):
        # Unit-only empty source-pin fixture; actual parent rehash is separate.
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'binding.json';r=dict(self.r);r['source_sha256']={};p.write_text(json.dumps(r))
            with patch.object(B,'RECORD',p):return B.prepare(d,args)
    def test_mandatory_guarded_entry(self):
        r=self.call(self.args);self.assertIn('--macro-track-gate',r['argv'])
        self.assertTrue(r['argv'][1].endswith('run_abi3_physical_aligned_guarded.py'))
        self.assertFalse(r['launch_executed'])
    def test_v2_requires_new_model(self):
        with self.assertRaises(ValueError):self.call([a.replace('asap7_memory_macros/','asap7_memory_macros_v2/') for a in self.args])
    def test_empty_macrocontext(self):
        with self.assertRaises(ValueError):self.call([])
    def test_duplicate_master(self):
        with self.assertRaises(ValueError):self.call(self.args+self.args[:2])
    def test_missing_RF_shape(self):
        with self.assertRaises(ValueError):self.call(self.args[2:])
    def test_cannot_hide_wrapper_gate(self):
        with self.assertRaises(ValueError):self.call(self.args+['--gate-only'])
    def test_changed_parent_guard_source(self):
        with tempfile.TemporaryDirectory() as d,self.assertRaises(FileNotFoundError):B.prepare(d,self.args)
    def test_no_physical_inheritance(self):
        self.assertFalse(self.r['inherited_parent_claims']['SSFF_wholeparent'])
        self.assertFalse(self.r['macro_geometry_adopted_from_v2'])
        self.assertEqual(self.r['target']['bench_period_ps'],10000)

if __name__=='__main__':unittest.main()
