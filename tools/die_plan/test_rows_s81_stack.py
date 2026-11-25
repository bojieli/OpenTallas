"""rows_s81_stack: stacked internal_stations points get de-stacked, first bus keeps the point, hops stay <= 405."""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_station_stack as A  # noqa: E402
import rows_s81_stack as R  # noqa: E402


def _type(nbus=20):
    st = []
    for i in range(nbus):
        st.append({"conn": f"core:a{i:02d}|core:b", "bits": 1, "from_um": [100.0, 500.0], "to_um": [500.0, 500.0],
                   "regs_um": [[300.0, 500.0]]})
    return {"outline_um": [800.0, 1000.0], "hard_cores": [{"origin_um": [320.0, 450.0], "outline_um": [60.0, 40.0]}],
            "internal_stations": st, "buses": []}


def test_destack_moves_all_but_first():
    t = _type()
    assert A.judge_type(t)["points"] == 1
    t0 = copy.deepcopy(t)
    stat = R.plan_type(t)
    assert stat["moved"] == 19 and not stat["refused"]
    assert A.judge_type(t)["points"] == 0
    assert t["internal_stations"][0]["regs_um"] == t0["internal_stations"][0]["regs_um"]
    for s in t["internal_stations"]:
        assert max(R.hops(s)) <= 405.0 + 1e-6
        x, y = s["regs_um"][0]
        assert not (320 - 4.32 < x < 380 + 4.32 and 450 - 4.32 < y < 490 + 4.32)
