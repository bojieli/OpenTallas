import pytest
import die_trial as D


def _nodes():
    return {0:dict(x=0., y=0., parent=None, taps=[("p", "clk", 900., 300.)])}


def test_default_preserves_direct_tap_assignment():
    v, place, taps, _, _ = D.tree_netlist(_nodes(), [])
    assert "assign t_p__clk = n0;" in v
    assert len(place) == 1


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
