import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/s81_compile_schedule'),str(ROOT/'tools/s81_suhc')]
from operand_layout import cp_binding
from su_gate import Run,SHAPES

class CPBindingTest(unittest.TestCase):
 def test_native_addresses_descriptor_and_banks(self):
  for layer in (2,8,14):
   for pool in (False,True):
    b=cp_binding(layer,0x12345678,int(pool),pool=pool)
    r=Run(SHAPES['full']);r.cp_bind(4816,4848,4880,12336,0x12345678,int(pool),pool)
    self.assertEqual(r.vm[12336],sum(x<<(32*i)for i,x in enumerate(b['descriptor_words'])))
    self.assertEqual(r.prog[0]>>7,b['command_arg24'])
    self.assertEqual(set(r.vm),{12336})
    self.assertFalse(r.exp)
    self.assertEqual([x['relative_issue_cycle']for x in b['read_requests']],list(range(0,128,4)))
    self.assertTrue(all(x['banks'][0]!=x['banks'][1]for x in b['read_requests']))
    self.assertEqual(len(b['output_rows']),32 if pool else 0)
    self.assertFalse(b['dispatch_eligible'])
 def test_wrong_ratio_or_context_refused(self):
  for layer,context,slot in [(20,1,0),(2,2**32,0),(2,1,2)]:
   with self.assertRaises(ValueError):cp_binding(layer,context,slot,pool=True)
 def test_descriptor_overlap_refused(self):
  r=Run(SHAPES['full'])
  with self.assertRaisesRegex(ValueError,'overlaps'):r.cp_bind(4816,4848,4880,4820,1,1,True)
if __name__=='__main__':unittest.main()
