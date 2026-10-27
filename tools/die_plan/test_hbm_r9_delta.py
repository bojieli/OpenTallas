"""PATH-HBM-R9 hub service-quadrant delta: synthetic topology checks (new tool; no existing output changes)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbm_r9_delta as D  # noqa: E402


def _hub():
    cores = [dict(inst="svc", module="m_svc", origin_um=[400.0, 100.0], outline_um=[200.0, 200.0]),
             dict(inst="d0", module="m_d", origin_um=[100.0, 100.0], outline_um=[100.0, 100.0]),
             dict(inst="d1", module="m_d", origin_um=[700.0, 100.0], outline_um=[100.0, 100.0])]
    st = [dict(conn="f0", launch="face_n.a", from_um=[50.0, 400.0], to_um=[450.0, 300.0], bits=100, regs_um=[]),
          dict(conn="f1", launch="face_n.b", from_um=[850.0, 400.0], to_um=[550.0, 300.0], bits=60, regs_um=[]),
          dict(conn="c0", launch="svc.x", from_um=[400.0, 150.0], to_um=[200.0, 150.0], bits=10, regs_um=[]),
          dict(conn="c1", launch="svc.y", from_um=[600.0, 150.0], to_um=[700.0, 150.0], bits=10, regs_um=[]),
          dict(conn="w0", launch="face_w.c", from_um=[0.0, 200.0], to_um=[400.0, 200.0], bits=40, regs_um=[]),
          dict(conn="dd", launch="d0.z", from_um=[200.0, 120.0], to_um=[700.0, 120.0], bits=8, regs_um=[])]
    return dict(outline_um=[900.0, 400.0], hard_cores=cores, internal_stations=st)


def test_replicate_and_lane_ownership():
    Q = D.plan_quadrants(_hub(), 2)
    names = sorted(h["inst"] for h in Q["cores"])
    assert names == ["d0", "d1", "svc__q0", "svc__q1"]
    assert Q["rep_mod"] == ["m_svc"]
    ends = {s["conn"]: [] for s, *_ in Q["stations"]}
    for s, ea, eb, ka, kb in Q["stations"]:
        ends[s["conn"]].append((ea[1] if ea[0] == "C" else "F", eb[1] if eb[0] == "C" else "F", ka, kb, s["bits"]))
    assert ends["f0"] == [("F", "svc__q0", 0, 0, 100)]            # N face lane lands at its segment's copy
    assert ends["f1"] == [("F", "svc__q1", 1, 1, 60)]
    assert ends["c0"] == [("svc__q0", "d0", 0, 0, 10)]             # copy serves the distributed instance in its segment
    assert ends["c1"] == [("svc__q1", "d1", 1, 1, 10)]
    w = sorted(ends["w0"], key=lambda r: r[3])                     # W face split by lane weight (110 : 70)
    assert [r[1] for r in w] == ["svc__q0", "svc__q1"] and sum(r[4] for r in w) >= 40
    assert ends["dd"] == [("d0", "d1", 0, 1, 8)]                   # inter-segment link stays one station
    assert D.boundary_bits(Q) == [8 + w[1][4]]


def test_serialise_inter_segment_only():
    t = _hub()
    Q = D.plan_quadrants(t, 2)
    cores, st, infos, stats = D.realise(t, Q, 400.0, kx=4, route=False)
    by = {s["conn"]: s for s in st if s["conn"] in ("dd", "c0", "f0")}
    assert by["dd"]["bits"] == 2 and by["dd"]["serial_k"] == 4 and by["dd"]["bits_parallel"] == 8
    assert "serial_k" not in by["c0"] and "serial_k" not in by["f0"]
    assert stats["inter_segment"] == sum(1 for s in st if s["r9_segments"][0] != s["r9_segments"][1])
