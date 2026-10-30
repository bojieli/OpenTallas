"""Zero-span detours share the immediately reachable street, rather than its first one-um bin."""
import numpy as np
import geom_rules as G
from test_auto_geom import dump


def crossing_dump(tmp_path, street, nets=400, direct=False):
    ys = [40 + i % 120 for i in range(1,nets+1)] if not direct else [5.] * nets
    flops = [(i,5,y) for i,y in enumerate(ys,1)] + [(1000+i,195,y) for i,y in enumerate(ys,1)]
    return dump(tmp_path/'crossing.tsv',flops=flops,macros=[(500,20,street,180,200)],
                nets=[('SIGNAL',f'i{i}',[f'i{1000+i}']) for i in range(1,nets+1)])


def test_complete_adjacent_streets_stop_before_another_wall():
    # The blocked bbox is bins2..3; only streets0..1 and4..5 flank it. Bin7 is behind another wall and stays out.
    cap=np.array([2.,2.,0.,0.,2.,2.,0.,2.])
    lo,hi=G._detour_channel_spans(cap,np.array([2]),np.array([3]))
    assert (lo.tolist(),hi.tolist())==([0],[5])
    # Capacity-weighted allocation still represents exactly one crossing.
    u=cap[lo[0]:hi[0]+1]/sum(cap[lo[0]:hi[0]+1])
    assert abs(sum(u)-1)<1e-12


def test_actual_width_street_absorbs_detours_without_one_bin_spike(tmp_path):
    d=G.Design(crossing_dump(tmp_path,36))
    m=G.demand_metrics(d)
    assert m['detour_h']>0 and m['blocked_h']==0
    assert m['channel_h_max']<G.DEMAND_MAX  # 400 crossings / (36um *36.46 tracks/um), no GRT input
    assert m['detour_h_extent_at']['allocated_um'][0]==0


def test_insufficient_ten_um_street_still_exceeds_capacity(tmp_path):
    m=G.demand_metrics(G.Design(crossing_dump(tmp_path,10)))
    assert m['detour_h']>0 and m['blocked_h']==0
    assert m['channel_h_max']>G.DEMAND_HARD


def test_full_macro_wall_keeps_zero_capacity_crossings_blocked(tmp_path):
    m=G.demand_metrics(G.Design(crossing_dump(tmp_path,0)))
    assert m['blocked_h']>0
    assert m['detour_h_extension_max_um']==0
    assert m['channel_h_max'] is None
    full=G.metrics(str(tmp_path/'crossing.tsv'),odb='3_place.odb')
    rules,_=G.judge(full,None,[200,200])
    assert next(r['status'] for r in rules if r['rule']=='blocked_h')=='FAIL'


def test_directly_accessible_pin_wall_is_not_spread_into_whole_street(tmp_path):
    # These direct nets already have capacity in their one-bin bbox. They must not borrow the rest of a36umstreet.
    m=G.demand_metrics(G.Design(crossing_dump(tmp_path,36,direct=True)))
    assert m['detour_h']==0
    assert m['channel_h_max']>G.DEMAND_HARD


def test_helper_preserves_all_blocked_case():
    lo,hi=G._detour_channel_spans(np.zeros(8),np.array([2]),np.array([3]))
    assert (lo.tolist(),hi.tolist())==([2],[3])
