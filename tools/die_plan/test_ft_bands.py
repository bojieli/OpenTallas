import sys
import unittest
from types import SimpleNamespace
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import ft_bands as B

class Bands(unittest.TestCase):
    def plan(self,share=1):
        return SimpleNamespace(types={'t':dict(outline_um=[12,8],ft_track_frac=0,die_ft_bands=[dict(dir='NS',span_um=[4,8],layers=['M5'],die_share=share)])},
             layers={L:dict(dir='H' if L in ('M4','M6') else 'V',pitch_um=1,offset_um=.5) for L in B.LAYERS},
             parts={o:dict(type='t',origin_um=[20,40],orient=o) for o in ('R0','MX','MY','R180')})
    def test_full_strip_and_complement(self):
        p=self.plan(); rs=B.type_rects(p,'t'); self.assertEqual(rs,[('M5',4,0,8,8)])
        self.assertEqual(sum((r[3]-r[1])*(r[4]-r[2]) for r in B.type_rects(p,'t',False)),12*8*4-32)
        for r in rs:
            for q in B.type_rects(p,'t',False):
                if r[0]==q[0]: self.assertEqual(B.coverage(r[1:],[q[1:]]),0)
    def test_share_never_rounds_up(self):
        for sh in (0,.1,.25,.49,.5,.75,1):
            rs=B.type_rects(self.plan(sh),'t')
            self.assertEqual(sum((r[3]-r[1]) for r in rs),int(4*sh))
    def test_mirrors(self):
        p=self.plan()
        r=B.type_rects(p,'t')[0]
        self.assertEqual(B.to_die(p,'MY',r),('M5',24,40,28,48))
        self.assertEqual(B.to_die(p,'MX',r),('M5',24,40,28,48))
    def test_overlap_union(self):
        p=self.plan();p.types['t']['die_ft_bands']*=2
        self.assertEqual(B.type_rects(p,'t'),[('M5',4,0,8,8)])
    def test_finite_rectangle_audit(self):
        self.assertAlmostEqual(B.coverage((0,0,10,10),[(0,0,10,2)]),.2)
        self.assertEqual(B.coverage((0,5,10,10),[(0,0,10,2)]),0)
    def test_background_and_override(self):
        p=self.plan(0);p.grid=4;p.types['t']['ft_track_frac']=.5
        rs=B.type_rects(p,'t')
        m5=[r for r in rs if r[0]=='M5']
        self.assertEqual(sum(r[3]-r[1] for r in m5),4)
        self.assertTrue(all(r[3]<=4 or r[1]>=8 for r in m5))
    def test_max_overlap(self):
        p=self.plan(.5);p.grid=4
        p.types['t']['die_ft_bands'].append(dict(dir='NS',span_um=[4,8],layers=['M5'],die_share=.75))
        self.assertEqual(sum(r[3]-r[1] for r in B.type_rects(p,'t') if r[0]=='M5'),3)
    def test_bad_direction(self):
        p=self.plan();p.types['t']['die_ft_bands'][0]['layers']=['M4']
        with self.assertRaises(ValueError): B.type_rects(p,'t')

if __name__=='__main__': unittest.main()
