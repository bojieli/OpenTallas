"""Actual S81 source geometry where narrow rings steal a wide ring's only bay."""
import copy,gzip,json,unittest
from pathlib import Path
import clock_landing_plan as C

class LandingBandOrder(unittest.TestCase):
    def setUp(self):
        with gzip.open(Path(__file__).parent/'testdata/s81_landing_order_t3.json.gz','rt')as f:self.fixture=json.load(f)

    def allocate(self,largest):
        f=self.fixture; used=copy.deepcopy(f['fixed_rectangles']);rings=list(f['rings']);out=[]
        data=[r for r in rings if r['has_epoch']];monitor=[r for r in rings if not r['has_epoch']]
        if largest:data.sort(key=lambda r:(-r['width'],r['bus']))
        for r in data+monitor:
            q=C._storage_band(f['type'],r['bus'],r['width'],used,has_epoch=r['has_epoch'])
            used.append(q['rect_um']);out.append(q)
        return out

    def test_actual_name_order_blocks_wide_ring(self):
        with self.assertRaisesRegex(ValueError,'no macro-free clock landing storage band forattnh_i0'):
            self.allocate(False)

    def test_largest_first_keeps_full_reserve_and_reach(self):
        boxes=self.allocate(True)
        self.assertEqual(len(boxes),len(self.fixture['rings']))
        for i,q in enumerate(boxes):
            a,b,c,d=q['rect_um']
            self.assertGreaterEqual((c-a)*(d-b)+1e-3,q['area_reserve_um2'])
            self.assertLessEqual(q['max_pin_to_band_hop_um'],405-2.16+1e-3)
            for earlier in boxes[:i]:
                w,x,y,z=earlier['rect_um']
                self.assertFalse(min(c,y)>max(a,w)+1e-6 and min(d,z)>max(b,x)+1e-6)

    def test_invalid_order_fails_before_build(self):
        with self.assertRaisesRegex(ValueError,'band_order_by_type'):
            C.compose({}, {}, band_order_by_type={'t':'relax'})

if __name__=='__main__':unittest.main()
