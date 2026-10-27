from types import SimpleNamespace
from unittest.mock import patch
import die_clock_mesh as DM

def vehicle(exact, generic=False, segments=None, ft=None):
 P=SimpleNamespace(W=800.,H=800.,clock={},types={'T':{}},layer_budget={'partition_signal_max':'M7'},parts={'p':{'type':'T'}},rect=lambda n:(0.,0.,800.,800.),to_die=lambda n,xy:xy)
 lat=dict(ys_um=[200.,600.],leaf_ys_um=[200.,600.],xs_um=[200.,600.],leaf_grid=[2,2],drv_reach_um=200.,off_core_resite=True,off_core_drop_driver=True,off_core_alt_l=True,hop_reach_um=405.,actual_leaf_slack=exact)
 if ft is not None:
  P.types['T']['ft_slots']=[dict(name='a',bit_site_cell_um=[1.404,.27],bit_sites_um=[[[200.,200.]]],regs_um=[])]
  lat['avoid_ft_halos']=ft
 if segments is not None:lat['min_level_segments']=segments
 with patch.object(DM.DC,'keepouts',return_value=[(150.,300.,250.,500.,'p/core')]),patch.object(DM.DC,'plan_taps',return_value=[('p','clk',600.,600.,0.)]),patch.object(DM.DC,'plan_tap_early',return_value={}):
  return DM.build(P,2,2,m=1,max_move=0.,rep_um=405.,hop_max=405.,lattice=None if generic else lat)

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


def test_generic_tree_does_not_enter_leaf_grid_optional_policy():
 cells,nets,ports,model=vehicle(False,generic=True)
 assert cells and nets and model['htree']


def test_minimum_segments_adds_equal_stages_to_the_whole_internal_level():
 _,_,_,base=vehicle(True);_,_,_,more=vehicle(True,segments={'1':2})
 assert {x['n_seg'] for x in base['htree'] if x['level']==1} == {1}
 assert {x['n_seg'] for x in more['htree'] if x['level']==1} == {2}
 assert all(x['n_seg']==1 for x in more['htree'] if x.get('leaf'))

def test_leaf_level_cannot_claim_unrealized_extra_buffers():
 import pytest
 with pytest.raises(ValueError,match='internal buffered levels'):
  vehicle(True,segments={'2':2})


def test_ft_halo_planner_moves_driver_off_actual_bit_bank():
 old,_,_,_=vehicle(True,ft=False);new,_,_,model=vehicle(True,ft=True)
 assert old['ckm_d_0_0_0'] != new['ckm_d_0_0_0']
 assert not model['clock_ft_keepout_violations']
 assert model['meta']['ft_halo_um']==2.0

def test_ft_halo_envelope_respects_mirrored_instance():
 P=SimpleNamespace(parts={'p':{'type':'T'}},types={'T':{'ft_slots':[dict(name='a',bit_site_cell_um=[1.404,.27],bit_sites_um=[[[100.,200.],[105.,200.]]])]}},to_die=lambda n,q:(800.-q[0],q[1]))
 r=DM.ft_halo_keepouts(P)[0]
 assert tuple(round(x,6) for x in r[:4]) == (691.596,198.,702.,202.27)
