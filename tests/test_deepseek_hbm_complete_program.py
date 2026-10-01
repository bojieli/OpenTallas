import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import deepseek_hbm_complete_program as P

class CompleteProgram(unittest.TestCase):
    def test_all40_and_head_handlers_cost_gaps_explicit(self):
        g=P.compile_program();self.assertEqual(g['coverage']['operations'],2213)
        self.assertEqual({i['layer'] for i in g['instructions']},set(range(40))|{'head'})
        self.assertEqual(g['coverage']['software_handlers_bound'],2213)
        self.assertFalse(g['coverage']['full_GPU_instruction_lowering_complete'])
        self.assertEqual(g['coverage']['ordinary_GPU_numerical_operator_bindings'],40)
        self.assertFalse(g['DUT_RTL_qualified'])
        self.assertEqual([i['pc'] for i in g['instructions']],list(range(2213)))
        for i in g['instructions']:
            self.assertIsNone(i['costs']['issue_cycles']);self.assertIsNone(i['costs']['HBM_service_cycles'])
            self.assertEqual(i['costs']['shared_bytes_per_fast_1p2GHz_cycle_limit'],96)
    def test_fail_closed_missing_kernel_or_geometry(self):
        g=json.loads((P.ROOT/P.SOURCE).read_text());g['layers'][0]['ops'][0]['fn']='invented'
        with self.assertRaises(ValueError):P.compile_program(g)
        g=json.loads((P.ROOT/P.SOURCE).read_text());g['tp']=4
        with self.assertRaises(ValueError):P.compile_program(g)

if __name__=='__main__':unittest.main()
