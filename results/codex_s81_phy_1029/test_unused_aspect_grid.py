"""A legal narrow S81-style corridor whose aspect was absent from the old search."""
import unittest
import clock_landing_plan as C

class LandingAspectGrid(unittest.TestCase):
    def scan(self,**kw):
        return C._grid_scan(300,600,[[56.16,0,300,600]],17.28,0,300,
                            16000,21.6,750,**kw)

    def test_opt_in_finds_real_reserved_corridor(self):
        self.assertEqual(self.scan(),[])
        found=self.scan(complete_aspect=True)
        self.assertTrue(found)
        for x0,y0,x1,y1 in found:
            self.assertGreaterEqual((x1-x0)*(y1-y0),16000)
            self.assertGreaterEqual(x0,17.28)
            self.assertGreaterEqual(y0,17.28)
            self.assertLessEqual(x1,56.16+1e-8)
            self.assertLessEqual(y1,600-17.28+1e-8)
            self.assertLessEqual(max(abs(x)+abs(y-300) for x in (x0,x1) for y in (y0,y1)),405-2.16+1e-8)

    def test_reach_is_not_relaxed(self):
        self.assertEqual(self.scan(complete_aspect=True,reach=100),[])

    def test_obstacle_is_not_shrunk(self):
        self.assertEqual(C._grid_scan(300,600,[[43.2,0,300,600]],17.28,0,300,
                                      16000,21.6,750,complete_aspect=True),[])

if __name__=='__main__':unittest.main()
