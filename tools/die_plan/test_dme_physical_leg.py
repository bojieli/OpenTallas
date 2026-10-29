"""A geometry-derived legal detour must have the same cost and cells at export."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_trial as D


class Site:
    W, H = 1200., 1200.
    def legal(self, q):
        return 0 <= q[0] <= self.W and 0 <= q[1] <= self.H and not (100 < q[0] < 700 and 201 < q[1] < 899)
    def nearest(self, q, axis=None):
        if self.legal(q): return q
        return (700.6, q[1])


@pytest.fixture(autouse=True)
def mode(monkeypatch):
    monkeypatch.setattr(D, 'DME_ACTUAL_MAX_UM', 405.)
    monkeypatch.setattr(D, 'EVEN_LEGS', True)


def test_actual_gap_detour_is_priced_before_export():
    site = Site();a=(400.,900.);b=(400.,200.)
    pl = D.physical_leg(site,a,b,250.)
    assert pl['repairs'] and pl['stages'] % 2 == 0
    assert max(D._man(x,y) for x,y in zip(pl['chain'],pl['chain'][1:])) <= 405
    assert all(site.legal(q) for q in pl['chain'])
    assert pl['delay_ps'] == pytest.approx(D.chain_ps(pl['chain']))
    assert pl['delay_ps'] > D.leg_ps(D._man(a,b),250.)
    n={0:dict(id=0,x=a[0],y=a[1],parent=None,level=0,kids=[1],taps=[]),
       1:dict(id=1,x=b[0],y=b[1],parent=0,level=1,kids=[],taps=[('p','clk',*b)],physical_leg=pl)}
    v,placed,_,_,parents=D.tree_netlist(n,[],rep_um=250.,site=site,clock_cell='inv2')
    xy={i:(x,y) for i,x,y in placed};p=['b1']
    while p[-1] in parents:p.append(parents[p[-1]])
    chain=tuple(xy[i] for i in reversed(p))
    assert chain == n[1]['physical_leg']['chain']
    assert D.chain_ps(chain) == n[1]['physical_leg']['delay_ps']


def test_export_rejects_changed_endpoint():
    site=Site();pl=D.physical_leg(site,(400.,900.),(400.,200.),250.)
    n={0:dict(id=0,x=400.,y=900.,parent=None,level=0,kids=[1],taps=[]),
       1:dict(id=1,x=401.,y=200.,parent=0,level=1,kids=[],taps=[],physical_leg=pl)}
    with pytest.raises(ValueError,match='changed after DME'):
        D.tree_netlist(n,[],rep_um=250.,site=site,clock_cell='inv2')


def test_default_leg_cost_is_unchanged(monkeypatch):
    monkeypatch.setattr(D,'DME_ACTUAL_MAX_UM',None)
    assert D.placed_leg_ps(Site(),(400.,900.),(400.,200.),250.) == D.leg_ps(700.,250.)


def test_physical_mode_prices_leaf_wire_even_without_snakes(monkeypatch):
    site=Site();tap=('p','clk',400.,500.)
    dn,root,_=D.dme_region_tree(site,[tap],delay_rep_um=250.,snake=False)
    distance=D._man((dn[root]['x'],dn[root]['y']),tap[2:])
    assert dn[root]['S'] == pytest.approx(D.tap_wire_ps(distance))
    monkeypatch.setattr(D,'DME_ACTUAL_MAX_UM',None)
    old,root,_=D.dme_region_tree(site,[tap],delay_rep_um=250.,snake=False)
    assert old[root]['S'] == pytest.approx(D._man((old[root]['x'],old[root]['y']),tap[2:]))


def test_prebuild_body_homes_have_native_r0_grid_and_no_overlaps():
    class OpenSite:
        def legal(self,q):return 0 <= q[0] <= 100 and 0 <= q[1] <= 100
    p=D.physical_pack(OpenSite(),[('a',50.,50.),('b',50.,50.),('c',50.,50.)])
    for name,x,y in p:
        assert abs(x/.054-round(x/.054)) < 1e-6
        assert abs(y/.54-round(y/.54)) < 1e-6
    for i,(_,x,y) in enumerate(p):
        for _,a,b in p[i+1:]:assert abs(a-x)>=1.62-1e-6 or abs(b-y)>=.27-1e-6
