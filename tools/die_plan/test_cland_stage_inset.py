import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cland_stage_inset as CI  # noqa: E402


def _type(stages_by_bus, w=622.08, h=1399.68, cores=()):
    return {"outline_um": [w, h], "hard_cores": [{"rect_um": list(r)} for r in cores],
            "clock": {"landing_writer_start": {"branches": {b: {"stages": [{"xy_um": list(p)} for p in s]}
                                                                for b, s in stages_by_bus.items()}}}}


def test_corner_stage_is_pulled_in_on_both_axes():
    t = _type({"a": [(300, 700), (617.76, 1395.36)]})
    mv, _ = CI.respot(t)
    (new,) = mv.values()
    assert new[0] <= 617.76 - 25.92 + 1e-6 and new[1] <= 1395.36 - 8.64 + 1e-6


def test_cluster_on_one_edge_spreads_on_the_lattice():
    pts = [(313.44 + 0.4 * i, 4.32) for i in range(6)]
    t = _type({"b%d" % i: [(315, 300), p] for i, p in enumerate(pts)})
    mv, _ = CI.respot(t)
    new = list(mv.values())
    assert len(new) == 6 and all(p[1] >= 4.32 + 8.64 - 1e-6 for p in new)
    for i, p in enumerate(new):
        for q in new[i + 1:]:
            assert abs(p[0] - q[0]) >= 25.92 - 1e-6 or abs(p[1] - q[1]) >= 8.64 - 1e-6


def test_interior_stage_untouched_and_shared_xy_moves_together():
    t = _type({"a": [(300, 700), (300, 4.32), (300, 4.32)], "b": [(300, 700), (300, 4.32), (300, 4.32)]})
    mv, _ = CI.respot(t)
    assert list(mv) == [(300, 4.32)]
    plan = {"partition_types": {"t": t}}
    CI.apply(plan)
    st = [s["xy_um"] for s in plan["partition_types"]["t"]["clock"]["landing_writer_start"]["branches"]["a"]["stages"]]
    assert st[0] == [300, 700] and st[1] == st[2] and st[1][1] >= 12.96 - 1e-6


def test_stage_count_and_branches_unchanged_and_hard_core_avoided():
    t = _type({"a": [(300, 700), (617.76, 600)]}, cores=[(560, 560, 618, 640)])
    n0 = len(t["clock"]["landing_writer_start"]["branches"]["a"]["stages"])
    plan = {"partition_types": {"t": t}}
    CI.apply(plan)
    br = plan["partition_types"]["t"]["clock"]["landing_writer_start"]["branches"]["a"]["stages"]
    assert len(br) == n0
    x, y = br[1]["xy_um"]
    assert not (560 - 4.32 <= x <= 618 + 4.32 and 560 - 4.32 <= y <= 640 + 4.32)
