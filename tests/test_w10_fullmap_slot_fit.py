import importlib.util
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w10_fullmap_slot_fit as F

def union_area(rects):
    xs=sorted({x for r in rects for x in (r[0],r[2])})
    area=0
    for a,b in zip(xs,xs[1:]):
        ys=sorted((r[1],r[3]) for r in rects if r[0]<b and r[2]>a)
        if not ys: continue
        lo,hi=ys[0];covered=0
        for l,h in ys[1:]:
            if l>hi: covered+=hi-lo;lo,hi=l,h
            else: hi=max(hi,h)
        area+=(b-a)*(covered+hi-lo)
    return area

def test_unique_grid_masks_and_minimal_density_budget():
    b=F.budget();rects=[]
    # Site coordinates relative to2160nm origin; capture-corridor candidate.
    for x in (376,15796):
        for y in (16,267):
            rects.extend([(x,y,x+2320,y+233),(x-256,y,x,y+233),
                          (x+2320,y,x+2576,y+233),
                          (x-38,y-8,x+2358,y),(x-38,y+233,x+2358,y+241)])
    assert union_area(rects)==b['macro_sites']+b['exclusive_escape_sites']+b['exclusive_top_bottom_halo_sites']
    assert all(0<=r[0]<r[2]<=b['width_sites'] and 0<=r[1]<r[3]<=b['rows'] for r in rects)
    assert b['free_sites']>=2*b['standard_cell_demand_sites']
    assert b['free_sites']-b['width_sites']<2*b['standard_cell_demand_sites']

def test_mirrored_phase_correction_required():
    centers=[780+96*i for i in range(144)]
    assert all((74250+62910-y)%48==12 for y in centers)
    assert any((73440+62910-y)%48!=12 for y in centers)
    assert (74250-2160)%270==0

def test_actual_endpoint_sets_cannot_be_shared_or_halved():
    import json
    e=json.loads((ROOT/'results/uarch/w10_baseline_wake/slot_fit_r1/macro_capture_endpoints.json').read_text())
    s=[set(v['endpoints']) for v in e.values()]
    assert len(set.union(*s))==sum(map(len,s))==1088
    assert all(v['types']=={'DFFHQNx1_ASAP7_75t_R':272} for v in e.values())

def test_growth_reserve_does_not_double_count_synthesis_or_change_density():
    a,b=F.budget(),F.budget(4665.4)
    assert a['density']==b['density']==.5
    assert a['macro_sites']==b['macro_sites']
    assert b['rows']>a['rows']
    assert b['stdcell_capacity_um2']>=62705.9+4665.4
