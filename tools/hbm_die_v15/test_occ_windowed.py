import unittest
import numpy as np
from die_occupancy import Occ,CELL

class WindowedOccupancy(unittest.TestCase):
 def compare(self,grid,args):
  a=Occ((grid.shape[1]-1)*CELL+1e-6,(grid.shape[0]-1)*CELL+1e-6)
  b=Occ(a.W,a.H);a.g[:]=grid;b.g[:]=grid
  b.ii()  # Original complete summed-area image oracle; exact same candidate order.
  self.assertEqual(a.find(*args),b.find(*args))
 def test_random_obstacles_regions_and_halos(self):
  rng=np.random.default_rng(17409)
  for k in range(48):
   grid=(rng.random((61,81))<.12).astype(np.uint8)
   x,y=rng.uniform(-20,820),rng.uniform(-20,620)
   w,h=rng.uniform(2,40),rng.uniform(2,40)
   region=(100,100,700,500) if k%3==0 else None
   self.compare(grid,(x,y,w,h,3.0 if k%2 else 0.0,region,30 if k%4==0 else None))
 def test_window_growth_far_free_rectangle_and_no_space(self):
  grid=np.ones((161,201),np.uint8);grid[130:140,170:180]=0
  self.compare(grid,(20,20,20,20,0,None,None))
  self.compare(np.ones((81,101),np.uint8),(0,0,30,30,0,None,None))
 def test_mark_invalidates_previous_full_cache(self):
  a=Occ(800,600);b=Occ(800,600);a.ii();b.ii()
  a.mark(380,280,60,60,2);b.mark(380,280,60,60,2);b.ii()
  self.assertIsNone(a._ii)
  self.assertEqual(a.find(400,300,30,30),b.find(400,300,30,30))

if __name__=='__main__':unittest.main()
