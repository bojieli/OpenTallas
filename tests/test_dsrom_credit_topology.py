"""Topology gate: every active macro leaf exactly once under its assigned root."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from gen_dsrom_credit_return import topology
class Topology(unittest.TestCase):
 def test_active_pair_coverage(self):
  for np,r in [(1,1),(5,2),(17,7),(2682,128),(4096,128)]:
   t=topology(np,r);nodes={x['id']:x for x in t['nodes']};seen=[]
   def visit(i):
    if i<2*np:return [i]
    x=nodes[i];self.assertLess(x['a'],i);self.assertLess(x['b'],i)
    return visit(x['a'])+visit(x['b'])
   for root,(lo,hi) in zip(t['roots'],t['pair_spans']):
    leaves=visit(root);self.assertEqual(leaves,list(range(2*lo,2*hi)));seen+=leaves
   self.assertEqual(seen,list(range(2*np)));self.assertEqual(len(nodes),2*np-r)
 def test_bad_geometry(self):
  for np,r in [(0,1),(3,4),(8,0)]:
   with self.assertRaises(ValueError):topology(np,r)
if __name__=='__main__':unittest.main()
