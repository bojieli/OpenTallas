"""Differential geometry checks for the exact tap candidate filter optimization."""
import math
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/die_plan'))
import schema as S


def reference(t,x,y,taken,clear,strict,boxes):
    w,h=t['outline_um']
    boxes=list(boxes)+[(a-clear,b-clear,c+clear,d+clear) for a,b,c,d in t.get('clock',{}).get('keepouts_um',[])]
    def free(px,py):
        return clear<=px<=w-clear and clear<=py<=h-clear and not any(abs(px-a)<clear and abs(py-b)<clear for a,b in taken) and not any(a<px<c and b<py<d for a,b,c,d in boxes)
    if (not boxes and not strict) or free(x,y):return x,y
    def candidates(origin,extent,edges):
        values={origin}
        for edge in [clear,extent-clear]+edges:
            q=(edge-origin)/S.TAP_STEP_UM
            for k in (math.floor(q),math.ceil(q)):
                v=round(origin+k*S.TAP_STEP_UM,8)
                if clear-1e-7<=v<=extent-clear+1e-7:values.add(v)
        return values
    obs=boxes+[(a-clear,b-clear,a+clear,b+clear) for a,b in taken]
    xs=candidates(x,w,[v for a,b,c,d in obs for v in (a,c)])
    ys=candidates(y,h,[v for a,b,c,d in obs for v in (b,d)])
    legal=[(px,py) for px in xs for py in ys if free(px,py)]
    if not legal:raise ValueError('no legal site')
    a,b=min(legal,key=lambda p:(round(max(abs(p[0]-x),abs(p[1]-y)),7),(p[0]-x)**2+(p[1]-y)**2,p))
    return round(a,4),round(b,4)

class TapFilterTest(unittest.TestCase):
    def test_exact_policy(self):
        rng=random.Random(1029)
        for case in range(160):
            t={'outline_um':[rng.uniform(8,160),rng.uniform(8,160)]}
            boxes=[]
            for _ in range(rng.randrange(14)):
                a,b=rng.uniform(-5,160),rng.uniform(-5,160)
                boxes.append((a,b,a+rng.uniform(0,80),b+rng.uniform(0,80)))
            taken=[(rng.uniform(0,160),rng.uniform(0,160)) for _ in range(rng.randrange(16))]
            x,y=rng.uniform(-5,160),rng.uniform(-5,160)
            clear=rng.choice([0.1,2.16,3.24,10.8]);strict=bool(case%2)
            with patch.object(S,'placed_macro_boxes',return_value=dict(enumerate(boxes))):
                try:expected=reference(t,x,y,taken,clear,strict,boxes)
                except ValueError:
                    with self.assertRaises(ValueError):S.tap_clear(t,x,y,taken,clear,strict)
                else:self.assertEqual(S.tap_clear(t,x,y,taken,clear,strict),expected,case)
    def test_float_boundary_and_no_site(self):
        for x,y in [(2.16,2.16),(4.32,4.32),(0.1+0.2,0.3)]:
            t={'outline_um':[20,20],'clock':{'keepouts_um':[[3,3,5,5]]}}
            taken=[(x+2.16,y),(x,y+2.16)]
            with patch.object(S,'placed_macro_boxes',return_value={}):
                self.assertEqual(S.tap_clear(t,x,y,taken,2.16,True),reference(t,x,y,taken,2.16,True,[]))
        with patch.object(S,'placed_macro_boxes',return_value={'all':(-10,-10,20,20)}):
            with self.assertRaisesRegex(ValueError,'no legal clock tap site'):S.tap_clear({'outline_um':[8,8]},4,4,strict=True)
if __name__=='__main__':unittest.main()
