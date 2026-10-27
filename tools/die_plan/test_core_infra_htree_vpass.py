"""HBM-CORE-LAT-R3: core_infra_htree --macro-vertical-pass (macros = node keep-outs crossed vertically only) and the
minimax-site radius widening.  Default behaviour (macros = wire walls) must be unchanged."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load():
    spec = importlib.util.spec_from_file_location("core_infra_htree_t", HERE / "core_infra_htree.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


CORE = (0.0, 0.0, 54.0, 54.0)
MAC = [("m0", (10.0, 20.0, 44.0, 34.0), (10.0, 21.0))]       # a macro band across the middle


def test_default_macro_is_wall():
    H = load(); H.MACRO_VPASS = False
    mz = H.Maze(CORE, MAC, G=0.54)
    a, b = mz.cell((27.0, 5.0)), mz.cell((27.0, 49.0))
    # wall: the path must detour around the macro (longer than the straight 44 um)
    assert mz.md(a, b) > 44.0 + 10.0


def test_vpass_vertical_straight_horizontal_blocked():
    H = load(); H.MACRO_VPASS = True
    mz = H.Maze(CORE, MAC, G=0.54)
    a, b = mz.cell((27.0, 5.0)), mz.cell((27.0, 49.0))
    assert abs(mz.md(a, b) - 44.0) < 1.1                      # straight vertical crossing
    i, j = round(27.0 / 0.54), round(27.0 / 0.54)
    assert not mz.site_ok(i, j)                               # no buffer on the macro
    assert not mz.step_ok(i, j, i + 1, j)                     # no horizontal move over it
    assert mz.step_ok(i, j, i, j + 1)                         # vertical move allowed
    p = mz.path(a, b)
    assert all(q[0] == p[0][0] for q in p)                    # the path stays on one column
    H.MACRO_VPASS = False


def test_minimax_widens_radius():
    H = load(); H.MACRO_VPASS = False
    big = [("m0", (2.0, 2.0, 52.0, 40.0), (2.0, 3.0))]
    mz = H.Maze(CORE, big, G=0.54)
    ch = [mz.cell((1.0, 1.0)), mz.cell((53.0, 1.0))]
    s = H.minimax_site(mz, ch, mz.cell((27.0, 20.0), node=False), radius=4)
    assert mz.site_ok(*s)
