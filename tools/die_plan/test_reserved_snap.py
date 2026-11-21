"""FLOW-GRT-RESID 11-21: reserved die-clock-site route obstructions snap their outer edges outward to the track lattice (no sliver track partly under an obstruction)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402


def edges(lines, layer):
    out = []
    for l in lines:
        if f"findLayer {layer}]" in l:
            out.append([float(v) for v in re.findall(r"round\(([-0-9.]+)\*\$rs_u\)", l)])
    return out


def test_snap_out_is_outward_and_on_lattice():
    for layer, (p, off) in gen_phys.RESERVED_TRACKS.items():
        for v in (10.0, 10.017, 123.4561, 0.3):
            lo, hi = gen_phys.snap_out(v, layer, False), gen_phys.snap_out(v, layer, True)
            assert lo <= v + 1e-9 and hi >= v - 1e-9 and hi - lo <= p + 1e-9
            for e in (lo, hi):
                assert abs(((e - off) / p - 0.5) - round((e - off) / p - 0.5)) < 1e-6      # midway between two tracks
    assert gen_phys.snap_out(10.0, "M1", True) == 10.0                                      # no table entry: unchanged


def test_reserved_rect_edges_snap_and_legacy_form_is_unchanged():
    site = (10.0, 10.0, 14.0, 12.0)
    legacy = gen_phys.route_obstruction_lines([(site, ["M4", "M7"])])
    assert edges(legacy, "M4") == [[10.0, 10.0, 14.0, 12.0]]
    L = gen_phys.route_obstruction_lines([(site, ["M1", "M4", "M7"])], snap=True)
    m4, m7, m1 = edges(L, "M4")[0], edges(L, "M7")[0], edges(L, "M1")[0]
    assert m1 == [10.0, 10.0, 14.0, 12.0]
    for e, (p, off) in ((m4, (0.048, 0.024)), (m7, (0.064, 0.032))):
        assert e[0] <= 10.0 and e[1] <= 10.0 and e[2] >= 14.0 and e[3] >= 12.0
        assert all(abs(((v - off) / p - 0.5) - round((v - off) / p - 0.5)) < 1e-6 for v in e)
        assert 10.0 - e[0] < p and e[2] - 14.0 < p


def test_escape_column_edges_stay():
    site = (10.0, 10.0, 14.0, 12.0)
    pins = {"M7": [(11.0, 10.5, 11.032, 11.268)]}
    L = gen_phys.route_obstruction_lines([(site, ["M7"])], pins, snap=True)
    es = edges(L, "M7")
    assert len(es) == 2 and es[0][2] == es[0][2] and any(abs(e[2] - (11.0 - gen_phys.TAP_ESCAPE_CLEAR_UM)) < 1e-9 for e in es)
