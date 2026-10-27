import pytest
import die_trial as D


def _nodes():
    return {0:dict(x=0., y=0., parent=None, taps=[("p", "clk", 900., 300.)])}


def test_default_preserves_direct_tap_assignment():
    v, place, taps, _, _ = D.tree_netlist(_nodes(), [])
    assert "assign t_p__clk = n0;" in v
    assert len(place) == 1


def test_inter_node_repeater_names_and_parent_chain_are_distinct():
    nodes={0:dict(x=0.,y=0.,parent=None,taps=[]),
           1:dict(x=1500.,y=0.,parent=0,taps=[("p","clk",1500.,0.)])}
    v,place,_,_,parent=D.tree_netlist(nodes,[],rep_um=405.)
    assert len({name for name,*_ in place})==len(place)==5
    assert parent==dict(r1_0="b0",r1_1="r1_0",r1_2="r1_1",b1="r1_2")
    assert all(a!=b for a,b in parent.items())


def test_long_last_mile_is_repeated_along_manhattan_route():
    v, place, taps, _, parent = D.tree_netlist(_nodes(), [], tap_rep_um=405.)
    assert len(place) == 3
    assert "assign t_p__clk = rtn0_0_1;" in v
    assert parent["rtap0_0_0"] == "b0"
    assert parent["rtap0_0_1"] == "rtap0_0_0"
    xy = [(0.,0.)]+[(x,y) for name,x,y in place if name.startswith("rtap")]+[(900.,300.)]
    assert max(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(xy,xy[1:])) <= 405.


def test_illegal_siting_cannot_silently_exceed_reach():
    class BadSite:
        def nearest(self, xy):
            return (1000.,1000.)
    with pytest.raises(ValueError, match="no legal tap-repeater sequence"):
        D.tree_netlist(_nodes(), [], site=BadSite(), tap_rep_um=405.)


def test_resited_long_leg_gets_legal_channel_anchors():
    class BoxSite:
        b=1000
        forb=[(0.,0.,648.,300.,"macro")]
        idx={(-1,-1):[0],(-1,0):[0],(0,-1):[0],(0,0):[0]}
        def legal(self,p):return not(0<p[0]<648 and 0<p[1]<300)
        def nearest(self,p,axis=None):
            if self.legal(p):return p
            return min([(-.6,p[1]),(648.6,p[1]),(p[0],-.6),(p[0],300.6)],
                       key=lambda q:abs(q[0]-p[0])+abs(q[1]-p[1]))
    a=(-20.,150.);b=(668.,150.);site=BoxSite()
    chain=D.legal_repeater_chain(a,b,site,405.)
    assert chain and all(site.legal(p) for p in chain)
    points=[a]+chain+[b]
    assert max(abs(p[0]-q[0])+abs(p[1]-q[1]) for p,q in zip(points,points[1:]))<=405.
