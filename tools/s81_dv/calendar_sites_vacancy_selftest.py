"""Adversarial geometry checks for atomic reset calendar reservations."""
import sys
import unittest
from pathlib import Path
from calendar_sites import remove_rect, rebuild_occupancy
from calendar_sites_vacancy import reserve


class CalendarSitesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Test with the actual case's executed Placer, supplied by the replay bundle.
        sys.path[:0] = [str(Path(sys.argv[0]).parent/'input/src/tools/s81_dv'),
                        str(Path(sys.argv[0]).parent/'input/src/tools')]
        from dv_rvcase import Placer
        cls.Placer = Placer

    def test_whole_chain_packs_around_fixed_macro(self):
        names = ['s%03d' % n for n in range(70)]
        parent = dict(zip(names[1:], names))
        kids = {v: ([names[k+1]] if k+1 < len(names) else []) for k,v in enumerate(names)}
        loc = {v: (491.36,491.36,17.28,17.28,'FIRM') for v in names}
        planned = {v:(500.,500.) for v in names}
        p = self.Placer(2000,2000)
        p.add((400,400,480,600))
        fixed, report = reserve(set(names),parent,kids,{v:[] for v in names},planned,loc,p,405,
                                {v:(300,300,700,700) for v in names})
        self.assertEqual(len(fixed),len(names))
        for v,c in fixed.items():
            self.assertTrue(300 <= c[0] <= 700 and 300 <= c[1] <= 700)
            for u,d in fixed.items():
                if u == v:continue
                self.assertTrue(abs(c[0]-d[0]) >= 17.78-1e-6 or abs(c[1]-d[1]) >= 17.78-1e-6)
        for v,u in parent.items():
            self.assertLessEqual(sum(abs(a-b) for a,b in zip(fixed[v],fixed[u])),399)

    def test_center_width_roundtrip_removes_every_bucket(self):
        p=self.Placer(20000,20000);c=10000.;w=17.28
        r=(c-w/2,c-w/2,c+w/2,c+w/2);p.add(r)
        rebuilt=(r[0],r[1],r[0]+w,r[1]+w)
        self.assertNotEqual(r,rebuilt)  # Actual failing legacy tuple identity.
        remove_rect(p,rebuilt)
        self.assertFalse(any(p.buck.values()))
        self.assertFalse(p.hits(r))

    def test_current_geometry_rebuild_drops_forward_ghosts_keeps_reserves(self):
        p=self.Placer(2000,2000);p.add((100,100,101.2,100.6))
        loc={'fwd_x':(500,500,1.2,.6,'PLACED'),'reset':(600,600,17.28,17.28,'FIRM')}
        rebuild_occupancy(p,loc,{'reset'},[dict(x=800,y=800,w=100,h=100)])
        self.assertFalse(p.hits((100,100,101.2,100.6)))
        self.assertTrue(p.hits((500,500,501.2,500.6)))
        self.assertTrue(p.hits((850,850,851,851)))
        self.assertFalse(p.hits((600,600,617.28,617.28)))

    def test_blocked_chain_never_partially_reserves(self):
        names=['a','b','c','d'];p=self.Placer(2000,2000);p.add((1.2,1.2,1998.8,1998.8))
        before=sum(map(len,p.buck.values()))
        fixed,report=reserve(set(names),{'b':'a','c':'b','d':'c'},
             {'a':['b'],'b':['c'],'c':['d'],'d':[]},{v:[] for v in names},
             {v:(500.,500.) for v in names},{v:(491.36,491.36,17.28,17.28,'FIRM') for v in names},p,405,{})
        self.assertFalse(fixed);self.assertEqual(sum(map(len,p.buck.values())),before)
        self.assertEqual(len(report['unresolved']),1)

    def test_explicit_macro_center_outside_body_is_insufficient(self):
        p=self.Placer(2000,2000);p.add((100,500,1000,1500))
        with self.assertRaises(ValueError):
            reserve({'x'},{},{'x':[]},{'x':[]},{'x':(500.,498.)},
                    {'x':(491.36,489.36,17.28,17.28,'FIRM')},p,405,{},explicit=['x'])


if __name__=='__main__':unittest.main()
