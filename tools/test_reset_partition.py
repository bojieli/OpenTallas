"""Reset domains must stay independent across elaborated child instances."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'qwen_dv'))
from reset_partition import partition

class ChildResetDomains(unittest.TestCase):
 def render(self,body):
  return partition('module top #(parameter integer N=8)(input wire ck,rst_n);\n'+body+'\nendmodule\n','top','rst_n')
 def test_inline_parameter_scope(self):
  text,m=self.render('for(genvar k=0;k<N;k=k+1) begin:g leaf u(.rst_n(rst_n));end')
  self.assertEqual(m['leaf_count'],8)
  self.assertIn('.rst_n(sr_reset[0+k])',text)
 def test_siblings_do_not_share_leaves(self):
  text,m=self.render('for(genvar k=0;k<8;k=k+1) begin:a leaf u(.rst_n(rst_n));end for(genvar j=0;j<4;j=j+1) begin:b leaf u(.rst_n(rst_n));end')
  self.assertEqual(m['leaf_count'],12)
  self.assertIn('.rst_n(sr_reset[0+k])',text)
  self.assertIn('.rst_n(sr_reset[8+j])',text)
 def test_legacy_generate_scope(self):
  text,m=self.render('genvar k;generate for(k=0;k<8;k=k+1) begin:g leaf u(.rst_n(rst_n));end endgenerate')
  self.assertEqual(m['leaf_count'],8)
  self.assertIn('.rst_n(sr_reset[0+k])',text)
 def test_nested_domains_fail_closed(self):
  with self.assertRaisesRegex(ValueError,'nested child generate'):
   self.render('for(genvar k=0;k<2;k=k+1) begin:a for(genvar j=0;j<4;j=j+1) begin:b leaf u(.rst_n(rst_n));end end')

if __name__=='__main__':unittest.main()
