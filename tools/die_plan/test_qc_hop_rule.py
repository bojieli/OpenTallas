import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import qc_hop_rule as R


def test_first_hop_uses_bit_span_not_window_centre():
    # slw_fe_v2 x_stm_p1_i: face (0,1693.6), leaf (311,915.8), window 113 um, plan hops were 435/218/218/218
    face, leaf = (0, 1693.6), (311.04, 915.84)
    regs, hops, ok = R.plan_chain(face, leaf, 3, 113.0)
    assert ok and max(hops) + 113 / 2 + R.REG_SPREAD_UM / 2 <= R.REACH_UM + 1e-6
    assert hops[0] <= R.REACH_UM - (113 / 2 + R.REG_SPREAD_UM / 2) + 1e-6
    # the old plan (first hop 435 from the window centre) must be rejected by the same limits
    assert not R.plan_chain(face, leaf, 3, 113.0)[2] or max(hops) < 435


def test_last_hop_aims_at_consumer_centroid():
    # slw_fw_v2 x_ctl_i: last reg (304.7,1100.4); core leaf y917 but consumers y 500-657
    consumers = [(290, 500), (340, 657), (310, 570), (320, 600)]
    r = R.plan_from_consumers((330.2, 1831.7), consumers, 109.0)
    c = R.centroid(consumers)
    assert r["ok"] and abs(r["aim_um"][1] - c[1]) < 1
    last = r["regs_um"][-1]
    assert max(R.l1(last, p) for p in consumers) <= R.REACH_UM - R.LAST_SLACK_UM


def test_min_regs_grows_with_span_and_distance():
    n0 = R.min_regs((0, 0), (0, 600), 0.0)
    n1 = R.min_regs((0, 0), (0, 600), 300.0)
    assert n1 >= n0 and R.min_regs((0, 0), (0, 100), 10.0) == 0


def test_regs_lie_on_line_and_count_is_n():
    regs, hops, ok = R.plan_chain((0, 0), (300, 600), 2, 50.0)
    assert len(regs) == 2 and abs(sum(hops) - 900) < 0.5
