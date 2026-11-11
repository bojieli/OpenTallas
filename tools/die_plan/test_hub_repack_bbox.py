"""CPL-S81-LEAF 11-11: route_station must keep a 1-register station whose only legal register sites are off both
L routes (the S81 leaf base geometry: 312 stations in 39 types were reported need_more_regs while unmoved)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hub_repack as HR  # noqa: E402

A, B = (10.08, 10.08), (600.48, 198.72)          # Manhattan 778.6 <= 2 x 405
CORES = [(300, 0, 460, 100), (150, 150, 270, 270)]  # block the 1-reg site on the HV and on the VH route


def _hops(a, regs, b):
    pts = [a] + list(regs) + [b]
    return [abs(q[0] - p[0]) + abs(q[1] - p[1]) for p, q in zip(pts, pts[1:])]


def test_off_l_site_keeps_one_register():
    R = HR.Raster(800, 800, CORES)
    r = HR.route_station(R, A, B, 1, 405.0)
    assert r is not None and len(r["regs"]) == 1 and r["kind"] == "bbox"
    assert max(_hops(A, r["regs"], B)) <= 405.0 + 1e-6
    assert all(R.free(x, y) for x, y in r["regs"])


def test_l_route_still_preferred_when_it_fits():
    R = HR.Raster(800, 800, [])
    r = HR.route_station(R, A, B, 1, 405.0)
    assert r is not None and len(r["regs"]) == 1 and r["kind"] in ("HV", "VH")


def test_bbox_none_when_no_free_site():
    R = HR.Raster(800, 800, [(60, 0, 560, 260)])
    assert HR.place_regs_bbox(R, A, B, 1, 405.0) is None
