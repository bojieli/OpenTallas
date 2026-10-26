import unittest
import numpy as np
from path_hbm_perbit_m5 import TargetIndex

class TargetGeometry(unittest.TestCase):
 def test_sparse_macro_corridors_match_exact_radius(self):
  x,y=np.meshgrid(np.arange(0,1000,8.64),np.arange(0,800,8.64));pts=np.column_stack((x.ravel(),y.ravel()));pts=pts[~((pts[:,0]>100)&(pts[:,0]<700)&(pts[:,1]>100)&(pts[:,1]<600))]
  idx=TargetIndex(pts,350)
  for p in ([0,0],[100,100],[350,350],[700,700],[999,799],[-10,400]):
   np.testing.assert_array_equal(idx.query(np.array(p)),np.flatnonzero(np.abs(pts-p).sum(axis=1)<=350))
 def test_boundary_targets_and_empty_region(self):
  pts=np.array([[0,0],[350,0],[700,0],[350,350],[0,700]],float);idx=TargetIndex(pts,350)
  np.testing.assert_array_equal(idx.query(np.array([350,0])),[0,1,2,3]);self.assertEqual(len(idx.query(np.array([2000,2000]))),0)
  self.assertEqual(len(TargetIndex(np.empty((0,2)),350).query(np.array([0,0]))),0)
if __name__=='__main__':unittest.main()
