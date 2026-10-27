"""PATH-HBM-R10 top-down lane entry: synthetic checks (new tool; hbm_r9_delta gains opt-in kwargs only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbm_r10_delta as D  # noqa: E402
import hbm_r9_delta as R9  # noqa: E402


def _hub():
    cores = [dict(inst="a", module="m", origin_um=[100.0, 100.0], outline_um=[100.0, 100.0]),
             dict(inst="b", module="m", origin_um=[700.0, 100.0], outline_um=[100.0, 100.0])]
    st = []
    # census cross-product: each core pin tied to BOTH N buses (L0 over x 0..450, L1 over x 450..900), full width
    for bus, x in (("L0_i", 200.0), ("L1_i", 650.0)):
        for c, cx in (("a", 150.0), ("b", 750.0)):
            st.append(dict(conn=f"bus:{bus}", launch=f"face bus {bus}", capture=f"{c}.d", from_um=[x, 400.0],
                           to_um=[cx, 200.0], bits=100, regs_um=[]))
    st.append(dict(conn="bus:L2_i", launch="face bus L2_i", capture="b.w", from_um=[0.0, 150.0], to_um=[700.0, 150.0],
                   bits=64, regs_um=[]))
    st.append(dict(conn="core", launch="a.z", capture="b.z", from_um=[200.0, 150.0], to_um=[700.0, 150.0], bits=8,
                   regs_um=[]))
    buses = [dict(name="L0_i", width=100), dict(name="L1_i", width=100), dict(name="L2_i", width=64)]
    return dict(outline_um=[900.0, 400.0], hard_cores=cores, internal_stations=st, buses=buses)


BI = {"L0_i": dict(partner="p0", ivx=(0.0, 450.0), ivy=None), "L1_i": dict(partner="p1", ivx=(450.0, 900.0), ivy=None),
      "L2_i": dict(partner="p2", ivx=None, ivy=(100.0, 200.0))}


def test_transport_resolves_cross_product():
    st, rep = D.resolve_lanes(_hub(), BI)
    sl = {(s["r10"]["bus"], s["capture"]): s["bits"] for s in st if s.get("r10")}
    assert sl == {("L0_i", "a.d"): 100, ("L1_i", "b.d"): 100, ("L2_i", "b.w"): 64}   # each pin once, nearest lane
    assert rep["old_face_bits_N"] == 400 and rep["new_face_bits_N"] == 200 and rep["broadcast_bits"] == 0
    assert any(s["conn"] == "core" for s in st)                                       # core-core kept


def test_pins_over_consumer_and_we_chain():
    t = _hub()
    st, _ = D.resolve_lanes(t, BI)
    D.place_pins(st, 900.0, 400.0, cap=6.0)
    by = {s["capture"]: s for s in st if s.get("r10")}
    assert abs(by["a.d"]["from_um"][0] - 150.0) < 1e-6 and by["a.d"]["from_um"][1] == 400.0
    assert abs(by["b.d"]["from_um"][0] - 750.0) < 1e-6
    assert 100.0 <= by["b.w"]["from_um"][1] <= 200.0
    assert D.chain_we(st, 900.0, 4, hop=405.0) == 1                                   # 700 um from W > one hop
    assert by["b.w"]["bits"] == 16 and by["b.w"]["bits_parallel"] == 64 and by["b.w"]["serial_k"] == 4


def test_legalise_capacity_and_order():
    pos, dens = D.legalise([("x", 10.0, 60), ("y", 10.0, 60)], 0.0, 100.0, 6.0)
    assert dens == 0.2 and pos["x"] < pos["y"] and abs((pos["y"] - pos["x"]) - 10.0) < 1e-6


def test_r9_default_unchanged_by_opt_in_args():
    t = dict(_hub())
    a = R9.plan_quadrants(t, 2)
    b = R9.plan_quadrants(t, 2, bounds=None, dist_by_x=False)
    assert a == b and "bounds" not in a
    c = R9.plan_quadrants(t, 2, bounds=[450.0])
    assert c["bounds"] == [450.0]
