"""CLOCK-KV-R13: split_drops gives each opposite drop pair of one trunk junction its own via/track (opt-in)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_clock_128 as C128  # noqa: E402

BUF_W, ROW_Y = 1.62, 0.27


def _toy():
    # leaf-row pair: a horizontal trunk from the driver, two loads straight above and below one x (shared junction)
    cells = {"d": dict(x=100.0, y=500.0), "u": dict(x=200.0, y=595.0), "w": dict(x=200.0, y=405.0)}
    M = dict(taps=[], meta=dict(root_um=[0.0, 0.0]))
    nets = [dict(name="n", drv="d", loads=["u", "w"])]
    return M, cells, nets


def _drops(w):
    return [s for s in w["segs"][1:] if s[0] == "M9"]


def test_default_shares_junction():
    M, cells, nets = _toy()
    w = C128.fixed_wires(M, cells, nets, BUF_W, ROW_Y)[0]
    d = _drops(w)
    assert len(d) == 2 and abs(d[0][1] - d[1][1]) < 1e-9   # unchanged default: one shared x / via


def test_split_drops_own_track():
    M, cells, nets = _toy()
    w = C128.fixed_wires(M, cells, nets, BUF_W, ROW_Y, split_drops=True)[0]
    d = _drops(w)
    assert len(d) == 2 and abs(d[0][1] - d[1][1]) >= C128.DROP_SPLIT_UM - 1e-9
    t = w["segs"][0]
    assert t[0] == "M8" and t[1] <= min(s[1] for s in d) and t[3] >= max(s[1] for s in d)   # trunk reaches both vias


def test_same_side_drops_not_split():
    M, cells, nets = _toy()
    cells["w"] = dict(x=200.0, y=560.0)      # both loads above: no shared opposite junction
    w = C128.fixed_wires(M, cells, nets, BUF_W, ROW_Y, split_drops=True)[0]
    d = _drops(w)
    assert abs(d[0][1] - d[1][1]) < 1e-9
