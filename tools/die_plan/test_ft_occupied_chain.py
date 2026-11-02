import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from ft_reach_legalizer import ReachAllocator, _weighted_distance
import numpy as np
class Chain(unittest.TestCase):
 def test_joint_path_uses_real_unoccupied_rows_around_wide_obstacle(self):
  a=ReachAllocator((0,0,14,12),blocked=[(3,0,10,8)],cell_size=(1,1),column_pitch=1,row_pitch=1,origin=(0,0))
  points,stats=a.allocate_chain((.5,.5),(13.5,.5),[(3,.5),(5,.5),(7,.5),(9,.5),(11,.5)],reach=6)
  self.assertEqual(len(points),5);self.assertLessEqual(stats['max_hop_um'],6)
  self.assertTrue(any(y>8 for x,y in points));self.assertEqual(len(a.used),5)
  self.assertTrue(all(not(3<x+.5 and x-.5<10 and 0<y+.5 and y-.5<8)for x,y in points))
 def test_reserved_only_bridge_stays_unavailable_and_failure_is_atomic(self):
  a=ReachAllocator((0,0,10,1),cell_size=(1,1),column_pitch=1,row_pitch=1,origin=(0,0));a.reserve_rectangle((4,0,5,1));old=set(a.used)
  with self.assertRaises(ValueError):a.allocate_chain((.5,.5),(8.5,.5),[(4.5,.5)],reach=4)
  self.assertEqual(old,a.used)
 def test_distinct_stage_bodies_are_reserved_once(self):
  a=ReachAllocator((0,0,12,2),cell_size=(1,1),column_pitch=1,row_pitch=1,origin=(0,0));pts,_=a.allocate_chain((.5,.5),(10.5,.5),[(3.5,.5),(7.5,.5)],reach=4)
  self.assertEqual(len(set(pts)),2);self.assertEqual(len(a.used),2)
class WeightedDistance(unittest.TestCase):
 def test_distances_match_exhaustive_weighted_manhattan_oracle(self):
  rng=np.random.default_rng(730)
  for shape in ((1,9),(9,1),(8,13)):
   mask=rng.random(shape)<.2;mask[-1,-1]=True
   actual=_weighted_distance(mask,(2.16,.27));grid=np.indices(shape).transpose(1,2,0)
   expected=np.min(np.array([np.abs(grid-q)@[2.16,.27] for q in np.argwhere(mask)]),axis=0)
   np.testing.assert_allclose(actual,expected,atol=1e-6,rtol=0)
 def test_backward_only_seed_propagates_without_mutating_input(self):
  mask=np.zeros((5,7),bool);mask[-1,-1]=True;saved=mask.copy()
  actual=_weighted_distance(mask,(2.16,.27));self.assertAlmostEqual(actual[0,0],4*2.16+6*.27)
  np.testing.assert_array_equal(mask,saved)
if __name__=='__main__':unittest.main()
