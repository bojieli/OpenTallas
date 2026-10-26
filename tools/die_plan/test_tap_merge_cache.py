"""The cache must preserve the original greedy geometry and index tie breaks."""
import random
import unittest
from unittest.mock import patch
import taps as T


def uncached(leaves, target, radius, blocked=lambda x,y: False):
    leaves=list(leaves)
    while True:
        best=None
        for i,a in enumerate(leaves):
            for j in range(i+1,len(leaves)):
                b=leaves[j]
                if a[2]+b[2]>target or abs(a[0]-b[0])+abs(a[1]-b[1])>2*radius:
                    continue
                g=a[4]+b[4]
                x,y=T._wmedian(g,0),T._wmedian(g,1)
                r=max(abs(p[0]-x)+abs(p[1]-y) for p in g)
                if r<=radius and not blocked(x,y) and (best is None or (r,i,j)<best[:3]):
                    best=(r,i,j,(x,y,a[2]+b[2],r,g))
        if best is None:
            return leaves
        _,i,j,m=best
        leaves=[q for k,q in enumerate(leaves) if k not in (i,j)]+[m]


def fixture(seed,n=36):
    rng=random.Random(seed)
    leaves=[]
    for i in range(n):
        g=[(float(i%9)*8+rng.randrange(3),float(i//9)*6+rng.randrange(3),float(rng.randrange(1,4))) for _ in range(5)]
        x,y=T._wmedian(g,0),T._wmedian(g,1)
        leaves.append((x,y,sum(p[2] for p in g),max(abs(p[0]-x)+abs(p[1]-y) for p in g),g))
    return leaves


class MergeCache(unittest.TestCase):
    def test_exact_geometry_and_sink_order(self):
        for seed in range(6):
            for blocked in (lambda x,y: False,lambda x,y: 20<x<36 and 4<y<14):
                leaves=fixture(seed)
                self.assertEqual(T._merge(leaves,80,35,blocked),uncached(leaves,80,35,blocked))

    def test_ties_and_single_heavy_site(self):
        leaves=[(float(i%3),float(i//3),1.,0.,[(float(i%3),float(i//3),1.)]) for i in range(9)]
        leaves.append((100.,100.,100.,0.,[(100.,100.,100.)]))
        self.assertEqual(T._merge(leaves,4,3),uncached(leaves,4,3))

    def test_unchanged_pairs_are_not_resorted(self):
        leaves=fixture(71)
        original=T._wmedian
        with patch.object(T,'_wmedian',wraps=original) as median:
            expected=uncached(leaves,80,35)
            old_calls=median.call_count
        with patch.object(T,'_wmedian',wraps=original) as median:
            actual=T._merge(leaves,80,35)
            new_calls=median.call_count
        self.assertEqual(actual,expected)
        self.assertLess(new_calls,old_calls/3)


if __name__=='__main__':
    unittest.main()
