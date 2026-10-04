import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from dsrom_s81_rd64_connectivity import derive,ledger,emit
class Connectivity(unittest.TestCase):
 def test_s81_exact_source_pruning(self):
  t=derive();m=ledger(t)
  self.assertEqual((len(t['active_leaves']),len(t['nodes']),len(t['removed_nodes']),len(t['roots'])),(4834,5090,2974,128))
  self.assertEqual(len(t['retained_unilateral_nodes']),384)
  self.assertEqual(m['exact_removed_declared_storage_bits'],24939964)
  self.assertEqual(m['original_storage_bits']-m['retained_storage_bits'],m['exact_removed_declared_storage_bits'])
  nodes={n['id']:n for n in t['nodes']}
  def descendants(i):
   if i is None:return []
   if i<4834:return [i]
   n=nodes[i];return descendants(n['a'])+descendants(n['b'])
  for root,(a,b) in zip(t['roots'],zip(t['region_bounds'],t['region_bounds'][1:])):
   self.assertEqual(descendants(root['input']),list(range(2*a,2*b)))
   self.assertEqual(root['region'],root['VM_port'])
  keep={n['old_id'] for n in t['nodes']};dead={n['old_id'] for n in t['removed_nodes']}
  self.assertFalse(keep&dead);self.assertEqual(len(keep|dead),8064)
 def test_NO_READY_unmodified_legacy_modules(self):
  s=emit(derive(5,2,4))
  self.assertNotIn('o_credit',s);self.assertNotIn('.a_ready',s);self.assertNotIn('ot_v41_ret_credit',s)
  self.assertEqual(s.count('ot_v41_ret_root #'),2)
  self.assertEqual(s.count('ot_v41_retn_w17w10 #'),len(derive(5,2,4)['nodes']))
 def test_bad_region_rejected(self):
  with self.assertRaises(ValueError):derive(region_bounds=[0]*129)
if __name__=='__main__':unittest.main()
