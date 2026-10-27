"""COORD GEOM HBM planU4f B1/B2: station / ft registers inside a hard core are a G0 ERROR (check.check_station_in_core)."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check


class _T:
    def __init__(self, types):
        self.types = types


def _type(st_reg, ft_reg):
    return dict(outline_um=[400.0, 400.0],
                hard_cores=[dict(inst="u_core", origin_um=[100.0, 100.0], outline_um=[100.0, 100.0], track_offset_um=[0.0, 0.0])],
                internal_stations=[dict(conn="bus:Lx", from_um=[0.0, 150.0], to_um=[100.0, 150.0], regs_um=[st_reg])],
                ft_slots=[dict(name="L1x1", width=1, stations=1, regs_um=[ft_reg])])


def _run(t):
    R = check.Report(); out = check.check_station_in_core(_T(dict(tt=t)), R)
    return out, [i for i in R.errors() if i["check"] == "station_in_core"]


def test_regs_inside_core_fail():
    out, errs = _run(_type([150.0, 150.0], [120.0, 180.0]))
    assert out == dict(stations=1, ft_regs=1) and len(errs) == 2
    assert "inside hard core u_core" in errs[0]["msg"]


def test_regs_on_street_and_edge_pass():
    out, errs = _run(_type([50.0, 150.0], [100.2, 150.0]))   # street; on the core edge (within eps) is not inside
    assert out == dict(stations=0, ft_regs=0) and not errs


def test_track_offset_applied():
    t = _type([50.0, 150.0], [205.0, 150.0]); t["hard_cores"][0]["track_offset_um"] = [10.0, 0.0]   # core now 110..210
    out, errs = _run(t)
    assert out["ft_regs"] == 1 and len(errs) == 1


def test_is_g0_not_g0c():
    assert "station_in_core" not in check.G0C_CHECKS
