import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_noECC_capture_intrinsic_sta as m

class CaptureTimingContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.work=Path(cls.tmp.name)/'fixture'
        cls.record=m.prepare(cls.work)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_budget_deducts_clkq_once(self):
        r=self.record
        self.assertAlmostEqual(r['remaining_after_macro_clkQ_ps'],767.5732666666665)
        self.assertEqual(r['added_cycles'],0)
    def test_all_full_retained_maps_match(self):
        for case in ('q','bfcolumn'):
            self.assertGreater((self.work/case/'mapped.v').stat().st_size,1000000)
            self.assertEqual(m.sha(self.work/case/'mapped.v'),self.record['inputs'][case+'_mapped_verilog'])
    def test_only_source_capture_gets_exception(self):
        for item in self.record['runs']:
            text=Path(item['tcl']).read_text()
            self.assertIn('set_multicycle_path -setup 2 -from $data -to $caps',text)
            self.assertIn('set_multicycle_path -hold 1 -from $data -to $caps',text)
            self.assertIn('!= 1088',text);self.assertIn('!= 1096',text)
            self.assertNotIn('set_input_delay',text);self.assertNotIn('set_output_delay',text)
            self.assertEqual(text.count('create_generated_clock'),8)
    def test_geometry_and_no_physical_claim(self):
        self.assertEqual(self.record['PG_cut_model_sha256'],m.sha(m.BASE/'local_cuts.json'))
        for key in ('PnR_admitted','physical_closure','parent_IO_closed','cold_mapping','engine_RTL_changed'):
            self.assertFalse(self.record[key])
    def test_first_evidence_cannot_be_overwritten(self):
        with self.assertRaises(ValueError):m.prepare(self.work)

if __name__=='__main__':unittest.main()
