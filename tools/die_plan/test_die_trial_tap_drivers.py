from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D


def _tree():
    nodes = {0: dict(id=0, x=0.0, y=0.0, parent=None, level=0, kids=[1], taps=[]),
             1: dict(id=1, x=300.0, y=0.0, parent=0, level=1, kids=[],
                     taps=[("pa", "clk", 300.0, 50.0), ("pb", "clk", 600.0, 300.0), ("pc", "clk", 0.0, 100.0)])}
    return nodes


def test_default_tree_unchanged_leaf_drives_all_taps():
    v, place, tp, nb, par = D.tree_netlist(_tree(), [], 450.0)
    assert "assign t_pa__clk = n1;" in v and not any(i.startswith("d") for i, *_ in place)


def test_tap_drivers_one_buffer_per_tap_uniform_depth():
    v, place, tp, nb, par = D.tree_netlist(_tree(), [], 450.0, tap_drivers=True)
    drv = [i for i, *_ in place if i.startswith("d")]
    assert len(drv) == 3 and all(par[d] == nb[1] for d in drv)
    for k in range(3):
        assert f"(.A(n1), .Y(dn1_{k}))" in v
    assert "assign t_pb__clk = dn1_1;" in v


def test_tap_driver_midpoint_on_long_leg():
    # leg 300 H + 300 V = 600 > 450: driver at path midpoint (end of the H run here), both halves 300
    assert D.tap_driver_xy(300.0, 0.0, 600.0, 300.0, 450.0) == (600.0, 0.0)
    assert D.tap_driver_xy(300.0, 0.0, 300.0, 50.0, 450.0) == (300.0, 0.0)
    x, y = D.tap_driver_xy(0.0, 0.0, 100.0, 400.0, 450.0)
    assert (x, y) == (100.0, 150.0)
