from types import SimpleNamespace
from unittest.mock import patch
import die_clock_mesh as DM

def vehicle(exact):
 P=SimpleNamespace(W=800.,H=800.,clock={},types={'T':{}},layer_budget={'partition_signal_max':'M7'},parts={'p':{'type':'T'}},rect=lambda n:(0.,0.,800.,800.),to_die=lambda n,xy:xy)
 lat=dict(ys_um=[200.,600.],leaf_ys_um=[200.,600.],xs_um=[200.,600.],leaf_grid=[2,2],drv_reach_um=200.,off_core_resite=True,off_core_drop_driver=True,off_core_alt_l=True,hop_reach_um=405.,actual_leaf_slack=exact)
 with patch.object(DM.DC,'keepouts',return_value=[(150.,300.,250.,500.,'p/core')]),patch.object(DM.DC,'plan_taps',return_value=[('p','clk',600.,600.,0.)]),patch.object(DM.DC,'plan_tap_early',return_value={}):
  return DM.build(P,2,2,m=1,max_move=0.,rep_um=405.,hop_max=405.,lattice=lat)

def test_actual_leaf_positions_allow_node_to_escape_core_without_extra_stages():
 _,_,_,old=vehicle(False);_,_,_,new=vehicle(True)
 assert len(old['pushdown'])==1
 assert not new['pushdown']
 assert not new['unplaced']
 assert len(old['htree'])==len(new['htree'])
 assert all(x['n_seg']==y['n_seg'] for x,y in zip(old['htree'],new['htree']))


def test_nearest_free_search_keeps_actual_incoming_reach_bound():
    # A geometrically free point may lie outside its already placed parent's
    # reach. Search must keep going, including when the ideal point is free.
    q, _ = DM.free_near(SimpleNamespace(hit=lambda *a, **k: False), (0., 0.), limit=4., step=1., accept=lambda z: z[0]>=2.)
    assert q == (2., 0.)
