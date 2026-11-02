import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ft_reach_legalizer import ReachAllocator
from tools.die_trial.legal_sites import RowAllocator
class Tests(unittest.TestCase):
 def make(self,kind=ReachAllocator):return kind((0,0,100,1),cell_size=(1,1),column_pitch=1,row_pitch=1,origin=(0,0))
 def test_nearest_illegal_hop_uses_actual_legal_neighbor(self):
  old=self.make(RowAllocator);q,_=old.allocate((8.5,.5),1,max_radius_um=20);self.assertGreater(abs(q[0][0]-.5),4)
  new=self.make();q,stats=new.allocate_reachable((8.5,.5),(.5,.5),(8.5,.5),reach=4,max_radius_um=20);self.assertEqual(q,(4.5,.5));self.assertEqual(stats['previous_hop_um'],4)
 def test_reserved_only_bridge_rejects_without_relaxing(self):
  a=self.make();a.reserve_rectangle((4,0,5,1))
  with self.assertRaises(ValueError):a.allocate_reachable((8.5,.5),(.5,.5),(8.5,.5),reach=4,max_radius_um=80)
 def test_exhausted_twenty_um_neighborhood_expands_within_original_reach(self):
  a=self.make();a.reserve_rectangle((30,0,71,1))
  with self.assertRaises(ValueError):a.allocate((50.5,.5),1,max_radius_um=20)
  q,_=a.allocate_reachable((50.5,.5),(.5,.5),(99.5,.5),reach=80,max_radius_um=80)
  self.assertGreater(abs(q[0]-50.5),20);self.assertLessEqual(max(abs(q[0]-.5),abs(q[0]-99.5)),80)
 def test_no_overlapping_reservations(self):
  a=self.make();q,_=a.allocate_reachable((50.5,.5),(.5,.5),(99.5,.5),reach=99)
  r,_=a.allocate_reachable((50.5,.5),(.5,.5),(99.5,.5),reach=99);self.assertNotEqual(q,r)
 def test_native_adapter_compiles_and_is_explicit(self):
  import tempfile
  import ft_sites_unblock as F
  from ft_reach_legalizer import install_reach_slot
  old=F._slot
  try:
   with tempfile.TemporaryDirectory()as d:
    src=install_reach_slot(F,Path(d)/'slot.py')
    self.assertIn('al.allocate_reachable',src)
    self.assertIn('reach=smax',src)
    self.assertIn('if worst > smax:',src)
  finally:F._slot=old
if __name__=='__main__':unittest.main()
