import unittest
from hbm_sm_control_station_pack import point, overlap, pack

class StationPack(unittest.TestCase):
 def test_rectilinear_arc(self):
  self.assertEqual(point([[0,0],[50,0],[50,50]],75),[50,25])
 def test_spacing(self):
  self.assertFalse(overlap([0,0,20,20],[22.16,0,42.16,20],2.16))
  self.assertTrue(overlap([0,0,20,20],[22,0,42,20],2.16))
 def test_four_distinct_rails(self):
  row=dict(sm='sm0',path_um=[[100,100],[1100,100]],path_length_um=1000,descriptor_bridge_HOPS=5)
  o=pack([row],[])
  self.assertEqual(o['station_count'],20)
  self.assertEqual(o['station_area_um2'],8000)
  self.assertEqual(o['conflict_count'],0)
  self.assertTrue(o['link_budget_pass'])
  cells=o['rows'][0]['stations']
  self.assertEqual(sorted(c['bits']for c in cells if c['stage']==0),[3,3,57,57])
  self.assertTrue(all(not overlap(a['box_um'],b['box_um'],2.16) for i,a in enumerate(cells) for b in cells[i+1:]))
 def test_obstruction_fails(self):
  row=dict(sm='sm0',path_um=[[100,100],[1100,100]],path_length_um=1000,descriptor_bridge_HOPS=5)
  self.assertGreater(pack([row],[('solid',[0,0,2000,2000])])['conflict_count'],0)
if __name__=='__main__':unittest.main()
