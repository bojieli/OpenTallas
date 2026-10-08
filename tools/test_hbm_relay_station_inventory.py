import unittest
from hbm_relay_station_inventory import Index, box, connect, length, overlap, sample, validate_inventory

class StationInventoryTests(unittest.TestCase):
    def test_adjacent_bucket_collision(self):
        i=Index([1000,1000]);i.add([80,80,99,99])
        self.assertFalse(i.legal([100,80,120,100]))
        self.assertTrue(i.legal([102,80,122,100]))
    def test_shape(self):
        self.assertEqual(box([70,90]),[60,80,80,100])
    def test_outline(self):
        i=Index([100,100]);self.assertFalse(i.legal(box([5,20])))
    def test_obstacle_dogleg(self):
        i=Index([1000,1000]);i.add([145,90,155,110])
        p=connect([100,100],[200,100],i,set(),5.12)
        self.assertIsNotNone(p);self.assertGreater(length(p),100)
    def test_pin_allowance(self):
        i=Index([1000,1000])
        self.assertIsNotNone(connect([100,100],[360,100],i,set(),5.12))
        self.assertIsNone(connect([100,100],[360.01,100],i,set(),5.12))
    def test_no_obstacle_bypass(self):
        i=Index([1000,1000]);i.add([145,1,155,999])
        self.assertIsNone(connect([100,100],[200,100],i,set(),5.12))
    def test_arc_sampling(self):
        self.assertEqual(sample([[10,10],[20,10],[20,30]],15),[20,15])
    def test_replay_detects_later_obstacle(self):
        a,b=box([100,100]),box([200,100])
        result={'outline_um':[1000,1000],'candidate_depth_cycles':2,'chains':[{'bus':'leaf','group':0,'bit_indices':[0],'stations':[{'box_um':a,'kind':'source'},{'box_um':b,'kind':'sink'}],'hops':[{'path_um':[[100,100],[200,100]]}]}]}
        paths={'endpoint_boxes':[a,b]}
        self.assertEqual(validate_inventory(result,paths,{'insts':[]})['error_count'],0)
        obstructed={'insts':[{'name':'late_macro','x':140,'y':90,'w':20,'h':20}]}
        self.assertGreater(validate_inventory(result,paths,obstructed)['error_count'],0)
    def test_physical_gap(self):
        self.assertTrue(overlap([0,0,20,20],[22,0,42,20],2.16))
        self.assertFalse(overlap([0,0,20,20],[22.16,0,42.16,20],2.16))
if __name__=='__main__':unittest.main()
