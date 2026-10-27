"""Leaf-grid drop-driver pruning retains every live driver and removes electrically empty subtrees."""
from types import SimpleNamespace
from unittest.mock import patch
import die_clock_mesh as DM


def vehicle(block=False,drop_inside=False,reach=0.):
    P=SimpleNamespace(W=1600.,H=1600.,clock={},types={'T':{}},layer_budget={'partition_signal_max':'M7'},parts={'p':{'type':'T'}},rect=lambda n:(0.,0.,1600.,1600.),to_die=lambda n,xy:xy)
    taps=[('p','clk',1200.,1200.,0.)]
    ko=[(1.,1.,799.,799.,'io/PHY')] if block else []
    lat=dict(ys_um=[200.,600.,1000.,1400.],leaf_ys_um=[200.,600.,1000.,1400.],xs_um=[200.,600.,1000.,1400.],leaf_grid=[4,4],drv_reach_um=reach,off_core_resite=True,off_core_drop_driver=True,off_core_alt_l=True,hop_reach_um=750.)
    if drop_inside:lat['io_macro_drivers']='drop_inside'
    with patch.object(DM.DC,'keepouts',return_value=ko),patch.object(DM.DC,'plan_taps',return_value=taps),patch.object(DM.DC,'plan_tap_early',return_value={}):
        return DM.build(P,4,4,m=1,max_move=0.,lattice=lat)


def test_dead_quadrant_is_pruned_before_interior_nodes():
    cells,nets,ports,M=vehicle(True)
    assert len(M['drivers'])==12
    assert 'h00' in M.get('pruned_branches',[])
    assert not any(k.startswith('ckm_n2_h00') or k.startswith('ckm_n3_h00') for k in cells)
    assert all(n['loads'] for n in nets), 'dead subtree left a loadless clock driver'
    driven={v for n in nets for v in n['loads']}
    assert all(c in driven for d in M['drivers'].values() for c in d['cells'])


def test_live_lattice_is_unchanged_without_dropped_drivers():
    cells,nets,ports,M=vehicle(False)
    assert len(M['drivers'])==16
    assert not M.get('pruned_branches')
    assert len([v for v in cells.values() if v['kind']=='node'])==15
    assert all(n['loads'] for n in nets)


def test_ideal_phy_drop_removes_even_near_edge_relocated_driver():
    _,_,_,old=vehicle(True,reach=250.)
    cells,nets,ports,new=vehicle(True,drop_inside=True,reach=250.)
    assert '1_1' in old['drivers'], 'control must have retained a relocated PHY driver'
    assert len(new['drivers'])==12
    assert all(k not in new['drivers'] for k in ('0_0','0_1','1_0','1_1'))
    assert all(d.get('reason')=='io_macro_ideal_inside' for d in new['dropped_drivers'])
    assert 'h00' in new['pruned_branches']
    assert all(n['loads'] for n in nets)
