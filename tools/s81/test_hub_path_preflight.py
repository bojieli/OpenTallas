import unittest
from hub_path_preflight import audit,merge_intervals

class HubPathPreflight(unittest.TestCase):
    def test_crossing_source_or_receiver_is_not_hidden(self):
        r=audit([(0,5),(30,5)],[(0,0,30,10)],[('macro',10,0,10,10)])
        self.assertEqual(r['macro_crossings'],[dict(segment=0,macro='macro',inside_um=10)])
    def test_allowed_region_mismatch_is_complete(self):
        r=audit([(0,0),(100,0)],[(0,-1,20,1),(50,-1,60,1)],[])
        self.assertEqual([x['length_um'] for x in r['station_region_gaps']],[30,40])
    def test_face_touch_and_short_access_gap_are_legal(self):
        r=audit([(0,0),(30,0)],[(10,-1,20,1)],[('macro',0,0,30,10)])
        self.assertFalse(r['macro_crossings']);self.assertFalse(r['station_region_gaps'])
    def test_vertical_crossing_and_non_orthogonal_refuse(self):
        self.assertTrue(audit([(5,0),(5,30)],None,[('macro',0,10,10,10)])['macro_crossings'])
        self.assertEqual(audit([(0,0),(2,2)],None,[])['macro_crossings'][0]['reason'],'NON_ORTHOGONAL')
    def test_union_handles_nested_and_disjoint_regions(self):
        self.assertEqual(merge_intervals([(0,2),(1,3),(2,2),(5,6)]),[[0,3],[5,6]])

if __name__=='__main__':unittest.main()
